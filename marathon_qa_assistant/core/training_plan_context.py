from __future__ import annotations

from datetime import date, datetime
import math
import re
from typing import Any, Dict, Optional


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


def _clamp_weeks(value: int) -> int:
    return max(1, min(int(value), 26))


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

    if requested_weeks is not None:
        resolved_plan_weeks = requested_weeks
        resolved_from = "query"
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
