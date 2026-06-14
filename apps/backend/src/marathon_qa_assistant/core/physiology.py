"""
运动生理学工具函数 —— 心率/配速区间计算与格式转换。

文献溯源说明：
- LTHR 分区概念源自 Joe Friel 的训练体系，本站点采用的 9 区百分比
  为教练实践经验提炼，未对应单一学术出版物。
- T-Pace 概念同样来自 Joe Friel 的阈值配速训练框架，本站点 9 区
  配速比率为教练实践经验适配。
- 纯工具函数（格式转换、有效性检查）无生理学公式来源，标注为
  [utility]。
"""

import re
from typing import Any, Dict


def is_zone_empty(zones: Dict[str, str], expected_count: int = 9) -> bool:
    """检查区间数据是否有效。

    出处：[utility] 数据校验工具函数，无运动生理学公式来源。
    """
    if not zones or not isinstance(zones, dict):
        return True
    
    # 根据期望的区间数量生成 key 列表
    required_keys = [f"Z{i}" for i in range(1, expected_count + 1)]
    
    if not all(key in zones for key in required_keys):
        return True
    for key in required_keys:
        value = str(zones.get(key, "")).strip()
        if value in ["-", "", "None", "0", "0-0", "—"]:
            return True
    return False


def calculate_hr_zones(lthr: int, model: str = "Coros") -> Dict[str, str]:
    """基于 LTHR 自动计算 9 区心率范围。

    M4: 当前仅支持 Coros 模型。model 参数保留用于未来多模型扩展 (Garmin/Polar 等)。
    出处：
    - 乳酸阈心率 (LTHR) 分区训练概念源自 Joe Friel (2009),
      Total Heart Rate Training, Ch.4; 以及 Joe Friel (2016),
      The Triathlete's Training Bible, 4th ed., Ch.7.
    - ACSM 运动处方指南 (Garber et al. 2011) 定义了基于 %HRmax
      或 %VO₂max 的 3-5 区通用分级，但未规定 %LTHR 多区映射。
    - 本站点采用的 9 区 %LTHR 具体阈值 (Z1<72% 至 Z9>105%)
      为 [coaching_practice]——综合 COROS/Stryd 等多区间训练
      生态的教练实践经验提炼，暂无单一文献出处。
    """
    if not lthr or lthr < 40:
        return {}

    # 采用用户自定义的 LTHR 九区映射比例
    # Z1: <72%, Z2: 72-78%, Z3: 79-84%, Z4: 85-89%, Z5: 90-93%, Z6: 94-97%, Z7: 98-100%, Z8: 101-105%, Z9: >105%
    return {
        "Z1": f"<{round(lthr * 0.72)} bpm",
        "Z2": f"{round(lthr * 0.72)}-{round(lthr * 0.78)} bpm",
        "Z3": f"{round(lthr * 0.79)}-{round(lthr * 0.84)} bpm",
        "Z4": f"{round(lthr * 0.85)}-{round(lthr * 0.89)} bpm",
        "Z5": f"{round(lthr * 0.90)}-{round(lthr * 0.93)} bpm",
        "Z6": f"{round(lthr * 0.94)}-{round(lthr * 0.97)} bpm",
        "Z7": f"{round(lthr * 0.98)}-{round(lthr * 1.00)} bpm",
        "Z8": f"{round(lthr * 1.01)}-{round(lthr * 1.05)} bpm",
        "Z9": f">{round(lthr * 1.05)} bpm",
    }


def pace_to_seconds(pace_str: str) -> int:
    """将 `M:SS`、`3.15`、`315` 等格式统一转换为秒。

    出处：[utility] 配速格式解析工具函数，无运动生理学公式来源。
    """
    if not pace_str:
        return 0

    pace_str = str(pace_str).strip()

    if ":" in pace_str:
        try:
            parts = [re.sub(r"\D", "", part) for part in pace_str.split(":")]
            parts = [part for part in parts if part]
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            if len(parts) >= 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except Exception:
            pass

    if "." in pace_str:
        try:
            minutes, seconds = pace_str.split(".")
            return int(minutes) * 60 + int(seconds)
        except Exception:
            pass

    if pace_str.isdigit() and len(pace_str) >= 3:
        try:
            minutes = int(pace_str[:-2])
            seconds = int(pace_str[-2:])
            return minutes * 60 + seconds
        except Exception:
            pass

    return 0


def seconds_to_pace(seconds: int) -> str:
    """将秒数转换为 `M:SS` 配速文本。

    出处：[utility] 秒数格式化工具函数，无运动生理学公式来源。
    """
    if seconds <= 0:
        return "-"
    minutes, remaining_seconds = divmod(int(round(seconds)), 60)
    return f"{minutes}:{remaining_seconds:02d}"


