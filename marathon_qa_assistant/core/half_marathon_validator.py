from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from marathon_qa_assistant.core.half_marathon_glossary import (
    evidence_basis_for_constraint,
    term_ids_for_constraint,
    term_ids_for_workout,
)
from marathon_qa_assistant.core.half_marathon_protocol import HM_SAFETY_CONSTRAINTS
from marathon_qa_assistant.core.half_marathon_schedule_composer import build_hmp_repair_suggestions


HMP_HARD_WORKOUT_IDS = {
    "hm_95_long_fast_run",
    "hm_100_float_intervals",
    "hm_105_specific_speed",
    "hm_110_support_speed",
}

SPEED_CALIBRATION_KEYWORDS = (
    "5K",
    "5k",
    "8K",
    "8k",
    "10K",
    "10k",
    "当前",
    "当时",
    "估测",
    "测试",
    "比赛",
    "校准",
)
ENVIRONMENT_OR_FATIGUE_KEYWORDS = (
    "高温",
    "湿热",
    "炎热",
    "大风",
    "强风",
    "有风",
    "伤",
    "疼",
    "酸痛",
    "疲劳",
    "状态差",
)
DOWNGRADE_KEYWORDS = (
    "降级",
    "下调",
    "缩短",
    "延后",
    "改为",
    "走路",
    "体感",
    "恢复跑",
    "取消",
)

DAY_ORDER = {
    "周一": 1,
    "周二": 2,
    "周三": 3,
    "周四": 4,
    "周五": 5,
    "周六": 6,
    "周日": 7,
}


@dataclass(frozen=True)
class HMPlanValidationIssue:
    severity: str
    constraint_id: str
    label: str
    message: str
    recommendation: str
    week_index: Optional[int] = None
    day: str = ""
    workout_type: str = ""
    evidence_basis: Dict[str, Any] = field(default_factory=dict)
    term_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def validate_half_marathon_protocol_plan(plan_dict: Dict[str, Any]) -> Dict[str, Any]:
    protocol = plan_dict.get("half_marathon_protocol") or {}
    if not isinstance(protocol, dict) or not protocol.get("active"):
        return {
            "active": False,
            "passed": True,
            "errors": [],
            "warnings": [],
            "issues": [],
            "checked_constraints": [],
            "repair_suggestions": [],
        }

    week_plans = [week for week in (plan_dict.get("week_plans") or []) if isinstance(week, dict)]
    issues: List[HMPlanValidationIssue] = []

    issues.extend(_validate_recent_marathon_intro(protocol, week_plans))
    issues.extend(_validate_sub70_volume_scaling(protocol, week_plans))
    issues.extend(_validate_capacity_budget(protocol, week_plans))
    issues.extend(_validate_quality_recovery_gap(week_plans))
    issues.extend(_validate_long_fast_run_progression(week_plans))
    issues.extend(_validate_100_hmp_timing(week_plans))
    issues.extend(_validate_dynamic_speed_calibration(week_plans))
    issues.extend(_validate_environment_or_fatigue_downgrade(week_plans))

    errors = [issue.message for issue in issues if issue.severity == "error"]
    warnings = [issue.message for issue in issues if issue.severity == "warning"]
    result = {
        "active": True,
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "issues": [issue.to_dict() for issue in issues],
        "checked_constraints": list(HM_SAFETY_CONSTRAINTS.keys()),
    }
    result["repair_suggestions"] = build_hmp_repair_suggestions(result)
    return result


def _validate_recent_marathon_intro(protocol: Dict[str, Any], week_plans: List[Dict[str, Any]]) -> List[HMPlanValidationIssue]:
    if not protocol.get("recent_marathon"):
        return []

    issues: List[HMPlanValidationIssue] = []
    for week in week_plans[:2]:
        week_index = _week_index(week)
        for session in _actual_hmp_sessions(week):
            workout_type = session["workout_type"]
            if workout_type in HMP_HARD_WORKOUT_IDS:
                issues.append(_issue(
                    severity="error",
                    constraint_id="marathon_recovery_intro",
                    week_index=week_index,
                    day=session["day"],
                    workout_type=workout_type,
                    message=f"第 {week_index} 周 {session['day']} 在刚比完全马导入期出现 {session['label']}，恢复风险过高。",
                    recommendation="前 1-2 周应以恢复、轻松跑、短法特莱克或坡冲为主，再逐步进入半马专项课。",
                ))
    return issues


