from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from marathon_qa_assistant.core.app_state import get_preferred_vector_dir, has_vector_kb_artifacts
from marathon_qa_assistant.core.zone_constants import ZONE_LABELS, ZONE_LABELS_DETAIL
from marathon_qa_assistant.services.vector_store import load_vector_kb, retrieve


@dataclass
class WorkoutTemplateEvidence:
    source_file: str
    page: Optional[int]
    chunk_id: str
    text: str
    score: float = 0.0


@dataclass
class DailyWorkoutTemplateCard:
    title: str
    workout_type: str
    training_type: str
    source: List[str] = field(default_factory=list)
    main_set_candidates: List[str] = field(default_factory=list)
    intensity_target: str = ""
    zone_range: str = ""
    training_objective: str = ""
    warmup_suggestion: str = ""
    cooldown_suggestion: str = ""
    alternative_workout: str = ""
    evidence_tier: str = "plan_only"
    evidence_status: Dict[str, str] = field(default_factory=dict)
    evidence: List[WorkoutTemplateEvidence] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


WORKOUT_TEMPLATE_REGISTRY = {
    "aerobic_threshold": {
        "display_name": "有氧阈值训练",
        "training_type_label": "有氧阈值训练（最大脂肪氧化训练）",
        "aliases": [
            "有氧阈值训练", "最大脂肪氧化训练", "有氧阈", "乳酸阈值", "阈值跑",
            "Aerobic Threshold", "Steady-State", "Endurance",
            "3-4*3000", "5-6*2000", "5000+3*2000",
        ],
        "title_template": "有氧阈值训练课",
        "source_priority": ["动作库.pdf"],
        "zone_range": "Z3-Z4",
        "intensity_target": "Z3-Z4 稳态有氧区至有氧阈值区",
        "intensity_keywords": ["Z3", "Z4", "有氧阈"],
        "extractor": "aerobic_threshold",
    },
    "long_run": {
        "display_name": "长距离",
        "training_type_label": "长距离训练",
        "aliases": ["长距离", "长距离跑", "耐力跑", "耐力", "补给节奏", "Long Run", "LSD", "L长距离Run"],
        "title_template": "长距离训练课",
        "source_priority": ["动作库.pdf"],
        "zone_range": "Z2-Z3",
        "intensity_target": "Z2-Z3 轻松有氧区至稳态有氧区",
        "intensity_keywords": ["Z2", "Z3", "稳定有氧"],
        "extractor": "generic",
    },
    "easy_run": {
        "display_name": "轻松跑",
        "training_type_label": "轻松跑",
        "aliases": ["轻松跑", "恢复跑", "Easy Run", "Z1", "Z2轻松", "轻松", "恢复"],
        "title_template": "轻松跑训练课",
        "source_priority": ["动作库.pdf"],
        "zone_range": "Z1-Z2",
        "intensity_target": "Z1-Z2 恢复放松区至轻松有氧区",
        "intensity_keywords": ["Z1", "Z2", "轻松"],
        "extractor": "generic",
    },
    "tempo_run": {
        "display_name": "节奏跑",
        "training_type_label": "节奏跑（乳酸阈值训练）",
        "aliases": ["节奏跑", "节奏", "Tempo", "乳酸阈", "阈值节奏"],
        "title_template": "节奏跑训练课",
        "source_priority": ["动作库.pdf"],
        "zone_range": "Z4",
        "intensity_target": "Z4 有氧阈值区",
        "intensity_keywords": ["Z4", "乳酸", "阈值"],
        "extractor": "generic",
    },
    "interval_run": {
        "display_name": "间歇跑",
        "training_type_label": "间歇跑（高强度间歇训练）",
        "aliases": ["间歇跑", "间歇", "Interval", "高强度间歇"],
        "title_template": "间歇训练课",
        "source_priority": ["动作库.pdf"],
        "zone_range": "Z5-Z6",
        "intensity_target": "Z5-Z6 马拉松专项区至乳酸阈值区",
        "intensity_keywords": ["Z5", "Z6", "间歇"],
        "extractor": "generic",
    },
    "vo2max_interval": {
        "display_name": "摄氧量训练",
        "training_type_label": "摄氧量训练（最大摄氧量间歇）",
        "aliases": ["摄氧量", "最大摄氧量", "VO2max", "VO2 max", "摄氧量间歇", "最大摄氧量间歇"],
        "title_template": "摄氧量训练课",
        "source_priority": ["动作库.pdf"],
        "zone_range": "Z6-Z7",
        "intensity_target": "Z6-Z7 乳酸阈值区至高强度耐受区",
        "intensity_keywords": ["Z6", "Z7", "摄氧量"],
        "extractor": "generic",
    },
    "anaerobic_threshold": {
        "display_name": "无氧阈跑",
        "training_type_label": "无氧阈跑（巡航间歇训练）",
        "aliases": ["无氧阈跑", "无氧阈", "巡航间歇", "Anaerobic Threshold"],
        "title_template": "无氧阈训练课",
        "source_priority": ["动作库.pdf"],
        "zone_range": "Z4-Z5",
        "intensity_target": "Z4-Z5 有氧阈值区至马拉松专项区",
        "intensity_keywords": ["Z4", "Z5", "无氧"],
        "extractor": "generic",
    },
    "marathon_pace": {
        "display_name": "马拉松配速跑",
        "training_type_label": "马拉松配速跑（专项配速训练）",
        "aliases": ["马拉松配速跑", "马拉松配速", "Marathon Pace", "专项配速"],
        "title_template": "配速训练课",
        "source_priority": ["动作库.pdf"],
        "zone_range": "Z3-Z4",
        "intensity_target": "Z3-Z4 稳态有氧区至有氧阈值区",
        "intensity_keywords": ["Z3", "Z4", "配速"],
        "extractor": "generic",
    },
    "progression_run": {
        "display_name": "渐进跑",
        "training_type_label": "渐进跑",
        "aliases": ["渐进跑", "渐进", "Progression", "渐加速"],
        "title_template": "渐进跑训练课",
        "source_priority": ["动作库.pdf"],
        "zone_range": "Z1→Z4",
        "intensity_target": "Z1→Z4 恢复放松区渐进至有氧阈值区",
        "intensity_keywords": ["渐进", "加速"],
        "extractor": "generic",
    },
    "fartlek": {
        "display_name": "法特莱克",
        "training_type_label": "法特莱克（速度游戏）",
        "aliases": ["法特莱克", "速度游戏", "Fartlek", "变速跑"],
        "title_template": "法特莱克训练课",
        "source_priority": ["动作库.pdf"],
        "zone_range": "Z2-Z5",
        "intensity_target": "Z2-Z5 轻松有氧区至马拉松专项区（变化）",
        "intensity_keywords": ["变速", "法特莱克", "Fartlek"],
        "extractor": "generic",
    },
    "hill_repeats": {
        "display_name": "坡道训练",
        "training_type_label": "坡道训练（坡道重复跑）",
        "aliases": ["坡道跑", "坡道训练", "坡道", "Hill", "爬坡"],
        "title_template": "坡道训练课",
        "source_priority": ["动作库.pdf"],
        "zone_range": "Z5-Z6",
        "intensity_target": "Z5-Z6 马拉松专项区至乳酸阈值区",
        "intensity_keywords": ["坡道", "爬坡", "Hill"],
        "extractor": "generic",
    },
    "strides": {
        "display_name": "短冲",
        "training_type_label": "短冲/加速跑（Strides）",
        "aliases": ["短冲", "加速跑", "Strides", "冲刺跑"],
        "title_template": "短冲训练课",
        "source_priority": ["动作库.pdf"],
        "zone_range": "Z7-Z8",
        "intensity_target": "Z7-Z8 高强度耐受区至无氧刺激区（短时）",
        "intensity_keywords": ["短冲", "加速", "Strides"],
        "extractor": "generic",
    },
}

