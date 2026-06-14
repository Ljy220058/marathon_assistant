from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import logging
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger("training_plan_skeleton")

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
from marathon_qa_assistant.core.training_plan_context import (
    align_plan_duration_context,
    coerce_float_from_unit_text,
    coerce_int_from_unit_text,
    merge_plan_profile_overrides,
)
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
    get_action_library_foundation_hits,
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
# WORKOUT_MAIN_SET_HINTS 和 WORKOUT_NOTES 已移除。
# _build_personalized_day() 现通过 SessionConstraint → _resolve_main_set_from_constraint()
# 从动作库检索课表内容，不可用时由 _build_main_set_fallback() 生成降级描述。
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


@dataclass
class SessionConstraint:
    """训练课约束描述——替代硬编码 main_set 字符串。

    骨架生成器不再硬编码具体训练课表文本（如 "12×400m @5K 配速"），
    改为输出约束描述。调用方用约束从动作库检索具体课表候选项，
    实现课表内容与骨架结构的解耦。

    Fields:
        workout_type: WORKOUT_TEMPLATE_REGISTRY 的 key，用于动作库检索
        training_type_display: 中文显示名（如 "间歇跑"、"长距离"）
        zone_range: 心率区间，如 "Z5-Z6"，来源于 WORKOUT_TEMPLATE_REGISTRY
        target_duration_min: 目标主课时间（分钟），由骨架公式或模板估算
        phase_context: 周期上下文，如 "base_week3"，用于动作库匹配过滤
        intensity_hint: 动态计算的配速/强度提示（非硬编码，由用户门槛配速算出）
        notes: 教练备注（保留原有的训练选择理由说明）
    """
    workout_type: str
    training_type_display: str
    zone_range: str
    target_duration_min: int
    phase_context: str
    intensity_hint: str = ""
    notes: str = ""

# [coaching_practice fallback] 训练类型→(低, 高)周跑量比例
# 数据来源为教练通用实践，不作为一次文献证据使用。
# 当 _distance_fraction_from_literature() 无法从文献规则动态计算时，
# 以此作为降级后备。不要直接引用此字典——优先使用 _main_km_for_type()。
_TRAINING_DISTANCE_FRACTIONS_FALLBACK: Dict[str, Tuple[float, float]] = {
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
_EASY_MAIN_KM_CAP = 14.0
_RECOVERY_MAIN_KM_CAP = 10.0
_EASY_MAIN_KM_MIN = 4.0
_RECOVERY_MAIN_KM_MIN = 3.0
_LONG_RUN_MAIN_KM_MIN = 11.5

# 反向映射：中文训练类型显示名 → WORKOUT_TEMPLATE_REGISTRY 的 key，
# 用于从动作库检索热身/冷身建议时做索引转换。
_DISPLAY_NAME_TO_REGISTRY_KEY: Dict[str, str] = {
    entry["display_name"]: key
    for key, entry in WORKOUT_TEMPLATE_REGISTRY.items()
}
# 补充映射：恢复跑与轻松跑共用同一 registry 条目
_DISPLAY_NAME_TO_REGISTRY_KEY["恢复跑"] = "easy_run"


def _distance_fraction_from_literature(
    training_type: str,
    weekly_volume: float,
) -> Optional[Tuple[float, float]]:
    """尝试从文献规则动态计算训练类型的周跑量比例。

    当前阶段尚未接入训练原则文献库，返回 None 走 fallback。
    后续可在此函数内查询文献知识库，基于用户周跑量和训练类型
    返回(低, 高)比例区间。

    Args:
        training_type: 训练类型中文显示名（如 "间歇跑"、"长距离"）
        weekly_volume: 用户周跑量 (km)

    Returns:
        (low_fraction, high_fraction) 或 None（触发 fallback）
    """
    return None


def _warmup_cooldown_from_action_library(training_type: str) -> Dict[str, Any]:
    """从动作库检索给定训练类型的热身/冷身建议，并尝试解析为距离 (km)。

    调用 workout_template_retriever.get_action_library_foundation_hits()
    获取动作库条目，从条目中提取 warmup_suggestion / cooldown_suggestion 字段。
    动作库无匹配或无法解析时，返回保守默认值并打 warning 日志。

    Args:
        training_type: 训练类型中文显示名（如 "间歇跑"、"长距离"）

    Returns:
        - 动作库匹配: {"warmup_km": float, "cooldown_km": float, "source": "action_library"}
        - 降级默认: {"warmup_km": 1.0, "cooldown_km": 1.0, "source": "fallback_conservative"}
    """
    if not training_type:
        logger.warning("_warmup_cooldown_from_action_library: 训练类型为空，返回保守默认值")
        return {"warmup_km": 1.0, "cooldown_km": 1.0, "source": "fallback_conservative"}

    registry_key = _DISPLAY_NAME_TO_REGISTRY_KEY.get(training_type)
    if not registry_key:
        logger.warning(
            "_warmup_cooldown_from_action_library: 未找到训练类型 '%s' 的 registry key，返回保守默认值",
            training_type,
        )
        return {"warmup_km": 1.0, "cooldown_km": 1.0, "source": "fallback_conservative"}

    try:
        hits = get_action_library_foundation_hits(registry_key)
    except Exception as exc:
        logger.warning(
            "_warmup_cooldown_from_action_library: get_action_library_foundation_hits('%s') 失败: %s，返回保守默认值",
            registry_key, exc,
        )
        return {"warmup_km": 1.0, "cooldown_km": 1.0, "source": "fallback_conservative"}

    warmup_text = ""
    cooldown_text = ""
    for hit in hits:
        warmup_text = warmup_text or str(hit.get("warmup_suggestion") or "").strip()
        cooldown_text = cooldown_text or str(hit.get("cooldown_suggestion") or "").strip()
        if warmup_text and cooldown_text:
            break

    if not warmup_text and not cooldown_text:
        logger.warning(
            "_warmup_cooldown_from_action_library: 动作库中 '%s' 无热身/冷身建议，返回保守默认值",
            training_type,
        )
        return {"warmup_km": 1.0, "cooldown_km": 1.0, "source": "fallback_conservative"}

    warmup_km = _parse_km_from_suggestion(warmup_text)
    cooldown_km = _parse_km_from_suggestion(cooldown_text)

    # 从建议文本可解析出距离时使用动作库数据，否则回退保守默认
    if warmup_km is not None or cooldown_km is not None:
        result = {
            "warmup_km": warmup_km if warmup_km is not None else 1.0,
            "cooldown_km": cooldown_km if cooldown_km is not None else 1.0,
            "source": "action_library",
        }
        logger.debug(
            "_warmup_cooldown_from_action_library: '%s' 从动作库解析 warmup=%.1fkm cooldown=%.1fkm",
            training_type, result["warmup_km"], result["cooldown_km"],
        )
        return result

    logger.warning(
        "_warmup_cooldown_from_action_library: 无法从动作库建议文本中解析 '%s' 的距离值，返回保守默认值",
        training_type,
    )
    return {"warmup_km": 1.0, "cooldown_km": 1.0, "source": "fallback_conservative"}


def _parse_km_from_suggestion(suggestion_text: str) -> Optional[float]:
    """从热身/冷身建议文本中尝试提取距离 (km)。

    匹配模式:
        - "3.2-4.8km" → 取最大值 4.8
        - "10-15分钟慢跑" → 按 ~6:00/km 配速估算 → 1.7-2.5km，取最大值 2.5
        - 无法解析时返回 None
    """
    if not suggestion_text:
        return None

    # 直接匹配距离值: "Xkm" 或 "X.Xkm"
    km_matches = re.findall(r"(\d+(?:\.\d+)?)\s*km", suggestion_text, flags=re.IGNORECASE)
    if km_matches:
        return max(float(m) for m in km_matches)

    # 从慢跑时长估算: "X分钟慢跑" 按 ~6:00/km 配速
    minute_matches = re.findall(r"(\d+)\s*分钟\s*慢跑", suggestion_text)
    if minute_matches:
        max_minutes = max(int(m) for m in minute_matches)
        return round(max_minutes / 6.0, 1)

    # "慢跑" + 数字 (可能在其他位置)
    jog_match = re.search(r"慢跑\s*(\d+)", suggestion_text)
    if jog_match:
        return round(int(jog_match.group(1)) / 6.0, 1)

    return None


def _parse_pace_seconds(pace: Any) -> int:
    text = str(pace or "").strip().lower()
    match = re.search(r"(\d+)[:：](\d+)", text)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))
    match = re.search(r"(\d+)\s*分\s*(\d+)", text)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))
    return 270