def calculate_pace_zones(
    t_pace_str: str,
    target_hmp_seconds: int = 0,
) -> Dict[str, str]:
    """基于 T-Pace 自动计算 9 区配速范围。

    如果提供了 target_hmp_seconds（目标半马配速，秒/km），Z5 马拉松专项区
    将以 HMP 为中心（±6 秒），而非从 T-Pace 推导，确保 Z5 与目标比赛配速一致。

    出处：
    - 阈值配速 (T-Pace / Threshold Pace) 概念源自 Joe Friel (2009),
      Your Best Triathlon, Ch.5; 以及 Joe Friel (2016),
      The Triathlete's Training Bible, 4th ed., Ch.7 —
      Friel 提出以乳酸阈配速为基准按比例推导各训练区间的框架。
    - 基于 VDOT 的配速区间表来自 Jack Daniels (2013),
      Daniels' Running Formula, 3rd ed., Ch.3-4 —
      Daniels 通过 VO₂max 预估比赛成绩并反推各强度配速，
      与 %T-Pace 比例法属于不同体系。
    - 本站点采用的 9 区 T-Pace 具体比率
      (Z1 1.30x-1.15x 至 Z9 0.85x-0.75x) 以及 Z5 围绕
      目标半马配速 ±6 秒/km 的调整策略，均为 [coaching_practice]——
      综合多位马拉松教练的实践经验适配，暂无单一文献出处。
    """
    t_seconds = pace_to_seconds(t_pace_str)
    if t_seconds <= 0:
        return {}

    def pace_range(slower_ratio: float, faster_ratio: float) -> str:
        return f"{seconds_to_pace(t_seconds * slower_ratio)}-{seconds_to_pace(t_seconds * faster_ratio)}"

    # 如果提供了目标 HMP，Z5 围绕 HMP 排列（±6 秒）
    # 这样进阶跑者的马拉松配速区直接对应目标比赛配速，偏差可控在 5-8 秒/km 内
    # P2: 无目标 HMP 时返回占位提示，避免从 T-Pace 推导出无意义的默认值
    if target_hmp_seconds > 0:
        z5_lower = target_hmp_seconds - 6  # 稍快于 HMP（下限）
        z5_upper = target_hmp_seconds + 6  # 稍慢于 HMP（上限）
        z5_range = f"{seconds_to_pace(z5_upper)}-{seconds_to_pace(z5_lower)}"
    else:
        z5_range = "设置目标配速后自动计算"

    # 采用用户确认的 T-Pace 九区映射
    return {
        "Z1": pace_range(1.30, 1.15),
        "Z2": pace_range(1.15, 1.08),
        "Z3": pace_range(1.08, 1.02),
        "Z4": pace_range(1.02, 0.99),
        "Z5": z5_range,
        "Z6": pace_range(0.95, 0.92),
        "Z7": pace_range(0.92, 0.90),
        "Z8": pace_range(0.90, 0.85),
        "Z9": pace_range(0.85, 0.75),
    }


# ---------------------------------------------------------------------------
# Critical Speed (CS) 拟合 —— 从多个距离的 PB 反推临界速度与 D'
# ---------------------------------------------------------------------------
# CS 模型：distance = D' + CS × time。对 (time, distance) 做最小二乘线性回归，
# 斜率 = CS（临界速度，m/s，可长时间维持的最大稳态速度），
# 截距 = D'（D-prime，有限无氧能量储备，m）。
# CS 约落在乳酸阈与 VO₂max 之间，可作为无 T-Pace 时的强度锚。
# 出处：Critical Power/Speed 模型（Monod & Scherrer 1965；Poole & Jones 2017 综述）。

_PB_DISTANCE_FIELDS = (
    (800, "pb_800m"),
    (1500, "pb_1500m"),
    (5000, "pb_5k"),
    (10000, "pb_10k"),
    (21097.5, "pb_half"),
    (42195, "pb_full"),
)


def collect_pb_distance_time(profile: Dict[str, Any]) -> Dict[float, int]:
    """从 profile 的 PB 字段收集 {距离m: 完赛时间s}，供 CS 拟合。

    PB 时间格式（mm:ss / h:mm:ss / 数字）统一用 pace_to_seconds 解析。
    """
    result: Dict[float, int] = {}
    if not isinstance(profile, dict):
        return result
    for distance, key in _PB_DISTANCE_FIELDS:
        raw = profile.get(key)
        if raw is None or str(raw).strip() in ("", "—", "-"):
            continue
        seconds = pace_to_seconds(str(raw))
        if seconds > 0:
            result[float(distance)] = seconds
    return result


def calculate_critical_speed(pb_seconds_by_distance: Dict[float, int]) -> Dict[str, Any]:
    """从多个距离的完赛时间拟合 Critical Speed (CS) 与 D'。

    模型 distance = D' + CS × time，最小二乘回归得 CS（斜率）与 D'（截距）。

    参数：{距离(m): 完赛时间(s)}，至少 2 个点（建议 3-4 个，含 5k/10k/半马/全马）。

    返回：cs_mps / d_prime_m / cs_pace_sec_per_km / cs_pace_str /
          n_points / r_squared / source_distances_m；点不足或拟合异常返回 {}。
    """
    points = [(t, d) for d, t in (pb_seconds_by_distance or {}).items() if d > 0 and t > 0]
    if len(points) < 2:
        return {}
    n = len(points)
    sum_t = sum(t for t, _ in points)
    sum_d = sum(d for _, d in points)
    sum_tt = sum(t * t for t, _ in points)
    sum_td = sum(t * d for t, d in points)
    denom = n * sum_tt - sum_t * sum_t
    if denom <= 0:
        return {}
    cs = (n * sum_td - sum_t * sum_d) / denom
    d_prime = (sum_d - cs * sum_t) / n
    if cs <= 0 or d_prime < 0:
        return {}
    mean_d = sum_d / n
    ss_tot = sum((d - mean_d) ** 2 for _, d in points)
    ss_res = sum((d - (cs * t + d_prime)) ** 2 for t, d in points)
    r_squared = (1 - ss_res / ss_tot) if ss_tot > 0 else 0.0
    cs_pace_sec_per_km = 1000.0 / cs
    return {
        "cs_mps": round(cs, 3),
        "d_prime_m": round(d_prime, 1),
        "cs_pace_sec_per_km": round(cs_pace_sec_per_km, 1),
        "cs_pace_str": seconds_to_pace(round(cs_pace_sec_per_km)),
        "n_points": n,
        "r_squared": round(r_squared, 4),
        "source_distances_m": sorted(d for _, d in points),
    }