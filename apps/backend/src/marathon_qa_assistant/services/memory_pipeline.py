"""记忆写入管道 — 从工作流关键节点自动提取和写入记忆。"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("workflow_engine")


def _get_store():
    from marathon_qa_assistant.services.memory_store import get_memory_store
    return get_memory_store()


def write_profile_change_memories(
    user_id: str,
    old_profile: Dict[str, Any],
    new_profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """画像变更时写入 user_stated 记忆。"""
    ms = _get_store()
    written = []
    tracked_fields = {
        "goal": ("goal", "训练目标变更为: {value}"),
        "weekly_mileage": ("performance", "周跑量: {value} km"),
        "lthr": ("performance", "LTHR 更新为: {value}"),
        "t_pace": ("performance", "阈值配速更新为: {value}"),
        "injury_history": ("injury", "伤病记录: {value}"),
        "target_race_date": ("goal", "目标赛事日期: {value}"),
    }
    for field, (category, template) in tracked_fields.items():
        old_val = old_profile.get(field)
        new_val = new_profile.get(field)
        if new_val and new_val != old_val:
            content = template.format(value=new_val)
            mem = ms.add_memory_safe(
                user_id, content,
                source="user_stated", category=category,
                tags=[field, "profile_change"],
            )
            if mem:
                written.append(mem)
    return written


def write_feedback_memories(
    user_id: str,
    workout_feedback: Dict[str, Any],
    *,
    raw_text: str = "",
    reason_codes: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """训练反馈提交时写入记忆。"""
    ms = _get_store()
    written = []

    pain = workout_feedback.get("pain_status", "")
    if pain in ("risk", "watch"):
        pain_detail = raw_text if raw_text and len(raw_text) < 200 else f"疼痛状态: {pain}"
        mem = ms.add_memory_safe(
            user_id, pain_detail,
            source="user_stated", category="injury",
            tags=["pain", "feedback"],
        )
        if mem:
            written.append(mem)

    fatigue = workout_feedback.get("subjective_fatigue", "")
    if fatigue == "high":
        mem = ms.add_memory_safe(
            user_id, "训练反馈显示高疲劳状态",
            source="user_stated", category="context",
            tags=["fatigue", "feedback"],
        )
        if mem:
            written.append(mem)

    sleep = workout_feedback.get("sleep_quality", "")
    if sleep == "poor":
        mem = ms.add_memory_safe(
            user_id, "训练反馈显示睡眠质量较差",
            source="user_stated", category="context",
            tags=["sleep", "feedback"],
        )
        if mem:
            written.append(mem)

    if reason_codes:
        for code in reason_codes[:3]:
            mem = ms.add_memory_safe(
                user_id, f"训练调整原因: {code}",
                source="system_computed", category="context",
                tags=["adjustment", "feedback"],
            )
            if mem:
                written.append(mem)

    return written


def write_zone_computed_memories(
    user_id: str,
    profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """系统计算区间时写入 system_computed 记忆。"""
    ms = _get_store()
    written = []

    hr_zones = profile.get("hr_zones", {})
    if hr_zones and len(hr_zones) >= 5:
        z2 = hr_zones.get("Z2", {})
        if isinstance(z2, dict):
            z2_max = z2.get("max", "")
            if z2_max:
                mem = ms.add_memory_safe(
                    user_id, f"Z2 心率上限 {z2_max}bpm (LTHR={profile.get('lthr', '?')})",
                    source="system_computed", category="performance",
                    tags=["hr_zones", "computed"],
                )
                if mem:
                    written.append(mem)

    return written
