from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import json
import logging

from marathon_qa_assistant.core import kb_runtime
from marathon_qa_assistant.core.app_state import get_preferred_vector_dir, has_vector_kb_artifacts
from marathon_qa_assistant.core.zone_constants import ZONE_LABELS, ZONE_LABELS_DETAIL
from marathon_qa_assistant.services.kb.source_registry import build_source_registry_id
# vector_store 懒加载，避免导入时触发 Ollama 连接

logger = logging.getLogger("workout_template_retriever")


def _runtime_retrieval_data():
    if not kb_runtime.KB_CHUNKS or not kb_runtime.RETRIEVE_FUNC:
        return None
    chunks = kb_runtime.KB_SHARD_CHUNKS if kb_runtime.KB_SHARD_CHUNKS is not None else kb_runtime.KB_CHUNKS
    return chunks, kb_runtime.KB_VECTORIZER, kb_runtime.KB_MATRIX, kb_runtime.KB_BM25, kb_runtime.RETRIEVE_FUNC


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
    source_authority: str = ""
    evidence_tier: str = "plan_only"
    evidence_status: Dict[str, str] = field(default_factory=dict)
    evidence: List[WorkoutTemplateEvidence] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        primary_source = self.source[0] if self.source else self.title
        if self.evidence_tier == "action_library":
            evidence_domain = "action_library"
            retrieval_mode = "action_library"
            prescription_permission = "can_write_core"
        elif self.evidence_tier == "protocol_rule":
            evidence_domain = "protocol"
            retrieval_mode = "protocol_rule"
            prescription_permission = "can_write_core"
        else:
            evidence_domain = self.evidence_tier
            retrieval_mode = "none"
            prescription_permission = "blocked_needs_evidence"
        data["kb_metadata"] = {
            "knowledge_layer": "prescription_library",
            "evidence_domain": evidence_domain,
            "retrieval_mode": retrieval_mode,
            "prescription_permission": prescription_permission,
            "source_registry_id": build_source_registry_id(primary_source),
        }
        return data


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
        "title_template": "马拉松配速训练课",
        "source_priority": ["动作库.pdf", "half_marathon_hmp_protocol.md"],
        "zone_range": "Z4-Z5",
        "intensity_target": "Z4-Z5 比赛配速区（100% HMP），配合 85-90% HMP 巡航恢复",
        "intensity_keywords": ["Z4", "Z5", "配速", "巡航恢复"],
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
    "hm_intro_fartlek_hills": {
        "display_name": "导入期法特莱克/坡跑",
        "training_type_label": "半马导入期法特莱克/坡跑（75-85% HMP）",
        "aliases": [
            "hm_intro_fartlek_hills",
            "导入期法特莱克",
            "导入期坡跑",
            "短法特莱克",
            "坡冲",
            "75-85% HMP",
        ],
        "title_template": "半马导入期法特莱克/坡跑课",
        "source_priority": ["docs/half_marathon_hmp_protocol.md", "Sub-70半程马拉松训练_图片OCR整理.md"],
        "zone_range": "Z3-Z4",
        "intensity_target": "Z3-Z4 / 75-85% HMP 温和重启区",
        "intensity_keywords": ["75-85% HMP", "法特莱克", "坡跑", "坡冲"],
        "extractor": "protocol",
        "main_set_candidates": [
            "35分钟体感法特莱克，含6×30秒轻快跑",
            "轻松越野渐速跑，快段控制在75-85% HMP",
            "短坡冲 + 轻松跑组合，重建跑姿和力量刺激",
        ],
        "training_objective": "低压力恢复训练热情，并重新引入速度、力量和跑姿刺激。",
        "warmup_suggestion": "15分钟轻松跑 + 动态拉伸 + 跑姿练习",
        "cooldown_suggestion": "10分钟慢跑 + 小腿、臀腿放松",
        "alternative_workout": "若全马后疲劳仍明显，改为30-45分钟Z1-Z2恢复跑或完全休息。",
        "applicable_phases": ["intro"],
    },
    "hm_base_threshold_progression": {
        "display_name": "基础期阈值/渐速跑",
        "training_type_label": "半马基础期阈值/渐速跑（75-85% HMP）",
        "aliases": [
            "hm_base_threshold_progression",
            "基础期阈值",
            "基础期渐速跑",
            "肯尼亚式渐速跑",
            "阈值巡航",
            "75-85% HMP",
            "85% HMP",
        ],
        "title_template": "半马基础期阈值/渐速课",
        "source_priority": ["docs/half_marathon_hmp_protocol.md", "Sub-70半程马拉松训练_图片OCR整理.md"],
        "zone_range": "Z3-Z4",
        "intensity_target": "Z3-Z4 / 75-85% HMP 基础阈值区",
        "intensity_keywords": ["75-85% HMP", "85% HMP", "阈值", "渐速"],
        "extractor": "protocol",
        "main_set_candidates": [
            "3×10分钟有氧阈值，组间3分钟慢跑，控制在75-85% HMP",
            "4×8分钟阈值巡航，组间2分钟慢跑，整体不超过85% HMP",
            "50分钟肯尼亚式渐速跑，从轻松跑逐步进到85% HMP",
        ],
        "training_objective": "构建SSmax、有氧功率、跑步经济性和多配速基础，为后续半马专项课留出承接能力。",
        "warmup_suggestion": "15分钟轻松跑 + 动态拉伸 + 4组短加速",
        "cooldown_suggestion": "10-15分钟慢跑 + 髋部和腘绳肌放松",
        "alternative_workout": "若疲劳较高，改为40-50分钟Z2轻松跑，取消阈值段。",
        "applicable_phases": ["general"],
    },
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
    # ── P9: 7 个新课型（基于 Daniels/Pfitzinger 教材三角验证） ──
    "recovery_run_z1": {
        "display_name": "恢复跑（Z1）",
        "training_type_label": "恢复跑（Z1 主动恢复）",
        "aliases": ["恢复跑", "Recovery Run", "Z1恢复", "主动恢复", "极松跑"],
        "title_template": "恢复跑训练课",
        "source_priority": ["references/Daniels_Running_Formula_4e.md", "references/Pfitzinger_Advanced_Marathoning_3e.md"],
        "zone_range": "Z1",
        "intensity_target": "Z1 恢复放松区（<72% LTHR）",
        "intensity_keywords": ["Z1", "恢复", "<72%", "Recovery"],
        "extractor": "generic",
    },
    "general_aerobic_z2z3": {
        "display_name": "一般有氧跑（Z2-Z3）",
        "training_type_label": "一般有氧跑（Z2-Z3 有氧基础）",
        "aliases": ["一般有氧跑", "General Aerobic", "GA", "稳定有氧", "基础有氧", "有氧跑", "日常跑"],
        "title_template": "一般有氧训练课",
        "source_priority": ["references/Pfitzinger_Advanced_Marathoning_3e.md", "references/Daniels_Running_Formula_4e.md"],
        "zone_range": "Z2-Z3",
        "intensity_target": "Z2-Z3 轻松有氧区至稳态有氧区",
        "intensity_keywords": ["Z2", "Z3", "有氧", "General Aerobic"],
        "extractor": "generic",
    },
    "continuous_tempo_z5z6": {
        "display_name": "连续节奏跑（Z5-Z6）",
        "training_type_label": "连续节奏跑（乳酸阈值训练）",
        "aliases": ["连续节奏跑", "Continuous Tempo", "LT持续跑", "连续T跑"],
        "title_template": "连续节奏训练课",
        "source_priority": ["references/Daniels_Running_Formula_4e.md", "references/Pfitzinger_Advanced_Marathoning_3e.md"],
        "zone_range": "Z5-Z6",
        "intensity_target": "Z5-Z6 乳酸阈值区（90-97% LTHR）",
        "intensity_keywords": ["Z5", "Z6", "Tempo", "LT", "乳酸"],
        "extractor": "generic",
    },
    "mp_mixed_long_run": {
        "display_name": "MP混合长距离",
        "training_type_label": "MP混合长距离（比赛配速+有氧巡航）",
        "aliases": ["MP混合长距离", "Long/MP", "配速长距离", "马拉松模拟长距离", "Long Run MP"],
        "title_template": "MP混合长距离训练课",
        "source_priority": ["references/Daniels_Running_Formula_4e.md", "references/Pfitzinger_Advanced_Marathoning_3e.md"],
        "zone_range": "Z2-Z5",
        "intensity_target": "Z2-Z3 巡航段 + Z4-Z5 比赛配速段",
        "intensity_keywords": ["Z2", "Z3", "Z4", "Z5", "MP", "配速", "长距离", "Long/MP"],
        "extractor": "generic",
    },
    "strides_z7z9": {
        "display_name": "跨步跑（Strides）",
        "training_type_label": "跨步跑（Z7-Z9 短时高速）",
        "aliases": ["跨步跑", "Strides", "加速跑", "短冲", "跨步", "跑姿经济性"],
        "title_template": "跨步跑训练课",
        "source_priority": ["references/Daniels_Running_Formula_4e.md", "references/Pfitzinger_Advanced_Marathoning_3e.md"],
        "zone_range": "Z7-Z9",
        "intensity_target": "Z7-Z9 短时高速刺激（80-90% 最大速度）",
        "intensity_keywords": ["Z7", "Z8", "Z9", "Strides", "跨步", "加速"],
        "extractor": "generic",
    },
    "race_simulation": {
        "display_name": "比赛模拟跑",
        "training_type_label": "比赛模拟跑（彩排/调整赛）",
        "aliases": ["比赛模拟", "Race Simulation", "模拟赛", "Tune-up", "彩排跑", "赛前预演"],
        "title_template": "比赛模拟训练课",
        "source_priority": ["references/Pfitzinger_Advanced_Marathoning_3e.md", "references/Daniels_Running_Formula_4e.md"],
        "zone_range": "Z5-Z7",
        "intensity_target": "Z5-Z7 比赛努力配速（模拟赛完整流程）",
        "intensity_keywords": ["Z5", "Z6", "Z7", "模拟", "Tune-up", "比赛"],
        "extractor": "generic",
    },
    "hm_specific_pace_a": {
        "display_name": "半马专项配速跑（A级教材）",
        "training_type_label": "半马专项配速跑（Daniels/Pfitzinger 教材级）",
        "aliases": ["半马专项配速", "HM Pace A", "HMP巡航", "100%HMP", "半马比赛配速", "半马专项"],
        "title_template": "半马专项配速训练课（教材级）",
        "source_priority": ["references/Daniels_Running_Formula_4e.md", "references/Pfitzinger_Advanced_Marathoning_3e.md"],
        "zone_range": "Z4-Z5",
        "intensity_target": "Z4-Z5 比赛配速区（100% HMP）+ 85% HMP 巡航恢复",
        "intensity_keywords": ["Z4", "Z5", "100% HMP", "巡航恢复", "半马专项"],
        "extractor": "generic",
    },
})

