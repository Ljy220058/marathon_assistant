# 马拉松助手技术需求文档 v3

> 版本：v3.0
> 日期：2026-06-12
> 范围：Marathon Agent / 受控训练计划生成器
> 基准：当前代码真实链路 + `marathon_agent_requirements_v2.md`

## 1. 定位与边界

本系统不是开放式聊天教练，而是受控训练计划生成器。它以跑者画像、结构化训练计划、动作库、HMP 基石协议、本地 KB/RAG 和审计链路为核心，生成可追踪、可审查、可回退的训练建议。

v3 替代旧 `TECH_REQUIREMENTS_V2.md`。旧文档中保留的长篇变更日志、过时旧前端入口、直接 Wiki 补充、未区分当前实现与目标设计的内容不再作为主技术需求来源。

硬边界：

- 核心训练处方优先来自本地 KB/RAG、协议规则、动作库和确定性约束。
- 外部资料只能作为候选来源，必须审查入库后才可参与正式检索和生成。
- `llm_general_knowledge` 只能用于说明层，不能写入核心处方、风险规则、`risk_level`、引用编号或证据链。
- 医疗红旗与高风险训练反馈必须 fail-closed，不允许继续生成加量或高强度建议。
- 所有关键输出必须保留证据来源、约束来源、审计结论和版本关系。

## 2. 当前真实工作流

当前 LangGraph 主链位于 `apps/backend/src/marathon_qa_assistant/core/workflow_graph.py`，状态模型为 `IntegratedState`。

主链节点：

```text
security_gate
-> router
-> context_fanout (profiler ∥ entity_extraction)
-> evidence_retriever
-> conditioning_constraints
-> supervisor
-> planner | coach | adaptive_coach | missing_info_handler
-> executor -> nutritionist -> psychologist
-> rule_checker
-> critic_auditor
-> safety_out
-> formatter
-> guided_questions_generator
```

说明：

- `router` 产出 `workflow_kind`：`plan / research / adaptive / profile_update / qa`，同时产出 `intent_labels` 列表和 `intent_priority` 主意图，并产出专家类别 `coach / nutritionist / therapist / research`。
- 混合意图必须保留多标签，例如计划 + 疼痛/疲劳反馈时要同时出现 `training_plan` 与 `adaptive_adjustment`，并优先进入 `adaptive` 链路。
- `profile_update` 不再作为 router 的独立主分支；画像更新由 `profiler` 作为每轮画像同步副作用承接，确认更新后可直接进入 `formatter`，非更新问题继续主链。独立图节点已删除。
- `context_fanout` 是 Layer 2 的并行收敛节点；它内部并行运行 `profiler` 与 `entity_extraction`，再把合并后的状态交给 `evidence_retriever`。
- `entity_extraction` 只做实体抽取和检索准备。
- `evidence_retriever` 是正式命名的证据检索节点；当前实现为本地 KB/RAG 优先，执行意图域过滤、专家域过滤、KG 融合、证据排序和 `evidence_bundle` 构建，返回空 `wiki_context` 作为旧字段兼容，明确不启用外部知识。
- `wiki_search_node` 已删除，不得作为新链路命名或优先外部检索入口。
- `conditioning_constraints` 是 `evidence_retriever` 之后的常驻容量边界节点；它先把 S&C 约束整理好，再决定回 `supervisor` 还是直接把 adaptive 重排请求送回 `planner`。
- `supervisor` 是约束收敛后和审计失败后的集中调度节点；当前图内正式分流目标是 `planner / coach / adaptive_coach / missing_info_handler`，避免把旧兼容节点误当成 supervisor 直连目标。
- 研究型训练问答由 `coach` 承接；独立 `research_analyst_node` 已删除，不再是主链调度目标。
- `conditioning_constraints` 是确定性 S&C 约束节点，不是自由 LLM 体能师。
- `rule_checker` 是 `critic_auditor` 前置硬规则门，独立检查引用、证据路径、协议、S&C 容量、治疗师前置和用户显式约束。
- `safety_out` 是审计后、格式化前的显式输出安全层；`formatter` 还有二道输出清洗。

## 3. KB/RAG 优先与外部资料准入

正式命名：

