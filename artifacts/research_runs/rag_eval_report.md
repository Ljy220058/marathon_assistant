# RAG 检索质量评测基线报告

> 本报告基于 `data/vector_kb/v2/eval_dataset.json` 的 60 条标准样本生成。Retrieval-only 指标已全量完成；RAGAS 生成质量指标已完成 60 条样本，但部分早期行未记录检索后端，报告中单独列出该限制。

## 1. 数据集概况

- 样本数：60
- 样本类型：49 positive，4 near_miss，4 negative，3 out_of_domain
- 领域覆盖：training_protocol 20，nutrition 10，injury_safety 11，medical_safety 12，external_reference 4，none 3
- 引用完整性：`reference_chunk_id`、`relevant_ids`、`negative_candidate_ids` 均已验证指向真实 v2 chunk

## 2. 检索指标基线

| 指标类型 | 指标 | 数值 |
|---|---:|---:|
| 精确块命中 | Recall@5 | 0.1509 |
| 精确块命中 | MRR@5 | 0.0912 |
| 精确块命中 | MAP@5 | 0.0912 |
| 同页命中 | Recall@5 | 0.2830 |
| 同页命中 | MRR@5 | 0.2343 |
| 同页命中 | MAP@5 | 0.2343 |
| 同文档命中 | Recall@5 | 0.3585 |
| 同文档命中 | MRR@5 | 0.2862 |
| 同文档命中 | MAP@5 | 0.2862 |
| Retrieval-only | recall@5 | 0.1887 |
| Retrieval-only | precision@5 | 0.0758 |
| Retrieval-only | mrr | 0.1478 |
| Retrieval-only | negative_hit_rate | 1.0000 |
| Retrieval-only | domain_mismatch_rate | 0.2830 |
| Retrieval-only | unsafe_retrieval_rate | 0.8571 |

## 3. RAGAS 生成质量基线

- 完成样本：60/60
- 原始 JSONL 行数：65（包含历史错误行）
- 检索后端记录：{"bm25": 15, "unknown": 45}

| 指标 | 均值 | 有效样本数 |
|---|---:|---:|
| context_precision | 0.0847 | 60 |
| faithfulness | 0.6020 | 60 |
| answer_relevancy | 0.5697 | 60 |
| context_recall | 0.2072 | 60 |

### 3.2 历史错误行

- `negative_competitor`：OSError(22, 'Invalid argument')
- `negative_profile_privacy`：OSError(22, 'Invalid argument')

## 4. 已知问题清单

### 4.1 Recall@5 未命中的正例/边界样例（43 条）

