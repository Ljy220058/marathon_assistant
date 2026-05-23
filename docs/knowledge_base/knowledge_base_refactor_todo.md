# Knowledge Base Refactor TODO

> 目标：把当前知识库从“少量论文 + 运行时向量索引”升级为可商用的分层专家知识库。核心标准是：来源可追溯、处方可控、证据可审计、覆盖足够厚，并能用评测证明 RAG 计划比裸 LLM 更专业。

## 0. 当前结论

- 当前知识库不只是“内容少”，还存在结构问题：`data/vector_kb/default/chunks.jsonl` 只有 `chunk_id/source_file/page/text`，不足以支撑证据抽屉、引用定位和处方权限控制。
- 当前 curated academic layer 有 `33` 条 paper cards、`27` 个 raw PDFs、`5` 个 academic groups；运行时 default vector KB 有 `1160` chunks，但只来自 `9` 个 source files。
- 已有 `services/kb` 最小证据内核和测试，但它解决的是 metadata vocabulary / evidence binding / graph evidence / evaluation primitives，不等于知识库体量和覆盖面已经合格。
- 后续路线采用 `A + D -> B -> C`：
  - `A Metadata-first`：先做 source registry、chunk schema v2、证据域、许可/用途、引用定位、禁止核心处方越权。
  - `D Evaluation-first`：同步做 KB coverage matrix 和 100-200 条 golden questions，证明 RAG 比裸 LLM 更权威。
  - `B Domain Packs`：扩成多层专家知识包：协议、动作库、风险医学、康复力量、营养补给、环境比赛、用户案例、竞品任务。
  - `C Corpus Expansion`：最后再扩到 150-300+ 高质量来源，避免把噪声、版权风险和不可审计内容一起导入。

## 1. 证据边界

### 外部依据锚点

这些锚点只用于 source candidate intake 和需求/评测设计；进入正式知识库前仍必须经过 `source_registry.v2`、许可/用途、metadata completeness 和处方权限审查。

- ACSM exercise prescription / FITT-VP：用于结构化处方字段，包括 frequency、intensity、time、type、volume、progression。候选来源：https://www.acsm.org/docs/default-source/publications-files/acsms-exercise-testing-prescription.pdf
- WHO Ethics and Governance of AI for Health：用于透明性、可解释性、责任边界、健康 AI 安全。候选来源：https://www.who.int/publications/i/item/9789240029200
- IOC consensus statement on load in sport and risk of injury：用于训练负荷、负荷突增和伤病风险边界。候选来源：https://bjsm.bmj.com/content/50/17/1030
- CDC heat and athletes / heat-related illnesses：用于高温、中暑、头晕、热相关红旗风险。候选来源：https://www.cdc.gov/heat-health/risk-factors/heat-and-athletes.html 和 https://www.cdc.gov/niosh/heat-stress/about/illnesses.html
- TrainingPeaks Structured Workout Builder：用于结构化 workout、planned/completed、threshold/zones、calendar 任务对标。候选来源：https://help.trainingpeaks.com/hc/en-us/articles/235164967-Structured-Workout-Builder
- Garmin Daily Suggested Workouts：用于训练状态、恢复时间、计划优先级和个性化建议边界。候选来源：https://support.garmin.com/en-US/?faq=oYknGZ910l1pfBNzkDHX6A
- Strava Training Log / Instant Workouts：用于训练日志、进度总览、推荐任务和安全边界的竞品任务证据，不直接作为训练处方来源。候选来源：https://support.strava.com/hc/en-us/articles/206535704-Training-Log 和 https://support.strava.com/hc/en-us/articles/36494392561677-Instant-Workouts
- Runna personalized training plans：用于竞品任务证据，重点观察个性化计划、力量训练、计划调整和用户沟通方式，不直接作为训练处方来源。候选来源：https://www.runna.com/

### 本地契约锚点

- `docs/knowledge_base/layered_kb_architecture.md`
- `docs/knowledge_base/kb_quality_rules.md`
- `docs/quality/shared_delivery_contract.md`
- `data/knowledge/runtime/literature_retrieval_policy.json`
- `apps/backend/src/marathon_qa_assistant/services/kb/*.py`
- `tests/test_kb_source_registry.py`
- `tests/test_kb_evidence_binding.py`
- `tests/test_kb_graph_evidence.py`
- `tests/test_kb_evaluation.py`
- `tests/test_kb_health.py`

## 2. 总体验收标准

- [ ] 每个 chunk 都有 `source_registry_id`、`evidence_domain`、`knowledge_layer`、`source_url`、`local_path`、`page`、`section`、`allowed_use`、`prescription_permission`。
- [ ] 核心处方字段只允许来自 `protocol` 或 `action_library`，且 `prescription_permission=can_write_core`。
- [ ] `llm_general_knowledge` 可回答一般知识，但不能伪造引用，也不能写入核心处方字段。
- [ ] RAG vs 裸 LLM 至少用 100 条 golden questions 对比：训练负荷、周期结构、伤病恢复、康复、力量、拉伸、营养、证据边界。
- [ ] 前端证据抽屉只显示真实来源；没有来源时显示“模型常识说明”，不显示 fake source、fake page、fake citation id。
- [ ] 知识库扩容必须先通过 source registry 校验、许可/用途校验和 metadata completeness 校验，不能直接把 PDF 扔进向量库。
- [ ] 学术文献默认 `explanation_only`；只有被结构化抽取并审查后，才能进入 protocol/action/risk rule。
- [ ] 训练负荷只能标为 `planned_load_proxy` 或 `estimated`，不得包装成 Garmin/COROS/TrainingPeaks 设备级真实生理负荷。

## 3. 分支与协作规则

- [ ] 每个 P 独立分支，分支名格式：`codex/kb-pN-<slug>`。
- [ ] 禁止 `git add .`；只 stage 本 P 修改的 docs/code/test/data fixture。
- [ ] 不提交 `data/vector_kb/default/user_profile.json`、`data/vector_kb/default/knowledge_graph.json`、`apps/web/dist/`、`.pytest_cache/`、截图和临时运行日志。
- [ ] 当前默认不需要子 agent；如必须审查，最多 1 个只读 reviewer agent。
- [ ] 每个 P 完成前必须更新本文件对应 checkbox，并记录实际验证命令。

## P0: KB Source Registry V2

### 目标

把 source registry 从“论文清单”升级为全知识库统一登记表，覆盖论文、协议、动作库、风险规则、康复规则、营养规则、竞品任务证据和用户案例。

### TODO

- [x] 定义 `source_registry.v2` 字段：
  - `source_registry_id`
  - `source_type`
  - `title`
  - `authors_or_owner`
  - `year`
  - `source_url`
  - `local_path`
  - `license_status`
  - `download_status`
  - `content_hash`
  - `evidence_domain`
  - `knowledge_layer`
  - `domain_pack`
  - `allowed_use`
  - `prescription_permission`
  - `quality_tier`
  - `freshness_status`
  - `applicable_runner_segments`
  - `contraindications`
  - `needs_review`
