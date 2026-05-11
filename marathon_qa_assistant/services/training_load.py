from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


ZONE_LOAD_WEIGHTS = {
    "Z1": 0.6,
    "Z2": 0.9,
    "Z3": 1.2,
    "Z4": 1.6,
    "Z5": 2.1,
    "Z6": 2.7,
    "Z7": 3.3,
    "Z8": 4.0,
    "Z9": 4.8,
}

WORKOUT_DEFAULT_DURATION_MIN = {
    "easy_run": 45,
    "long_run": 90,
    "tempo_run": 55,
    "aerobic_threshold": 60,
    "anaerobic_threshold": 55,
    "marathon_pace": 70,
    "progression_run": 60,
    "fartlek": 55,
    "interval_run": 60,
    "vo2max_interval": 55,
    "hill_repeats": 55,
    "strides": 35,
    "hm_90_support_endurance": 90,
    "hm_95_long_fast_run": 100,
    "hm_100_float_intervals": 95,
    "hm_105_specific_speed": 70,
    "hm_110_support_speed": 55,
}

WORKOUT_FALLBACK_ZONE = {
    "easy_run": "Z2",
    "long_run": "Z2",
    "tempo_run": "Z4",
    "aerobic_threshold": "Z4",
    "anaerobic_threshold": "Z5",
    "marathon_pace": "Z3",
    "progression_run": "Z3",
    "fartlek": "Z5",
    "interval_run": "Z6",
    "vo2max_interval": "Z7",
    "hill_repeats": "Z6",
    "strides": "Z8",
    "hm_90_support_endurance": "Z4",
    "hm_95_long_fast_run": "Z5",
    "hm_100_float_intervals": "Z5",
    "hm_105_specific_speed": "Z6",
    "hm_110_support_speed": "Z7",
}


@dataclass
class TrainingLoadEstimate:
    duration_min: int
    intensity_zone: str
    intensity_weight: float
    training_load: int
    method: str
    factors: Dict[str, Any]


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_zones(*values: Any) -> List[str]:
    text = " ".join(str(v or "") for v in values)
    zones = re.findall(r"\bZ([1-9])\b", text.upper())
    return [f"Z{z}" for z in zones]


