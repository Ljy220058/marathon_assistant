# S3 Gold-only 50题运行总结

## 0. 目的

本文件记录 P0 Gold Evidence Bundle 接入后的第一轮完整 S3 gold-only 运行结果。

本轮运行的目的不是报告最终论文指标，而是验证：

- 50 题 benchmark 是否能被 S3 runner 完整读取。
- `benchmark_kb` gold evidence 是否能按 qid 注入 Evidence Gate。
- `designed_unanswerable` 控制题是否能触发拒答。
- Auditor / Repair 是否能发现并修复缺失或不规范 citation。

## 1. 运行配置

| 字段 | 值 |
|---|---|
| run_id | `stai_s3_gold_only_50q_run02` |
| system_id | `S3` |
| evidence_mode | `gold_only` |
| dataset | `docs/paper_project/stai_benchmark_v0.2_50_question_draft.jsonl` |
| benchmark_kb | `docs/paper_project/benchmark_kb` |
| qid map | `docs/paper_project/benchmark_kb/qid_to_gold_evidence_v0.1.json` |
| model | `qwen2.5:latest` |
| sample_count | 50 |
| elapsed_sec | 599.318 |
| outputs | `docs/paper_project/runs/stai_s3_gold_only_50q_run02/outputs.jsonl` |
| metadata | `docs/paper_project/runs/stai_s3_gold_only_50q_run02/metadata.json` |

说明：

- `run01` 因为预创建同名 run 目录失败，没有进入样本运行。
- `run03_p040_p050` 是补跑分段结果；后续分析以完整的 `run02` 为主。

## 2. 覆盖检查

| 检查项 | 结果 |
|---|---:|
| rows | 50 |
| unique_qids | 50 |
| missing_qids | 0 |

题型分布：

| category | 数量 |
|---|---:|
| fact | 15 |
| applied_reasoning | 15 |
| risk_safety | 15 |
| evidence_insufficient | 5 |

## 3. 运行结果快照

### 3.1 Final status

| final_status | 数量 |
|---|---:|
| answered | 18 |
| partial_answer | 24 |
| refused | 8 |

### 3.2 Category x final_status

| category | answered | partial_answer | refused |
|---|---:|---:|---:|
| fact | 7 | 8 | 0 |
| applied_reasoning | 6 | 9 | 0 |
| risk_safety | 5 | 7 | 3 |
| evidence_insufficient | 0 | 0 | 5 |

### 3.3 Evidence Gate

| gate_status | 数量 |
|---|---:|
| answerable | 34 |
| partial | 8 |
| unanswerable | 8 |

### 3.4 Audit / Repair

| audit_status | 数量 |
|---|---:|
| pass | 20 |
| repair_required | 26 |
| refuse_required | 4 |

| repair_action | 数量 |
|---|---:|
| none | 18 |
| repaired_invalid_or_missing_citations | 24 |
| refused_due_to_insufficient_evidence | 4 |
| refused_due_to_insufficient_evidence_with_safety_deescalation | 4 |

## 4. 关键观察

### 4.1 Gold Evidence Bundle 已经可运行

P001-P045 每题都有 gold evidence context，P046-P050 没有 gold evidence context。S3 runner 能正确区分这两类样本，并把上下文保存为：

- `retrieved_contexts`
- `gold_evidence_contexts`
- `evidence_contexts`

这说明 P0 的核心工程目标已经完成。

### 4.2 无证据控制题行为正确

以下 `designed_unanswerable` 题全部被拒答：

- STAI-P046
- STAI-P047
- STAI-P048
- STAI-P049
- STAI-P050

这对论文很重要：系统不是“永远给答案”，而是能在没有 gold evidence 时拒绝编造百分比、页码、诊断或确定性承诺。

### 4.3 Auditor / Repair 实际发挥作用

24 条最终输出经过 `repaired_invalid_or_missing_citations`。主要原因是模型常常能答出正确内容，但 citation 格式不符合要求，例如：

- 缺少 chunk_id citation。
- 只写裸 evidence id。
- 没有带 page 或 section。

这支持后续论文中的一个论点：仅靠 prompt 要求引用格式并不稳定，独立 audit 与确定性 repair 是必要组件。

### 4.4 三个可答题被拒答，需要诊断

以下题有 gold evidence，但最终仍然拒答：

| qid | category | 初步判断 |
|---|---|---|
| STAI-P036 | risk_safety | overtraining 相关 span 可能不足以支持具体训练调整，或 Evidence Gate 过保守 |
| STAI-P040 | risk_safety | illness / fever 场景的 evidence span 可能不够直接 |
| STAI-P045 | risk_safety | heat acclimatization 证据对“是否维持平时强度”支持不够直接 |

这三条不应简单视为失败。它们更像是 benchmark KB 与 Evidence Gate 的联合诊断点：

- 如果原 evidence span 确实太短，应补充更直接的 span。
- 如果 span 足够，应改进 Evidence Gate prompt 或 gold context 格式。
- 在正式指标中，应区分“保守拒答”与“错误拒答”。

## 5. 当前不能过度声称的内容

本轮不能直接声称：

- S3 已经优于 S0/S1/S1b。
- 所有回答都已人工验证正确。
- 45 条 evidence span 已经达到最终投稿引用质量。
- `partial_answer` 都是语义不完整答案。

原因：

- 当前只跑了 `gold_only`，还没有与 `retrieval_only` 和 `retrieval_plus_gold` 对比。
- citation repair 会把很多答案标成 `partial_answer`，这更像 workflow 过程状态，不等同于答案不可用。
- 还没有统一 claim-level metrics。
- 还没有人工 spot-check。

## 6. 下一步

建议顺序：

1. P1：做 Unified Experiment Harness 的最小版本，至少统一记录 `system_id`、`evidence_mode`、dataset、run config。
2. P3：做 gold-only run 的轻量 metrics 汇总，先区分 answered / partial / refused / citation repaired / designed_unanswerable refusal。
3. 针对 P036、P040、P045 做 evidence span spot-check。
4. 跑 `retrieval_only` 50题，分析真实 vector retrieval 与 gold evidence 的差距。
5. 跑 `retrieval_plus_gold`，观察混合证据模式是否提升 Evidence Gate 稳定性。
