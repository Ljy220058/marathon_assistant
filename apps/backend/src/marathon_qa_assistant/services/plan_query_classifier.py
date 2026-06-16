from __future__ import annotations

from typing import Any, Dict


PLAN_QUERY_KEYWORDS = (
    "训练计划", "周计划", "月历", "日历", "课表", "生成计划", "制定", "安排",
    "备赛", "半马", "全马", "马拉松",
    "half marathon", "marathon", "training plan", "training feedback",
    "adjust next week", "adjusted plan", "adaptive plan",
    "race prep", "race preparation", "sub ", "pb",
)

NUTRITION_EXCLUSION_KEYWORDS = (
    "营养", "补给", "吃", "喝", "补水", "蛋白", "碳水", "恢复餐",
    "能量胶", "电解质", "饮食", "素食", "生酮", "空腹", "低血糖",
    "hydration", "fuel", "nutrition", "diet",
)

# 伤病/康复查询优先走 QA 路径（team mode），不走计划生成路径
INJURY_EXCLUSION_KEYWORDS = (
    "痛", "疼", "伤", "膝盖", "跟腱", "足底", "受伤", "拉伤", "应力",
    "骨折", "髂胫束", "筋膜", "肿", "康复", "rehabilitation", "injury", "pain",
)


def is_plan_query(query: str) -> bool:
    text = str(query or "").lower()
    if any(keyword.lower() in text for keyword in NUTRITION_EXCLUSION_KEYWORDS):
        return False
    if any(keyword.lower() in text for keyword in INJURY_EXCLUSION_KEYWORDS):
        return False
    return any(keyword.lower() in text for keyword in PLAN_QUERY_KEYWORDS)


def has_plan_generation_profile(profile: Dict[str, Any]) -> bool:
    if not isinstance(profile, dict):
        return False
    plan_fields = (
        profile.get("goal"),
        profile.get("current_half_time"),
        profile.get("target_half_time"),
        profile.get("target_race_date"),
        profile.get("weekly_mileage"),
        profile.get("recent_four_week_mileage"),
        profile.get("recent_4_week_mileage"),
        profile.get("last_month_mileage"),
        profile.get("available_days"),
        profile.get("target_pace"),
        profile.get("injury_or_fatigue"),
        profile.get("injury"),
        profile.get("recovery_state"),
    )
    return any(value not in (None, "", []) for value in plan_fields)