WORKOUT_TEMPLATE_REGISTRY.update({
    "hm_90_support_endurance": {
        "display_name": "半马90%HMP辅助耐力跑",
        "training_type_label": "半马辅助耐力跑（90% HMP）",
        "aliases": [
            "hm_90_support_endurance",
            "90% HMP",
            "90%HMP",
            "半马辅助耐力",
            "辅助耐力跑",
            "稳定长跑",
            "分段递进跑",
        ],
        "title_template": "半马90%HMP辅助耐力课",
        "source_priority": ["docs/half_marathon_hmp_protocol.md", "Sub-70半程马拉松训练_图片OCR整理.md"],
        "zone_range": "Z3-Z4",
        "intensity_target": "Z3-Z4 / 90% HMP 辅助耐力区",
        "intensity_keywords": ["90% HMP", "90%HMP", "辅助耐力"],
        "extractor": "protocol",
        "main_set_candidates": [
            "中等强度长跑，后段逐步接近90% HMP",
            "分段递进跑：86%-88%-92% HMP",
            "稳定长跑：以90% HMP附近完成主要连续段",
        ],
        "training_objective": "为95% HMP长距离快速跑提供耐力支撑，建立半马专项前的稳定输出能力。",
        "warmup_suggestion": "15-20分钟轻松跑 + 动态拉伸 + 4组短加速",
        "cooldown_suggestion": "10-15分钟慢跑 + 下肢放松",
        "alternative_workout": "若疲劳较高，改为Z2-Z3长距离轻松跑并保留最后4-6组短加速。",
        "applicable_phases": ["general", "race_supportive"],
    },
    "hm_95_long_fast_run": {
        "display_name": "半马95%HMP专项耐力长距离快速跑",
        "training_type_label": "半马专项耐力长距离快速跑（95% HMP）",
        "aliases": [
            "hm_95_long_fast_run",
            "95% HMP",
            "95%HMP",
            "长距离快速跑",
            "半马专项耐力",
            "long fast run",
        ],
        "title_template": "半马95%HMP专项耐力课",
        "source_priority": ["docs/half_marathon_hmp_protocol.md", "Sub-70半程马拉松训练_图片OCR整理.md"],
        "zone_range": "Z4-Z5",
        "intensity_target": "Z4-Z5 / 95% HMP 专项耐力区",
        "intensity_keywords": ["95% HMP", "95%HMP", "专项耐力"],
        "extractor": "protocol",
        "main_set_candidates": [
            "较短95% HMP快速跑，先控制总量再递增距离",
            "90% HMP辅助耐力 + 短95% HMP收尾",
            "长距离快速跑：主要段接近95% HMP",
        ],
        "training_objective": "建立半马后程抗疲劳和接近目标配速的持续能力。",
        "warmup_suggestion": "20分钟轻松跑 + 动态拉伸 + 4-6组加速跑",
        "cooldown_suggestion": "10-15分钟慢跑 + 补水放松",
        "alternative_workout": "若刚比完全马或恢复不足，降级为90% HMP稳定跑或分段递进跑。",
        "applicable_phases": ["race_supportive", "race_specific"],
    },
    "hm_100_float_intervals": {
        "display_name": "半马100%HMP核心专项巡航恢复间歇",
        "training_type_label": "半马核心专项巡航恢复间歇（100% HMP）",
        "aliases": [
            "hm_100_float_intervals",
            "100% HMP",
            "100%HMP",
            "巡航恢复",
            "浮动间歇",
            "float intervals",
            "半马核心专项",
        ],
        "title_template": "半马100%HMP核心专项课",
        "source_priority": ["docs/half_marathon_hmp_protocol.md", "Sub-70半程马拉松训练_图片OCR整理.md"],
        "zone_range": "Z4-Z5",
        "intensity_target": "Z4-Z5 / 100% HMP 比赛专项区",
        "intensity_keywords": ["100% HMP", "100%HMP", "巡航恢复"],
        "extractor": "protocol",
        "main_set_candidates": [
            "1km@100% HMP / 1km巡航恢复交替",
            "2km@100% HMP / 1km巡航恢复交替",
            "3km-2km-1km组合，恢复段保持可控巡航",
        ],
        "training_objective": "提升目标半马配速下的代谢效率，并训练乳酸转运和恢复段再加速能力。",
        "warmup_suggestion": "20分钟轻松跑 + 动态拉伸 + 4-6组加速跑",
        "cooldown_suggestion": "10-15分钟慢跑 + 拉伸",
        "alternative_workout": "若状态不稳，改为阈值巡航间歇或缩短100% HMP累计距离。",
        "applicable_phases": ["race_specific"],
    },
    "hm_105_specific_speed": {
        "display_name": "半马105%HMP专项速度间歇",
        "training_type_label": "半马专项速度间歇（105% HMP）",
        "aliases": [
            "hm_105_specific_speed",
            "105% HMP",
            "105%HMP",
            "专项速度",
            "中长间歇",
            "8K",
            "10K",
        ],
        "title_template": "半马105%HMP专项速度课",
        "source_priority": ["docs/half_marathon_hmp_protocol.md", "Sub-70半程马拉松训练_图片OCR整理.md"],
        "zone_range": "Z5-Z6",
        "intensity_target": "Z5-Z6 / 105% HMP 专项速度区",
        "intensity_keywords": ["105% HMP", "105%HMP", "专项速度"],
        "extractor": "protocol",
        "main_set_candidates": [
            "500-1000m重复跑，强度约105% HMP",
            "1200m-2km中长间歇，控制恢复质量",
            "6-8km快速持续跑或8K/10K测试赛",
        ],
        "training_objective": "建立8K/10K速度储备，让目标HMP感觉更轻松。",
        "warmup_suggestion": "15-20分钟轻松跑 + 跑姿练习 + 4组加速跑",
        "cooldown_suggestion": "10-15分钟慢跑",
        "alternative_workout": "若速度课压力过大，改为短法特莱克或坡跑，保留神经肌肉刺激。",
        "applicable_phases": ["race_supportive", "race_specific"],
    },
    "hm_110_support_speed": {
        "display_name": "半马107-110%HMP辅助速度训练",
        "training_type_label": "半马辅助速度训练（107-110% HMP）",
        "aliases": [
            "hm_110_support_speed",
            "107% HMP",
            "110% HMP",
            "107-110% HMP",
            "辅助速度",
            "短法特莱克",
            "短坡跑",
            "5K",
        ],
        "title_template": "半马107-110%HMP辅助速度课",
        "source_priority": ["docs/half_marathon_hmp_protocol.md", "Sub-70半程马拉松训练_图片OCR整理.md"],
        "zone_range": "Z6-Z7",
        "intensity_target": "Z6-Z7 / 107-110% HMP 辅助速度区",
        "intensity_keywords": ["107% HMP", "110% HMP", "辅助速度"],
        "extractor": "protocol",
        "main_set_candidates": [
            "35-45分钟混合法特莱克",
            "400-1000m短间歇，累计6-7km以内",
            "短坡冲或1-2分钟短法特莱克",
        ],
        "training_objective": "发展VO2max、速度上限、乳酸转运和乳酸氧化能力。",
        "warmup_suggestion": "15-20分钟轻松跑 + 动态拉伸 + 技术跑 drills",
        "cooldown_suggestion": "10-15分钟慢跑 + 小腿和髋部放松",
        "alternative_workout": "若疲劳或5K能力不足，降低到105% HMP附近或改为坡冲。",
        "applicable_phases": ["general", "race_supportive"],
    },
})

