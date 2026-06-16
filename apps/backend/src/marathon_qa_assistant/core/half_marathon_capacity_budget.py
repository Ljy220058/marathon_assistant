from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

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
    phase_family: str = "general",          # _phase_family() 返回值
    total_training_sessions: Optional[int] = None,  # 一周训练总课次, 默认=available_days_count
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

    # 强度课约束: 文献约束范围取上限作为 quality_sessions_max
    # (Seiler 2010 B 级 + Pfitzinger/Daniels A 级 + Gabbett 2016 B 级)
    total_sessions = int(total_training_sessions or days or 3)
    intensity_lower, intensity_upper = _compute_intensity_bounds(
        total_sessions=total_sessions,
        phase_family=phase_family,
        profile={
            "injury_or_fatigue": fatigue_or_injury,
            "recent_marathon": recent_marathon,
        },
    )
    quality_sessions_max = intensity_upper

    # 原有的降级条件作为附加安全阀: 触发时强制上限为 1
    if low_volume or constrained_days or recovery_risk or phase_id == "introductory":
        quality_sessions_max = min(quality_sessions_max, 1)

    # A1: 容量安全乘数 — 来源分级标注
    # - low_volume (0.82): Seiler 2010 极化训练对低跑量人群的保守适配 (B 级外推)
    # - constrained_days (0.88): Gabbett 2016 ACWR 高负荷风险, 训练日少→单次负荷高→需保守 (B 级外推)
    # - recovery_risk (0.78): Mujika & Padilla 2000 停训效应, 恢复期负荷敏感 (B 级外推)
    # - speed_calibration (0.9): Pfitzinger/Daniels 配速校准原则, 缺当前成绩→保守估计 (A 级)
    # 注意: 具体乘数值为教练实践级 (C 级) 外推，文献仅提供方向（应降/应保守），不提供精确百分比
    multiplier = 1.0
    if low_volume:
        multiplier *= 0.82  # 文献方向: 降；具体值: C 级外推
    if constrained_days:
        multiplier *= 0.88  # 文献方向: 降；具体值: C 级外推
    if recovery_risk:
        multiplier *= 0.78  # 文献方向: 降；具体值: C 级外推
    if not speed_calibration_available:
        multiplier *= 0.9   # 文献方向: 降；具体值: C 级外推 (A 级原则, C 级数值)

    # M3: 训练频次驱动的单课容量调节 (Seiler 2010 频率-强度分布 + Gabbett 2016 单次负荷上限)
    # - 高训练日数: 周总负荷分散于更多课次, 单课容量下调以控制每课负荷
    # - 低训练日数: 周总负荷集中于少数课次, 单课容量需略高以承载足够训练刺激
    # 方向 B 级 (Seiler 2010, Gabbett 2016); 具体乘数值 C 级外推
    # 注意: 频次调节比 constrained_days (<4日) 粒度更细, 覆盖 3-7 练全范围
    if total_sessions >= 7:
        multiplier *= 0.92  # 7练/周: 单次容量保守 (B 级方向, C 级数值)
        freq_note = "7练/周频次高, 单课容量下调"
    elif total_sessions >= 6:
        multiplier *= 0.95  # 6练/周: 单次容量略保守
        freq_note = "6练/周频次较高, 单课容量轻微下调"
    elif total_sessions <= 3:
        multiplier *= 1.05  # 3练/周: 单次容量略高 (quality_sessions_max 已约束强度课数量)
        freq_note = "3练/周频次低, 单课容量轻微上调以承载足够负荷"
    else:
        freq_note = ""

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
    if freq_note:
        notes.append(freq_note)

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


# ── 训练频次→强度课约束范围（Seiler 2010 + Pfitzinger + Gabbett 2016）──

def _frequency_bounds(total_sessions: int) -> Tuple[int, int]:
    """训练总课次 → 强度课范围 (lower, upper)。

    来源标注：
    - 上限: Seiler 2010 (20% sessions), Stoggl 2014 POL 验证 (B 级)
    - 下限: Pfitzinger Advanced Marathoning, Daniels Running Formula (A 级)
    - 6-7 练区间: 组合外推, 非直接实验证据
    """
    if total_sessions <= 0:
        raise ValueError(f"total_sessions 必须为正整数, 收到 {total_sessions}")
    # ≤3 和 ≤5 分两支以保留文献来源标注的差异
    #   (1,3): 三练中一练是长距离，天然占去强度负荷
    #   (4,5): 五一训练者的经典结构，Seiler 20%×5=1.0
    if total_sessions <= 3:
        return 1, 1
    elif total_sessions <= 5:
        return 1, 1
    elif total_sessions <= 7:
        return 1, 2
    elif total_sessions <= 10:
        return 1, 2
    else:
        return 2, 3


def _compute_intensity_bounds(
    total_sessions: int,
    phase_family: str,
    profile: Optional[Dict[str, Any]] = None,
) -> Tuple[int, int]:
    """根据训练频次、阶段、画像返回强度课范围 (lower, upper)。

    Args:
        total_sessions: 一周训练总课次 (当前 = len(available_days))
        phase_family: _phase_family() 返回值 (base_1/base_2/build/peak/taper/intro)
        profile: 跑者画像, 可选。用于伤病/中断修正。

    Returns:
        (lower, upper) — 强度课数量约束范围, 两端均为闭区间。
        代码层安全边界: 1 ≤ lower ≤ 3, 1 ≤ upper ≤ 3。
    """
    profile = profile or {}

    # 1. 文献约束表 → 基础范围
    lower, upper = _frequency_bounds(total_sessions)

    # 2. 阶段修正 (来源: Bompa 周期化理论 + Pfitzinger 阶段模板)
    if phase_family in ("base_1", "base_2", "intro"):
        upper = lower  # 基础期: 只用下限
    elif phase_family == "build":
        upper = max(lower, upper - 1)  # 建设期: 取中间值
    elif phase_family == "peak":
        lower = upper  # 比赛专项期: 用上限
    elif phase_family == "taper":
        return 1, 1  # 减量期: 强制 1 节

    # 3. 画像修正: 伤病/近全马 → 强制 1 节
    #    (来源: Gabbett 2016 ACWR + 教练实践 A/B 级)
    if profile.get("injury_or_fatigue") or profile.get("recent_marathon"):
        return 1, 1

    # 4. 安全裁剪
    return max(1, lower), min(3, upper)


__all__ = ["build_half_marathon_capacity_budget"]
