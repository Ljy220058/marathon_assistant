# STAI 2026 Claim-Level 30 条草案汇总

## 1. 生成范围

本轮已将 claim-level 标注从模板扩展到 30 条 response：

- S0 No-RAG LLM：15 条
- S1 Vanilla RAG：15 条
- 数据集：`stai2026_pilot_benchmark_v0.1.jsonl`
- 草案文件：`docs/paper_project/stai2026_claim_annotation_machine_draft_v0.1.jsonl`
- 草案指标：`docs/paper_project/stai2026_claim_metrics_machine_draft_v0.1.json`

## 2. 重要边界

本轮结果是 `machine_draft_needs_review`，不是最终人工标注结果，不能直接写成论文结论。

标注时执行了一个保守后处理规则：如果某条 response 没有可见检索上下文，则其事实性或建议性 claim 不能被计为 `supported`。因此 S0 的 claim evidence coverage 在草案指标中不会因为模型常识回答而被加分。

引用统计也采用确定性后处理：只统计答案文本中的显式方括号引用；不会把 prompt 中的检索上下文当作答案引用。

## 3. 草案校验

结构校验结果：

- JSONL rows：30
- unique `(system_id, qid)` pairs：30
- annotation_status：`machine_draft_needs_review`
- empty claim records：0

## 4. 草案指标快照

以下仅用于发现问题和安排人工复核优先级，不代表最终实验结果。

| system_id | responses | claims | supported | unsupported | not_applicable | claim_evidence_coverage | unsupported_claim_rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| S0 | 15 | 31 | 0 | 23 | 8 | 0.0 | 1.0 |
| S1 | 15 | 15 | 0 | 1 | 14 | 0.0 | 1.0 |

| system_id | risk_safety_responses | safe_deescalation_rate | unsafe_advice_rate | professional_referral_rate |
|---|---:|---:|---:|---:|
| S0 | 6 | 0.8333 | 0.1667 | 0.3333 |
| S1 | 6 | 0.0 | 0.25 | 1.0 |

## 5. 当前观察

S1 的草案中大量 claim 被标为 `not_applicable`，主要因为 S1 回答经常选择“检索证据不足以回答”。这可能是真实反映，也可能受到本次 S1 运行中 `context_max_chars=120` 的上下文截断影响。后续人工复核时，应重点检查 S1 是否过度拒答，以及完整 chunk 是否能支持原问题。

S0 的草案中许多答案包含常识性训练建议，但由于没有可见检索证据，按 evidence grounding 指标应先视为 unsupported。后续若要评估 factual correctness，应单独设置事实正确性指标，不能和 evidence grounding 混在一起。

## 6. 下一步

1. 人工复核全部 30 条草案，尤其是 S1 的 `not_applicable` 和风险题的 `safe_deescalation`。
2. 对 S1 的关键问题回查完整 `vector_kb/chunks.jsonl`，判断 120 字符截断是否导致证据不足。
3. 将复核后的文件另存为 `stai2026_claim_annotation_human_reviewed_v0.1.jsonl`。
4. 用 `scripts/compute_stai_claim_metrics.py --input ...` 重新生成最终指标。
