from __future__ import annotations

from datetime import date, timedelta
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from marathon_qa_assistant.core.periodization import (
    BlockParams,
    Macrocycle,
    Mesocycle,
    compute_week_volume_factor,
    resolve_4week_blocks,
)
from marathon_qa_assistant.core.half_marathon_protocol import (
    HM_PHASE_RULES,
    RunnerArchetypeInput,
    recommend_archetypes,
    select_phase_sequence,
    workout_rules_for_archetype,
)
from marathon_qa_assistant.core.half_marathon_pace_calibration import (
    build_half_marathon_pace_calibration,
    detect_half_marathon_profile_gaps,
)
from marathon_qa_assistant.core.half_marathon_capacity_budget import build_half_marathon_capacity_budget
from marathon_qa_assistant.core.half_marathon_validator import validate_half_marathon_protocol_plan
from marathon_qa_assistant.core.half_marathon_repair_executor import apply_half_marathon_repairs
from marathon_qa_assistant.core.half_marathon_schedule_composer import (
    build_hmp_repair_suggestions,
    compose_hmp_week_sessions,
)
from marathon_qa_assistant.core.training_plan_context import align_plan_duration_context
from marathon_qa_assistant.core.training_plan_models import (
    DayPlan,
    PhaseBlock,
    PlanMeta,
    StructuredTrainingPlan,
    WEEKDAY_ORDER,
    WeekPlan,
    ensure_repeat_guard_signature,
)
from marathon_qa_assistant.services.workout_template_retriever import (
    WORKOUT_TEMPLATE_REGISTRY,
    normalize_workout_type_for_template,
)

DEFAULT_AVAILABLE_DAYS = ["周二", "周四", "周日"]
CHINESE_COUNT_MAP = {
    "一": 1,
    "1": 1,
    "二": 2,
    "两": 2,
    "2": 2,
    "三": 3,
    "3": 3,
    "四": 4,
    "4": 4,
    "五": 5,
    "5": 5,
    "六": 6,
    "6": 6,
    "七": 7,
    "7": 7,
}
WORKOUT_MAIN_SET_HINTS = {
    "aerobic_threshold": "有氧阈值主课",
    "tempo_run": "25分钟阈值节奏跑",
    "vo2max_interval": "5×3分钟摄氧量间歇，组间慢跑3分钟",
    "interval_run": "5×800m间歇，组间慢跑200m",
    "anaerobic_threshold": "3×1600m巡航间歇，组间慢跑400m",
    "marathon_pace": "2×15分钟马拉松配速跑，组间轻松跑5分钟",
    "progression_run": "50分钟渐进跑，从轻松配速渐进到稳态配速",
    "fartlek": "40分钟法特莱克自由变速",
    "hill_repeats": "8×200m坡道跑，慢跑下坡恢复",
    "strides": "6×100m短冲，组间慢跑100m",
    "long_run": "90分钟稳定有氧长距离",
    "easy_run": "40分钟轻松跑",
}
WORKOUT_NOTES = {
    "aerobic_threshold": "来自用户个性化周结构要求，安排有氧阈刺激。",
    "tempo_run": "来自用户个性化周结构要求，安排节奏跑刺激。",
    "vo2max_interval": "来自用户个性化周结构要求，安排摄氧量训练刺激。",
    "interval_run": "来自用户个性化周结构要求，安排间歇训练刺激。",
    "anaerobic_threshold": "来自用户个性化周结构要求，安排无氧阈训练刺激。",
    "marathon_pace": "来自用户个性化周结构要求，安排马拉松专项配速刺激。",
    "progression_run": "来自用户个性化周结构要求，安排渐进跑刺激。",
    "fartlek": "来自用户个性化周结构要求，安排法特莱克刺激。",
    "hill_repeats": "来自用户个性化周结构要求，安排坡道训练刺激。",
    "strides": "来自用户个性化周结构要求，安排短冲刺激。",
    "long_run": "来自用户个性化周结构要求，安排长距离训练。",
    "easy_run": "来自用户个性化周结构要求，安排轻松跑。",
}
QUALITY_WORKOUT_TYPES = {
    "aerobic_threshold",
    "tempo_run",
    "vo2max_interval",
    "interval_run",
    "anaerobic_threshold",
    "marathon_pace",
    "progression_run",
    "fartlek",
    "hill_repeats",
    "strides",
}

TRAINING_DISTANCE_FRACTIONS = {
    "间歇跑": (0.06, 0.14),
    "无氧阈跑": (0.10, 0.18),
    "节奏跑": (0.10, 0.20),
    "有氧阈值训练": (0.14, 0.24),
    "摄氧量训练": (0.08, 0.16),
    "马拉松配速跑": (0.14, 0.26),
    "渐进跑": (0.13, 0.22),
    "法特莱克": (0.10, 0.20),
    "坡道训练": (0.06, 0.12),
    "短冲": (0.02, 0.06),
    "长距离": (0.22, 0.35),
    "轻松跑": (0.10, 0.18),
    "恢复跑": (0.06, 0.12),
}

FIXED_WARMUP_COOLDOWN = {
    "quality": (3.0, 1.5),
    "long_run": (2.0, 1.5),
    "easy": (1.5, 1.5),
    "recovery": (1.5, 1.5),
    "rest": (0.0, 0.0),
}


def _parse_pace_seconds(pace: Any) -> int:
    text = str(pace or "").strip().lower()
    match = re.search(r"(\d+)[:：](\d+)", text)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))
    match = re.search(r"(\d+)\s*分\s*(\d+)", text)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))
    return 270


def _format_pace(seconds: int) -> str:
    bounded = max(180, min(int(seconds), 480))
    return f"{bounded // 60}:{bounded % 60:02d}"


def _format_pace_range(left_seconds: int, right_seconds: int) -> str:
    return f"{_format_pace(left_seconds)}-{_format_pace(right_seconds)}"


def _normalize_available_days(raw: Any) -> List[str]:
    if isinstance(raw, Sequence) and not isinstance(raw, str):
        values = [str(item).strip() for item in raw if str(item).strip()]
    else:
        text = str(raw or "").strip()
        values = [item.strip() for item in re.split(r"[，,、/\s]+", text) if item.strip()]

    normalized: List[str] = []
    for weekday in WEEKDAY_ORDER:
        if weekday in values and weekday not in normalized:
            normalized.append(weekday)
    return normalized or DEFAULT_AVAILABLE_DAYS.copy()


def _split_weekly_structure_segments(text: str) -> List[str]:
    normalized = re.sub(r"[。；;，,、]+", "，", str(text or "").strip())
    normalized = re.sub(r"(周[一二三四五六日])", r"，\1", normalized)
    normalized = re.sub(r"(?<!不)(安排|想要|我想要|本周)", r"，\1", normalized)
    normalized = re.sub(r"^，", "", normalized)
    return [item.strip(" ，") for item in normalized.split("，") if item.strip(" ，")]


def _find_day_for_alias(segment: str, alias: str) -> Optional[str]:
    match = re.search(rf"(周[一二三四五六日])[^，,、。；;]{{0,8}}{re.escape(alias)}", segment)
    return match.group(1) if match else None


def _find_count_for_alias(segment: str, alias: str) -> Tuple[int, str]:
    count_segment = re.sub(r"^(这周|本周)", "", str(segment or "").strip())
    count_patterns = [
        rf"(?<!周)([一二两三四五六七1-7])\s*(?:节|次|个)\s*{re.escape(alias)}",
        rf"(?<!周)([一二两三四五六七1-7])\s*(?:节|次|个)\s*[^，,、。；;]{{0,8}}{re.escape(alias)}",
        rf"(?<!周)([一二两三四五六七1-7])\s*(?:节|次|个)\s*(?:{re.escape(alias)}|轻松|恢复|节奏|摄氧量|长距离|有氧阈|无氧阈|马拉松配速|渐进)",
    ]
    for pattern in count_patterns:
        match = re.search(pattern, count_segment)
        if match:
            return int(CHINESE_COUNT_MAP.get(match.group(1), 1)), match.group(0)
    return 1, alias


