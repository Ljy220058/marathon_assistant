# 多智能体工作流链路命名审计

> 审计来源：只读 explorer agent `Goodall`  
> 审计时间：2026-06-12  
> 审计范围：当前工作区 `C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手`  
> 说明：本报告记录审计 agent 的静态检查结论，未运行长时间训练生成，未修改代码。

## 当前真实主链路

截至本文件更新，主线程已完成以下修正：

- `entity_extraction` 只做实体抽取，`evidence_retriever` 承担本地 KB/RAG、KG 融合和 evidence bundle 构建。
- `context_fanout` 承担 Layer 2 扇出与收敛：并行运行 `profiler` 与 `entity_extraction`，再进入 `evidence_retriever`。
- 旧 `wiki_search_node` 兼容别名已删除，不在主图中承担外部 Wiki 检索。
- 已加入显式 `supervisor` 和 `rule_checker`。
- `critic_auditor` 失败回跳统一回 `supervisor`。
- 研究型训练问答主链已并入 `coach`，独立 `research_analyst` 节点实现已删除。
- `profile_update` 已从 router 独立主分支调整为 `profiler` 的画像同步副作用；独立图节点已删除。
- `missing_info_handler` 已输出 `workflow_pause.resume_target=router` 的暂停/恢复协议；当前仍保留 formatter 兼容输出，真实 resume 由调用方补齐画像后以原始请求重新进入 router。

### API 默认计划链路

`/query` 对计划类请求默认走 skeleton-first 路径：

```text
/query
-> is_plan_query()
-> _build_skeleton_plan_response()
-> _build_skeleton_state()
-> build_structured_training_plan_skeleton()
-> generate_daily_schedule()
-> build_training_plan_review()
-> build_workflow_trace()
-> 保存训练计划
-> 返回 QueryResponse
```

关键点：

- 计划类请求只有显式 `response_mode="full"` 才走 `integrated_app.ainvoke()`。
- 默认计划链路不执行完整 LangGraph 多节点图。
- `qa_fast` 快速问答链路只跑部分节点，不经过完整审计闭环。

### Full LangGraph 链路

当前 full graph 主链路：

```text
START
-> security_gate
-> router
-> context_fanout (profiler ∥ entity_extraction)
-> evidence_retriever
-> conditioning_constraints
-> supervisor
-> 分支
```

计划主分支：

```text
conditioning_constraints
-> planner
-> executor
-> nutritionist
-> psychologist
-> rule_checker
-> critic_auditor
-> safety_out
-> formatter
-> guided_questions_generator
-> END
```

普通教练问答：

```text
coach
-> rule_checker
-> critic_auditor
-> safety_out
-> formatter
```

营养问答：

```text
nutritionist
-> psychologist
-> rule_checker
-> critic_auditor
-> safety_out
-> formatter
```

研究型训练问答：

```text
coach
-> rule_checker
-> critic_auditor
-> safety_out
-> formatter
```

## 自适应调整链路

入口：

```text
security_gate
-> router
-> context_fanout (profiler ∥ entity_extraction)
-> evidence_retriever
-> conditioning_constraints
-> supervisor
-> adaptive_coach
```

分流规则：

```text
INJURY / FATIGUE / needs_therapist_review
-> therapist
-> conditioning_constraints
-> planner
-> executor
-> rule_checker
-> critic_auditor
```

```text
MISSED / SCHEDULE / PERFORMANCE
-> conditioning_constraints
-> planner
-> executor
-> rule_checker
-> critic_auditor
```

## KB / RAG / 外部 Wiki 优先级

真实优先级：

1. 本地知识库 RAG 与动作库。
2. 知识图谱融合。
3. 角色专家补证据。
4. 外部资料仅作为候选补充，不直接进入核心处方。

当前主链路不直接启用外部 Wiki。`wiki_search_node()` 历史兼容别名已删除，正式链路节点是 `evidence_retriever`。

## 命名不一致清单

### P0

1. API 默认计划链路不是完整 multi-agent graph，但旧文档容易让人误解为所有计划都走 LangGraph。
2. `evidence_retriever` 曾经只是占位名，真实检索在 `entity_extraction`；该项已在主线程修正为真实检索节点。
3. `wiki_search_node` 历史别名已删除；`wiki_context` 仍是输出 schema/UI 兼容字段，当前保持为空。
4. `auditor_node` / `reviewer` / `critic_auditor` 多套命名并存，应统一以 `critic_auditor` 为当前正式名。

### P1

1. `planner` 实际更像任务规划器，真正生成结构化计划的是 `executor`。
2. `executor` 实际承担训练计划生成器职责，不只是执行子任务。
3. `conditioning_constraints` 实际是 S&C 容量边界节点，应在文档中明确。

### P2

1. `nutritionist -> psychologist -> critic_auditor` 是固定图边，但 `psychologist_node` 内部可按需跳过。
2. `mode` 与 `workflow_kind` 并存，当前路由主要依赖 `workflow_kind`。

## 建议策略

- 主链统一使用 `evidence_retriever`，不再保留 `wiki_search_node` deprecated alias。
- `entity_extraction` 只做实体抽取和检索准备。
- `evidence_retriever` 承担 RAG、KG、意图域过滤、专家域过滤和 evidence bundle 构建。
- 文档中把 `planner` 解释为 task planner，把 `executor` 解释为 plan generator executor。
- 文档统一使用 `critic_auditor`，旧名只作为历史兼容说明。
- API 文档明确区分 skeleton-first 默认路径和 full multi-agent workflow 路径。

## 仍待处理的架构问题

- 已补显式 `supervisor` 节点；当前代码里 `critic_auditor` 失败后统一先回 `supervisor`，再由 `supervisor` 只分流到 `planner / coach / adaptive_coach / missing_info_handler`。
- 已补独立 `rule_checker`，硬规则结果写入 `rule_check_result` 后再交给 `critic_auditor`。
- `critic_auditor` 失败回跳已统一回 `supervisor`；更细粒度的 diagnosis-aware 深度回跳还没有在当前图里落成，不能把它当成已上线链路。
- `missing_info_handler` 已输出结构化暂停/恢复协议；尚未引入 LangGraph checkpoint interrupt，调用方需按 `workflow_pause.pending_query` 和 `resume_target=router` 重新提交原始请求。
- `research_analyst` 主链职责已并入 `coach`；旧节点实现和直接测试已删除。
- `profile_update` 已合并为 profiler 副作用；独立图节点已删除，画像同步实现仍由 profiler 内部调用。
- `nutritionist` 同时承担营养问答角色和计划后标注角色，建议后续拆名或文档明确双职责。

## 判断依据

- `apps/backend/src/marathon_qa_assistant/core/workflow.py`
- `apps/backend/src/marathon_qa_assistant/core/workflow_graph.py`
- `apps/backend/src/marathon_qa_assistant/nodes/routing/__init__.py`
- `apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py`
- `apps/backend/src/marathon_qa_assistant/nodes/expert_nodes.py`
- `apps/backend/src/marathon_qa_assistant/nodes/plan_nodes.py`
- `apps/backend/src/marathon_qa_assistant/apps/routers/query.py`
- `apps/backend/src/marathon_qa_assistant/apps/response_builders.py`
- `docs/architecture/workflow_node_glossary.md`
