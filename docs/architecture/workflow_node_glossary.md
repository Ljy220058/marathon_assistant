# Workflow Node Glossary

> 目的：把当前后端工作流节点名翻成中文解释，方便排查、交接和面试说明。本文描述的是当前代码里的真实职责，不代表所有长期重构都已完成。

## 总体流程

当前主工作流由 `apps/backend/src/marathon_qa_assistant/core/workflow_graph.py` 组装。无论是 LangGraph 版本还是 fallback 执行器，节点名字和大体路由是一致的。

简化顺序：

1. `security_gate`
2. `router`
3. `context_fanout`
4. `profiler / entity_extraction`
5. `evidence_retriever`
6. `conditioning_constraints`
7. `supervisor`
8. `planner / coach / adaptive_coach / missing_info_handler`
9. `executor / nutritionist / psychologist / therapist`
10. `rule_checker`
11. `critic_auditor`
12. `safety_out`
13. `formatter`
14. `guided_questions_generator`

## Node Meanings

### `security_gate`

- 中文：安全门
- 作用：先判断输入是否带有 prompt injection、危险请求、历史风险或需要直接拦截的模式。
- 输出：允许继续、直接进入格式化、或切到特定安全路径。
- 什么时候看它：用户说“为什么一上来就被拦截”时，先看这里。

### `router`

- 中文：分流器
- 作用：判断这轮请求更像普通问答、训练计划、画像更新、研究分析，还是自适应调整。
- 输出：`workflow_kind / intent_type`，以及 `intent_labels / intent_priority` 一类的工作流方向信号。
- 说明：混合意图会保留多个标签，当前优先级顺序是 `adaptive_adjustment > training_plan > nutrition_query > profile_update > general_qa`。
- 什么时候看它：请求为什么走到了 `planner` 而不是普通 QA，先看这里。

### `profiler`

- 中文：画像整理器
- 作用：把现有画像归一化，补齐区间、基础字段和缺失信息标记；当 router 判定为画像更新时，内部调用画像同步逻辑，确认更新后可直接进入 `formatter`，非更新问题继续主链。
- 输出：标准化后的用户画像和缺失字段列表。
- 什么时候看它：计划生成前为什么要求补字段，先看这里。

### `context_fanout`

- 中文：上下文并行扇出器
- 作用：在 `router` 之后并行运行 `profiler` 与 `entity_extraction`，再把画像、缺失字段和实体抽取结果收敛给 `evidence_retriever`。
- 输出：合并后的 `user_profile`、`missing_fields`、`entities / selected_entities`、执行日志与轨迹。
- 什么时候看它：排查 Layer 2 是否仍误走 `profiler -> entity_extraction` 串行链路时看这里。

### `entity_extraction`

- 中文：实体抽取与检索准备
- 作用：从 query 里抽取训练相关实体，只做检索前置准备，不直接拉取 RAG/KG 证据。
- 输出：`entities`、`selected_entities`。
- 什么时候看它：回答为什么识别了错误实体、或后续检索 query 为什么偏了时看这里。

### `evidence_retriever`

- 中文：证据检索入口
- 作用：在 `router` 已给出意图和角色类别、`entity_extraction` 已给出实体之后，执行本地知识库 RAG、意图域过滤、专家域过滤、KG 融合和 evidence bundle 构建。保持“知识库优先、外部资料不直接作为处方依据”的链路语义。
- 输出：`gate_hits`、`rag_sources`、`ranked_evidence`、`evidence_bundle`、`graph_context`、`safety_constraints`；当前保持 `wiki_context` 为空，作为旧结构化报告和 UI 的兼容字段。
- 什么时候看它：排查链路是否错误地启用了外部知识、或证据检索是否没有按意图域过滤时看。

### `supervisor`

- 中文：调度主管
- 作用：集中承接 `conditioning_constraints` 之后的意图分发，以及 `critic_auditor` 失败后的重调度。当前图内正式分发目标是 `planner / coach / adaptive_coach / missing_info_handler`；审计失败统一先回这里，再决定下一步。
- 输出：`supervisor_decision` 和路由日志。
- 什么时候看它：某个请求为什么进入 `planner / coach / adaptive_coach / missing_info_handler`，或审计失败后为什么重新调度时看这里。

### `conditioning_constraints`

- 中文：S&C 容量约束器
- 作用：把训练容量、恢复窗口、力量编排规则和风险标记整理成可执行约束，作为后续计划与调整链路的边界条件。
- 输出：`training_capacity_envelope`、`s_and_c_constraints`、`needs_therapist_review`、`s_and_c_done`。
- 什么时候看它：计划为什么不能加量、为什么需要 therapist 复核、为什么 adaptive 请求会先重算容量边界。

### `planner`

- 中文：计划草案生成器
- 作用：把计划类请求转成周级/阶段级骨架，决定需要什么训练结构。
- 输出：训练计划草案或下一步需要的补充信息。
- 什么时候看它：为什么生成了某个训练周期结构，先看这里。

### `executor`