def _parse_weekly_structure_constraints(query: str) -> Dict[str, Any]:
    text = str(query or "").strip()
    constraints = {
        "scope": "this_week" if "这周" in text or "本周" in text else "plan",
        "required_workouts": [],
        "forbidden_workouts": [],
        "required_rest_days": [],
        "weekly_frequency": None,
        "notes": [],
    }
    if not text:
        return constraints

    segments = _split_weekly_structure_segments(text)
    seen_requirements = set()
    for workout_type, entry in WORKOUT_TEMPLATE_REGISTRY.items():
        aliases = [str(item or "").strip() for item in entry.get("aliases", []) if str(item or "").strip()]
        aliases.sort(key=len, reverse=True)
        for alias in aliases:
            for segment in segments:
                if alias not in segment:
                    continue
                if f"不要{alias}" in segment or f"不安排{alias}" in segment or f"避免{alias}" in segment:
                    if workout_type not in constraints["forbidden_workouts"]:
                        constraints["forbidden_workouts"].append(workout_type)
                    continue
                day = _find_day_for_alias(segment, alias)
                count, count_source = _find_count_for_alias(segment, alias)
                source_text = segment if day else count_source
                key = (workout_type, day or "", source_text)
                if key in seen_requirements:
                    continue
                seen_requirements.add(key)
                constraints["required_workouts"].append(
                    {
                        "workout_type": workout_type,
                        "display_name": str(entry.get("display_name") or workout_type),
                        "count": int(count),
                        "day": day,
                        "required": True,
                        "source_text": source_text,
                    }
                )
                break
            else:
                continue
            break

    rest_days = []
    for day in WEEKDAY_ORDER:
        if f"{day}休息" in text or f"{day}必须休息" in text:
            rest_days.append(day)
    constraints["required_rest_days"] = rest_days

    frequency_match = re.search(r"(?:跑|训练)\s*([一二两三四五六七1-7])\s*(?:天|次)", text)
    if frequency_match:
        constraints["weekly_frequency"] = CHINESE_COUNT_MAP.get(frequency_match.group(1))

    quality_count = sum(
        int(item.get("count") or 0)
        for item in constraints["required_workouts"]
        if item.get("workout_type") in QUALITY_WORKOUT_TYPES
    )
    if quality_count >= 3:
        constraints["notes"].append("用户指定的质量课达到3节，生成计划时需要保留恢复日并避免连续高强度。")
    return constraints


def _build_personalized_day(requirement: Dict[str, Any], fallback_day: str) -> DayPlan:
    workout_type = str(requirement.get("workout_type") or "").strip()
    entry = WORKOUT_TEMPLATE_REGISTRY.get(workout_type, {})
    day = str(requirement.get("day") or fallback_day).strip() or fallback_day
    training_type = str(entry.get("display_name") or requirement.get("display_name") or workout_type)
    venue = "田径场/平路" if workout_type in QUALITY_WORKOUT_TYPES else "公路/绿道"
    if workout_type == "easy_run":
        venue = "公园/绿道"
    return DayPlan(
        day=day,
        training_type=training_type,
        warmup="慢跑15分钟 + 动态拉伸" if workout_type in QUALITY_WORKOUT_TYPES else "慢跑10分钟 + 动态拉伸",
        main_set=WORKOUT_MAIN_SET_HINTS.get(workout_type, f"{training_type}主课"),
        cooldown="慢跑10分钟 + 静态拉伸",
        venue=venue,
        notes=WORKOUT_NOTES.get(workout_type, "来自用户个性化周结构要求。"),
    )


def _apply_weekly_structure_constraints(days: List[DayPlan], constraints: Dict[str, Any], available_days: List[str]) -> List[DayPlan]:
    requirements = [item for item in constraints.get("required_workouts", []) if isinstance(item, dict)]
    if not requirements and not constraints.get("required_rest_days"):
        return days

    updated = {day.day: day for day in days}
    preferred_days = [day for day in available_days if day in WEEKDAY_ORDER] or DEFAULT_AVAILABLE_DAYS.copy()
    used_days = {day.day for day in days if day.training_type == "休息" and day.day not in preferred_days}
    for requirement in requirements:
        count = max(1, int(requirement.get("count") or 1))
        for index in range(count):
            target_day = requirement.get("day") if index == 0 else None
            if target_day and target_day in used_days:
                target_day = None
            if not target_day:
                target_day = next(
                    (
                        item
                        for item in preferred_days
                        if item not in used_days and item not in (constraints.get("required_rest_days") or [])
                    ),
                    None,
                )
            if not target_day:
                target_day = next(
                    (item for item in WEEKDAY_ORDER if item not in used_days and item not in (constraints.get("required_rest_days") or [])),
                    WEEKDAY_ORDER[0],
                )
            used_days.add(str(target_day))
            personalized = dict(requirement)
            personalized["day"] = target_day
            updated[str(target_day)] = _build_personalized_day(personalized, str(target_day))

    for rest_day in constraints.get("required_rest_days") or []:
        if rest_day not in WEEKDAY_ORDER:
            continue
        updated[rest_day] = DayPlan(
            day=rest_day,
            training_type="休息",
            warmup="无",
            main_set="休息 + 灵活性训练15分钟",
            cooldown="无",
            venue="居家",
            notes="来自用户个性化周结构要求，保留休息日。",
        )
    updated_days = [updated.get(day, next(item for item in days if item.day == day)) for day in WEEKDAY_ORDER]
    return updated_days


def _validate_weekly_structure_constraints(
    structured_plan: Dict[str, Any],
    constraints: Dict[str, Any],
) -> Dict[str, Any]:
    requirements = [item for item in constraints.get("required_workouts", []) if isinstance(item, dict)]
    forbidden = [str(item) for item in constraints.get("forbidden_workouts", []) if str(item).strip()]
    if not requirements and not forbidden and not constraints.get("required_rest_days") and not constraints.get("weekly_frequency"):
        return {}

    week = next((item for item in structured_plan.get("week_plans", []) or [] if isinstance(item, dict)), {})
    days = [item for item in week.get("days", []) or [] if isinstance(item, dict)]
    actual_by_type: Dict[str, List[str]] = {}
    for day in days:
        workout_type = normalize_workout_type_for_template(str(day.get("training_type") or ""), str(day.get("main_set") or ""))
        if not workout_type:
            continue
        actual_by_type.setdefault(workout_type, []).append(str(day.get("day") or ""))

    matched = []
    violations = []
    for requirement in requirements:
        workout_type = str(requirement.get("workout_type") or "").strip()
        required_count = int(requirement.get("count") or 1)
        matched_days = actual_by_type.get(workout_type, [])
        if requirement.get("day"):
            matched_days = [day for day in matched_days if day == requirement.get("day")]
        item = {
            "workout_type": workout_type,
            "display_name": str(requirement.get("display_name") or workout_type),
            "required_count": required_count,
            "actual_count": len(matched_days),
            "matched_days": matched_days,
            "required_day": requirement.get("day"),
        }
        if len(matched_days) >= required_count:
            matched.append(item)
        else:
            violation = dict(item)
            violation["reason"] = f"用户要求 {required_count} 节，当前安排 {len(matched_days)} 节"
            violations.append(violation)

    for workout_type in forbidden:
        matched_days = actual_by_type.get(workout_type, [])
        if matched_days:
            entry = WORKOUT_TEMPLATE_REGISTRY.get(workout_type, {})
            violations.append(
                {
                    "workout_type": workout_type,
                    "display_name": str(entry.get("display_name") or workout_type),
                    "required_count": 0,
                    "actual_count": len(matched_days),
                    "matched_days": matched_days,
                    "reason": "用户要求本周不安排该训练类型",
                }
            )

    warnings = list(constraints.get("notes") or [])
    status = "satisfied" if not violations else ("partially_satisfied" if matched else "unsatisfied")
    return {
        "status": status,
        "matched_requirements": matched,
        "violations": violations,
        "warnings": warnings,
    }


def _resolve_macrocycle(profile: Dict[str, Any], total_weeks: int) -> Macrocycle:
    macrocycle = Macrocycle.from_profile(profile)
    if macrocycle is not None and macrocycle.total_weeks == total_weeks:
        return macrocycle
    return Macrocycle.from_race_date(
        race_date=date.today() + timedelta(weeks=max(1, total_weeks)),
        total_weeks=total_weeks,
        profile=profile,
    )


def _phase_to_load_level(phase_name: str, week_in_phase: int, phase_weeks: int) -> str:
    phase_name = str(phase_name or "")
    if "减量" in phase_name or "调整" in phase_name:
        return "taper"
    if "巅峰" in phase_name:
        return "high"
    if "建设" in phase_name and phase_weeks >= 3 and week_in_phase == phase_weeks:
        return "high"
    if "基础" in phase_name and phase_weeks >= 3 and week_in_phase == phase_weeks:
        return "medium"
    return "medium" if week_in_phase > 1 else "low"