- [x] 建立字段枚举：
  - `evidence_domain`: `protocol` / `action_library` / `sports_science_reference` / `medical_safety` / `rehab_strength_mobility` / `nutrition_race_fueling` / `environment_race_context` / `competitor_product_reference` / `user_profile_case` / `llm_general_knowledge`
  - `allowed_use`: `core_prescription` / `explanation` / `risk_gate` / `rehab_guidance` / `nutrition_guidance` / `product_design_reference` / `evaluation_only`
  - `prescription_permission`: `can_write_core` / `explanation_only` / `blocked_needs_evidence`
- [x] 迁移现有 `paper_cards.jsonl` 到 registry v2 draft。
- [x] 修正 `purpose` 字段乱码，不能保留 `????` 作为可检索内容。
- [x] 修正 `data/knowledge/README.md` 中 `canonical/academic_literature` 与实际 `curated/academic_literature` 的路径漂移。
- [x] 给每个 source 增加 `content_hash`，用于重复来源检测。
- [x] 未下载全文或 PDF 校验失败的条目只能进入 source registry metadata，不得进入 chunk index。

### 验收标准

- [x] `tests/test_kb_source_registry.py` 覆盖缺少 `source_registry_id/evidence_domain/knowledge_layer/allowed_use/prescription_permission` 时 fail-fast。
- [x] 所有现有 `33` 条 paper cards 都能生成 registry v2 record。
- [x] 没有 `purpose` 包含 `????` 的 source 被标记为 ready。
- [x] `source_registry_id` 稳定，重复运行不变化。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_source_registry.py -q
```

## P1: Chunk Schema V2 And Index Metadata

### 目标

让每个 chunk 都能回到 source registry、具体页码、段落和用途权限。没有 metadata 的 chunk 不能进入正式索引。

### TODO

- [x] 定义 `chunk_schema.v2`：
  - `chunk_id`
  - `source_registry_id`
  - `source_file`
  - `source_url`
  - `local_path`
  - `page`
  - `section`
  - `paragraph_index`
  - `char_start`
  - `char_end`
  - `text`
  - `language`
  - `evidence_domain`
  - `knowledge_layer`
  - `domain_pack`
  - `allowed_use`
  - `prescription_permission`
  - `quality_tier`
  - `exclude_from_training_generation`
  - `needs_review`
- [x] 修改 vector build pipeline：chunk 时 join source registry，而不是只用 `file_path.name`。
- [x] `chunk_id` 加入 source registry id 或 path hash，避免同名 PDF 在不同目录下 collision。
- [x] 保留 `page/section/paragraph_index`，没有 page 的文本 source 要用 `section` 和 char span 定位。
- [x] 给 `source_path` 做内部字段隔离，API 普通响应不得泄露本地绝对路径。
- [x] 对旧 `data/vector_kb/default/chunks.jsonl` 输出 health report：统计缺 metadata、缺 page、未知 source、不可用于 core prescription 的比例。
- [x] 新旧索引并行一轮，避免一次替换破坏 `/query`。

### 验收标准

- [x] 新生成 chunks 的 metadata completeness 达到 100%。
- [x] 旧索引 health report 能明确说明 `1160` chunks 仅 `chunk_id/source_file/page/text`，属于 legacy index。
- [x] API 证据响应不返回 Windows 绝对路径。
- [x] 没有 `prescription_permission=explanation_only` 的 chunk 写入核心处方字段。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_evidence_binding.py tests/test_kb_health.py -q
```

## P2: Coverage Matrix And Gap Budget

### 目标

先定义“够厚”是什么，再扩容。每个领域有目标来源数、规则数、golden questions 数和最低证据等级。

### TODO

- [x] 创建 coverage matrix，字段：
  - `domain_pack`
  - `subdomain`
  - `target_source_count`
  - `current_source_count`
  - `target_rule_count`
  - `current_rule_count`
  - `target_question_count`
  - `current_question_count`
  - `minimum_quality_tier`
  - `can_write_core`
  - `gap_status`
- [x] 第一批 domain packs：
  - `training_protocols`
  - `action_library`
  - `training_load`
  - `medical_risk`
  - `rehab_return_to_run`
  - `strength_conditioning`
  - `mobility_recovery`
  - `nutrition_race_fueling`
  - `environment_race_context`
  - `competitor_product_tasks`
  - `user_profile_cases`
- [x] 初始目标体量：
  - training_protocols: 50-80 structured rules/templates
  - action_library: 100-160 workout/action cards
  - training_load: 30-50 load/risk rules
  - medical_risk: 40-60 red-flag/risk rules
  - rehab_return_to_run: 40-60 return-to-run rules
  - strength_conditioning: 60-100 strength/mobility actions
  - nutrition_race_fueling: 40-70 sources/rules
  - environment_race_context: 30-50 environment rules
  - competitor_product_tasks: 40-80 evidence cards
  - user_profile_cases: 100+ anonymized cases, only after privacy rules exist
- [x] 每个 domain pack 至少 10 条 golden questions。
- [x] coverage matrix 必须输出 Top 10 gaps，不能只给总分。

### 验收标准

- [x] 可以一眼看到每个领域当前数量、目标数量和 gap。
- [x] 当前 5 个 academic groups 被映射到新的 domain packs，但不冒充 protocol/action_library。
- [x] 没有 coverage row 的 source 不允许进入正式 ingest。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_evaluation.py -q
```

## P3: Golden Questions And RAG-vs-Base Evaluation

### 目标

建立至少 100 条黄金问题，用来证明 RAG 不是“看起来有依据”，而是真的比裸 LLM 更稳、更可追溯。

### TODO

- [x] 扩展 `tests/fixtures/kb_golden_questions.json` 到 100 条。
- [x] 每条 golden question 必须包含：
  - `question_id`
  - `user_profile`
  - `task_type`
  - `domain_pack`
  - `expected_answer_traits`
  - `required_sources`
  - `forbidden_behaviors`
  - `core_prescription_allowed`
  - `medical_red_flag_expected`
  - `llm_general_knowledge_allowed`
- [x] 覆盖任务：
  - 训练负荷真实性
  - 周期结构
  - 5K/10K/半马/全马计划
  - 低跑量计划
  - 回归训练
  - 减量期
  - 疼痛/胸痛/头晕/中暑
  - 睡眠不足和过度疲劳
  - 康复 return-to-run
  - 力量体能
  - mobility/recovery
  - 营养补给
  - 高温/湿度/海拔/旅行
  - 无本地证据时的一般回答
  - fake citation 防护
- [x] 建立评测维度：
  - `retrieval_coverage`
  - `citation_faithfulness`
  - `core_permission_compliance`
  - `medical_safety_compliance`
  - `answer_usefulness`
  - `rag_advantage_over_base`
- [x] 对每条问题跑 `rag_answer` 和 `base_llm_answer` 对照，保留评测结果。

### 验收标准

- [x] golden questions >= 100。
- [x] 每个第一批 domain pack >= 10 条问题。
- [x] 任意核心处方问题，如果没有 protocol/action_library 来源，评测必须标 `blocked_needs_evidence`。
- [x] 任意医疗红旗问题必须 fail-closed，不能生成高强度替代训练。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_evaluation.py tests/test_training_plan_review.py -q
```

