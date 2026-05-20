# 三篇 Rule Challenge / RuleML 相关论文写作规范 v0.1

本文基于以下三篇本地 PDF 的只读解析整理：

- `paper50.pdf`: *Solving "Greeting a Customer with Unknown Data" Challenge with Epistemic DMN*
- `paper44.pdf`: *Explanatory Dialogues with Active Learning for Rule-based Expertise*
- `paper3.pdf`: *RuleMiner: An Interactive Web Tool for Rule-Based Data Analysis*

## 1. 样本文献基础

| PDF | 题名 | 页数 | 结构特点 | 图表 | 引用量 |
|---|---:|---:|---|---:|---:|
| `paper50.pdf` | *Solving "Greeting a Customer with Unknown Data" Challenge with Epistemic DMN* | 13 | Challenge -> criteria -> formalism -> solution -> results -> implementation | 7 图，2 表 | 约 10 篇 |
| `paper44.pdf` | *Explanatory Dialogues with Active Learning for Rule-based Expertise* | 15 | Background -> method -> human-machine interaction -> conclusion | 8 图，0 表 | 约 18 篇 |
| `paper3.pdf` | *RuleMiner: An Interactive Web Tool for Rule-Based Data Analysis* | 13 | Related work 前置 -> system/tool -> illustrative example -> future work | 约 12 图，0 表 | 约 39 篇 |

## 2. 总体写作定位

Rule Challenge 论文不是普通方法论文，也不是纯 benchmark 论文。最稳的写法是：

```text
问题/挑战是什么
为什么现有规则系统、LLM、RAG 或工具不能直接解决
你的 challenge 输入、输出、评估对象是什么
你的规则接口或参考系统如何解决
用案例、图、表、实验或 artifact 证明它可运行、可复现、可审查
明确局限，不夸大真实部署或临床安全
```

三篇论文的共同点是：都不是靠复杂公式堆砌，而是靠清楚的问题定义、可运行系统或模型、图示流程、示例结果、artifact 或 implementation 说明来支撑贡献。

## 3. 推荐篇幅

你的论文目标控制在 11-14 页是合理的。三篇参考论文都是 13-15 页，说明 RuleML/CEUR 风格允许比较充分的系统和图表说明。

| 部分 | 建议篇幅 |
|---|---:|
| Introduction | 0.8-1 页 |
| Challenge Definition | 1-1.3 页 |
| Benchmark Construction | 1.2-1.6 页 |
| Rule Reasoning Interface | 1.2-1.5 页 |
| Reference System | 1.3-1.8 页 |
| Evaluation | 1.5-2 页 |
| Related Work | 1.2-1.6 页 |
| Discussion / Limitations | 0.8-1 页 |
| Artifact / Conclusion | 0.4-0.7 页 |
| References | 1.5-2 页 |

## 4. 章节结构规范

推荐采用以下结构：

```text
1. Introduction

2. Challenge Definition
  2.1 System-Visible Inputs
  2.2 Output Contract and Status Space
  2.3 Evaluator-Only Gold Fields

3. Benchmark Construction
  3.1 Case Taxonomy
  3.2 Gold Split and Leakage Control
  3.3 Stress-Test Set

4. Rule Reasoning Interface
  4.1 Rule Facts and Predicates
  4.2 Priority and Conflict Resolution
  4.3 Trace Requirements

5. Rule-Governed Reference System
  5.1 Risk and Evidence Gates
  5.2 Prescription Contract
  5.3 Rule Auditor and Bounded Repair

6. Implementation and Evaluation
  6.1 Compared Systems
  6.2 Metrics
  6.3 Main Results
  6.4 Stress-Set Findings

7. Related Work

8. Discussion and Limitations

9. Artifact Availability

10. Conclusion
```

理由：`paper50.pdf` 最像 Rule Challenge solution，它先定义 challenge，再给 criteria，再讲 formalism 和 solution。M-EXRxBench 也应该先把 challenge 和 benchmark 讲清楚，再讲规则接口和 reference system。

## 5. 图表规范

三篇论文都大量用图，说明 RuleML/CEUR 对系统图、流程图、工具截图是接受的。M-EXRxBench 的图表应更偏规则系统和 benchmark protocol，不必担心图多，只要每张图有明确证据作用。

建议最终图表清单：