def _parse_duration_seconds(value: Any) -> Optional[int]:
    text = str(value or "").strip().lower()
    if not text:
        return None
    match = re.search(r"(\d+)\s*小时\s*(\d+)\s*分?", text)
    if match:
        return int(match.group(1)) * 3600 + int(match.group(2)) * 60
    match = re.search(r"(\d+)\s*h\s*(\d+)", text)
    if match:
        return int(match.group(1)) * 3600 + int(match.group(2)) * 60
    match = re.search(r"\b([1-3])[:：](\d{2})(?::(\d{2}))?\b", text)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds
    return None


def _parse_target_pace_seconds(value: Any) -> Optional[int]:
    text = str(value or "").strip().lower()
    if not text:
        return None
    match = re.search(r"(\d+)[:：](\d{2})\s*/?\s*(?:km|公里|千米)?", text)
    if match:
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        if 2 <= minutes <= 9:
            return minutes * 60 + seconds
    return None


def _cap_fast_pace_by_profile(seconds: int, profile: Dict[str, Any]) -> int:
    mileage = coerce_float_from_unit_text(profile.get("weekly_mileage"), default=0.0) or 0.0
    goal_text = _profile_text(profile, "goal", "target_pace", "target_time", "target_half_time")
    if any(token in goal_text for token in ("完赛", "轻松", "健康", "首")):
        fastest = 330 if mileage < 45 else 300
    elif mileage < 40:
        fastest = 315
    elif mileage < 55:
        fastest = 285
    elif mileage < 70:
        fastest = 260
    else:
        fastest = 220
    return max(int(seconds), fastest)


def _resolve_threshold_pace_seconds(profile: Dict[str, Any], race_type: str) -> int:
    target_text = _profile_text(profile, "target_pace", "target_time", "target_half_time", "goal")
    target_pace = _parse_target_pace_seconds(target_text)
    if target_pace:
        return _cap_fast_pace_by_profile(target_pace - 10, profile)

    target_duration = _parse_duration_seconds(target_text)
    if target_duration and race_type == "half_marathon":
        hmp_seconds = int(target_duration / 21.0975)
        return _cap_fast_pace_by_profile(hmp_seconds - 10, profile)
    if target_duration and race_type == "marathon":
        mp_seconds = int(target_duration / 42.195)
        return _cap_fast_pace_by_profile(mp_seconds - 20, profile)

    parsed_t_pace = _parse_pace_seconds(profile.get("t_pace"))
    if str(profile.get("t_pace") or "").strip():
        return _cap_fast_pace_by_profile(parsed_t_pace, profile)

    return _cap_fast_pace_by_profile(360, profile)


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


# 经验水平对训练时长的调整系数。
# 等级：[coaching_heuristic]——基于训练实践共识（新手训练年龄<1y，恢复/适应能力低→降量；
# 精英训练年龄>3y，耐受与恢复强→可加量）。无单一同行评审文献给出精确系数，待实证校准
# （建议积累用户训练响应数据后用个体响应模型替换）。
_EXPERIENCE_DURATION_FACTOR = {
    "新手": 0.85, "初级": 0.85,   # 训练年龄 <1 年
    "进阶": 1.00, "中级": 1.00,   # 训练年龄 1-3 年，标准负荷
    "精英": 1.10, "高级": 1.10,   # 训练年龄 >3 年
}


def _personalized_target_duration(
    training_type_display: str,
    profile: Optional[Dict[str, Any]] = None,
) -> int:
    """按训练类型典型值 × 个体系数(经验/跑量)估算主课时长，替代硬编码 40。

    L1 个性化。来源标注：
    - typical_minutes / clamp 边界 [min,max]：WORKOUT_CONSTRAINTS
      （Daniels' Running Formula / Pfitzinger / Billat 2001，A 级教材，
      见 core/workout_constraints.py 每条 source/source_grade 字段）。
    - experience_factor：[coaching_heuristic]，见 _EXPERIENCE_DURATION_FACTOR 注释。
    - mileage_factor：[coaching_heuristic]——周跑量<30km 单课耐受低→×0.90，
      >60km 耐受高→×1.10；依据 ACSM 渐进原则与 Daniels 周跑量-单课占比（间接），
      精确阈值待实证校准。

    profile 缺失时退化为训练类型 typical（仅 A 级文献常量，无启发式系数）。
    """
    try:
        from marathon_qa_assistant.core.workout_constraints import WORKOUT_CONSTRAINTS
    except Exception:
        WORKOUT_CONSTRAINTS = {}
    constraint = WORKOUT_CONSTRAINTS.get(str(training_type_display or ""))
    typical = int(getattr(constraint, "typical_minutes", 0)) or 40
    factor = 1.0
    if isinstance(profile, dict):
        factor *= _EXPERIENCE_DURATION_FACTOR.get(
            str(profile.get("experience_level") or "").strip(), 1.0
        )
        try:
            mileage = float(profile.get("weekly_mileage") or 0)
        except (TypeError, ValueError):
            mileage = 0.0
        if mileage > 0:
            factor *= 0.90 if mileage < 30 else (1.10 if mileage > 60 else 1.0)
    return _cap_session_duration_min(str(training_type_display or ""), int(round(typical * factor)))


def _build_personalized_day(
    requirement: Dict[str, Any],
    fallback_day: str,
    profile: Optional[Dict[str, Any]] = None,
) -> DayPlan:
    workout_type = str(requirement.get("workout_type") or "").strip()
    entry = WORKOUT_TEMPLATE_REGISTRY.get(workout_type, {})
    day = str(requirement.get("day") or fallback_day).strip() or fallback_day
    training_type = str(entry.get("display_name") or requirement.get("display_name") or workout_type)
    venue = "田径场/平路" if workout_type in QUALITY_WORKOUT_TYPES else "公路/绿道"
    if workout_type == "easy_run":
        venue = "公园/绿道"

    # SessionConstraint → 动作库检索；主课时长按训练类型典型值 × 个体系数（L1 个性化，替代硬编码 40）
    constraint = _session_constraint(
        training_type_display=training_type,
        target_duration_min=_personalized_target_duration(training_type, profile),
        phase_context="user_defined",
        notes=f"来自用户个性化周结构要求，安排{training_type}。",
    )
    main_set, _ = _resolve_main_set_from_constraint(constraint)

    wc = _warmup_cooldown_from_action_library(training_type)
    if wc["source"] == "action_library":
        warmup = f"慢跑{wc['warmup_km']}km + 动态拉伸"
        cooldown = f"慢跑{wc['cooldown_km']}km + 静态拉伸"
    else:
        warmup = "慢跑15分钟 + 动态拉伸" if workout_type in QUALITY_WORKOUT_TYPES else "慢跑10分钟 + 动态拉伸"
        cooldown = "慢跑10分钟 + 静态拉伸"

    return DayPlan(
        day=day,
        training_type=training_type,
        warmup=warmup,
        main_set=main_set,
        cooldown=cooldown,
        venue=venue,
        notes=constraint.notes,
    )