def _validate_sub70_volume_scaling(protocol: Dict[str, Any], week_plans: List[Dict[str, Any]]) -> List[HMPlanValidationIssue]:
    input_mileage = _safe_float(protocol.get("input_weekly_mileage_km"))
    if input_mileage is None:
        return []

    issues: List[HMPlanValidationIssue] = []
    for week in week_plans:
        week_index = _week_index(week)
        planned_volume = _week_volume_km(week)
        if planned_volume is None:
            continue
        aggressive_jump = planned_volume >= max(110.0, input_mileage * 1.6)
        if aggressive_jump and input_mileage < 90:
            issues.append(_issue(
                severity="warning",
                constraint_id="no_sub70_volume_copy",
                week_index=week_index,
                message=f"第 {week_index} 周计划跑量约 {planned_volume:.1f} km，明显接近 Sub-70 案例跑量，但画像周跑量仅约 {input_mileage:.1f} km。",
                recommendation="应按用户历史跑量缩放，而不是把 110-130km/周作为默认半马目标。",
            ))
    return issues


def _validate_capacity_budget(protocol: Dict[str, Any], week_plans: List[Dict[str, Any]]) -> List[HMPlanValidationIssue]:
    budget_by_week = _capacity_budget_by_week(protocol)
    fallback_budget = protocol.get("capacity_budget") if isinstance(protocol.get("capacity_budget"), dict) else {}
    if not budget_by_week and not fallback_budget:
        return []

    issues: List[HMPlanValidationIssue] = []
    for week in week_plans:
        week_index = _week_index(week)
        budget = budget_by_week.get(week_index) or fallback_budget
        if not budget:
            continue

        sessions = _actual_hmp_sessions(week)
        quality_max = _safe_float(budget.get("quality_sessions_max"))
        hard_count = sum(1 for item in sessions if item["workout_type"] in HMP_HARD_WORKOUT_IDS)
        if quality_max is not None and hard_count > quality_max:
            issues.append(_issue(
                severity="warning",
                constraint_id="capacity_budget_exceeded",
                week_index=week_index,
                message=f"第 {week_index} 周 HMP 硬课 {hard_count} 堂，超过容量预算上限 {quality_max:.0f} 堂。",
                recommendation="按当前周跑量和可训练日压缩质量课密度，保留一堂主课，其余改为轻松跑或90% HMP支撑。",
            ))

        for session in sessions:
            workout_type = session["workout_type"]
            budget_key = _capacity_budget_key(workout_type)
            if not budget_key:
                continue
            cap = _safe_float(budget.get(budget_key))
            if cap is None or cap <= 0:
                continue
            observed = _hmp_workout_volume_km(session["text"], workout_type)
            if observed is None:
                continue
            if observed > cap + 0.5:
                issues.append(_issue(
                    severity="warning",
                    constraint_id="capacity_budget_exceeded",
                    week_index=week_index,
                    day=session["day"],
                    workout_type=workout_type,
                    message=(
                        f"第 {week_index} 周 {session['day']} {session['label']} 约 {observed:.1f} km，"
                        f"超过当前容量预算上限 {cap:.1f} km。"
                    ),
                    recommendation="应按用户周跑量、恢复状态和当前能力缩短HMP累计量，而不是照搬Sub-70理想容量。",
                ))
    return issues


def _validate_quality_recovery_gap(week_plans: List[Dict[str, Any]]) -> List[HMPlanValidationIssue]:
    issues: List[HMPlanValidationIssue] = []
    previous: Optional[Tuple[int, int, Dict[str, str]]] = None

    for week in week_plans:
        week_index = _week_index(week)
        for session in _actual_hmp_sessions(week):
            day_number = DAY_ORDER.get(session["day"])
            if day_number is None:
                continue
            absolute_day = (week_index - 1) * 7 + day_number
            if previous is not None:
                previous_week, previous_day, previous_session = previous
                if absolute_day - previous_day < 2:
                    issues.append(_issue(
                        severity="warning",
                        constraint_id="quality_recovery_gap",
                        week_index=week_index,
                        day=session["day"],
                        workout_type=session["workout_type"],
                        message=(
                            f"第 {previous_week} 周 {previous_session['day']} 与第 {week_index} 周 {session['day']} "
                            "半马专项质量课间隔不足 48 小时。"
                        ),
                        recommendation="半马专项大课之间通常应保留至少 48 小时恢复，必要时下调后一堂课容量。",
                    ))
            previous = (week_index, absolute_day, session)
    return issues


