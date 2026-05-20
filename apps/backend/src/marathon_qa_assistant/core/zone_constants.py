"""
Z1-Z9 区间常量、标签与配速映射。
统一项目中所有 zone label 定义的唯一来源。
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

# ---- Z1-Z9 LTHR% 范围定义 ----
ZONE_LTHR_PCT = {
    "Z1": (0, 72),
    "Z2": (72, 78),
    "Z3": (79, 84),
    "Z4": (85, 89),
    "Z5": (90, 93),
    "Z6": (94, 97),
    "Z7": (98, 100),
    "Z8": (101, 105),
    "Z9": (106, 200),
}

# ---- 统一区间标签（运动生理学命名） ----
ZONE_LABELS = {
    "Z1": "Z1 恢复放松区",
    "Z2": "Z2 轻松有氧区",
    "Z3": "Z3 稳态有氧区",
    "Z4": "Z4 有氧阈值区",
    "Z5": "Z5 马拉松专项区",
    "Z6": "Z6 乳酸阈值区",
    "Z7": "Z7 高强度耐受区",
    "Z8": "Z8 无氧刺激区",
    "Z9": "Z9 冲刺神经肌肉区",
}

ZONE_LABELS_DETAIL = {
    "Z1": "Z1 恢复放松区 (<72% LTHR)",
    "Z2": "Z2 轻松有氧区 (72-78% LTHR)",
    "Z3": "Z3 稳态有氧区 (79-84% LTHR)",
    "Z4": "Z4 有氧阈值区 (85-89% LTHR)",
    "Z5": "Z5 马拉松专项区 (90-93% LTHR)",
    "Z6": "Z6 乳酸阈值区 (94-97% LTHR)",
    "Z7": "Z7 高强度耐受区 (98-100% LTHR)",
    "Z8": "Z8 无氧刺激区 (101-105% LTHR)",
    "Z9": "Z9 冲刺神经肌肉区 (>105% LTHR)",
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


# ---- 配速区间映射 ----

def map_zone_to_pace(zone: str, user_profile: Optional[Dict[str, Any]] = None) -> str:
    """
    从用户画像的 pace_zones 中读取指定 zone 的配速范围。
    严格仅返回画像中已计算好的配速，绝不自行编造。
    
    返回格式如 "5:25-5:58/km"，无数据时返回空字符串。
    """
    if not user_profile or not isinstance(user_profile, dict):
        return ""

    zone = str(zone or "").strip()
    if not zone or not zone.startswith("Z"):
        return ""

    pace_zones = user_profile.get("pace_zones") or {}
    if not isinstance(pace_zones, dict):
        return ""

    pace_value = str(pace_zones.get(zone, "")).strip()
    if not pace_value or pace_value in ("-", "None", "0-0", "—"):
        return ""

    return f"{pace_value}/km"


# 匹配各种 LLM 可能编造的配速字符串
_PACE_PATTERN = re.compile(
    r'[，,；;]?\s*(?:目标\s*)?配速\s*[:：]?\s*\d+[:：.]\d+(?:\s*[-~–—]\s*\d+[:：.]\d+)?\s*/km',
    flags=re.IGNORECASE,
)


def sanitize_pace_text(text: str, user_profile: Optional[Dict[str, Any]] = None, current_zone: str = "") -> str:
    """
    清洗文本中的 LLM 编造配速，可选追加来自画像的区间映射配速。

    规则：
    1. 删除所有「配速 X:XX/km」格式的文本
    2. 若 current_zone 有效且画像中有对应配速，在文本末尾追加「目标配速 ≈ X:XX-X:XX/km」
    3. 若无映射结果，只保留区间描述（Z1-Z9），不追加任何配速数字
    """
    if not text:
        return text

    cleaned = _PACE_PATTERN.sub("", str(text)).strip()

    if current_zone and user_profile:
        verified_pace = map_zone_to_pace(current_zone, user_profile)
        if verified_pace:
            cleaned = f"{cleaned}，目标配速 ≈ {verified_pace}"

    return cleaned


def sanitize_all_pace(text: str) -> str:
    """仅删除所有编造配速，不追加画像配速。用于非训练日上下文。"""
    if not text:
        return text
    return _PACE_PATTERN.sub("", str(text)).strip()


__all__ = [
    "ZONE_LTHR_PCT",
    "ZONE_LABELS",
    "ZONE_LABELS_DETAIL",
    "ZONE_ORDER",
    "build_zone_mapping_table",
    "map_zone_to_pace",
    "sanitize_pace_text",
    "sanitize_all_pace",
]
