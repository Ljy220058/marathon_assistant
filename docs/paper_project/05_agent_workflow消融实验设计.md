# Agent Workflow 消融实验设计

## 0. 文档目的

本文件用于设计论文中的 agent workflow 对比实验与消融实验，目标是回答一个核心问题：

> 当前提出的 protocol-grounded, evidence-gated, audit-and-repair agentic RAG workflow，是否比无检索 LLM、普通 RAG 和缺少关键节点的 agentic RAG 更可信、更可追溯、更安全？

本文件只定义实验方案，不记录实验结果。任何数值、结论、显著性或图表必须来自后续真实运行。

硬性约束：

- 不编造指标。
- 不编造样本量。
- 不编造模型版本。
- 不把预期结果写成已观察结果。
- 不把一次失败运行从实验记录中删除。

## 1. 实验总目标

第一版实验围绕 RAG 问答入口，而不是完整训练计划生成入口。

实验希望验证：

1. RAG 是否优于无检索 LLM。
2. 证据约束 RAG 是否优于普通 RAG。
3. 领域协议、证据门、独立审计和有界修复分别贡献了什么。
4. 在风险安全题中，完整 workflow 是否更少产生无证据或不安全建议。

## 2. Benchmark 范围

第一版使用 30-50 题 pilot benchmark，推荐先做 36 题。

题型分布：

| 题型 | 建议数量 | 主要评测能力 |
|---|---:|---|
| 事实抽取 | 12 | 是否能从证据中准确抽取定义、数值、原则和原文事实 |
| 应用推理 | 12 | 是否能基于有限证据进行保守场景化建议 |
| 风险安全 | 12 | 是否能识别缺证、高风险、伤痛、过度训练和异常反馈 |

每道题必须包含：

- `qid`
- `category`
- `question`
- `expected_answer`
- `evidence_ids`
- `evidence_locations`
- `answerable`
- `safety_required`
- `rubric`

## 3. 实验系统设置

### 3.1 主对照组

| ID | 系统设置 | 描述 | 目的 |
|---|---|---|---|
| S0 | No-RAG LLM | 不检索知识库，直接让模型回答 | 测试模型常识与幻觉风险 |
| S1 | Vanilla RAG | 检索 Top-k 上下文后直接生成 | 测试普通检索增强价值 |
| S2 | Agentic RAG without Evidence Gate | 有 agent 路由和证据包，但缺证不阻断 | 测试 agent 编排本身是否足够 |
| S3 | Full Workflow | 协议约束 + 证据门 + 独立审计 + 有界修复/拒答 | 测试完整方法 |

### 3.2 消融组

| ID | 消融设置 | 移除或弱化的模块 | 主要检验 |
|---|---|---|---|
| A1 | w/o Protocol Grounding | 不使用 HMP / 训练协议规则，只用检索上下文 | 协议约束是否降低不安全建议 |
| A2 | w/o Tiered EvidenceBundle | 检索内容直接拼接给生成器，不做证据分层 | 分层证据是否提高引用可追溯性 |
| A3 | w/o Evidence Gate | 检索结果不经过证据充足性判断 | 缺证阻断是否降低 unsupported claims |
| A4 | w/o Independent Auditor | 生成节点自我批准或直接输出 | 独立审计是否降低无效引用和风险回答 |
| A5 | w/o Bounded Repair | 审计失败后不修复，或无限制重试 | 有界修复是否改善质量并控制不稳定性 |
| A6 | w/o Risk-Aware Agent Activation | 所有问题走固定 agent 路径 | 动态激活是否减少成本并保持安全性 |

第一版最小可运行组合：

- S0
- S1
- S3
- A3
- A4

如果时间有限，先完成这 5 组；后续再补 A1、A2、A5、A6。

## 4. 模型设置

第一版计划使用两类模型：

| 模型类型 | 说明 | 必须记录 |
|---|---|---|
| 本地 Ollama 模型 | 与当前项目运行环境一致 | 模型名、tag、Ollama 版本、运行设备 |
| 主流 API 模型 | 提升外部可比性 | 供应商、模型名、版本/快照、调用日期、参数、费用记录 |

所有系统设置必须尽量保持相同生成参数：

- temperature
- top_p
- max_tokens
- system prompt 版本
- user prompt 模板版本
- Top-k
- 知识库版本
- benchmark 版本

