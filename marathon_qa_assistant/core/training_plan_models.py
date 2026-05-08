from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional


LoadLevel = Literal["low", "medium", "high", "recovery", "taper", "race"]
PlanType = Literal["single_week", "multi_week"]

WEEKDAY_ORDER = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
QUALITY_SESSION_KEYWORDS = ("间歇", "重复", "节奏", "阈值", "tempo", "interval", "vo2", "专项")
LONG_RUN_KEYWORDS = ("长距离", "long run")
REST_SESSION_KEYWORDS = ("休息", "rest")
RECOVERY_LOAD_LEVELS = {"recovery", "taper"}


@dataclass
class DayPlan:
    day: str
    training_type: str
    warmup: str
    main_set: str
    cooldown: str
    venue: str
    notes: str = ""
    warmup_km: float = 0.0
    main_km: float = 0.0
    cooldown_km: float = 0.0

    @property
    def total_km(self) -> float:
        return self.warmup_km + self.main_km + self.cooldown_km


@dataclass
class RepeatGuardSignature:
    quality_sessions: List[str] = field(default_factory=list)
    quality_session_count: int = 0
    long_run_minutes: int = 0
    long_run_distance_km: Optional[float] = None
    key_intensity: str = ""
    weekly_volume_km: Optional[float] = None
    hard_day_count: int = 0
    rest_day_count: int = 0


@dataclass
class WeekPlan:
    week_index: int
    phase: str
    week_goal: str
    load_level: LoadLevel
    load_progression_note: str
    days: List[DayPlan]
    execution_reminder: str
    key_workouts: List[str] = field(default_factory=list)
    action_suggestions: List[str] = field(default_factory=list)
    repeat_guard_signature: RepeatGuardSignature = field(default_factory=RepeatGuardSignature)


@dataclass
class PhaseBlock:
    phase: str
    start_week: int
    end_week: int
    objective: str


@dataclass
class PlanMeta:
    request_text: str
    requested_weeks: int
    actual_weeks: int
    goal: str
    experience_level: str
    target_race_date: str
    plan_type: PlanType
    generated_at: str
    render_version: str = "v1"


@dataclass
class StructuredTrainingPlan:
    plan_meta: PlanMeta
    phase_summary: List[PhaseBlock]
    week_plans: List[WeekPlan]
    first_week_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normalize_text(text: str) -> str:
    cleaned = str(text or "").strip().lower()
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned


def _safe_float_equal(left: Optional[float], right: Optional[float], tolerance: float = 0.1) -> bool:
    if left is None or right is None:
        return False
    return abs(float(left) - float(right)) <= tolerance


def _parse_minutes(text: str) -> int:
    match = re.search(r"(\d+)\s*分钟", str(text or ""))
    return int(match.group(1)) if match else 0


def _parse_distance_km(text: str) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)\s*km", str(text or "").lower())
    if not match:
        return None
    return float(match.group(1))


def _is_quality_session(day: DayPlan) -> bool:
    haystack = " ".join([day.training_type, day.main_set, day.notes]).lower()
    return any(keyword in haystack for keyword in QUALITY_SESSION_KEYWORDS)


def _is_long_run(day: DayPlan) -> bool:
    haystack = " ".join([day.training_type, day.main_set, day.notes]).lower()
    return any(keyword in haystack for keyword in LONG_RUN_KEYWORDS)


def _is_rest_day(day: DayPlan) -> bool:
    haystack = " ".join([day.training_type, day.main_set, day.notes]).lower()
    return any(keyword in haystack for keyword in REST_SESSION_KEYWORDS)


def build_repeat_guard_signature(week: WeekPlan) -> RepeatGuardSignature:
    quality_sessions: List[str] = []
    long_run_minutes = 0
    long_run_distance_km: Optional[float] = None
    hard_day_count = 0
    rest_day_count = 0

    for day in week.days:
        if _is_quality_session(day):
            hard_day_count += 1
            quality_sessions.append(day.training_type.strip() or "质量课")
        if _is_long_run(day):
            long_run_minutes = max(long_run_minutes, _parse_minutes(day.main_set) or _parse_minutes(day.notes))
            parsed_distance = _parse_distance_km(day.main_set) or _parse_distance_km(day.notes)
            if parsed_distance is not None:
                long_run_distance_km = parsed_distance
        if _is_rest_day(day):
            rest_day_count += 1

    quality_sessions = list(dict.fromkeys(quality_sessions))
    key_intensity = quality_sessions[0] if quality_sessions else ""

    existing = week.repeat_guard_signature
    weekly_volume_km = existing.weekly_volume_km if existing.weekly_volume_km is not None else None

    return RepeatGuardSignature(
        quality_sessions=quality_sessions,
        quality_session_count=len(quality_sessions),
        long_run_minutes=long_run_minutes,
        long_run_distance_km=long_run_distance_km,
        key_intensity=key_intensity,
        weekly_volume_km=weekly_volume_km,
        hard_day_count=hard_day_count,
        rest_day_count=rest_day_count,
    )