- `training_taper_volume`：减量期应该如何安排训练强度和训练量？；期望领域 `training_protocol`；参考 `chunkv2_src_train_tapering_meta_2023_0017`；Top-5 `chunkv2_src_internal_hmp_protocol_pilot_0105, chunkv2_src_local_norway_method_book_2026_1678, chunkv2_src_local_norway_method_book_2026_2025, chunkv2_src_local_norway_method_book_2026_1319, chunkv2_src_internal_hmp_protocol_pilot_0011`
- `training_easy_run_share`：轻松跑和低强度跑在总跑量中应该承担什么作用？；期望领域 `training_protocol`；参考 `chunkv2_src_train_world_class_middle_distance_2021_0095`；Top-5 `chunkv2_src_internal_hmp_protocol_pilot_0037, chunkv2_src_internal_hmp_protocol_pilot_0026, chunkv2_src_local_norway_method_book_2026_1763, chunkv2_src_internal_hmp_protocol_pilot_0114, chunkv2_src_local_norway_method_book_2026_1109`
- `training_interval_pace`：间歇训练的配速和恢复应该如何控制？；期望领域 `training_protocol`；参考 `chunkv2_src_train_world_class_middle_distance_2021_0081`；Top-5 `chunkv2_src_local_norway_method_book_2026_1552, chunkv2_src_local_norway_method_book_2026_2365, chunkv2_src_local_norway_method_book_2026_2148, chunkv2_src_local_norway_method_book_2026_2638, chunkv2_src_local_norway_method_book_2026_2206`
- `training_long_run_frequency`：长距离跑在马拉松训练中应如何安排频率？；期望领域 `training_protocol`；参考 `chunkv2_src_train_marathon_physiology_2025_0363`；Top-5 `chunkv2_src_internal_hmp_protocol_pilot_0037, chunkv2_src_internal_hmp_protocol_pilot_0026, chunkv2_src_local_norway_method_book_2026_1588, chunkv2_src_local_norway_method_book_2026_1463, chunkv2_src_local_norway_method_book_2026_2449`
- `training_threshold`：乳酸阈训练对耐力跑者有什么意义？；期望领域 `training_protocol`；参考 `chunkv2_src_local_norway_method_book_2026_0017`；Top-5 `chunkv2_src_internal_hmp_protocol_pilot_0035, chunkv2_src_internal_action_library_pilot_0050, chunkv2_src_internal_hmp_protocol_pilot_0008, chunkv2_src_local_norway_method_book_2026_2482, chunkv2_src_pmc_strength_training_running_economy_2024_0023`
- `training_strength_balance`：力量训练和耐力训练如何放在同一个计划里？；期望领域 `training_protocol`；参考 `chunkv2_src_pmc_strength_training_running_economy_2024_0035`；Top-5 `chunkv2_src_local_norway_method_book_2026_2382, chunkv2_src_local_norway_method_book_2026_1296, chunkv2_src_local_norway_method_book_2026_2389, chunkv2_src_internal_hmp_protocol_pilot_0008, chunkv2_src_internal_hmp_protocol_pilot_0035`
- `training_load_progression`：增加跑量时为什么需要控制负荷进展？；期望领域 `training_protocol`；参考 `chunkv2_src_safety_subjective_load_2018_0003`；Top-5 `chunkv2_src_local_norway_method_book_2026_1001, chunkv2_src_local_norway_method_book_2026_2567, chunkv2_src_internal_hmp_protocol_pilot_0111, chunkv2_src_local_norway_method_book_2026_0741, chunkv2_src_local_norway_method_book_2026_2317`
- `training_tid`：耐力训练强度分布为什么会影响长期表现？；期望领域 `training_protocol`；参考 `chunkv2_src_train_tid_theory_2025_0162`；Top-5 `chunkv2_src_nutrition_issn_review_2018_1900, chunkv2_src_local_norway_method_book_2026_1776, chunkv2_src_pmc_strength_training_running_economy_2024_0023, chunkv2_src_train_low_intensity_2025_0106, chunkv2_src_local_norway_method_book_2026_2741`
- `training_race_pace`：马拉松目标配速应该如何和训练课连接？；期望领域 `training_protocol`；参考 `chunkv2_src_train_marathon_physiology_2025_0135`；Top-5 `chunkv2_src_internal_hmp_protocol_pilot_0037, chunkv2_src_internal_hmp_protocol_pilot_0026, chunkv2_src_local_norway_method_book_2026_1763, chunkv2_src_internal_hmp_protocol_pilot_0114, chunkv2_src_local_norway_method_book_2026_1105`
- `nutrition_during_race`：马拉松比赛中应该如何补充碳水？；期望领域 `nutrition`；参考 `chunkv2_src_nutrition_distance_runners_2019_0002`；Top-5 `chunkv2_src_local_norway_method_book_2026_1455, chunkv2_src_internal_hmp_protocol_pilot_0114, chunkv2_src_local_norway_method_book_2026_1103, chunkv2_src_internal_hmp_protocol_pilot_0002, chunkv2_src_local_norway_method_book_2026_1102`
- `nutrition_electrolytes`：长距离跑中电解质补充有什么作用？；期望领域 `nutrition`；参考 `chunkv2_src_nutrition_issn_review_2018_0162`；Top-5 `chunkv2_src_nutrition_distance_runners_2019_0077, chunkv2_src_nutrition_issn_review_2018_0227, chunkv2_src_nutrition_acsm_position_2016_0240, chunkv2_src_internal_hmp_protocol_pilot_0054, chunkv2_src_internal_hmp_protocol_pilot_0039`
- `nutrition_recovery_protein`：赛后或高负荷训练后蛋白质补充应该关注什么？；期望领域 `nutrition`；参考 `chunkv2_src_nutrition_acsm_position_2016_0192`；Top-5 `chunkv2_src_local_norway_method_book_2026_0617, chunkv2_src_local_norway_method_book_2026_1645, chunkv2_src_local_norway_method_book_2026_1626, chunkv2_src_local_norway_method_book_2026_2477, chunkv2_src_local_norway_method_book_2026_0391`
- `nutrition_gi_tolerance`：比赛补给为什么要提前在训练中测试？；期望领域 `nutrition`；参考 `chunkv2_src_nutrition_distance_runners_2019_0070`；Top-5 `chunkv2_src_nutrition_issn_review_2018_0147, chunkv2_src_nutrition_ultramarathon_issn_2019_0017, chunkv2_src_internal_nutrition_electrolyte_1_0559, chunkv2_src_internal_nutrition_hydration_1_0551, chunkv2_src_nutrition_carb_during_exercise_2014_0021`
- `nutrition_hot_conditions`：高温条件下营养和补水策略需要怎么调整？；期望领域 `nutrition`；参考 `chunkv2_src_nutrition_acsm_position_2016_0237`；Top-5 `chunkv2_src_nutrition_issn_review_2018_0424, chunkv2_src_nutrition_issn_review_2018_0226, chunkv2_src_nutrition_issn_review_2018_0227, chunkv2_src_nutrition_issn_review_2018_0229, chunkv2_src_nutrition_issn_review_2018_0228`
- `nutrition_daily_carbs`：耐力训练日常碳水摄入为什么要随训练目标变化？；期望领域 `nutrition`；参考 `chunkv2_src_nutrition_issn_review_2018_0100`；Top-5 `chunkv2_src_nutrition_issn_review_2018_1944, chunkv2_src_nutrition_issn_review_2018_1900, chunkv2_src_nutrition_issn_review_2018_0619`
- `nutrition_caffeine`：咖啡因作为比赛营养策略需要注意什么？；期望领域 `nutrition`；参考 `chunkv2_src_nutrition_issn_review_2018_0403`；Top-5 `chunkv2_src_nutrition_distance_runners_2019_0136, chunkv2_src_nutrition_issn_review_2018_0105, chunkv2_src_nutrition_issn_review_2018_0147, chunkv2_src_internal_nutrition_hydration_1_0551, chunkv2_src_nutrition_acsm_position_2016_0259`
- `injury_achilles`：跟腱疼痛时还能继续跑步吗？；期望领域 `injury_safety`；参考 `chunkv2_src_safety_running_injuries_state_art_2021_0012`；Top-5 `chunkv2_src_safety_running_msk_injuries_2012_0060, chunkv2_src_pmc_return_running_tibial_bsi_2024_0019, chunkv2_src_pmc_return_running_tibial_bsi_2024_0211, chunkv2_src_pmc_return_running_tibial_bsi_2024_0224, chunkv2_src_pmc_return_running_tibial_bsi_2024_0141`
- `injury_bone_stress_return`：胫骨骨应力损伤后恢复跑步要看哪些条件？；期望领域 `injury_safety`；参考 `chunkv2_src_pmc_return_running_tibial_bsi_2024_0057`；Top-5 `chunkv2_src_pmc_return_running_tibial_bsi_2024_0224, chunkv2_src_pmc_return_running_tibial_bsi_2024_0219, chunkv2_src_pmc_return_running_tibial_bsi_2024_0229, chunkv2_src_pmc_return_running_tibial_bsi_2024_0223, chunkv2_src_pmc_return_running_tibial_bsi_2024_0189`
- `injury_load_errors`：训练负荷错误为什么会增加跑步伤病风险？；期望领域 `injury_safety`；参考 `chunkv2_src_safety_training_errors_2012_0009`；Top-5 `chunkv2_src_pmc_return_running_tibial_bsi_2024_0162, chunkv2_src_pmc_return_running_tibial_bsi_2024_0244, chunkv2_src_pmc_return_running_tibial_bsi_2024_0161, chunkv2_src_pmc_return_running_tibial_bsi_2024_0015, chunkv2_src_pmc_return_running_tibial_bsi_2024_0160`
- `injury_overuse_risk`：过用性跑步损伤有哪些常见风险因素？；期望领域 `injury_safety`；参考 `chunkv2_src_pmc_return_running_tibial_bsi_2024_0192`；Top-5 `chunkv2_src_pmc_return_running_tibial_bsi_2024_0189, chunkv2_src_pmc_return_running_tibial_bsi_2024_0161, chunkv2_src_pmc_return_running_tibial_bsi_2024_0204, chunkv2_src_pmc_return_running_tibial_bsi_2024_0223, chunkv2_src_pmc_return_running_tibial_bsi_2024_0219`
- 其余 23 条见 `rag_eval_retrieval_only_baseline.json`。

