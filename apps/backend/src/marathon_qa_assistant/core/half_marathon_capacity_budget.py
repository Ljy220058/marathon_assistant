from __future__ import annotations

from typing import Any, Dict, Optional

from marathon_qa_assistant.core.training_plan_context import coerce_float_from_unit_text


def build_half_marathon_capacity_budget(
    *,
    weekly_volume_km: Optional[float],
    phase_id: str,
    available_days_count: Optional[int] = None,
    recent_four_week_mileage_km: Optional[float] = None,
    recent_marathon: bool = False,
    fatigue_or_injury: bool = False,
    speed_calibration_available: bool = True,
) -> Dict[str, Any]:
    """按当前画像把 Sub-70 理想课表容量缩放为可执行预算。"""
    planned_volume = _safe_float(weekly_volume_km) or 40.0
    recent_volume = _safe_float(recent_four_week_mileage_km)
    volume = planned_volume
    volume_basis = "planned_weekly_volume"
    if recent_volume is not None and 0 < recent_volume < planned_volume:
        volume = recent_volume
        volume_basis = "recent_four_week_mileage"
    days = int(available_days_count or 0)
    low_volume = volume < 45
    constrained_days = days > 0 and days < 4
    recovery_risk = bool(recent_marathon or fatigue_or_injury)

    quality_sessions_max = 2
    if low_volume or constrained_days or recovery_risk or phase_id == "introductory":
        quality_sessions_max = 1

    multiplier = 1.0
    if low_volume:
        multiplier *= 0.82
    if constrained_days:
        multiplier *= 0.88
    if recovery_risk:
        multiplier *= 0.78
    if not speed_calibration_available:
        multiplier *= 0.9

    if phase_id == "introductory":
        caps = {
            "long_run_max_km": min(14.0, volume * 0.28),
            "hmp_90_max_km": min(8.0, volume * 0.18),
            "hmp_95_max_km": 0.0,
            "hmp_100_total_max_km": 0.0,
            "hmp_105_total_max_km": 0.0,
            "hmp_110_total_max_km": min(2.0, volume * 0.04),
        }
    elif phase_id == "general":
        caps = {
            "long_run_max_km": min(18.0, volume * 0.32),
            "hmp_90_max_km": min(12.0, volume * 0.24),
            "hmp_95_max_km": min(6.0, volume * 0.12),
            "hmp_100_total_max_km": 0.0,
            "hmp_105_total_max_km": min(5.0, volume * 0.10),
            "hmp_110_total_max_km": min(3.0, volume * 0.06),
        }
    elif phase_id == "race_specific":
        caps = {
            "long_run_max_km": min(24.0, volume * 0.35),
            "hmp_90_max_km": min(16.0, volume * 0.26),
            "hmp_95_max_km": min(20.0, volume * 0.30),
            "hmp_100_total_max_km": min(14.0, volume * 0.20),
            "hmp_105_total_max_km": min(8.0, volume * 0.14),
            "hmp_110_total_max_km": min(4.0, volume * 0.07),
        }
    else:
        caps = {
            "long_run_max_km": min(22.0, volume * 0.34),
            "hmp_90_max_km": min(15.0, volume * 0.26),
            "hmp_95_max_km": min(16.0, volume * 0.26),
            "hmp_100_total_max_km": min(6.0, volume * 0.10),
            "hmp_105_total_max_km": min(8.0, volume * 0.15),
            "hmp_110_total_max_km": min(4.0, volume * 0.07),
        }

    scaled = {key: _round_km(value * multiplier) for key, value in caps.items()}
    notes = []
    if low_volume:
        notes.append("周跑量低于45km，HMP关键课容量按低跑量保守缩放。")
    if volume_basis == "recent_four_week_mileage":
        notes.append("近4周平均周跑量低于计划周跑量，容量预算按近期跑量保守计算。")
    if constrained_days:
        notes.append("可训练日少于4天，每周质量课上限降为1堂。")
    if recovery_risk:
        notes.append("近期全马、疲劳或伤病风险存在，关键课容量下调。")
    if not speed_calibration_available:
        notes.append("缺少当前5K/10K成绩，105-110% HMP速度容量保守缩放。")

    return {
        "status": "ready",
        "phase_id": phase_id,
        "weekly_volume_km": round(planned_volume, 1),
        "effective_weekly_volume_km": round(volume, 1),
        "recent_four_week_mileage_km": round(recent_volume, 1) if recent_volume is not None else None,
        "volume_basis": volume_basis,
        "quality_sessions_max": quality_sessions_max,
        **scaled,
        "notes": notes,
    }


def _round_km(value: float) -> float:
    return round(max(0.0, value) * 2) / 2


def _safe_float(value: Any) -> Optional[float]:
    return coerce_float_from_unit_text(value)


__all__ = ["build_half_marathon_capacity_budget"]
