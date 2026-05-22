from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from marathon_qa_assistant.core.half_marathon_protocol import build_hmp_zone_pace_table, format_pace
from marathon_qa_assistant.core.training_plan_context import coerce_float_from_unit_text


HALF_MARATHON_KM = 21.0975


@dataclass(frozen=True)
class ProfileGap:
    field: str
    label: str
    reason: str
    severity: str = "warning"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def detect_half_marathon_profile_gaps(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    gaps: List[ProfileGap] = []
    if _target_half_time_seconds(profile) is None:
        gaps.append(ProfileGap(
            field="half_marathon_goal_or_pb",
            label="目标半马成绩或半马PB",
            reason="缺少目标半马成绩时，HMP百分比只能回退到T-Pace估算。",
        ))
    if _race_time_seconds(profile, _FIVE_K_KEYS) is None:
        gaps.append(ProfileGap(
            field="current_5k_time",
            label="当前5K成绩",
            reason="105-110% HMP速度课需要当前短距离能力校准。",
        ))
    if _race_time_seconds(profile, _TEN_K_KEYS) is None:
        gaps.append(ProfileGap(
            field="current_10k_time",
            label="当前10K成绩",
            reason="105% HMP中长间歇更适合用当前8K/10K能力校准。",
        ))
    if _safe_float(profile.get("weekly_mileage")) is None:
        gaps.append(ProfileGap(
            field="weekly_mileage",
            label="当前周跑量",
            reason="缺少周跑量时，95% HMP长距离快速跑和Sub-70跑量缩放不稳定。",
        ))
    if not str(profile.get("available_days") or "").strip() and not isinstance(profile.get("available_days"), list):
        gaps.append(ProfileGap(
            field="available_days",
            label="可训练日",
            reason="缺少可训练日时，关键课恢复间隔只能按默认结构安排。",
        ))
    if not _has_recovery_state(profile):
        gaps.append(ProfileGap(
            field="fatigue_injury_recovery",
            label="疲劳/伤病/恢复状态",
            reason="缺少恢复状态时，导入期和自动降级策略会偏保守。",
            severity="info",
        ))
    return [gap.to_dict() for gap in gaps]


def build_half_marathon_pace_calibration(profile: Dict[str, Any]) -> Dict[str, Any]:
    target_half_time_seconds, target_source = _target_half_time_detail(profile)
    target_seconds = round(target_half_time_seconds / HALF_MARATHON_KM) if target_half_time_seconds else None
    target_pace_seconds, target_pace_source = _target_pace_seconds_detail(profile)
    if target_pace_seconds is not None:
        target_seconds = target_pace_seconds
        target_source = target_pace_source
        if target_half_time_seconds is None:
            target_half_time_seconds = round(target_pace_seconds * HALF_MARATHON_KM)
    t_pace_seconds = _pace_seconds(profile.get("t_pace"))
    source_estimates = _current_hm_estimates(profile)
    current_seconds = _choose_current_hmp(source_estimates)
    current_half_time_seconds, current_source = _current_half_time_detail(profile)
    fallback_used = False

    if target_seconds is None and t_pace_seconds is not None:
        target_seconds = t_pace_seconds
        fallback_used = True
    if current_seconds is None and t_pace_seconds is not None:
        current_seconds = t_pace_seconds
        fallback_used = True

    status = "ready"
    if current_seconds is None or target_seconds is None:
        status = "insufficient"
    elif current_seconds > target_seconds * 1.04:
        status = "ambitious_target"
    elif current_seconds < target_seconds * 0.96:
        status = "current_faster_than_target"

    speed_calibration_available = (
        _race_time_seconds(profile, _FIVE_K_KEYS) is not None
        or _race_time_seconds(profile, _TEN_K_KEYS) is not None
    )

    time_gap_seconds = (
        current_half_time_seconds - target_half_time_seconds
        if current_half_time_seconds is not None and target_half_time_seconds is not None
        else None
    )
    source_fields = [item for item in (current_source, target_source) if item]
    decision_reason = _calibration_decision_reason(status, current_seconds, target_seconds)

    return {
        "status": status,
        "speed_calibration_available": speed_calibration_available,
        "fallback_used": fallback_used,
        "source_fields": source_fields,
        "decision_reason": decision_reason,
        "target_half_time_seconds": target_half_time_seconds,
        "target_half_time": _format_duration(target_half_time_seconds),
        "target_hmp_seconds_per_km": target_seconds,
        "target_hmp_pace": format_pace(target_seconds) if target_seconds else "",
        "current_half_time_seconds": current_half_time_seconds,
        "current_half_time": _format_duration(current_half_time_seconds),
        "current_hmp_seconds_per_km": current_seconds,
        "current_hmp_pace": format_pace(current_seconds) if current_seconds else "",
        "gap_seconds_per_km": (
            round(float(current_seconds - target_seconds), 1)
            if current_seconds is not None and target_seconds is not None
            else None
        ),
        "time_gap_seconds": time_gap_seconds,
        "improvement_percent": (
            round((float(time_gap_seconds) / current_half_time_seconds) * 100, 1)
            if time_gap_seconds is not None and current_half_time_seconds
            else None
        ),
        "target_zone_table": build_hmp_zone_pace_table(target_seconds) if target_seconds else [],
        "current_zone_table": build_hmp_zone_pace_table(current_seconds) if current_seconds else [],
        "source_estimates": source_estimates,
        "notes": _calibration_notes(status, speed_calibration_available, fallback_used),
    }


def _calibration_notes(status: str, speed_calibration_available: bool, fallback_used: bool) -> List[str]:
    notes: List[str] = []
    if status == "insufficient":
        notes.append("缺少目标半马成绩、当前短距离成绩或T-Pace，HMP配速表暂不完整。")
    if status == "ambitious_target":
        notes.append("目标HMP快于当前能力估计，专项课应优先使用当前能力配速并保守推进。")
    if not speed_calibration_available:
        notes.append("缺少当前5K/10K成绩，105-110% HMP速度课应按体感10K强度保守执行。")
    if fallback_used:
        notes.append("部分HMP估计使用T-Pace兜底，建议补充比赛成绩提高精度。")
    return notes


def _calibration_decision_reason(status: str, current_seconds: Optional[int], target_seconds: Optional[int]) -> str:
    if current_seconds is None or target_seconds is None:
        return "缺少当前能力或目标成绩，暂不能完成半马目标配速校准。"
    if status == "ambitious_target":
        return "目标半马配速快于当前能力估计，关键课应以当前能力为下限并逐步贴近目标HMP。"
    if status == "current_faster_than_target":
        return "当前能力估计已经快于目标半马配速，可复核目标是否过低或进入更高目标。"
    return "当前能力与目标半马配速差距在可校准范围内，可进入HMP专项推进。"


_FIVE_K_KEYS = ("current_5k", "current_5k_time", "five_k_time", "pb_5k", "recent_5k")
_TEN_K_KEYS = ("current_10k", "current_10k_time", "ten_k_time", "pb_10k", "recent_10k")
_HALF_KEYS = ("current_half", "current_half_time", "half_marathon_time", "pb_half", "half_pb", "recent_half")


def _target_half_time_seconds(profile: Dict[str, Any]) -> Optional[int]:
    target_seconds, _source = _target_half_time_detail(profile)
    if target_seconds:
        return round(target_seconds / HALF_MARATHON_KM)
    target_pace_seconds, _pace_source = _target_pace_seconds_detail(profile)
    return target_pace_seconds


def _target_half_time_detail(profile: Dict[str, Any]) -> Tuple[Optional[int], str]:
    for key in ("target_half_time", "half_marathon_goal_time", "goal_time", "target_time"):
        parsed = _duration_seconds(profile.get(key), prefer_hours_for_short_colon=True)
        if parsed:
            return parsed, key

    target_pace_text = str(profile.get("target_pace") or "")
    if _looks_like_half_time_text(target_pace_text) or _looks_like_standalone_race_duration(target_pace_text):
        parsed = _duration_seconds(target_pace_text, prefer_hours_for_short_colon=True)
        if parsed:
            return parsed, "target_pace"

    goal_text = str(profile.get("goal") or "")
    marked_target = _target_marked_duration_seconds(goal_text)
    if marked_target:
        return marked_target, "goal"

    parsed = _duration_seconds(goal_text, prefer_hours_for_short_colon=_looks_like_half_time_text(goal_text))
    if parsed and ("半马" in goal_text or "半程" in goal_text or "half" in goal_text.lower()):
        return parsed, "goal"

    compact_match = re.search(r"(?:半马|半程|half)\s*(\d{2,3})\b", goal_text, flags=re.IGNORECASE)
    if compact_match:
        raw = int(compact_match.group(1))
        if raw < 60:
            return None, ""
        if raw < 100:
            seconds = raw * 60
        else:
            hours = raw // 100
            minutes = raw % 100
            seconds = (hours * 60 + minutes) * 60
        return seconds, "goal"

    return None, ""


def _target_pace_seconds_detail(profile: Dict[str, Any]) -> Tuple[Optional[int], str]:
    value = profile.get("target_pace")
    text = str(value or "").strip().lower()
    if not text:
        return None, ""
    if "/km" not in text and "配速" not in text and "pace" not in text:
        return None, ""
    parsed = _pace_seconds(value)
    return (parsed, "target_pace") if parsed else (None, "")


def _target_marked_duration_seconds(value: Any) -> Optional[int]:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("：", ":")
    marker = r"(?:target|goal|sub|under|目标|冲击|冲|破|突破)"
    optional_half = r"(?:\s*(?:half\s*marathon|half|hm|半马|半程|成绩|time))*"
    duration = r"(\d+:\d{1,2}(?::\d{1,2})?|\d{2,3})"
    for pattern in (
        rf"{marker}{optional_half}\s*{duration}",
        rf"(?:half\s*marathon|half|hm|半马|半程).*?{marker}{optional_half}\s*{duration}",
    ):
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if not match:
            continue
        parsed = _duration_seconds(match.group(1), prefer_hours_for_short_colon=True)
        if parsed:
            return parsed
    return None


def _current_half_time_detail(profile: Dict[str, Any]) -> Tuple[Optional[int], str]:
    for key in _HALF_KEYS:
        parsed = _duration_seconds(profile.get(key), prefer_hours_for_short_colon=True)
        if parsed:
            return parsed, key
    return None, ""


def _current_hm_estimates(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    estimates: List[Dict[str, Any]] = []
    for label, keys, distance in [
        ("5K", _FIVE_K_KEYS, 5.0),
        ("10K", _TEN_K_KEYS, 10.0),
        ("半马", _HALF_KEYS, HALF_MARATHON_KM),
    ]:
        race_seconds = _race_duration_seconds(profile, keys)
        if not race_seconds:
            continue
        predicted_seconds = race_seconds if distance == HALF_MARATHON_KM else _riegel_predict(race_seconds, distance, HALF_MARATHON_KM)
        pace_seconds = round(predicted_seconds / HALF_MARATHON_KM)
        estimates.append({
            "source": label,
            "input_time_seconds": race_seconds,
            "estimated_half_time_seconds": round(predicted_seconds),
            "estimated_hmp_seconds_per_km": pace_seconds,
            "estimated_hmp_pace": format_pace(pace_seconds),
        })
    return estimates


def _choose_current_hmp(estimates: List[Dict[str, Any]]) -> Optional[int]:
    if not estimates:
        return None
    ten_or_half = [
        int(item["estimated_hmp_seconds_per_km"])
        for item in estimates
        if item.get("source") in {"10K", "半马"}
    ]
    if ten_or_half:
        return max(ten_or_half)
    return max(int(item["estimated_hmp_seconds_per_km"]) for item in estimates)


def _race_time_seconds(profile: Dict[str, Any], keys: Tuple[str, ...]) -> Optional[int]:
    seconds = _race_duration_seconds(profile, keys)
    if not seconds:
        return None
    distance = HALF_MARATHON_KM
    if keys == _FIVE_K_KEYS:
        distance = 5.0
    elif keys == _TEN_K_KEYS:
        distance = 10.0
    predicted = seconds if distance == HALF_MARATHON_KM else _riegel_predict(seconds, distance, HALF_MARATHON_KM)
    return round(predicted / HALF_MARATHON_KM)


def _race_duration_seconds(profile: Dict[str, Any], keys: Tuple[str, ...]) -> Optional[int]:
    for key in keys:
        parsed = _duration_seconds(profile.get(key), prefer_hours_for_short_colon=keys == _HALF_KEYS)
        if parsed:
            return parsed
    return None


def _duration_seconds(value: Any, *, prefer_hours_for_short_colon: bool = False) -> Optional[int]:
    text = str(value or "").strip()
    if not text:
        return None
    text = text.replace("：", ":")

    match = re.search(r"(\d+):(\d{1,2})(?::(\d{1,2}))?", text)
    if match:
        first = int(match.group(1))
        second = int(match.group(2))
        third = int(match.group(3) or 0)
        if match.group(3) is not None:
            return first * 3600 + second * 60 + third
        if prefer_hours_for_short_colon and 0 <= first <= 3 and 0 <= second < 60:
            return first * 3600 + second * 60
        return first * 60 + second

    hour_min = re.search(r"(\d+)\s*(?:小时|h)\s*(\d+)\s*(?:分|m|min)?", text, flags=re.IGNORECASE)
    if hour_min:
        return int(hour_min.group(1)) * 3600 + int(hour_min.group(2)) * 60

    minutes = re.search(r"(\d+(?:\.\d+)?)\s*(?:分钟|分|min|m)(?:\b|$)", text, flags=re.IGNORECASE)
    if minutes:
        return round(float(minutes.group(1)) * 60)

    numeric = re.fullmatch(r"\d{2,3}", text)
    if numeric:
        raw = int(text)
        if raw < 60:
            return raw * 60
        if raw < 100:
            return raw * 60
        return ((raw // 100) * 60 + raw % 100) * 60

    return None


def _looks_like_half_time_text(value: Any) -> bool:
    text = str(value or "").strip().lower()
    if not text or "/km" in text or "配速" in text:
        return False
    return any(token in text for token in ("半马", "半程", "half"))


def _looks_like_standalone_race_duration(value: Any) -> bool:
    text = str(value or "").strip().lower().replace("：", ":")
    if not text or "/km" in text or "配速" in text or "pace" in text:
        return False
    if re.fullmatch(r"\d+:\d{1,2}:\d{1,2}", text):
        return True
    return bool(re.fullmatch(r"[01]:[0-5]\d", text))


def _format_duration(seconds: Optional[int]) -> str:
    if seconds is None:
        return ""
    total = max(0, int(seconds))
    hours = total // 3600
    minutes = (total % 3600) // 60
    remainder = total % 60
    if remainder:
        return f"{hours}:{minutes:02d}:{remainder:02d}"
    return f"{hours}:{minutes:02d}"


def _pace_seconds(value: Any) -> Optional[int]:
    text = str(value or "").strip()
    if not text:
        return None
    match = re.search(r"(\d+)\s*[:：]\s*(\d{1,2})", text)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))
    return None


def _riegel_predict(seconds: int, from_km: float, to_km: float) -> float:
    return float(seconds) * math.pow(to_km / from_km, 1.06)


def _safe_float(value: Any) -> Optional[float]:
    return coerce_float_from_unit_text(value)


def _has_recovery_state(profile: Dict[str, Any]) -> bool:
    for key in ("injury_or_fatigue", "injury", "fatigue", "recovery_state", "recent_marathon"):
        value = profile.get(key)
        if isinstance(value, bool):
            return True
        if str(value or "").strip():
            return True
    return False


__all__ = [
    "build_half_marathon_pace_calibration",
    "detect_half_marathon_profile_gaps",
]
