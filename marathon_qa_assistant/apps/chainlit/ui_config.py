"""
UI 相关的常量与配置
"""

MULTI_VALUE_FIELDS = {"available_days", "terrain_preference", "training_types"}

# 反馈类关键词检测
FEEDBACK_INDICATORS = [
    "腿酸", "肌肉酸", "酸痛", "疲劳", "累了", "好累", "跑不动",
    "没劲", "状态差", "不舒服", "疼", "痛", "抽筋", "受伤", "膝盖",
    "脚踝", "踝", "髋", "腰酸", "肩", "背痛", "跟腱", "足底",
    "心率高", "心率异常", "没完成", "跑崩", "撞墙", "掉速",
]

# 9 区标签映射
ZONE_LABELS = {
    "Z1": "Z1 恢复跑 (<72%)",
    "Z2": "Z2 有氧耐力 (72-78%)",
    "Z3": "Z3 有氧动力 (79-84%)",
    "Z4": "Z4 阈值下限 (85-89%)",
    "Z5": "Z5 阈值上限 (90-93%)",
    "Z6": "Z6 无氧阈 (94-97%)",
    "Z7": "Z7 临界强度 (98-100%)",
    "Z8": "Z8 无氧耐力 (101-105%)",
    "Z9": "Z9 极高强度 (>105%)"
}

ZONE_ORDER = tuple(f"Z{i}" for i in range(1, 10))


def build_zone_mapping_table(hr_zones: dict | None, pace_zones: dict | None) -> str:
    """构建侧边栏使用的 Z1-Z9 区间映射表。"""
    hr_zones = hr_zones or {}
    pace_zones = pace_zones or {}

    rows = ["| 区间 | 心率 | 配速 |", "| :--- | :--- | :--- |"]
    for zone in ZONE_ORDER:
        hr_value = str(hr_zones.get(zone, "-")).split(" ")[0]
        pace_value = pace_zones.get(zone, "-")
        rows.append(f"| **{zone}** | {hr_value} | {pace_value} |")

    return "\n".join(rows)
