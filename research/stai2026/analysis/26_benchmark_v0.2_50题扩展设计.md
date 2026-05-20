# STAI Benchmark v0.2 50题扩展设计

## 0. 目标

本文件把当前 15 题 pilot benchmark 扩展为 50 题研究基准草案，用于后续评估：

> Evidence-Gated Audit-and-Repair Agentic RAG in safety-sensitive endurance-training advice.

当前 v0.2 是“题目与证据需求草案 + 可运行 gold evidence bundle”，不是最终可投稿数据集。P001-P045 已完成 `verified_span` 登记，P046-P050 是故意设计的无证据控制题。正式写入论文前仍需人工 spot-check 页码、section、短 quote 和引用格式。

## 1. 设计原则

- 不为了凑数量编造文献、页码、引用或实验结果。
- 每道题必须绑定一个证据需求，即使该证据当前仍为 pending。
- 风险安全题优先使用官方指南、共识声明、系统综述或医学/运动科学权威来源。
- evidence-insufficient 题是刻意设计的控制题，用于评估系统是否能在证据不足时拒答或降级，而不是自由发挥。
- v0.2 不直接替代 v0.1 实验；v0.1 仍是当前已跑通的最小实验集。

## 2. 题型配比

| category | 数量 | 目的 |
|---|---:|---|
| fact | 15 | 定义、研究发现、概念边界 |
| applied_reasoning | 15 | 证据约束下的训练建议与外推边界 |
| risk_safety | 15 | 热病、心血管、疲劳、伤病、筛查等安全降级 |
| evidence_insufficient | 5 | 测试系统是否拒绝无证据的精确承诺、诊断或伪引用 |
| 合计 | 50 | 覆盖 grounding、safety、refusal、citation robustness |

## 3. 证据状态定义

| evidence_status | 含义 | 可否用于最终论文指标 |
|---|---|---|
| `verified_summary` | 已在 `08_v0.1证据段落抽取表.md` 标为 verified，但仍需迁移到 `benchmark_kb` 的精确 span | 可用于 pilot，但论文前仍需人工复核 |
| `verified_span` | 已在 `benchmark_kb/evidence_items_v0.1.jsonl` 登记可定位来源、section 和短证据 span | 可用于下一轮实验，但论文前建议人工 spot-check |
| `pending` | 已有候选来源或证据槽位，但尚未完成全文定位和 span 抽取 | 不可作为最终 gold evidence |
| `designed_unanswerable` | 故意设计的知识库不足/拒答控制题 | 可用于评估拒答，但必须在协议中说明 |

## 4. 新增覆盖方向

| 方向 | 题号范围 | 主要来源候选 |
|---|---|---|
| 世界级长跑训练特征 | STAI-P016 至 STAI-P018 | T09 |
| 训练负荷与疲劳监控 | STAI-P019 至 STAI-P021 | T10 |
| 力量训练与跑步表现 | STAI-P022 至 STAI-P024 | T13 |
| 训练负荷变化与跑步伤病 | STAI-P025 至 STAI-P030 | R05, R08 |
| ACSM 运动处方、taper、过度训练 | STAI-P031 至 STAI-P036 | T01, T07, R01 |
| IOC 负荷-伤病/疾病风险、运动前筛查 | STAI-P037 至 STAI-P042 | R02, R03, R12 |
| 跑步伤病综述与热病补充 | STAI-P043 至 STAI-P045 | R07, R10 |
| 证据不足控制题 | STAI-P046 至 STAI-P050 | 无 gold evidence |

## 5. 输出文件

- 机器可读草案：`docs/paper_project/stai_benchmark_v0.2_50_question_draft.jsonl`
- 结构校验脚本：`scripts/validate_stai_benchmark_questions.py`
- Gold evidence loader：`scripts/stai_benchmark_kb.py`
- S3 证据模式：`retrieval_only`、`gold_only`、`retrieval_plus_gold`

## 6. 使用边界

当前 v0.2 可以用于：

- 跑 S3 的 `gold_only` 与 `retrieval_plus_gold` 实验。
- 分析真实向量检索是否漏召回 gold evidence。
- 作为统一 runner 改造时的数据结构目标。

当前 v0.2 暂不应用于：

- 直接报告最终实验指标。
- 声称 50 题均有 verified gold evidence。
- 生成论文中的定量结论。

## 7. 下一步

1. 对 P001-P045 的 `verified_span` 做人工 spot-check，确认页码、section 与短 quote 在正式引用格式中可复现。
2. 将 `benchmark_kb` 升级为 v0.2 文件名，避免 v0.1 文件承载 50 题扩展后语义混乱。
3. 用 S3 runner 分别跑 `gold_only`、`retrieval_only` 和 `retrieval_plus_gold`，比较 evidence gate、audit 和 final_status 差异。