def _is_half_year_plan(total_weeks: int) -> bool:
    return int(total_weeks or 0) >= 20


def _phase_family(phase_name: str) -> str:
    text = str(phase_name or "")
    if "基础期-1" in text:
        return "base_1"
    if "基础期-2" in text:
        return "base_2"
    if "建设期-1" in text:
        return "build_1"
    if "建设期-2" in text:
        return "build_2"
    if "巅峰" in text:
        return "peak"
    if "减量" in text or "调整" in text:
        return "taper"
    if "基础" in text:
        return "base"
    return "build"


def _resolve_training_slots(available_days: List[str]) -> Tuple[str, Optional[str], str]:
    ordered = available_days or DEFAULT_AVAILABLE_DAYS.copy()
    long_run_day = ordered[-1]
    quality_days = [day for day in ordered if day != long_run_day]
    primary_quality_day = quality_days[0] if quality_days else ("周二" if long_run_day != "周二" else "周三")
    secondary_quality_day = quality_days[1] if len(quality_days) > 1 else None
    return primary_quality_day, secondary_quality_day, long_run_day


def _resolve_goal_race_type(goal: Any) -> str:
    text = str(goal or "").lower()
    if "半马" in text or "半程" in text or "half" in text or "21k" in text or "21.1" in text:
        return "half_marathon"
    if "全马" in text or "全程" in text or "马拉松" in text or "marathon" in text or "42k" in text or "42.2" in text:
        return "marathon"
    return "general"


def _goal_strategy_label(race_type: str) -> str:
    if race_type == "half_marathon":
        return "半马目标：首周以阈值节奏和专项配速感为主，长距离控制在中等时长。"
    if race_type == "marathon":
        return "全马目标：首周以有氧耐力和渐进长距离为主，质量课避免过早堆高强度。"
    return "通用目标：首周以建立稳定训练节奏为主。"


def _profile_text(profile: Dict[str, Any], *keys: str) -> str:
    return " ".join(str(profile.get(key) or "") for key in keys)


def _profile_flag(profile: Dict[str, Any], *keys: str) -> bool:
    for key in keys:
        value = profile.get(key)
        if isinstance(value, bool):
            if value:
                return True
            continue
        if isinstance(value, (int, float)) and value:
            return True
        text = str(value or "").strip().lower()
        if text in {"true", "yes", "y", "1", "是", "有", "刚比完", "刚完成"}:
            return True
    return False


def _build_hm_archetype_input(profile: Dict[str, Any], total_weeks: int) -> RunnerArchetypeInput:
    background = _profile_text(
        profile,
        "training_background",
        "background",
        "running_background",
        "race_history",
        "recent_race",
        "strengths",
        "weaknesses",
    ).lower()
    recent_text = _profile_text(profile, "recent_race", "last_race", "race_history")
    strengths = _profile_text(profile, "strengths", "advantage", "runner_strength").lower()
    weaknesses = _profile_text(profile, "weaknesses", "limitation", "runner_weakness").lower()

    recent_marathon = (
        _profile_flag(profile, "recent_marathon", "just_ran_marathon", "recent_full_marathon")
        or ("全马" in recent_text and any(token in recent_text for token in ("刚", "最近", "完成", "赛后")))
        or ("marathon" in recent_text.lower() and any(token in recent_text.lower() for token in ("recent", "just", "last")))
    )
    endurance_background = any(token in background for token in ("越野", "超马", "ultra", "trail"))
    marathon_background = any(token in background for token in ("全马", "马拉松", "marathon"))
    long_training_gap = (
        _profile_flag(profile, "long_training_gap", "training_gap", "detrained")
        or any(token in background for token in ("久疏", "停训", "中断", "无系统训练", "gap", "detrained"))
    )
    middle_distance_background = any(token in background for token in ("1500", "3000", "5000", "5k", "中距离"))
    speed_strength = (
        _profile_flag(profile, "speed_strength", "speed_based")
        or any(token in strengths for token in ("速度", "短距离", "5k", "1500", "speed"))
    )
    half_marathon_experience_low = (
        _profile_flag(profile, "half_marathon_experience_low", "first_half_marathon")
        or any(token in weaknesses for token in ("半马经验少", "耐力不足", "长距离不足"))
    )
    injury_or_fatigue = (
        _profile_flag(profile, "injury_or_fatigue", "injury", "fatigue")
        or any(token in background for token in ("伤", "疲劳", "酸痛", "injury", "fatigue"))
    )

    return RunnerArchetypeInput(
        recent_marathon=recent_marathon,
        build_weeks=total_weeks,
        endurance_background=endurance_background,
        marathon_background=marathon_background,
        long_training_gap=long_training_gap,
        middle_distance_background=middle_distance_background,
        speed_strength=speed_strength,
        half_marathon_experience_low=half_marathon_experience_low,
        weekly_mileage_km=float(profile.get("weekly_mileage") or 0) or None,
        injury_or_fatigue=injury_or_fatigue,
    )


def _build_hm_protocol_context(profile: Dict[str, Any], total_weeks: int, race_type: str) -> Dict[str, Any]:
    if race_type != "half_marathon":
        return {"active": False}
    archetype_input = _build_hm_archetype_input(profile, total_weeks)
    decisions = recommend_archetypes(archetype_input)
    primary = decisions[0]
    preferred_rules = workout_rules_for_archetype(primary.archetype_id)
    profile_gaps = detect_half_marathon_profile_gaps(profile)
    pace_calibration = build_half_marathon_pace_calibration(profile)
    return {
        "active": True,
        "recent_marathon": archetype_input.recent_marathon,
        "input_weekly_mileage_km": archetype_input.weekly_mileage_km,
        "profile_gaps": profile_gaps,
        "pace_calibration": pace_calibration,
        "selected_archetype": primary.to_dict(),
        "archetype_candidates": [decision.to_dict() for decision in decisions],
        "phase_sequence": select_phase_sequence(total_weeks, recent_marathon=archetype_input.recent_marathon),
        "preferred_workouts": [rule.to_dict() for rule in preferred_rules],
    }


def _hm_protocol_phase_id(
    mesocycle: Mesocycle,
    week_index: int,
    total_weeks: int,
    hm_protocol_context: Optional[Dict[str, Any]],
) -> Optional[str]:
    if not hm_protocol_context or not hm_protocol_context.get("active"):
        return None
    phase_family = _phase_family(mesocycle.name)
    week_in_phase = week_index - mesocycle.start_week + 1
    if hm_protocol_context.get("recent_marathon") and mesocycle.start_week == 1 and week_in_phase <= min(2, mesocycle.weeks):
        return "introductory"
    if phase_family in {"base", "base_1", "base_2"}:
        return "general"
    if phase_family in {"build", "build_1", "build_2"}:
        return "race_supportive"
    if phase_family in {"peak", "taper"}:
        return "race_specific"
    sequence = hm_protocol_context.get("phase_sequence") or []
    return sequence[-1] if sequence else None


def _hm_protocol_workout_candidates(
    hm_protocol_context: Optional[Dict[str, Any]],
    phase_id: Optional[str],
) -> List[Dict[str, Any]]:
    if not hm_protocol_context or not hm_protocol_context.get("active") or not phase_id:
        return []
    phase_rule = HM_PHASE_RULES.get(phase_id)
    preferred = list(hm_protocol_context.get("preferred_workouts") or [])
    if not phase_rule:
        return preferred[:2]
    phase_zones = set(phase_rule.preferred_zones)
    matched = [
        workout
        for workout in preferred
        if str(workout.get("primary_zone") or "") in phase_zones
    ]
    return (matched or preferred)[:2]


def _hm_protocol_week_note(
    mesocycle: Mesocycle,
    week_index: int,
    total_weeks: int,
    hm_protocol_context: Optional[Dict[str, Any]],
) -> str:
    phase_id = _hm_protocol_phase_id(mesocycle, week_index, total_weeks, hm_protocol_context)
    if not phase_id:
        return ""
    phase_rule = HM_PHASE_RULES.get(phase_id)
    selected = (hm_protocol_context or {}).get("selected_archetype") or {}
    candidates = _hm_protocol_workout_candidates(hm_protocol_context, phase_id)
    candidate_labels = "、".join(str(item.get("label") or item.get("id")) for item in candidates)
    parts = [
        f"HMP协议：{phase_rule.label if phase_rule else phase_id}",
        f"画像={selected.get('label')}",
    ]
    if candidate_labels:
        parts.append(f"候选课表={candidate_labels}")
    return "；".join(part for part in parts if part)


