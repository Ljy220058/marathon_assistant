import re
from typing import Dict


def is_zone_empty(zones: Dict[str, str], expected_count: int = 9) -> bool:
    """检查区间数据是否有效。"""
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
    """基于 LTHR 自动计算 9 区心率范围。"""
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
    """将 `M:SS`、`3.15`、`315` 等格式统一转换为秒。"""
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
    """将秒数转换为 `M:SS` 配速文本。"""
    if seconds <= 0:
        return "-"
    minutes, remaining_seconds = divmod(int(round(seconds)), 60)
    return f"{minutes}:{remaining_seconds:02d}"


def calculate_pace_zones(t_pace_str: str) -> Dict[str, str]:
    """基于 T-Pace 自动计算 9 区配速范围。"""
    t_seconds = pace_to_seconds(t_pace_str)
    if t_seconds <= 0:
        return {}

    def pace_range(slower_ratio: float, faster_ratio: float) -> str:
        return f"{seconds_to_pace(t_seconds * slower_ratio)}-{seconds_to_pace(t_seconds * faster_ratio)}"

    # 采用用户确认的 T-Pace 九区映射
    return {
        "Z1": pace_range(1.30, 1.15),
        "Z2": pace_range(1.15, 1.08),
        "Z3": pace_range(1.08, 1.02),
        "Z4": pace_range(1.02, 0.99),
        "Z5": pace_range(0.99, 0.95),
        "Z6": pace_range(0.95, 0.92),
        "Z7": pace_range(0.92, 0.90),
        "Z8": pace_range(0.90, 0.85),
        "Z9": pace_range(0.85, 0.75),
    }