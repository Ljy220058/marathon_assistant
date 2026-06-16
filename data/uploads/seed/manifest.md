# Upload Seed Manifest

> 目的：索引上传种子资料、隔离资料、中文名文件和特殊字符文件。这里不判断医学或训练建议有效性，只记录检索入口和治理状态。

## Active seed files

| short_id | path | topic | source | purpose | quality_state | next_action |
|---|---|---|---|---|---|---|
| `nutrition_marathon_2016` | [2016+-+Nutrition+for+Marathon+Running.pdf](2016+-+Nutrition+for+Marathon+Running.pdf) | marathon nutrition | uploaded seed | 知识库候选资料 | active | 后续进入 curated 前补来源和质量评估 |
| `unknown_hash_pdf` | [36b5639a13f6f78e00f1c2ca46b86e854898.pdf](36b5639a13f6f78e00f1c2ca46b86e854898.pdf) | unknown | uploaded seed | 待识别资料 | active | 打开文件确认题名、来源和是否保留 |
| `ewm_base_plan` | [EWM-Training-Guides-Base-Plan.pdf](EWM-Training-Guides-Base-Plan.pdf) | training plan | uploaded seed | 训练计划知识库候选资料 | active | 补版权/来源和适用边界 |
| `basic_training_methodology` | [Level2꞉Chapter4꞉BasicTrainingMethodology_English.pdf](Level2꞉Chapter4꞉BasicTrainingMethodology_English.pdf) | training methodology | uploaded seed | 基础训练方法知识库候选资料 | active | 后续新文件名应避免特殊冒号字符 |
| `jhse_8_ii_350_366` | [jhse_Vol_8_N_II_350-366.pdf](jhse_Vol_8_N_II_350-366.pdf) | exercise science | uploaded seed | 待主题归类资料 | active | 补题名、来源和主题 |
| `movement_library_cn` | [动作库.pdf](动作库.pdf) | exercise movement library | uploaded seed | 中文动作资料入口 | active | 后续迁移时使用 ASCII slug，中文保留在标题或 manifest |
| `vo2max_lactate_threshold_cn` | [VO₂max与乳酸阈专项训练.txt](VO₂max与乳酸阈专项训练.txt) | VO2max and lactate threshold training | uploaded seed | 中文专项训练 seed 文本 | needs_review | 补来源、作者/生成方式、证据质量和适用人群 |
| `recreational_masters_runner_cn` | [大众跑者与老将跑者训练指南.txt](大众跑者与老将跑者训练指南.txt) | recreational and masters runners | uploaded seed | 中文训练指南 seed 文本 | needs_review | 补来源、作者/生成方式、证据质量和适用人群 |
| `running_biomechanics_injury_cn` | [跑步生物力学与常见运动损伤预防.txt](跑步生物力学与常见运动损伤预防.txt) | biomechanics and injury prevention | uploaded seed | 中文损伤预防 seed 文本 | needs_review | 补来源、医学边界、证据质量和适用人群 |
| `marathon_taper_prerace_cn` | [马拉松减量训练与赛前策略.txt](马拉松减量训练与赛前策略.txt) | marathon taper and pre-race strategy | uploaded seed | 中文赛前策略 seed 文本 | needs_review | 补来源、作者/生成方式、证据质量和适用人群 |
| `marathon_periodization_cn` | [马拉松周期化训练体系.txt](马拉松周期化训练体系.txt) | marathon periodization | uploaded seed | 中文周期化训练 seed 文本 | needs_review | 补来源、作者/生成方式、证据质量和适用人群 |
| `marathon_psychology_cn` | [马拉松心理训练与意志力策略.txt](马拉松心理训练与意志力策略.txt) | marathon psychology | uploaded seed | 中文心理训练 seed 文本 | needs_review | 补来源、心理健康边界、证据质量和适用人群 |
| `marathon_recovery_sleep_cn` | [马拉松恢复科学与睡眠优化策略.txt](马拉松恢复科学与睡眠优化策略.txt) | recovery and sleep | uploaded seed | 中文恢复睡眠 seed 文本 | needs_review | 补来源、医学边界、证据质量和适用人群 |
| `marathon_race_execution_cn` | [马拉松比赛策略与赛道执行.txt](马拉松比赛策略与赛道执行.txt) | marathon race execution | uploaded seed | 中文比赛执行 seed 文本 | needs_review | 补来源、作者/生成方式、证据质量和适用人群 |
| `heat_adaptation_hydration_cn` | [高温环境下的热适应与补水策略.txt](高温环境下的热适应与补水策略.txt) | heat adaptation and hydration | uploaded seed | 中文高温补水 seed 文本 | needs_review | 补来源、医学边界、证据质量和适用人群 |

## Quarantined files

| short_id | path | topic | source | purpose | quality_state | next_action |
|---|---|---|---|---|---|---|
| `quarantine_9787213062605` | [_quarantine_low_quality_20260512_knowledge_cleanup/-9787213062605.pdf](_quarantine_low_quality_20260512_knowledge_cleanup/-9787213062605.pdf) | unknown | cleanup batch 2026-05-12 | 低质量或待确认资料隔离 | quarantined | 不进入默认检索包，确认后再处理 |
| `quarantine_10078_60_2017` | [_quarantine_low_quality_20260512_knowledge_cleanup/10078-60-2017-v60-2017-28.pdf](_quarantine_low_quality_20260512_knowledge_cleanup/10078-60-2017-v60-2017-28.pdf) | unknown | cleanup batch 2026-05-12 | 低质量或待确认资料隔离 | quarantined | 不进入默认检索包，确认后再处理 |
| `quarantine_fphys_12_715044` | [_quarantine_low_quality_20260512_knowledge_cleanup/fphys-12-715044.pdf](_quarantine_low_quality_20260512_knowledge_cleanup/fphys-12-715044.pdf) | physiology | cleanup batch 2026-05-12 | 低质量或待确认资料隔离 | quarantined | 不进入默认检索包，确认后再处理 |
| `quarantine_nkf_hues_booklet` | [_quarantine_low_quality_20260512_knowledge_cleanup/NKF-Hues-Booklet.pdf](_quarantine_low_quality_20260512_knowledge_cleanup/NKF-Hues-Booklet.pdf) | booklet | cleanup batch 2026-05-12 | 低质量或待确认资料隔离 | quarantined | 不进入默认检索包，确认后再处理 |
| `quarantine_periodization_strength` | [_quarantine_low_quality_20260512_knowledge_cleanup/Periodization for Massive Strength Gains.pdf](<_quarantine_low_quality_20260512_knowledge_cleanup/Periodization for Massive Strength Gains.pdf>) | strength periodization | cleanup batch 2026-05-12 | 低质量或待确认资料隔离 | quarantined | 后续迁移时改为 `periodization_for_massive_strength_gains.pdf` |

## 使用规则

- 默认知识库构建不应自动吃入 `_quarantine_*` 目录。
- 新上传资料先进入 seed，再由人工或脚本写入来源、题名、主题和质量状态。
- 中文文件名和特殊字符文件名可暂时保留，但必须在本 manifest 中有 ASCII `short_id`。
- 迁入 curated 前需要补齐来源、版权/许可边界、适用人群和证据质量。