def _build_phase_objective_with_hm_protocol(
    mesocycle: Mesocycle,
    base_objective: str,
    total_weeks: int,
    hm_protocol_context: Optional[Dict[str, Any]],
) -> str:
    phase_id = _hm_protocol_phase_id(mesocycle, mesocycle.start_week, total_weeks, hm_protocol_context)
    if not phase_id:
        return base_objective
    phase_rule = HM_PHASE_RULES.get(phase_id)
    if not phase_rule:
        return base_objective
    return f"{base_objective}；HMP协议阶段目标：{phase_rule.objective}"


def _build_quality_session(
    mesocycle: Mesocycle,
    week_index: int,
    threshold_pace_seconds: int,
    race_type: str = "general",
    total_weeks: int = 0,
) -> Tuple[str, str, str]:
    phase_name = mesocycle.name
    phase_family = _phase_family(phase_name)
    week_in_phase = week_index - mesocycle.start_week + 1
    long_plan = _is_half_year_plan(total_weeks)
    interval_pace = _format_pace(threshold_pace_seconds - 12 - (week_index % 3) * 2)
    threshold_pace = _format_pace(threshold_pace_seconds)
    slower_threshold_pace = _format_pace(threshold_pace_seconds + 5)
    marathon_pace = _format_pace(threshold_pace_seconds + 18)

    if long_plan and race_type == "half_marathon" and phase_family != "taper":
        options_by_phase = {
            "base_1": [
                ("有氧阈值训练", f"3×2000m，配速{slower_threshold_pace}/km，组间慢跑400m", "半年级半马计划前段以有氧阈和动作稳定性打底。"),
                ("节奏跑", f"20分钟，配速{threshold_pace}/km", "用短节奏跑建立半马专项配速感。"),
                ("轻松跑", f"55分钟，配速{_format_pace_range(threshold_pace_seconds + 45, threshold_pace_seconds + 65)}/km", "长周期前段控制强度，优先建立训练连续性。"),
                ("短冲", f"6×100m，配速{interval_pace}/km，组间慢跑100m", "基础期轻量短冲引入速度元素，不带疲劳。"),
            ],
            "base_2": [
                ("无氧阈跑", f"3×1600m，配速{slower_threshold_pace}/km，组间慢跑400m", "在有氧基础上加入巡航间歇，提升阈值耐受。"),
                ("渐进跑", f"45分钟，从{_format_pace(threshold_pace_seconds + 45)}/km渐进至{threshold_pace}/km", "通过渐进跑连接有氧基础与专项强度。"),
                ("节奏跑", f"25分钟，配速{threshold_pace}/km", "逐步延长半马专项连续输出。"),
                ("法特莱克", f"40分钟，配速{_format_pace_range(threshold_pace_seconds + 25, threshold_pace_seconds)}/km自由变速", "以速度游戏方式在不同强度间切换，提升有氧变通能力。"),
            ],
            "build_1": [
                ("间歇跑", f"5×800m，配速{interval_pace}/km，组间慢跑200m", "建设期前段用中短间歇提升速度储备。"),
                ("无氧阈跑", f"4×1600m，配速{slower_threshold_pace}/km，组间慢跑400m", "强化半马配速附近的稳定输出。"),
                ("节奏跑", f"30分钟，配速{threshold_pace}/km", "把持续跑时间推进到专项区间。"),
                ("坡道训练", f"8×200m上坡，配速{interval_pace}/km，慢跑下坡恢复", "利用坡道同时训练力量和跑步经济性。"),
            ],
            "build_2": [
                ("摄氧量训练", f"5×3分钟，配速{interval_pace}/km，组间慢跑3分钟", "建设期后段保留摄氧量刺激但控制总量。"),
                ("无氧阈跑", f"3×2000m，配速{slower_threshold_pace}/km，组间慢跑500m", "以更长巡航间歇提升专项耐力。"),
                ("节奏跑", f"2×15分钟，配速{threshold_pace}/km，组间轻松跑5分钟", "把节奏跑拆组，减少长计划后段重复感。"),
                ("坡道训练", f"6×300m上坡，配速{slower_threshold_pace}/km，慢跑下坡恢复", "用更长坡道段强化抗疲劳能力。"),
            ],
            "peak": [
                ("节奏跑", f"35分钟，配速{threshold_pace}/km", "巅峰期强化半马专项持续输出。"),
                ("摄氧量训练", f"4×4分钟，配速{interval_pace}/km，组间慢跑3分钟", "用较短总量维持高端能力。"),
                ("无氧阈跑", f"2×3000m，配速{slower_threshold_pace}/km，组间慢跑600m", "接近比赛前用长巡航间歇巩固阈值。"),
            ],
        }
        options = options_by_phase.get(phase_family, options_by_phase["build_1"])
    elif long_plan and race_type == "marathon" and phase_family != "taper":
        options_by_phase = {
            "base_1": [
                ("轻松跑", f"60分钟，配速{_format_pace_range(threshold_pace_seconds + 50, threshold_pace_seconds + 70)}/km", "半年级全马前段优先扩展有氧容量。"),
                ("马拉松配速跑", f"2×10分钟，配速{marathon_pace}/km，组间轻松跑5分钟", "早期轻量接触全马专项配速。"),
                ("渐进跑", f"45分钟，从{_format_pace(threshold_pace_seconds + 60)}/km渐进至{_format_pace(threshold_pace_seconds + 25)}/km", "用渐进节奏提升有氧控制能力。"),
                ("短冲", f"6×100m，配速{interval_pace}/km，组间慢跑100m", "基础期末尾短冲激活神经肌肉，不带疲劳。"),
            ],
            "base_2": [
                ("马拉松配速跑", f"2×15分钟，配速{marathon_pace}/km，组间轻松跑5分钟", "巩固全马配速感。"),
                ("渐进跑", f"55分钟，从{_format_pace(threshold_pace_seconds + 55)}/km渐进至{marathon_pace}/km", "连接有氧基础与专项耐力。"),
                ("无氧阈跑", f"3×1600m，配速{slower_threshold_pace}/km，组间慢跑400m", "用较温和巡航间歇提高效率。"),
                ("法特莱克", f"50分钟，配速{_format_pace_range(threshold_pace_seconds + 25, threshold_pace_seconds)}/km自由变速", "通过速度游戏累积不同区间的有氧时间。"),
            ],
            "build_1": [
                ("马拉松配速跑", f"3×15分钟，配速{marathon_pace}/km，组间轻松跑5分钟", "建设期前段增加专项配速累计时间。"),
                ("节奏跑", f"25分钟，配速{threshold_pace}/km", "提高乳酸阈值，为全马配速留余量。"),
                ("渐进跑", f"65分钟，从{_format_pace(threshold_pace_seconds + 50)}/km渐进至{marathon_pace}/km", "强化后段稳定输出。"),
                ("坡道训练", f"8×200m上坡，配速{interval_pace}/km，慢跑下坡恢复", "利用坡道同时训练力量与跑步经济性。"),
            ],
            "build_2": [
                ("马拉松配速跑", f"2×25分钟，配速{marathon_pace}/km，组间轻松跑8分钟", "建设期后段突出全马专项耐力。"),
                ("无氧阈跑", f"4×1600m，配速{slower_threshold_pace}/km，组间慢跑400m", "保留阈值刺激但不堆叠过高强度。"),
                ("渐进跑", f"75分钟，从{_format_pace(threshold_pace_seconds + 55)}/km渐进至{marathon_pace}/km", "模拟长距离后段专项配速控制。"),
                ("坡道训练", f"6×300m上坡，配速{slower_threshold_pace}/km，慢跑下坡恢复", "用更长坡道段强化抗疲劳能力。"),
            ],
            "peak": [
                ("马拉松配速跑", f"3×20分钟，配速{marathon_pace}/km，组间轻松跑6分钟", "巅峰期模拟比赛配速节奏。"),
                ("渐进跑", f"70分钟，后30分钟配速{marathon_pace}/km", "把专项配速放在疲劳后段完成。"),
                ("节奏跑", f"30分钟，配速{threshold_pace}/km", "用较短质量课维持跑步经济性。"),
            ],
        }
        options = options_by_phase.get(phase_family, options_by_phase["build_1"])
    elif "减量" in phase_name or "调整" in phase_name:
        options = [
            ("节奏跑", f"{20 + (week_index % 2) * 5}分钟，配速{threshold_pace}/km", "保留节奏感，但总负荷下降。"),
            ("间歇跑", f"{4 + (week_index % 2)}×400m，配速{interval_pace}/km，组间慢跑200m", "以短间歇维持步频与速度感。"),
        ]
    elif "基础" in phase_name:
        options = [
            ("有氧阈值训练", f"3×2000m，配速{slower_threshold_pace}/km，组间慢跑400m", "以有氧阈值训练建立脂肪代谢基础，保持低强度高有氧刺激。"),
            ("节奏跑", f"{20 + (week_index % 3) * 5}分钟，配速{threshold_pace}/km", "以稳定阈值持续跑温和提升有氧基础。"),
            ("渐进跑", f"{40 + (week_index % 3) * 5}分钟，从{_format_pace(threshold_pace_seconds + 45)}/km渐进至{threshold_pace}/km", "通过渐进跑温和引入强度元素，不急于堆高强度。"),
            ("法特莱克", f"35分钟，配速{_format_pace_range(threshold_pace_seconds + 25, threshold_pace_seconds)}/km自由变速", "以速度游戏方式在不同强度间切换，低心理压力高有氧刺激。"),
        ]
    elif race_type == "half_marathon" and "减量" not in phase_name and "调整" not in phase_name:
        options = [
            ("无氧阈跑", f"3×1600m，配速{slower_threshold_pace}/km，组间慢跑400m", "半马目标优先建立阈值耐受和专项节奏感。"),
            ("节奏跑", f"25分钟，配速{threshold_pace}/km", "围绕半马专项配速感做连续输出。"),
            ("间歇跑", f"5×800m，配速{interval_pace}/km，组间慢跑200m", "用较短间歇保持速度储备，避免首周过量。"),
        ]
    elif race_type == "marathon" and "减量" not in phase_name and "调整" not in phase_name:
        options = [
            ("马拉松配速跑", f"2×15分钟，配速{marathon_pace}/km，组间轻松跑5分钟", "全马目标优先建立可持续专项配速感。"),
            ("渐进跑", f"50分钟，从{_format_pace(threshold_pace_seconds + 55)}/km渐进至{marathon_pace}/km", "用渐进节奏连接有氧基础与全马专项耐力。"),
            ("轻松跑", f"55分钟，配速{_format_pace_range(threshold_pace_seconds + 45, threshold_pace_seconds + 65)}/km", "首周先稳住有氧容量，不急于堆高强度。"),
        ]
    else:
        options = [
            ("间歇跑", f"{5 + (week_index % 3)}×1000m，配速{interval_pace}/km，组间慢跑200m", "围绕专项能力做主质量课。"),
            ("无氧阈跑", f"{4 + (week_index % 2)}×1600m，配速{slower_threshold_pace}/km，组间慢跑400m", "强化比赛配速附近的耐受。"),
            ("节奏跑", f"{25 + (week_index % 3) * 5}分钟，配速{threshold_pace}/km", "把持续跑时间推进到专项区间。"),
            ("法特莱克", f"45分钟，配速{_format_pace_range(threshold_pace_seconds + 25, threshold_pace_seconds)}/km自由变速", "通过速度游戏丰富训练刺激，避免同型课重复。"),
            ("坡道训练", f"8×200m上坡，配速{interval_pace}/km，慢跑下坡恢复", "利用坡道同时训练力量和跑步经济性。"),
        ]

    option_index = week_in_phase - 1 if long_plan and phase_family != "taper" else week_index - 1
    return options[option_index % len(options)]