_ACTION_LIBRARY_SOURCE = "动作库.pdf"

_CORE_PRESCRIPTION_CATEGORY_TOKENS = {
    "aerobic",
    "anaerobic",
    "endurance",
    "steady-state",
    "long-run",
    "marathon",
    "marathon-spec",
    "threshold",
    "tempo",
    "interval",
    "intervals",
    "vo2max",
    "fartlek",
    "hills",
    "strength-endurance",
    "speed",
    "lactate",
    "active-rest",
    "race",
    "阈值",
    "长距离",
    "⻓距离",
    "跑走",
    "节奏",
    "间歇",
    "坡",
    "法特莱克",
    "配速",
    "轻松跑",
    "恢复跑",
}

_NON_CORE_ONLY_CATEGORY_TOKENS = {
    "warm-up",
    "pre-run",
    "mobility",
    "flexibility",
    "self-massage",
    "activation",
    "technique",
    "drills",
    "热身",
    "激活",
    "灵活",
    "拉伸",
    "泡沫",
    "放松",
    "技术",
    "马克操",
}

_WORKOUT_TYPE_REQUIRED_CATEGORY_TOKENS = {
    "aerobic_threshold": {"steady-state", "阈值", "最大脂肪", "有氧阈值"},
    "long_run": {"long-run", "marathon-spec", "长距离", "⻓距离"},
    "easy_run": {"active-rest", "easy run", "recovery run", "跑走", "轻松跑", "恢复跑"},
    "tempo_run": {"tempo", "threshold", "lactate-threshold", "节奏", "阈值"},
    "interval_run": {"interval", "intervals", "vo2max", "speed", "间歇"},
    "vo2max_interval": {"vo2max", "intervals", "hard", "摄氧", "间歇"},
    "anaerobic_threshold": {"threshold", "lactate-threshold", "cruise", "无氧阈", "阈值"},
    "marathon_pace": {"marathon-pace", "marathon", "配速"},
    "progression_run": {"progression", "long-run", "tempo", "节奏", "渐进"},
    "fartlek": {"fartlek", "法特莱克"},
    "hill_repeats": {"hills", "strength-endurance", "坡"},
    "strides": {"strides", "speed", "加速跑", "短冲"},
}