_ACTION_LIBRARY_SOURCE = "动作库.pdf"

EVIDENCE_TIER_LABELS = {
    "action_library": "动作库课表",
    "kb_fallback": "参考知识库生成",
    "plan_only": "基础计划",
}

WORKOUT_TYPE_ALIASES = {
    key: entry["aliases"] for key, entry in WORKOUT_TEMPLATE_REGISTRY.items()
}

WORKOUT_TYPE_KEYWORD_MAP = {
    "aerobic_threshold": ["有氧阈", "最大脂肪氧化"],
    "long_run": ["长距离"],
    "easy_run": ["轻松跑", "恢复跑"],
    "tempo_run": ["节奏跑"],
    "vo2max_interval": ["最大摄氧量间歇", "摄氧量间歇", "最大摄氧量", "摄氧量", "VO2max", "VO2 max"],
    "interval_run": ["间歇跑", "间歇"],
    "anaerobic_threshold": ["无氧阈跑", "无氧阈"],
    "marathon_pace": ["马拉松配速跑", "马拉松配速"],
    "progression_run": ["渐进跑", "渐进"],
    "fartlek": ["法特莱克", "速度游戏"],
    "hill_repeats": ["坡道跑", "坡道", "Hill"],
    "strides": ["短冲", "加速跑"],
}