def _build_secondary_session(
    mesocycle: Mesocycle,
    week_index: int,
    threshold_pace_seconds: int,
    allow_quality: bool,
    total_weeks: int = 0,
) -> Tuple[str, str, str]:
    phase_family = _phase_family(mesocycle.name)
    long_plan = _is_half_year_plan(total_weeks)
    easy_pace = _format_pace_range(threshold_pace_seconds + 45, threshold_pace_seconds + 65)
    threshold_pace = _format_pace(threshold_pace_seconds + 3)

    if long_plan and phase_family != "taper":
        if phase_family in {"base_1", "base_2"}:
            if week_index % 4 == 0:
                return (
                    "恢复跑",
                    f"40分钟，配速{easy_pace}/km",
                    "半年级长计划前半段把第二训练日留给恢复，减少重复感。",
                )
            if phase_family == "base_2" and week_index % 2 == 0:
                return (
                    "轻松跑",
                    f"50分钟，配速{easy_pace}/km",
                    "通过轻松跑维持周跑量，减少周内双质量课频率。",
                )
            return (
                "节奏跑",
                f"20分钟，配速{threshold_pace}/km",
                "在基础阶段后半程加入温和节奏刺激。",
            )
        if phase_family in {"build_1", "build_2"}:
            if week_index % 3 == 0:
                return (
                    "马拉松配速跑",
                    f"2×12分钟，配速{_format_pace(threshold_pace_seconds + 18)}/km，组间轻松跑5分钟",
                    "建设期的第二训练日加入专项配速，但总量控制在可恢复范围。",
                )
            if week_index % 2 == 0:
                return (
                    "节奏跑",
                    f"25分钟，配速{threshold_pace}/km",
                    "以节奏跑承接主课，避免每周都出现同型间歇。",
                )
            return (
                "轻松跑",
                f"45分钟，配速{easy_pace}/km",
                "让长计划中的中段周内结构保留恢复窗口。",
            )
        if phase_family == "peak":
            if week_index % 2 == 0:
                return (
                    "渐进跑",
                    f"50分钟，从{_format_pace(threshold_pace_seconds + 55)}/km渐进至{_format_pace(threshold_pace_seconds + 20)}/km",
                    "峰值阶段第二训练日用渐进跑增强疲劳下配速控制。",
                )
            return (
                "轻松跑",
                f"40分钟，配速{easy_pace}/km",
                "峰值阶段保留更明确的恢复窗口。",
            )

    if not allow_quality or "减量" in mesocycle.name or "调整" in mesocycle.name:
        return (
            "轻松跑",
            f"{40 + (week_index % 3) * 5}分钟，配速{easy_pace}/km",
            "用轻松跑承接主课后的恢复。",
        )

    if phase_family == "build":
        if week_index % 2 == 0:
            return (
                "节奏跑",
                f"{20 + (week_index % 2) * 5}分钟，配速{threshold_pace}/km",
                "建设期次课以节奏跑维持乳酸阈值刺激。",
            )
        return (
            "法特莱克",
            f"35分钟，配速{easy_pace}/km自由变速",
            "建设期奇数周以法特莱克丰富刺激，低心理压力。",
        )

    if week_index % 2 == 0:
        return (
            "节奏跑",
            f"{20 + (week_index % 2) * 5}分钟，配速{threshold_pace}/km",
            "作为本周第二刺激点，保持与主课不同的刺激形式。",
        )
    return (
        "轻松跑",
        f"{45 + (week_index % 2) * 5}分钟，配速{easy_pace}/km",
        "维持跑量，不再叠加额外高强度。",
    )


