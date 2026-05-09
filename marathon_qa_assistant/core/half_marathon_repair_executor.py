from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class HMPRepairAction:
    constraint_id: str
    severity: str
    week_index: Optional[int]
    day: str
    action: str
    before_training_type: str = ""
    before_main_set: str = ""
    after_training_type: str = ""
    after_main_set: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def apply_half_marathon_repairs(plan_dict: Dict[str, Any], validation: Dict[str, Any]) -> Dict[str, Any]:
    """根据 HMP 验证问题应用一轮确定性降级修复，并返回新计划与修复日志。"""
    repaired = deepcopy(plan_dict)
    repair_log: List[HMPRepairAction] = []
    repaired_day_keys = set()

    for issue in validation.get("issues") or []:
        if not isinstance(issue, dict):
            continue
        constraint_id = str(issue.get("constraint_id") or "")
        week_index = _safe_int(issue.get("week_index"))
        day_label = str(issue.get("day") or "").strip()
        severity = str(issue.get("severity") or "warning")

        if constraint_id == "dynamic_hmp_calibration":
            action = _add_plan_level_speed_calibration(repaired, severity)
        elif constraint_id == "no_sub70_volume_copy":
            action = _add_plan_level_volume_scaling_note(repaired, severity, week_index)
        else:
            day_key = (week_index, day_label)
            if day_key in repaired_day_keys and constraint_id in {"progress_long_fast_run", "race_specific_timing"}:
                continue
            day = _find_day(repaired, week_index, day_label)
            if day is None:
                continue
            action = _repair_day(day, constraint_id, severity, week_index, day_label)

        if action is not None:
            repair_log.append(action)
            if action.week_index is not None and action.day:
                repaired_day_keys.add((action.week_index, action.day))

    repaired["half_marathon_protocol_repair_log"] = [item.to_dict() for item in repair_log]
    protocol = repaired.get("half_marathon_protocol")
    if isinstance(protocol, dict):
        protocol["repair_log"] = [item.to_dict() for item in repair_log]
    return repaired


def _repair_day(
    day: Dict[str, Any],
    constraint_id: str,
    severity: str,
    week_index: Optional[int],
    day_label: str,
) -> Optional[HMPRepairAction]:
    before_type = str(day.get("training_type") or "")
    before_main = str(day.get("main_set") or "")

    if constraint_id == "marathon_recovery_intro":
        _set_day(
            day,
            training_type="法特莱克",
            main_set="hm_intro_fartlek_hills：35分钟体感法特莱克，含6×30秒轻快跑，强度控制在75-85% HMP；由HMP修复器从硬课降级",
            note_suffix="HMP修复：刚比完全马导入期，取消高消耗半马专项硬课。",
        )
        action = "导入期硬课已降级为hm_intro_fartlek_hills。"
    elif constraint_id == "progress_long_fast_run":
        _set_day(
            day,
            training_type="渐进跑",
            main_set="hm_90_support_endurance：14km 分段递进，86%-88%-90% HMP；由高消耗专项课降级",
            note_suffix="HMP修复：先建立90% HMP支撑，再进入后续专项上限课。",
        )
        action = "95% HMP跳级课已降级为hm_90_support_endurance。"
    elif constraint_id == "race_specific_timing":
        _set_day(
            day,
            training_type="渐进跑",
            main_set="hm_90_support_endurance：12km 分段递进，86%-88%-90% HMP；核心专项课延后到赛前6周内",
            note_suffix="HMP修复：核心专项课过早，已延后并替换为90% HMP支撑跑。",
        )
        action = "过早100% HMP核心课已替换为90% HMP支撑跑。"
    elif constraint_id == "quality_recovery_gap":
        _set_day(
            day,
            training_type="轻松跑",
            main_set="40分钟轻松跑，配速按Z1-Z2体感；HMP质量课顺延以保留约48小时恢复",
            note_suffix="HMP修复：质量课间隔不足48小时，后一堂课改为轻松跑。",
        )
        action = "恢复间隔不足的后一堂HMP质量课已改为轻松跑。"
    elif constraint_id == "environment_or_fatigue_downgrade":
        notes = str(day.get("notes") or "")
        suffix = "HMP修复：环境/疲劳/伤痛风险触发，按体感降级、缩短主课，必要时改为恢复跑。"
        day["notes"] = _append_note(notes, suffix)
        if "降级" not in before_main and "缩短" not in before_main and "改为" not in before_main:
            day["main_set"] = f"{before_main}；若高温/强风/疼痛/疲劳明显，降级并缩短，或改为30-40分钟恢复跑"
        action = "环境/疲劳风险已补充显式降级方案。"
    elif constraint_id == "capacity_budget_exceeded":
        _set_day(
            day,
            training_type="渐进跑",
            main_set="hm_90_support_endurance：10km 分段递进，86%-88%-90% HMP；由容量超额专项课降级",
            note_suffix="HMP修复：关键课容量超过当前画像预算，先降级为90% HMP支撑跑。",
        )
        action = "容量超额HMP课已降级为90% HMP支撑跑。"
    else:
        return None

    return HMPRepairAction(
        constraint_id=constraint_id,
        severity=severity,
        week_index=week_index,
        day=day_label,
        action=action,
        before_training_type=before_type,
        before_main_set=before_main,
        after_training_type=str(day.get("training_type") or ""),
        after_main_set=str(day.get("main_set") or ""),
    )


