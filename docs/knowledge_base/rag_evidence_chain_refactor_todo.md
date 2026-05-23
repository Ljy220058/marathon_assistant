# RAG Evidence Chain Refactor TODO

> 目标：把当前 RAG、知识库、引用和前端证据展示链路从“能返回来源摘要”升级为“可审计、可证明、可商用的证据系统”。本 TODO 专门处理证据链路，不替代 `docs/knowledge_base/knowledge_base_refactor_todo.md` 的知识库扩容计划。

## 0. 当前审计结论

### 本地事实

- 当前运行分支：`codex/kb-rag-evidence-chain-todo`。
- 当前工作区存在大量并行前端修改，本轮只新增本 TODO 和必要共享契约，不 stage 或覆盖其他 agent 的前端改动。
- 当前 runtime KB：`data/vector_kb/default/chunks.jsonl` 有 `1160` 个 legacy chunk，来自 `9` 个 source file，只包含 `chunk_id/page/source_file/text`，没有 `source_registry_id/evidence_domain/knowledge_layer/allowed_use/prescription_permission/source_url/section`。
- 当前 source registry v2：`data/knowledge/governance/source_registry_v2.jsonl` 有 `750` 条，其中 `707` 条 `seed_only`，`43` 条 `candidate`，`approved_records=0`，`ready_records=0`。
- 当前 release gate：`data/knowledge/governance/kb_release_report.json` 显示 `commercial_release_ready=false`，阻塞项包括 `no_approved_sources`、`no_ready_sources`、`all_domain_packs_still_have_gaps`。
- 当前 runtime v2 manifest：`data/knowledge/governance/runtime_index_v2_manifest.json` 显示 `status=preview_only_not_runtime`、`runtime_index_schema_version=legacy`、`can_replace_runtime=false`。
- 当前 legacy quarantine：`data/knowledge/governance/legacy_runtime_quarantine_report.json` 已隔离 `10078-60-2017-v60-2017-28.pdf`，其余 legacy source 只能作为 explanation-only fallback。
- 当前 golden questions v2：`tests/fixtures/kb_golden_questions_v2.json` 有 `110` 题，并有 `expected_evidence_ids/forbidden_claims/required_safety_behavior/judge_rubric`。
- 当前相关回归命令已通过：`python -m pytest tests/test_kb_governance.py tests/test_kb_source_review.py tests/test_kb_runtime_quarantine.py tests/test_kb_health.py tests/test_kb_evidence_binding.py tests/test_vector_kb_runtime_contract.py -q`，结果 `32 passed`。

### 证据链主要断点

- `build_rag_sources()` 只保留 legacy 字段，丢失 v2 permission metadata；即使底层 hit 有 `source_registry_id`，进入 `rag_sources` 后仍会被压扁。
- `build_ranked_evidence()` 对 vector hit 也只抽 `source_file/page/chunk_id/text/score`，没有保存 `source_url/section/evidence_domain/prescription_permission/allowed_use`。
- `evidence_bundle` 会把 `rag_sources` 与 `ranked_evidence` 混合重编号，但 `citation_label` 的有效性只在部分 auditor 中检查，API response 没有统一暴露 `answer_source_mode`。
- `evidence_base_from_bundle()` 会把 `source_path` 和 `source_file` 继续回传给前端，缺少 public/expert 投影边界；普通用户层有机会看到本地路径或 legacy 文件名。
- 前端 `collectEvidenceItems()`、`buildDayEvidenceItems()` 和后端 `/evidence-tier-reference` 的 `evidence_drawer_contract` 不是同一个 DTO；前端仍有“补模型知识说明”“结构化计划规则”这种本地拼接证据项。
- 日卡 `field_sources/kb_metadata/action_match` 与 QA `evidence_bundle/evidence_base` 是两套结构；用户点击“查看依据”时可能看到“日卡主课来源”和“QA 文本来源”不一致。
- Graph evidence 的 `map_edge_to_evidence()` 路径仍可能生成 graph-only evidence；如果没有可定位 `source_url/page/section/chunk_id`，只能作为 graph hint，不能展示为 verified citation。
- `/query` 的普通问答无证据时已经开始走 `llm_general_knowledge`，但 response contract 未全局固化，前端仍可能只读 Markdown，不知道这是“模型常识说明”而非证据。
- 当前 runtime health 能说明 `legacy`，但 `/query` 和前端证据抽屉没有强制根据 `runtime_core_prescription_enabled=false` 降级所有核心处方引用状态。
- 训练计划评审 `training_plan_review` 已检查核心字段来源违规，但它不是证据链 gate 的唯一出口，还缺少“一条回答中每个引用都能在 evidence payload 中定位”的端到端测试。