def _action_hit_category_blob(hit: Dict[str, Any]) -> str:
    tags = hit.get("tags") if isinstance(hit.get("tags"), dict) else {}
    values = [
        tags.get("categories", ""),
        tags.get("workout_name", ""),
        " ".join(str(item or "") for item in (hit.get("domain_terms") or [])),
        str(hit.get("text") or "")[:400],
    ]
    return " ".join(str(value or "") for value in values).lower()


def _action_hit_label_blob(hit: Dict[str, Any]) -> str:
    tags = hit.get("tags") if isinstance(hit.get("tags"), dict) else {}
    values = [
        tags.get("categories", ""),
        tags.get("workout_name", ""),
        " ".join(str(item or "") for item in (hit.get("domain_terms") or [])),
    ]
    return " ".join(str(value or "") for value in values).lower()


def _action_hit_search_blob(hit: Dict[str, Any]) -> str:
    tags = hit.get("tags") if isinstance(hit.get("tags"), dict) else {}
    values = [
        str(hit.get("text") or ""),
        tags.get("categories", ""),
        tags.get("workout_name", ""),
        " ".join(str(item or "") for item in (hit.get("domain_terms") or [])),
    ]
    blob = " ".join(str(value or "") for value in values).lower()
    normalized_blob = blob.replace("⻓", "长").replace("-", " ")
    return f"{blob} {normalized_blob}"


