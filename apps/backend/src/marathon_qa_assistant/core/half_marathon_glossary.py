from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Optional, Sequence


HMP_SOURCE_DOCS = (
    "Sub-70半程马拉松训练_图片OCR整理.md",
    "docs/half_marathon_hmp_protocol.md",
    "docs/product/half_marathon_hmp_protocol.md",
    "docs/product/reports/Sub-70半程马拉松训练_图片OCR整理.md",
)


@dataclass(frozen=True)
class HMPGlossaryTerm:
    id: str
    label: str
    definition: str
    training_implication: str
    source_docs: Sequence[str] = HMP_SOURCE_DOCS

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


HMP_GLOSSARY_TERMS: Dict[str, HMPGlossaryTerm] = {
    "hmp": HMPGlossaryTerm(
        id="hmp",
        label="HMP",
        definition="Half Marathon Pace，目标半马配速或当前半马能力配速。",
        training_implication="所有百分比课表都必须先区分目标 HMP 与当前能力 HMP，再决定是否保守下调。",
    ),
    "support_endurance_90": HMPGlossaryTerm(
        id="support_endurance_90",
        label="90% HMP 支撑耐力",
        definition="略慢于 HMP 的专项有氧支撑区间。",
        training_implication="常作为 95% HMP 长距离快跑和 100% HMP 核心课之前的前置能力。",
    ),
    "specific_endurance_95": HMPGlossaryTerm(
        id="specific_endurance_95",
        label="95% HMP 专项耐力",
        definition="接近比赛配速但仍保留余量的长距离专项耐力区间。",
        training_implication="属于高消耗课表，需要由短到长进阶，并按跑量和恢复能力缩放。",
    ),
    "race_specific_100": HMPGlossaryTerm(
        id="race_specific_100",
        label="100% HMP 比赛专项",
        definition="目标半马配速或当前半马能力配速的核心比赛专项强度。",
        training_implication="应主要放在赛前专项窗口内，从 1km 段逐步推进到 2-3km 段。",
    ),
    "cruise_recovery": HMPGlossaryTerm(
        id="cruise_recovery",
        label="巡航恢复",
        definition="100% HMP 间歇之间的受控恢复跑，而不是完全停走恢复。",
        training_implication="用于训练乳酸转运和配速稳定性，但会显著提高整堂课负荷。",
    ),
    "specific_speed_105": HMPGlossaryTerm(
        id="specific_speed_105",
        label="105% HMP 专项速度",
        definition="快于 HMP 的专项速度储备区间，接近 8K/10K 能力刺激。",
        training_implication="需要当前 5K/8K/10K 能力校准，不能机械套用目标配速。",
    ),
    "support_speed_107_110": HMPGlossaryTerm(
        id="support_speed_107_110",
        label="107-110% HMP 辅助速度",
        definition="发展速度上限、VO2max 和跑步经济性的辅助速度刺激。",
        training_implication="低跑量、疲劳或缺少短距离成绩时应优先改为短时间、低容量刺激。",
    ),
    "introductory_phase": HMPGlossaryTerm(
        id="introductory_phase",
        label="导入期",
        definition="从恢复或基础训练过渡到半马专项训练的低风险阶段。",
        training_implication="刚比完全马或准备期较短时，应先用轻法特莱克、坡跑和 90% HMP 支撑课导入。",
    ),
    "general_phase": HMPGlossaryTerm(
        id="general_phase",
        label="基础阶段",
        definition="以总跑量、多配速能力和基础有氧功率为核心的半马准备阶段。",
        training_implication="优先安排阈值、渐进跑、轻量速度刺激和长距离轻松跑，避免过早堆叠 100% HMP 大课。",
    ),
    "race_supportive_phase": HMPGlossaryTerm(
        id="race_supportive_phase",
        label="专项能力构建阶段",
        definition="在比赛专项期前建立 90-95% HMP 耐力支撑和 105-110% HMP 速度支撑的阶段。",
        training_implication="课表应围绕支撑能力递进，而不是直接跳到比赛日需求。",
    ),
    "race_specific_phase": HMPGlossaryTerm(
        id="race_specific_phase",
        label="比赛专项阶段",
        definition="靠近比赛窗口、围绕 95-105% HMP 关键能力完成专项整合的阶段。",
        training_implication="100% HMP 巡航恢复间歇应在该阶段逐步推进，并配套充分恢复。",
    ),
    "capacity_budget": HMPGlossaryTerm(
        id="capacity_budget",
        label="HMP 容量预算",
        definition="按周跑量、可训练日、恢复状态和阶段目标计算的专项课上限。",
        training_implication="先预算再排课，超过预算的 95/100/105% HMP 课应缩短或降级。",
    ),
    "dynamic_calibration": HMPGlossaryTerm(
        id="dynamic_calibration",
        label="动态配速校准",
        definition="用当前短距离成绩、半马 PB 或保守阈值估计修正 HMP 执行配速。",
        training_implication="目标配速过激或证据不足时，速度课按当前能力而不是愿望目标执行。",
    ),
    "sub70_volume_scaling": HMPGlossaryTerm(
        id="sub70_volume_scaling",
        label="Sub-70 跑量缩放",
        definition="基石文章中的高水平案例跑量不能直接作为普通跑者默认跑量。",
        training_implication="系统必须保留百分比训练结构，但按用户画像重算周跑量和专项容量。",
    ),
    "threshold_lt2": HMPGlossaryTerm(
        id="threshold_lt2",
        label="LT2 / 阈值训练",
        definition="接近第二乳酸阈值的可控高有氧强度训练。",
        training_implication="基础阶段可用阈值巡航和阈值长间歇补有氧功率，为 100% HMP 核心课铺垫。",
    ),
    "ssmax": HMPGlossaryTerm(
        id="ssmax",
        label="SSmax 最大稳态",
        definition="跑者可长时间维持、但接近上限的稳定有氧输出能力。",
        training_implication="通过阈值、次阈值和 105% HMP 速度储备训练提高，不能用单次极限课替代。",
    ),
    "progression_run": HMPGlossaryTerm(
        id="progression_run",
        label="渐进跑",
        definition="从轻松或中等强度逐步加速到目标区间的连续跑。",
        training_implication="适合基础阶段和导入期，用较低心理成本连接轻松跑、阈值和 HMP 支撑区间。",
    ),
    "long_fast_run": HMPGlossaryTerm(
        id="long_fast_run",
        label="长距离快速跑",
        definition="在 90-95% HMP 或相邻区间完成的较长距离连续或分段快速跑。",
        training_implication="必须由短到长进阶，并根据容量预算缩放；不能从短间歇直接跳到 20-25 公里。",
    ),
    "alternating_kilometers": HMPGlossaryTerm(
        id="alternating_kilometers",
        label="一公里交替跑",
        definition="以 100% HMP 主段和 85-90% HMP 巡航恢复段交替组成的核心专项形式。",
        training_implication="可逐步延长 HMP 累计量，但恢复段仍有负荷，需要纳入整堂课容量。",
    ),
    "fartlek": HMPGlossaryTerm(
        id="fartlek",
        label="法特莱克",
        definition="以时间或地形变化组织快慢交替的体感配速训练。",
        training_implication="适合导入期和辅助速度建设，疲劳或缺少短距离成绩时可替代硬性配速间歇。",
    ),
    "hill_sprints": HMPGlossaryTerm(
        id="hill_sprints",
        label="坡冲 / 坡跑",
        definition="在坡度上完成的短时间神经肌肉激活或中长间歇刺激。",
        training_implication="导入期可用短坡冲重启速度和力量，避免演变为力竭训练。",
    ),
    "strides": HMPGlossaryTerm(
        id="strides",
        label="跨步跑",
        definition="短距离、放松快速、强调跑姿和神经激活的加速跑。",
        training_implication="可作为轻松跑后的低成本速度刺激，不应替代真正的专项课。",
    ),
    "vo2max": HMPGlossaryTerm(
        id="vo2max",
        label="VO2max 最大摄氧量",
        definition="高强度耐力运动中摄取和利用氧气的能力上限。",
        training_implication="107-110% HMP 辅助速度课可刺激 VO2max，但低跑量或疲劳用户必须压缩总量。",
    ),
    "fatigue_downgrade": HMPGlossaryTerm(
        id="fatigue_downgrade",
        label="疲劳降级",
        definition="当疼痛、持续疲劳、睡眠差或主观压力高时主动降低课表强度或容量。",
        training_implication="安全约束优先于原计划完整性；必要时改为恢复跑、轻松跑或延后关键课。",
    ),
    "environment_adjustment": HMPGlossaryTerm(
        id="environment_adjustment",
        label="环境调整",
        definition="因高温、湿热、强风、路面或海拔等外部条件改变训练执行目标。",
        training_implication="同一配速在恶劣环境下真实负荷更高，应优先按体感和安全边界调整。",
    ),
    "recovery_window": HMPGlossaryTerm(
        id="recovery_window",
        label="恢复窗口",
        definition="关键训练之间用于吸收刺激、降低伤病风险的恢复间隔。",
        training_implication="高质量 HMP 课之间通常需要约 48 小时恢复，连续硬课必须有明确理由和降级预案。",
    ),
}