| 类型 | 作用 | 是否建议保留 |
|---|---|---|
| Figure 1: Rule-governed workflow | 解释整体系统执行顺序 | 必保留 |
| Figure 2: Trace-governed decision example | 支撑标题里的 Trace-Governed | 必保留 |
| Figure 3: Benchmark split and evaluation protocol | 证明 gold split / leakage control | 必保留 |
| Figure 4: Decision coverage map | 展示不同系统在 500 cases 上的边界表现 | 建议保留 |
| Table: Challenge outcomes | 定义 answered / partial / clarify / refused | 必保留 |
| Table: Case taxonomy | 证明 benchmark 覆盖面 | 必保留 |
| Table: Compared systems | 说明 baselines / ablations | 必保留 |
| Table: Main results | 核心实验结果 | 必保留 |
| Table: Hard100 stress result | 体现边界失败和诚实局限 | 建议保留 |

图的风格应接近 `paper50.pdf` 和 `paper3.pdf`：信息密度高、白底、少装饰、每张图都服务正文论点。避免海报式、营销式、AI 味很重的流程图。

## 6. 引用规范

三篇的引用量差异较大：

- `paper50.pdf`: 约 10 篇，偏 challenge solution，引用少但集中。
- `paper44.pdf`: 约 18 篇，偏 framework/method，引用中等。
- `paper3.pdf`: 约 39 篇，偏工具系统和 related work，对比多。

M-EXRxBench 建议引用 22-30 篇。太少会显得定位不足，太多会挤压正文。

引用分布建议：

| 类别 | 建议数量 |
|---|---:|
| RuleML / Rule Challenge / rule reasoning | 6-8 |
| RAG / agent / LLM evaluation | 5-7 |
| Clinical decision support / safety / traceability | 3-5 |
| Exercise prescription / ACSM / WHO / load / injury | 5-7 |
| Benchmark / gold split / leakage / evaluation | 3-5 |

正文里不要出现大段无引用背景。尤其 Introduction、Related Work、Ethics/Limitations 的医学和运动安全表述要有引用支撑。

## 7. Artifact 写法

`paper3.pdf` 和 `paper50.pdf` 都明确写 implementation / GitHub / available resources。M-EXRxBench 也应该写，但要短。

推荐写法：

```text
The artifact is available at [URL]. It contains benchmark files, schemas,
rules, the reference runner, evaluator, generated traces, result summaries,
figures, and reproducibility scripts.
```

不要在正文里写太多命令行细节。详细运行命令放 README 或 supplement。正文只写 artifact 内容、许可证、可复现性入口。

## 8. Results 写法

Rule Challenge 论文可以有结果，但结果要服务“challenge 可运行”和“规则边界可审查”，不要写成 clinical effectiveness。

可以写：

- deterministic evaluator
- synthetic benchmark
- rule-compliance score
- unsafe advice rate under the evaluator
- unsupported prescription rate
- trace field completeness
- stress-set boundary failures

不要写：

- clinically safe
- real-world safe
- improves athlete outcomes
- medically validated
- deployable coach

## 9. Related Work 写法

Related Work 不要写成论文列表。建议四段式：

1. Exercise prescription and safety guidance

说明为什么运动处方不是普通训练建议。

2. RAG and evidence-constrained generation

说明现有 RAG 解决 grounding，但不解决“证据是否有权授权处方”。

3. Rule reasoning and decision support

连接 RuleML+RR、CDSS、规则优先级、冲突解决。

4. LLM agents and tool use

说明多 agent 有用，但如果没有 rule boundary，就容易变成自由协商式计划生成。

每段最后都要落回你的差异点：trace-governed permission boundary。

## 10. 写作风险清单

投稿前重点检查这些：

- 是否把 reference system 写得像 gold label 生成器。
- 是否暗示 hard100 结果也是主 benchmark 成绩。
- 是否把 trace completeness 写成 semantic correctness。
- 是否把 synthetic benchmark 写成真实临床验证。
- 是否把 LLM/RAG 背景写太长，冲淡 Rule Challenge。
- 是否缺少 GitHub/artifact availability。
- 是否图多但正文没有解释每张图为什么存在。
- 是否 Related Work 引用足够但没有比较。
- 是否章节太碎，第 4/5 节规则内容重复。
- 是否全文标题说 Trace-Governed，但正文缺 trace 示例或 trace 表。

## 11. 一句话标准

M-EXRxBench 论文应该写成：

> 一个可复现的 Rule Challenge artifact：定义 evidence-bounded exercise prescription 的输入、输出、gold split、规则接口、trace 要求和参考系统，并用 synthetic benchmark 证明规则边界可被审查，而不是证明真实运动处方安全。