- 新文档和代码讨论统一使用 `evidence_retriever`。
- 不再把 `wiki_search` 作为业务节点名，也不保留 legacy alias。
- “外部概念补充”不是处方证据，默认关闭。

资料准入流程：

```text
外部资料候选
-> source_registry 归档
-> 元数据规范化
-> 人工/规则审查
-> 分片与 schema 校验
-> 向量索引与知识图谱重建
-> runtime health 通过
-> RAG 可检索
```

核心字段：

- `source_registry_id`
- `evidence_domain`
- `knowledge_layer`
- `domain_pack`
- `allowed_use`
- `prescription_permission`
- `review_status`
- `needs_review`
- `source_path / source_url / content_hash`

准入规则：

- 只有 `review_status=approved`、`needs_review=false` 且 `validate_source_registry_v2()` 通过的来源可视为 ready。
- `prescription_permission=can_write_core` 仅允许 `protocol` 和 `action_library` 等可控域写入核心处方。
- `explanation_only` 只可用于解释、背景和引用说明。
- `blocked_needs_evidence` 必须保持可见失败，不得被 LLM 文案填平。

## 4. 证据包与专家证据溯源

统一证据包由 `core/evidence_bundle.py` 构建，输出 `evidence_bundle.evidence_items[]`。每条证据必须尽量保留：

- `citation_label`
- `tier`
- `evidence_tier`
- `source_file`
- `source_path`
- `page`
- `chunk_id`
- `text / snippet`
- `trace`
- `allowed_use`
- `prescription_permission`
- `review_status`

专家节点和计划链路关键角色必须维护 `expert_evidence_trace`：

- `conditioning_constraints`
- `planner`
- `executor`
- `coach`
- `adaptive_coach`
- `nutritionist`
- `psychologist`
- `therapist`

其中 `planner` / `executor` 是计划生成链路角色，不是新增领域专家；它们必须记录本轮拆解和生成所消费的 `evidence_bundle` / S&C 约束来源。角色证据项应尽量保留 `citation_label`、`source_file`、`source_path`、`page`、`chunk_id`、`evidence_domain`、`retrieval_mode` 和 `why_retrieved`，用于审计链路回放。

专家证据状态：

- `verified`：该专家节点可见到角色相关 KB 证据。
- `needs_evidence`：未找到角色相关证据，输出必须标注边界。

引用规则：

- 使用本地知识库事实时只允许 `[1]`、`[2]` 这类纯数字编号。
- 不能编造 `[n]`，不能引用不存在编号。
- 图谱 hint、模型通用知识、legacy explanation 只能作为背景，不可作为核心处方依据。

## 5. S&C 约束节点

`conditioning_constraints` 是训练容量边界节点，调用 `build_training_capacity_envelope()`。

输入：

- `user_profile`
- `query`
- `ranked_evidence`
- `medical_constraints`
- `structured_training_plan`

输出：

- `training_capacity_envelope`
- `s_and_c_constraints`
- `s_and_c_done`
- `needs_therapist_review`

核心 envelope：

```text
training_capacity_envelope.schema_version = training_capacity_envelope.v1
source_role = s_and_c
load_ceiling.weekly_load_cap_km
load_ceiling.weekly_load_floor_km
load_ceiling.max_long_run_km
load_ceiling.quality_sessions_max
load_ceiling.progression_multiplier
strength_rules.max_strength_sessions_per_week
strength_rules.heavy_lower_body_spacing_hours
recovery_windows.post_long_run_hours
recovery_windows.post_quality_hours
capacity_risk_flags[]
```

S&C 边界：

- S&C 只约束正常训练容量。
- 疼痛、伤病和医疗红旗属于 therapist / risk gate 权限。
- 若出现 `requires_therapist_review`，路由必须进入 therapist 或审计层，不得直接放行。
- planner、executor、critic_auditor 都必须消费 `load_ceiling`。

## 6. Adaptive 五类路由

自适应调整由 `adaptive_coach` 识别反馈，再通过条件边路由：

