"""
UI 相关的常量与配置
"""

from marathon_qa_assistant.core.zone_constants import (
    ZONE_LABELS,
    ZONE_LABELS_DETAIL,
    ZONE_ORDER,
    build_zone_mapping_table,
)

MULTI_VALUE_FIELDS = {"available_days", "terrain_preference", "training_types"}

# 反馈类关键词检测
FEEDBACK_INDICATORS = [
    "腿酸", "肌肉酸", "酸痛", "疲劳", "累了", "好累", "跑不动",
    "没劲", "状态差", "不舒服", "疼", "痛", "抽筋", "受伤", "膝盖",
    "脚踝", "踝", "髋", "腰酸", "肩", "背痛", "跟腱", "足底",
    "心率高", "心率异常", "没完成", "跑崩", "撞墙", "掉速",
]