WORKOUT_TERM_IDS: Dict[str, Sequence[str]] = {
    "hm_90_support_endurance": ("hmp", "support_endurance_90", "long_fast_run", "capacity_budget"),
    "hm_95_long_fast_run": ("hmp", "specific_endurance_95", "long_fast_run", "support_endurance_90", "capacity_budget"),
    "hm_100_float_intervals": ("hmp", "race_specific_100", "cruise_recovery", "alternating_kilometers", "capacity_budget"),
    "hm_105_specific_speed": ("hmp", "specific_speed_105", "dynamic_calibration", "capacity_budget"),
    "hm_110_support_speed": ("hmp", "support_speed_107_110", "vo2max", "fartlek", "dynamic_calibration", "capacity_budget"),
    "hm_intro_fartlek_hills": ("introductory_phase", "fartlek", "hill_sprints", "strides"),
    "hm_base_threshold_progression": ("hmp", "threshold_lt2", "ssmax", "progression_run", "dynamic_calibration"),
}


CONSTRAINT_TERM_IDS: Dict[str, Sequence[str]] = {
    "no_sub70_volume_copy": ("sub70_volume_scaling", "capacity_budget"),
    "marathon_recovery_intro": ("introductory_phase", "specific_endurance_95", "capacity_budget"),
    "quality_recovery_gap": ("recovery_window", "capacity_budget"),
    "progress_long_fast_run": ("long_fast_run", "support_endurance_90", "specific_endurance_95", "capacity_budget"),
    "dynamic_hmp_calibration": ("hmp", "dynamic_calibration", "specific_speed_105", "support_speed_107_110"),
    "race_specific_timing": ("race_specific_phase", "race_specific_100", "cruise_recovery", "capacity_budget"),
    "environment_or_fatigue_downgrade": ("fatigue_downgrade", "environment_adjustment", "capacity_budget", "dynamic_calibration"),
    "capacity_budget_exceeded": ("capacity_budget", "sub70_volume_scaling"),
}