def _validate_long_fast_run_progression(week_plans: List[Dict[str, Any]]) -> List[HMPlanValidationIssue]:
    issues: List[HMPlanValidationIssue] = []
    seen_support = False
    seen_short_95 = False

    for week in week_plans:
        week_index = _week_index(week)
        for session in _actual_hmp_sessions(week):
            workout_type = session["workout_type"]
            distance = _max_distance_km(session["text"])

            if workout_type == "hm_90_support_endurance":
                seen_support = True
            if workout_type == "hm_95_long_fast_run":
                if distance is not None and distance < 18:
                    seen_short_95 = True
                if distance is not None and distance >= 20 and not (seen_support or seen_short_95):
                    issues.append(_issue(
                        severity="error",
                        constraint_id="progress_long_fast_run",
                        week_index=week_index,
                        day=session["day"],
                        workout_type=workout_type,
                        message=f"第 {week_index} 周 {session['day']} 直接出现约 {distance:.1f} km 的 95% HMP 长距离快速跑，缺少前置进阶。",
                        recommendation="先安排较短 95% HMP、90% HMP 辅助耐力或分段递进跑，再进入 20-25km 上限课。",
                    ))
                seen_short_95 = True
    return issues


def _validate_100_hmp_timing(week_plans: List[Dict[str, Any]]) -> List[HMPlanValidationIssue]:
    total_weeks = len(week_plans)
    issues: List[HMPlanValidationIssue] = []

    for week in week_plans:
        week_index = _week_index(week)
        weeks_to_race = total_weeks - week_index + 1
        phase_text = str(week.get("phase") or "")
        for session in _actual_hmp_sessions(week):
            if session["workout_type"] != "hm_100_float_intervals":
                continue
            max_rep_km = _max_repetition_km(session["text"])
            if weeks_to_race > 6 or "基础" in phase_text or "导入" in phase_text:
                issues.append(_issue(
                    severity="error",
                    constraint_id="race_specific_timing",
                    week_index=week_index,
                    day=session["day"],
                    workout_type=session["workout_type"],
                    message=f"第 {week_index} 周 {session['day']} 过早出现 100% HMP 核心专项巡航恢复课。",
                    recommendation="100% HMP 核心课应主要放在比赛专项阶段，通常从赛前约 6 周开始逐步推进。",
                ))
            elif max_rep_km >= 2.5 and weeks_to_race > 3:
                issues.append(_issue(
                    severity="warning",
                    constraint_id="race_specific_timing",
                    week_index=week_index,
                    day=session["day"],
                    workout_type=session["workout_type"],
                    message=f"第 {week_index} 周 {session['day']} 的 100% HMP 单段已接近 {max_rep_km:.1f} km，进阶时点偏早。",
                    recommendation="参考 6/4/2 周进阶：1km -> 2km -> 3km 交替跑，避免过早进入最长单段。",
                ))
            elif max_rep_km >= 1.5 and weeks_to_race > 5:
                issues.append(_issue(
                    severity="warning",
                    constraint_id="race_specific_timing",
                    week_index=week_index,
                    day=session["day"],
                    workout_type=session["workout_type"],
                    message=f"第 {week_index} 周 {session['day']} 已进入 2km 级别 100% HMP 间歇，早于标准进阶。",
                    recommendation="赛前约 6 周优先从 1km/1km 巡航恢复交替跑开始。",
                ))
    return issues


def _validate_dynamic_speed_calibration(week_plans: List[Dict[str, Any]]) -> List[HMPlanValidationIssue]:
    plan_text = " ".join(_week_text(week) for week in week_plans)
    has_speed_hmp = any(
        session["workout_type"] in {"hm_105_specific_speed", "hm_110_support_speed"}
        for week in week_plans
        for session in _actual_hmp_sessions(week)
    )
    if not has_speed_hmp or any(keyword in plan_text for keyword in SPEED_CALIBRATION_KEYWORDS):
        return []

    return [_issue(
        severity="warning",
        constraint_id="dynamic_hmp_calibration",
        message="计划包含 105-110% HMP 速度课，但未看到基于当前 5K/8K/10K 能力的校准说明。",
        recommendation="105-110% HMP 应按当前短距离能力动态校准，耐力型跑者尤其不宜机械使用名义 110% HMP。",
    )]