def _add_plan_level_speed_calibration(repaired: Dict[str, Any], severity: str) -> HMPRepairAction:
    note = "HMP修复：105-110% HMP按当前5K/8K/10K能力校准；未补成绩前降为体感10K强度。"
    target_day = _first_hmp_speed_day(repaired)
    if target_day is not None:
        before_main = str(target_day.get("main_set") or "")
        target_day["main_set"] = before_main + "；按当前5K/8K/10K能力校准"
        target_day["notes"] = _append_note(str(target_day.get("notes") or ""), note)
        return HMPRepairAction(
            constraint_id="dynamic_hmp_calibration",
            severity=severity,
            week_index=None,
            day=str(target_day.get("day") or ""),
            action="速度课已补充当前5K/8K/10K校准说明。",
            before_training_type=str(target_day.get("training_type") or ""),
            before_main_set=before_main,
            after_training_type=str(target_day.get("training_type") or ""),
            after_main_set=str(target_day.get("main_set") or ""),
        )

    _append_protocol_note(repaired, note)
    return HMPRepairAction(
        constraint_id="dynamic_hmp_calibration",
        severity=severity,
        week_index=None,
        day="",
        action="协议层已补充当前5K/8K/10K校准要求。",
    )


def _add_plan_level_volume_scaling_note(
    repaired: Dict[str, Any],
    severity: str,
    week_index: Optional[int],
) -> HMPRepairAction:
    note = "HMP修复：不得照搬Sub-70跑量，周总量与长距离容量需按输入周跑量缩放。"
    _append_protocol_note(repaired, note)
    week = _find_week(repaired, week_index)
    if week is not None:
        week["execution_reminder"] = _append_note(str(week.get("execution_reminder") or ""), note)
    return HMPRepairAction(
        constraint_id="no_sub70_volume_copy",
        severity=severity,
        week_index=week_index,
        day="",
        action="已在协议和周执行提醒中写入跑量缩放要求。",
    )


def _set_day(day: Dict[str, Any], *, training_type: str, main_set: str, note_suffix: str) -> None:
    day["training_type"] = training_type
    day["main_set"] = main_set
    day["notes"] = _append_note(str(day.get("notes") or ""), note_suffix)


def _append_protocol_note(plan_dict: Dict[str, Any], note: str) -> None:
    protocol = plan_dict.get("half_marathon_protocol")
    if not isinstance(protocol, dict):
        return
    notes = protocol.get("repair_notes")
    if not isinstance(notes, list):
        notes = []
    if note not in notes:
        notes.append(note)
    protocol["repair_notes"] = notes


def _append_note(existing: str, note: str) -> str:
    if note in existing:
        return existing
    if not existing.strip():
        return note
    return f"{existing} {note}"


def _find_week(plan_dict: Dict[str, Any], week_index: Optional[int]) -> Optional[Dict[str, Any]]:
    if not week_index:
        return None
    for week in plan_dict.get("week_plans") or []:
        if isinstance(week, dict) and _safe_int(week.get("week_index")) == week_index:
            return week
    return None


def _find_day(plan_dict: Dict[str, Any], week_index: Optional[int], day_label: str) -> Optional[Dict[str, Any]]:
    week = _find_week(plan_dict, week_index)
    if week is None:
        return None
    for day in week.get("days") or []:
        if isinstance(day, dict) and str(day.get("day") or "").strip() == day_label:
            return day
    return None


def _first_hmp_speed_day(plan_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    speed_tokens = ("105% HMP", "105%HMP", "107-110% HMP", "110% HMP", "110%HMP", "hm_105", "hm_110")
    for week in plan_dict.get("week_plans") or []:
        if not isinstance(week, dict):
            continue
        for day in week.get("days") or []:
            if not isinstance(day, dict):
                continue
            text = " ".join(str(day.get(key) or "") for key in ("training_type", "main_set", "notes"))
            if any(token in text for token in speed_tokens):
                return day
    return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "HMPRepairAction",
    "apply_half_marathon_repairs",
]