def _apply_weekly_structure_constraints(days: List[DayPlan], constraints: Dict[str, Any], available_days: List[str], profile: Optional[Dict[str, Any]] = None) -> List[DayPlan]:
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
            updated[str(target_day)] = _build_personalized_day(personalized, str(target_day), profile)

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


def _resolve_macrocycle(
    profile: Dict[str, Any],
    total_weeks: int,
    advisory: Optional[Any] = None,
) -> Macrocycle:
    macrocycle = Macrocycle.from_profile(profile, advisory=advisory)
    if macrocycle is not None and macrocycle.total_weeks == total_weeks:
        return macrocycle
    return Macrocycle.from_race_date(
        race_date=date.today() + timedelta(weeks=max(1, total_weeks)),
        total_weeks=total_weeks,
        profile=profile,
        advisory=advisory,
    )


def _phase_to_load_level(phase_name: str, week_in_phase: int, phase_weeks: int) -> str:
    phase_name = str(phase_name or "")
    if any(kw in phase_name for kw in ("减量", "调整", "Taper", "taper")):
        return "taper"
    if any(kw in phase_name for kw in ("巅峰", "Peak", "peak")):
        return "high"
    if any(kw in phase_name for kw in ("建设", "Build", "build")) and phase_weeks >= 3 and week_in_phase == phase_weeks:
        return "high"
    if any(kw in phase_name for kw in ("基础", "Base", "base")) and phase_weeks >= 3 and week_in_phase == phase_weeks:
        return "medium"
    return "medium" if week_in_phase > 1 else "low"


def _is_half_year_plan(total_weeks: int) -> bool:
    return int(total_weeks or 0) >= 20


def _phase_family(phase_name: str) -> str:
    text = str(phase_name or "")
    # 精确匹配（子阶段编号）
    if any(kw in text for kw in ("基础期-1", "基础阶段-1", "Base 1", "General Phase 1")):
        return "base_1"
    if any(kw in text for kw in ("基础期-2", "基础阶段-2", "Base 2", "General Phase 2")):
        return "base_2"
    if any(kw in text for kw in ("建设期-1", "建设阶段-1", "Build 1")):
        return "build_1"
    if any(kw in text for kw in ("建设期-2", "建设阶段-2", "Build 2")):
        return "build_2"
    # 精确匹配（HMP 协议阶段，在泛关键词前拦截）
    if "比赛专项" in text:
        return "peak"
    if "专项构建" in text:
        return "build"
    # 全马 / 通用阶段关键词
    if any(kw in text for kw in ("巅峰", "Peak", "peak")):
        return "peak"
    if any(kw in text for kw in ("减量", "调整", "Taper", "taper")):
        return "taper"
    if any(kw in text for kw in ("基础", "Base", "base")):
        return "base"
    if any(kw in text for kw in ("建设", "构建", "Build", "build")):
        return "build"
    return "build"


def _resolve_training_slots(available_days: List[str]) -> Tuple[str, Optional[str], str]:
    ordered = available_days or DEFAULT_AVAILABLE_DAYS.copy()
    long_run_day = ordered[-1]
    quality_days = [day for day in ordered if day != long_run_day]
    primary_quality_day = quality_days[0] if quality_days else ("周二" if long_run_day != "周二" else "周三")
    secondary_quality_day = quality_days[1] if len(quality_days) > 1 else None
    return primary_quality_day, secondary_quality_day, long_run_day


def _resolve_goal_race_type(goal: Any) -> str:
    """从 goal 文本解析赛事类型。

    注意："全程" 有时指 "全马"（全程马拉松），但也有语境歧义；
    优先看更明确的标识（全马/马拉松等），再回落看半马。
    当全马和半马关键词同时出现时，"全马" 优先（全马是更特定目标）。
    """
    text = str(goal or "").lower()
    has_full = "全马" in text or "马拉松" in text or "marathon" in text or "42k" in text or "42.2" in text or "全程" in text
    has_half = "半马" in text or "半程" in text or "half" in text or "21k" in text or "21.1" in text
    # P0-3: 全马优先于半马，避免 "先半马后全马" 的描述被误判为半马
    if has_full:
        return "marathon"
    if has_half:
        return "half_marathon"
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


def _profile_float(profile: Dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        value = profile.get(key)
        parsed = coerce_float_from_unit_text(value)
        if parsed is None:
            continue
        return parsed
    return None


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
        weekly_mileage_km=_profile_float(profile, "weekly_mileage"),
        injury_or_fatigue=injury_or_fatigue,
    )