| adaptation_type | 典型触发 | 路由 |
|---|---|---|
| `INJURY` | 疼痛、伤病、无法承重、跟腱/膝/足底风险 | `adaptive_coach -> therapist -> conditioning_constraints -> planner` |
| `FATIGUE` | 高疲劳、睡眠差、RPE 异常、恢复不足 | `adaptive_coach -> therapist -> conditioning_constraints -> planner` |
| `MISSED` | 漏训、未完成、跳过关键课 | `adaptive_coach -> conditioning_constraints -> planner` |
| `SCHEDULE` | 出差、时间变化、训练日调整 | `adaptive_coach -> conditioning_constraints -> planner` |
| `PERFORMANCE` | 成绩变化、配速达不到、表现退步/进步 | `adaptive_coach -> conditioning_constraints -> planner` |

未知自适应信号保守处理：先 therapist，再 S&C。

`adaptive_coach` 不直接生成最终计划，只生成：

- `adaptive_feedback`
- `adaptive_adjustment`
- `adaptation_type`
- `adaptation_context`

最终计划仍必须走 `planner -> executor -> audit -> safety_out -> formatter`。

## 7. 计划生成与日卡证据

计划链路：

- `planner` 拆解子任务，不直接生成完整课表。
- `executor` 调用 `build_structured_training_plan_skeleton()` 生成结构化训练计划骨架，并调用 LLM 生成文本计划。
- `formatter` 把 `structured_training_plan` 投影为 `training_plan_overview`、`phase_summary`、`training_plan_weeks`、`monthly_training_calendar`、`daily_schedule_cards`。

结构化计划必须优先承载：

- `plan_meta`
- `phase_summary`
- `week_plans[]`
- `repeat_guard_signature`
- `training_capacity_envelope`
- `half_marathon_protocol`
- `half_marathon_protocol_validation`
- `weekly_structure_constraints`
- `weekly_structure_validation`

每日训练卡必须逐步稳定以下审计字段：

- `field_sources`
- `protocol_check`
- `action_match`
- `kb_fallback`
- `risk_gate`
- `trace / workflow_trace`

证据优先级：

1. `protocol_rule`：HMP 基石协议、容量预算、阶段和安全边界。
2. `action_library`：用户可见主课、动作执行内容、热身/冷身/替代项。
3. `kb_fallback`：解释、术语、恢复建议等非核心字段。
4. `needs_evidence`：动作库和 KB 都不能支撑时的可见缺证状态。
5. `llm_general_knowledge`：仅一般说明，不参与处方字段。

## 8. 安全与审计

输入安全：

- `security_gate` 先做 prompt injection / 越权检查。
- 再做医疗红旗扫描：胸痛、呼吸困难、晕厥、骨折/应力性骨折、跟腱断裂、横纹肌溶解、中暑迹象等。
- 严重红旗直接 `mode=intercepted`，输出就医建议，不进入计划生成。

反馈风险门：

- `/feedback` 必须先输出 `risk_gate`。
- 再输出 `protocol_recheck`。
- 最后才给 `adaptive_adjustment` 和可选 `plan_diff`。
- `medical_referral` 状态不得包含继续训练、高强度替代或加量建议。

审计：

- `critic_auditor` 检查引用编号、`source_path`、HMP 验证、S&C 容量、用户合同和治疗师审查。
- 审计不追求“最优训练方案”主观评分，只处理可证实问题。
- 达到重试上限时可以强制放行，但必须标注剩余风险并继续经过 `safety_out`。

输出安全：

- `safety_out` 扫描执行轨迹和待输出文本。
- `formatter` 再执行 `output_guard_obj.check()`。
- 风险内容必须进入 `risk_alert` 或结构化报告，不得静默吞掉。

## 9. 版本化、回退与历史

训练计划持久化在 `training_plans`，日历事件在 `training_calendar_events`，反馈在 `training_event_feedback`。

版本字段：

- `lineage_id`
- `version`
- `parent_plan_id`
- `parent_version`
- `trigger`
- `trigger_detail`

回退规则：

- `rollback_training_plan(plan_id, to_version)` 不覆盖旧版本。
- 回退会复制目标版本结构化计划，并创建新版本。
- 新版本 `trigger=manual_rollback`，`parent_plan_id` 指向被回退版本。
- 后续调整必须基于新版本继续生成，不得改写历史版本。

反馈历史：