- 中文：计划执行细化器
- 作用：先生成结构化训练计划骨架，再尝试补充文本版周计划；若 LLM 文本超时，仍保留骨架、证据和日卡链路继续向后执行。
- 输出：可被日历和解释层消费的结构化计划结果，以及可能的文本草案。
- 什么时候看它：计划骨架有了，但日卡细节不完整时看这里。

### `coach`

- 中文：训练教练
- 作用：处理一般训练建议、节奏安排、跑量、恢复建议，以及偏研究/原理类训练问答。
- 输出：训练指导文本、结构化建议或进入后续审查的数据。
- 什么时候看它：普通训练问答、研究型训练问答、非营养非伤病问题时经常会经过这里。

### `adaptive_coach`

- 中文：自适应调整教练
- 作用：处理“根据我最近训练反馈，调整下周计划”这类请求。
- 输出：调整建议、风险降级结果和后续审查输入。
- 什么时候看它：反馈驱动的计划调整问题。

### `therapist`

- 中文：伤病/风险专家
- 作用：检查伤病、疼痛、恢复和风险信号，输出医疗保护约束，必要时触发更保守的后续编排。
- 输出：`medical_constraints`、风险解释和是否需要更严格保护。
- 什么时候看它：疼痛、胸痛、头晕、恢复期等问题都应该经过这里。

### `nutritionist`

- 中文：营养专家
- 作用：只负责营养、补给、补水、能量胶等建议。
- 边界：不负责写核心训练处方。
- 什么时候看它：如果 query 明显是营养问题，流程会直达这里。

### `missing_info_handler`

- 中文：缺失信息处理器
- 作用：当画像或计划关键字段不足时，暂停当前处方链路，告诉用户还缺什么，而不是继续硬生成。
- 输出：`missing_info_status=awaiting_profile`、`workflow_pause.resume_target=router`、缺失字段提示和旧 UI 兼容报告。
- 恢复方式：前端/客户端把这轮 `workflow_pause` 原样带回 `/query` 的 `resume_from_workflow_pause`，后端用其中的 `pending_query` 重新进入 `router`，这属于 API 级恢复，不是 LangGraph checkpoint。
- 什么时候看它：系统为什么没有直接给计划，而是要求补充信息。

### `critic_auditor`

- 中文：审查专家
- 作用：消费 `rule_checker` 的硬规则结果，做最终审计判定、重试诊断和放行决策。
- 输出：`is_approved`、审计分数、风险说明、是否回退。
- 什么时候看它：为什么结果被打回、为什么进入 fallback 或格式化。

### `rule_checker`

- 中文：硬规则检查器
- 作用：在 LLM 审计前执行确定性规则检查，包括引用编号、证据路径、HMP 验证、S&C 容量边界、治疗师前置要求和用户显式合同约束。
- 输出：`rule_check_result`，供 `critic_auditor` 判断是否放行或回退。
- 什么时候看它：计划是否违反硬约束、审计失败是否来自确定性规则时先看这里。

### `formatter`

- 中文：结果格式化器
- 作用：把上游产生的结构化状态整理成 API / 前端可消费的最终输出。
- 输出：`report`、结构化字段、附加说明。
- 什么时候看它：最终响应字段丢失或格式不一致时看这里。

### `guided_questions_generator`

- 中文：追问建议生成器
- 作用：生成下一轮可继续追问的问题，帮助用户继续完善训练计划或理解结果。
- 输出：`guided_questions`
- 什么时候看它：前端追问建议为空或风格异常时看这里。

## Route Meanings

### `after_router_route`

- 中文：router 后分流规则
- 作用：统一进入 `context_fanout`，并行运行 `profiler` 与 `entity_extraction`。

### `after_context_fanout_route`

- 中文：context_fanout 后分流规则
- 作用：画像更新已在 `profiler` 内完成时直接进 `formatter`；其他请求进入 `evidence_retriever`。

### `after_conditioning_route`

- 中文：conditioning_constraints 后分流规则
- 作用：普通链路进入 `supervisor`；adaptive 请求在约束已就绪后可直接回 `planner` 重排。

### `after_planner_route`

- 中文：planner 后分流规则
- 作用：校验 planner 是否产出了可执行子任务；通过后进入 `executor`。

### `after_executor_route`

- 中文：executor 后分流规则
- 作用：执行层完成后固定进入 `nutritionist`，再补充营养与心理标注后进入规则检查链。

### `after_adaptive_coach_route`

- 中文：adaptive_coach 后分流规则
- 作用：`INJURY / FATIGUE` 或显式需要 therapist 复核时进入 `therapist`；其余自适应类型直接回 `conditioning_constraints`。

### `after_critic_auditor_route`

- 中文：审查后路由
- 作用：如果审查通过则进入 `safety_out` 再格式化；如果审查失败则统一回 `supervisor`，由 supervisor 带着 critique 重新调度。

## Operational Notes

- `nutritionist` 是“营养建议节点”，不是“训练处方节点”。
- `critic_auditor` 是当前唯一应该做最终放行判断的审查节点。
- `workflow_kind` 比旧的 `mode` 更接近当前真实分流语义。
- fallback 执行器与 LangGraph 执行图现在共享关键路由规则，避免两套行为漂移。
