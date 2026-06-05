# Workflow Node Glossary

> 目的：把当前后端工作流节点名翻成中文解释，方便排查、交接和面试说明。本文描述的是当前代码里的真实职责，不代表所有长期重构都已完成。

## 总体流程

当前主工作流由 `apps/backend/src/marathon_qa_assistant/core/workflow_graph.py` 组装。无论是 LangGraph 版本还是 fallback 执行器，节点名字和大体路由是一致的。

简化顺序：

1. `security_gate`
2. `router`
3. `profile_update` 或 `profiler`
4. `entity_extraction`
5. `wiki_search`
6. `planner / coach / nutritionist / research_analyst / adaptive_coach / missing_info_handler`
7. `therapist`
8. `critic_auditor`
9. `formatter`
10. `guided_questions_generator`

## Node Meanings

### `security_gate`

- 中文：安全门
- 作用：先判断输入是否带有 prompt injection、危险请求、历史风险或需要直接拦截的模式。
- 输出：允许继续、直接进入格式化、或切到特定安全路径。
- 什么时候看它：用户说“为什么一上来就被拦截”时，先看这里。

### `router`

- 中文：分流器
- 作用：判断这轮请求更像普通问答、训练计划、画像更新、研究分析，还是自适应调整。
- 输出：`workflow_kind / intent_type` 一类的工作流方向信号。
- 什么时候看它：请求为什么走到了 `planner` 而不是普通 QA，先看这里。

### `profile_update`

- 中文：画像更新器
- 作用：处理从自然语言里抽出的跑者画像更新，把能确定的字段并回用户画像。
- 输出：更新后的 profile 和最小必要状态。
- 什么时候看它：用户说“我明明提供了周跑量，为什么系统没记住”时看这里。

### `profiler`

- 中文：画像整理器
- 作用：把现有画像归一化，补齐区间、基础字段和缺失信息标记。
- 输出：标准化后的用户画像和缺失字段列表。
- 什么时候看它：计划生成前为什么要求补字段，先看这里。

### `entity_extraction`

- 中文：实体抽取与检索准备
- 作用：从 query 里抽取训练相关实体，做向量检索和图谱检索的前置准备。
- 输出：`entities`、`rag_sources`、`ranked_evidence`、`evidence_bundle`、图谱上下文。
- 什么时候看它：回答为什么没有证据、为什么命中了奇怪来源时看这里。

### `wiki_search`

- 中文：外部知识补充位
- 作用：当前代码里主要保留接口和兼容路径，默认不作为核心训练处方真源。
- 输出：可选的 wiki/context 补充。
- 什么时候看它：主要在排查“为什么没有额外背景知识”时看。

### `planner`

- 中文：计划草案生成器
- 作用：把计划类请求转成周级/阶段级骨架，决定需要什么训练结构。
- 输出：训练计划草案或下一步需要的补充信息。
- 什么时候看它：为什么生成了某个训练周期结构，先看这里。

### `executor`

- 中文：计划执行细化器
- 作用：把计划草案进一步细化成更完整的训练日安排。
- 输出：可被日历和解释层消费的结构化计划结果。
- 什么时候看它：计划骨架有了，但日卡细节不完整时看这里。

### `coach`

- 中文：训练教练
- 作用：处理一般训练建议、节奏安排、跑量和恢复建议。
- 输出：训练指导文本、结构化建议或进入后续审查的数据。
- 什么时候看它：普通训练问答、非营养非伤病问题时经常会经过这里。

### `adaptive_coach`

- 中文：自适应调整教练
- 作用：处理“根据我最近训练反馈，调整下周计划”这类请求。
- 输出：调整建议、风险降级结果和后续审查输入。
- 什么时候看它：反馈驱动的计划调整问题。

### `therapist`

- 中文：伤病/风险专家
- 作用：检查伤病、疼痛、恢复和风险信号，必要时压制过激训练建议。
- 输出：安全边界、风险解释和是否允许继续。
- 什么时候看它：疼痛、胸痛、头晕、恢复期等问题都应该经过这里。

### `nutritionist`

- 中文：营养专家
- 作用：只负责营养、补给、补水、能量胶等建议。
- 边界：不负责写核心训练处方。
- 什么时候看它：如果 query 明显是营养问题，流程会直达这里。

### `research_analyst`

- 中文：研究分析节点
- 作用：处理偏研究、原理、证据整理类问题。
- 输出：研究性解释或后续交给 `therapist / critic_auditor` 的内容。
- 什么时候看它：偏“为什么、原理、研究证据怎么看”这类问题。

### `missing_info_handler`

- 中文：缺失信息处理器
- 作用：当画像或计划关键字段不足时，告诉用户还缺什么，而不是继续硬生成。
- 输出：缺失字段提示和保守引导。
- 什么时候看它：系统为什么没有直接给计划，而是要求补充信息。

### `critic_auditor`

- 中文：审查专家
- 作用：统一检查风险、证据、越权、工作流一致性，决定结果能否放行。
- 输出：`is_approved`、审计分数、风险说明、是否回退。
- 什么时候看它：为什么结果被打回、为什么进入 fallback 或格式化。

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
- 作用：根据 `workflow_kind` 决定去 `profile_update` 还是 `profiler`。

### `after_planner_route`

- 中文：planner 后分流规则
- 作用：决定计划草案可以直接进 `executor`，还是需要先补信息。

### `after_executor_route`

- 中文：executor 后分流规则
- 作用：决定计划执行结果是否先补营养建议，还是直接交给 `critic_auditor`。
- 备注：fallback executor 现在复用这一套规则，不再硬编码固定跳到 `critic_auditor`。

### `after_therapist_route`

- 中文：therapist 后分流规则
- 作用：伤病/恢复检查后，决定是否需要营养补充或直接审查。

### `after_critic_auditor_route`

- 中文：审查后路由
- 作用：如果审查通过则进入 `formatter`，否则按工作流种类回退到前面的生成节点或缺失信息处理。

## Operational Notes

- `nutritionist` 是“营养建议节点”，不是“训练处方节点”。
- `critic_auditor` 是当前唯一应该做最终放行判断的审查节点。
- `workflow_kind` 比旧的 `mode` 更接近当前真实分流语义。
- fallback 执行器与 LangGraph 执行图现在共享关键路由规则，避免两套行为漂移。