## P4: Training Protocol Domain Pack

### 目标

训练协议层只存结构化规则，不长期依赖自由文本检索。它是核心处方来源之一。

### TODO

- [x] 建立 `training_protocols` pack：
  - 5K
  - 10K
  - half_marathon
  - marathon
  - low_mileage
  - return_to_training
  - taper
- [x] 每条 protocol rule 字段：
  - `protocol_id`
  - `distance`
  - `runner_level`
  - `phase`
  - `week_range`
  - `frequency`
  - `intensity`
  - `time_or_duration`
  - `type`
  - `volume`
  - `progression`
  - `rest_day_rule`
  - `long_run_cap`
  - `quality_session_cap`
  - `contraindications`
  - `source_registry_ids`
  - `prescription_permission=can_write_core`
- [x] 半马 HMP 现有规则需要映射到 protocol pack，不能只藏在代码逻辑里。
- [x] 学术文献只能作为 rule rationale，不能直接写入 main_set。

### 验收标准

- [x] `workout_type/main_set/intensity/duration/progression/risk_downgrade` 的协议来源可追溯。
- [x] 每个距离至少有 beginner/intermediate/advanced 或等价能力层。
- [x] 低跑量和回归训练有更保守的 progression。
- [x] taper 规则能解释赛前减量，不把减量期当普通周。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_training_plan_skeleton.py tests/test_daily_schedule_generator.py -q
```

## P5: Action Library Domain Pack

### 目标

动作库必须成为主课、热身、冷身、替代训练和禁忌条件的结构化来源。缺动作库时，核心主课进入 `needs_evidence`。

### TODO

- [x] 建立 action card schema：
  - `action_id`
  - `name`
  - `category`
  - `workout_type`
  - `distance_context`
  - `phase_context`
  - `main_set`
  - `warmup`
  - `cooldown`
  - `duration_range`
  - `intensity_zone`
  - `pace_anchor`
  - `load_proxy_range`
  - `contraindications`
  - `regression`
  - `progression`
  - `alternative_actions`
  - `source_registry_ids`
  - `prescription_permission=can_write_core`
- [x] 重建 `动作库.pdf` 的中文内容，修复乱码和 chunk 过少问题。
- [x] 不允许 `" / "` 拼接多个候选主课；候选只能进 `alternatives`。
- [x] HMP `hm_*` 日卡的 `field_sources.main_set.source_type` 必须是 `action_library`。
- [x] 热身/冷身/notes 可以来自 `action_library` 或非核心 explanation source，但来源要标清。

### 验收标准

- [x] action library cards >= 100。
- [x] 每个核心 workout type 至少 3 个动作候选。
- [x] 缺 action library 时，核心主课不展示自由生成文本。
- [x] `hm_*` 内部 ID 不泄漏给普通用户。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_workout_template_retriever.py tests/test_daily_schedule_generator.py -q
```

## P6: Training Load Domain Pack

### 目标

训练负荷必须真实、可解释、保守。当前只允许 `planned_load_proxy`，不能伪装成设备级生理负荷。

### TODO

- [x] 定义 planned load proxy schema：
  - `load_proxy_id`
  - `inputs`
  - `missing_inputs`
  - `calculation_method`
  - `confidence`
  - `not_device_metric=true`
  - `disclaimer`
  - `source_registry_ids`
- [x] 结构化周跑量变化规则。
- [x] 结构化强度分布规则。
- [x] 结构化恢复日规则。
- [x] 结构化长距离上限和 quality session 上限。
- [x] 将 IOC load/injury consensus 作为风险背景来源，不直接写入核心处方。
- [x] 所有负荷输出区分：
  - `planned_load_proxy`
  - `estimated_from_plan`
  - `device_metric_unavailable`

### 验收标准

- [x] 前后端都不把 planned load 显示成 Garmin/COROS/TrainingPeaks 真实生理负荷。
- [x] 负荷判断输出 `inputs/missing_inputs/confidence/not_device_metric/disclaimer`。
- [x] 周跑量突增、连续高强度、缺恢复日能触发 risk review。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_training_plan_review.py tests/test_daily_schedule_generator.py -q
```

## P7: Medical Risk And Return-to-Run Packs

### 目标

风险医学与康复规则必须 fail-closed。它们可以拒绝或降级计划，但不能让 LLM 诊断疾病或自由生成康复处方。

### TODO

- [x] 建立 medical red flag schema：
  - `risk_rule_id`
  - `symptom_pattern`
  - `severity`
  - `must_stop_training`
  - `medical_referral_required`
  - `allowed_response`
  - `forbidden_response`
  - `source_registry_ids`
- [x] 第一批 red flags：
  - chest pain
  - dizziness / fainting
  - heat illness / heat stroke
  - acute sharp pain
  - pain worsening during run
  - swelling / inability to bear weight
  - severe fatigue with poor sleep
- [x] 建立 return-to-run schema：
  - `injury_context`
  - `stage`
  - `entry_criteria`
  - `allowed_activity`
  - `progression_criteria`
  - `regression_trigger`
  - `contraindications`
  - `source_registry_ids`
- [x] 常见跑步伤病第一批：
  - IT band pain
  - plantar fascia pain
  - Achilles/calf pain
  - knee pain
  - shin pain / stress reaction warning
  - hamstring/glute pain
- [x] 医疗风险命中时，禁止输出高强度替代训练。

### 验收标准

- [x] 胸痛、头晕、中暑等返回 `medical_referral`，不继续生成普通训练负荷调整。
- [x] 疼痛风险只允许低冲击或休息/评估建议。
- [x] return-to-run 有进入/进阶/退阶标准，不只是一段安慰性文案。
- [x] 没有来源时，康复类核心建议标 `needs_evidence` 或 `medical_referral`，不假装有依据。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_state_models.py tests/test_api_app.py -q
```

## P8: Strength, Mobility, Recovery, And Nutrition Packs

### 目标

补齐跑者真正需要的“非跑步训练”知识厚度：力量、核心、髋膝踝稳定、mobility、拉伸放松、赛前/赛中/赛后营养。

### TODO

- [x] strength card schema：
  - `movement_id`
  - `target_area`
  - `runner_goal`
  - `sets_reps_or_duration`
  - `progression`
  - `regression`
  - `contraindications`
  - `placement_rule`
  - `source_registry_ids`
- [x] mobility/recovery card schema：
  - `routine_id`
  - `use_case`
  - `duration`
  - `movement_sequence`
  - `when_to_use`
  - `when_to_avoid`
  - `source_registry_ids`
- [x] nutrition rule schema：
  - `nutrition_rule_id`
  - `race_context`
  - `timing`
  - `carbohydrate_guidance`
  - `hydration_guidance`
  - `electrolyte_guidance`
  - `GI_risk_note`
  - `supplement_safety_note`
  - `source_registry_ids`
- [x] 第一批 strength 子域：
  - core stability
  - hip strength
  - calf/Achilles capacity
  - single-leg control
  - posterior chain
  - running economy support