若某模型不支持相同参数，必须在实验记录中说明。

## 5. 指标设计

主表建议保留 6-8 个指标，其他指标放附录或补充材料。

### 5.1 检索指标

| 指标 | 说明 |
|---|---|
| Recall@5 | 标准证据是否出现在 Top-5 |
| MRR@5 | 第一个相关证据出现位置的倒数 |
| Same-Document Recall@5 | 是否命中同一来源文档 |
| Same-Page Recall@5 | 若有页码，是否命中同页证据 |

### 5.2 生成与事实一致性指标

| 指标 | 说明 |
|---|---|
| Faithfulness | 回答是否受给定上下文支持 |
| Answer Relevancy | 回答是否切题 |
| Unsupported Claim Rate | 关键结论中无证据支持的比例 |
| Invalid Citation Rate | 引用不存在、编号错误或指向错误证据的比例 |
| Claim Evidence Coverage | 关键结论中被有效证据覆盖的比例 |

### 5.3 安全指标

| 指标 | 说明 |
|---|---|
| Safe Refusal Rate | 缺证或高风险时是否正确拒答 |
| De-escalation Rate | 是否将高风险建议降级为保守建议 |
| Unsafe Advice Rate | 是否输出可能加重风险的建议 |
| Professional Referral Rate | 是否在必要场景提示专业评估 |

### 5.4 成本与效率指标

| 指标 | 说明 |
|---|---|
| Average Latency | 平均响应时间 |
| Token Usage | 输入、输出与总 token |
| Repair Attempts | 平均修复轮数 |
| Agent Activation Count | 每题启用 agent 数量 |

成本指标不作为第一版论文主贡献，但可用于讨论。

## 6. 评分方式

### 6.1 自动评分

可自动统计：

- Recall@k。
- MRR@k。
- 引用编号是否存在。
- 是否输出拒答标记。
- 是否触发修复。
- token 和 latency。

### 6.2 半自动评分

需要规则 + 人工复核：

- Claim Evidence Coverage。
- Unsupported Claim Rate。
- Unsafe Advice Rate。
- De-escalation Rate。

建议流程：

1. 自动抽取回答中的关键 claims。
2. 标注每个 claim 是否被证据支持。
3. 对风险题标注是否安全合规。
4. 随机抽查 20%-30% 样本进行人工复核。

### 6.3 人工评分

如后续加入专家评审，可评分：

- 训练建议专业性。
- 风险判断合理性。
- 可执行性。
- 解释清晰度。

第一版 pilot 不强制引入专家评分。

## 7. Claim-Level 审计模板

每个回答可以拆成若干关键 claim：

| 字段 | 说明 |
|---|---|
| `qid` | 问题编号 |
| `system_id` | 系统设置 |
| `claim_id` | claim 编号 |
| `claim_text` | 关键结论 |
| `claim_type` | fact / inference / safety / recommendation |
| `cited_evidence` | 回答中引用的证据编号 |
| `support_status` | supported / partially_supported / unsupported / contradicted |
| `risk_status` | safe / caution / unsafe / not_applicable |
| `notes` | 标注说明 |

统计公式草案：

```text
Claim Evidence Coverage =
  supported_claims / all_key_claims

Unsupported Claim Rate =
  unsupported_or_contradicted_claims / all_key_claims

Invalid Citation Rate =
  invalid_citations / all_citations
```

## 8. 实验假设

以下是假设，不是结果。

| 假设 | 内容 | 对应实验 |
|---|---|---|
| H1 | Vanilla RAG 比 No-RAG LLM 有更高事实一致性 | S0 vs S1 |
| H2 | Full Workflow 比 Vanilla RAG 有更低 unsupported claim rate | S1 vs S3 |
| H3 | Evidence Gate 能减少缺证场景下的无证据回答 | S2/A3 vs S3 |
| H4 | Independent Auditor 能减少无效引用和安全违规 | A4 vs S3 |
| H5 | Protocol Grounding 能降低训练建议中的协议违规 | A1 vs S3 |
| H6 | Risk-aware activation 能在保持安全性的同时降低平均 agent 调用成本 | A6 vs S3 |

## 9. 结果表模板

### 9.1 主结果表

