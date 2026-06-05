from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "apps" / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))


DEFAULT_CHUNKS_PATH = ROOT / "data" / "vector_kb" / "v2" / "chunks.jsonl"
DEFAULT_OUTPUT_PATH = ROOT / "data" / "vector_kb" / "v2" / "eval_dataset.json"


GOLDEN_QUESTIONS: List[Dict[str, Any]] = [
    # Training protocol
    {"id": "training_taper_volume", "question": "减量期应该如何安排训练强度和训练量？", "ground_truth": "减量期通常保留一定训练强度，同时减少训练量，让疲劳下降并维持比赛专项能力。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["taper", "volume", "intensity", "减量"], "source_hints": ["train_tapering_meta_2023"]},
    {"id": "training_periodization", "question": "什么是周期化训练，它为什么适合马拉松备赛？", "ground_truth": "周期化训练把备赛拆成不同训练阶段，通过负荷、强度和恢复的有计划变化支持长期适应。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["periodization", "variation", "training", "周期"], "source_hints": ["train_world_class_middle_distance_2021", "train_tid_theory_2025"]},
    {"id": "training_easy_run_share", "question": "轻松跑和低强度跑在总跑量中应该承担什么作用？", "ground_truth": "轻松跑用于积累有氧基础和可恢复训练量，是耐力训练分布中的重要组成部分。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["easy run", "low intensity", "endurance", "aerobic"], "source_hints": ["train_tid_theory_2025", "train_world_class_middle_distance_2021"]},
    {"id": "training_interval_pace", "question": "间歇训练的配速和恢复应该如何控制？", "ground_truth": "间歇训练应围绕目标强度控制配速，并通过间歇时长和恢复安排管理整体负荷。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["interval", "pace", "recovery", "VO2max"], "source_hints": ["the-norway-method", "train_tid_theory_2025"]},
    {"id": "training_long_run_frequency", "question": "长距离跑在马拉松训练中应如何安排频率？", "ground_truth": "长距离跑用于建立专项耐力，应结合总负荷、恢复能力和比赛目标周期性安排。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["long run", "marathon", "endurance", "training"], "source_hints": ["train_marathon_physiology_2025", "the-norway-method"]},
    {"id": "training_threshold", "question": "乳酸阈训练对耐力跑者有什么意义？", "ground_truth": "乳酸阈训练帮助跑者在较高速度下维持代谢稳定，是提升耐力表现的重要训练刺激。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["threshold", "lactate", "LT", "阈值"], "source_hints": ["the-norway-method", "train_tid_theory_2025"]},
    {"id": "training_strength_balance", "question": "力量训练和耐力训练如何放在同一个计划里？", "ground_truth": "力量训练应服务于跑步经济性和抗伤能力，同时通过时机和负荷控制避免干扰关键耐力课。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["strength training", "running economy", "endurance", "balance"], "source_hints": ["src_pmc_strength_training_running_economy_2024"]},
    {"id": "training_load_progression", "question": "增加跑量时为什么需要控制负荷进展？", "ground_truth": "跑量进展过快会增加疲劳和伤病风险，训练计划需要用可恢复的负荷递增支持适应。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["training load", "progression", "adaptation", "running load"], "source_hints": ["training_load", "the-norway-method"]},
    {"id": "training_tid", "question": "耐力训练强度分布为什么会影响长期表现？", "ground_truth": "强度分布决定低强度容量和高强度刺激的比例，影响恢复、适应和比赛表现。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["training intensity distribution", "TID", "low intensity", "high intensity"], "source_hints": ["train_tid_theory_2025"]},
    {"id": "training_race_pace", "question": "马拉松目标配速应该如何和训练课连接？", "ground_truth": "目标配速应通过专项训练、节奏控制和渐进负荷连接到比赛需求，而不是孤立设定。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["marathon", "pace", "race", "specific"], "source_hints": ["half_marathon_hmp_protocol", "train_marathon_physiology_2025"]},

    # Nutrition
    {"id": "nutrition_carb_loading", "question": "赛前碳水加载应该关注哪些原则？", "ground_truth": "赛前碳水策略旨在提高糖原储备，应结合比赛时长、日常饮食和胃肠耐受来安排。", "expected_domain": "nutrition", "sample_type": "positive", "keywords": ["carbohydrate", "glycogen", "CHO", "loading"], "source_hints": ["nutrition_acsm_position_2016", "nutrition_distance_runners_2019"]},
    {"id": "nutrition_during_race", "question": "马拉松比赛中应该如何补充碳水？", "ground_truth": "比赛中碳水摄入要根据时长和强度安排，目标是在可耐受范围内维持可用能量。", "expected_domain": "nutrition", "sample_type": "positive", "keywords": ["carbohydrate", "during exercise", "CHO", "race"], "source_hints": ["nutrition_carb_during_exercise_2014", "nutrition_distance_runners_2019"]},
    {"id": "nutrition_hydration_pre", "question": "训练或比赛前补水应该怎么做？", "ground_truth": "运动前应促进良好水合状态，例如提前摄入适量水或运动饮料，同时避免过量。", "expected_domain": "nutrition", "sample_type": "positive", "keywords": ["pre-exercise hydration", "500 mL", "water", "hydration"], "source_hints": ["nutrition_issn_review_2018"]},
    {"id": "nutrition_dehydration", "question": "脱水为什么会影响耐力表现？", "ground_truth": "脱水会影响体温调节和运动能力，限制体液丢失是耐力运动营养策略的重要部分。", "expected_domain": "nutrition", "sample_type": "positive", "keywords": ["dehydration", "water", "performance", "fluid"], "source_hints": ["nutrition_issn_review_2018", "nutrition_acsm_position_2016"]},
    {"id": "nutrition_electrolytes", "question": "长距离跑中电解质补充有什么作用？", "ground_truth": "电解质策略主要用于配合补水和出汗损失管理，但应根据环境、汗率和个体耐受调整。", "expected_domain": "nutrition", "sample_type": "positive", "keywords": ["electrolyte", "sodium", "sweat", "fluid"], "source_hints": ["nutrition_acsm_position_2016", "nutrition_issn_review_2018"]},
    {"id": "nutrition_recovery_protein", "question": "赛后或高负荷训练后蛋白质补充应该关注什么？", "ground_truth": "恢复期蛋白质摄入应支持肌肉修复和适应，并与总能量和碳水补充一起考虑。", "expected_domain": "nutrition", "sample_type": "positive", "keywords": ["protein", "recovery", "muscle", "adaptation"], "source_hints": ["nutrition_acsm_position_2016", "nutrition_issn_review_2018"]},
    {"id": "nutrition_gi_tolerance", "question": "比赛补给为什么要提前在训练中测试？", "ground_truth": "补给策略需要考虑胃肠耐受，训练中测试能降低比赛中消化不适和执行失败的风险。", "expected_domain": "nutrition", "sample_type": "positive", "keywords": ["gastrointestinal", "tolerance", "race nutrition", "feeding"], "source_hints": ["nutrition_distance_runners_2019"]},
    {"id": "nutrition_hot_conditions", "question": "高温条件下营养和补水策略需要怎么调整？", "ground_truth": "高温会增加体液和热压力，补水、降温和碳水策略需要结合环境条件调整。", "expected_domain": "nutrition", "sample_type": "positive", "keywords": ["hot environments", "hydration", "heat", "fluid"], "source_hints": ["nutrition_acsm_position_2016", "nutrition_distance_runners_2019"]},
    {"id": "nutrition_daily_carbs", "question": "耐力训练日常碳水摄入为什么要随训练目标变化？", "ground_truth": "碳水需求会随训练量、强度和表现目标变化，不能只用固定摄入量覆盖所有阶段。", "expected_domain": "nutrition", "sample_type": "positive", "keywords": ["daily carbohydrate", "training", "performance goal", "carbohydrate needs"], "source_hints": ["nutrition_issn_review_2018"]},
    {"id": "nutrition_caffeine", "question": "咖啡因作为比赛营养策略需要注意什么？", "ground_truth": "咖啡因可能改善表现，但应考虑剂量、时机、个体反应和副作用。", "expected_domain": "nutrition", "sample_type": "positive", "keywords": ["caffeine", "ergogenic", "performance", "dose"], "source_hints": ["nutrition_issn_review_2018", "nutrition_acsm_position_2016"]},

    # Injury safety
    {"id": "injury_runner_knee", "question": "跑者膝或髌股疼痛在跑者中常见吗？", "ground_truth": "髌股疼痛综合征是跑步相关肌骨损伤中的常见问题，需要结合疼痛和负荷管理处理。", "expected_domain": "injury_safety", "sample_type": "positive", "keywords": ["patellofemoral", "knee", "runner", "injuries"], "source_hints": ["safety_running_msk_injuries_2012"]},
    {"id": "injury_achilles", "question": "跟腱疼痛时还能继续跑步吗？", "ground_truth": "跟腱疼痛提示可能存在肌腱负荷问题，应降低刺激并根据疼痛、功能和恢复情况决定是否跑步。", "expected_domain": "injury_safety", "sample_type": "positive", "keywords": ["Achilles", "tendon", "overuse", "injury"], "source_hints": ["safety_running_msk_injuries_2012", "src_pmc_running_overuse_risk_factors_2020"]},
    {"id": "injury_bone_stress_return", "question": "胫骨骨应力损伤后恢复跑步要看哪些条件？", "ground_truth": "骨应力损伤回跑应满足症状、负荷承受和功能标准，再从低量低强度逐步恢复。", "expected_domain": "injury_safety", "sample_type": "positive", "keywords": ["tibial", "bone stress", "returning to running", "criteria"], "source_hints": ["src_pmc_return_running_tibial_bsi_2024"]},
    {"id": "injury_load_errors", "question": "训练负荷错误为什么会增加跑步伤病风险？", "ground_truth": "负荷变化过快、恢复不足或强度安排不当会超过组织适应能力，提高过用损伤风险。", "expected_domain": "injury_safety", "sample_type": "positive", "keywords": ["training errors", "running related injuries", "load", "risk"], "source_hints": ["safety_training_errors_2012", "safety_injury_continuum_2023"]},
    {"id": "injury_overuse_risk", "question": "过用性跑步损伤有哪些常见风险因素？", "ground_truth": "过用损伤风险与训练负荷、既往伤病、身体条件和恢复状态等因素相关。", "expected_domain": "injury_safety", "sample_type": "positive", "keywords": ["overuse injuries", "risk factors", "running", "systematic review"], "source_hints": ["src_pmc_running_overuse_risk_factors_2020"]},
    {"id": "injury_fatigue_monitoring", "question": "主观疲劳和心率指标为什么能用于监控训练风险？", "ground_truth": "疲劳监控能帮助识别负荷累积和恢复不足，降低训练过量带来的风险。", "expected_domain": "injury_safety", "sample_type": "positive", "keywords": ["fatigue", "heart rate", "subjective", "monitoring"], "source_hints": ["safety_fatigue_recreational_runners_2024", "safety_subjective_load_2018"]},
    {"id": "injury_mtsk", "question": "胫骨内侧应力综合征和跑量有什么关系？", "ground_truth": "胫骨相关疼痛常与重复冲击和负荷管理有关，应关注跑量进展和症状反应。", "expected_domain": "injury_safety", "sample_type": "positive", "keywords": ["medial tibial stress syndrome", "tibial", "running injuries", "load"], "source_hints": ["safety_running_msk_injuries_2012"]},
    {"id": "injury_return_progression", "question": "伤后回跑为什么要逐步进展而不是直接恢复原跑量？", "ground_truth": "伤后组织承受能力需要重新建立，逐步进展可以观察症状反应并降低复发风险。", "expected_domain": "injury_safety", "sample_type": "positive", "keywords": ["returning to running", "progression", "30", "50"], "source_hints": ["src_pmc_return_running_tibial_bsi_2024"]},
    {"id": "injury_pain_signal", "question": "跑步疼痛什么时候应当被视为训练风险信号？", "ground_truth": "持续、加重或影响功能的疼痛应被视为风险信号，需要调整训练并考虑专业评估。", "expected_domain": "injury_safety", "sample_type": "positive", "keywords": ["pain", "injury", "risk", "running"], "source_hints": ["safety_injury_continuum_2023", "safety_running_msk_injuries_2012"]},
    {"id": "injury_prevention_strength", "question": "力量训练对跑步伤病预防可能有什么帮助？", "ground_truth": "合适的力量训练可改善组织承受能力和跑步经济性，但需要与跑步负荷协调。", "expected_domain": "injury_safety", "sample_type": "positive", "keywords": ["strength training", "injury", "running economy", "runners"], "source_hints": ["src_pmc_strength_training_running_economy_2024", "safety_running_msk_injuries_2012"]},

    # Medical safety
    {"id": "medical_chest_pain", "question": "跑步时出现胸痛应该怎么办？", "ground_truth": "跑步时胸痛属于红旗信号，应停止运动并根据症状严重程度及时寻求医疗帮助。", "expected_domain": "medical_safety", "sample_type": "positive", "keywords": ["chest pain", "heart attack", "discomfort", "symptoms"], "source_hints": ["cdc_heart_attack_symptoms"]},
    {"id": "medical_heat_stroke", "question": "热射病有哪些关键识别信号？", "ground_truth": "热射病是最严重的热相关疾病，体温失控、意识异常等情况需要紧急处理。", "expected_domain": "medical_safety", "sample_type": "positive", "keywords": ["heat stroke", "most serious", "temperature", "emergency"], "source_hints": ["cdc_heat_related_illnesses"]},
    {"id": "medical_heat_exhaustion", "question": "热衰竭和热射病为什么不能当作普通疲劳处理？", "ground_truth": "热相关疾病可能快速恶化，应停止暴露、降温并根据症状升级处理。", "expected_domain": "medical_safety", "sample_type": "positive", "keywords": ["heat exhaustion", "heat-related illness", "treat", "cool"], "source_hints": ["cdc_heat_related_illnesses"]},
    {"id": "medical_dizziness", "question": "跑步中头晕或晕厥还能继续跑吗？", "ground_truth": "头晕或晕厥提示潜在安全风险，应停止跑步、评估原因并在需要时就医。", "expected_domain": "medical_safety", "sample_type": "positive", "keywords": ["dizziness", "fainting", "syncope", "头晕"], "source_hints": ["cdc_heat_related_illnesses", "medical_dizziness_or_fainting"]},
    {"id": "medical_stop_refer", "question": "什么情况下跑者必须停止训练并考虑转诊？", "ground_truth": "胸痛、晕厥、严重热病、神经症状或其他红旗症状应优先停止训练并寻求医疗评估。", "expected_domain": "medical_safety", "sample_type": "positive", "keywords": ["medical", "red", "symptoms", "stop"], "source_hints": ["medical", "cdc"]},
    {"id": "medical_heart_attack_symptoms", "question": "心脏病发作相关症状有哪些不应忽视？", "ground_truth": "胸部不适、上肢或背部不适、呼吸急促、冷汗、恶心或头晕等都不应忽视。", "expected_domain": "medical_safety", "sample_type": "positive", "keywords": ["heart attack", "shortness of breath", "cold sweat", "nausea"], "source_hints": ["cdc_heart_attack_symptoms"]},
    {"id": "medical_heat_first_aid", "question": "怀疑热射病时第一步处理原则是什么？", "ground_truth": "怀疑热射病时应立即停止运动、呼叫急救并尽快降温，而不是继续训练。", "expected_domain": "medical_safety", "sample_type": "positive", "keywords": ["treat", "heat stroke", "call 911", "cool"], "source_hints": ["cdc_heat_related_illnesses"]},
    {"id": "medical_breath_short", "question": "跑步时异常呼吸困难是否属于安全信号？", "ground_truth": "异常呼吸困难可能提示医疗风险，特别是伴随胸痛、晕厥或其他症状时应停止并评估。", "expected_domain": "medical_safety", "sample_type": "positive", "keywords": ["shortness of breath", "heart attack", "symptom", "breath"], "source_hints": ["cdc_heart_attack_symptoms"]},
    {"id": "medical_confusion_heat", "question": "高温中出现意识混乱为什么危险？", "ground_truth": "意识混乱可能提示严重热病或热射病，需要立即停止运动和紧急处理。", "expected_domain": "medical_safety", "sample_type": "positive", "keywords": ["confusion", "heat stroke", "altered mental", "temperature"], "source_hints": ["cdc_heat_related_illnesses"]},
    {"id": "medical_do_not_prescribe", "question": "医疗风险场景为什么不能直接生成核心训练处方？", "ground_truth": "医疗风险证据只能用于安全解释和转诊提示，不能替代医生评估或写入核心训练处方。", "expected_domain": "medical_safety", "sample_type": "positive", "keywords": ["medical_risk", "explanation_only", "Permission", "Domain pack"], "source_hints": ["medical"]},

    # Environment and race context
    {"id": "environment_heat_adjust", "question": "高温天气训练应该如何调整？", "ground_truth": "高温训练应降低热压力，调整强度和时段，重视补水、降温和停止信号。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["heat", "hot", "training", "adjust"], "source_hints": ["environment_race_context", "cdc_heat"]},
    {"id": "environment_humidity", "question": "湿热环境为什么会影响跑步表现？", "ground_truth": "湿热环境会削弱散热并提高热压力，配速和补水计划需要更保守。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["humidity", "hot environments", "temperature", "heat"], "source_hints": ["nutrition_acsm_position_2016", "environment"]},
    {"id": "environment_altitude", "question": "高海拔比赛准备需要考虑什么？", "ground_truth": "高海拔会改变生理压力和营养需求，备赛应考虑适应、强度控制和恢复。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["altitude", "high-altitude", "exposure", "exercise"], "source_hints": ["nutrition_acsm_position_2016", "environment"]},
    {"id": "environment_race_travel", "question": "旅行和比赛环境变化会怎样影响赛前计划？", "ground_truth": "旅行、时差和环境变化会影响恢复与执行，赛前计划需要留出适应和调整空间。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["travel", "race", "recovery", "environment"], "source_hints": ["environment_race_context", "race"]},
    {"id": "environment_hills", "question": "坡道或丘陵比赛应如何影响配速策略？", "ground_truth": "坡道比赛应以努力程度和地形变化管理配速，避免用平路目标配速硬套全程。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["hill", "hills", "pace", "race"], "source_hints": ["environment_race_context", "the-norway-method"]},
    {"id": "environment_rain", "question": "雨天比赛策略需要关注哪些风险？", "ground_truth": "雨天比赛应关注体温、抓地、装备和补给执行，策略要随环境风险调整。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["rain", "weather", "race", "environment"], "source_hints": ["environment_race_context", "race"]},
    {"id": "environment_cold", "question": "寒冷天气训练和比赛要注意什么？", "ground_truth": "寒冷环境需要关注保暖、热身、路面风险和补给执行，训练强度也应结合安全调整。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["cold", "weather", "temperature", "training"], "source_hints": ["environment_race_context", "race"]},
    {"id": "environment_fueling_race", "question": "比赛环境变化为什么会影响补给执行？", "ground_truth": "温度、湿度、赛道和补给站条件会影响水分、碳水摄入和胃肠耐受，应提前演练。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["race", "nutrition", "hydration", "environment"], "source_hints": ["nutrition_distance_runners_2019", "environment"]},
    {"id": "environment_heat_safety_boundary", "question": "高温训练何时应从训练调整升级为安全停止？", "ground_truth": "当出现热病或红旗症状时，应从配速调整升级为停止训练和安全处理。", "expected_domain": "training_protocol", "sample_type": "near_miss", "keywords": ["heat", "stop", "safety", "training"], "source_hints": ["cdc_heat_related_illnesses", "environment"]},
    {"id": "environment_race_pacing", "question": "比赛日配速为什么要根据环境而不是只看目标成绩？", "ground_truth": "环境会改变同一配速的生理成本，比赛日应根据天气、地形和身体反应调整目标。", "expected_domain": "training_protocol", "sample_type": "positive", "keywords": ["race", "pace", "environment", "heat"], "source_hints": ["the-norway-method", "environment"]},

    # Negative / out-of-domain / near-miss
    {"id": "negative_rag_definition", "question": "RAG 是什么？", "ground_truth": "这是信息检索与生成系统问题，不属于马拉松训练处方；标准检索不应返回核心训练处方证据。", "expected_domain": "", "sample_type": "out_of_domain", "keywords": ["RAG", "retrieval augmented generation"], "source_hints": ["ai_rag"]},
    {"id": "negative_python_code", "question": "怎么用 Python 写一个网页爬虫？", "ground_truth": "这是编程问题，不属于马拉松助手知识库的训练、营养或安全问答范围。", "expected_domain": "", "sample_type": "out_of_domain", "keywords": ["Python", "code", "crawler"], "source_hints": ["ai_rag"]},
    {"id": "negative_meal_recipe", "question": "晚饭做番茄炒蛋要放多少盐？", "ground_truth": "这是通用烹饪问题，不应召回马拉松核心训练处方证据。", "expected_domain": "", "sample_type": "out_of_domain", "keywords": ["recipe", "salt", "food"], "source_hints": ["nutrition"]},
    {"id": "negative_ai_hallucination", "question": "如何评估大语言模型幻觉？", "ground_truth": "这是 AI 评测问题，最多属于解释性外部参考，不应进入马拉松训练处方证据。", "expected_domain": "external_reference", "sample_type": "negative", "keywords": ["hallucination", "faithfulness", "RAGAS"], "source_hints": ["ai_rag", "ragas"]},
    {"id": "negative_ui_design", "question": "健康推荐系统界面怎么设计才透明？", "ground_truth": "这是 HCI/推荐系统解释性问题，不应召回核心训练处方证据。", "expected_domain": "external_reference", "sample_type": "negative", "keywords": ["health recommender", "transparency", "interface"], "source_hints": ["hci"]},
    {"id": "near_miss_cold_run", "question": "感冒了可以继续跑步吗？", "ground_truth": "感冒跑步属于边界健康问题，应优先识别症状严重程度，不应直接给高负荷训练处方。", "expected_domain": "medical_safety", "sample_type": "near_miss", "keywords": ["symptoms", "medical", "risk", "stop"], "source_hints": ["medical"]},
    {"id": "near_miss_knee_race", "question": "膝盖疼但周末有比赛，还能硬跑吗？", "ground_truth": "这是伤病和比赛目标冲突的边界场景，应优先评估疼痛和安全，不应只召回配速策略。", "expected_domain": "injury_safety", "sample_type": "near_miss", "keywords": ["knee", "pain", "race", "injury"], "source_hints": ["safety_running_msk_injuries_2012"]},
    {"id": "near_miss_heat_pr", "question": "热浪天气还能按 PB 配速跑马拉松吗？", "ground_truth": "热浪天气下目标配速必须服从安全约束，应降低目标并关注热病信号。", "expected_domain": "medical_safety", "sample_type": "near_miss", "keywords": ["heat", "race", "pace", "heat stroke"], "source_hints": ["cdc_heat_related_illnesses"]},
    {"id": "negative_competitor", "question": "竞品跑步 App 的商业化功能怎么设计？", "ground_truth": "这是产品竞品分析问题，不应召回可写入核心训练处方的证据。", "expected_domain": "external_reference", "sample_type": "negative", "keywords": ["competitor", "product", "tasks"], "source_hints": ["competitor_product_tasks"]},
    {"id": "negative_profile_privacy", "question": "用户画像案例可以直接用来生成训练处方吗？", "ground_truth": "用户画像案例最多用于解释性线索和隐私治理，不应直接作为核心训练处方来源。", "expected_domain": "external_reference", "sample_type": "negative", "keywords": ["user profile", "privacy", "cases"], "source_hints": ["user_profile_cases"]},
]


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _tokens(values: Iterable[str]) -> List[str]:
    tokens: List[str] = []
    for value in values:
        value = str(value or "").strip().lower()
        if value:
            tokens.append(value)
    return tokens


def _score_chunk(question: Dict[str, Any], chunk: Dict[str, Any]) -> float:
    text = str(chunk.get("text") or "").lower()
    source_file = str(chunk.get("source_file") or "").lower()
    domain_terms = {str(item) for item in chunk.get("domain_terms") or []}
    domain_pack = str(chunk.get("domain_pack") or "").lower()
    evidence_domain = str(chunk.get("evidence_domain") or "").lower()
    expected_domain = str(question.get("expected_domain") or "")
    score = 0.0
    if expected_domain and expected_domain in domain_terms:
        score += 12.0
    if expected_domain and expected_domain in {domain_pack, evidence_domain}:
        score += 6.0
    for keyword in _tokens(question.get("keywords") or []):
        if keyword in text:
            score += 5.0
        elif any(part and part in text for part in re.split(r"\s+", keyword)):
            score += 1.5
    for hint in _tokens(question.get("source_hints") or []):
        if hint in source_file or hint in domain_pack:
            score += 4.0
    text_len = len(str(chunk.get("text") or ""))
    if text_len >= 120:
        score += 1.0
    if text_len < 40:
        score -= 2.0
    return score


def _pick_relevant_chunks(question: Dict[str, Any], chunks: List[Dict[str, Any]], *, limit: int = 3) -> List[Dict[str, Any]]:
    scored = [
        (score, chunk)
        for chunk in chunks
        if (score := _score_chunk(question, chunk)) > 0
    ]
    scored.sort(key=lambda item: (item[0], len(str(item[1].get("text") or ""))), reverse=True)
    selected: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    for _score, chunk in scored:
        chunk_id = str(chunk.get("chunk_id") or "")
        if not chunk_id or chunk_id in seen_ids:
            continue
        selected.append(chunk)
        seen_ids.add(chunk_id)
        if len(selected) >= limit:
            break
    return selected


def build_eval_dataset(chunks: List[Dict[str, Any]], questions: List[Dict[str, Any]] = GOLDEN_QUESTIONS) -> List[Dict[str, Any]]:
    dataset: List[Dict[str, Any]] = []
    for question in questions:
        relevant_chunks = _pick_relevant_chunks(question, chunks, limit=3)
        sample_type = str(question.get("sample_type") or "positive")
        if sample_type in {"positive", "near_miss"} and not relevant_chunks:
            raise ValueError(f"No relevant chunk found for required sample {question['id']}: {question['question']}")
        reference_chunk = relevant_chunks[0] if relevant_chunks else {}
        relevant_ids = [str(chunk.get("chunk_id")) for chunk in relevant_chunks if chunk.get("chunk_id")]
        dataset.append(
            {
                "id": question["id"],
                "question": question["question"],
                "ground_truth": question["ground_truth"],
                "reference_chunk_id": str(reference_chunk.get("chunk_id") or ""),
                "relevant_ids": relevant_ids,
                "expected_domain": str(question.get("expected_domain") or ""),
                "sample_type": sample_type,
                "reference_context": str(reference_chunk.get("text") or ""),
                "reference_source_file": str(reference_chunk.get("source_file") or ""),
                "negative_candidate_ids": [
                    str(chunk.get("chunk_id"))
                    for chunk in _pick_negative_candidates(question, chunks, limit=3)
                    if chunk.get("chunk_id")
                ],
            }
        )
    return dataset


def _pick_negative_candidates(question: Dict[str, Any], chunks: List[Dict[str, Any]], *, limit: int = 3) -> List[Dict[str, Any]]:
    expected_domain = str(question.get("expected_domain") or "")
    if not expected_domain:
        candidates = [chunk for chunk in chunks if "external_reference" not in set(chunk.get("domain_terms") or [])]
    else:
        candidates = [chunk for chunk in chunks if expected_domain not in set(chunk.get("domain_terms") or [])]
    candidates.sort(key=lambda chunk: len(str(chunk.get("text") or "")), reverse=True)
    return candidates[:limit]


def summarize_dataset(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_domain: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    missing_refs: List[str] = []
    for row in dataset:
        by_domain[str(row.get("expected_domain") or "none")] = by_domain.get(str(row.get("expected_domain") or "none"), 0) + 1
        by_type[str(row.get("sample_type") or "positive")] = by_type.get(str(row.get("sample_type") or "positive"), 0) + 1
        if str(row.get("sample_type") or "positive") in {"positive", "near_miss"} and not row.get("reference_chunk_id"):
            missing_refs.append(str(row.get("id") or row.get("question") or "unknown"))
    return {
        "count": len(dataset),
        "by_domain": dict(sorted(by_domain.items())),
        "by_sample_type": dict(sorted(by_type.items())),
        "missing_required_reference_ids": missing_refs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build v2 retrieval-quality golden eval dataset.")
    parser.add_argument("--chunks-path", default=str(DEFAULT_CHUNKS_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args()

    chunks = _load_jsonl(Path(args.chunks_path))
    dataset = build_eval_dataset(chunks)
    summary = summarize_dataset(dataset)
    if summary["count"] < 50:
        raise ValueError(f"eval dataset must contain at least 50 rows: {summary}")
    if summary["missing_required_reference_ids"]:
        raise ValueError(f"positive/near_miss rows missing references: {summary}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output_path), **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
