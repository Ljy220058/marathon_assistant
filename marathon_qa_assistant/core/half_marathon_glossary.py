from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Optional, Sequence


HMP_SOURCE_DOCS = (
    "Sub-70半程马拉松训练_图片OCR整理.md",
    "docs/half_marathon_hmp_protocol.md",
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
}


WORKOUT_TERM_IDS: Dict[str, Sequence[str]] = {
    "hm_90_support_endurance": ("hmp", "support_endurance_90"),
    "hm_95_long_fast_run": ("hmp", "specific_endurance_95", "support_endurance_90", "capacity_budget"),
    "hm_100_float_intervals": ("hmp", "race_specific_100", "cruise_recovery", "capacity_budget"),
    "hm_105_specific_speed": ("hmp", "specific_speed_105", "dynamic_calibration", "capacity_budget"),
    "hm_110_support_speed": ("hmp", "support_speed_107_110", "dynamic_calibration", "capacity_budget"),
    "hm_intro_fartlek_hills": ("introductory_phase",),
    "hm_base_threshold_progression": ("hmp", "dynamic_calibration"),
}


CONSTRAINT_TERM_IDS: Dict[str, Sequence[str]] = {
    "no_sub70_volume_copy": ("sub70_volume_scaling", "capacity_budget"),
    "marathon_recovery_intro": ("introductory_phase", "specific_endurance_95", "capacity_budget"),
    "quality_recovery_gap": ("capacity_budget",),
    "progress_long_fast_run": ("support_endurance_90", "specific_endurance_95", "capacity_budget"),
    "dynamic_hmp_calibration": ("hmp", "dynamic_calibration", "specific_speed_105", "support_speed_107_110"),
    "race_specific_timing": ("race_specific_100", "cruise_recovery", "capacity_budget"),
    "environment_or_fatigue_downgrade": ("capacity_budget", "dynamic_calibration"),
    "capacity_budget_exceeded": ("capacity_budget", "sub70_volume_scaling"),
}


PHASE_TERM_IDS: Dict[str, Sequence[str]] = {
    "introductory": ("introductory_phase",),
    "race_supportive": ("support_endurance_90", "specific_endurance_95"),
    "race_specific": ("race_specific_100", "cruise_recovery"),
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