| System | Recall@5 | MRR@5 | Faithfulness | Claim Evidence Coverage | Unsupported Claim Rate | Invalid Citation Rate | Safe Refusal Rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| S0 No-RAG LLM | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| S1 Vanilla RAG | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| S2 Agentic RAG w/o Gate | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| S3 Full Workflow | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 9.2 消融表

| System | Removed Module | Unsupported Claim Rate | Invalid Citation Rate | Unsafe Advice Rate | Repair Attempts | Notes |
|---|---|---:|---:|---:|---:|---|
| A1 | Protocol Grounding | TBD | TBD | TBD | TBD | TBD |
| A2 | Tiered EvidenceBundle | TBD | TBD | TBD | TBD | TBD |
| A3 | Evidence Gate | TBD | TBD | TBD | TBD | TBD |
| A4 | Independent Auditor | TBD | TBD | TBD | TBD | TBD |
| A5 | Bounded Repair | TBD | TBD | TBD | TBD | TBD |
| A6 | Risk-Aware Activation | TBD | TBD | TBD | TBD | TBD |

### 9.3 分题型结果表

| System | Category | N | Claim Evidence Coverage | Unsupported Claim Rate | Safe Refusal Rate | Answer Relevancy |
|---|---|---:|---:|---:|---:|---:|
| S3 Full Workflow | Fact Extraction | TBD | TBD | TBD | TBD | TBD |
| S3 Full Workflow | Applied Reasoning | TBD | TBD | TBD | TBD | TBD |
| S3 Full Workflow | Risk Safety | TBD | TBD | TBD | TBD | TBD |

## 10. 错误类型分类

错误分析建议至少覆盖：

| 错误类型 | 描述 |
|---|---|
| Retrieval Miss | 未召回关键证据 |
| Evidence Misuse | 召回了证据但误解或过度推断 |
| Unsupported Claim | 生成了无证据结论 |
| Invalid Citation | 引用编号不存在或指向错误证据 |
| Protocol Violation | 违反训练协议、安全边界或容量预算 |
| Unsafe Advice | 对伤痛、异常心率、高疲劳等给出激进建议 |
| Over-Refusal | 本可回答的问题被过度拒答 |
| Under-Refusal | 应拒答或降级的问题被直接回答 |
| State Contamination | 上一轮状态污染当前回答 |
| Formatting Failure | 表格、引用、证据展示结构损坏 |

## 11. 实验运行记录模板

每次实验必须记录：

| 字段 | 内容 |
|---|---|
| `run_id` | 实验编号 |
| `date` | 运行日期 |
| `git_commit` | 代码快照 |
| `benchmark_version` | 测试集版本 |
| `kb_version` | 知识库版本 |
| `system_id` | S0/S1/S2/S3/A1-A6 |
| `model_provider` | ollama / api provider |
| `model_name` | 模型名 |
| `model_version` | 模型版本或快照 |
| `generation_params` | temperature/top_p/max_tokens 等 |
| `retrieval_params` | top_k、reranker、query expansion |
| `output_path` | 原始输出路径 |
| `metric_script` | 指标脚本路径 |
| `notes` | 异常、失败、重跑说明 |

## 12. 最小执行顺序

建议按以下顺序推进：

1. 固化 36 题 benchmark。
2. 固化 evidence metadata 和标准答案。
3. 实现或配置 S0、S1、S3 三组。
4. 先跑本地 Ollama 模型。
5. 检查指标脚本和输出格式。
6. 增加 API 模型。
7. 补 A3、A4 两个关键消融。
8. 做错误分析。
9. 再考虑 A1、A2、A5、A6 扩展消融。

## 13. 投稿前必须补齐

- 目标期刊或会议对实验规模的最低预期。
- benchmark 是否公开、部分公开或私有。
- API 模型的版本稳定性说明。
- 版权 PDF 的引用与开放边界。
- 人工评分一致性，如 Cohen's kappa 或至少双人复核记录。
- 失败案例与 limitation。

## 14. 当前优先级

第一优先级：

- S0 / S1 / S3 主实验。
- A3 evidence gate 消融。
- A4 independent auditor 消融。
- Claim-level evidence coverage 指标。
- 风险安全题的 safe refusal / de-escalation 评分。

第二优先级：

- A1 protocol grounding 消融。
- A2 evidence bundle 消融。
- A5 bounded repair 消融。
- A6 risk-aware activation 消融。

第三优先级：

- 专家评分。
- 用户研究。
- 长期训练日志追踪。