def ensure_repeat_guard_signature(week: WeekPlan) -> RepeatGuardSignature:
    current = week.repeat_guard_signature
    has_signal = any(
        [
            current.quality_sessions,
            current.quality_session_count,
            current.long_run_minutes,
            current.long_run_distance_km is not None,
            bool(current.key_intensity),
            current.weekly_volume_km is not None,
            current.hard_day_count,
            current.rest_day_count,
        ]
    )
    if has_signal:
        return current

    derived = build_repeat_guard_signature(week)
    week.repeat_guard_signature = derived
    return derived


def validate_plan_meta(plan: StructuredTrainingPlan) -> List[str]:
    errors: List[str] = []
    meta = plan.plan_meta
    if not (1 <= int(meta.requested_weeks) <= 26):
        errors.append("requested_weeks 必须在 1-26 之间。")
    if meta.actual_weeks != len(plan.week_plans):
        errors.append("actual_weeks 必须等于 week_plans 的数量。")
    expected_type = "single_week" if meta.requested_weeks == 1 else "multi_week"
    if meta.plan_type != expected_type:
        errors.append(f"plan_type 应与 requested_weeks 对齐，当前应为 {expected_type}。")
    if not str(meta.request_text or "").strip():
        errors.append("request_text 不能为空。")
    return errors


def validate_week_count(plan: StructuredTrainingPlan) -> List[str]:
    errors: List[str] = []
    week_indices = [week.week_index for week in plan.week_plans]
    expected = list(range(1, len(plan.week_plans) + 1))
    if week_indices != expected:
        errors.append("week_index 必须从 1 开始连续递增。")
    return errors


def validate_phase_summary(plan: StructuredTrainingPlan) -> List[str]:
    errors: List[str] = []
    total_weeks = len(plan.week_plans)
    for block in plan.phase_summary:
        if block.start_week > block.end_week:
            errors.append(f"阶段 {block.phase} 的 start_week 不能大于 end_week。")
        if block.start_week < 1 or block.end_week > total_weeks:
            errors.append(f"阶段 {block.phase} 的周范围超出实际计划周数。")
        if not str(block.objective or "").strip():
            errors.append(f"阶段 {block.phase} 必须包含 objective。")
    return errors


def validate_week_structure(week: WeekPlan) -> List[str]:
    errors: List[str] = []
    if not str(week.phase or "").strip():
        errors.append(f"第 {week.week_index} 周缺少 phase。")
    if not str(week.week_goal or "").strip():
        errors.append(f"第 {week.week_index} 周缺少 week_goal。")
    if not str(week.execution_reminder or "").strip():
        errors.append(f"第 {week.week_index} 周缺少 execution_reminder。")
    if not week.key_workouts:
        errors.append(f"第 {week.week_index} 周缺少 key_workouts。")
    if not week.action_suggestions:
        errors.append(f"第 {week.week_index} 周缺少 action_suggestions。")
    if len(week.days) != 7:
        errors.append(f"第 {week.week_index} 周必须完整覆盖 7 天。")
    weekdays = [day.day for day in week.days]
    if weekdays != WEEKDAY_ORDER:
        errors.append(f"第 {week.week_index} 周的 day 顺序必须严格为周一到周日。")
    for day in week.days:
        if not str(day.training_type or "").strip():
            errors.append(f"第 {week.week_index} 周 {day.day} 缺少 training_type。")
        if not str(day.main_set or "").strip():
            errors.append(f"第 {week.week_index} 周 {day.day} 缺少 main_set。")

    signature = ensure_repeat_guard_signature(week)
    has_signature_signal = any(
        [
            signature.quality_sessions,
            signature.quality_session_count,
            signature.long_run_minutes,
            signature.long_run_distance_km is not None,
            bool(signature.key_intensity),
            signature.weekly_volume_km is not None,
            signature.hard_day_count,
            signature.rest_day_count,
        ]
    )
    if not has_signature_signal:
        errors.append(f"第 {week.week_index} 周缺少可用于重复检测的 signature 特征。")
    return errors


