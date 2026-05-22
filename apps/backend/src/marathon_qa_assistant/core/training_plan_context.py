from __future__ import annotations

from datetime import date, datetime
import math
import re
from typing import Any, Dict, List, Optional, Tuple


_DIRECT_DURATION_MAP = {
    "1个月": 4,
    "一个月": 4,
    "2个月": 8,
    "二个月": 8,
    "两个月": 8,
    "3个月": 12,
    "三个月": 12,
    "半年": 24,
}

_CN_DIGITS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}

PLAN_PROFILE_OVERRIDE_FIELDS = (
    "goal",
    "current_half_time",
    "target_half_time",
    "target_race_date",
    "weekly_mileage",
    "recent_four_week_mileage",
    "last_month_mileage",
    "available_days",
    "target_pace",
    "injury_or_fatigue",
    "injury",
    "recovery_state",
)

_PLAN_PROFILE_FIELD_ALIASES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("recent_four_week_mileage", ("recent_four_week_mileage", "recent_4_week_mileage", "近4周平均周跑量", "近四周平均周跑量", "上个月月跑量", "最近四周跑量")),
    ("last_month_mileage", ("last_month_mileage", "last_month_weekly_mileage", "上月跑量", "上个月跑量", "最近一个月跑量")),
    ("target_race_date", ("target_race_date", "目标比赛日期", "比赛日期", "目标赛事日期", "赛事日期", "比赛时间")),
    ("weekly_mileage", ("weekly_mileage", "周跑量", "平均周跑量", "每周跑量")),
    ("available_days", ("available_days", "可训练日", "可跑步日", "训练日", "每周训练日")),
    ("injury_or_fatigue", ("injury_or_fatigue", "伤病或疲劳", "伤病/疲劳", "疲劳或伤病", "伤病疲劳", "伤病", "疲劳")),
    ("injury", ("injury", "injury_status", "伤情", "伤痛", "疼痛")),
    ("recovery_state", ("recovery_state", "recovery", "恢复状态", "恢复情况")),
    ("current_half_time", ("current_half_time", "current_half_marathon_time", "当前半马成绩", "当前半程成绩", "当前半马时间", "半马PB", "半马pb")),
    ("target_half_time", ("target_half_time", "target_half_marathon_time", "half_marathon_goal_time", "目标半马成绩", "目标半程成绩", "目标半马时间", "半马目标成绩")),
    ("target_pace", ("target_pace", "目标配速", "目标成绩", "目标时间", "target_time")),
    ("goal", ("goal", "目标", "训练目标")),
)

_NEGATIVE_HEALTH_VALUES = {"", "无", "没有", "暂无", "否", "none", "no", "n", "false", "0", "无伤病", "无疲劳"}
_NEGATIVE_HEALTH_FIELDS = {"injury_or_fatigue", "injury", "fatigue"}
_AVERAGE_WEEKS_PER_MONTH = 4.345


def _clamp_weeks(value: int) -> int:
    return max(1, min(int(value), 26))


def _normalize_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^[\-*•\s]+", "", text)
    text = re.sub(r"[\s_／/\\-]+", "", text)
    return text


def _field_for_label(label: str) -> Optional[str]:
    normalized = _normalize_label(label)
    if not normalized:
        return None
    for field, aliases in _PLAN_PROFILE_FIELD_ALIASES:
        for alias in aliases:
            alias_key = _normalize_label(alias)
            if normalized == alias_key or normalized.endswith(alias_key):
                return field
    return None


def _split_labeled_profile_line(line: str) -> Optional[Tuple[str, str]]:
    cleaned = str(line or "").strip()
    if not cleaned:
        return None
    cleaned = re.sub(r"^[\-*•\s]+", "", cleaned)
    match = re.match(r"([^:：=]{1,32})\s*[:：=]\s*(.+)$", cleaned)
    if not match:
        return None
    field = _field_for_label(match.group(1))
    if not field:
        return None
    value = match.group(2).strip()
    return field, value