WORKOUT_TYPE_KEYWORD_MAP.update({
    "hm_90_support_endurance": ["hm_90_support_endurance", "90% HMP", "90%HMP", "半马辅助耐力", "辅助耐力跑"],
    "hm_95_long_fast_run": ["hm_95_long_fast_run", "95% HMP", "95%HMP", "长距离快速跑", "半马专项耐力"],
    "hm_100_float_intervals": ["hm_100_float_intervals", "100% HMP", "100%HMP", "巡航恢复", "浮动间歇"],
    "hm_105_specific_speed": ["hm_105_specific_speed", "105% HMP", "105%HMP", "专项速度", "8K/10K"],
    "hm_110_support_speed": ["hm_110_support_speed", "107-110% HMP", "110% HMP", "107% HMP", "辅助速度"],
})


def build_workout_template_query(workout_type: str) -> str:
    aliases = WORKOUT_TYPE_ALIASES.get(str(workout_type or "").strip(), [])
    if not aliases:
        return str(workout_type or "").strip()
    return " ".join(dict.fromkeys([*aliases, "课表", "主训练", "content", "objective", _ACTION_LIBRARY_SOURCE]))


def retrieve_daily_workout_template_card(
    workout_type: str,
    day: str = "",
    vector_dir: Optional[Path] = None,
    top_k: int = 20,
) -> Dict[str, Any]:
    selected_vector_dir = vector_dir or get_preferred_vector_dir()
    if not has_vector_kb_artifacts(selected_vector_dir):
        return _empty_card(workout_type, day, "知识库产物不可用，未生成课表。")

    chunks, vectorizer, matrix, bm25 = load_vector_kb(selected_vector_dir)
    hits = retrieve(build_workout_template_query(workout_type), chunks, vectorizer, matrix, top_k=top_k, bm25=bm25)
    return build_daily_workout_template_card_from_hits(workout_type=workout_type, day=day, hits=hits)


