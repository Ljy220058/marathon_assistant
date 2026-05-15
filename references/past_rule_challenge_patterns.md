# Past Rule Challenge Patterns

## 来源

- RuleML+RR Companion 2025, CEUR Vol. 4083: <https://ceur-ws.org/Vol-4083/>
- RuleML+RR Companion 2024, CEUR Vol. 3816: <https://ceur-ws.org/Vol-3816/>
- RuleML+RR Challenge 2023, CEUR Vol. 3485: <https://ceur-ws.org/Vol-3485/>

## 观察到的录用形态

| Year | Paper / Pattern | Type | 对 M-EXRx 的启发 |
|---|---|---|---|
| 2025 | Wikidata as a Challenge for Rule Systems | benchmark / open challenge | challenge 可以以开放问题和评测基础设施为核心贡献 |
| 2025 | Synthesising Bayesian Network Models for Clinical Decision Support from Rule-Based Logic | healthcare / rules + decision support | 健康决策支持可以进入 Rule Challenge，但必须有规则和评估 |
| 2025 | Scalable, Context-Aware NLP Moderation for Child Safety: A Multi-Agent Ethical and Legal Compliance Framework | multi-agent / compliance / safety | 多智能体要被伦理/法律规则约束，而不是自由讨论 |
| 2025 | When Data Stands Before the Law: Representing Financial Rules in SPARQL | policy / compliance | 高风险场景适合强调规则优先级和可审计表示 |
| 2025 | Time for FuN3: Pre-compiling Rules into a High-Level Imperative Language | tool / rule execution | 工具型论文需要说明可执行性和性能/可用性 |
| 2024 | RuleMiner: An Interactive Web Tool for Rule-Based Data Analysis | tool / UX | Rule Challenge 接受可交互工具；我们的 CLI 可作为最低版本，viewer 是增强项 |
| 2024 | Rule-aware Datalog Fact Explanation Using Group-SAT Solver | explanation / rule reasoning | trace 不能只是日志，应能解释规则如何触发 |
| 2024 | Softening Ontological Reasoning with Large Language Models | LLM + symbolic reasoning | LLM 与规则结合是可投方向，但规则贡献要清楚 |
| 2024 | Distributed Component Interoperation and Execution for Norm-Based Real-time Compliance | distributed rules / compliance | 可借鉴 norm-based compliance 叙事来解释 Rule Auditor |
| 2024 | Integrating Symbolic Knowledge and Machine Learning in Healthcare | healthcare / hybrid AI | healthcare/life sciences 场景需要明确安全边界 |
| 2024 | Fair Shifts by the Rule: a Rule-based Compliance Methodology for Medical Rosters | healthcare / policy / fairness | 医疗相关任务常以约束、合规和公平性为核心 |
| 2023 | Towards Complex Event Processing for Clinical Decision Support using FHIR | clinical decision support / CEP | 风险信号可被建模为 event / rule trigger |
| 2023 | GPT-3 for Decision Logic Modeling | LLM + decision logic | 说明 RuleML 社区关注 LLM 参与规则建模，但不是直接自由输出 |
| 2023 | Multi-agent Online Planning Architecture for Real-time Compliance | multi-agent / compliance | 说明 multi-agent + rules 的接收路径；本文应强调 auditor veto |
| 2023 | An Ontology-based Approach for Detecting and Classifying Inappropriate Prescribing | prescribing / ontology / safety | 与运动处方最接近：处方任务需要拒绝不适当建议 |
| 2023 | Defeasible Reasoning with Large Language Models | LLM + non-monotonic reasoning | 可作为讨论中说明 LLM 与规则推理结合的先例 |
| 2023 | Reasoning over Health Records with Vadalog | health records / rules | 健康路径可以规则化，本文把训练处方也规则化 |

## 对本文的验收启发

1. **必须有 artifact**：只写 conceptual workflow 不够，需要 benchmark、runner、trace、schema。
2. **必须有规则主贡献**：LLM 应被写成候选生成器/解释器，而不是最终推理器。
3. **必须有真实挑战感**：红旗症状、证据不足、提示注入、目标冲突比普通训练计划更能体现 challenge。
4. **必须可审计**：输出计划之外，要展示 `rules_fired`、`audit_result`、`repair_log`。
5. **必须有开放资源路径**：即便暂时没有 Web UI，也要有 repo、命令、数据格式和扩展说明。

## 本文可借鉴的写法

> We align with the Rule Challenge tradition of presenting executable, reproducible artifacts for rule-oriented problems. Unlike generic LLM planning systems, our challenge is centered on prescription eligibility: whether a candidate exercise recommendation is allowed, downgraded, repaired, clarified, or refused under explicit safety and evidence rules.