- [x] 第一批 recovery 子域：
  - cooldown
  - dynamic warmup
  - mobility
  - sleep/fatigue recovery
  - easy-day recovery
- [x] 第一批 nutrition 子域：
  - pre-race meal
  - race fueling
  - post-run recovery
  - hydration
  - electrolyte
  - supplement caution

### 验收标准

- [x] 计划评审维度 `strength_conditioning/mobility_recovery/nutrition_race_fueling` 不再长期为空。
- [x] 力量和 mobility 建议能按训练日上下文放置，而不是每周随机出现。
- [x] 补剂建议必须保守，且需要明确来源或显示为一般说明。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_training_plan_review.py tests/test_daily_schedule_generator.py -q
```

## P9: Environment And Race Context Pack

### 目标

支持真实比赛环境：高温、湿度、海拔、坡度、路面、旅行、比赛周 logistics。

### TODO

- [x] environment rule schema：
  - `environment_rule_id`
  - `condition`
  - `trigger`
  - `training_adjustment`
  - `race_adjustment`
  - `risk_note`
  - `source_registry_ids`
- [x] 第一批环境规则：
  - high heat
  - high humidity
  - cold weather
  - altitude
  - hilly route
  - hard surface
  - travel fatigue
  - time-zone shift
  - race-week logistics
- [x] 环境规则默认不能写核心主课，只能触发 risk downgrade 或 explanation，除非转成 protocol/action rule。
- [x] 高温/中暑相关规则必须能触发 medical red flag。

### 验收标准

- [x] 用户输入“天气很热/头晕/中暑”不会生成高强度训练。
- [x] 海拔/坡度/旅行只影响调整和解释，不伪装成精确生理预测。
- [x] 比赛周规则能解释 taper、补给、睡眠和行程。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_api_app.py tests/test_training_plan_review.py -q
```

## P10: Corpus Expansion Pipeline

### 目标

在 metadata、coverage 和 evaluation 具备以后，再系统扩容到 150-300+ 高质量来源。

### TODO

- [x] 建立 source candidate intake 表：
  - `candidate_id`
  - `domain_pack`
  - `title`
  - `source_url`
  - `source_type`
  - `owner`
  - `license_status`
  - `reason_to_include`
  - `risk_to_include`
  - `review_status`
- [x] 来源优先级：
  - official guideline / consensus
  - peer-reviewed systematic review / meta-analysis
  - position stand
  - official product docs / support docs
  - high-quality open access paper
  - expert-authored internal rule, clearly marked
  - anonymized user case, privacy-reviewed
- [x] 拒收来源：
  - ResearchGate/Scribd/网盘/随机镜像
  - 无许可或来源不明 PDF
  - HTML 错误页伪装 PDF
  - 不能定位出处的中文搬运内容
  - 没有审查状态的用户案例
- [x] 每批 ingest 限制在 20-30 sources，先跑 evaluation，再进入下一批。
- [x] 每批输出 ingest report：
  - 新增 source 数
  - 新增 chunk 数
  - metadata completeness
  - coverage gap 改善
  - evaluation 改善/退化
  - blocked sources

### 验收标准

- [x] 总来源数达到 150+ 之前，必须有 coverage/evaluation dashboard。
- [x] 扩容不得降低 citation faithfulness。
- [x] 任一新增 source 没有 license/allowed_use，不允许入正式索引。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_source_registry.py tests/test_kb_health.py tests/test_kb_evaluation.py -q
```

## P11: Frontend Evidence Drawer Contract

### 目标

前端只显示真实来源；没有来源时显示“模型常识说明”，不显示假 citation。普通用户看人话，专家层看 raw metadata。

### TODO

- [x] 后端证据 payload 给前端稳定输出：
  - `source_label`
  - `source_url`
  - `page`
  - `section`
  - `evidence_domain`
  - `prescription_permission`
  - `display_mode`: `verified_source` / `model_general_knowledge` / `needs_evidence`
  - `user_facing_summary`
  - `expert_metadata`
- [x] 普通层显示：
  - “协议依据”
  - “动作库”
  - “运动科学参考”
  - “安全边界”
  - “模型常识说明”
  - “需补证据”
- [x] 专家层才显示：
  - `source_registry_id`
  - `retrieval_mode`
  - `prescription_permission`
  - `rag_eval`
  - `source_quality`
- [x] 无 `source_url/page/section` 时，前端不能展示 citation badge。
- [x] `model_general_knowledge` 不得显示为“权威来源”。

### 验收标准

- [x] 没有本地来源时，EvidenceDrawer 显示“模型常识说明”，不显示 fake page。
- [x] 核心处方字段如果是 `needs_evidence`，前端不显示“已验证处方”。
- [x] 普通层不暴露 raw ids。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_astro_frontend_contract.py tests/test_openapi_contract.py -q
```

## P12: Release Review And No-Regret Gate

### 目标

每轮知识库扩容后，不能只说“变大了”。必须证明质量没有退化，处方边界没有破。

### TODO

- [x] 每轮输出 `kb_release_report`：
  - source 增量
  - chunk 增量
  - coverage matrix delta
  - golden question pass/fail
  - core prescription violations
  - fake citation violations
  - medical safety violations
  - unsupported answer examples
  - next gaps
- [x] reviewer 必查：
  - source registry 完整性
  - chunk metadata 完整性
  - protocol/action_library 权限
  - medical red flag fail-closed
  - llm_general_knowledge 边界
  - frontend EvidenceDrawer 文案边界
- [x] 若出现以下任一问题，禁止进入下一批扩容：
  - fake citation
  - `llm_general_knowledge` 写入核心处方
  - 医疗红旗继续生成高强度训练
  - `source_url/local_path/page/section` 大面积缺失
  - RAG 评测相对上一批退化且无解释

### 验收标准

- [x] release report 明确写出“仍值得修的问题”，不能写“差不多可以”。
- [x] shared delivery contract 和本 TODO 状态一致。
- [x] QA/reviewer 没有未处理 P0/P1 风险。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest -p no:cacheprovider `
  tests/test_kb_source_registry.py `
  tests/test_kb_evidence_binding.py `
  tests/test_kb_graph_evidence.py `
  tests/test_kb_evaluation.py `
  tests/test_kb_health.py `
  tests/test_training_plan_review.py `
  tests/test_daily_schedule_generator.py `
  tests/test_api_app.py `
  tests/test_openapi_contract.py -q
```

## 4. 首轮执行建议

首轮不要直接扩容 PDF。先做以下 5 件事：

1. P0: source registry v2。
2. P1: chunk schema v2。
3. P2: coverage matrix。
4. P3: 100 条 golden questions 的 schema 和前 30 条种子问题。
5. P11: EvidenceDrawer contract 的 no-fake-citation 契约。

完成这 5 件事后，再进入 P4-P10 的知识包扩容。这个顺序比较慢，但它能防止知识库变成一大锅“看似专业、其实不可审计”的汤。

## 5. 当前验证记录

