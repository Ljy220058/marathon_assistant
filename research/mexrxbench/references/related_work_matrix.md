# Related Work Matrix

本矩阵服务于 RuleML+RR 2026 Rule Challenge 论文《A Trace-Governed Rule Challenge for Evidence-Bounded Exercise Prescription》。选择文献的原则不是泛泛覆盖全部运动科学或 RAG 文献，而是横向比较四个与本文直接相关的领域：

1. 运动处方、康复与临床决策支持系统。
2. 规则推理、RuleML、合规与符号治理。
3. RAG、LLM 证据治理与安全修复。
4. 多智能体系统、agent safety 与 benchmark。

本文的核心定位是：现有工作分别证明了规则化运动处方、临床 CDSS、RAG 证据增强、LLM 安全原则、多智能体协作和规则 benchmark 的价值，但缺少一个面向运动处方 agent 的可复现、可审计、证据有界、规则治理的 Rule Challenge artifact。

## 横向领域对比

| ID | 领域 | 代表论文 | 方法与规模 | 主要贡献 | 可改进不足 | 本文差异化机会 |
|---|---|---|---|---|---|---|
| RW01 | 运动处方 / 康复 CDSS | REPT: rule-based exercise prescription tool for phase III cardiac rehabilitation | 约 112 条 actionable rules；12 个模拟病例；外部评估含 33 名 general practitioners | 证明心脏康复场景中，规则化运动处方可以输出 permissibility report 与 FITT 训练安排 | 单病种、病例规模小；缺公开 benchmark、hard cases、跨系统对比和自动修复评测 | 将“规则化处方工具”推进为“可比较评测基础设施”：500 cases + hard100、trace-level scoring、bounded repair |
| RW02 | 临床 CDSS / FHIR | CAREPATH: transforming evidence-based clinical guidelines into implementable CDS services | 25 个指南来源；65 个 CDS services；296 条 CDS rules；346 个 CDS cards | 展示如何把指南转为 UML、FHIR concepts、CDS Hooks cards | 更像指南转译工程，不是 generative agent benchmark；运动处方部分较浅；临床可用性仍待验证 | 借鉴标准化 CDSS artifact，但要求 agent 输出 PrescriptionContract、evidence trace 和 audit result |
| RW03 | RuleML 医疗规则系统 | KMR-II: Managing High Disease Risk Factors | RuleML Challenge 医疗知识管理 use case；主要是架构与场景展示 | 将规则、工作流、预测模型和健康管理通知组合成医疗 CDSS 基础设施 | 不是公开 benchmark；没有系统性风险、证据、修复和可复现实验设计 | 将 RuleML 医疗规则原型升级为可运行、可评测、可复现的运动处方 Rule Challenge |
| RW04 | 规则 benchmark / 业务规则 | Benchmark for Rule Induction in Automated Business Decisions | 多个公开业务决策数据集与 synthetic suites；比较多种 rule induction pipeline | 说明 RuleML+RR 接受 benchmark 化、artifact 化的规则研究 | 关注业务分类和规则归纳，不覆盖健康风险、证据边界或生成式处方 | 用运动处方构造规则遵循、风险门控和处方合约的垂直 benchmark |
| RW05 | 规则遵循 benchmark | RuleArena | 95 条真实规则；816 个 test problems；航空行李、NBA 交易、税务三个领域 | 评估 LLM 在真实规则约束下的推理与遵循能力 | 规则域较泛；没有运动处方、医学风险分层、处方剂量结构和 fail-closed 机制 | 把 rule following 推进到 evidence-bounded prescription：不只判断答案对错，还判断能否处方 |
| RW06 | RAG / 证据自检 | Self-RAG | 训练 LM 生成 Retrieve、IsRel、IsSup、IsUse 等 reflection tokens；评测 PopQA、TriviaQA、PubHealth、ARC 等 | 证明生成过程需要显式判断检索需要、证据相关性和支持度 | 主要处理事实性和引用支持，不处理处方资格、禁忌证、训练剂量边界 | EvidenceGate 区分“解释证据”和“处方证据”，trace 记录证据资格而非仅引用文本 |
| RW07 | RAG / 检索纠错 | CRAG: Corrective Retrieval Augmented Generation | 用 retrieval evaluator 判断 Correct / Incorrect / Ambiguous，并触发纠错或补检索 | 证明普通 RAG 检索失败需要被检测和修正 | 检索纠错不等于安全处方；web search 可能引入新噪声；没有 contract 或风险门 | 将纠错限制为 bounded repair：删除、降级、替换 approved action，不能自由再生成 |
| RW08 | LLM 安全原则 | Constitutional AI | 用显式原则驱动 critique、revision 和 RLAIF；大规模 red-team 与 preference 数据 | 证明安全行为可以由显式原则驱动自我批判和修订 | 原则多为自然语言，主观性强；不是医学证据绑定；无法保证处方结构合规 | 把 constitution 具体化为 RiskGate、EvidenceGate、rule priority、repair invariants 和 PrescriptionContract |
| RW09 | 多智能体 benchmark | MultiAgentBench / MARBLE | 覆盖 research、Minecraft、database、coding、bargaining、Werewolf 等场景；比较 star/tree/chain/graph 协作拓扑 | 系统评估多智能体协作、规划、沟通和任务完成能力 | 关注协作能力，不关注医学合规；部分指标依赖 LLM judge；缺少高风险 domain rules | 本文不是比拼协作拓扑，而是让多角色运动处方团队服从可审计规则和 veto |
| RW10 | Agent safety benchmark | Agent-SafetyBench | 349 个交互环境、2,000 个测试用例、8 类安全风险、10 类 failure modes；评测 16 个 tool-using agents | 说明 tool-using agents 在安全场景中普遍存在鲁棒性和风险意识问题 | 风险标签较粗；不能定位证据不足、禁忌、处方结构违约、修复失败等具体错误 | M-EXRxBench 以 trace-level metrics 拆解 unsafe advice、unsupported prescription、rule violation、repair success |
| RW11 | Prompt injection / tool safety | AgentDojo | 97 个真实感用户任务、629 个安全测试用例、70+ 工具；组合 user task 与 attacker goal | 动态评估 tool-calling agent 面对 prompt injection 的任务效用和攻击成功率 | 重点是工具输出注入，不处理运动处方证据资格、医学红旗和剂量边界 | 将 prompt/retrieval injection 纳入运动处方 hard cases，并用 Rule Auditor 覆盖注入优先级冲突 |