def _build_long_run_main_set(
    mesocycle: Mesocycle,
    week_index: int,
    base_minutes: int,
    threshold_pace_seconds: int,
    race_type: str = "general",
    total_weeks: int = 0,
) -> str:
    phase_family = _phase_family(mesocycle.name)
    long_plan = _is_half_year_plan(total_weeks)
    if long_plan:
        easy_range = _format_pace_range(threshold_pace_seconds + 35, threshold_pace_seconds + 55)
        if phase_family == "taper":
            taper_step = max(0, week_index - int(total_weeks or week_index) + 4)
            minutes = max(50, base_minutes - 26 - taper_step * 7)
            if taper_step >= 3:
                return f"{minutes}分钟减量长距离，后半程保持轻松顺畅，不再追求专项配速"
            return f"{minutes}分钟减量长距离，前半程轻松，后20分钟保持顺畅节奏"
        cap = 150 if total_weeks >= 24 else 135
        if race_type == "marathon":
            cap = 185 if total_weeks >= 24 else 170
        minutes = min(cap, base_minutes + week_index * 3)
        if "巅峰" in mesocycle.name:
            minutes = min(cap, base_minutes + 35 + (week_index % 3) * 5)
        phase_weeks = mesocycle.weeks
        week_in_phase = week_index - mesocycle.start_week + 1
        load_level = _phase_to_load_level(mesocycle.name, week_in_phase, phase_weeks)
        if load_level == "low" and week_index > 1:
            minutes = max(base_minutes + 6, minutes - 10)
            return f"{minutes}分钟恢复性长距离，配速{easy_range}/km，保留余力"
        if week_index % 5 == 0:
            return f"{minutes}分钟长距离，中段加入2×12分钟马拉松配速，组间轻松跑8分钟"
        if week_index % 4 == 0:
            return f"{minutes}分钟长距离，最后20分钟逐步加速到稳态配速"
        if week_index % 3 == 0:
            return f"{minutes}分钟长距离，前70%轻松，后30%提高到稳定有氧上沿"
        suffix = "，后段保持稳定有氧并练习补给" if race_type == "marathon" else "，最后15分钟接近半马专项舒适配速"
        return f"{minutes}分钟，配速{easy_range}/km{suffix}"

    if "减量" in mesocycle.name or "调整" in mesocycle.name:
        minutes = max(60, base_minutes - 20)
        suffix = ""
    elif race_type == "half_marathon":
        minutes = min(125, base_minutes + week_index * 2)
        suffix = "，最后15分钟接近半马专项舒适配速"
    elif race_type == "marathon":
        minutes = min(160, base_minutes + 15 + week_index * 4)
        suffix = "，后段保持稳定有氧并练习补给"
    elif "巅峰" in mesocycle.name:
        minutes = min(150, base_minutes + 15)
        suffix = ""
    else:
        minutes = min(145, base_minutes + week_index * 3)
        suffix = ""
    return f"{minutes}分钟，配速{_format_pace_range(threshold_pace_seconds + 35, threshold_pace_seconds + 55)}/km{suffix}"


def _build_weekly_volume(
    base_weekly_mileage: float,
    week_index: int,
    blocks: List[BlockParams],
) -> float:
    factor = compute_week_volume_factor(week_index, blocks)
    return round(max(18.0, base_weekly_mileage * factor), 1)


def _classify_day_label(training_type: str) -> str:
    quality_labels = {"间歇跑", "无氧阈跑", "节奏跑", "有氧阈值训练", "摄氧量训练", "马拉松配速跑", "渐进跑", "法特莱克", "坡道训练", "短冲"}
    if training_type == "长距离":
        return "long_run"
    if training_type in quality_labels:
        return "quality"
    if training_type == "恢复跑":
        return "recovery"
    if training_type == "轻松跑":
        return "easy"
    return "rest"


def _main_km_for_type(training_type: str, target_km: float, ratio: str) -> float:
    if training_type in ("休息", ""):
        return 0.0
    fraction = TRAINING_DISTANCE_FRACTIONS.get(training_type, (0.10, 0.18))
    if ratio == "lower":
        return round(target_km * fraction[0], 1)
    elif ratio == "upper":
        return round(target_km * fraction[1], 1)
    return round(target_km * (fraction[0] + fraction[1]) / 2, 1)


def _easy_km_text(km: float, pace_range: str) -> str:
    return f"{km:.1f}km，配速{pace_range}/km"


def _fixed_km_for_training_type(training_type: str, role: str) -> Tuple[float, float]:
    if role == "long_run":
        return 2.0, 1.5
    if training_type in ("轻松跑", "恢复跑", ""):
        return 1.5, 1.5
    return 3.0, 1.5


def _allocate_high_load_four_day_main_km(
    target_km: float,
    available_days: List[str],
    primary_day: str,
    primary_type: str,
    secondary_day: Optional[str],
    secondary_type: str,
    long_run_day: str,
    easy_candidates: List[str],
) -> Optional[Dict[str, float]]:
    if len(available_days) > 4 or target_km / max(1, len(available_days)) < 18.0:
        return None

    role_items: List[Tuple[str, str, str, float, float]] = []
    used_days = set()

    def add_role(day: Optional[str], role: str, training_type: str, weight: float, cap_ratio: float) -> None:
        if not day or day in used_days:
            return
        if day not in available_days:
            return
        role_items.append((day, role, training_type, weight, cap_ratio))
        used_days.add(day)

    add_role(primary_day, "primary", primary_type, 0.24, 0.28)
    add_role(secondary_day, "secondary", secondary_type, 0.24 if secondary_type not in ("轻松跑", "恢复跑", "") else 0.21, 0.28)
    for day in easy_candidates:
        add_role(day, "easy", "轻松跑", 0.19, 0.25)
    add_role(long_run_day, "long_run", "长距离", 0.33, 0.35)

    if len(role_items) < 4:
        return None

    total_weight = sum(item[3] for item in role_items)
    total_targets: Dict[str, float] = {}
    for day, _role, _training_type, weight, cap_ratio in role_items:
        total_targets[day] = min(round(target_km * weight / total_weight, 1), round(target_km * cap_ratio, 1))

    remaining = round(target_km - sum(total_targets.values()), 1)
    adjustable = [item for item in role_items if total_targets[item[0]] < round(target_km * item[4], 1)]
    while remaining > 0 and adjustable:
        changed = False
        for day, _role, _training_type, _weight, cap_ratio in adjustable:
            cap = round(target_km * cap_ratio, 1)
            room = round(cap - total_targets[day], 1)
            if room <= 0:
                continue
            inc = min(remaining, room, 1.0)
            total_targets[day] = round(total_targets[day] + inc, 1)
            remaining = round(remaining - inc, 1)
            changed = True
            if remaining <= 0:
                break
        adjustable = [item for item in adjustable if total_targets[item[0]] < round(target_km * item[4], 1)]
        if not changed:
            break

    if abs(sum(total_targets.values()) - target_km) > 0.2:
        return None

    main_targets: Dict[str, float] = {}
    for day, role, training_type, _weight, _cap_ratio in role_items:
        wu, cd = _fixed_km_for_training_type(training_type, role)
        main_targets[day] = round(max(0.0, total_targets[day] - wu - cd), 1)
    return main_targets