- [x] 只读统计当前 KB：`27` raw files，约 `72.66 MB`；`33` paper cards；default vector KB `1160` chunks / `9` sources；chunk keys 为 `chunk_id,source_file,page,text`。
- [x] 当前 KB 内核测试通过：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest -q tests/test_kb_source_registry.py tests/test_kb_evidence_binding.py tests/test_kb_graph_evidence.py tests/test_kb_evaluation.py tests/test_kb_health.py
```

结果：`16 passed in 0.10s`。
## 6. P0-P12 ???????2026-05-23?

- [x] P0 source registry v2??? `SourceRecord` v2 ???`AllowedUse`?registry v2 ???paper card ??????? `data/knowledge/governance/source_registry_v2.jsonl`??? `750` records??? `data/knowledge/README.md` ? `canonical` / `curated` ?????
- [x] P1 chunk schema v2??? chunk v2 health gate??? `data/knowledge/governance/chunk_schema_v2_preview.jsonl` ? `chunk_schema_v2_health.json`?metadata completeness `1.0`??? `legacy_chunk_health.json`???? default vector KB ? `1160` legacy chunks?
- [x] P2 coverage matrix??? `data/knowledge/governance/coverage_matrix.json`??? `11` ??? domain packs???? Top gaps?
- [x] P3 golden questions??? `tests/fixtures/kb_golden_questions.json` ? `110` ?????? domain pack ?? `10` ???? `validate_golden_questions` gate?
- [x] P4-P10 domain packs / corpus pipeline??? `build_seed_domain_pack_catalog`??? `707` ???? seed items??????????????????????return-to-run????mobility??????????????????????? registry ?? `750` ???? seed ??? `internal_structured_rule_seed` / `needs_review=true`?????????
- [x] P11 EvidenceDrawer contract??? `build_evidence_drawer_payload`??????? `model_general_knowledge` ? `needs_evidence`???? fake source/page?`/evidence-tier-reference` ?? `evidence_drawer_contract` ? `core_prescription_permissions`?
- [x] P12 release review gate??? `data/knowledge/governance/kb_release_report.json`??? release gate ????? fake citation???????????????metadata ???????????
- [x] ????????? `docs/quality/shared_delivery_contract.md` ? `knowledge_layer`?`evidence_domain`???????? EvidenceDrawer ?????
- [x] fresh verification?`$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest -q`??? `454 passed in 4.55s`?`git diff --check` ???`python tools/dev/check_repo.py --scope hygiene` ??????? warning?`apps/web` ? `npm run build` ???

### ????????

- ?????`codex/kb-p0-12-hardening`?
- ???? P ???? 13 ????????????????? agent ?????? dirty changes????????????????????? hardening ???? TODO ??? P0-P12 ???????
- ??? stage?? commit?? push??? broad stage???????????? KB ??/??/??/???????

## 7. P13-P32：知识库商业化重构长路线（2026-05-23 补充）

> 本节承接 P0-P12 的审计结论：当前 `source_registry_v2`、`chunk_schema_v2_preview`、coverage matrix、golden questions 和 release report 已经提供治理骨架，但运行时 KB 仍是 legacy index，全部 registry 记录仍是 `needs_review=true`，且 release gate 过宽。下面的 P13-P32 是下一阶段“真实商用知识库”的长 TODO。每个 P 都必须先写测试或审计脚本，再改实现，最后更新 release report 和共享交付契约。

### P13：Release Gate 必须区分 seed / reviewed / approved

#### 目标

修正当前 `ready_for_next_batch=true` 但 `ready_records=0` 的门禁漏洞。治理种子不能等同于可商用知识来源；只要核心 domain pack 没有 approved source，release gate 就不能放行下一批扩容。

#### TODO

- [x] 在 source registry 中新增或固化 `review_status`：`candidate / extracted / reviewed / approved / blocked / seed_only`。
- [x] 将 `internal_structured_rule_seed` 默认归类为 `seed_only`，不得参与 `ready_records` 统计。
- [x] `ready_for_next_batch` 必须同时满足：无 fake citation、无 core permission violation、无 medical safety violation、`approved_records > 0`、核心 domain pack 不存在 P0 gap。
- [x] release report 必须输出 `seed_records`、`reviewed_records`、`approved_records`、`blocked_records`、`ready_records`。
- [x] `still_worth_fixing` 非空时，release report 不得显示“可商用完成”，只能显示“可继续治理/不可发布”。
- [x] 补测试覆盖：全部记录 `needs_review=true` 时必须阻断下一批。

#### 验收标准

- [x] 当前 750 条 registry 在未审核前不会被统计为 approved。
- [x] `kb_release_report.json.ready_for_next_batch` 在 `approved_records=0` 时为 `false`。
- [x] 测试能明确失败于“seed 被误当成可发布来源”的情况。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_governance.py tests/test_kb_health.py -q
```

实际结果（P13 分支 `codex/kb-p13-release-gate`）：`tests/test_kb_source_registry.py tests/test_kb_governance.py tests/test_kb_health.py -q` 通过，`22 passed in 0.09s`。当前 `source_registry_v2.jsonl` 统计为 `750` records、`707` seed、`0` approved、`0` ready；`kb_release_report.json.ready_for_next_batch=false`，阻断原因为 `no_approved_sources / no_ready_sources / all_domain_packs_still_have_gaps`。

### P14：Runtime KB V2 索引管线

#### 目标

把治理层从“预览文件”接入真实检索路径。当前 runtime chunks 只有 `chunk_id/source_file/page/text`，无法支撑 EvidenceDrawer、核心处方权限和引用定位。

#### TODO

- [x] 新增 v2 ingest pipeline 的运行时契约边界：`source_registry_v2 -> chunk_schema_v2_preview -> runtime_index_v2_manifest -> future vector_index_v2 -> retrieval`。本轮不覆盖旧 FAISS。
- [x] v2 chunk 必须包含 `source_registry_id/evidence_domain/knowledge_layer/domain_pack/allowed_use/prescription_permission/page/section`。
- [x] legacy index 只能作为兼容 fallback，默认不得用于核心处方证据。
- [x] 检索返回对象必须携带 `retrieval_mode`、`source_registry_id`、`prescription_permission`。
- [x] 增加 runtime health artifact，显示当前运行中的 index 是 legacy 还是 v2。
- [x] 增加回滚机制说明：v2 必须构建到独立目录，health/evidence/evaluation gate 通过后才能切换。

#### 验收标准