- `training_event_feedback` 必须保存 `adaptive_reason_codes`、`risk_gate_json`、`protocol_recheck_json`。
- `training_event_exceptions` 记录反馈对后续训练日的影响。
- `AdjustmentHistory` 应从持久化反馈和 exception 水合，而不是从 Markdown 推断。

## 10. 状态与可观测性

必须保留：

- `node_visit_count`
- `execution_trace`
- `workflow_trace`
- `audit_diagnosis`
- `evidence_bundle.health`
- `workflow_pause`
- `used_fallback / fallback_reason`
- `audit_scores`
- `risk_alert`

熔断：

- 单节点访问上限由 `CIRCUIT_BREAKER_CONFIG.max_node_visits` 控制。
- 总节点访问上限为 `max_total_node_visits`。
- LLM 节点默认 120 秒 timeout，最多 2 次重试。

前端展示不得把 `planned_load_proxy` 表述为真实生理负荷。若使用前端估算，必须标记为估算口径。

## 11. 验收标准

功能验收：

- 计划请求在画像缺失时进入 `missing_info_handler`，不生成伪处方。
- `missing_info_handler` 必须写出 `missing_info_status=awaiting_profile` 和 `workflow_pause.resume_target=router`；用户补齐后恢复原始请求，从 router 重新进入全链路，而不是把补充信息直接 formatter 输出。
- 计划请求有足够画像时生成结构化多周计划，并带 `daily_schedule_cards`。
- HMP 半马计划通过协议验证，主课不泄漏内部 `hm_*` ID。
- 动作库命中课型时，用户可见 `main_set` 来自动作库。
- 自适应五类反馈按表路由，疼痛/疲劳优先 therapist。
- 输出包含 `expert_evidence_trace` 和可点击证据基础。
- 无证据时保持 `needs_evidence` 或 `llm_general_knowledge` 边界。
- 计划版本可列出、回退，并创建新版本。