def _allocate_weekly_volume(
    target_km: float,
    available_days: List[str],
    primary_day: str,
    primary_type: str,
    primary_main_set: str,
    secondary_day: Optional[str],
    secondary_type: str,
    secondary_main_set: str,
    long_run_day: str,
    long_run_main_set: str,
    week_in_block: int,
    is_taper_block: bool = False,
) -> List[DayPlan]:
    available_set = set(available_days)
    if is_taper_block:
        quality_ratio = "lower"
        long_ratio = "lower"
    elif week_in_block == 1:
        quality_ratio = "lower"
    elif week_in_block == 3:
        quality_ratio = "upper"
    elif week_in_block == 4:
        quality_ratio = "lower"
    else:
        quality_ratio = "mid"

    long_ratio = "upper" if week_in_block == 3 and not is_taper_block else ("lower" if week_in_block in (1, 4) or is_taper_block else "mid")

    long_km = _main_km_for_type("长距离", target_km, long_ratio)
    primary_km = _main_km_for_type(
        primary_type, target_km, quality_ratio
    ) if primary_type not in ("休息", "轻松跑", "恢复跑", "") else 0.0
    secondary_km = _main_km_for_type(
        secondary_type, target_km, "lower"
    ) if secondary_day and secondary_type not in ("休息", "轻松跑", "恢复跑", "") else 0.0

    fixed_wu_cd = 0.0
    for day in WEEKDAY_ORDER:
        if day not in available_set and day not in (long_run_day, primary_day, secondary_day):
            continue
        if day == long_run_day:
            fixed_wu_cd += 2.0 + 1.5
        elif day == primary_day:
            if primary_type in ("轻松跑", "恢复跑", ""):
                fixed_wu_cd += 1.5 + 1.5
            else:
                fixed_wu_cd += 3.0 + 1.5
        elif day == secondary_day:
            if secondary_type in ("轻松跑", "恢复跑", ""):
                fixed_wu_cd += 1.5 + 1.5
            else:
                fixed_wu_cd += 3.0 + 1.5
        elif day in available_set:
            fixed_wu_cd += 1.5 + 1.5

    allocated_main = long_km + primary_km + secondary_km
    easy_budget = target_km - fixed_wu_cd - allocated_main

    easy_candidates = [
        d for d in WEEKDAY_ORDER
        if d in available_set
        and d not in (long_run_day, primary_day, secondary_day)
    ]

    high_load_main_km = _allocate_high_load_four_day_main_km(
        target_km=target_km,
        available_days=available_days,
        primary_day=primary_day,
        primary_type=primary_type,
        secondary_day=secondary_day,
        secondary_type=secondary_type,
        long_run_day=long_run_day,
        easy_candidates=easy_candidates,
    )
    if high_load_main_km is not None:
        long_km = high_load_main_km.get(long_run_day, long_km)
        primary_km = high_load_main_km.get(primary_day, primary_km)
        if secondary_day:
            secondary_km = high_load_main_km.get(secondary_day, secondary_km)
        easy_km_by_day = {day: high_load_main_km.get(day, 0.0) for day in easy_candidates}
    else:
        easy_km_by_day = {}

    if high_load_main_km is not None:
        easy_km_each = 0.0
    elif not easy_candidates:
        easy_km_each = 0.0
        budget_leftover = target_km - fixed_wu_cd - allocated_main
        if budget_leftover > 0 and secondary_day and secondary_type in ("轻松跑", "恢复跑"):
            secondary_km += budget_leftover
        elif budget_leftover > 0 and primary_type in ("轻松跑", "恢复跑"):
            primary_km += budget_leftover
    elif easy_budget <= 0:
        easy_km_each = 3.5
    else:
        easy_km_each = round(easy_budget / len(easy_candidates), 1)
        if easy_km_each < 3.0:
            easy_km_each = max(3.0, round(easy_budget / len(easy_candidates), 1))

    days: List[DayPlan] = []
    for day in WEEKDAY_ORDER:
        if day == long_run_day:
            wu, cd = 2.0, 1.5
            days.append(DayPlan(
                day=day, training_type="长距离",
                warmup="慢跑15分钟 + 动态拉伸",
                main_set=long_run_main_set,
                cooldown="慢跑10分钟 + 静态拉伸",
                venue="公路/绿道",
                notes="长距离跑，板块跑量约束已分配距离。",
                warmup_km=wu, main_km=long_km, cooldown_km=cd,
            ))
            continue

        if day == primary_day:
            if primary_type in ("轻松跑", "恢复跑", ""):
                wu, cd = 1.5, 1.5
            else:
                wu, cd = 3.0, 1.5
            days.append(DayPlan(
                day=day, training_type=primary_type,
                warmup="慢跑15分钟 + 动态拉伸",
                main_set=primary_main_set,
                cooldown="慢跑10分钟 + 静态拉伸",
                venue="田径场/平路",
                notes="主质量课，板块跑量约束已分配距离。",
                warmup_km=wu, main_km=primary_km, cooldown_km=cd,
            ))
            continue

        if secondary_day and day == secondary_day:
            if secondary_type in ("轻松跑", "恢复跑", ""):
                wu, cd = 1.5, 1.5
            else:
                wu, cd = 3.0, 1.5
            days.append(DayPlan(
                day=day, training_type=secondary_type,
                warmup="慢跑10分钟 + 动态拉伸",
                main_set=secondary_main_set,
                cooldown="慢跑10分钟 + 静态拉伸",
                venue="公园/绿道",
                notes="次课，板块跑量约束已分配距离。",
                warmup_km=wu, main_km=secondary_km, cooldown_km=cd,
            ))
            continue

        if day in available_set:
            wu, cd = 1.5, 1.5
            easy_main_km = easy_km_by_day.get(day, easy_km_each)
            days.append(DayPlan(
                day=day, training_type="轻松跑",
                warmup="慢跑10分钟",
                main_set=_easy_km_text(easy_main_km, "5:05-5:25"),
                cooldown="慢跑10分钟 + 拉伸",
                venue="公园",
                notes="衔接日维持跑量，强度保持轻松。",
                warmup_km=wu, main_km=easy_main_km, cooldown_km=cd,
            ))
            continue

        days.append(DayPlan(
            day=day, training_type="休息",
            warmup="无", main_set="休息 + 灵活性训练15分钟",
            cooldown="无", venue="居家",
            notes="非训练日，优先恢复与睡眠。",
            warmup_km=0.0, main_km=0.0, cooldown_km=0.0,
        ))

    return days


def _build_key_workouts(days: List[DayPlan]) -> List[str]:
    priority_keywords = ("摄氧量", "间歇", "节奏", "阈值", "无氧阈", "马拉松配速", "渐进", "长距离")
    selected: List[str] = []

    for keyword in priority_keywords:
        for day in days:
            if keyword not in day.training_type and keyword not in day.main_set:
                continue
            summary = f"{day.day} {day.training_type}：{day.main_set}"
            if summary not in selected:
                selected.append(summary)
            if len(selected) >= 3:
                return selected

    for day in days:
        if day.training_type == "休息":
            continue
        summary = f"{day.day} {day.training_type}：{day.main_set}"
        if summary not in selected:
            selected.append(summary)
        if len(selected) >= 3:
            break
    return selected


def _build_week_action_suggestions(
    week_index: int,
    mesocycle: Mesocycle,
    available_days: List[str],
    days: List[DayPlan],
) -> List[str]:
    suggestions: List[str] = []
    training_days = "、".join(available_days) if available_days else "周二、周四、周日"
    suggestions.append(f"先确认本周固定训练日为 {training_days}，避免临时打乱课表。")

    primary_quality = next(
        (
            day
            for day in days
            if day.training_type not in {"休息", "轻松跑", "长距离"}
        ),
        None,
    )
    if primary_quality is not None:
        suggestions.append(f"优先完成 {primary_quality.day} 的{primary_quality.training_type}主课：{primary_quality.main_set}。")

    long_run_day = next((day for day in days if day.training_type == "长距离"), None)
    if long_run_day is not None:
        suggestions.append(f"{long_run_day.day} 长距离前准备补给与配速方案，主训练为 {long_run_day.main_set}。")
    else:
        suggestions.append(f"围绕{mesocycle.goal}安排恢复与补给，保证本周训练连续性。")

    if week_index == 1:
        suggestions.append("首周先以完成度优先，不需要额外加量。")

    return suggestions[:3]


def _build_first_week_actions(week_plan: WeekPlan) -> List[str]:
    actions = list(week_plan.action_suggestions[:2])
    if week_plan.key_workouts:
        actions.append(f"本周重点先执行：{week_plan.key_workouts[0]}。")
    if not actions:
        actions.append("按首周训练日顺序开始执行，不需要额外补做缺省课表。")
    return actions[:3]


def _build_week_days(
    mesocycle: Mesocycle,
    week_index: int,
    profile: Dict[str, Any],
    available_days: List[str],
    blocks: List[BlockParams],
    total_weeks: int = 0,
    hm_protocol_context: Optional[Dict[str, Any]] = None,
) -> Tuple[List[DayPlan], float, Dict[str, Any]]:
    threshold_pace_seconds = _parse_pace_seconds(profile.get("t_pace"))
    race_type = _resolve_goal_race_type(profile.get("goal"))
    base_weekly_mileage = float(profile.get("weekly_mileage") or 40.0)
    max_session_minutes = int(profile.get("max_session_minutes") or 90)
    primary_quality_day, secondary_quality_day, long_run_day = _resolve_training_slots(available_days)
    week_in_phase = week_index - mesocycle.start_week + 1
    weekly_volume_km = _build_weekly_volume(base_weekly_mileage, week_index, blocks)

    primary_type, primary_main_set, primary_note = _build_quality_session(
        mesocycle, week_index, threshold_pace_seconds, race_type, total_weeks
    )
    secondary_type, secondary_main_set, secondary_note = _build_secondary_session(
        mesocycle,
        week_index,
        threshold_pace_seconds,
        mesocycle.max_high_intensity_per_week >= 2,
        total_weeks,
    )
    long_run_main_set = _build_long_run_main_set(
        mesocycle,
        week_index,
        min(120, max(80, max_session_minutes)),
        threshold_pace_seconds,
        race_type,
        total_weeks,
    )
    hmp_week_decision: Dict[str, Any] = {}
    if hm_protocol_context and hm_protocol_context.get("active") and race_type == "half_marathon":
        phase_id = _hm_protocol_phase_id(mesocycle, week_index, total_weeks, hm_protocol_context) or ""
        selected = hm_protocol_context.get("selected_archetype") or {}
        pace_calibration = hm_protocol_context.get("pace_calibration") or {}
        hmp_week_decision = compose_hmp_week_sessions(
            week_index=week_index,
            total_weeks=total_weeks,
            phase_id=phase_id,
            archetype_id=str(selected.get("archetype_id") or "general_half_marathon"),
            recent_marathon=bool(hm_protocol_context.get("recent_marathon")),
            weekly_volume_km=weekly_volume_km,
            speed_calibration_available=bool(pace_calibration.get("speed_calibration_available")),
            pace_calibration_status=str(pace_calibration.get("status") or ""),
            capacity_budget=build_half_marathon_capacity_budget(
                weekly_volume_km=weekly_volume_km,
                phase_id=phase_id or "general",
                available_days_count=len(available_days),
                recent_marathon=bool(hm_protocol_context.get("recent_marathon")),
                fatigue_or_injury=bool(profile.get("injury_or_fatigue") or profile.get("fatigue") or profile.get("injury")),
                speed_calibration_available=bool(pace_calibration.get("speed_calibration_available")),
            ),
        )
        for session in hmp_week_decision.get("sessions") or []:
            if not isinstance(session, dict):
                continue
            role = str(session.get("role") or "")
            if role == "primary" and phase_id != "general":
                primary_type = str(session.get("training_type") or primary_type)
                primary_main_set = str(session.get("main_set") or primary_main_set)
                primary_note = str(session.get("note") or primary_note)
            elif role == "secondary" and secondary_quality_day and len(available_days) >= 4:
                secondary_type = str(session.get("training_type") or secondary_type)
                secondary_main_set = str(session.get("main_set") or secondary_main_set)
                secondary_note = str(session.get("note") or secondary_note)
            elif role == "long_run" and _phase_family(mesocycle.name) != "taper":
                long_run_main_set = str(session.get("main_set") or long_run_main_set)

    week_in_block = ((week_index - 1) % 4) + 1
    current_block = next((b for b in blocks if b.start_week <= week_index <= b.end_week), None)
    is_taper_block = current_block is not None and current_block.block_coeff <= 0.65
    days = _allocate_weekly_volume(
        target_km=weekly_volume_km,
        available_days=available_days,
        primary_day=primary_quality_day,
        primary_type=primary_type,
        primary_main_set=primary_main_set,
        secondary_day=secondary_quality_day,
        secondary_type=secondary_type,
        secondary_main_set=secondary_main_set,
        long_run_day=long_run_day,
        long_run_main_set=long_run_main_set,
        week_in_block=week_in_block,
        is_taper_block=is_taper_block,
    )
    return days, weekly_volume_km, hmp_week_decision