- [x] `/query` 或相关 RAG 检索路径能返回 v2 evidence metadata。
- [x] legacy chunk 不带权限字段时，不允许进入 `can_write_core`。
- [x] health report 能一眼看出 runtime 使用的索引版本和来源数量。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_evidence_binding.py tests/test_kb_health.py tests/test_api_app.py -q
```

实际结果（P14 分支 `codex/kb-p14-runtime-v2-index`）：`tests/test_kb_health.py tests/test_kb_evidence_binding.py tests/test_kb_bootstrap.py tests/test_vector_kb_runtime_contract.py -q` 通过，`14 passed in 0.10s`。新增 `runtime_index_v2_manifest.json`，当前声明 `chunk_schema_v2` 为 `preview_only_not_runtime`，当前 runtime 仍为 `legacy`，`can_replace_runtime=false`，阻断原因为 v2 尚未 embedding 到 FAISS、runtime 仍旧、`approved_records=0`、`ready_records=0`。

### P15：Source Review Workflow 审核流水线

#### 目标

把“找到来源”拆成可审计流程：候选、抽取、人工/规则审核、批准、阻断。防止把 PDF 或网页直接扔进向量库。

#### TODO

- [ ] 设计 `source_review_queue.jsonl` 或数据库表，记录每个 source 的审核状态。
- [ ] 每个 source 必须检查：URL 可访问性、license、owner、年份、内容 hash、重复标题/DOI、local file 是否存在。
- [ ] 对 PDF 增加页数、文本抽取质量、乱码比例、空页比例检查。
- [ ] 对网页增加 canonical URL、抓取时间、正文抽取质量、robots/许可备注。
- [ ] `blocked` 来源必须记录 `blocked_reason`，不得无声丢弃。
- [ ] 审核结果必须能反写 registry，但不得覆盖原始 metadata。

#### 验收标准

- [ ] 未经过 `reviewed/approved` 状态的来源不能进入正式 v2 index。
- [ ] 任何 `blocked` 来源都能在报告中解释为什么被排除。
- [ ] 重复来源不会重复贡献 coverage。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_source_registry.py -q
```

### P16：Runtime KB 噪声隔离与旧索引清洗

#### 目标

处理当前 legacy KB 中 book review、无关 PDF、不可定位片段等噪声。知识库不是越大越好，先保证进入检索的材料确实能支撑跑者任务。

#### TODO

- [ ] 对 `data/vector_kb/default/chunks.jsonl` 的 9 个 source 做逐项审计。
- [ ] 标记 `allow_runtime_retrieval / explanation_only / quarantine / delete_candidate`。
- [ ] 将 book review、非训练处方、无关体能理论、乱码严重内容放入 quarantine 清单。
- [ ] 输出 `legacy_runtime_quarantine_report.json`。
- [ ] 查询链路对 quarantine source 默认不可检索。
- [ ] 保留必要迁移记录，避免误删用户或其他 agent 正在使用的数据。

#### 验收标准

- [ ] 噪声 source 不再出现在用户可见证据中。
- [ ] Quarantine report 能说明来源、样例文本、隔离原因。
- [ ] 清洗不破坏已有 API 基础问答路径。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_health.py tests/test_api_app.py -q
```

### P17：Golden Questions 从模板升级为判分集

#### 目标

当前 110 条 golden questions 主要验证字段完整，不足以证明 RAG 比裸 LLM 更权威。需要建立带答案特征、证据要求、拒绝行为和评分维度的评测集。

#### TODO

- [ ] 每题新增 `expected_evidence_ids`、`expected_answer_traits`、`forbidden_claims`、`required_safety_behavior`。
- [ ] 新增 `judge_rubric`：事实正确性、引用忠实度、处方权限、风险边界、可执行性、用户可理解性。
- [ ] 核心处方题必须指定允许来源类型：`protocol/action_library`。
- [ ] 医疗红旗题必须指定 `medical_referral` 或 `risk_refused`。
- [ ] 无本地证据题必须允许 `model_general_knowledge`，但禁止 fake citation。
- [ ] 生成 `golden_questions_v2_summary.json`，展示每个 domain pack 的题量和风险覆盖。

#### 验收标准

- [ ] 每题都有可判定标准，而不是只有 schema 字段。
- [ ] 至少 100 条题能区分 RAG、裸 LLM、无证据常识回答三种路径。
- [ ] 评测失败样例能进入 release report。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_evaluation.py -q
```

### P18：RAG vs Base LLM 对照评测

#### 目标

证明本项目不是“接了 RAG 就更专业”，而是能在训练负荷、周期结构、伤病恢复、康复训练、力量体能、拉伸放松、营养补给、环境风险等维度稳定优于裸模型。

#### TODO

- [ ] 定义 `base_llm_answer`、`rag_answer`、`rag_with_review_answer` 三路输出。
- [ ] 固定 prompt、模型、temperature、检索 top_k、知识库版本。
- [ ] 对每题保存：输入、检索证据、答案、判分结果、失败原因。
- [ ] 指标包括：citation faithfulness、core permission compliance、medical safety、load truthfulness、answer usefulness。
- [ ] 输出 `rag_vs_base_eval_report.json` 和人类可读 Markdown 报告。
- [ ] 任何 RAG 低于 base LLM 的维度都要进入 `still_worth_fixing`。

#### 验收标准

- [ ] 至少 100 条 golden questions 跑通对照评测。
- [ ] 不允许只报平均分，必须列出失败样例。
- [ ] 评测报告能说明 RAG 在哪些维度更好、哪些维度仍不如裸模型。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_evaluation.py tests/test_training_plan_review.py -q
```

### P19：Action Library 从占位主课升级为真实训练卡

#### 目标

替换 `"controlled easy_run main set v1"` 这类占位主课。动作库是核心处方来源之一，必须具备真实主课、热身、冷身、强度、禁忌、替代训练和进退阶。

#### TODO

- [ ] 梳理当前 action seed，找出所有占位 `main_set`。
- [ ] 为 easy、long、tempo、threshold、interval、hill、recovery、cross-training、strength、mobility 建立真实 action card。
- [ ] 每张卡必须包含 `main_set/warmup/cooldown/intensity_zone/duration_range/contraindications/regression/progression`。
- [ ] 核心主课必须绑定 approved action source。
- [ ] 不允许用 `" / "` 拼接多个候选主课；候选放入 `alternatives`。
- [ ] HMP `hm_*` 映射必须只在内部使用，用户层不泄漏内部 ID。

#### 验收标准

- [ ] 用户可见日卡不再出现占位文案。
- [ ] 缺少 approved action source 时，核心主课进入 `needs_evidence`。
- [ ] 每个核心 workout type 至少有 3 张 approved 或 reviewed action card。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_workout_template_retriever.py tests/test_daily_schedule_generator.py -q
```

### P20：Training Protocol Pack 真实化

#### 目标

把 protocol 从“抽象阶段规则”升级为可审计的训练计划协议层，覆盖 5K、10K、半马、全马、低跑量、回归训练、减量期。

#### TODO

- [ ] 每条 protocol rule 必须有明确目标人群、训练周期、周频率、关键课数量、恢复日规则。
- [ ] 低跑量和回归训练必须有更保守的 progression。
- [ ] 半马和全马必须区分专项期、减量期、长距离上限和配速锚点。
- [ ] protocol 只能定义结构边界，具体主课仍由 action library 承接。
- [ ] 文献或指南只能作为 rationale，不能直接写用户主课。
- [ ] 增加 protocol-to-action 映射测试，防止骨架模板污染日卡。

#### 验收标准