def _build_hm_protocol_context(profile: Dict[str, Any], total_weeks: int, race_type: str) -> Dict[str, Any]:
    if race_type != "half_marathon":
        return {"active": False}

    # ── 原型判断：优先走 LLM，不可用时降级到关键词匹配 ──
    llm_archetype_input: Optional[RunnerArchetypeInput] = None
    field_evidence: Dict[str, str] = {}
    try:
        from marathon_qa_assistant.core.archetype_advisor import (  # noqa: E402
            get_archetype_advisory,
        )
        llm_archetype_input, field_evidence = get_archetype_advisory(profile, total_weeks)
    except Exception as exc:
        logger.debug("archetype advisor 调用失败，降级到关键词匹配: %s", exc)

    archetype_input: RunnerArchetypeInput = (
        llm_archetype_input
        if llm_archetype_input is not None
        else _build_hm_archetype_input(profile, total_weeks)
    )

    decisions = recommend_archetypes(archetype_input)
    primary = decisions[0]
    preferred_rules = workout_rules_for_archetype(primary.archetype_id)
    profile_gaps = detect_half_marathon_profile_gaps(profile)
    pace_calibration = build_half_marathon_pace_calibration(profile)
    return {
        "active": True,
        "recent_marathon": archetype_input.recent_marathon,
        "input_weekly_mileage_km": archetype_input.weekly_mileage_km,
        "input_recent_four_week_mileage_km": _profile_float(
            profile,
            "recent_four_week_mileage",
            "recent_4_week_mileage",
            "recent_four_weekly_mileage",
            "last_month_mileage",
        ),
        "profile_gaps": profile_gaps,
        "pace_calibration": pace_calibration,
        "selected_archetype": primary.to_dict(),
        "archetype_candidates": [decision.to_dict() for decision in decisions],
        "phase_sequence": select_phase_sequence(total_weeks, recent_marathon=archetype_input.recent_marathon),
        "preferred_workouts": [rule.to_dict() for rule in preferred_rules],
        "archetype_llm_generated": llm_archetype_input is not None,
        "archetype_field_evidence": field_evidence,
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


def _resolve_main_set_from_constraint(
    constraint: SessionConstraint,
) -> Tuple[str, List[str]]:
    """从 SessionConstraint 检索动作库，返回 (main_set_text, evidence_sources)。

    优先从动作库（JSONL/FAISS）检索匹配的训练课表候选项，
    不可用时回退到从约束字段生成文本描述。
    返回的 evidence_sources 用于追溯 main_set 的来源（动作库 chunk 或 fallback）。
    """
    if not constraint or not constraint.workout_type:
        return ("训练课待确认", [])

    # 尝试从动作库检索
    try:
        hits = get_action_library_foundation_hits(constraint.workout_type)
    except Exception as exc:
        logger.debug("_resolve_main_set_from_constraint: 动作库检索失败 (%s)，使用 fallback", exc)
        hits = []

    if hits:
        try:
            card = build_daily_workout_template_card_from_hits(
                workout_type=constraint.workout_type,
                day="",
                hits=hits,
            )
            candidates = card.get("main_set_candidates", [])
            if candidates:
                # 选取第一个候选项，附加配速/强度提示
                main_set = _clamp_main_set_minutes(str(candidates[0]), constraint.training_type_display)
                if constraint.intensity_hint:
                    main_set = f"{main_set}（{constraint.intensity_hint}）"
                sources = card.get("source", [])
                logger.debug(
                    "_resolve_main_set_from_constraint: '%s' 从动作库命中 %d 个候选项",
                    constraint.workout_type, len(candidates),
                )
                return (main_set, sources)
        except Exception as exc:
            logger.debug(
                "_resolve_main_set_from_constraint: build card 失败 (%s)，使用 fallback", exc,
            )

    # Fallback: 用约束字段生成文本描述，保留训练类型和配速信息
    fallback = _build_main_set_fallback(constraint)
    logger.debug(
        "_resolve_main_set_from_constraint: '%s' 动作库未命中，使用 fallback 文本",
        constraint.workout_type,
    )
    return (fallback, [])


def _build_main_set_fallback(constraint: SessionConstraint) -> str:
    """从 SessionConstraint 生成 main_set 文本描述（动作库不可用时的降级方案）。

    该降级方案保留训练类型显示名和动态计算的配速信息，
    但不再包含硬编码的训练课表结构（如 "3×2000m"）。
    """
    parts = [f"{constraint.training_type_display}：约{constraint.target_duration_min}分钟"]
    if constraint.intensity_hint:
        parts.append(constraint.intensity_hint)
    return "，".join(parts)


def _build_long_run_fallback(
    minutes: int,
    pace_range: str,
    suffix: str = "",
    training_type_display: str = "长距离",
) -> str:
    """长距离跑 main_set 降级文本——保留动态计算的距离/时间公式结果。

    距离计算公式（如 weekly_volume * 0.25）属于数学计算而非硬编码模板，
    此处保留计算结果；仅移除硬编码的具体训练结构描述。
    """
    text = f"{minutes}分钟，配速{pace_range}/km"
    if suffix:
        text += f"，{suffix}"
    return text


def _session_constraint(
    training_type_display: str,
    target_duration_min: int,
    phase_context: str,
    intensity_hint: str = "",
    notes: str = "",
) -> SessionConstraint:
    """从训练类型中文名构建 SessionConstraint，自动查询 registry 获取 workout_type 和 zone_range。"""
    registry_key = _DISPLAY_NAME_TO_REGISTRY_KEY.get(training_type_display)
    if not registry_key:
        logger.warning(
            "_session_constraint: 未找到训练类型 '%s' 的 registry key，回退到 easy_run",
            training_type_display,
        )
        registry_key = "easy_run"

    entry = WORKOUT_TEMPLATE_REGISTRY.get(registry_key, {})
    zone_range = entry.get("zone_range", "Z1-Z2")

    return SessionConstraint(
        workout_type=registry_key,
        training_type_display=training_type_display,
        zone_range=zone_range,
        target_duration_min=_cap_session_duration_min(training_type_display, target_duration_min),
        phase_context=phase_context,
        intensity_hint=intensity_hint,
        notes=notes,
    )


def _build_quality_session(
    mesocycle: Mesocycle,
    week_index: int,
    threshold_pace_seconds: int,
    race_type: str = "general",
    total_weeks: int = 0,
) -> SessionConstraint:
    phase_name = mesocycle.name
    phase_family = _phase_family(phase_name)
    week_in_phase = week_index - mesocycle.start_week + 1
    long_plan = _is_half_year_plan(total_weeks)
    interval_pace = _format_pace(threshold_pace_seconds - 12 - (week_index % 3) * 2)
    threshold_pace = _format_pace(threshold_pace_seconds)
    slower_threshold_pace = _format_pace(threshold_pace_seconds + 5)
    marathon_pace = _format_pace(threshold_pace_seconds + 18)
    phase_ctx = f"{phase_family}_week{week_in_phase}"
    easy_pace_range = _format_pace_range(threshold_pace_seconds + 45, threshold_pace_seconds + 65)
    sc = _session_constraint  # 局部别名以缩短行

    if long_plan and race_type == "half_marathon" and phase_family != "taper":
        options_by_phase = {
            "base_1": [
                sc("有氧阈值训练", 35, phase_ctx, f"配速{slower_threshold_pace}/km", "半年级半马计划前段以有氧阈和动作稳定性打底。"),
                sc("节奏跑", 20, phase_ctx, f"配速{threshold_pace}/km", "用短节奏跑建立半马专项配速感。"),
                sc("轻松跑", 55, phase_ctx, f"配速{easy_pace_range}/km", "长周期前段控制强度，优先建立训练连续性。"),
                sc("短冲", 20, phase_ctx, f"配速{interval_pace}/km", "基础期轻量短冲引入速度元素，不带疲劳。"),
            ],
            "base_2": [
                sc("无氧阈跑", 30, phase_ctx, f"配速{slower_threshold_pace}/km", "在有氧基础上加入巡航间歇，提升阈值耐受。"),
                sc("渐进跑", 45, phase_ctx, f"从{_format_pace(threshold_pace_seconds + 45)}/km渐进至{threshold_pace}/km", "通过渐进跑连接有氧基础与专项强度。"),
                sc("节奏跑", 25, phase_ctx, f"配速{threshold_pace}/km", "逐步延长半马专项连续输出。"),
                sc("法特莱克", 40, phase_ctx, f"配速{_format_pace_range(threshold_pace_seconds + 25, threshold_pace_seconds)}/km", "以速度游戏方式在不同强度间切换，提升有氧变通能力。"),
            ],
            "build_1": [
                sc("间歇跑", 25, phase_ctx, f"配速{interval_pace}/km", "建设期前段用中短间歇提升速度储备。"),
                sc("无氧阈跑", 38, phase_ctx, f"配速{slower_threshold_pace}/km", "强化半马配速附近的稳定输出。"),
                sc("节奏跑", 30, phase_ctx, f"配速{threshold_pace}/km", "把持续跑时间推进到专项区间。"),
                sc("坡道训练", 25, phase_ctx, f"配速{interval_pace}/km", "利用坡道同时训练力量和跑步经济性。"),
            ],
            "build_2": [
                sc("摄氧量训练", 30, phase_ctx, f"配速{interval_pace}/km", "建设期后段保留摄氧量刺激但控制总量。"),
                sc("无氧阈跑", 36, phase_ctx, f"配速{slower_threshold_pace}/km", "以更长巡航间歇提升专项耐力。"),
                sc("节奏跑", 35, phase_ctx, f"配速{threshold_pace}/km", "把节奏跑拆组，减少长计划后段重复感。"),
                sc("坡道训练", 25, phase_ctx, f"配速{slower_threshold_pace}/km", "用更长坡道段强化抗疲劳能力。"),
            ],
            "peak": [
                sc("节奏跑", 35, phase_ctx, f"配速{threshold_pace}/km", "巅峰期强化半马专项持续输出。"),
                sc("摄氧量训练", 25, phase_ctx, f"配速{interval_pace}/km", "用较短总量维持高端能力。"),
                sc("无氧阈跑", 35, phase_ctx, f"配速{slower_threshold_pace}/km", "接近比赛前用长巡航间歇巩固阈值。"),
            ],
        }
        options = options_by_phase.get(phase_family, options_by_phase["build_1"])
    elif long_plan and race_type == "marathon" and phase_family != "taper":
        options_by_phase = {
            "base_1": [
                sc("轻松跑", 60, phase_ctx, f"配速{_format_pace_range(threshold_pace_seconds + 50, threshold_pace_seconds + 70)}/km", "半年级全马前段优先扩展有氧容量。"),
                sc("马拉松配速跑", 25, phase_ctx, f"配速{marathon_pace}/km", "早期轻量接触全马专项配速。"),
                sc("渐进跑", 45, phase_ctx, f"从{_format_pace(threshold_pace_seconds + 60)}/km渐进至{_format_pace(threshold_pace_seconds + 25)}/km", "用渐进节奏提升有氧控制能力。"),
                sc("短冲", 20, phase_ctx, f"配速{interval_pace}/km", "基础期末尾短冲激活神经肌肉，不带疲劳。"),
            ],
            "base_2": [
                sc("马拉松配速跑", 35, phase_ctx, f"配速{marathon_pace}/km", "巩固全马配速感。"),
                sc("渐进跑", 55, phase_ctx, f"从{_format_pace(threshold_pace_seconds + 55)}/km渐进至{marathon_pace}/km", "连接有氧基础与专项耐力。"),
                sc("无氧阈跑", 30, phase_ctx, f"配速{slower_threshold_pace}/km", "用较温和巡航间歇提高效率。"),
                sc("法特莱克", 50, phase_ctx, f"配速{_format_pace_range(threshold_pace_seconds + 25, threshold_pace_seconds)}/km", "通过速度游戏累积不同区间的有氧时间。"),
            ],
            "build_1": [
                sc("马拉松配速跑", 55, phase_ctx, f"配速{marathon_pace}/km", "建设期前段增加专项配速累计时间。"),
                sc("节奏跑", 25, phase_ctx, f"配速{threshold_pace}/km", "提高乳酸阈值，为全马配速留余量。"),
                sc("渐进跑", 65, phase_ctx, f"从{_format_pace(threshold_pace_seconds + 50)}/km渐进至{marathon_pace}/km", "强化后段稳定输出。"),
                sc("坡道训练", 25, phase_ctx, f"配速{interval_pace}/km", "利用坡道同时训练力量与跑步经济性。"),
            ],
            "build_2": [
                sc("马拉松配速跑", 60, phase_ctx, f"配速{marathon_pace}/km", "建设期后段突出全马专项耐力。"),
                sc("无氧阈跑", 38, phase_ctx, f"配速{slower_threshold_pace}/km", "保留阈值刺激但不堆叠过高强度。"),
                sc("渐进跑", 75, phase_ctx, f"从{_format_pace(threshold_pace_seconds + 55)}/km渐进至{marathon_pace}/km", "模拟长距离后段专项配速控制。"),
                sc("坡道训练", 25, phase_ctx, f"配速{slower_threshold_pace}/km", "用更长坡道段强化抗疲劳能力。"),
            ],
            "peak": [
                sc("马拉松配速跑", 70, phase_ctx, f"配速{marathon_pace}/km", "巅峰期模拟比赛配速节奏。"),
                sc("渐进跑", 70, phase_ctx, f"后段配速{marathon_pace}/km", "把专项配速放在疲劳后段完成。"),
                sc("节奏跑", 30, phase_ctx, f"配速{threshold_pace}/km", "用较短质量课维持跑步经济性。"),
            ],
        }
        options = options_by_phase.get(phase_family, options_by_phase["build_1"])
    elif any(kw in phase_name for kw in ("减量", "调整", "Taper", "taper")):
        taper_tempo_min = 20 + (week_index % 2) * 5
        options = [
            sc("节奏跑", taper_tempo_min, phase_ctx, f"配速{threshold_pace}/km", "保留节奏感，但总负荷下降。"),
            sc("间歇跑", 15, phase_ctx, f"配速{interval_pace}/km", "以短间歇维持步频与速度感。"),
        ]
    elif any(kw in phase_name for kw in ("基础", "Base", "base")):
        base_tempo_min = 20 + (week_index % 3) * 5
        base_prog_min = 40 + (week_index % 3) * 5
        options = [
            sc("有氧阈值训练", 35, phase_ctx, f"配速{slower_threshold_pace}/km", "以有氧阈值训练建立脂肪代谢基础，保持低强度高有氧刺激。"),
            sc("节奏跑", base_tempo_min, phase_ctx, f"配速{threshold_pace}/km", "以稳定阈值持续跑温和提升有氧基础。"),
            sc("渐进跑", base_prog_min, phase_ctx, f"从{_format_pace(threshold_pace_seconds + 45)}/km渐进至{threshold_pace}/km", "通过渐进跑温和引入强度元素，不急于堆高强度。"),
            sc("法特莱克", 35, phase_ctx, f"配速{_format_pace_range(threshold_pace_seconds + 25, threshold_pace_seconds)}/km", "以速度游戏方式在不同强度间切换，低心理压力高有氧刺激。"),
        ]
    elif race_type == "half_marathon" and not any(kw in phase_name for kw in ("减量", "调整", "Taper", "taper")):
        options = [
            sc("无氧阈跑", 30, phase_ctx, f"配速{slower_threshold_pace}/km", "半马目标优先建立阈值耐受和专项节奏感。"),
            sc("节奏跑", 25, phase_ctx, f"配速{threshold_pace}/km", "围绕半马专项配速感做连续输出。"),
            sc("间歇跑", 25, phase_ctx, f"配速{interval_pace}/km", "用较短间歇保持速度储备，避免首周过量。"),
        ]
    elif race_type == "marathon" and not any(kw in phase_name for kw in ("减量", "调整", "Taper", "taper")):
        options = [
            sc("马拉松配速跑", 35, phase_ctx, f"配速{marathon_pace}/km", "全马目标优先建立可持续专项配速感。"),
            sc("渐进跑", 50, phase_ctx, f"从{_format_pace(threshold_pace_seconds + 55)}/km渐进至{marathon_pace}/km", "用渐进节奏连接有氧基础与全马专项耐力。"),
            sc("轻松跑", 55, phase_ctx, f"配速{easy_pace_range}/km", "首周先稳住有氧容量，不急于堆高强度。"),
        ]
    else:
        gen_interval_reps = 5 + (week_index % 3)
        gen_threshold_reps = 4 + (week_index % 2)
        gen_tempo_min = 25 + (week_index % 3) * 5
        options = [
            sc("间歇跑", 30, phase_ctx, f"配速{interval_pace}/km", "围绕专项能力做主质量课。"),
            sc("无氧阈跑", 38, phase_ctx, f"配速{slower_threshold_pace}/km", "强化比赛配速附近的耐受。"),
            sc("节奏跑", gen_tempo_min, phase_ctx, f"配速{threshold_pace}/km", "把持续跑时间推进到专项区间。"),
            sc("法特莱克", 45, phase_ctx, f"配速{_format_pace_range(threshold_pace_seconds + 25, threshold_pace_seconds)}/km", "通过速度游戏丰富训练刺激，避免同型课重复。"),
            sc("坡道训练", 25, phase_ctx, f"配速{interval_pace}/km", "利用坡道同时训练力量和跑步经济性。"),
        ]

    option_index = week_in_phase - 1 if long_plan and phase_family != "taper" else week_index - 1
    return options[option_index % len(options)]


def _build_secondary_session(
    mesocycle: Mesocycle,
    week_index: int,
    threshold_pace_seconds: int,
    allow_quality: bool,
    total_weeks: int = 0,
) -> SessionConstraint:
    phase_family = _phase_family(mesocycle.name)
    long_plan = _is_half_year_plan(total_weeks)
    easy_pace = _format_pace_range(threshold_pace_seconds + 45, threshold_pace_seconds + 65)
    threshold_pace = _format_pace(threshold_pace_seconds + 3)
    phase_ctx = f"{phase_family}_week{week_index}"
    sc = _session_constraint

    if long_plan and phase_family != "taper":
        if phase_family in {"base_1", "base_2"}:
            if week_index % 4 == 0:
                return sc("恢复跑", 40, phase_ctx, f"配速{easy_pace}/km", "半年级长计划前半段把第二训练日留给恢复，减少重复感。")
            if phase_family == "base_2" and week_index % 2 == 0:
                return sc("轻松跑", 50, phase_ctx, f"配速{easy_pace}/km", "通过轻松跑维持周跑量，减少周内双质量课频率。")
            return sc("节奏跑", 20, phase_ctx, f"配速{threshold_pace}/km", "在基础阶段后半程加入温和节奏刺激。")
        if phase_family in {"build_1", "build_2"}:
            if week_index % 3 == 0:
                return sc("马拉松配速跑", 30, phase_ctx, f"配速{_format_pace(threshold_pace_seconds + 18)}/km", "建设期的第二训练日加入专项配速，但总量控制在可恢复范围。")
            if week_index % 2 == 0:
                return sc("节奏跑", 25, phase_ctx, f"配速{threshold_pace}/km", "以节奏跑承接主课，避免每周都出现同型间歇。")
            return sc("轻松跑", 45, phase_ctx, f"配速{easy_pace}/km", "让长计划中的中段周内结构保留恢复窗口。")
        if phase_family == "peak":
            if week_index % 2 == 0:
                return sc("渐进跑", 50, phase_ctx, f"从{_format_pace(threshold_pace_seconds + 55)}/km渐进至{_format_pace(threshold_pace_seconds + 20)}/km", "峰值阶段第二训练日用渐进跑增强疲劳下配速控制。")
            return sc("轻松跑", 40, phase_ctx, f"配速{easy_pace}/km", "峰值阶段保留更明确的恢复窗口。")

    if not allow_quality or any(kw in mesocycle.name for kw in ("减量", "调整", "Taper", "taper")):
        easy_min = 40 + (week_index % 3) * 5
        return sc("轻松跑", easy_min, phase_ctx, f"配速{easy_pace}/km", "用轻松跑承接主课后的恢复。")

    if phase_family == "build":
        if week_index % 2 == 0:
            tempo_min = 20 + (week_index % 2) * 5
            return sc("节奏跑", tempo_min, phase_ctx, f"配速{threshold_pace}/km", "建设期次课以节奏跑维持乳酸阈值刺激。")
        return sc("法特莱克", 35, phase_ctx, f"配速{easy_pace}/km", "建设期奇数周以法特莱克丰富刺激，低心理压力。")

    if week_index % 2 == 0:
        tempo_min = 20 + (week_index % 2) * 5
        return sc("节奏跑", tempo_min, phase_ctx, f"配速{threshold_pace}/km", "作为本周第二刺激点，保持与主课不同的刺激形式。")
    easy_min = 45 + (week_index % 2) * 5
    return sc("轻松跑", easy_min, phase_ctx, f"配速{easy_pace}/km", "维持跑量，不再叠加额外高强度。")


def _build_long_run_main_set(
    mesocycle: Mesocycle,
    week_index: int,
    base_minutes: int,
    threshold_pace_seconds: int,
    race_type: str = "general",
    total_weeks: int = 0,
) -> SessionConstraint:
    """长距离跑主课约束描述。

    距离计算公式（如 weekly_volume * 0.25、base_minutes + week_index * 3）
    属于数学计算而非硬编码模板，此处保留计算结果。
    特殊结构指令（如 "中段加入马拉松配速块"）放入 notes，由动作库检索解析。
    """
    phase_family = _phase_family(mesocycle.name)
    long_plan = _is_half_year_plan(total_weeks)
    week_in_phase = week_index - mesocycle.start_week + 1
    phase_ctx = f"{phase_family}_week{week_in_phase}"
    easy_range = _format_pace_range(threshold_pace_seconds + 35, threshold_pace_seconds + 55)
    suffix = ""
    structure_note = ""  # 特殊结构指令（动作库检索时作为 hints）

    if long_plan:
        if phase_family == "taper":
            taper_step = max(0, week_index - int(total_weeks or week_index) + 4)
            minutes = max(50, base_minutes - 26 - taper_step * 7)
            if taper_step >= 3:
                structure_note = "后半程保持轻松顺畅，不再追求专项配速"
            else:
                structure_note = "前半程轻松，后20分钟保持顺畅节奏"
        else:
            cap = 150 if total_weeks >= 24 else 135
            if race_type == "marathon":
                cap = 185 if total_weeks >= 24 else 170
            minutes = min(cap, base_minutes + week_index * 3)
            if any(kw in mesocycle.name for kw in ("巅峰", "Peak", "peak")):
                minutes = min(cap, base_minutes + 35 + (week_index % 3) * 5)
            phase_weeks = mesocycle.weeks
            load_level = _phase_to_load_level(mesocycle.name, week_in_phase, phase_weeks)
            if load_level == "low" and week_index > 1:
                minutes = max(base_minutes + 6, minutes - 10)
                structure_note = "恢复性长距离，保留余力"
            elif week_index % 5 == 0:
                structure_note = "中段加入马拉松配速块"
            elif week_index % 4 == 0:
                structure_note = "最后20分钟逐步加速到稳态配速"
            elif week_index % 3 == 0:
                structure_note = "前70%轻松，后30%提高到稳定有氧上沿"
            elif race_type == "marathon":
                structure_note = "后段保持稳定有氧并练习补给"
            else:
                structure_note = "最后15分钟接近半马专项舒适配速"
    else:
        if any(kw in mesocycle.name for kw in ("减量", "调整", "Taper", "taper")):
            minutes = max(60, base_minutes - 20)
        elif race_type == "half_marathon":
            minutes = min(125, base_minutes + week_index * 2)
            structure_note = "最后15分钟接近半马专项舒适配速"
        elif race_type == "marathon":
            minutes = min(160, base_minutes + 15 + week_index * 4)
            structure_note = "后段保持稳定有氧并练习补给"
            # C2: 短周期 (<8周) 强制包含 MP 段——Daniels M 跑短周期适配 (B 级外推)
            if total_weeks < 8 and phase_family not in ("intro", "base_1", "taper"):
                structure_note += "；中后段加入2-3km马拉松配速段 (短周期保守适配, Daniels B级外推)"
        elif any(kw in mesocycle.name for kw in ("巅峰", "Peak", "peak")):
            minutes = min(150, base_minutes + 15)
        else:
            minutes = min(145, base_minutes + week_index * 3)

    # 将特殊结构指令合并到 intensity_hint，便于动作库检索时做语义匹配
    pace_hint = f"配速{easy_range}/km"
    if structure_note:
        pace_hint = f"{pace_hint}；{structure_note}"

    # 长距离跑的训练笔记：合并动态计算信息和结构指令
    notes_parts = [f"长距离跑，公式计算目标时间约{minutes}分钟"]
    if structure_note:
        notes_parts.append(structure_note)
    if race_type == "marathon":
        notes_parts.append("全马目标：关注补给策略执行")
    elif race_type == "half_marathon":
        notes_parts.append("半马目标：关注后半程配速保持")

    return SessionConstraint(
        workout_type="long_run",
        training_type_display="长距离",
        zone_range="Z2-Z3",
        target_duration_min=minutes,
        phase_context=phase_ctx,
        intensity_hint=pace_hint,
        notes="；".join(notes_parts),
    )


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
    """按训练类型和周跑量目标，返回主课训练距离 (km)。

    优先从文献规则动态计算距离比例，失败时回退到教练通用实践字典。
    """
    if training_type in ("休息", ""):
        return 0.0
    # 优先尝试文献规则动态计算
    fraction = _distance_fraction_from_literature(training_type, target_km)
    # 文献规则不可用时使用教练实践 fallback
    if fraction is None:
        fraction = _TRAINING_DISTANCE_FRACTIONS_FALLBACK.get(training_type, (0.10, 0.18))
    if ratio == "lower":
        return round(target_km * fraction[0], 1)
    elif ratio == "upper":
        return round(target_km * fraction[1], 1)
    return round(target_km * (fraction[0] + fraction[1]) / 2, 1)


def _easy_km_text(km: float, pace_range: str) -> str:
    return f"{km:.1f}km，配速{pace_range}/km"


def _duration_bounds_for_training_type(training_type: str) -> Optional[Tuple[int, int]]:
    try:
        from marathon_qa_assistant.core.workout_constraints import WORKOUT_CONSTRAINTS
    except Exception:
        return None
    constraint = WORKOUT_CONSTRAINTS.get(str(training_type or ""))
    if not constraint:
        return None
    return int(constraint.min_minutes), int(constraint.max_minutes)


def _cap_session_duration_min(training_type: str, minutes: int) -> int:
    bounds = _duration_bounds_for_training_type(training_type)
    if not bounds:
        return int(minutes)
    lower, upper = bounds
    return max(lower, min(int(minutes), upper))


def _clamp_main_set_minutes(main_set: str, training_type: str) -> str:
    bounds = _duration_bounds_for_training_type(training_type)
    if not bounds:
        return main_set
    match = re.search(r"(\d+)\s*(分钟|min)", str(main_set or ""), flags=re.IGNORECASE)
    if not match:
        return main_set
    lower, upper = bounds
    current = int(match.group(1))
    clamped = max(lower, min(current, upper))
    if clamped == current:
        return main_set
    return f"{main_set[:match.start(1)]}{clamped}{main_set[match.end(1):]}"


def _cap_low_intensity_main_km(training_type: str, main_km: float) -> float:
    value = float(main_km or 0.0)
    if value <= 0:
        return 0.0
    if training_type == "恢复跑":
        return round(min(max(value, _RECOVERY_MAIN_KM_MIN), _RECOVERY_MAIN_KM_CAP), 1)
    if training_type in ("轻松跑", ""):
        return round(min(max(value, _EASY_MAIN_KM_MIN), _EASY_MAIN_KM_CAP), 1)
    return round(value, 1)


def _strip_hmp_workout_prefix(main_set: Any) -> Tuple[str, str]:
    text = str(main_set or "").strip()
    match = re.match(r"^(hm_[a-z0-9_]+)\s*[：:]\s*(.*)$", text, flags=re.IGNORECASE)
    if not match:
        return text, ""
    return match.group(2).strip() or text, match.group(1)


def _clean_hmp_ids_for_frontend(plan_dict: Dict[str, Any]) -> None:
    for week in plan_dict.get("week_plans") or []:
        if not isinstance(week, dict):
            continue
        for day in week.get("days") or []:
            if not isinstance(day, dict):
                continue
            cleaned, workout_id = _strip_hmp_workout_prefix(day.get("main_set"))
            if workout_id:
                day["main_set"] = cleaned
                day["workout_type"] = day.get("workout_type") or workout_id


def _fixed_km_for_training_type(training_type: str, role: str) -> Tuple[float, float]:
    """按训练类型和角色返回热身/冷身固定距离 (km)。

    优先从动作库动态获取热身/冷身建议，不可用时回退到教练实践硬编码值。
    """
    result = _warmup_cooldown_from_action_library(training_type)
    if result.get("source") == "action_library":
        # 动作库提供了可解析的距离值，直接使用
        return float(result.get("warmup_km", 1.5)), float(result.get("cooldown_km", 1.0))

    # 动作库无匹配或无法解析 — 回退到教练实践硬编码值
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
    easy_pace_range: str,
    is_taper_block: bool = False,
    distance_based_long_run: bool = False,
    max_long_run_km: Optional[float] = None,
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

    if max_long_run_km is not None:
        long_km = round(min(max(float(long_km or 0.0), _LONG_RUN_MAIN_KM_MIN), float(max_long_run_km)), 1)
    elif long_km > 0:
        long_km = round(max(float(long_km or 0.0), _LONG_RUN_MAIN_KM_MIN), 1)
    primary_km = _cap_low_intensity_main_km(primary_type, primary_km)
    secondary_km = _cap_low_intensity_main_km(secondary_type, secondary_km)
    easy_km_each = _cap_low_intensity_main_km("轻松跑", easy_km_each)
    easy_km_by_day = {
        day: _cap_low_intensity_main_km("轻松跑", km)
        for day, km in easy_km_by_day.items()
    }

    days: List[DayPlan] = []
    for day in WEEKDAY_ORDER:
        if day == long_run_day:
            wu, cd = 2.0, 1.5
            long_run_text = long_run_main_set
            if distance_based_long_run and "分钟" in str(long_run_text):
                long_run_text = f"{long_km:.1f}km轻松长距离，配速{easy_pace_range}/km"
            days.append(DayPlan(
                day=day, training_type="长距离",
                warmup="慢跑15分钟 + 动态拉伸",
                main_set=long_run_text,
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
                main_set=_easy_km_text(easy_main_km, easy_pace_range),
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
    training_capacity_envelope: Optional[Dict[str, Any]] = None,
) -> Tuple[List[DayPlan], float, Dict[str, Any]]:
    race_type = _resolve_goal_race_type(profile.get("goal"))
    threshold_pace_seconds = _resolve_threshold_pace_seconds(profile, race_type)
    base_weekly_mileage = coerce_float_from_unit_text(profile.get("weekly_mileage"), default=40.0) or 40.0
    max_session_minutes = coerce_int_from_unit_text(profile.get("max_session_minutes"), default=90) or 90
    primary_quality_day, secondary_quality_day, long_run_day = _resolve_training_slots(available_days)
    week_in_phase = week_index - mesocycle.start_week + 1
    weekly_volume_km = _build_weekly_volume(base_weekly_mileage, week_index, blocks)
    load_ceiling = training_capacity_envelope.get("load_ceiling") if isinstance(training_capacity_envelope, dict) else {}
    if isinstance(load_ceiling, dict) and load_ceiling.get("weekly_load_cap_km") is not None:
        weekly_volume_km = min(float(weekly_volume_km), float(load_ceiling.get("weekly_load_cap_km")))
    max_long_run_km = None
    if isinstance(load_ceiling, dict) and load_ceiling.get("max_long_run_km") is not None:
        try:
            max_long_run_km = float(load_ceiling.get("max_long_run_km"))
        except (TypeError, ValueError):
            max_long_run_km = None

    primary_constraint = _build_quality_session(
        mesocycle, week_index, threshold_pace_seconds, race_type, total_weeks
    )
    secondary_constraint = _build_secondary_session(
        mesocycle,
        week_index,
        threshold_pace_seconds,
        mesocycle.max_high_intensity_per_week >= 2,
        total_weeks,
    )
    long_run_constraint = _build_long_run_main_set(
        mesocycle,
        week_index,
        min(120, max(80, max_session_minutes)),
        threshold_pace_seconds,
        race_type,
        total_weeks,
    )

    # 用约束从动作库检索具体课表候选项，不可用时回退到约束字段生成的文本描述
    primary_main_set, _ = _resolve_main_set_from_constraint(primary_constraint)
    secondary_main_set, _ = _resolve_main_set_from_constraint(secondary_constraint)
    long_run_main_set, _ = _resolve_main_set_from_constraint(long_run_constraint)

    primary_type = primary_constraint.training_type_display
    primary_note = primary_constraint.notes
    secondary_type = secondary_constraint.training_type_display
    secondary_note = secondary_constraint.notes
    hmp_week_decision: Dict[str, Any] = {}
    distance_based_long_run = False
    if hm_protocol_context and hm_protocol_context.get("active") and race_type == "half_marathon":
        phase_id = _hm_protocol_phase_id(mesocycle, week_index, total_weeks, hm_protocol_context) or ""
        selected = hm_protocol_context.get("selected_archetype") or {}
        pace_calibration = hm_protocol_context.get("pace_calibration") or {}
        # 当前阶段分类 + 训练总课次，用于文献约束驱动强度课数量
        current_phase_family = _phase_family(mesocycle.name)
        total_training_sessions = len(available_days)

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
                recent_four_week_mileage_km=hm_protocol_context.get("input_recent_four_week_mileage_km"),
                recent_marathon=bool(hm_protocol_context.get("recent_marathon")),
                fatigue_or_injury=_profile_flag(profile, "injury_or_fatigue", "fatigue", "injury"),
                speed_calibration_available=bool(pace_calibration.get("speed_calibration_available")),
                phase_family=current_phase_family,
                total_training_sessions=total_training_sessions,
            ),
        )
        for session in hmp_week_decision.get("sessions") or []:
            if not isinstance(session, dict):
                continue
            role = str(session.get("role") or "")
            if role == "primary":
                primary_type = str(session.get("training_type") or primary_type)
                primary_main_set = str(session.get("main_set") or primary_main_set)
                primary_note = str(session.get("note") or primary_note)
            elif role == "secondary" and secondary_quality_day and len(available_days) >= 4:
                secondary_type = str(session.get("training_type") or secondary_type)
                secondary_main_set = str(session.get("main_set") or secondary_main_set)
                secondary_note = str(session.get("note") or secondary_note)
            elif role == "long_run" and _phase_family(mesocycle.name) != "taper":
                long_run_main_set = str(session.get("main_set") or long_run_main_set)
        capacity_budget = hmp_week_decision.get("capacity_budget") or {}
        if capacity_budget.get("volume_basis") == "recent_four_week_mileage":
            effective_volume = capacity_budget.get("effective_weekly_volume_km")
            if effective_volume:
                weekly_volume_km = min(float(weekly_volume_km), float(effective_volume))
                distance_based_long_run = True
        # 低频训练者长距离负荷约束 (来源: Pfitzinger 低频计划模板 + Gabbett ACWR)
        if total_training_sessions <= 4 and secondary_quality_day and not capacity_budget.get("volume_basis"):
            secondary_type = "轻松跑"
            secondary_main_set = _easy_km_text(8.0, _format_pace_range(threshold_pace_seconds + 45, threshold_pace_seconds + 65))
            secondary_note = "周训练≤4天且含长距离课，强度课上限保持1节（Pfitzinger/Gabbett 约束）。本次课降级为轻松跑。"
        elif capacity_budget.get("quality_sessions_max") == 1 and secondary_quality_day:
            secondary_type = "轻松跑"
            secondary_main_set = _easy_km_text(8.0, _format_pace_range(threshold_pace_seconds + 45, threshold_pace_seconds + 65))
            secondary_note = "近4周跑量或恢复约束触发容量预算，本次次课降级为轻松跑。"

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
        easy_pace_range=_format_pace_range(threshold_pace_seconds + 45, threshold_pace_seconds + 65),
        is_taper_block=is_taper_block,
        distance_based_long_run=distance_based_long_run or max_long_run_km is not None,
        max_long_run_km=max_long_run_km,
    )
    actual_weekly_volume_km = round(sum(day.total_km for day in days), 1)
    return days, min(float(weekly_volume_km), actual_weekly_volume_km), hmp_week_decision


