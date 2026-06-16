"""缺课调整器：基于 stimulus_type 的三条硬规则（不调 LLM）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from marathon_qa_assistant.services.workout_template_retriever import derive_stimulus_type


@dataclass
class AdjustmentProposal:
    """一条调整建议。"""
    action: str  # "reschedule" | "delete" | "trim"
    target_day: str  # 建议调整的目标日
    original_type: str  # 原训练类型
    new_type: str = ""  # 调整后的训练类型
    reason: str = ""  # 调整理由（含来源标注）
    source_citation: str = ""  # 文献来源
    requires_confirmation: bool = True  # 是否需用户确认


ADJUSTMENT_RULES = {
    "intensity": {
        "action": "reschedule",
        "reason_template": (
            "跳过的 {training_type} 属于强度刺激课（stimulus_type=intensity）。"
            "根据 Mujika & Padilla (2000) 和 Spiering et al. (2021) 的部分停训研究，"
            "VO2max 和乳酸阈值等核心生理适应在停训 7-10 天后开始退化。"
            "建议在 7 天内找一个空位补上，维持原强度不变。"
        ),
        "source": "Mujika & Padilla 2000; Spiering et al. 2021 (B 级)",
    },
    "volume_only": {
        "action": "delete",
        "reason_template": (
            "跳过的 {training_type} 属于纯跑量课（stimulus_type=volume_only）。"
            "根据 Seiler (2010) 的 80/20 训练强度分布研究，低强度课没有独特的不可替代刺激——"
            "其价值来自周总跑量而非单次课。跳过一节无需补课。"
        ),
        "source": "Seiler 2010 (B 级)",
    },
    "mixed": {
        "action": "trim",
        "reason_template": (
            "跳过的 {training_type} 包含高强度段和低强度巡航段（stimulus_type=mixed）。"
            "根据 Pfitzinger 训练调整原则，保留比赛配速的高强度部分，"
            "可将巡航跑量部分缩短至原时长的 60%，以保留核心刺激并控制负荷。"
        ),
        "source": "Pfitzinger Advanced Marathoning (A 级)",
    },
}


def _has_intensity_conflict(
    target_day: str, current_week: List[Dict[str, Any]], available_days: List[str]
) -> bool:
    """检查目标日与已有强度课的间隔是否 ≥48h。"""
    weekday_order = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    if target_day not in weekday_order:
        return True  # 无法判断，保守处理

    target_idx = weekday_order.index(target_day)
    for day in current_week:
        day_name = str(day.get("day", ""))
        if day_name not in weekday_order:
            continue
        st = derive_stimulus_type(str(day.get("zone_range", "") or ""))
        if st == "intensity":
            other_idx = weekday_order.index(day_name)
            if abs(target_idx - other_idx) < 2:
                return True
    return False


def _is_long_run_day(day_name: str, current_week: List[Dict[str, Any]]) -> bool:
    """检查某天是否为长距离日。"""
    for d in current_week:
        if d.get("day") == day_name and "长距离" in str(d.get("training_type", "") or ""):
            return True
    return False


def _find_reschedule_slot(
    current_week: List[Dict[str, Any]], available_days: List[str]
) -> Optional[str]:
    """在 7 天内找一个与已有强度课不冲突且非长距离日的空位。"""
    candidates = []
    for day_name in available_days:
        existing = [d for d in current_week if d.get("day") == day_name]
        if _is_long_run_day(day_name, current_week):
            continue  # 避免在长距离日加强度课 (教练实践)
        if not existing or existing[0].get("is_rest"):
            if not _has_intensity_conflict(day_name, current_week, available_days):
                candidates.append(day_name)
        elif existing:
            st = derive_stimulus_type(str(existing[0].get("zone_range", "") or ""))
            if st == "volume_only" and not _has_intensity_conflict(day_name, current_week, available_days):
                candidates.append(day_name)
    # 优先返回非长距离日的候选；若无候选，回退到包含长距离日的全部空位
    if candidates:
        return candidates[0]
    # 极端情况下：所有可用日都被长距离或强度课占满→返回 None（触发 trim 降级）
    return None


def propose_adjustments(
    missed_day: Dict[str, Any],
    current_week: List[Dict[str, Any]],
    profile: Optional[Dict[str, Any]] = None,
) -> List[AdjustmentProposal]:
    """根据跳过的训练课生成调整建议列表。

    Args:
        missed_day: 被跳过的 DayPlan（dict 形式，含 training_type / zone_range / stimulus_type）
        current_week: 当前周的所有 DayPlan（dict 列表）
        profile: 跑者画像，可选

    Returns:
        调整建议列表（≥1 条）。用户需确认后应用。
    """
    training_type = str(missed_day.get("training_type") or "")
    zone_range = str(missed_day.get("zone_range") or "")
    stimulus_type = str(missed_day.get("stimulus_type") or "")
    if not stimulus_type and zone_range:
        stimulus_type = derive_stimulus_type(zone_range)
    if not stimulus_type:
        stimulus_type = "volume_only"  # 默认保守

    # 获取可用训练日 (M5: 从跑者画像读取，fallback 全周)
    available_days = (profile or {}).get("available_days") or ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    rule = ADJUSTMENT_RULES.get(stimulus_type, ADJUSTMENT_RULES["volume_only"])
    proposals = []

    if rule["action"] == "reschedule":
        slot = _find_reschedule_slot(current_week, available_days)
        if slot:
            proposals.append(AdjustmentProposal(
                action="reschedule",
                target_day=slot,
                original_type=training_type,
                new_type=training_type,
                reason=rule["reason_template"].format(training_type=training_type),
                source_citation=rule["source"],
            ))
        else:
            # 没有合适空位 → 降级为 trim（只补强度段）
            proposals.append(AdjustmentProposal(
                action="trim",
                target_day=missed_day.get("day", ""),
                original_type=training_type,
                new_type=f"{training_type}（缩短版）",
                reason=(
                    f"跳过的 {training_type} 属于强度课，但 7 天内没有不与已有强度课冲突的空位。"
                    f"建议缩短原课时长并保留核心强度段。"
                    f"来源：{rule['source']}"
                ),
                source_citation=rule["source"],
            ))

    elif rule["action"] == "delete":
        proposals.append(AdjustmentProposal(
            action="delete",
            target_day=missed_day.get("day", ""),
            original_type=training_type,
            reason=rule["reason_template"].format(training_type=training_type),
            source_citation=rule["source"],
        ))

    elif rule["action"] == "trim":
        proposals.append(AdjustmentProposal(
            action="trim",
            target_day=missed_day.get("day", ""),
            original_type=training_type,
            new_type=f"{training_type}（保留强度段，跑量缩减 40%）",
            reason=rule["reason_template"].format(training_type=training_type),
            source_citation=rule["source"],
        ))

    # F2: 永远不返回空列表——无建议时返回信息性消息
    if not proposals:
        proposals.append(AdjustmentProposal(
            action="info",
            target_day="",
            original_type=training_type,
            reason="本周训练课安排已满，无法自动建议调整。建议保持原计划并在下次训练前评估身体状态。",
            source_citation="教练实践 (C 级)",
            requires_confirmation=False,
        ))

    return proposals
