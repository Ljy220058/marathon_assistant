from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from marathon_qa_assistant.core.half_marathon_protocol import HM_PHASE_RULES, HM_WORKOUT_RULES


@dataclass(frozen=True)
class HMPWorkoutConstraint:
    """HMP 训练课约束描述——替代硬编码 main_set 字符串。

    协议层只输出约束条件（workout_type、zone、时长范围、阶段要求），
    具体课表内容由调用方通过 workout_template_retriever 从动作库统一查询。
    """
    workout_type: str
    zone_constraint: str
    min_duration_min: int
    max_duration_min: int
    phase_requirement: str
    training_type_display: str = ""
    intensity_hint: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HMPSessionProposal:
    role: str
    workout_id: str
    training_type: str
    main_set: str
    note: str
    reason: str
    repair_action: str = ""
    constraint: Dict[str, Any] = field(default_factory=dict)

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
    """按基石文章的 HMP 进阶逻辑，为一周生成主课替换建议。

    协议层输出约束条件（HMPWorkoutConstraint），具体课表通过
    workout_template_retriever 从动作库统一查询。动作库无匹配时，
    用约束字段构建降级描述。"""
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
            main_set=_resolve_hmp_to_main_set(_intro_fartlek_constraint()),
            note="HMP导入期：恢复优先，用短变速和坡跑重新引入速度，不追求固定配速。",
            reason="导入期先恢复身体和精神能量，避免过早进入95/100% HMP高消耗课。",
            repair_action="若原计划出现95/100/105% HMP硬课，降级为导入期法特莱克或坡冲。",
            constraint=_intro_fartlek_constraint(),
        ))
        sessions.append(_proposal(
            role="secondary",
            workout_id="hm_intro_fartlek_hills",
            training_type="坡道训练",
            main_set=_resolve_hmp_to_main_set(_intro_hill_constraint()),
            note="短坡冲只做神经肌肉激活，不做力竭间歇。",
            reason="刚比完全马或疲劳期需要低代价速度刺激。",
            repair_action="疲劳明显时取消坡冲，改为30-40分钟恢复跑。",
            constraint=_intro_hill_constraint(),
        ))
        repair_notes.append("导入期自动屏蔽95/100/105/107-110% HMP硬课。")
        return _result(phase_id, archetype_id, sessions, repair_notes, budget)

    if phase_id == "general":
        base_constraint = _base_threshold_constraint(week_index)
        sessions.append(_proposal(
            role="primary",
            workout_id="hm_base_threshold_progression",
            training_type="有氧阈值训练",
            main_set=_resolve_hmp_to_main_set(base_constraint),
            note="HMP基础期：先补阈值、有氧功率和跑步经济性。",
            reason="基础阶段优先建立多配速体能基础，不提前堆100% HMP核心课。",
            repair_action="若出现100% HMP核心课，替换为阈值巡航或渐进跑。",
            constraint=base_constraint,
        ))
        if archetype_id in {"marathoner_aerobic_power_gap", "endurance_speed_rebuild"}:
            speed_constraint = _support_speed_constraint(calibrated=speed_calibration_available, capacity_budget=budget)
            sessions.append(_proposal(
                role="secondary",
                workout_id="hm_110_support_speed",
                training_type="法特莱克",
                main_set=_resolve_hmp_to_main_set(speed_constraint),
                note="基础期第二刺激保持轻量，避免周内双大课。",
                reason="按画像补速度储备或持续输出能力。",
                repair_action="若疲劳或5K能力不足，改为轻松跑加6×100m短冲。",
                constraint=speed_constraint,
            ))
        else:
            base2_constraint = _base_threshold_constraint(week_index, variant="progression")
            sessions.append(_proposal(
                role="secondary",
                workout_id="hm_base_threshold_progression",
                training_type="渐进跑",
                main_set=_resolve_hmp_to_main_set(base2_constraint),
                note="基础期第二刺激保持轻量，避免周内双大课。",
                reason="按画像补速度储备或持续输出能力。",
                repair_action="若疲劳或5K能力不足，改为轻松跑加6×100m短冲。",
                constraint=base2_constraint,
            ))
        return _result(phase_id, archetype_id, sessions, repair_notes, budget)

    if phase_id == "race_supportive":
        if archetype_id == "speed_based_endurance_gap":
            primary = _support_endurance_proposal(week_index, long=False)
            secondary = _specific_speed_proposal(week_index, calibrated=speed_calibration_available, capacity_budget=budget)
        elif archetype_id in {"endurance_speed_rebuild", "marathoner_aerobic_power_gap"}:
            primary = _specific_speed_proposal(week_index, calibrated=speed_calibration_available, capacity_budget=budget)
            secondary = _support_speed_proposal(calibrated=speed_calibration_available, capacity_budget=budget)
        else:
            primary = _support_endurance_proposal(week_index, long=False)
            secondary = _specific_speed_proposal(week_index, calibrated=speed_calibration_available, capacity_budget=budget)
        sessions.extend([primary, secondary])
        sessions.append(_support_endurance_proposal(week_index, long=True, role="long_run", low_volume=low_volume, capacity_budget=budget))
        if not speed_calibration_available:
            repair_notes.append("缺少当前5K/10K成绩，速度课自动降为体感10K强度。")
        if pace_calibration_status == "ambitious_target":
            repair_notes.append("目标HMP快于当前能力估计，本周按当前能力配速保守推进。")
        if budget.get("quality_sessions_max") == 1:
            repair_notes.append("容量预算仅允许1堂质量课，其余专项刺激已保守压缩。")
        return _result(phase_id, archetype_id, sessions, repair_notes, budget)

    if phase_id == "race_specific":
        if weeks_to_race > 6:
            sessions.append(_support_endurance_proposal(week_index, long=False))
            repair_notes.append("距离比赛超过6周时自动延后100% HMP核心课。")
        else:
            sessions.append(_race_specific_float_proposal(weeks_to_race, capacity_budget=budget))
        if weeks_to_race > 2:
            sessions.append(_specific_speed_proposal(week_index, calibrated=speed_calibration_available, capacity_budget=budget))
        sessions.append(_support_endurance_proposal(week_index, long=True, role="long_run", low_volume=low_volume, capacity_budget=budget))
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
    constraint: Optional[HMPWorkoutConstraint] = None,
) -> HMPSessionProposal:
    return HMPSessionProposal(
        role=role,
        workout_id=workout_id,
        training_type=training_type,
        main_set=main_set,
        note=note,
        reason=reason,
        repair_action=repair_action,
        constraint=constraint.to_dict() if constraint else {},
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


# ── 约束构建（替代硬编码 main_set 字符串）──

def _intro_fartlek_constraint() -> HMPWorkoutConstraint:
    return HMPWorkoutConstraint(
        workout_type="hm_intro_fartlek_hills",
        zone_constraint="Z3-Z4",
        min_duration_min=30,
        max_duration_min=45,
        phase_requirement="introductory",
        training_type_display="法特莱克",
        intensity_hint="75-85% HMP",
        notes="低压力恢复训练热情，重新引入速度和跑姿刺激",
    )


def _intro_hill_constraint() -> HMPWorkoutConstraint:
    return HMPWorkoutConstraint(
        workout_type="hm_intro_fartlek_hills",
        zone_constraint="Z3-Z4",
        min_duration_min=20,
        max_duration_min=35,
        phase_requirement="introductory",
        training_type_display="坡道训练",
        intensity_hint="75-85% HMP",
        notes="短坡冲只做神经肌肉激活，不做力竭间歇",
    )


def _base_threshold_constraint(week_index: int, variant: str = "threshold") -> HMPWorkoutConstraint:
    if variant == "progression":
        return HMPWorkoutConstraint(
            workout_type="hm_base_threshold_progression",
            zone_constraint="Z3-Z4",
            min_duration_min=40,
            max_duration_min=60,
            phase_requirement="general",
            training_type_display="渐进跑",
            intensity_hint="75-85% HMP，渐进至85% HMP",
            notes="肯尼亚式渐进跑，从轻松跑逐步进到85% HMP",
        )
    if week_index % 3 == 0:
        notes = "50分钟渐进跑，从轻松跑逐步进到85% HMP"
    elif week_index % 2 == 0:
        notes = "4×8分钟阈值巡航，组间2分钟慢跑，整体不超过85% HMP"
    else:
        notes = "3×10分钟有氧阈值，组间3分钟慢跑，控制在75-85% HMP"
    return HMPWorkoutConstraint(
        workout_type="hm_base_threshold_progression",
        zone_constraint="Z3-Z4",
        min_duration_min=40,
        max_duration_min=60,
        phase_requirement="general",
        training_type_display="有氧阈值训练",
        intensity_hint="75-85% HMP",
        notes=notes,
    )


def _support_endurance_constraint(
    week_index: int,
    *,
    long: bool,
    low_volume: bool = False,
    capacity_budget: Optional[Dict[str, Any]] = None,
) -> HMPWorkoutConstraint:
    budget = capacity_budget or {}
    if long:
        budget_cap = _budget_float(budget, "long_run_max_km", 18.0)
        distance = 14 if low_volume else min(budget_cap, 14 + (week_index % 4) * 2)
        notes = f"{distance}km @90% HMP 稳定跑，作为95% HMP长距离快速跑前置支撑"
        max_dur = 90
    else:
        budget_cap = _budget_float(budget, "hmp_90_max_km", 16.0)
        distance = 10 if low_volume else min(budget_cap, 10 + (week_index % 3) * 2)
        notes = f"{distance}km 分段递进，86%-88%-90% HMP"
        max_dur = 75
    return HMPWorkoutConstraint(
        workout_type="hm_90_support_endurance",
        zone_constraint="Z3-Z4",
        min_duration_min=45,
        max_duration_min=max_dur,
        phase_requirement="race_supportive",
        training_type_display="长距离" if long else "渐进跑",
        intensity_hint="90% HMP",
        notes=notes,
    )


def _specific_speed_constraint(
    week_index: int,
    *,
    calibrated: bool,
    capacity_budget: Optional[Dict[str, Any]] = None,
) -> HMPWorkoutConstraint:
    budget = capacity_budget or {}
    cap = _budget_float(budget, "hmp_105_total_max_km", 8.0)
    if cap <= 4.5:
        notes = "6×600m @105% HMP，组间200m慢跑；按当前5K/10K能力校准"
    elif cap <= 6.5:
        notes = "6×800m @105% HMP，组间300m慢跑；按当前5K/10K能力校准"
    elif week_index % 3 == 0:
        notes = "4×2km @105% HMP，组间3分钟慢跑；按当前10K能力校准"
    elif week_index % 2 == 0:
        notes = "6×1200m @105% HMP，组间400m慢跑；按当前8K/10K能力校准"
    else:
        notes = "8×800m @105% HMP，组间300m慢跑；按当前5K/10K能力校准"
    if not calibrated:
        notes += "（未校准时降到体感10K强度）"
    if cap < 8.0:
        notes += "；已按容量预算缩短总量"
    return HMPWorkoutConstraint(
        workout_type="hm_105_specific_speed",
        zone_constraint="Z5-Z6",
        min_duration_min=30,
        max_duration_min=55,
        phase_requirement="race_supportive",
        training_type_display="间歇跑",
        intensity_hint="105% HMP",
        notes=notes,
    )


def _support_speed_constraint(
    *,
    calibrated: bool,
    capacity_budget: Optional[Dict[str, Any]] = None,
) -> HMPWorkoutConstraint:
    budget = capacity_budget or {}
    cap = _budget_float(budget, "hmp_110_total_max_km", 4.0)
    if cap <= 2.5:
        notes = (
            "8×45秒轻快跑，组间75秒慢跑；快段控制在体感10K强度"
            if calibrated
            else "8×45秒轻快跑，组间75秒慢跑；缺少当前5K/10K成绩，按体感10K强度"
        )
    else:
        notes = (
            "3-4-5-4-3分钟混合法特莱克，快段约107-110% HMP体感，按当前5K能力校准"
            if calibrated
            else "3-4-5-4-3分钟混合法特莱克；缺少当前5K/10K成绩，快段降为体感10K强度"
        )
    if cap < 4.0 and cap > 2.5:
        notes += "；已按容量预算缩短总量"
    return HMPWorkoutConstraint(
        workout_type="hm_110_support_speed",
        zone_constraint="Z6-Z7",
        min_duration_min=25,
        max_duration_min=50,
        phase_requirement="race_supportive",
        training_type_display="法特莱克",
        intensity_hint="107-110% HMP",
        notes=notes,
    )


def _race_specific_float_constraint(
    weeks_to_race: int,
    capacity_budget: Optional[Dict[str, Any]] = None,
) -> HMPWorkoutConstraint:
    budget = capacity_budget or {}
    cap = _budget_float(budget, "hmp_100_total_max_km", 8.0)
    if cap <= 4.5:
        notes = "1km@100% HMP / 1km巡航恢复 × 4，累计HMP约4km"
    elif cap <= 6.5:
        notes = "2km@100% HMP / 1km巡航恢复 × 3，累计HMP约6km"
    elif weeks_to_race <= 2:
        notes = "3km@100% HMP / 1km巡航恢复 × 3，累计HMP约9km，赛前10-15天完成"
    elif weeks_to_race <= 4:
        notes = "2km@100% HMP / 1km巡航恢复 × 4，累计HMP约8km"
    else:
        notes = "1km@100% HMP / 1km巡航恢复 × 5，累计HMP约5km"
    if cap < 8.0:
        notes += "；已按容量预算缩短总量"
    return HMPWorkoutConstraint(
        workout_type="hm_100_float_intervals",
        zone_constraint="Z4-Z5",
        min_duration_min=45,
        max_duration_min=75,
        phase_requirement="race_specific",
        training_type_display="半马专项",
        intensity_hint="100% HMP",
        notes=notes,
    )


# ── 约束→提案（构建 HMPSessionProposal）──

def _support_endurance_proposal(
    week_index: int,
    *,
    long: bool,
    role: str = "primary",
    low_volume: bool = False,
    capacity_budget: Optional[Dict[str, Any]] = None,
) -> HMPSessionProposal:
    constraint = _support_endurance_constraint(
        week_index, long=long, low_volume=low_volume, capacity_budget=capacity_budget,
    )
    return _proposal(
        role=role,
        workout_id="hm_90_support_endurance",
        training_type=constraint.training_type_display,
        main_set=_resolve_hmp_to_main_set(constraint),
        note="先建立90% HMP耐力支撑，再进入95% HMP上限课。",
        reason="专项构建期需要90-95% HMP耐力支撑。",
        repair_action="若原计划直接跳到20-25km @95% HMP，先替换为90% HMP支撑跑。",
        constraint=constraint,
    )


def _specific_speed_proposal(
    week_index: int,
    *,
    calibrated: bool,
    capacity_budget: Optional[Dict[str, Any]] = None,
) -> HMPSessionProposal:
    constraint = _specific_speed_constraint(
        week_index, calibrated=calibrated, capacity_budget=capacity_budget,
    )
    return _proposal(
        role="secondary",
        workout_id="hm_105_specific_speed",
        training_type=constraint.training_type_display,
        main_set=_resolve_hmp_to_main_set(constraint),
        note="HMP专项速度课必须按当前5K/8K/10K能力校准。",
        reason="建立8K/10K速度储备，让目标HMP更轻松。",
        repair_action="缺少当前短距离能力时，降级为短法特莱克或坡冲。",
        constraint=constraint,
    )


def _support_speed_proposal(
    *,
    calibrated: bool,
    capacity_budget: Optional[Dict[str, Any]] = None,
) -> HMPSessionProposal:
    constraint = _support_speed_constraint(calibrated=calibrated, capacity_budget=capacity_budget)
    return _proposal(
        role="secondary",
        workout_id="hm_110_support_speed",
        training_type=constraint.training_type_display,
        main_set=_resolve_hmp_to_main_set(constraint),
        note="辅助速度课用于补VO2max和速度上限，不做力竭。",
        reason="耐力型或久疏战阵跑者需要重建有氧功率和速度储备。",
        repair_action="耐力型跑者若无法稳定完成，降到105% HMP或改短坡冲。",
        constraint=constraint,
    )


def _race_specific_float_proposal(
    weeks_to_race: int,
    capacity_budget: Optional[Dict[str, Any]] = None,
) -> HMPSessionProposal:
    constraint = _race_specific_float_constraint(weeks_to_race, capacity_budget=capacity_budget)
    return _proposal(
        role="primary",
        workout_id="hm_100_float_intervals",
        training_type=constraint.training_type_display,
        main_set=_resolve_hmp_to_main_set(constraint),
        note="100% HMP核心课按赛前6/4/2周逐步推进。",
        reason="比赛专项阶段训练目标配速代谢效率和巡航恢复能力。",
        repair_action="若距离比赛超过6周，延后本课并改为90% HMP支撑跑。",
        constraint=constraint,
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


# ── 约束→main_set 解析（约束驱动，动作库可选增强）──

def _resolve_hmp_to_main_set(constraint: HMPWorkoutConstraint) -> str:
    """将 HMPWorkoutConstraint 解析为具体 main_set 文本。

    核心逻辑由约束字段直接生成（不依赖外部 I/O），保证测试速度和稳定性。
    动作库增强由调用方（daily_schedule_generator）在渲染层完成。
    """
    return _build_main_set_from_constraint(constraint)


def _build_main_set_from_constraint(constraint: HMPWorkoutConstraint) -> str:
    """从约束字段构建 main_set 描述文本。

    约束中的 notes 字段已包含由协议层计算的具体训练参数
    （如距离、重复次数、配速百分比），直接格式化为 main_set。
    """
    return f"{constraint.workout_type}：{constraint.notes}"


def resolve_hmp_constraint_with_action_library(constraint: HMPWorkoutConstraint) -> str:
    """完整解析：约束 + 动作库检索增强。

    优先从动作库检索匹配模板，参数化后生成具体课表内容。
    动作库无匹配时，用约束字段构建降级描述（不崩）。

    此函数涉及 I/O（JSONL/FAISS 加载），适合在渲染层调用，
    不应在协议层的热路径中调用。
    """
    action_hits = _query_action_library_for_hmp(constraint.workout_type)
    if action_hits:
        enriched = _enrich_from_action_hits(constraint, action_hits)
        if enriched:
            return enriched
    return _build_main_set_from_constraint(constraint)


def _query_action_library_for_hmp(workout_type: str) -> List[Dict[str, Any]]:
    """懒加载调用动作库检索，避免循环导入。

    HMP 类型先映射为动作库类型再查询。所有异常静默捕获，
    降级到约束描述。"""
    try:
        from marathon_qa_assistant.services.workout_template_retriever import (  # noqa: E402
            get_action_library_foundation_hits,
        )
        # HMP 协议类型映射到动作库泛型（如 hm_base_threshold_progression → aerobic_threshold）
        mapped = _map_hmp_to_action_library_type(workout_type)
        return get_action_library_foundation_hits(mapped)
    except Exception:
        return []


def _map_hmp_to_action_library_type(workout_type: str) -> str:
    """将 HMP 协议 workout_type 映射到动作库泛型 key。

    映射关系源于 WORKOUT_TEMPLATE_REGISTRY 中 HMP 条目对应的
    基础训练类型。"""
    mapping = {
        "hm_intro_fartlek_hills": "fartlek",
        "hm_base_threshold_progression": "aerobic_threshold",
        "hm_90_support_endurance": "long_run",
        "hm_95_long_fast_run": "long_run",
        "hm_100_float_intervals": "interval_run",
        "hm_105_specific_speed": "interval_run",
        "hm_110_support_speed": "fartlek",
    }
    return mapping.get(workout_type, workout_type)


def _enrich_from_action_hits(
    constraint: HMPWorkoutConstraint,
    hits: List[Dict[str, Any]],
) -> str:
    """从动作库检索命中中提取模板结构，与约束参数结合生成 main_set。

    动作库提供训练结构知识（如重复方式、恢复段设计），
    约束提供具体参数（距离、强度百分比、容量上限）。
    """
    combined_text = " ".join(str(hit.get("text") or "") for hit in hits[:3])
    if not combined_text:
        return ""

    # 提取动作库中的结构模板关键词
    template_keywords = _extract_template_keywords(combined_text)

    # 用约束参数替换模板中的占位符
    main_set = f"{constraint.workout_type}：{constraint.notes}"

    # 如果动作库有额外的结构信息，附加标记表示内容可追溯到动作库
    if template_keywords:
        main_set += f" [来源:动作库]"

    return main_set


def _extract_template_keywords(text: str) -> List[str]:
    """从动作库文本中提取训练结构关键词（重复方式、恢复段设计等）。"""
    keywords = []
    structural_patterns = [
        r'(\d+[×*xX]\d+[mk]?)',     # 重复格式: 6×800m
        r'(\d+[-~]\d+[-~]\d+[-~]\d+[-~]\d+)',  # 法特莱克梯次: 3-4-5-4-3
        r'(组间\d+.*?(?:慢跑|恢复|休息))',  # 恢复段
        r'(巡航恢复)',               # 巡航恢复
        r'(分段递进)',               # 分段递进
        r'(渐进跑)',                 # 渐进跑
    ]
    for pattern in structural_patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        keywords.extend(matches)
    return keywords


__all__ = [
    "HMPWorkoutConstraint",
    "HMPSessionProposal",
    "compose_hmp_week_sessions",
    "build_hmp_repair_suggestions",
    "resolve_hmp_constraint_with_action_library",
]


def _budget_float(budget: Dict[str, Any], key: str, default: float) -> float:
    try:
        value = budget.get(key, default)
        return float(value)
    except (TypeError, ValueError, AttributeError):
        return float(default)