def choose_intensity_zone(
    *,
    workout_type: str = "",
    zone_range: str = "",
    zone_label: str = "",
    intensity_target: str = "",
) -> str:
    zones = _extract_zones(zone_range, zone_label, intensity_target)
    if zones:
        return zones[len(zones) // 2]
    return WORKOUT_FALLBACK_ZONE.get(workout_type, "Z2")


def _planned_distance_km(day: Dict[str, Any]) -> float:
    explicit_total = (
        _safe_float(day.get("total_km"))
        or _safe_float(day.get("distance_km"))
        or _safe_float(day.get("planned_km"))
    )
    if explicit_total and explicit_total > 0:
        return explicit_total
    return sum(
        _safe_float(day.get(key)) or 0.0
        for key in ("warmup_km", "main_km", "cooldown_km")
    )


def _extract_repetition_duration_min(text: str) -> int:
    values: List[float] = []
    for reps, minutes in re.findall(
        r"(\d{1,2})\s*(?:x|×|\*)\s*(\d{1,3}(?:\.\d+)?)\s*(?:分钟|分|min|mins|minute|minutes)",
        text,
        re.I,
    ):
        reps_value = _safe_float(reps) or 0
        minute_value = _safe_float(minutes) or 0
        if reps_value > 0 and minute_value > 0:
            values.append(reps_value * minute_value)

    recovery_matches = [
        _safe_float(value) or 0.0
        for value in re.findall(r"(?:组间|间歇|恢复|慢跑)\s*(\d{1,3}(?:\.\d+)?)\s*(?:分钟|分|min|mins)", text, re.I)
    ]
    if values and recovery_matches:
        primary_match = re.search(r"(\d{1,2})\s*(?:x|×|\*)\s*(\d{1,3}(?:\.\d+)?)", text, re.I)
        reps_value = int(_safe_float(primary_match.group(1)) or 0) if primary_match else 0
        values.append(max(0, reps_value - 1) * max(recovery_matches))

    return int(round(sum(values))) if values else 0


def _extract_distance_repetition_estimate(text: str) -> Dict[str, Any]:
    normalized = str(text or "").replace("公里", "km").replace("米", "m")
    match = re.search(
        r"(\d{1,2})\s*(?:x|×|\*)\s*(\d{2,5}(?:\.\d+)?)\s*(km|m)\b",
        normalized,
        re.I,
    )
    if not match:
        return {}

    reps = int(_safe_float(match.group(1)) or 0)
    unit_distance = _safe_float(match.group(2)) or 0.0
    unit = match.group(3).lower()
    if reps <= 0 or unit_distance <= 0:
        return {}

    unit_km = unit_distance if unit == "km" else unit_distance / 1000
    total_km = reps * unit_km
    if total_km <= 0:
        return {}

    recovery_matches = [
        _safe_float(value) or 0.0
        for value in re.findall(r"(?:组间|间歇|恢复|慢跑)\s*(\d{1,3}(?:\.\d+)?)\s*(?:分钟|分|min|mins)", normalized, re.I)
    ]
    recovery_min = max(recovery_matches) if recovery_matches else 0.0
    work_duration = total_km * 6.5
    recovery_duration = max(0, reps - 1) * recovery_min
    return {
        "duration_min": int(round(work_duration + recovery_duration)),
        "distance_repetition_reps": reps,
        "distance_repetition_unit_km": round(unit_km, 3),
        "distance_repetition_km": round(total_km, 1),
        "distance_repetition_recovery_min": recovery_min,
    }


def infer_duration_min(day: Dict[str, Any], workout_type: str = "") -> int:
    explicit = _safe_float(day.get("duration_min") or day.get("duration"))
    if explicit and explicit > 0:
        return int(round(explicit))

    km_total = _planned_distance_km(day)
    if km_total > 0:
        return max(10, int(round(km_total * 6.5)))

    text = " ".join(
        str(day.get(key) or "")
        for key in ("main_set", "warmup", "cooldown", "notes")
    )
    repetition_duration = _extract_repetition_duration_min(text)
    if repetition_duration > 0:
        return max(10, repetition_duration)

    distance_repetition = _extract_distance_repetition_estimate(text)
    if distance_repetition.get("duration_min"):
        return max(10, int(distance_repetition["duration_min"]))

    minute_matches = [
        int(value)
        for value in re.findall(r"(\d{1,3})\s*(?:分钟|分|min|mins|minute|minutes)", text, re.I)
    ]
    if minute_matches:
        return max(10, sum(minute_matches))

    km_matches = [_safe_float(value) for value in re.findall(r"(\d+(?:\.\d+)?)\s*km", text, re.I)]
    km_from_text = sum(value or 0.0 for value in km_matches)
    if km_from_text > 0:
        return max(10, int(round(km_from_text * 6.5)))

    return WORKOUT_DEFAULT_DURATION_MIN.get(workout_type, 45)


def calculate_plan_training_load(
    day: Dict[str, Any],
    *,
    workout_type: str = "",
    zone_range: str = "",
    zone_label: str = "",
    intensity_target: str = "",
) -> TrainingLoadEstimate:
    duration_min = infer_duration_min(day, workout_type)
    text = " ".join(
        str(day.get(key) or "")
        for key in ("main_set", "warmup", "cooldown", "notes")
    )
    distance_repetition = _extract_distance_repetition_estimate(text)
    intensity_zone = choose_intensity_zone(
        workout_type=workout_type,
        zone_range=zone_range,
        zone_label=zone_label,
        intensity_target=intensity_target,
    )
    intensity_weight = ZONE_LOAD_WEIGHTS.get(intensity_zone, ZONE_LOAD_WEIGHTS["Z2"])
    training_load = int(round(duration_min * intensity_weight))
    return TrainingLoadEstimate(
        duration_min=duration_min,
        intensity_zone=intensity_zone,
        intensity_weight=intensity_weight,
        training_load=training_load,
        method="planned_zone_duration",
        factors={
            "duration_min": duration_min,
            "intensity_zone": intensity_zone,
            "intensity_weight": intensity_weight,
            "source": "planned workout zone and inferred duration",
            "load_kind": "planned_load_proxy",
            "disclaimer": "计划代理负荷，不等同于设备基于心率、HRV或个体恢复状态计算的真实生理负荷。",
            **{key: value for key, value in distance_repetition.items() if key != "duration_min"},
        },
    )


def calculate_hr_trimp_training_load(
    *,
    duration_min: float,
    avg_hr: float,
    resting_hr: float,
    max_hr: float,
    sex: str = "male",
) -> TrainingLoadEstimate:
    if duration_min <= 0 or max_hr <= resting_hr:
        raise ValueError("duration_min must be positive and max_hr must be greater than resting_hr")

    hrr = (avg_hr - resting_hr) / (max_hr - resting_hr)
    hrr = min(1.0, max(0.0, hrr))
    if str(sex).lower().startswith("f"):
        multiplier = 0.86 * math.exp(1.67 * hrr)
    else:
        multiplier = 0.64 * math.exp(1.92 * hrr)
    load = int(round(duration_min * hrr * multiplier))
    return TrainingLoadEstimate(
        duration_min=int(round(duration_min)),
        intensity_zone="HR",
        intensity_weight=round(hrr * multiplier, 4),
        training_load=load,
        method="hr_trimp",
        factors={
            "hrr": round(hrr, 4),
            "avg_hr": avg_hr,
            "resting_hr": resting_hr,
            "max_hr": max_hr,
            "sex": sex,
        },
    )


def classify_intensity_trend(intensity_trend: float) -> str:
    if intensity_trend >= 150:
        return "excessive"
    if intensity_trend >= 100:
        return "optimized"
    if intensity_trend >= 80:
        return "maintaining"
    if intensity_trend >= 50:
        return "resuming"
    return "decreasing"


def classify_weekly_load_change(delta_percent: float) -> str:
    if delta_percent <= -8:
        return "deload"
    if delta_percent >= 8:
        return "build"
    return "stable"


def build_training_load_summary(days: Iterable[Any]) -> Dict[str, Any]:
    day_dicts = [d.to_dict() if hasattr(d, "to_dict") else dict(d) for d in days]
    loads = [int(round(_safe_float(day.get("training_load")) or 0)) for day in day_dicts]
    weekly_loads: List[Dict[str, Any]] = []
    by_week: Dict[int, int] = {}
    for day, load in zip(day_dicts, loads):
        week_index = int(day.get("week_index") or 0)
        by_week[week_index] = by_week.get(week_index, 0) + load

    previous_load: Optional[int] = None
    for week_index in sorted(k for k in by_week if k > 0):
        current_load = by_week[week_index]
        if previous_load is None:
            delta = 0
            delta_percent = 0.0
            trend_label = "baseline"
        else:
            delta = current_load - previous_load
            delta_percent = round((delta / previous_load) * 100, 1) if previous_load else 0.0
            trend_label = classify_weekly_load_change(delta_percent)
        weekly_loads.append({
            "week_index": week_index,
            "training_load": current_load,
            "delta_from_previous": delta,
            "delta_percent_from_previous": delta_percent,
            "trend_label": trend_label,
        })
        previous_load = current_load

    load_impact = sum(loads[:7])
    window_42 = loads[:42]
    if window_42:
        base_fitness = int(round((sum(window_42) / len(window_42)) * 7))
    else:
        base_fitness = 0
    intensity_trend = round((load_impact / base_fitness) * 100, 1) if base_fitness else 0.0

    return {
        "method": "planned_zone_duration_proxy",
        "load_kind": "planned_load_proxy",
        "disclaimer": "这是计划代理负荷：由计划时长与强度区权重估算，用于比较课表内部负荷，不等同于 COROS/Garmin 等设备的真实生理负荷。",
        "total_planned_load": sum(loads),
        "load_impact_7d": load_impact,
        "base_fitness_42d_weekly_equivalent": base_fitness,
        "intensity_trend": intensity_trend,
        "intensity_trend_zone": classify_intensity_trend(intensity_trend),
        "weekly_loads": weekly_loads,
        "weekly_load_changes": weekly_loads,
    }