def _is_core_prescription_action_hit(hit: Dict[str, Any]) -> bool:
    if hit.get("exclude_from_training_generation") is True:
        return False

    label_blob = _action_hit_label_blob(hit)
    label_has_core_category = any(token in label_blob for token in _CORE_PRESCRIPTION_CATEGORY_TOKENS)
    label_has_non_core_category = any(token in label_blob for token in _NON_CORE_ONLY_CATEGORY_TOKENS)
    if label_has_non_core_category and not label_has_core_category:
        return False

    category_blob = _action_hit_category_blob(hit)
    has_core_category = any(token in category_blob for token in _CORE_PRESCRIPTION_CATEGORY_TOKENS)
    has_non_core_category = any(token in category_blob for token in _NON_CORE_ONLY_CATEGORY_TOKENS)

    # Warm-up, mobility, drill, and activation chunks can supplement execution
    # details, but they must not become the visible main-set prescription.
    if has_non_core_category and not has_core_category:
        return False

    return True


def _is_action_hit_aligned_with_workout_type(workout_type: str, hit: Dict[str, Any]) -> bool:
    required_tokens = _WORKOUT_TYPE_REQUIRED_CATEGORY_TOKENS.get(str(workout_type or "").strip())
    if not required_tokens:
        return True
    category_blob = _action_hit_category_blob(hit)
    return any(token.lower() in category_blob for token in required_tokens)

EVIDENCE_TIER_LABELS = {
    "action_library": "动作库课表",
    "protocol_rule": "HMP 基石协议",
    "kb_fallback": "参考知识库生成",
    "needs_evidence": "证据不足待补全",
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
    # P9: 7 个新课型关键词
    "recovery_run_z1": ["恢复跑", "Z1恢复", "主动恢复", "极松跑", "Recovery Run"],
    "general_aerobic_z2z3": ["一般有氧跑", "GA", "稳定有氧", "基础有氧", "General Aerobic"],
    "continuous_tempo_z5z6": ["连续节奏跑", "Continuous Tempo", "Tempo Run", "LT跑", "阈值巡航"],
    "mp_mixed_long_run": ["MP混合长距离", "Long/MP", "配速长距离", "马拉松模拟", "MP长距离"],
    "strides_z7z9": ["跨步跑", "Strides", "跨步", "跑姿经济性"],
    "race_simulation": ["比赛模拟", "模拟赛", "Tune-up", "彩排跑", "赛前预演"],
    "hm_specific_pace_a": ["半马专项配速", "HM Pace A", "HMP巡航", "半马比赛配速"],
}