def _attach_evidence_grades_to_plan(plan_dict: Dict[str, Any]) -> None:
    """为计划中每天附证据来源/等级（A/B/C），供前端诚实展示每节训练课的依据强度。

    A=同行评审教材（Daniels/Pfitzinger/Billat 等）、B=论文、C=教练实践（无同行评审）。
    数据来自 WORKOUT_CONSTRAINTS 的 source/source_grade 字段。
    """
    try:
        from marathon_qa_assistant.core.workout_constraints import WORKOUT_CONSTRAINTS
    except Exception:
        return
    for week in plan_dict.get("week_plans") or []:
        if not isinstance(week, dict):
            continue
        for day in week.get("days") or []:
            if not isinstance(day, dict):
                continue
            constraint = WORKOUT_CONSTRAINTS.get(str(day.get("training_type") or ""))
            if constraint:
                day["evidence_source"] = constraint.source
                day["evidence_grade"] = constraint.source_grade


def build_structured_training_plan_skeleton(
    query: str,
    profile: Dict[str, Any],
    requested_weeks: Optional[int] = None,
    training_capacity_envelope: Optional[Dict[str, Any]] = None,
    framework: Optional[str] = None,
) -> Dict[str, Any]:
    # framework 预留：教练/训练框架（如 "Daniels"/"Hansen"/"80_20"），当前未实现分支，
    # 留作未来"多框架对比"功能的扩展点（需先在 KB 标注 framework + 补对应文献）。None = 现有默认逻辑。
    profile = merge_plan_profile_overrides(query, profile)
    plan_context = align_plan_duration_context(query, profile)
    aligned_profile = dict(plan_context["aligned_profile"])
    total_weeks = int(plan_context["resolved_plan_weeks"])
    available_days = _normalize_available_days(aligned_profile.get("available_days"))
    weekly_structure_constraints = _parse_weekly_structure_constraints(query)
    race_type = _resolve_goal_race_type(aligned_profile.get("goal"))

    # RAG + LLM 周期化顾问：阶段模型选择决策
    periodization_advisory = None
    try:
        from marathon_qa_assistant.core.periodization_advisor import (  # noqa: E402
            get_periodization_advisory,
        )
        periodization_advisory = get_periodization_advisory(
            aligned_profile, total_weeks, race_type,
        )
    except Exception as exc:
        logger.debug("periodization advisor 调用失败，降级到确定性规则: %s", exc)

    macrocycle = _resolve_macrocycle(aligned_profile, total_weeks, advisory=periodization_advisory)
    base_weekly_mileage = coerce_float_from_unit_text(aligned_profile.get("weekly_mileage"), default=40.0) or 40.0
    blocks = resolve_4week_blocks(total_weeks, base_weekly_mileage)
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
            training_capacity_envelope,
        )
        if week_index == 1:
            days = _apply_weekly_structure_constraints(days, weekly_structure_constraints, available_days, aligned_profile)
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
            performance_calibration=(
                hm_protocol_context.get("pace_calibration") if hm_protocol_context.get("active") else {}
            ),
        ),
        phase_summary=phase_summary,
        week_plans=week_plans,
        first_week_actions=_build_first_week_actions(week_plans[0]) if week_plans else [],
    )
    plan_dict = plan.to_dict()
    _attach_evidence_grades_to_plan(plan_dict)
    if isinstance(training_capacity_envelope, dict) and training_capacity_envelope:
        plan_dict["training_capacity_envelope"] = training_capacity_envelope
        plan_dict["s_and_c_constraints"] = training_capacity_envelope
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
        _clean_hmp_ids_for_frontend(plan_dict)
    if weekly_structure_constraints.get("required_workouts") or weekly_structure_constraints.get("forbidden_workouts") or weekly_structure_constraints.get("required_rest_days") or weekly_structure_constraints.get("weekly_frequency"):
        plan_dict["weekly_structure_constraints"] = weekly_structure_constraints
        plan_dict["weekly_structure_validation"] = _validate_weekly_structure_constraints(plan_dict, weekly_structure_constraints)
    if periodization_advisory is not None and periodization_advisory.llm_generated:
        plan_dict["periodization_advisory"] = {
            "model_tier": periodization_advisory.model_tier,
            "needs_introductory": periodization_advisory.needs_introductory,
            "intro_weeks": periodization_advisory.intro_weeks,
            "phase_adjustments": periodization_advisory.phase_adjustments,
            "reasoning": periodization_advisory.reasoning,
            "evidence_sources": periodization_advisory.evidence_sources,
            "llm_generated": True,
        }
    return plan_dict


__all__ = ["build_structured_training_plan_skeleton"]