def _validate_environment_or_fatigue_downgrade(week_plans: List[Dict[str, Any]]) -> List[HMPlanValidationIssue]:
    issues: List[HMPlanValidationIssue] = []
    for week in week_plans:
        week_index = _week_index(week)
        for session in _actual_hmp_sessions(week):
            if session["workout_type"] not in HMP_HARD_WORKOUT_IDS:
                continue
            text = session["text"]
            has_risk_context = any(keyword in text for keyword in ENVIRONMENT_OR_FATIGUE_KEYWORDS)
            has_downgrade = any(keyword in text for keyword in DOWNGRADE_KEYWORDS)
            if has_risk_context and not has_downgrade:
                issues.append(_issue(
                    severity="warning",
                    constraint_id="environment_or_fatigue_downgrade",
                    week_index=week_index,
                    day=session["day"],
                    workout_type=session["workout_type"],
                    message=f"第 {week_index} 周 {session['day']} 的半马专项课伴随环境/疲劳/伤痛风险描述，但未看到降级或替代安排。",
                    recommendation="高温、强风、疼痛或明显疲劳时，应改用体感控制、缩短主课、延后关键课或改恢复跑。",
                ))
    return issues


def _actual_hmp_sessions(week: Dict[str, Any]) -> List[Dict[str, str]]:
    sessions: List[Dict[str, str]] = []
    for day in week.get("days") or []:
        if not isinstance(day, dict):
            continue
        text = " ".join(str(day.get(key) or "") for key in ("training_type", "main_set", "notes"))
        workout_type, label = _classify_hmp_workout(text)
        if workout_type:
            sessions.append({
                "day": str(day.get("day") or ""),
                "text": text,
                "workout_type": workout_type,
                "label": label,
            })
    return sessions