### 4.2 负例/领域外查询仍有召回（7 条）

- `negative_rag_definition`（out_of_domain）：RAG 是什么？；Top-5 `chunkv2_src_external_cdc_sleep_about_0011, chunkv2_src_internal_hmp_protocol_pilot_0102, chunkv2_src_external_cdc_heat_athletes_0038, chunkv2_src_external_cdc_heat_athletes_0047, chunkv2_src_external_strava_uploads_api_0036`
- `negative_python_code`（out_of_domain）：怎么用 Python 写一个网页爬虫？；Top-5 `chunkv2_src_external_cdc_sleep_about_0011, chunkv2_src_internal_hmp_protocol_pilot_0102, chunkv2_src_internal_hmp_protocol_pilot_0017, chunkv2_src_internal_hmp_protocol_pilot_0025, chunkv2_src_internal_hmp_protocol_pilot_0036`
- `negative_meal_recipe`（out_of_domain）：晚饭做番茄炒蛋要放多少盐？；Top-5 `chunkv2_src_internal_hmp_protocol_pilot_0102, chunkv2_src_internal_hmp_protocol_pilot_0017, chunkv2_src_internal_hmp_protocol_pilot_0025, chunkv2_src_internal_hmp_protocol_pilot_0036, chunkv2_src_internal_hmp_protocol_pilot_0049`
- `negative_ai_hallucination`（negative）：如何评估大语言模型幻觉？；Top-5 `chunkv2_src_internal_hmp_protocol_pilot_0048, chunkv2_src_internal_hmp_protocol_pilot_0018, chunkv2_src_local_norway_method_book_2026_2364, chunkv2_src_local_norway_method_book_2026_0121, chunkv2_src_local_norway_method_book_2026_1309`
- `negative_ui_design`（negative）：健康推荐系统界面怎么设计才透明？；Top-5 `chunkv2_src_local_norway_method_book_2026_0027, chunkv2_src_local_norway_method_book_2026_1497, chunkv2_src_local_norway_method_book_2026_1546, chunkv2_src_local_norway_method_book_2026_0682, chunkv2_src_local_norway_method_book_2026_1619`
- `negative_competitor`（negative）：竞品跑步 App 的商业化功能怎么设计？；Top-5 `chunkv2_src_internal_hmp_protocol_pilot_0054, chunkv2_src_external_cdc_heat_athletes_0002, chunkv2_src_ai_generate_citations_2023_0177, chunkv2_src_local_norway_method_book_2026_0493, chunkv2_src_external_cdc_heat_athletes_0038`
- `negative_profile_privacy`（negative）：用户画像案例可以直接用来生成训练处方吗？；Top-5 `chunkv2_src_internal_hmp_protocol_pilot_0124, chunkv2_src_local_norway_method_book_2026_2330, chunkv2_src_local_norway_method_book_2026_2044, chunkv2_src_internal_hmp_protocol_pilot_0070, chunkv2_src_internal_hmp_protocol_pilot_0079`

