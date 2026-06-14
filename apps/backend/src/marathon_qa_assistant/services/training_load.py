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
    method = "planned_zone_duration_proxy"
    return TrainingLoadEstimate(
        duration_min=duration_min,
        intensity_zone=intensity_zone,
        intensity_weight=intensity_weight,
        training_load=training_load,
        method=method,
        factors={
            "duration_min": duration_min,
            "intensity_zone": intensity_zone,
            "intensity_weight": intensity_weight,
            "method": method,
            "source": "planned workout zone and inferred duration",
            "source_type": "planned_load_proxy",
            "load_kind": "planned_load_proxy",
            "is_estimated": True,
            "confidence": "estimated",
            "not_device_metric": True,
            "calculation_inputs": ["duration_min", "intensity_zone", "intensity_weight"],
            "missing_inputs": ["heart_rate", "hrv", "sleep_score", "device_recovery_status"],
            "disclaimer": "计划代理负荷，不等同于设备基于心率、HRV、睡眠或个体恢复状态计算的真实生理负荷。",
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
        method="hr_trimp_estimated",
        factors={
            "method": "hr_trimp_estimated",
            "source_type": "estimated_heart_rate_proxy",
            "load_kind": "estimated",
            "is_estimated": True,
            "confidence": "estimated_from_heart_rate",
            "not_device_metric": True,
            "calculation_inputs": ["duration_min", "avg_hr", "resting_hr", "max_hr", "sex"],
            "missing_inputs": ["hrv", "sleep_score", "device_recovery_status"],
            "hrr": round(hrr, 4),
            "avg_hr": avg_hr,
            "resting_hr": resting_hr,
            "max_hr": max_hr,
            "sex": sex,
            "disclaimer": "HR TRIMP 是基于输入心率的训练负荷代理值，不等同于设备厂商的完整恢复或生理负荷模型。",
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


def classify_tsb(tsb: float) -> str:
    """TSB (Training Stress Balance = CTL − ATL) 分级，即 Banister Form 指标。

    来源（TrainingPeaks 官方 + Joe Friel）：
    - TrainingPeaks Help Center, "Form (TSB)",
      https://help.trainingpeaks.com/hc/en-us/articles/204071764
    - TrainingPeaks Coach Blog, "A Coach's Guide to ATL, CTL & TSB"
    - Joe Friel, "Training Stress Balance—So What?", joefrieltraining.com

    区间语义（对齐 TrainingPeaks 官方）：
      TSB ≥ 25         : very_fresh（比赛就绪/peaked）
      10 ≤ TSB < 25    : fresh（减量期）
      -10 ≤ TSB < 10   : neutral（维持期）
      -30 ≤ TSB < -10  : productive_training（高效 fitness building 区，非疲劳）
      TSB < -30        : overreaching_risk（极端负荷，过度训练风险）

    注意：-10~-30 是 TrainingPeaks 定义的"最佳训练区"，是健康加量区间，不是疲劳。
    """
    if tsb >= 25:
        return "very_fresh"
    if tsb >= 10:
        return "fresh"
    if tsb >= -10:
        return "neutral"
    if tsb >= -30:
        return "productive_training"
    return "overreaching_risk"


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
        "source_type": "planned_load_proxy",
        "is_estimated": True,
        "confidence": "estimated",
        "not_device_metric": True,
        "calculation_inputs": ["daily.training_load", "week_index"],
        "missing_inputs": ["heart_rate", "hrv", "sleep_score", "device_recovery_status"],
        "disclaimer": "这是计划代理负荷：由计划时长与强度区权重估算，用于比较课表内部负荷，不等同于 COROS/Garmin 等设备的真实生理负荷。",
        "total_planned_load": sum(loads),
        "load_impact_7d": load_impact,
        "base_fitness_42d_weekly_equivalent": base_fitness,
        # L2 Fitness-Fatigue 标准化指标：CTL(慢性42d) / ATL(急性7d) / TSB(Form=CTL−ATL)
        "ctl_42d_weekly_equivalent": base_fitness,
        "atl_7d": load_impact,
        "tsb": base_fitness - load_impact,
        "tsb_label": classify_tsb(base_fitness - load_impact),
        "intensity_trend": intensity_trend,
        "intensity_trend_zone": classify_intensity_trend(intensity_trend),
        "weekly_loads": weekly_loads,
        "weekly_load_changes": weekly_loads,
    }


# ---------------------------------------------------------------------------
# ACWR (Acute:Chronic Workload Ratio) — Gabbett 2016
# ---------------------------------------------------------------------------

def acute_load(daily_loads_7d: Iterable[float]) -> float:
    """最近 7 天总训练负荷（急性负荷窗口）。

    Returns:
        7 天内训练负荷总和（等同于 1 周总负荷）。
    """
    values = [float(v) for v in daily_loads_7d if v is not None]
    return round(sum(values), 1)


def chronic_load(daily_loads_28d: Iterable[float]) -> float:
    """最近 28 天滚动平均训练负荷（慢性负荷窗口），以周总负荷为单位。

    按 Gabbett 2016 方法，慢性负荷为过去 4 周急性负荷的滚动平均。
    从每日数据计算时：chronic = (28 天总和) / 4，即平均每周总负荷。

    Returns:
        平均每周总负荷（与 acute_load 同单位，方便 ACWR 计算）。
    """
    values = [float(v) for v in daily_loads_28d if v is not None]
    if not values:
        return 0.0
    # 按 Gabbett 惯例：28 天 / 4 = 7 天窗口等效值
    # 等价于：avg_daily * 7
    return round(sum(values) / 4, 1)


def calculate_acwr(acute_load: float, chronic_load: float) -> float:
    """急性:慢性工作负荷比值 (ACWR)。

    ACWR = acute / chronic。两者均以周总负荷为单位。
    当 chronic_load 为 0 时返回 0（无法计算）。
    """
    if chronic_load <= 0:
        return 0.0
    return round(acute_load / chronic_load, 2)


def classify_risk(acwr: float) -> str:
    """按 Gabbett 2016 安全阈值对 ACWR 分类。

    参考：Gabbett TJ. The training-injury prevention paradox:
    should athletes be training smarter and harder?
    Br J Sports Med. 2016;50(5):273-280.

    阈值：
      - < 0.8  → undertraining（训练不足）
      - 0.8-1.3 → safe（安全区间）
      - 1.3-1.5 → elevated（升高风险）
      - > 1.5  → high_risk（高风险）
    """
    if acwr == 0.0:
        return "insufficient_data"
    if acwr < 0.8:
        return "undertraining"
    if acwr < 1.3:
        return "safe"
    if acwr < 1.5:
        return "elevated"
    return "high_risk"


def compute_acwr_summary(
    daily_loads: List[float],
    *,
    acute_window: int = 7,
    chronic_window: int = 28,
) -> Dict[str, Any]:
    """从每日负荷列表计算完整的 ACWR 摘要。

    Args:
        daily_loads: 每日训练负荷值列表（最近的在末尾）。
        acute_window: 急性窗口天数（默认 7）。
        chronic_window: 慢性窗口天数（默认 28）。

    Returns:
        ACWR 摘要字典，包含指标、分类和建议。
    """
    if not daily_loads:
        return {
            "acute_load": 0.0,
            "chronic_load": 0.0,
            "acwr": 0.0,
            "risk_level": "insufficient_data",
            "method": "acwr_gabbett_2016",
            "windows": {"acute_days": acute_window, "chronic_days": chronic_window},
            "note": "无可用训练负荷数据。",
        }

    acute = acute_load(daily_loads[-acute_window:])
    chr_load = chronic_load(daily_loads[-chronic_window:])
    acwr = calculate_acwr(acute, chr_load)
    risk = classify_risk(acwr)

    note = ""
    if risk == "high_risk":
        note = "ACWR > 1.5 伤bing风险显著升高，建议减量至安全区间 (0.8-1.3)。"
    elif risk == "elevated":
        note = "ACWR 处于升高区间，注意恢复并避免进一步增加负荷。"
    elif risk == "safe":
        note = "负荷递进在安全范围内，可继续按计划训练。"
    elif risk == "undertraining":
        note = "当前训练负荷偏低，可逐步增加以达到训练刺激。"
    else:
        note = "数据不足，无法评估负荷风险。"

    return {
        "acute_load": acute,
        "chronic_load": chr_load,
        "acwr": acwr,
        "risk_level": risk,
        "note": note,
        "method": "acwr_gabbett_2016",
        "reference": "Gabbett TJ. Br J Sports Med. 2016;50(5):273-280.",
        "windows": {"acute_days": acute_window, "chronic_days": chronic_window},
        "risk_thresholds": {
            "undertraining": "< 0.8",
            "safe": "0.8 - 1.3",
            "elevated": "1.3 - 1.5",
            "high_risk": "> 1.5",
        },
    }