def validate_full_training_plan(plan: StructuredTrainingPlan) -> List[str]:
    errors: List[str] = []
    errors.extend(validate_plan_meta(plan))
    errors.extend(validate_week_count(plan))
    errors.extend(validate_phase_summary(plan))
    if not plan.first_week_actions:
        errors.append("计划缺少 first_week_actions。")
    for week in plan.week_plans:
        errors.extend(validate_week_structure(week))
    return errors


def _normalized_key_sessions(week: WeekPlan) -> List[str]:
    result: List[str] = []
    for day in week.days:
        if _is_quality_session(day) or _is_long_run(day):
            result.append(f"{_normalize_text(day.training_type)}::{_normalize_text(day.main_set)}")
    return result


def key_sessions_identical(week_a: WeekPlan, week_b: WeekPlan) -> bool:
    return _normalized_key_sessions(week_a) == _normalized_key_sessions(week_b) and bool(_normalized_key_sessions(week_a))


def compare_adjacent_weeks(week_a: WeekPlan, week_b: WeekPlan) -> Dict[str, Any]:
    reasons: List[str] = []
    score = 0

    sig_a = ensure_repeat_guard_signature(week_a)
    sig_b = ensure_repeat_guard_signature(week_b)

    if sig_a.quality_sessions == sig_b.quality_sessions and sig_a.quality_sessions:
        score += 20
        reasons.append("质量课类型集合相同")

    if sig_a.long_run_minutes and sig_a.long_run_minutes == sig_b.long_run_minutes:
        score += 20
        reasons.append("长距离时长相同")

    if sig_a.key_intensity and sig_a.key_intensity == sig_b.key_intensity:
        score += 15
        reasons.append("关键强度类型相同")

    if _safe_float_equal(sig_a.weekly_volume_km, sig_b.weekly_volume_km):
        score += 15
        reasons.append("周总量相同")

    same_training_days = 0
    same_main_set_days = 0
    for day_a, day_b in zip(week_a.days, week_b.days):
        if day_a.training_type == day_b.training_type:
            same_training_days += 1
        if _normalize_text(day_a.main_set) == _normalize_text(day_b.main_set) and _normalize_text(day_a.main_set):
            same_main_set_days += 1

    if same_training_days >= 6:
        score += 15
        reasons.append(f"7 天中有 {same_training_days} 天训练类型相同")

    if same_main_set_days >= 4:
        score += 15
        reasons.append(f"7 天中有 {same_main_set_days} 天主课内容相同")

    if key_sessions_identical(week_a, week_b):
        score += 20
        reasons.append("关键训练安排完全一致")

    if week_b.load_level in RECOVERY_LOAD_LEVELS:
        score = max(0, score - 10)
        reasons.append("检测到恢复/减量周，已下调重复风险分")

    if score >= 85:
        status = "fail"
    elif score >= 70:
        status = "warn"
    else:
        status = "pass"

    suggestion_map = {
        "fail": f"重生成第 {week_b.week_index} 周，并调整关键训练结构、长距离或周总量。",
        "warn": f"建议检查第 {week_b.week_index} 周是否需要增加 progression 或恢复差异。",
        "pass": "周间差异通过当前重复检测规则。",
    }

    return {
        "status": status,
        "similarity_score": max(0, min(score, 100)),
        "week_a": week_a.week_index,
        "week_b": week_b.week_index,
        "reasons": reasons,
        "suggestion": suggestion_map[status],
    }


def compare_all_adjacent_weeks(plan: StructuredTrainingPlan) -> List[Dict[str, Any]]:
    return [
        compare_adjacent_weeks(plan.week_plans[idx], plan.week_plans[idx + 1])
        for idx in range(len(plan.week_plans) - 1)
    ]


__all__ = [
    "DayPlan",
    "LoadLevel",
    "PhaseBlock",
    "PlanMeta",
    "PlanType",
    "RepeatGuardSignature",
    "StructuredTrainingPlan",
    "WeekPlan",
    "WEEKDAY_ORDER",
    "build_repeat_guard_signature",
    "compare_adjacent_weeks",
    "compare_all_adjacent_weeks",
    "ensure_repeat_guard_signature",
    "key_sessions_identical",
    "validate_full_training_plan",
    "validate_phase_summary",
    "validate_plan_meta",
    "validate_week_count",
    "validate_week_structure",
]