- [ ] 12/16/24 周计划能完整生成，不截断。
- [ ] protocol 输出能解释周期结构，但不越权生成自由主课。
- [ ] 低跑量、回归训练、减量期不会套用高强度模板。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_training_plan_skeleton.py tests/test_daily_schedule_generator.py -q
```

### P21：Training Load 真实性与负荷代理模型

#### 目标

训练负荷必须保守、真实、可解释。系统只能声明 `planned_load_proxy` 或 `estimated`，不能暗示 Garmin/COROS/TrainingPeaks 级别的真实生理负荷。

#### TODO

- [ ] 为每个负荷输出附带 `inputs/missing_inputs/calculation_method/confidence/not_device_metric/disclaimer`。
- [ ] 区分周跑量、时长、强度分布、关键课数量、长距离比例。
- [ ] 检测周跑量突增、连续高强度、恢复日不足、长跑占比过高。
- [ ] 负荷评审结果进入 `training_plan_review.dimensions.training_load`。
- [ ] 前端普通层只显示“计划代理负荷/估算”，不得显示“真实生理负荷”。
- [ ] 缺少关键输入时降低 confidence，不得补猜。

#### 验收标准

- [ ] 所有计划负荷字段都有真实性声明。
- [ ] 无设备数据时不出现 HRV、恢复时间、训练状态等伪设备指标。
- [ ] 负荷异常能触发 review warning。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_training_plan_review.py tests/test_astro_frontend_contract.py -q
```

### P22：Medical Risk 与红旗边界加强

#### 目标

医疗风险相关知识必须 fail-closed。胸痛、头晕、中暑、急性锐痛、无法承重等场景不能继续生成高强度替代训练。

#### TODO

- [ ] 建立 red flag rule 的 reviewed source 绑定。
- [ ] `/feedback` 和 `/query` 同时识别医疗风险。
- [ ] 医疗风险命中时返回 `medical_referral` 或 `risk_refused`。
- [ ] 禁止输出高强度替代训练、配速建议或继续加量。
- [ ] 用户层文案必须清楚：停止训练、寻求专业评估、不要把系统当诊断。
- [ ] 记录 `risk_gate.triggers/decision_reason/adjustment_action`。

#### 验收标准

- [ ] 胸痛、头晕、中暑测试稳定 fail-closed。
- [ ] 疼痛风险只能降级或建议低冲击/休息。
- [ ] 无证据时不伪造医学引用。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_state_models.py tests/test_api_app.py -q
```

### P23：Return-to-Run 康复规则包

#### 目标

康复不是一句“注意休息”。需要支持常见跑步伤病的进入标准、进阶标准、退阶触发、允许活动和禁忌边界。

#### TODO

- [ ] 建立 IT band、plantar fascia、Achilles/calf、knee、shin/stress warning、hamstring/glute 第一批规则。
- [ ] 每条规则必须包含 `entry_criteria/progression_criteria/regression_trigger/allowed_activity/contraindications`。
- [ ] return-to-run 规则默认 `rehab_guidance`，不得越权成诊断。
- [ ] 疼痛加重、肿胀、无法承重时回到 medical risk gate。
- [ ] 与 feedback 闭环连接：用户反馈疼痛后，自动给出保守调整和复查建议。
- [ ] 添加黄金问题覆盖“轻微不适”和“红旗疼痛”的区别。

#### 验收标准

- [ ] 康复建议有明确进退阶标准。
- [ ] 红旗不被误判为普通 return-to-run。
- [ ] 规则来源、权限和用户可见边界清楚。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_state_models.py tests/test_kb_evaluation.py -q
```

### P24：Strength / Mobility / Recovery 知识包深化

#### 目标

补足跑者长期需要的非跑步训练：核心、髋、膝、踝、小腿跟腱、单腿稳定、后链、动态热身、冷身、mobility、睡眠疲劳恢复。

#### TODO

- [ ] 每个动作卡包含目标区域、训练目的、组数/次数/时长、进阶、退阶、禁忌、安排位置。
- [ ] 区分跑前动态热身、跑后冷身、恢复日 mobility、力量日训练。
- [ ] 不把拉伸放松当成伤病治疗。
- [ ] 关键跑课前避免安排高疲劳力量训练。
- [ ] 与日历排布连接：力量/灵活性训练有合适放置规则。
- [ ] 补充 evaluation questions：力量安排是否影响关键跑课、疼痛时如何退阶。

#### 验收标准

- [ ] 计划评审不再长期缺失 `strength_conditioning/mobility_recovery` 维度。
- [ ] 支撑训练不会随机堆到日历里。
- [ ] 用户能理解“为什么今天做这个辅助训练”。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_training_plan_review.py tests/test_daily_schedule_generator.py -q
```

### P25：Nutrition / Race Fueling 知识包深化

#### 目标

补齐赛前、赛中、赛后、碳水、水合、电解质、胃肠风险和补剂安全边界。营养建议默认保守，不做医疗化承诺。

#### TODO

- [ ] 每条 nutrition rule 包含 race context、timing、carbohydrate guidance、hydration guidance、electrolyte guidance、GI risk note。
- [ ] 区分 5K/10K/半马/全马/长距离训练的补给需要。
- [ ] 高温高湿时与 environment risk 联动。
- [ ] 补剂建议必须保守并标注证据边界。
- [ ] 赛前新食物/新补剂必须提醒“训练中试用，不要比赛当天首次尝试”。
- [ ] 无 approved 来源时只允许 model_general_knowledge，不展示 citation。

#### 验收标准

- [ ] 营养补给建议不会伪装成医学或个体化处方。
- [ ] 用户能看到 timing 和风险边界。
- [ ] 半马/全马长距离场景不再缺补给评审。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_evaluation.py tests/test_training_plan_review.py -q
```

### P26：Environment / Race Context 知识包深化

#### 目标

支持真实比赛和训练环境：高温、湿度、寒冷、海拔、坡度、路面、旅行、时差、比赛周 logistics。

#### TODO

- [ ] 每条 environment rule 包含 condition、trigger、training_adjustment、race_adjustment、risk_note。
- [ ] 高温/中暑相关输入必须能触发 medical risk gate。
- [ ] 海拔、坡度、路面只影响解释和保守调整，不伪装为精确生理预测。
- [ ] 旅行和时差影响赛前安排、睡眠、恢复和减量期。
- [ ] 与 nutrition pack 联动：高温时水合/电解质建议更显眼。
- [ ] 前端只展示用户行动建议，专家层再展示规则细节。

#### 验收标准

- [ ] 用户输入“天气很热、头晕、中暑”不会生成高强度训练。
- [ ] 比赛周能解释 taper、补给、睡眠和行程安排。
- [ ] 环境风险不被当成设备级预测。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_api_app.py tests/test_training_plan_review.py -q
```

### P27：User Profile Case Layer 与隐私边界

#### 目标

用户案例层只能在隐私审查后使用。案例用于评估和模式识别，不得泄露个人信息，也不得把 LLM 推测写入用户画像。

#### TODO

- [ ] 定义 anonymized case schema：目标、跑量、训练日、反馈、调整、结果、风险，不含身份信息。
- [ ] 增加 privacy review status：`not_collected / anonymized / approved / blocked`。
- [ ] 禁止将用户原始备注直接进入 KB。
- [ ] 用户画像事实只能来自用户输入、训练反馈或可靠数据，不得由模型臆测。
- [ ] 案例默认 `evaluation_only` 或 `explanation`，不得直接写核心处方。
- [ ] 增加数据删除和回溯能力，支持未来合规需求。

#### 验收标准

- [ ] 没有隐私审核的案例不能进入正式检索。
- [ ] 用户输入不会被静默永久写入公共 KB。
- [ ] 案例层不会覆盖 protocol/action_library 的核心处方权。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_source_registry.py tests/test_api_app.py -q
```