WORKOUT_TYPE_KEYWORD_MAP.update({
    "hm_intro_fartlek_hills": ["hm_intro_fartlek_hills", "导入期法特莱克", "导入期坡跑", "短法特莱克", "75-85% HMP"],
    "hm_base_threshold_progression": ["hm_base_threshold_progression", "基础期阈值", "基础期渐速跑", "阈值巡航", "85% HMP"],
    "hm_90_support_endurance": ["hm_90_support_endurance", "90% HMP", "90%HMP", "半马辅助耐力", "辅助耐力跑"],
    "hm_95_long_fast_run": ["hm_95_long_fast_run", "95% HMP", "95%HMP", "长距离快速跑", "半马专项耐力"],
    "hm_100_float_intervals": ["hm_100_float_intervals", "100% HMP", "100%HMP", "巡航恢复", "浮动间歇"],
    "hm_105_specific_speed": ["hm_105_specific_speed", "105% HMP", "105%HMP", "专项速度", "8K/10K"],
    "hm_110_support_speed": ["hm_110_support_speed", "107-110% HMP", "110% HMP", "107% HMP", "辅助速度"],
})


# ── 动作库 JSONL 后备路径（FAISS 不可用时加载） ──
_ACTION_LIBRARY_JSONL = None  # 延迟解析


def _load_action_library_fallback() -> Dict[str, List[Dict[str, Any]]]:
    """FAISS 不可用时，从 JSONL 文件加载动作库数据。"""
    global _ACTION_LIBRARY_JSONL
    if _ACTION_LIBRARY_JSONL is not None:
        return _ACTION_LIBRARY_JSONL

    from marathon_qa_assistant.core.app_state import DATA_DIR
    jsonl_path = DATA_DIR / "knowledge" / "curated" / "action_library" / "action_library_chunks.jsonl"
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    if not jsonl_path.exists():
        logger.warning("动作库 JSONL 后备文件不存在: %s", jsonl_path)
        _ACTION_LIBRARY_JSONL = grouped
        return grouped

    try:
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                chunk = json.loads(line)
                source_file = str(chunk.get("source_file") or "动作库.pdf")
                grouped.setdefault(source_file, []).append({
                    "source_file": source_file,
                    "page": chunk.get("page"),
                    "chunk_id": chunk.get("chunk_id", ""),
                    "score": 1.0,
                    "text": chunk.get("text", ""),
                    "warmup_suggestion": chunk.get("warmup_suggestion"),
                    "cooldown_suggestion": chunk.get("cooldown_suggestion"),
                    "source_authority": chunk.get("source_authority", ""),
                    "tags": chunk.get("tags") or {},
                    "allowed_use": chunk.get("allowed_use", ""),
                    "prescription_permission": chunk.get("prescription_permission", ""),
                    "exclude_from_training_generation": chunk.get("exclude_from_training_generation", False),
                    "quality_tier": chunk.get("quality_tier", ""),
                })
    except Exception as exc:
        logger.warning("加载动作库 JSONL 失败: %s", exc)

    _ACTION_LIBRARY_JSONL = grouped
    return grouped