def extract_plan_profile_overrides(query: str) -> Dict[str, Any]:
    """从前端 prompt 或显式请求中提取本轮计划生成应优先采用的画像字段。"""
    overrides: Dict[str, Any] = {}
    for raw_line in str(query or "").splitlines():
        parsed = _split_labeled_profile_line(raw_line)
        if not parsed:
            continue
        field, value = parsed
        if not value:
            continue
        if field in _NEGATIVE_HEALTH_FIELDS and _normalize_label(value) in _NEGATIVE_HEALTH_VALUES:
            overrides[field] = ""
        else:
            overrides[field] = value
    return overrides


def merge_plan_profile_overrides(query: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    """合并画像时让本轮显式请求覆盖旧画像污染，但不写回持久画像。"""
    merged = dict(profile or {})
    overrides = extract_plan_profile_overrides(query)
    if overrides:
        merged.update(overrides)
        derived_weekly_from_month = _weekly_mileage_from_monthly_mileage(overrides.get("last_month_mileage"))
        if "last_month_mileage" in overrides and "recent_four_week_mileage" not in overrides:
            merged["recent_four_week_mileage"] = derived_weekly_from_month or overrides["last_month_mileage"]
        if "last_month_mileage" in overrides and "weekly_mileage" not in overrides and derived_weekly_from_month:
            merged["weekly_mileage"] = derived_weekly_from_month
        explicit_fields: List[str] = list(merged.get("_explicit_plan_profile_fields") or [])
        derived_fields: List[str] = []
        if "last_month_mileage" in overrides and "recent_four_week_mileage" not in overrides:
            derived_fields.append("recent_four_week_mileage")
        if "last_month_mileage" in overrides and "weekly_mileage" not in overrides and derived_weekly_from_month:
            derived_fields.append("weekly_mileage")
        for field in list(overrides) + derived_fields:
            if field not in explicit_fields:
                explicit_fields.append(field)
        merged["_explicit_plan_profile_fields"] = explicit_fields
        if "target_race_date" in overrides and "plan_duration_weeks" not in overrides:
            merged.pop("plan_duration_weeks", None)
    return merged


def _weekly_mileage_from_monthly_mileage(value: Any) -> Optional[str]:
    monthly = coerce_float_from_unit_text(value)
    if monthly is None or monthly <= 0:
        return None
    weekly = monthly / _AVERAGE_WEEKS_PER_MONTH
    rounded = round(weekly, 1)
    number = int(rounded) if rounded.is_integer() else rounded
    return f"{number} km"


def coerce_float_from_unit_text(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return default
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return default
    try:
        return float(match.group(0))
    except ValueError:
        return default


def coerce_int_from_unit_text(value: Any, default: Optional[int] = None) -> Optional[int]:
    parsed = coerce_float_from_unit_text(value)
    if parsed is None:
        return default
    return int(parsed)


def _coerce_int(value: Any) -> Optional[int]:
    parsed = coerce_int_from_unit_text(value)
    if parsed is None:
        return None
    return _clamp_weeks(parsed)


def _parse_chinese_number(token: str) -> Optional[int]:
    if not token:
        return None
    token = token.strip()
    if not token:
        return None
    if token.isdigit():
        return int(token)
    if token in _CN_DIGITS:
        return _CN_DIGITS[token]
    if token == "十":
        return 10
    if "十" in token:
        left, right = token.split("十", 1)
        tens = 1 if not left else _CN_DIGITS.get(left)
        ones = 0 if not right else _CN_DIGITS.get(right)
        if tens is None or ones is None:
            return None
        return tens * 10 + ones
    return None


def parse_requested_weeks(query: str) -> Optional[int]:
    text = str(query or "").strip().replace("週", "周")
    if not text:
        return None

    for keyword, weeks in _DIRECT_DURATION_MAP.items():
        if keyword in text:
            return weeks

    labeled_week_match = re.search(
        r"(?:计划周期|训练周期|备赛周期|周期)\s*[:：]?\s*([0-9一二两三四五六七八九十]+)(?!\s*(?:天|日|公里|km|千米|分钟|min))",
        text,
        flags=re.IGNORECASE,
    )
    if labeled_week_match:
        value = _parse_chinese_number(labeled_week_match.group(1))
        if value is not None:
            return _clamp_weeks(value)

    for week_match in re.finditer(r"(?:第)?\s*([0-9一二两三四五六七八九十]+)\s*周", text):
        prefix = text[max(0, week_match.start() - 3):week_match.start()]
        if any(marker in prefix for marker in ("近", "最近", "过去")):
            continue
        value = _parse_chinese_number(week_match.group(1))
        if value is not None:
            return _clamp_weeks(value)

    month_match = re.search(r"([0-9一二两三四五六七八九十]+)\s*个?\s*月", text)
    if month_match:
        value = _parse_chinese_number(month_match.group(1))
        if value is not None:
            return _clamp_weeks(value * 4)

    english_week_match = re.search(
        r"\b([0-9]+)\s*(?:week|weeks|wk|wks)\b",
        text,
        flags=re.IGNORECASE,
    )
    if english_week_match:
        return _clamp_weeks(int(english_week_match.group(1)))

    return None


def derive_plan_duration_weeks(target_race_date: Any) -> Optional[int]:
    text = str(target_race_date or "").strip().replace("週", "周")
    if not text or text.lower() in {"none", "null", "未设置", "无比赛"}:
        return None

    if text in _DIRECT_DURATION_MAP:
        return _DIRECT_DURATION_MAP[text]

    week_match = re.search(r"([0-9一二两三四五六七八九十]+)\s*个?\s*周", text)
    if week_match:
        value = _parse_chinese_number(week_match.group(1))
        if value is not None:
            return _clamp_weeks(value)

    month_match = re.search(r"([0-9一二两三四五六七八九十]+)\s*个?\s*月", text)
    if month_match:
        value = _parse_chinese_number(month_match.group(1))
        if value is not None:
            return _clamp_weeks(value * 4)

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%d/%m/%Y"):
        try:
            parsed = datetime.strptime(text, fmt).date()
            delta_days = (parsed - date.today()).days
            return _clamp_weeks(max(1, math.ceil(delta_days / 7)))
        except ValueError:
            continue

    return None


def align_plan_duration_context(query: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    requested_weeks = parse_requested_weeks(query)
    target_race_weeks = derive_plan_duration_weeks((profile or {}).get("target_race_date"))
    stored_plan_weeks = _coerce_int((profile or {}).get("plan_duration_weeks"))
    explicit_fields = set((profile or {}).get("_explicit_plan_profile_fields") or [])

    if requested_weeks is not None:
        resolved_plan_weeks = requested_weeks
        resolved_from = "query"
    elif target_race_weeks is not None and "target_race_date" in explicit_fields:
        resolved_plan_weeks = target_race_weeks
        resolved_from = "target_race_date"
    elif stored_plan_weeks is not None:
        resolved_plan_weeks = stored_plan_weeks
        resolved_from = "profile"
    elif target_race_weeks is not None:
        resolved_plan_weeks = target_race_weeks
        resolved_from = "target_race_date"
    else:
        resolved_plan_weeks = 12
        resolved_from = "default"

    aligned_profile = dict(profile or {})
    aligned_profile["plan_duration_weeks"] = _clamp_weeks(resolved_plan_weeks)

    return {
        "requested_weeks": requested_weeks,
        "target_race_weeks": target_race_weeks,
        "stored_plan_weeks": stored_plan_weeks,
        "resolved_plan_weeks": aligned_profile["plan_duration_weeks"],
        "resolved_from": resolved_from,
        "aligned_profile": aligned_profile,
    }