PHASE_TERM_IDS: Dict[str, Sequence[str]] = {
    "introductory": ("introductory_phase", "fartlek", "hill_sprints", "strides"),
    "general": ("general_phase", "threshold_lt2", "progression_run"),
    "race_supportive": ("race_supportive_phase", "support_endurance_90", "specific_endurance_95", "specific_speed_105"),
    "race_specific": ("race_specific_phase", "race_specific_100", "cruise_recovery"),
}


CONSTRAINT_EVIDENCE_SUMMARY: Dict[str, str] = {
    "no_sub70_volume_copy": "Sub-70 案例提供百分比训练结构，不提供可照搬的普通跑者跑量。",
    "marathon_recovery_intro": "刚比完全马后应先完成导入和恢复，再进入高消耗 HMP 专项课。",
    "quality_recovery_gap": "半马专项质量课之间需要保留恢复窗口，避免刺激叠加超过吸收能力。",
    "progress_long_fast_run": "95% HMP 长距离快跑需要由 90% 支撑课或较短 95% 课逐步进阶。",
    "dynamic_hmp_calibration": "105-110% HMP 速度课必须用当前能力校准，目标配速不能直接等同执行配速。",
    "race_specific_timing": "100% HMP 巡航恢复课属于比赛专项高消耗课，应靠近比赛窗口逐步推进。",
    "environment_or_fatigue_downgrade": "环境、疲劳或伤痛会改变同一课表的真实负荷，需要显式降级。",
    "capacity_budget_exceeded": "95/100/105% HMP 容量必须按用户画像预算，不应照搬 Sub-70 高水平案例上限。",
}


def get_hmp_glossary_terms(term_ids: Optional[Iterable[str]] = None, limit: Optional[int] = None) -> List[Dict[str, object]]:
    ids = list(HMP_GLOSSARY_TERMS.keys()) if term_ids is None else _dedupe(term_ids)
    terms = [HMP_GLOSSARY_TERMS[term_id].to_dict() for term_id in ids if term_id in HMP_GLOSSARY_TERMS]
    return terms[:limit] if limit is not None else terms


def term_ids_for_workout(workout_id: str) -> List[str]:
    return _dedupe(WORKOUT_TERM_IDS.get(str(workout_id or ""), ()))


def term_ids_for_constraint(constraint_id: str) -> List[str]:
    return _dedupe(CONSTRAINT_TERM_IDS.get(str(constraint_id or ""), ()))


def term_ids_for_phase(phase_id: str) -> List[str]:
    return _dedupe(PHASE_TERM_IDS.get(str(phase_id or ""), ()))


def evidence_basis_for_constraint(constraint_id: str, workout_type: str = "") -> Dict[str, object]:
    term_ids = _dedupe([
        *term_ids_for_constraint(constraint_id),
        *term_ids_for_workout(workout_type),
    ])
    return {
        "constraint_id": str(constraint_id or ""),
        "workout_type": str(workout_type or ""),
        "summary": CONSTRAINT_EVIDENCE_SUMMARY.get(str(constraint_id or ""), "该问题来自半马 HMP 协议安全约束。"),
        "term_ids": term_ids,
        "source_docs": list(HMP_SOURCE_DOCS),
    }


def _dedupe(values: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


__all__ = [
    "HMP_GLOSSARY_TERMS",
    "HMPGlossaryTerm",
    "evidence_basis_for_constraint",
    "get_hmp_glossary_terms",
    "term_ids_for_constraint",
    "term_ids_for_phase",
    "term_ids_for_workout",
]
