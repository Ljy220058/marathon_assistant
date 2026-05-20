from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from marathon_qa_assistant.core.half_marathon_protocol import HM_PHASE_RULES, HM_WORKOUT_RULES


@dataclass(frozen=True)
class HMPSessionProposal:
    role: str
    workout_id: str
    training_type: str
    main_set: str
    note: str
    reason: str
    repair_action: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compose_hmp_week_sessions(
    *,
    week_index: int,
    total_weeks: int,
    phase_id: str,
    archetype_id: str,
    recent_marathon: bool = False,
    weekly_volume_km: Optional[float] = None,
    speed_calibration_available: bool = True,
    pace_calibration_status: str = "",
    capacity_budget: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """按基石文章的 HMP 进阶逻辑，为一周生成主课替换建议。"""
    if not phase_id:
        return {"active": False, "sessions": [], "repair_notes": []}

    weeks_to_race = max(1, int(total_weeks or week_index) - int(week_index) + 1)
    low_volume = weekly_volume_km is not None and weekly_volume_km < 45
    budget = capacity_budget or {}
    sessions: List[HMPSessionProposal] = []
    repair_notes: List[str] = []

    if phase_id == "introductory":
        sessions.append(_proposal(
            role="primary",
            workout_id="hm_intro_fartlek_hills",
            training_type="法特莱克",
            main_set="hm_intro_fartlek_hills：35分钟体感法特莱克，含6×30秒轻快跑，强度控制在75-85% HMP",
            note="HMP导入期：恢复优先，用短变速和坡跑重新引入速度，不追求固定配速。",
            reason="导入期先恢复身体和精神能量，避免过早进入95/100% HMP高消耗课。",
            repair_action="若原计划出现95/100/105% HMP硬课，降级为导入期法特莱克或坡冲。",
        ))
        sessions.append(_proposal(
            role="secondary",
            workout_id="hm_intro_fartlek_hills",
            training_type="坡道训练",
            main_set="hm_intro_fartlek_hills：8×10秒坡冲，完全走回恢复；其余保持轻松跑",
            note="短坡冲只做神经肌肉激活，不做力竭间歇。",
            reason="刚比完全马或疲劳期需要低代价速度刺激。",
            repair_action="疲劳明显时取消坡冲，改为30-40分钟恢复跑。",
        ))
        repair_notes.append("导入期自动屏蔽95/100/105/107-110% HMP硬课。")
        return _result(phase_id, archetype_id, sessions, repair_notes, budget)

    if phase_id == "general":
        sessions.append(_proposal(
            role="primary",
            workout_id="hm_base_threshold_progression",
            training_type="有氧阈值训练",
            main_set=_base_threshold_main_set(week_index),
            note="HMP基础期：先补阈值、有氧功率和跑步经济性。",
            reason="基础阶段优先建立多配速体能基础，不提前堆100% HMP核心课。",
            repair_action="若出现100% HMP核心课，替换为阈值巡航或渐进跑。",
        ))
        sessions.append(_proposal(
            role="secondary",
            workout_id="hm_110_support_speed" if archetype_id in {"marathoner_aerobic_power_gap", "endurance_speed_rebuild"} else "hm_base_threshold_progression",
            training_type="法特莱克" if archetype_id in {"marathoner_aerobic_power_gap", "endurance_speed_rebuild"} else "渐进跑",
            main_set=(
                _support_speed_main_set(calibrated=speed_calibration_available, capacity_budget=budget)
                if archetype_id in {"marathoner_aerobic_power_gap", "endurance_speed_rebuild"}
                else "hm_base_threshold_progression：45分钟肯尼亚式渐进跑，从轻松跑渐进至85% HMP"
            ),
            note="基础期第二刺激保持轻量，避免周内双大课。",
            reason="按画像补速度储备或持续输出能力。",
            repair_action="若疲劳或5K能力不足，改为轻松跑加6×100m短冲。",
        ))
        return _result(phase_id, archetype_id, sessions, repair_notes, budget)

    if phase_id == "race_supportive":
        if archetype_id == "speed_based_endurance_gap":
            primary = _support_endurance(week_index, long=False)
            secondary = _specific_speed(week_index, calibrated=speed_calibration_available, capacity_budget=budget)
        elif archetype_id in {"endurance_speed_rebuild", "marathoner_aerobic_power_gap"}:
            primary = _specific_speed(week_index, calibrated=speed_calibration_available, capacity_budget=budget)
            secondary = _support_speed(calibrated=speed_calibration_available, capacity_budget=budget)
        else:
            primary = _support_endurance(week_index, long=False)
            secondary = _specific_speed(week_index, calibrated=speed_calibration_available, capacity_budget=budget)
        sessions.extend([primary, secondary])
        sessions.append(_support_endurance(week_index, long=True, role="long_run", low_volume=low_volume, capacity_budget=budget))
        if not speed_calibration_available:
            repair_notes.append("缺少当前5K/10K成绩，速度课自动降为体感10K强度。")
        if pace_calibration_status == "ambitious_target":
            repair_notes.append("目标HMP快于当前能力估计，本周按当前能力配速保守推进。")
        if budget.get("quality_sessions_max") == 1:
            repair_notes.append("容量预算仅允许1堂质量课，其余专项刺激已保守压缩。")
        return _result(phase_id, archetype_id, sessions, repair_notes, budget)

    if phase_id == "race_specific":
        if weeks_to_race > 6:
            sessions.append(_support_endurance(week_index, long=False))
            repair_notes.append("距离比赛超过6周时自动延后100% HMP核心课。")
        else:
            sessions.append(_race_specific_float(weeks_to_race, capacity_budget=budget))
        if weeks_to_race > 2:
            sessions.append(_specific_speed(week_index, calibrated=speed_calibration_available, capacity_budget=budget))
        sessions.append(_support_endurance(week_index, long=True, role="long_run", low_volume=low_volume, capacity_budget=budget))
        if not speed_calibration_available:
            repair_notes.append("缺少当前5K/10K成绩，比赛专项速度课自动保守降级。")
        if pace_calibration_status == "ambitious_target":
            repair_notes.append("目标HMP快于当前能力估计，核心课容量不按目标配速上限推进。")
        if budget.get("quality_sessions_max") == 1:
            repair_notes.append("容量预算仅允许1堂质量课，比赛专项刺激已压缩。")
        return _result(phase_id, archetype_id, sessions, repair_notes, budget)

    phase_rule = HM_PHASE_RULES.get(phase_id)
    return {
        "active": True,
        "phase_id": phase_id,
        "phase_label": phase_rule.label if phase_rule else phase_id,
        "archetype_id": archetype_id,
        "sessions": [],
        "repair_notes": repair_notes,
    }


def _proposal(
    *,
    role: str,
    workout_id: str,
    training_type: str,
    main_set: str,
    note: str,
    reason: str,
    repair_action: str,
) -> HMPSessionProposal:
    return HMPSessionProposal(
        role=role,
        workout_id=workout_id,
        training_type=training_type,
        main_set=main_set,
        note=note,
        reason=reason,
        repair_action=repair_action,
    )


def _result(
    phase_id: str,
    archetype_id: str,
    sessions: List[HMPSessionProposal],
    repair_notes: List[str],
    capacity_budget: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    phase_rule = HM_PHASE_RULES.get(phase_id)
    return {
        "active": True,
        "phase_id": phase_id,
        "phase_label": phase_rule.label if phase_rule else phase_id,
        "phase_objective": phase_rule.objective if phase_rule else "",
        "archetype_id": archetype_id,
        "sessions": [session.to_dict() for session in sessions],
        "repair_notes": repair_notes,
        "capacity_budget": capacity_budget or {},
    }


def _base_threshold_main_set(week_index: int) -> str:
    if week_index % 3 == 0:
        return "hm_base_threshold_progression：50分钟渐进跑，从轻松跑逐步进到85% HMP"
    if week_index % 2 == 0:
        return "hm_base_threshold_progression：4×8分钟阈值巡航，组间2分钟慢跑，整体不超过85% HMP"
    return "hm_base_threshold_progression：3×10分钟有氧阈值，组间3分钟慢跑，控制在75-85% HMP"


def _support_endurance(
    week_index: int,
    *,
    long: bool,
    role: str = "primary",
    low_volume: bool = False,
    capacity_budget: Optional[Dict[str, Any]] = None,
) -> HMPSessionProposal:
    budget = capacity_budget or {}
    if long:
        budget_cap = _budget_float(budget, "long_run_max_km", 18.0)
        distance = 14 if low_volume else min(budget_cap, 14 + (week_index % 4) * 2)
        main_set = f"hm_90_support_endurance：{distance}km @90% HMP 稳定跑，作为95% HMP长距离快速跑前置支撑"
    else:
        budget_cap = _budget_float(budget, "hmp_90_max_km", 16.0)
        distance = 10 if low_volume else min(budget_cap, 10 + (week_index % 3) * 2)
        main_set = f"hm_90_support_endurance：{distance}km 分段递进，86%-88%-90% HMP"
    return _proposal(
        role=role,
        workout_id="hm_90_support_endurance",
        training_type="长距离" if role == "long_run" else "渐进跑",
        main_set=main_set,
        note="先建立90% HMP耐力支撑，再进入95% HMP上限课。",
        reason="专项构建期需要90-95% HMP耐力支撑。",
        repair_action="若原计划直接跳到20-25km @95% HMP，先替换为90% HMP支撑跑。",
    )


def _specific_speed(week_index: int, *, calibrated: bool, capacity_budget: Optional[Dict[str, Any]] = None) -> HMPSessionProposal:
    budget = capacity_budget or {}
    cap = _budget_float(budget, "hmp_105_total_max_km", 8.0)
    if cap <= 4.5:
        main_set = "hm_105_specific_speed：6×600m @105% HMP，组间200m慢跑；按当前5K/10K能力校准"
    elif cap <= 6.5:
        main_set = "hm_105_specific_speed：6×800m @105% HMP，组间300m慢跑；按当前5K/10K能力校准"
    elif week_index % 3 == 0:
        main_set = "hm_105_specific_speed：4×2km @105% HMP，组间3分钟慢跑；按当前10K能力校准"
    elif week_index % 2 == 0:
        main_set = "hm_105_specific_speed：6×1200m @105% HMP，组间400m慢跑；按当前8K/10K能力校准"
    else:
        main_set = "hm_105_specific_speed：8×800m @105% HMP，组间300m慢跑；按当前5K/10K能力校准"
    if not calibrated:
        main_set += "（未校准时降到体感10K强度）"
    if cap < 8.0:
        main_set += "；已按容量预算缩短总量"
    return _proposal(
        role="secondary",
        workout_id="hm_105_specific_speed",
        training_type="间歇跑",
        main_set=main_set,
        note="HMP专项速度课必须按当前5K/8K/10K能力校准。",
        reason="建立8K/10K速度储备，让目标HMP更轻松。",
        repair_action="缺少当前短距离能力时，降级为短法特莱克或坡冲。",
    )


def _support_speed(*, calibrated: bool, capacity_budget: Optional[Dict[str, Any]] = None) -> HMPSessionProposal:
    main_set = _support_speed_main_set(calibrated=calibrated, capacity_budget=capacity_budget)
    return _proposal(
        role="secondary",
        workout_id="hm_110_support_speed",
        training_type="法特莱克",
        main_set=main_set,
        note="辅助速度课用于补VO2max和速度上限，不做力竭。",
        reason="耐力型或久疏战阵跑者需要重建有氧功率和速度储备。",
        repair_action="耐力型跑者若无法稳定完成，降到105% HMP或改短坡冲。",
    )


def _support_speed_main_set(*, calibrated: bool, capacity_budget: Optional[Dict[str, Any]] = None) -> str:
    budget = capacity_budget or {}
    cap = _budget_float(budget, "hmp_110_total_max_km", 4.0)
    main_set = (
        "hm_110_support_speed：3-4-5-4-3分钟混合法特莱克，快段约107-110% HMP体感，按当前5K能力校准"
        if calibrated
        else "hm_110_support_speed：3-4-5-4-3分钟混合法特莱克；缺少当前5K/10K成绩，快段降为体感10K强度"
    )
    if cap <= 2.5:
        main_set = (
            "hm_110_support_speed：8×45秒轻快跑，组间75秒慢跑；快段控制在体感10K强度"
            if calibrated
            else "hm_110_support_speed：8×45秒轻快跑，组间75秒慢跑；缺少当前5K/10K成绩，按体感10K强度"
        )
    elif cap < 4.0:
        main_set += "；已按容量预算缩短总量"
    return main_set


def _race_specific_float(weeks_to_race: int, capacity_budget: Optional[Dict[str, Any]] = None) -> HMPSessionProposal:
    budget = capacity_budget or {}
    cap = _budget_float(budget, "hmp_100_total_max_km", 8.0)
    if cap <= 4.5:
        main_set = "hm_100_float_intervals：1km@100% HMP / 1km巡航恢复 × 4，累计HMP约4km"
    elif cap <= 6.5:
        main_set = "hm_100_float_intervals：2km@100% HMP / 1km巡航恢复 × 3，累计HMP约6km"
    elif weeks_to_race <= 2:
        main_set = "hm_100_float_intervals：3km@100% HMP / 1km巡航恢复 × 3，累计HMP约9km，赛前10-15天完成"
    elif weeks_to_race <= 4:
        main_set = "hm_100_float_intervals：2km@100% HMP / 1km巡航恢复 × 4，累计HMP约8km"
    else:
        main_set = "hm_100_float_intervals：1km@100% HMP / 1km巡航恢复 × 5，累计HMP约5km"
    if cap < 8.0:
        main_set += "；已按容量预算缩短总量"
    return _proposal(
        role="primary",
        workout_id="hm_100_float_intervals",
        training_type="半马专项",
        main_set=main_set,
        note="100% HMP核心课按赛前6/4/2周逐步推进。",
        reason="比赛专项阶段训练目标配速代谢效率和巡航恢复能力。",
        repair_action="若距离比赛超过6周，延后本课并改为90% HMP支撑跑。",
    )


def build_hmp_repair_suggestions(validation: Dict[str, Any]) -> List[Dict[str, str]]:
    suggestions: List[Dict[str, str]] = []
    for issue in validation.get("issues") or []:
        if not isinstance(issue, dict):
            continue
        constraint_id = str(issue.get("constraint_id") or "")
        if constraint_id == "marathon_recovery_intro":
            action = "改为hm_intro_fartlek_hills或恢复跑，至少保留1-2周导入。"
        elif constraint_id == "progress_long_fast_run":
            action = "把长距离95% HMP降级为hm_90_support_endurance或较短95% HMP。"
        elif constraint_id == "race_specific_timing":
            action = "100% HMP课延后到赛前6周内，并按1km->2km->3km进阶。"
        elif constraint_id == "dynamic_hmp_calibration":
            action = "补当前5K/8K/10K能力；未补前把105-110% HMP降为体感10K强度。"
        elif constraint_id == "environment_or_fatigue_downgrade":
            action = "按体感缩短主课、延后关键课，或改为恢复跑。"
        elif constraint_id == "quality_recovery_gap":
            action = "移动后一堂质量课，保证约48小时恢复。"
        elif constraint_id == "no_sub70_volume_copy":
            action = "按输入周跑量重新缩放周总量和单次长距离。"
        elif constraint_id == "capacity_budget_exceeded":
            action = "按容量预算缩短95/100/105% HMP累计量，或把超额课降级为90% HMP支撑跑。"
        else:
            action = str(issue.get("recommendation") or "按验证建议下调风险。")
        suggestions.append({
            "constraint_id": constraint_id,
            "severity": str(issue.get("severity") or "warning"),
            "week_index": str(issue.get("week_index") or ""),
            "day": str(issue.get("day") or ""),
            "action": action,
        })
    return suggestions


__all__ = [
    "HMPSessionProposal",
    "compose_hmp_week_sessions",
    "build_hmp_repair_suggestions",
]


def _budget_float(budget: Dict[str, Any], key: str, default: float) -> float:
    try:
        value = budget.get(key, default)
        return float(value)
    except (TypeError, ValueError, AttributeError):
        return float(default)