## 纵向差异链条

### 从运动处方系统到运动处方 benchmark

REPT、CAREPATH 和 KMR-II 说明规则系统、FHIR/CDSS 和康复处方工具都具备实践价值，但这些工作多数以单系统、单病种、少量场景或工程转译为主。M-EXRxBench 的差异是把问题改写成 Rule Challenge：给定 system-visible cases、gold split、schema、evaluator、baselines、trace viewer 和 reproducibility scripts，让不同系统可以在同一安全敏感任务上比较。

### 从 RAG 证据增强到证据资格治理

Self-RAG 和 CRAG 证明“检索到文本”不足以保证生成可靠，系统还需要判断证据相关性、支持度和检索质量。本文进一步区分 evidence relevance 与 prescription eligibility：普通论文、一般 KB 或通用指南可以解释概念，但不能自动授权个体化训练剂量。EvidenceGate 因此是处方资格门，而不只是检索排序器。

### 从通用 AI safety 到处方合约

Constitutional AI 和 Agent-SafetyBench 提供了通用安全原则与 agent safety 评测思路，但对运动处方来说，安全不是单一二元标签。本文把安全拆成 RiskGate、EvidenceGate、PrescriptionContract、rule priority、bounded repair 和 trace completeness，使评估能定位具体失败层：红旗未拒绝、证据不足仍处方、训练量越界、注入绕过规则、修复不合法等。

### 从多智能体协作到规则治理团队

MultiAgentBench 评估多智能体协作是否有效，但普通“专家讨论后由教练总结”的模式无法保证高风险边界。本文保留三类常驻角色：Evidence Steward、Prescription Coach、Rule Auditor。Coach 负责整合，但不是最高权力；Rule Auditor 有 veto；条件专家只在 RiskGate 触发时进入。这使多智能体从角色扮演转向规则治理。

## 可写入论文的差异化表述

本文不是提出另一个 RAG running coach，而是把运动处方生成重新定义为一个 evidence-bounded rule challenge。与现有 CDSS 和运动处方工具相比，本文提供公开 benchmark、gold split、baselines、trace schema 和可复现实验；与 Self-RAG/CRAG 相比，本文把证据相关性进一步提升为处方资格判定；与 Constitutional AI 和 agent safety benchmark 相比，本文将安全原则落地为可机器检查的处方合约、风险门和修复不变量；与 multi-agent benchmark 相比，本文不追求更多角色协作，而是追求角色输出被 Rule Auditor 约束、审计和必要时拒绝。

建议在论文中保留一条克制但清晰的 novelty claim：

> To our knowledge, M-EXRxBench is the first Rule Challenge artifact that evaluates evidence-bounded, rule-governed multi-agent exercise-prescription agents with prescription contracts, fail-closed repair, and auditable traces.