def get_action_library_foundation_hits(workout_type: str) -> List[Dict[str, Any]]:
    """根据训练类型从 FAISS 向量库检索动作库条目，不可用时回退 JSONL。

    原先硬编码的 ACTION_LIBRARY_FOUNDATION_HITS 已移除，现在通过 FAISS
    语义检索 动作库.pdf 的真实 chunk，或从提取的 JSONL 后备文件加载。
    """
    normalized_type = str(workout_type or "").strip()
    if not normalized_type:
        return []

    registry_entry = WORKOUT_TEMPLATE_REGISTRY.get(normalized_type, {})
    aliases = registry_entry.get("aliases", [normalized_type])
    search_query = " ".join(aliases[:5])

    # 从 JSONL 动作库检索（FAISS 语义检索作为未来升级路径）
    fallback = _load_action_library_fallback()
    matched = []
    for source_file, chunks in fallback.items():
        for chunk in chunks:
            search_blob = _action_hit_search_blob(chunk)
            if any(str(alias or "").lower() in search_blob for alias in aliases[:7]):
                matched.append(dict(chunk))

    if not matched:
        # JSONL 无匹配时尝试 FAISS（懒加载，避免阻塞常规路径）
        try:
            selected_vector_dir = None
            runtime_data = _runtime_retrieval_data()
            if runtime_data is not None:
                chunks, vectorizer, matrix, bm25, faiss_retrieve = runtime_data
                hits = faiss_retrieve(search_query, chunks, vectorizer, matrix, top_k=10, bm25=bm25)
                matched = [h for h in hits if "动作库" in str(h.get("source_file", ""))]
            else:
                candidate_dir = get_preferred_vector_dir()
                if has_vector_kb_artifacts(candidate_dir):
                    selected_vector_dir = candidate_dir
            if not matched and selected_vector_dir:
                from marathon_qa_assistant.services.vector_store import load_vector_kb, retrieve as faiss_retrieve  # noqa: E402
                chunks, vectorizer, matrix, bm25 = load_vector_kb(selected_vector_dir)
                hits = faiss_retrieve(search_query, chunks, vectorizer, matrix, top_k=10, bm25=bm25)
                matched = [h for h in hits if "动作库" in str(h.get("source_file", ""))]
                if matched:
                    logger.debug("FAISS 检索动作库命中 %d 条", len(matched))
        except Exception as exc:
            logger.debug("FAISS 动作库检索跳过: %s", exc)

    logger.debug("动作库匹配 %d 条 (type=%s)", len(matched), normalized_type)
    return matched


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
    from marathon_qa_assistant.services.vector_store import load_vector_kb, retrieve as faiss_retrieve

    runtime_data = _runtime_retrieval_data() if vector_dir is None else None
    if runtime_data is not None:
        chunks, vectorizer, matrix, bm25, retrieve_fn = runtime_data
    else:
        selected_vector_dir = vector_dir or get_preferred_vector_dir()
        if not has_vector_kb_artifacts(selected_vector_dir):
            return _empty_card(workout_type, day, "知识库产物不可用，未生成课表。")
        chunks, vectorizer, matrix, bm25 = load_vector_kb(selected_vector_dir)
        retrieve_fn = faiss_retrieve

    hits = retrieve_fn(build_workout_template_query(workout_type), chunks, vectorizer, matrix, top_k=top_k, bm25=bm25)
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
    # 从首个命中的 chunk 读取来源权威等级
    source_authority = str(relevant_hits[0].get("source_authority") or "") if relevant_hits else ""
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
        source_authority=source_authority,
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
        source_authority="C",
        main_set_candidates=main_set_candidates,
        intensity_target=registry_entry.get("intensity_target", ""),
        zone_range=registry_entry.get("zone_range", ""),
        training_objective=registry_entry.get("training_objective", ""),
        warmup_suggestion=registry_entry.get("warmup_suggestion", ""),
        cooldown_suggestion=registry_entry.get("cooldown_suggestion", ""),
        alternative_workout=registry_entry.get("alternative_workout", ""),
        evidence_tier="protocol_rule",
        evidence_status={
            "main_set_candidates": "protocol" if main_set_candidates else "missing",
            "intensity_target": "protocol" if registry_entry.get("intensity_target") else "missing",
            "training_objective": "protocol" if registry_entry.get("training_objective") else "missing",
            "warmup_suggestion": "protocol" if registry_entry.get("warmup_suggestion") else "missing",
            "cooldown": "protocol" if registry_entry.get("cooldown_suggestion") else "missing",
            "alternative_workout": "protocol" if registry_entry.get("alternative_workout") else "missing",
            "reason": "半马HMP基石协议确定性排课，动作库字段提供执行细节。",
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
        if source_file not in source_priority:
            continue
        if not _is_core_prescription_action_hit(hit):
            continue
        if not _is_action_hit_aligned_with_workout_type(workout_type, hit):
            continue
        search_blob = _action_hit_search_blob(hit)
        if any(str(alias or "").lower() in search_blob for alias in aliases[:7]):
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
    for pattern_index, pattern in enumerate(candidate_patterns):
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
        if pattern_index == 0 and candidates:
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
    if "HMP" in combined:
        if any(keyword in combined for keyword in ("有氧阈值", "阈值巡航", "基础期阈值", "基础期渐速", "渐进跑")):
            return "hm_base_threshold_progression"
        if any(keyword in combined for keyword in ("法特莱克", "坡跑", "坡冲", "坡道")):
            return "hm_intro_fartlek_hills"
        if any(keyword in combined for keyword in ("90% HMP", "90%HMP", "辅助耐力")):
            return "hm_90_support_endurance"
        if any(keyword in combined for keyword in ("95% HMP", "95%HMP", "长距离快速", "专项耐力")):
            return "hm_95_long_fast_run"
        if any(keyword in combined for keyword in ("100% HMP", "100%HMP", "巡航恢复", "浮动间歇")):
            return "hm_100_float_intervals"
        if any(keyword in combined for keyword in ("105% HMP", "105%HMP", "专项速度", "8K", "10K")):
            return "hm_105_specific_speed"
        if any(keyword in combined for keyword in ("107-110% HMP", "110% HMP", "107% HMP", "辅助速度")):
            return "hm_110_support_speed"
        # P9: 半马专项配速 A 级（需在 HMP 协议条目前优先匹配）
        if any(keyword in combined for keyword in ("半马专项配速", "HMP巡航")):
            return "hm_specific_pace_a"
    # P9: 新课型优先匹配——仅当出现新课型独有的特征词时才路由
    if any(keyword in combined for keyword in ("Z1恢复", "主动恢复", "极松跑")):
        return "recovery_run_z1"
    if any(keyword in combined for keyword in ("一般有氧跑", "General Aerobic", "GA跑")):
        return "general_aerobic_z2z3"
    if any(keyword in combined for keyword in ("连续节奏跑", "Continuous Tempo", "LT跑", "LT Run")):
        return "continuous_tempo_z5z6"
    if any(keyword in combined for keyword in ("MP混合", "Long/MP", "MP长距离")):
        return "mp_mixed_long_run"
    if any(keyword in combined for keyword in ("跨步跑", "跨步", "跑姿经济性")):
        return "strides_z7z9"
    if any(keyword in combined for keyword in ("比赛模拟跑", "模拟赛", "彩排跑", "赛前预演")):
        return "race_simulation"
    if any(keyword in combined for keyword in ("半马专项配速", "HM Pace A", "HMP巡航", "半马比赛配速")):
        return "hm_specific_pace_a"
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


_SOURCE_AUTHORITY_BADGES = {"A": "[A级 教材]", "B": "[B级 文献]", "C": "[C级 协议]"}

def _build_source_labels(hits: List[Dict[str, Any]]) -> List[str]:
    labels = []
    for hit in hits:
        source = str(hit.get("source_file") or hit.get("source") or "").strip()
        page = hit.get("page")
        authority = str(hit.get("source_authority") or "")
        if not source:
            continue
        label = f"{source}，第 {page} 页" if page else source
        # 追加权威等级标记，便于前端透传
        badge = _SOURCE_AUTHORITY_BADGES.get(authority, "")
        if badge:
            label = f"{label} {badge}"
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


def derive_stimulus_type(zone_range: str) -> str:
    """从 zone_range 推导 stimulus_type（intensity / volume_only / mixed）。

    规则:
    - Z5+ 且无 Z3-Z4 → intensity（纯高强度刺激，不可替代）
    - Z1-Z2 only → volume_only（纯低强度累积，可删减）
    - Z5+ 且有 Z3-Z4 → mixed（高低混合，保留高强度部分砍低强度部分）
    - 其余（如 Z3-Z4 only）→ volume_only

    >>> derive_stimulus_type("Z5-Z6")
    'intensity'
    >>> derive_stimulus_type("Z1-Z2")
    'volume_only'
    >>> derive_stimulus_type("Z2-Z5")
    'mixed'
    """
    zones = zone_range.replace(" ", "").split(",")
    has_high = any(f"Z{z}" in zone_range for z in ["5", "6", "7", "8", "9"])
    has_mid = any(f"Z{z}" in zone_range for z in ["2", "3"])  # Z4+ = 阈值及以上, 不计入 mid

    if has_high and has_mid:
        return "mixed"
    if has_high:
        return "intensity"
    return "volume_only"


__all__ = [
    "DailyWorkoutTemplateCard",
    "WorkoutTemplateEvidence",
    "WORKOUT_TEMPLATE_REGISTRY",
    "WORKOUT_TYPE_KEYWORD_MAP",
    "build_daily_workout_template_card_from_hits",
    "build_workout_template_query",
    "derive_stimulus_type",
    "get_action_library_foundation_hits",
    "normalize_workout_type_for_template",
    "retrieve_daily_workout_template_card",
]