建议回归命令：

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_plan_workflow_expectations.py -q
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_kb_source_registry.py tests/test_kb_evidence_binding.py tests/test_evidence_chain_contract.py -q
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_api_app.py tests/test_router_behavior.py tests/test_security_guards.py -q
```

## 12. 迁移要求

- 新文档路径：`docs/architecture/marathon_agent_technical_requirements_v3.md`。
- 旧 `docs/architecture/TECH_REQUIREMENTS_V2.md` 不再保留。
- 文档、计划和 backlog 中的技术需求引用应迁移到 v3。
- 若脚本、测试样例或数据产物仍硬编码旧路径，主线程需单独处理，避免文档迁移误改代码或生成数据。

## 13. workflow_pause 恢复合同

当前实现采用 API 级恢复合同，而不是 LangGraph checkpoint 级 `interrupt/resume`。

- `missing_info_handler` 在计划画像不足时返回 `workflow_pause.status=awaiting_user_input`、`workflow_pause.resume_target=router` 和 `workflow_pause.pending_query`。
- 客户端补齐信息后，再次调用 `/query`，把上一轮 `workflow_pause` 原样放入 `resume_from_workflow_pause`。
- `/query` 入口以 `resume_from_workflow_pause.pending_query` 作为有效原始请求重新构造 `WorkingState`，从 `router` 重新进入全链路。
- 本轮 `query` 文本仍会参与画像字段解析，用来补齐 `weekly_mileage`、`available_days` 等缺失画像，但不会替代原始请求成为新的业务意图。
- 若没有合法 `resume_from_workflow_pause.status=awaiting_user_input` 或没有 `pending_query`，`/query` 按普通请求处理。

## 14. KB 现状约束

> 本节记录知识库当前已知边界、许可权限语义和运行时限制。工程师在修改 KB 构建脚本、添加 domain pack 或修改检索逻辑前，必须先阅读本节。

### 14.1 双库架构

系统运行两套向量库，启动时由 `kb_bootstrap.py` 按以下优先级选择：

| 库 | 路径 | 状态 | 激活条件 |
|----|------|------|----------|
| **v2_sharded**（主库） | `data/vector_kb/v2_sharded/` | 商业就绪 | `sharded_retrieval_enabled=True`（默认） |
| **v2**（兜底库） | `data/vector_kb/v2/` | 元数据完整，FAISS 有 4-向量缺口 | `sharded_base` 不存在或设置关闭时 |

**任何时候不得把 v2 当成主库使用。** v2 的 `runtime_core_prescription_enabled=false`，所有 chunk 的 `prescription_permission` 均为 `explanation_only`，不支持处方级输出。

### 14.2 v2_sharded 分片现状

| Domain Pack | 路径 | Chunk 数 | 商业就绪 |
|-------------|------|---------|--------|
| training_protocol | `v2_sharded/training_protocol/` | 6 007 | ✅ |
| nutrition | `v2_sharded/nutrition/` | 4 757 | ✅ |
| injury_safety | `v2_sharded/injury_safety/` | 3 698 | ✅ |
| medical_safety | `v2_sharded/medical_safety/` | 690 | ✅ |
| sport_psychology | `v2_sharded/sport_psychology/` | 501 | ✅ |

总计 15 653 chunks。`shard_meta.json` 中 `commercial_release_status: "ready"`。

### 14.3 chunk_schema_v2 必填字段

所有 chunk 必须包含以下 15 个字段（来源：`services/kb/health.py::CHUNK_SCHEMA_V2_REQUIRED_FIELDS`）：

```
chunk_id, source_registry_id, source_file, source_url, local_path,
page, section, text, language, evidence_domain, knowledge_layer,
domain_pack, allowed_use, prescription_permission, quality_tier
```

字段缺失（包括空字符串 `""`）或 `page==0` 均被 `health.py::_missing_fields` 视为缺失，导致 `metadata_completeness` 下降。

### 14.4 prescription_permission 语义与安全规则

`prescription_permission` 有三个合法值：

| 值 | 含义 | 安全规则 |
|----|------|---------|
| `can_write_core` | 可用于生成处方级建议 | **仅允许**以下 quality_tier：`systematic_review_meta_analysis`、`randomized_controlled_trial`、`clinical_practice_guideline`、`consensus_or_position_statement` |
| `explanation_only` | 只能作为解释性内容，不能直接生成处方 | — |
| `referral_and_flag_only` | 仅用于标记和转介绍，不能生成任何建议 | — |

**禁止规则**：`expert_review_narrative`（叙述性综述，未经同行评审）和 `practitioner_coach_material`（教练实操材料）这两类 quality_tier 的 chunk 必须是 `explanation_only`，**不得设为 `can_write_core`**。  
违反此规则会导致 `health.py::probe_vector_kb_health` 的商业就绪检查失败（`no_unsafe_can_write_core` 为 False）。

### 14.5 FAISS 重建要求

以下情况需要运行 `bash tools/kb/rebuild_faiss.sh <dir>` 重建 FAISS 索引：

1. **v2 兜底库**：FAISS 存在 4-向量缺口（`faiss_gap_count=4`），原因是 bge-m3 嵌入时出现 NaN/Inf 验证失败。受影响的 4 个 chunk 仅可通过 BM25 兜底检索，无法向量检索。
2. **v2_sharded 各分片**：Task#19/21 期间新增了 curated example chunk（training_protocol、nutrition、injury_safety、sport_psychology），但未重建嵌入。新 chunk 已写入 chunks.jsonl，FAISS 索引尚未包含这些向量。

重建前确认 `bge-m3:latest` 模型在 Ollama 中已加载：`ollama list`。

### 14.6 KB 运行时限制汇总

| 限制项 | 当前值/状态 | 说明 |
|--------|-----------|------|
| 主库总 chunk 数 | 15 653（v2_sharded） | 商业验收最低门槛：400+ chunks/shard，15+ sources/shard |
| 嵌入模型 | bge-m3:latest（1 024 维） | 换模型必须完整重建全部 FAISS 分片 |
| Chunk 大小 | 900 字符目标，110 字符重叠 | semantic_v2_sentence_window 策略 |
| STRICT_MODE | True | `knowledge_graph.py` 中禁止 LLM 自动抽取三元组；图谱仅使用注册表（registry-only） |
| v2 prescription | false | v2 兜底库全部 `explanation_only`，不支持处方输出 |
| 商业发布安全检查 | 必须通过 | `probe_vector_kb_health` 的 `no_unsafe_can_write_core` 和 `has_approved_curated_examples` 两项检查均须为 True |