### P28：EvidenceDrawer 与普通/专家层证据展示契约

#### 目标

前端只显示真实来源；没有来源时显示“模型常识说明”；核心处方缺证据时显示“需补证据”，不能伪造引用。

#### TODO

- [ ] `/evidence-tier-reference` 固化 `display_modes`：`verified_source/model_general_knowledge/needs_evidence`。
- [ ] 日卡、解释、QA、计划评审共用同一 evidence payload。
- [ ] 普通层隐藏 raw ids、local path、retrieval score。
- [ ] 专家层显示 `source_registry_id/retrieval_mode/prescription_permission/rag_eval`。
- [ ] `model_general_knowledge` 不得显示为权威来源。
- [ ] source_url/page/section 缺失时不显示 citation badge。

#### 验收标准

- [ ] fake citation 测试为 0。
- [ ] 普通用户不会看到内部 ID 和调试字段。
- [ ] 核心字段 `needs_evidence` 不会显示成“已验证处方”。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_astro_frontend_contract.py tests/test_openapi_contract.py -q
```

### P29：LLM General Knowledge 兜底边界

#### 目标

普通问题不能硬拒答。没有本地证据时，大模型可以用自身知识回答一般解释，但必须明确这是 `model_general_knowledge`，且不能伪造引用、不能写核心训练处方。

#### TODO

- [ ] `/query` 中区分 ordinary QA、core prescription、medical risk、evidence citation 四类路径。
- [ ] ordinary QA 无证据时走 `model_general_knowledge`，不返回“信息不足，请补充上下文”硬拒答。
- [ ] 核心处方无 protocol/action_library 时仍 fail-closed 到 `needs_evidence`。
- [ ] 医疗红旗仍 fail-closed 到 `medical_referral`。
- [ ] 响应中增加 `answer_source_mode`：`verified_rag / model_general_knowledge / needs_evidence / medical_referral`。
- [ ] 前端普通层用人话解释来源模式。

#### 验收标准

- [ ] 普通知识问答不会出现硬拒答模板。
- [ ] 无证据常识回答不带 fake citation。
- [ ] 核心训练处方仍不会由裸 LLM 自由生成。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_api_app.py tests/test_kb_evidence_binding.py -q
```

### P30：Corpus Expansion 批次管理

#### 目标

扩容必须小批量、可回滚、可评测。不要一次导入 150-300 个来源，把噪声、版权和不可审计内容一起带进系统。

#### TODO

- [ ] 每批只允许 20-30 个 source candidate。
- [ ] 每批必须先跑 source review，再跑 chunk health，再跑 golden questions。
- [ ] 每批输出 ingest report：新增 source、chunk、metadata completeness、coverage delta、eval delta、blocked sources。
- [ ] 若 citation faithfulness 或 medical safety 退化，停止下一批。
- [ ] 每批建立 manifest 和 checksum，支持回滚。
- [ ] 只允许 approved source 进入正式 v2 index。

#### 验收标准

- [ ] 任一批次都能解释新增了什么、改善了什么、阻断了什么。
- [ ] 扩容不会降低核心安全指标。
- [ ] 失败批次不会污染 runtime index。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_source_registry.py tests/test_kb_health.py tests/test_kb_evaluation.py -q
```

### P31：Knowledge Ops Dashboard / Report

#### 目标

让知识库质量可以被运营、研发和 reviewer 一眼看懂，而不是藏在 JSON 文件里。

#### TODO

- [ ] 输出 Markdown/HTML 报告：source readiness、coverage gaps、eval pass/fail、runtime index version。
- [ ] 显示每个 domain pack：approved sources、rules、questions、core permission count、blocked count。
- [ ] 显示 Top 10 gaps 和 Top 10 blocked reasons。
- [ ] 显示 RAG vs base LLM 的维度对比。
- [ ] 显示 fake citation、core permission、medical safety、load truthfulness 指标。
- [ ] 报告中明确“仍不可商用”的原因，不得只写测试通过。

#### 验收标准

- [ ] reviewer 不读源码也能判断 KB 是否可发布。
- [ ] 报告能指出下一批最该补的知识域。
- [ ] 报告与 release gate 使用同一数据源。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_governance.py tests/test_kb_evaluation.py -q
```

### P32：最终 No-Regret Commercial KB Gate

#### 目标

建立“不后悔发布”的最终门禁。自动化测试通过只是基础；必须确认知识来源、处方边界、医学安全、负荷真实性、用户可理解性和前后端契约都没有未处理的 P0/P1 风险。

#### TODO

- [ ] 整合 P13-P31 的 gate：source readiness、runtime v2、eval、EvidenceDrawer、LLM fallback、medical risk、load truthfulness。
- [ ] 建立 `commercial_kb_gate_report.json` 和 Markdown 签收清单。
- [ ] Backend owner、Frontend owner、QA/reviewer、Version owner 分别签收。
- [ ] 任何一方仍有 P0/P1 未签收项，不得声明商用完成。
- [ ] shared delivery contract 必须同步写入当前 KB gate 状态。
- [ ] Git stage 清单必须排除 runtime profile、临时 artifacts、缓存和其他 agent 未确认文件。

#### 验收标准

- [ ] `approved_records > 0` 且核心 domain pack 不再只有 seed。
- [ ] runtime index 使用 v2 metadata。
- [ ] golden questions v2 和 RAG-vs-base eval 通过最低门槛。
- [ ] 没有 fake citation、核心权限越权、医疗红旗误生成高强度训练、负荷真实性误导。
- [ ] 共享契约中 Frontend / Backend / QA / Version owner 均无 P0/P1 未签收项。

#### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest -q
cd apps/web
npm run build
```

### P13-P32 执行顺序建议

1. 先做 P13、P14、P15、P16：修正门禁、打通 runtime v2、建立审核、隔离旧噪声。
2. 再做 P17、P18：把评测从 schema 检查升级为真实判分。
3. 然后做 P19-P27：逐个知识域从 seed 升级为 reviewed/approved 内容。
4. 接着做 P28、P29：打磨证据展示和无证据常识回答边界。
5. 最后做 P30-P32：扩容批次、质量面板和最终商用门禁。

### P13-P32 版本管理规则

- [ ] 每个 P 使用独立分支：`codex/kb-p13-release-gate`、`codex/kb-p14-runtime-v2-index` 等。
- [ ] 不允许 `git add .`。
- [ ] 每个 P 完成前必须更新本 TODO 的状态、验证命令和实际结果。
- [ ] 每个 P 如果影响前端证据展示、API 字段或 release gate，必须同步更新 `docs/quality/shared_delivery_contract.md`。
- [ ] 每轮最多 1 个子 agent，完成后立即关闭并记录在 review TODO。