def _capacity_budget_by_week(protocol: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    budgets: Dict[int, Dict[str, Any]] = {}
    for item in protocol.get("weekly_decisions") or []:
        if not isinstance(item, dict):
            continue
        budget = item.get("capacity_budget")
        if not isinstance(budget, dict):
            continue
        week_index = _safe_int(item.get("week_index"))
        if week_index is not None:
            budgets[week_index] = budget
    return budgets


def _capacity_budget_key(workout_type: str) -> str:
    if workout_type == "hm_95_long_fast_run":
        return "hmp_95_max_km"
    if workout_type == "hm_100_float_intervals":
        return "hmp_100_total_max_km"
    if workout_type == "hm_105_specific_speed":
        return "hmp_105_total_max_km"
    if workout_type == "hm_110_support_speed":
        return "hmp_110_total_max_km"
    return ""


def _hmp_workout_volume_km(text: str, workout_type: str) -> Optional[float]:
    normalized = str(text or "")
    explicit = re.search(r"(?:累计|累积)HMP(?:约|大约)?\s*(\d+(?:\.\d+)?)\s*(?:km|公里)", normalized, flags=re.IGNORECASE)
    if explicit:
        return float(explicit.group(1))

    products: List[float] = []
    for reps, distance in re.findall(r"(\d+)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(?:km|公里)", normalized, flags=re.IGNORECASE):
        products.append(float(reps) * float(distance))
    for reps, meters in re.findall(r"(\d+)\s*[x×]\s*(\d{3,4})\s*m", normalized, flags=re.IGNORECASE):
        products.append(float(reps) * float(meters) / 1000.0)
    for distance, reps in re.findall(r"(\d+(?:\.\d+)?)\s*(?:km|公里).*?[x×]\s*(\d+)", normalized, flags=re.IGNORECASE):
        products.append(float(distance) * float(reps))
    if products:
        return max(products)

    if workout_type in {"hm_95_long_fast_run", "hm_100_float_intervals", "hm_105_specific_speed"}:
        return _max_distance_km(normalized)
    return None


def _classify_hmp_workout(text: str) -> Tuple[str, str]:
    normalized = str(text or "")
    if "hm_90_support_endurance" in normalized:
        return "hm_90_support_endurance", "90% HMP 辅助耐力课"
    if "hm_95_long_fast_run" in normalized:
        return "hm_95_long_fast_run", "95% HMP 长距离快速跑"
    if "hm_100_float_intervals" in normalized:
        return "hm_100_float_intervals", "100% HMP 核心专项课"
    if "hm_105_specific_speed" in normalized:
        return "hm_105_specific_speed", "105% HMP 专项速度课"
    if "hm_110_support_speed" in normalized:
        return "hm_110_support_speed", "107-110% HMP 辅助速度课"
    if "100% HMP" in normalized or "100%HMP" in normalized or "巡航恢复" in normalized:
        return "hm_100_float_intervals", "100% HMP 核心专项课"
    if "95% HMP" in normalized or "95%HMP" in normalized or "长距离快速跑" in normalized:
        return "hm_95_long_fast_run", "95% HMP 长距离快速跑"
    if "105% HMP" in normalized or "105%HMP" in normalized:
        return "hm_105_specific_speed", "105% HMP 专项速度课"
    if "107-110% HMP" in normalized or "110% HMP" in normalized or "110%HMP" in normalized:
        return "hm_110_support_speed", "107-110% HMP 辅助速度课"
    if "90% HMP" in normalized or "90%HMP" in normalized:
        return "hm_90_support_endurance", "90% HMP 辅助耐力课"
    return "", ""


def _issue(
    severity: str,
    constraint_id: str,
    message: str,
    recommendation: str,
    week_index: Optional[int] = None,
    day: str = "",
    workout_type: str = "",
) -> HMPlanValidationIssue:
    constraint = HM_SAFETY_CONSTRAINTS.get(constraint_id)
    term_ids = _dedupe([
        *term_ids_for_constraint(constraint_id),
        *term_ids_for_workout(workout_type),
    ])
    return HMPlanValidationIssue(
        severity=severity,
        constraint_id=constraint_id,
        label=constraint.label if constraint else constraint_id,
        message=message,
        recommendation=recommendation,
        week_index=week_index,
        day=day,
        workout_type=workout_type,
        evidence_basis=evidence_basis_for_constraint(constraint_id, workout_type),
        term_ids=term_ids,
    )


def _dedupe(values: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _week_index(week: Dict[str, Any]) -> int:
    try:
        return int(week.get("week_index") or 0)
    except (TypeError, ValueError):
        return 0


def _week_text(week: Dict[str, Any]) -> str:
    parts = [
        week.get("phase"),
        week.get("week_goal"),
        *(week.get("key_workouts") or []),
        *(week.get("action_suggestions") or []),
    ]
    for day in week.get("days") or []:
        if isinstance(day, dict):
            parts.extend(day.get(key) for key in ("training_type", "main_set", "notes"))
    return " ".join(str(part or "") for part in parts)


def _week_volume_km(week: Dict[str, Any]) -> Optional[float]:
    signature = week.get("repeat_guard_signature") or {}
    if isinstance(signature, dict):
        volume = _safe_float(signature.get("weekly_volume_km"))
        if volume is not None:
            return volume

    total = 0.0
    has_distance = False
    for day in week.get("days") or []:
        if not isinstance(day, dict):
            continue
        day_total = sum(_safe_float(day.get(key)) or 0.0 for key in ("warmup_km", "main_km", "cooldown_km"))
        if day_total > 0:
            has_distance = True
            total += day_total
    return total if has_distance else None


def _max_distance_km(text: str) -> Optional[float]:
    distances = _distance_values_km(text)
    return max(distances) if distances else None


def _max_repetition_km(text: str) -> float:
    distances = _distance_values_km(text)
    if not distances:
        return 0.0
    return max(value for value in distances if value <= 6.0) if any(value <= 6.0 for value in distances) else max(distances)


def _distance_values_km(text: str) -> List[float]:
    values: List[float] = []
    for raw in re.findall(r"(\d+(?:\.\d+)?)\s*(?:km|公里)", str(text or ""), flags=re.IGNORECASE):
        values.append(float(raw))
    for raw in re.findall(r"(\d+(?:\.\d+)?)\s*英里", str(text or "")):
        values.append(float(raw) * 1.60934)
    return values


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "HMPlanValidationIssue",
    "validate_half_marathon_protocol_plan",
]
