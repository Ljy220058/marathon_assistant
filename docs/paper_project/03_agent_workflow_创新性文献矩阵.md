# Agent Workflow 创新性文献矩阵

## 0. 目的

本文件用于判断当前“马拉松助手”工作流是否具备论文创新点，并从其他 agent / agentic RAG / 多智能体 / 高风险领域工作流中提炼可借鉴机制。

当前拟定位：

> 面向耐力训练问答的 protocol-grounded, evidence-gated, audit-and-repair agentic RAG workflow。

注意：

- 本文件是创新性诊断和论文构思材料，不等同于最终参考文献表。
- 投稿前必须逐条核查 BibTeX、作者、年份、会议/期刊、DOI、页码和版本。
- 不把已有论文机制写成我们的原创贡献。
- 我们的创新应来自“领域协议 + 分层证据 + 独立审计 + 有界修复/拒答”的组合，而不是泛泛宣称“多智能体 RAG”。

## 1. 当前工作流可发表资产

当前仓库中已经有潜在论文方法贡献的组件：

| 组件 | 当前资产 | 可转化为论文语言 |
|---|---|---|
| 干净运行态 | `build_working_state()` | Per-request working-state reset，避免长期会话 agent 的状态污染。 |
| 安全门 | `security_gate_node` | Safety-first request screening。 |
| 意图分流 | `router_node` / `workflow_kind` | Task-adaptive routing for QA / planning / research / adaptive requests。 |
| 证据包 | `EvidenceBundle` | Tiered evidence contract for downstream generation, auditing, and UI citation。 |
| 领域协议 | HMP protocol / capacity budget / validator / repair executor | Domain protocol as executable constraints, not merely retrieved text。 |
| 审计节点 | `critic_auditor` | Independent gatekeeper; generation nodes cannot self-approve。 |
| 有界修复 | `repair_executor` + max repair attempts | Bounded audit-repair loop with refusal / missing-info fallback。 |
| 解释展示 | evidence base / protocol panels | Evidence-aware user-facing explanation。 |

初步判断：

- “多角色协作”本身不新。
- “RAG + 自我批判”本身不新。
- 有潜力的新点是：在耐力训练这种安全敏感、协议明确但知识异构的领域，把训练协议、RAG 证据、审计修复和拒答机制编排成一个可评测 workflow。

## 2. 20 篇核心相关论文

### 2.1 工具使用与单 Agent 编排