def build_daily_workout_template_card_from_hits(
    workout_type: str,
    day: str = "",
    hits: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    normalized_type = str(workout_type or "").strip()
    registry_entry = WORKOUT_TEMPLATE_REGISTRY.get(normalized_type)

    if not registry_entry:
        return _empty_card(workout_type, day, "当前工作类型注册表中未找到该训练类型。")

    title_prefix = f"{day}｜" if str(day or "").strip() else ""

    relevant_hits = _select_relevant_action_library_hits(normalized_type, hits or [])
    if not relevant_hits:
        if registry_entry.get("extractor") == "protocol":
            return _build_protocol_template_card(normalized_type, day, registry_entry)
        return _empty_card(
            workout_type,
            day,
            f"未检索到动作库中'{registry_entry['display_name']}'的直接证据，未生成课表。",
        )

    combined_text = "\n".join(str(hit.get("text") or "") for hit in relevant_hits)

    extractor_type = registry_entry.get("extractor", "generic")
    if extractor_type == "aerobic_threshold":
        main_set_candidates = _extract_aerobic_threshold_candidates(combined_text)
        training_objective = _extract_objective(combined_text)
        warmup = _extract_warmup(combined_text)
        cooldown = _extract_generic_cooldown(combined_text)
        alternative = _extract_alternative_workout(combined_text)
    else:
        main_set_candidates = _extract_generic_main_set_candidates(combined_text, normalized_type)
        training_objective = _extract_generic_objective(combined_text)
        warmup = _extract_generic_warmup(combined_text)
        cooldown = _extract_generic_cooldown(combined_text)
        alternative = _extract_alternative_workout(combined_text)

    intensity_keywords = registry_entry.get("intensity_keywords", [])
    default_intensity = registry_entry.get("intensity_target", "")
    zone_range = registry_entry.get("zone_range", "")

    has_any_keyword = any(kw in combined_text for kw in intensity_keywords) if intensity_keywords else True
    intensity_target = default_intensity if has_any_keyword else ""

    source = _build_source_labels(relevant_hits)
    evidence = [
        WorkoutTemplateEvidence(
            source_file=str(hit.get("source_file") or ""),
            page=hit.get("page"),
            chunk_id=str(hit.get("chunk_id") or ""),
            text=str(hit.get("text") or ""),
            score=float(hit.get("score") or 0.0),
        )
        for hit in relevant_hits[:5]
    ]

    card = DailyWorkoutTemplateCard(
        title=f"{title_prefix}{registry_entry['title_template']}",
        workout_type=normalized_type,
        training_type=registry_entry.get("training_type_label", ""),
        source=source,
        main_set_candidates=main_set_candidates,
        intensity_target=intensity_target,
        zone_range=zone_range,
        evidence_tier="action_library",
        training_objective=training_objective,
        warmup_suggestion=warmup,
        cooldown_suggestion=cooldown,
        alternative_workout=alternative,
        evidence_status={
            "main_set_candidates": "direct" if main_set_candidates else "missing",
            "intensity_target": "direct" if intensity_target else "missing",
            "training_objective": "direct" if training_objective else "missing",
            "warmup_suggestion": "direct" if warmup else "missing",
            "cooldown": "direct" if cooldown else "missing",
            "alternative_workout": "direct" if alternative else "missing",
        },
        evidence=evidence,
    )
    return card.to_dict()


def _build_protocol_template_card(
    workout_type: str,
    day: str,
    registry_entry: Dict[str, Any],
) -> Dict[str, Any]:
    title_prefix = f"{day}｜" if str(day or "").strip() else ""
    main_set_candidates = [
        str(item)
        for item in registry_entry.get("main_set_candidates", [])
        if str(item or "").strip()
    ][:6]
    card = DailyWorkoutTemplateCard(
        title=f"{title_prefix}{registry_entry.get('title_template', registry_entry.get('display_name', workout_type))}",
        workout_type=workout_type,
        training_type=registry_entry.get("training_type_label", ""),
        source=["docs/half_marathon_hmp_protocol.md", "Sub-70半程马拉松训练_图片OCR整理.md"],
        main_set_candidates=main_set_candidates,
        intensity_target=registry_entry.get("intensity_target", ""),
        zone_range=registry_entry.get("zone_range", ""),
        training_objective=registry_entry.get("training_objective", ""),
        warmup_suggestion=registry_entry.get("warmup_suggestion", ""),
        cooldown_suggestion=registry_entry.get("cooldown_suggestion", ""),
        alternative_workout=registry_entry.get("alternative_workout", ""),
        evidence_tier="plan_only",
        evidence_status={
            "main_set_candidates": "protocol" if main_set_candidates else "missing",
            "intensity_target": "protocol" if registry_entry.get("intensity_target") else "missing",
            "training_objective": "protocol" if registry_entry.get("training_objective") else "missing",
            "warmup_suggestion": "protocol" if registry_entry.get("warmup_suggestion") else "missing",
            "cooldown": "protocol" if registry_entry.get("cooldown_suggestion") else "missing",
            "alternative_workout": "protocol" if registry_entry.get("alternative_workout") else "missing",
            "reason": "半马HMP协议确定性模板，等待后续知识库证据增强。",
        },
    )
    return card.to_dict()


def _empty_card(workout_type: str, day: str, reason: str) -> Dict[str, Any]:
    title_prefix = f"{day}｜" if str(day or "").strip() else ""
    registry_entry = WORKOUT_TEMPLATE_REGISTRY.get(str(workout_type or "").strip(), {})
    card = DailyWorkoutTemplateCard(
        title=f"{title_prefix}课表证据不足",
        workout_type=str(workout_type or ""),
        training_type=registry_entry.get("training_type_label", ""),
        zone_range=registry_entry.get("zone_range", ""),
        intensity_target=registry_entry.get("intensity_target", ""),
        evidence_tier="plan_only",
        evidence_status={
            "main_set_candidates": "missing",
            "intensity_target": "missing",
            "training_objective": "missing",
            "warmup_suggestion": "missing",
            "cooldown": "missing",
            "alternative_workout": "missing",
            "reason": reason,
        },
    )
    return card.to_dict()


def _select_relevant_action_library_hits(workout_type: str, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    registry_entry = WORKOUT_TEMPLATE_REGISTRY.get(workout_type, {})
    aliases = registry_entry.get("aliases", [])
    source_priority = registry_entry.get("source_priority", [_ACTION_LIBRARY_SOURCE])
    selected = []
    for hit in hits:
        source_file = str(hit.get("source_file") or hit.get("source") or "")
        text = str(hit.get("text") or "")
        if source_file not in source_priority:
            continue
        if any(alias in text for alias in aliases[:7]):
            selected.append(hit)
    return selected


def _extract_aerobic_threshold_candidates(text: str) -> List[str]:
    normalized = _clean_text(text)
    patterns = [
        r"3-4\s*[*×xX]\s*3000\s*/\s*2min",
        r"5-6\s*[*×xX]\s*2000\s*/\s*2min",
        r"3\s*[*×xX]\s*3000\+3\+2000(?:\([^)]*\))?",
        r"上下坡交替跑15km",
        r"5000\+3\s*[*×xX]\s*2000",
        r"（?3min有氧阈\+2min慢跑\+2min有氧阈\+1min慢跑）?\s*[*×xX]\s*6",
    ]
    labels = []
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            labels.append(_format_candidate(match.group(0)))
    return list(dict.fromkeys(labels))[:6]


def _extract_objective(text: str) -> str:
    normalized = _clean_text(text)
    match = re.search(r"objective[:：](.*?)(?:3\. name|4\. name|5\. name|【|$)", normalized, flags=re.DOTALL)
    if not match:
        return ""
    objective = match.group(1).strip(" 。；;，,\n")
    if "脂代谢" in objective or "最大脂肪氧化" in objective:
        return objective
    objective_match = re.search(r"提升脂代谢效率与有氧耐力，提升最大脂肪氧化率", normalized)
    return objective_match.group(0) if objective_match else ""


def _extract_warmup(text: str) -> str:
    normalized = _clean_text(text)
    match = re.search(r"15分钟慢跑\+动态拉伸\+马克操\+3\.2-4\.8km加速跑(?:（[^）]*）)?", normalized)
    return _format_candidate(match.group(0)) if match else ""


def _extract_generic_main_set_candidates(text: str, workout_type: str) -> List[str]:
    normalized = _clean_text(text)
    candidates: List[str] = []
    candidate_patterns = [
        r"(?:^|\n)\s*(?:[a-f]\.)\s*(.+?)(?:\n|$)",
        r"(?:content|主训练|主课)[:：]\s*(.+?)(?:\n(?:objective|热身|warm|cooldown|【)|$)",
        r"(\d+[-×*]?\d*\s*[×*]\s*\d+[mk]?\s*/?\s*\d*\s*min)",
        r"(\d+\s*[-~到至]\s*\d+\s*分钟)",
        r"(\d+\s*[×*]\s*\d+[mk]\s*[,，]?\s*[配组间].*?min)",
        r"(\d+\s*分?钟?[^\n]{0,20}?[配跑])",
    ]
    for pattern in candidate_patterns:
        for match in re.finditer(pattern, normalized, flags=re.IGNORECASE | re.DOTALL):
            raw = match.group(1).strip()
            parts = re.split(r"(?=(?:[a-f]\.)\s*)", raw)
            for part in parts:
                cleaned = re.sub(r"^[a-f]\.\s*", "", part.strip(), flags=re.IGNORECASE)
                candidate = _format_candidate(cleaned)
                if candidate and 5 <= len(candidate) <= 80 and candidate not in candidates:
                    candidates.append(candidate)
                if len(candidates) >= 6:
                    return candidates[:6]
    return candidates[:6]


def _extract_generic_objective(text: str) -> str:
    normalized = _clean_text(text)
    match = re.search(r"objective[:：](.*?)(?:\n(?:热身|warm|cooldown|【)|\n\n|$)", normalized, flags=re.DOTALL)
    if not match:
        return ""
    objective = match.group(1).strip(" 。；;，,\n")
    return objective[:120] if objective else ""


def _extract_generic_warmup(text: str) -> str:
    normalized = _clean_text(text)
    warmup_patterns = [
        r"(?:热身|warm[-_ ]?up)[:：]\s*(.{5,80}?)(?:\n|【|$)",
        r"(?:热身|warm[-_ ]?up)\s+(.{5,60}?)(?:\n|$)",
        r"(\d+分[钟]?\s*慢跑\s*[\+＋]\s*动态拉伸.{3,60}?)",
    ]
    for pattern in warmup_patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return _format_candidate(match.group(1).strip() if match.lastindex else match.group(0).strip())
    return ""


def _extract_generic_cooldown(text: str) -> str:
    normalized = _clean_text(text)
    cooldown_patterns = [
        r"(?:冷身|cooldown|cool[-_ ]?down)[:：]\s*(.{5,80}?)(?:\n(?:【|$)|\n\n|$)",
        r"(?:冷身|cooldown|cool[-_ ]?down)\s+(.{5,60}?)(?:\n|$)",
        r"(\d+分[钟]?\s*慢跑\s*[\+＋]\s*拉伸.{3,60}?)",
        r"冷身\s*[:：]?\s*(.{5,60}?)(?:\n|$)",
    ]
    for pattern in cooldown_patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return _format_candidate(match.group(1).strip() if match.lastindex else match.group(0).strip())
    return ""


def _extract_alternative_workout(text: str) -> str:
    normalized = _clean_text(text)
    alt_patterns = [
        r"(?:替代[训练课]?|备选[训练课]?|alternative)[:：]\s*(.{5,80}?)(?:\n(?:【|$)|\n\n|$)",
        r"可选[训练课]?[:：]\s*(.{5,80}?)(?:\n(?:【|$)|\n\n|$)",
        r"(?:若无|如果[没不]有|如果无法).{0,15}?[，,]\s*(.{5,60}?)(?:[。；;]|$)",
    ]
    for pattern in alt_patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return _format_candidate(match.group(1).strip() if match.lastindex else match.group(0).strip())
    return ""


def normalize_workout_type_for_template(training_type: str, main_set: str = "") -> str:
    training_text = str(training_type or "").strip()
    main_set_text = str(main_set or "").strip()
    combined = f"{training_text} {main_set_text}"
    all_pairs = [
        (keyword, type_key)
        for type_key, keywords in WORKOUT_TYPE_KEYWORD_MAP.items()
        for keyword in keywords
    ]
    all_pairs.sort(key=lambda pair: len(pair[0]), reverse=True)
    for keyword, type_key in all_pairs:
        if keyword in combined:
            return type_key
    return ""


def _build_source_labels(hits: List[Dict[str, Any]]) -> List[str]:
    labels = []
    for hit in hits:
        source = str(hit.get("source_file") or hit.get("source") or "").strip()
        page = hit.get("page")
        if not source:
            continue
        label = f"{source}，第 {page} 页" if page else source
        if label not in labels:
            labels.append(label)
    return labels[:5]


def _clean_text(text: str) -> str:
    return re.sub(r"[^\S\n]+", "", str(text or "").replace("​", "").replace("×", "*"))


def _format_candidate(text: str) -> str:
    value = str(text or "").replace("*", " × ").replace("/", "，组间 ")
    value = value.replace("2min", "2min")
    value = re.sub(r"\s+", " ", value).strip()
    return value


__all__ = [
    "DailyWorkoutTemplateCard",
    "WorkoutTemplateEvidence",
    "WORKOUT_TEMPLATE_REGISTRY",
    "WORKOUT_TYPE_KEYWORD_MAP",
    "build_daily_workout_template_card_from_hits",
    "build_workout_template_query",
    "normalize_workout_type_for_template",
    "retrieve_daily_workout_template_card",
]