### 外部依据锚点

- WHO 健康 AI 指南强调健康 AI 必须把伦理、人权、治理和责任边界纳入设计与部署，适合作为本项目健康/训练建议透明边界依据。来源：[WHO Ethics and governance of artificial intelligence for health](https://www.who.int/publications/i/item/9789240029200)。
- NIST AI RMF 强调把可信性纳入 AI 产品设计、开发、使用和评估，适合作为 release gate 与风险管理依据。来源：[NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)。
- OWASP LLM Top 10 明确列出 prompt injection、insecure output handling、training data poisoning、sensitive information disclosure、overreliance 等 LLM 应用风险，适合作为 RAG 检索内容安全和引用输出安全依据。来源：[OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)。
- OpenAI Retrieval 文档把 vector store、ranking options、score threshold、hybrid search 权重等作为检索质量控制接口，适合作为本项目检索参数审计和可观测性设计参考。来源：[OpenAI Retrieval Guide](https://platform.openai.com/docs/guides/retrieval)。
- RAGAS 论文把 RAG 评价拆为 retrieval context relevance、faithful exploitation of context、generation quality 等维度，适合作为 golden questions v2 的自动评测维度参考。来源：[Ragas: Automated Evaluation of Retrieval Augmented Generation](https://arxiv.org/abs/2309.15217)。

## 1. 总体验收标准

- [ ] `/query`、`/training-calendar`、`GET /plans/{plan_id}`、反馈调整版计划都返回统一 `evidence_chain` 或兼容字段，前端不需要自己猜来源。
- [ ] 每个用户可点击引用都能定位到 `source_registry_id/source_url/page_or_section/chunk_id/text_span`，否则不显示 citation badge。
- [ ] `model_general_knowledge` 可以回答普通问题，但永远不能伪装成引用，也不能写入核心处方字段。
- [ ] 核心处方字段只允许 `protocol/action_library` 且 `prescription_permission=can_write_core`；legacy runtime、seed、candidate、reviewed-but-not-approved 都不能写核心字段。
- [ ] Graph-only evidence 只能作为“关联线索”，没有可定位 source anchor 时不能显示为 verified source。
- [ ] 普通用户层不暴露 `source_path/local_path/retrieval_score/internal ids`；专家层必须能看到完整审计链。
- [ ] RAG vs base LLM 评估能输出至少 `retrieval_coverage/citation_faithfulness/core_permission_compliance/medical_safety/load_truthfulness/user_actionability`。
- [ ] 任何 fake citation、source path leak、core permission violation、medical red flag override 都阻塞 commercial release gate。

## 2. 分支与协作规则

- [ ] 每个 P 独立分支，命名：`codex/rag-evidence-pN-<slug>`。
- [ ] 禁止 `git add .`，只 stage 当前 P 涉及文件。
- [ ] 不提交 `data/vector_kb/default/user_profile.json`、`data/vector_kb/default/knowledge_graph.json`、`apps/artifacts/`、`artifacts/`、截图、临时缓存。
- [ ] 本轮最多 1 个子 agent；本 TODO 设计阶段没有开启子 agent。
- [ ] 任何改动影响前端 EvidenceDrawer、API response model、OpenAPI、runtime health 或 release gate 时，必须同步更新 `docs/quality/shared_delivery_contract.md`。

## P0: Evidence Chain Map And Contract Inventory

### 目标

把当前所有证据入口、传递字段、前端展示点列成一张链路表，避免继续靠散落字段维护引用。

### TODO

- [x] 梳理 backend chain：`get_context -> retrieve -> build_rag_sources -> build_ranked_evidence -> build_evidence_bundle -> _build_structured_report -> QueryResponse`。
- [x] 梳理 plan chain：`build_structured_training_plan_skeleton -> generate_daily_schedule -> field_sources/kb_metadata/action_match -> training_plan_review`。
- [x] 梳理 graph chain：`infer_entities -> graph_engine.search_graph -> map_edge_to_evidence -> graph_binding_to_legacy_evidence -> ranked_evidence`。
- [x] 梳理 frontend chain：`renderEvidencePreview -> collectEvidenceItems -> buildDayEvidenceItems -> openEvidenceDrawer -> renderEvidenceDrawerItem`。
- [x] 输出 `docs/knowledge_base/reports/evidence_chain_inventory.md`，列出每个字段的 owner、可见层级、是否允许普通层展示、是否可写核心处方。
- [x] 给每条证据状态定义唯一枚举：`verified_source/model_general_knowledge/needs_evidence/graph_hint/legacy_explanation/rejected_source`。

### 验收标准

- [x] 文档能一眼看出 `rag_sources`、`ranked_evidence`、`evidence_bundle`、`evidence_base`、`field_sources` 的关系。
- [x] 任何新增证据字段必须能在 inventory 中找到 owner。
- [x] 前端 owner 能按文档判断哪些字段普通层可见，哪些只给专家层。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_evidence_binding.py tests/test_openapi_contract.py -q
```

实际结果：`tests/test_kb_evidence_binding.py tests/test_openapi_contract.py -q` 通过；`git diff --check -- docs/knowledge_base/reports/evidence_chain_inventory.md docs/knowledge_base/rag_evidence_chain_refactor_todo.md` 通过。

## P1: Canonical Evidence DTO

### 目标

建立唯一后端证据 DTO，统一 QA、日卡、计划评审、GraphRAG、模型常识兜底，不再让前端现场拼“证据项”。

### TODO

- [ ] 新增 `EvidenceChainItem` schema，字段包含 `evidence_id`、`display_mode`、`source_label`、`source_registry_id`、`source_url`、`page`、`section`、`chunk_id`、`text_span`、`evidence_domain`、`knowledge_layer`、`allowed_use`、`prescription_permission`、`retrieval_mode`、`quality_tier`、`review_status`、`field_binding`、`user_facing_summary`、`expert_metadata`。
- [ ] 新增 `EvidenceChainPayload` schema，字段包含 `items`、`answer_source_mode`、`runtime_index_schema_version`、`runtime_core_prescription_enabled`、`fake_citation_violations`、`core_permission_violations`、`source_path_leak_count`。
- [ ] 保留旧 `evidence_bundle/evidence_base` 兼容字段，但由 canonical DTO 投影生成。
- [ ] `model_general_knowledge` 项必须没有 `source_url/page/chunk_id`，且 `display_mode=model_general_knowledge`。
- [ ] `needs_evidence` 项必须说明缺失原因，不可带 citation label。

### 验收标准

- [ ] `/evidence-tier-reference` 暴露 canonical DTO 字段与 display mode。
- [ ] `QueryResponse`、`TrainingCalendarResponse`、`PlanDetailResponse` 至少有兼容字段能映射到 canonical DTO。
- [ ] 旧前端不崩，新前端可以只读 canonical DTO 渲染证据抽屉。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_openapi_contract.py tests/test_api_app.py -q
```

## P2: Retrieval Metadata Preservation

### 目标

确保 vector hit 从 FAISS 回来到最终 response 全程保留 v2 metadata；legacy hit 明确降级。

### TODO

- [ ] 修改 `build_rag_sources()`，保留 `source_registry_id/source_url/local_path/section/evidence_domain/knowledge_layer/domain_pack/allowed_use/prescription_permission/quality_tier/review_status/needs_review`。
- [ ] 修改 `build_ranked_evidence()`，vector evidence 不再只保留 legacy 字段。
- [ ] `_merge_ranked_hits()` 合并时保留最完整 metadata，不因 score 更新丢失字段。
- [ ] 对 legacy hit 自动补 `evidence_domain=sports_science_reference`、`prescription_permission=explanation_only`、`display_mode=legacy_explanation`。
- [ ] 如果 `source_url/page/section` 不完整，则 `verified_source=false`。
- [ ] 增加对 v2 metadata round-trip 的测试。

### 验收标准

- [ ] v2 hit 进入 `rag_sources`、`ranked_evidence`、`evidence_bundle` 后 metadata 不丢。
- [ ] legacy hit 不会被标成 `can_write_core`。
- [ ] 合并多 query variant 的 hit 时不会丢 `source_registry_id`。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_vector_store_query_fusion.py tests/test_kb_evidence_binding.py tests/test_working_state_audit_loop.py -q
```

## P3: No Fake Citation Gate

### 目标

把“没有真实来源就不显示引用”从前端约定提升为后端 gate。

### TODO

- [ ] 新增 `validate_citation_faithfulness(answer_text, evidence_chain)`。
- [ ] 检查 Markdown 中 `[1]`、`[2]` 等引用是否存在于 evidence item。
- [ ] 检查每个可点击 citation 是否有 `source_url` 且有 `page` 或 `section`。
- [ ] 如果回答引用了 `model_general_knowledge`，直接标为 fake citation violation。
- [ ] 如果回答引用了 legacy explanation-only source，允许在专家层显示背景来源，但普通层不显示 citation badge。
- [ ] gate 结果写入 `workflow_trace.evidence_state` 和 `training_plan_review.dimensions.evidence_control`。

### 验收标准

- [ ] `answer [99]` 必须被 auditor 拦截。
- [ ] 无 `source_url/page/section` 的 source 不生成 citation badge。
- [ ] fake citation count > 0 时 commercial gate fail。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_working_state_audit_loop.py tests/test_kb_governance.py -q
```

## P4: Answer Source Mode Contract

### 目标

固化普通问答、计划生成、模型常识、医疗阻断和证据不足之间的状态，不再只靠 Markdown 标题表达。

### TODO

- [ ] 在 `/query` response 中新增或稳定返回 `answer_source_mode`：`verified_rag/model_general_knowledge/needs_evidence/medical_referral/structured_plan_rule`。
- [ ] 普通 QA 无本地证据时必须走 `model_general_knowledge`，不显示“信息不足，请补充上下文”。
- [ ] 核心训练处方缺 `protocol/action_library` 时必须走 `needs_evidence`，不能由 LLM 常识写主课。
- [ ] 医疗红旗走 `medical_referral`，不继续生成训练负荷调整。
- [ ] `answer_source_mode` 同步写入 `workflow_trace` 和前端 EvidenceDrawer 摘要。

### 验收标准

- [ ] 普通知识问答无证据时仍有可执行回答，但没有 citation。
- [ ] 计划主课缺证据时显示“待补证据”，不是通用回答。
- [ ] 医疗红旗不会被 `model_general_knowledge` 覆盖。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_api_app.py tests/test_state_models.py -q
```

## P5: Runtime Health Gates Evidence Display

### 目标

让 runtime health 真正影响证据展示和核心处方权限，而不是只在 `/health` 里报告。

### TODO

- [ ] `/query` response 携带 `rag_health.index_schema_version`、`metadata_completeness`、`runtime_core_prescription_enabled`。
- [ ] 当 runtime 是 `legacy` 或 `mixed` 时，所有 vector KB 命中最多为 `legacy_explanation`。
- [ ] 当 `runtime_core_prescription_enabled=false` 时，后端不允许把 vector hit 绑定到核心字段。
- [ ] `training_plan_review` 增加 `runtime_kb_boundary` 维度。
- [ ] 前端普通层显示“当前依据可解释但不可写核心处方”的人话状态。

### 验收标准

- [ ] 当前 legacy runtime 下不会出现 `verified_core_prescription_source`。
- [ ] `/health` 与 `/query` 中 runtime 状态一致。
- [ ] runtime 切 v2 前，核心处方仍只来自协议和动作库。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_health.py tests/test_vector_kb_runtime_contract.py tests/test_training_plan_review.py -q
```

## P6: Daily Card Evidence Binding Unification

### 目标

日卡主课来源、动作库匹配、日卡 EvidenceDrawer 和 QA 证据链使用同一套证据 DTO。

### TODO

- [ ] `generate_daily_schedule()` 输出 `evidence_chain_items` 或 `evidence_refs`，引用 canonical DTO。
- [ ] `field_sources.main_set` 必须能映射到一个 `EvidenceChainItem` 或一个明确 `needs_evidence` item。
- [ ] `action_match` 中的 source/page/action_id 不再由前端临时拼证据项。
- [ ] `kb_fallback.blocked_core_candidates` 不进入用户可见主课。
- [ ] 日卡 `needs_evidence` 时仍可显示模型常识说明，但必须标为非处方证据。

### 验收标准

- [ ] 每张非休息日卡都有 `field_sources` 和可审计 evidence state。
- [ ] `main_set` 为 action_library 时能找到对应 evidence item。
- [ ] `needs_evidence` 日卡不展示可执行主课模板。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_daily_schedule_generator.py tests/test_workout_template_retriever.py -q
```

## P7: GraphRAG Traceability Boundary

### 目标

图谱可以帮助排序和解释，但不能凭空制造引用或核心处方来源。

### TODO

- [ ] `graph_engine.map_edge_to_evidence()` 必须返回可定位 source anchor，否则标 `display_mode=graph_hint`。
- [ ] Graph-only hit 没有 `chunk_id/source_url/page/section` 时不生成 citation label。
- [ ] Fusion hit 只有在 vector side 有 verified anchor 时才显示 verified citation。
- [ ] Graph relation、source node、target node 只进入专家层。
- [ ] Graph edge 文本需要经过 prompt injection scan。

### 验收标准

- [ ] graph-only evidence 不会出现在普通层 citation badge。
- [ ] fusion evidence 的 citation 指向 vector source，而不是图谱关系本身。
- [ ] graph evidence 不能让 `sports_science_reference` 获得 `can_write_core`。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_graph_evidence.py tests/test_high_risk_contracts.py -q
```

## P8: EvidenceDrawer API And Frontend Contract

### 目标

前端证据抽屉只渲染后端 canonical payload，不再自己制造来源。

### TODO

- [ ] 后端 `/evidence-tier-reference` 增加 canonical examples：`verified_source`、`model_general_knowledge`、`needs_evidence`、`graph_hint`、`legacy_explanation`。
- [ ] 前端 `collectEvidenceItems()` 优先读取 canonical `evidence_chain.items`。
- [ ] 前端禁止把 `source_path/local_path` 展示给普通用户。
- [ ] 前端 `buildDayEvidenceItems()` 不再用 `动作库.pdf` 作为默认来源占位。
- [ ] 前端普通层只展示 `source_label/page_or_section/user_facing_summary/display_mode`。
- [ ] 专家层才展示 `source_registry_id/retrieval_mode/score/prescription_permission`。

### 验收标准

- [ ] 无真实来源时前端显示“模型常识说明”或“待补证据”，没有假 citation。
- [ ] 当前 legacy runtime 下 EvidenceDrawer 不显示“已验证处方来源”。
- [ ] 点击日卡依据和点击 QA 引用打开的是同一套 evidence item。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_astro_frontend_contract.py tests/test_openapi_contract.py -q
cd apps/web
npm run build
```

## P9: Source Review State In Runtime Answers

### 目标

`seed_only/candidate/reviewed/approved/blocked` 状态必须能影响回答与展示。

### TODO

- [ ] `source_registry_id` 进入 runtime hit 后，能反查 source review status。
- [ ] `seed_only` 和 `candidate` 永远不能显示为 verified source。
- [ ] `approved` 但 metadata 不完整时仍不能显示为 verified citation。
- [ ] `blocked` source 不进入 retrieval context；如果历史缓存命中必须过滤。
- [ ] release report 暴露 `answer_blocked_by_source_review_count`。

### 验收标准

- [ ] 当前 `approved_records=0` 状态下没有任何 KB source 被称为已审核权威证据。
- [ ] seed/candidate 命中可以作为内部召回诊断，但普通层只能看到“待审核来源”或不显示。
- [ ] blocked/quarantine source 不进入 evidence chain。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_source_review.py tests/test_kb_runtime_quarantine.py tests/test_kb_governance.py -q
```

## P10: RAG Evaluation Runner V2

### 目标

让“RAG 比裸 LLM 更权威”成为可跑出来的评估结论，而不是产品宣称。

### TODO

- [ ] 使用 `kb_golden_questions_v2.json` 作为 evaluation source。
- [ ] 对每题跑 `rag_answer` 和 `base_llm_answer`。
- [ ] 评估维度至少包含 `retrieval_coverage`、`citation_faithfulness`、`core_permission_compliance`、`medical_safety`、`load_truthfulness`、`user_actionability`。
- [ ] 输出 JSONL 明细和 Markdown summary。
- [ ] 如果本地 approved source 为 0，RAG 不能被判为商业优势，只能判为治理链路 ready 或 not ready。
- [ ] 加入最小离线 mock judge，避免 CI 依赖外部 LLM。

### 验收标准

- [ ] 110 条 golden questions 能全部被加载和判分。
- [ ] fake citation、核心权限越权、医疗红旗失败会单独计数。
- [ ] 报告中能区分“裸 LLM 答得更丰富”和“RAG 答得更可信”。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_evaluation.py tests/test_training_plan_review.py -q
```

## P11: Prompt Injection And Retrieved Content Safety

### 目标

把检索内容当作不可信输入处理，防止 KB 内容诱导模型泄露、越权或忽略系统边界。

### TODO

- [ ] 对 vector hit、graph text_span、source excerpt 统一执行 `InputGuard.check(input_type="rag")`。
- [ ] 被清洗内容不进入 citation excerpt，只显示安全拦截摘要。
- [ ] 检测 “ignore previous instructions”、“system prompt”、“API key”、“local path”等注入模式。
- [ ] 不把 retrieved content 中的用户画像推测写回 profile。
- [ ] 输出 `rag_input_guard_violations` metrics。

### 验收标准

- [ ] 注入性 chunk 不会进入 LLM prompt 原文。
- [ ] 被拦截 hit 不显示为 verified source。
- [ ] metrics 能看到拦截数量和原因，不记录敏感原文。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_security_guards.py tests/test_working_state_audit_loop.py -q
```

## P12: Evidence Observability And Ops Metrics

### 目标

让证据链质量可观测：不是出问题后翻日志，而是每次请求都有结构化状态。

### TODO

- [ ] 在 `/ops/metrics` 增加 `evidence_display_mode_counts`。
- [ ] 增加 `fake_citation_violation_count`、`core_permission_violation_count`、`source_path_leak_count`。
- [ ] 增加 `runtime_index_schema_version_counts` 和 `answer_source_mode_counts`。
- [ ] 记录 request-level `evidence_chain_status`，但不记录用户原始 query 或 prompt。
- [ ] 给 `/query` 每次 response 加 `request_id` 并在 workflow trace 中保留。

### 验收标准

- [ ] ops metrics 可以回答“过去请求中多少是模型常识、多少是真证据、多少待补证据”。
- [ ] metrics 不泄露 query、API key、本地绝对路径。
- [ ] evidence gate fail 能被计数。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_openapi_contract.py tests/test_security_guards.py tests/test_api_app.py -q
```

## P13: Runtime V2 Preview To Production Cutover Gate

### 目标

未来接入 v2 runtime 前建立切换门槛，避免把 seed/candidate 或未审核 PDF 直接塞进生产检索。

### TODO

- [ ] 构建独立 `data/vector_kb/v2_preview`，不覆盖 default runtime。
- [ ] v2 preview 必须 `metadata_completeness=1.0`。
- [ ] v2 preview 中 `can_write_core` 只允许 `protocol/action_library` 且 `review_status=approved`。
- [ ] 切换前跑 golden questions v2、fake citation gate、medical safety gate、load truthfulness gate。
- [ ] 切换 manifest 必须记录 source count、chunk count、blocked source count、eval delta、rollback path。
- [ ] default runtime 切换必须是显式配置，不允许脚本默认覆盖。

### 验收标准

- [ ] `runtime_index_v2_manifest.can_replace_runtime=true` 前不能替换 default。
- [ ] v2 preview 失败不会污染 legacy fallback。
- [ ] rollback 可以恢复上一版 runtime。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_vector_kb_runtime_contract.py tests/test_kb_health.py tests/test_kb_governance.py -q
```

## P14: Commercial Evidence Release Gate

### 目标

建立最终商用证据链门禁，保证没有值得修的证据链问题时才签收。

### TODO

- [ ] 整合 P0-P13 gate，输出 `commercial_evidence_chain_gate_report.json` 和 Markdown report。
- [ ] gate 必须包含 local facts、source readiness、runtime schema、fake citation、core permission、medical safety、load truthfulness、frontend display contract、ops metrics。
- [ ] Backend owner、Frontend owner、QA/reviewer、Version owner 分别签收。
- [ ] 任意 P0/P1 未完成、approved source 为 0、runtime v2 未 ready、fake citation > 0、核心权限越权 > 0、医疗红旗失败 > 0，都不能签收商用证据链。
- [ ] 共享契约 `docs/quality/shared_delivery_contract.md` 必须同步当前状态。

### 验收标准

- [ ] 全量后端测试通过。
- [ ] 前端 build 与 evidence contract 测试通过。
- [ ] `commercial_evidence_chain_gate_report.json` 明确写出 `commercial_ready=true/false` 和阻塞项。
- [ ] 共享契约中没有未解决的 P0/P1 证据链冲突。

### 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest -q
cd apps/web
npm run build
```

## 3. 前端共同契约新增要求

- 前端 EvidenceDrawer 下一轮必须优先消费 canonical `evidence_chain.items`。
- 普通层不得展示 `source_path/local_path/retrieval_score/internal source_registry_id`。
- 无真实 `source_url + page/section` 时不得显示 citation badge。
- `model_general_knowledge` 必须显示为“模型常识说明”，不能显示为“权威来源”。
- `needs_evidence` 必须显示为“待补证据”，不能显示为“已生成训练安排”。
- `graph_hint` 必须显示为“关联线索”，不能显示为“引用来源”。
- 当前 runtime 为 legacy 时，普通层不得出现“已审核知识库证据”“已验证处方来源”等文案。
- 日卡主课依据必须来自后端 `field_sources` 或 canonical evidence item，不得由前端硬编码 `动作库.pdf` 补来源。

## 4. 执行顺序建议

1. 先做 P0-P2，统一字段和 metadata 保真。
2. 再做 P3-P5，堵住假引用、状态误判和 runtime 权限。
3. 然后做 P6-P9，统一日卡、GraphRAG、EvidenceDrawer 和 source review。
4. 接着做 P10-P12，补评估和可观测性。
5. 最后做 P13-P14，准备 v2 runtime 切换和商用门禁。