| ID | 论文 | 工作流机制 | 对我们的启发 |
|---|---|---|---|
| P01 | [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) | 交替执行 reasoning trace 与 action/tool use。 | 我们可以把检索、协议校验、容量预算、审计都显式建成 action，而不是隐藏在 prompt 里。 |
| P02 | [MRKL Systems: A Modular, Neuro-Symbolic Architecture That Combines Large Language Models, External Knowledge Sources and Discrete Reasoning](https://arxiv.org/abs/2205.00445) | 路由到不同专家模块或符号工具。 | 我们的 HMP 协议、动作库、RAG、Wiki 不应混成一个上下文，应以模块化证据源进入工作流。 |
| P03 | [Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761) | 模型学习何时调用外部工具。 | 后续可以设计“何时检索、何时调用协议规则、何时拒答”的策略评测。 |
| P04 | [ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models](https://arxiv.org/abs/2305.18323) | 先规划工具调用，再批量观察结果，减少交互成本。 | 可借鉴为 retrieval planner -> hybrid retriever -> evidence ranker，降低长链路重复检索。 |
| P05 | [An LLM Compiler for Parallel Function Calling](https://arxiv.org/abs/2312.04511) | 将任务编译为可并行函数调用计划。 | 多证据源检索、规则校验、安全检查可并行化，形成更强的 agent workflow 工程亮点。 |
| P06 | [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560) | 把上下文、长期记忆和外部存储分层管理。 | 长期运行到投稿阶段时，用户画像、实验记录、证据审计和短期对话必须分层，不能混入同一状态。 |

### 2.2 自反、验证与 Agentic RAG

| ID | 论文 | 工作流机制 | 对我们的启发 |
|---|---|---|---|
| P07 | [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366) | agent 通过语言反馈反思失败并改进后续尝试。 | 审计反馈可进入修复器，但必须由确定性规则约束，避免 LLM 自我美化。 |
| P08 | [Self-Refine: Iterative Refinement with Self-Feedback](https://arxiv.org/abs/2303.17651) | 生成、反馈、改写的迭代闭环。 | 可借鉴“反馈-修复”形式，但我们的论文要强调独立 auditor 和最多 1-2 轮有界修复。 |
| P09 | [Chain-of-Verification Reduces Hallucination in Large Language Models](https://arxiv.org/abs/2309.11495) | 先生成回答，再生成验证问题并回答验证问题以减少幻觉。 | 我们可把风险题拆成 claim-level verification，而不是只看最终答案是否顺眼。 |
| P10 | [Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection](https://arxiv.org/abs/2310.11511) | 模型学习检索、生成和批判的反思 token。 | 不能只说“有检索有审计”就是创新；我们的差异应是领域协议与证据等级约束。 |
| P11 | [Corrective Retrieval Augmented Generation](https://arxiv.org/abs/2401.15884) | 检索评估器判断文档质量，不足时纠错或扩展检索。 | 可直接启发 evidence_gate：证据不足、主题不相关、召回低质时拒答或补检索。 |
| P12 | [RAGTruth: A Hallucination Corpus for Developing Trustworthy Retrieval-Augmented Language Models](https://arxiv.org/abs/2401.00396) | 对 RAG 输出进行细粒度幻觉标注。 | 我们的 benchmark 应加入 unsupported claim rate、claim evidence coverage、invalid citation rate。 |

### 2.3 多智能体协作框架

| ID | 论文 | 工作流机制 | 对我们的启发 |
|---|---|---|---|
| P13 | [AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation](https://arxiv.org/abs/2308.08155) | 通过多 agent 对话组织复杂任务。 | coach / therapist / nutritionist / auditor 可以借鉴对话式协作，但论文必须展示固定职责和可评测输出。 |
| P14 | [CAMEL: Communicative Agents for "Mind" Exploration of Large Scale Language Model Society](https://arxiv.org/abs/2303.17760) | role-playing agent 通过角色互动完成任务。 | 角色设定不能停留在 prompt；需要把角色输出绑定到 evidence bundle 和安全规则。 |
| P15 | [ChatDev: Communicative Agents for Software Development](https://arxiv.org/abs/2307.07924) | 用软件公司 SOP 组织多 agent 开发流程。 | 很适合借鉴“领域 SOP 化”：把耐力训练咨询流程编码成固定阶段，而不是自由聊天。 |
| P16 | [MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework](https://arxiv.org/abs/2308.00352) | 将标准操作程序编码进多 agent 协作。 | 这是我们最重要的横向借鉴之一：HMP 协议、风险降级、审计放行都可以写成 endurance-training SOP。 |
| P17 | [AgentVerse: Facilitating Multi-Agent Collaboration and Exploring Emergent Behaviors](https://arxiv.org/abs/2308.10848) | 提供多 agent 协作和环境反馈框架。 | 可借鉴 task solving -> simulation/evaluation 的结构，用 benchmark 作为我们的环境反馈。 |
| P18 | [AutoAgents: A Framework for Automatic Agent Generation](https://arxiv.org/abs/2309.17288) | 自动生成不同角色 agent 以适应任务。 | 后续可探索按问题类型动态启用 coach / therapist / nutritionist，而不是每轮固定全走。 |

### 2.4 辩论、医疗与高风险领域 Agent

| ID | 论文 | 工作流机制 | 对我们的启发 |
|---|---|---|---|
| P19 | [Improving Factuality and Reasoning in Language Models through Multiagent Debate](https://arxiv.org/abs/2305.14325) | 多 agent 互相辩论，提高事实性和推理质量。 | 可借鉴为“专家意见冲突时进入审计”，但不能让辩论替代真实证据。 |
| P20 | [MDAgents: An Adaptive Collaboration of LLMs for Medical Decision-Making](https://arxiv.org/abs/2404.15155) | 医疗决策中根据任务复杂度动态选择单 agent 或多 agent 协作。 | 对我们非常关键：耐力训练建议虽非医疗诊断，但也有健康风险，可借鉴复杂度/风险驱动的 agent 激活策略。 |

## 3. 这些论文告诉我们：哪些不能当创新点

以下说法不宜作为核心创新：

- “我们用了多个 agent。”
- “我们加入了 critic / auditor。”
- “我们用了 RAG 减少幻觉。”
- “我们有 planner-executor 工作流。”
- “我们让模型自己反思修复。”

这些都已有大量相关工作。若作为论文贡献，需要进一步领域化、可评测化和机制化。

## 4. 更有希望的创新表述

### 4.1 Protocol-Grounded Agentic RAG

已有 RAG 多把外部知识作为上下文；我们的差异可以是：

- 耐力训练协议不是普通文本，而是机器可执行约束。
- HMP 阶段、容量预算、训练类型、恢复间隔、风险降级先生成结构化骨架。
- LLM 只负责表达、解释和引用，不自由新增处方级负荷。

可写成：

> We encode endurance-training protocols as executable constraints and place them before free-form generation in the agentic RAG workflow.

### 4.2 Tiered EvidenceBundle

已有工作重视 retrieved documents；我们的差异可以是分层证据契约：

- `protocol_rule`：领域规则。
- `action_library`：训练动作或课表模板。
- `kb_fallback`：一般知识库证据。
- `graph`：图谱路径。
- `wiki_context`：概念解释，不作为处方依据。
- `plan_only`：规则骨架兜底，需要显式标注。

可写成：

> We introduce a tiered evidence contract that separates protocol rules, retrieved knowledge, graph evidence, and explanatory context before generation and auditing.

### 4.3 Evidence Gate + Audit-Repair-Refusal

已有 Self-RAG / CRAG 会评估检索质量；我们的差异可以是：

- evidence gate 不只判断检索相关性，还判断是否足以支撑训练建议。
- auditor 独立放行，生成节点不能自我批准。
- 修复有上限，修不好就拒答或补信息。

可写成：

> The workflow turns insufficient evidence into missing-information requests, conservative fallback, or refusal rather than unsupported generation.

### 4.4 Risk-Aware Agent Activation

借鉴 MDAgents，可把不同风险级别映射到不同 agent 路径：

| 风险/复杂度 | 建议路径 |
|---|---|
| 低风险事实问答 | retriever -> evidence gate -> answer writer |
| 应用推理 | retriever -> evidence bundle -> coach -> auditor |
| 疲劳/伤痛/异常心率 | therapist + safety audit 必须启用 |
| 营养补给问题 | nutritionist + evidence audit |
| 缺证或冲突证据 | missing-info / refusal |

这比固定多 agent 更像可发表的 adaptive workflow。

## 5. 可借鉴的实验设计

### 5.1 消融实验

至少应设计以下 ablation：

| 设置 | 移除内容 | 预期观察 |
|---|---|---|
| Full workflow | 无 | 最佳证据覆盖与安全表现 |
| w/o protocol rules | 移除 HMP / 训练协议规则 | 应用推理和风险题更容易失控 |
| w/o evidence gate | 检索结果直接给生成器 | unsupported claim 增多 |
| w/o independent auditor | 生成节点自我批准 | invalid citation / unsafe answer 增多 |
| w/o repair/refusal | 审计失败仍输出 | 安全合规下降 |

### 5.2 指标

建议主指标：

- Recall@5。
- MRR@5。
- Claim Evidence Coverage。
- Unsupported Claim Rate。
- Invalid Citation Rate。
- Safe Refusal / De-escalation Rate。
- Faithfulness。
- Answer Relevancy。

### 5.3 数据集结构

pilot benchmark 先保持 30-50 题：

- 事实抽取：约 1/3。
- 应用推理：约 1/3。
- 风险安全：约 1/3。

每题必须标注：

- 是否 answerable。
- 标准答案依据。
- 证据材料 ID。
- 证据定位。
- 是否需要拒答、降级或专业建议。

## 6. 对我们论文最有帮助的三条借鉴路线

### 路线 A：从 MetaGPT / ChatDev 借鉴 SOP 化

把 endurance training consultation 写成 SOP：

1. 安全检查。
2. 意图分类。
3. 证据规划。
4. 多源检索。
5. 证据分层。
6. 协议约束。
7. 生成。
8. 审计。
9. 修复、拒答或格式化输出。

适合支撑“agent 框架是论文大创新点”。

### 路线 B：从 CRAG / Self-RAG 借鉴证据门控

把 RAG 质量判断做成显式节点：

- 证据是否命中。
- 证据等级是否足够。
- 证据是否支持处方级建议。
- 是否需要补检索或拒答。

适合支撑“不是普通 RAG，而是证据约束 RAG”。

### 路线 C：从 MDAgents 借鉴风险驱动协作

把不同风险问题映射到不同 agent 激活策略：

- 低风险不强制多 agent。
- 高风险必须 therapist / auditor。
- 营养问题启用 nutritionist。
- 证据冲突启用 auditor 或 refusal。

适合支撑“多智能体不是堆角色，而是按风险和复杂度动态编排”。

## 7. 下一步建议

建议后续新增或补充两个文档：

1. `04_agent_workflow方法草图.md`
   - 画出我们自己的 workflow。
   - 明确每个节点输入、输出、失败条件和可评测字段。

2. `05_agent_workflow消融实验设计.md`
   - 把 full workflow、普通 RAG、无检索 LLM、移除审计、移除证据门控等设置写成实验矩阵。

在代码层，下一步最值得补强的是：

- 将 `EvidenceBundle` 的证据等级和输出 claim 绑定，形成 claim-level evidence coverage。
- 把 `critic_auditor` 的失败原因标准化为可统计标签。
- 为风险安全题增加 safe refusal / de-escalation 的自动或半自动评分。
- 实现风险驱动 agent activation，而不是固定路径依赖。