def build_structured_training_plan_skeleton(
    query: str,
    profile: Dict[str, Any],
    requested_weeks: Optional[int] = None,
) -> Dict[str, Any]:
    plan_context = align_plan_duration_context(query, profile)
    aligned_profile = dict(plan_context["aligned_profile"])
    total_weeks = int(plan_context["resolved_plan_weeks"])
    available_days = _normalize_available_days(aligned_profile.get("available_days"))
    weekly_structure_constraints = _parse_weekly_structure_constraints(query)
    macrocycle = _resolve_macrocycle(aligned_profile, total_weeks)
    base_weekly_mileage = float(aligned_profile.get("weekly_mileage") or 40.0)
    blocks = resolve_4week_blocks(total_weeks, base_weekly_mileage)
    race_type = _resolve_goal_race_type(aligned_profile.get("goal"))
    hm_protocol_context = _build_hm_protocol_context(aligned_profile, total_weeks, race_type)

    phase_summary = [
        PhaseBlock(
            phase=mesocycle.name,
            start_week=mesocycle.start_week,
            end_week=mesocycle.end_week,
            objective=_build_phase_objective_with_hm_protocol(
                mesocycle,
                mesocycle.goal,
                total_weeks,
                hm_protocol_context,
            ),
        )
        for mesocycle in macrocycle.mesocycles
    ]

    week_plans: List[WeekPlan] = []
    hmp_week_decisions: List[Dict[str, Any]] = []
    for week_index in range(1, total_weeks + 1):
        mesocycle = macrocycle.get_phase_for_week(week_index) or macrocycle.mesocycles[-1]
        week_in_phase = week_index - mesocycle.start_week + 1
        days, weekly_volume_km, hmp_week_decision = _build_week_days(
            mesocycle,
            week_index,
            aligned_profile,
            available_days,
            blocks,
            total_weeks,
            hm_protocol_context,
        )
        if week_index == 1:
            days = _apply_weekly_structure_constraints(days, weekly_structure_constraints, available_days)
        phase_weeks = mesocycle.weeks
        key_workouts = _build_key_workouts(days)
        action_suggestions = _build_week_action_suggestions(week_index, mesocycle, available_days, days)
        hm_week_note = _hm_protocol_week_note(mesocycle, week_index, total_weeks, hm_protocol_context)
        if hm_week_note:
            key_workouts.append(hm_week_note)
            action_suggestions = [hm_week_note] + action_suggestions
        if hmp_week_decision.get("active"):
            hmp_week_decisions.append({
                "week_index": week_index,
                "phase_id": hmp_week_decision.get("phase_id"),
                "phase_label": hmp_week_decision.get("phase_label"),
                "sessions": hmp_week_decision.get("sessions") or [],
                "repair_notes": hmp_week_decision.get("repair_notes") or [],
                "capacity_budget": hmp_week_decision.get("capacity_budget") or {},
            })
            for session in hmp_week_decision.get("sessions") or []:
                if not isinstance(session, dict):
                    continue
                summary = (
                    f"HMP生成器：{session.get('workout_id')} / {session.get('role')} / "
                    f"{session.get('reason')}"
                )
                if summary not in action_suggestions:
                    action_suggestions.append(summary)
        week_plan = WeekPlan(
            week_index=week_index,
            phase=mesocycle.name,
            week_goal=f"第{week_index}周聚焦{mesocycle.goal}；{_goal_strategy_label(race_type)}" + (f"；{hm_week_note}" if hm_week_note else ""),
            load_level=_phase_to_load_level(mesocycle.name, week_in_phase, phase_weeks),
            load_progression_note=(
                f"第{week_index}周位于{mesocycle.name}第{week_in_phase}/{phase_weeks}周，"
                f"周跑量目标约 {weekly_volume_km} km。"
            ),
            days=days,
            execution_reminder="当前仅输出结构骨架，后续逐周渲染阶段再把具体文案与审计信息接入 UI。",
            key_workouts=key_workouts,
            action_suggestions=action_suggestions,
        )
        ensure_repeat_guard_signature(week_plan).weekly_volume_km = weekly_volume_km
        week_plans.append(week_plan)

    plan = StructuredTrainingPlan(
        plan_meta=PlanMeta(
            request_text=str(query or ""),
            requested_weeks=int(requested_weeks or total_weeks),
            actual_weeks=total_weeks,
            goal=str(aligned_profile.get("goal") or "未设置"),
            experience_level=str(aligned_profile.get("experience_level") or "未知"),
            target_race_date=str(aligned_profile.get("target_race_date") or ""),
            plan_type="single_week" if total_weeks == 1 else "multi_week",
            generated_at=date.today().isoformat(),
        ),
        phase_summary=phase_summary,
        week_plans=week_plans,
        first_week_actions=_build_first_week_actions(week_plans[0]) if week_plans else [],
    )
    plan_dict = plan.to_dict()
    if hm_protocol_context.get("active"):
        hm_protocol_context["weekly_decisions"] = hmp_week_decisions
        hm_protocol_context["capacity_budget"] = (
            hmp_week_decisions[0].get("capacity_budget") if hmp_week_decisions else {}
        )
        plan_dict["half_marathon_protocol"] = hm_protocol_context
        validation = validate_half_marathon_protocol_plan(plan_dict)
        if validation.get("issues"):
            repaired_plan = apply_half_marathon_repairs(plan_dict, validation)
            repair_log = repaired_plan.get("half_marathon_protocol_repair_log") or []
            if repair_log:
                plan_dict = repaired_plan
                validation = validate_half_marathon_protocol_plan(plan_dict)
                validation["repair_log"] = repair_log
                validation["repair_applied"] = True
            else:
                validation["repair_applied"] = False
        else:
            validation["repair_applied"] = False
        validation["repair_suggestions"] = build_hmp_repair_suggestions(validation)
        plan_dict["half_marathon_protocol_validation"] = validation
    if weekly_structure_constraints.get("required_workouts") or weekly_structure_constraints.get("forbidden_workouts") or weekly_structure_constraints.get("required_rest_days") or weekly_structure_constraints.get("weekly_frequency"):
        plan_dict["weekly_structure_constraints"] = weekly_structure_constraints
        plan_dict["weekly_structure_validation"] = _validate_weekly_structure_constraints(plan_dict, weekly_structure_constraints)
    return plan_dict


__all__ = ["build_structured_training_plan_skeleton"]