### 4.3 领域错配查询（19 条）

- `training_tid`：期望 `training_protocol`；错配 `chunkv2_src_nutrition_issn_review_2018_1900`
- `nutrition_during_race`：期望 `nutrition`；错配 `chunkv2_src_local_norway_method_book_2026_1455, chunkv2_src_internal_hmp_protocol_pilot_0114, chunkv2_src_local_norway_method_book_2026_1103, chunkv2_src_internal_hmp_protocol_pilot_0002, chunkv2_src_local_norway_method_book_2026_1102`
- `nutrition_electrolytes`：期望 `nutrition`；错配 `chunkv2_src_internal_hmp_protocol_pilot_0054, chunkv2_src_internal_hmp_protocol_pilot_0039`
- `nutrition_recovery_protein`：期望 `nutrition`；错配 `chunkv2_src_local_norway_method_book_2026_0617, chunkv2_src_local_norway_method_book_2026_1645, chunkv2_src_local_norway_method_book_2026_1626, chunkv2_src_local_norway_method_book_2026_2477, chunkv2_src_local_norway_method_book_2026_0391`
- `injury_fatigue_monitoring`：期望 `injury_safety`；错配 `chunkv2_src_external_medlineplus_heart_warning_signs_0010`
- `injury_mtsk`：期望 `injury_safety`；错配 `chunkv2_src_internal_hmp_protocol_pilot_0035, chunkv2_src_local_norway_method_book_2026_0556, chunkv2_src_local_norway_method_book_2026_0382, chunkv2_src_internal_hmp_protocol_pilot_0104, chunkv2_src_local_norway_method_book_2026_2424`
- `medical_chest_pain`：期望 `medical_safety`；错配 `chunkv2_src_pmc_return_running_tibial_bsi_2024_0224, chunkv2_src_pmc_return_running_tibial_bsi_2024_0231, chunkv2_src_pmc_return_running_tibial_bsi_2024_0213`
- `medical_stop_refer`：期望 `medical_safety`；错配 `chunkv2_src_local_norway_method_book_2026_1962, chunkv2_src_internal_hmp_protocol_pilot_0011, chunkv2_src_local_norway_method_book_2026_1393, chunkv2_src_local_norway_method_book_2026_2033, chunkv2_src_local_norway_method_book_2026_0667`
- `medical_heart_attack_symptoms`：期望 `medical_safety`；错配 `chunkv2_src_local_norway_method_book_2026_2076, chunkv2_src_local_norway_method_book_2026_0555, chunkv2_src_local_norway_method_book_2026_0215, chunkv2_src_local_norway_method_book_2026_1350, chunkv2_src_local_norway_method_book_2026_0083`
- `environment_heat_adjust`：期望 `training_protocol`；错配 `chunkv2_src_external_cdc_heat_illnesses_0005, chunkv2_src_external_cdc_heat_illnesses_0003`
- `environment_fueling_race`：期望 `training_protocol`；错配 `chunkv2_src_nutrition_ultramarathon_issn_2019_0017, chunkv2_src_nutrition_carb_during_exercise_2014_0021, chunkv2_src_nutrition_issn_review_2018_0147, chunkv2_src_internal_nutrition_hydration_1_0551, chunkv2_src_internal_nutrition_hydration_2_0552`
- `environment_heat_safety_boundary`：期望 `training_protocol`；错配 `chunkv2_src_external_cdc_heat_illnesses_0005, chunkv2_src_external_cdc_heat_illnesses_0007, chunkv2_src_external_cdc_heat_illnesses_0003`
- `negative_ai_hallucination`：期望 `external_reference`；错配 `chunkv2_src_internal_hmp_protocol_pilot_0048, chunkv2_src_internal_hmp_protocol_pilot_0018, chunkv2_src_local_norway_method_book_2026_2364, chunkv2_src_local_norway_method_book_2026_0121, chunkv2_src_local_norway_method_book_2026_1309`
- `negative_ui_design`：期望 `external_reference`；错配 `chunkv2_src_local_norway_method_book_2026_0027, chunkv2_src_local_norway_method_book_2026_1497, chunkv2_src_local_norway_method_book_2026_1546, chunkv2_src_local_norway_method_book_2026_0682, chunkv2_src_local_norway_method_book_2026_1619`
- `near_miss_cold_run`：期望 `medical_safety`；错配 `chunkv2_src_internal_hmp_protocol_pilot_0102, chunkv2_src_internal_hmp_protocol_pilot_0017, chunkv2_src_internal_hmp_protocol_pilot_0025, chunkv2_src_internal_hmp_protocol_pilot_0036, chunkv2_src_internal_hmp_protocol_pilot_0049`
- `near_miss_knee_race`：期望 `injury_safety`；错配 `chunkv2_src_internal_hmp_protocol_pilot_0018, chunkv2_src_internal_hmp_protocol_pilot_0048, chunkv2_src_internal_hmp_protocol_pilot_0058, chunkv2_src_internal_hmp_protocol_pilot_0012, chunkv2_src_internal_hmp_protocol_pilot_0010`
- `near_miss_heat_pr`：期望 `medical_safety`；错配 `chunkv2_src_internal_hmp_protocol_pilot_0037, chunkv2_src_internal_hmp_protocol_pilot_0026, chunkv2_src_internal_hmp_protocol_pilot_0114, chunkv2_src_local_norway_method_book_2026_2454, chunkv2_src_local_norway_method_book_2026_1020`
- `negative_competitor`：期望 `external_reference`；错配 `chunkv2_src_internal_hmp_protocol_pilot_0054, chunkv2_src_external_cdc_heat_athletes_0002, chunkv2_src_local_norway_method_book_2026_0493, chunkv2_src_external_cdc_heat_athletes_0038`
- `negative_profile_privacy`：期望 `external_reference`；错配 `chunkv2_src_internal_hmp_protocol_pilot_0124, chunkv2_src_local_norway_method_book_2026_2330, chunkv2_src_local_norway_method_book_2026_2044, chunkv2_src_internal_hmp_protocol_pilot_0070, chunkv2_src_internal_hmp_protocol_pilot_0079`

## 5. 后续改进方向

- 优先分析 internal_hmp_protocol_pilot / norway_method 对训练类查询的强召回，以及 out_of_domain 查询未被拒召的问题。
- 修复 FAISS 加载稳定性后，建议用 `tools/kb/run_ragas_eval_batch.py --rerun` 重新生成一版后端一致的 RAGAS 分数。
