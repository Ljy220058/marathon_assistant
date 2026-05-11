# STAI 2026 当前阶段汇总

## 1. 已完成

### S0 No-RAG

- run_id：`stai_s0_norag_qwen2_5_20260510_run01`
- 样本：15
- 作用：无检索基线。

### S1 Vanilla RAG context120

- run_id：`stai_s1_vanilla_rag_qwen2_5_after_reboot_full01`
- 样本：15
- Top-k：5
- `context_max_chars`：120
- 观察：大量回答为“检索证据不足”，说明短上下文和检索覆盖共同限制了普通 RAG。

### S1b Vanilla RAG context500

- run_id：`stai_s1b_vanilla_rag_qwen2_5_context500_full01`
- 样本：15
- Top-k：5
- `context_max_chars`：500
- 观察：P007 能基于检索上下文给出 running economy 定义，但多数题仍为证据不足。说明增加上下文长度有帮助，但不能解决知识库覆盖和证据门控问题。

## 2. 当前复核文件

- S0/S1 Codex-reviewed 标注：`docs/paper_project/stai2026_claim_annotation_codex_reviewed_v0.1.jsonl`
- S1b Codex-reviewed 标注：`docs/paper_project/stai2026_claim_annotation_s1b_codex_reviewed_v0.1.jsonl`
- 合并标注：`docs/paper_project/stai2026_claim_annotation_codex_reviewed_with_s1b_v0.1.jsonl`
- 合并指标：`docs/paper_project/stai2026_claim_metrics_codex_reviewed_with_s1b_v0.1.json`

这些文件状态是 `codex_reviewed_needs_human_spotcheck`，不是最终人工标注结果。

## 3. Codex-reviewed 指标快照

| system_id | responses | supported_claims | unsupported_claims | not_applicable_claims | safe_deescalation_rate | invalid_citation_rate |
|---|---:|---:|---:|---:|---:|---:|
| S0 | 15 | 0 | 13 | 2 | 1.0 | null |
| S1 | 15 | 0 | 0 | 15 | 0.3333 | null |
| S1b | 15 | 1 | 0 | 14 | 0.1667 | 1.0 |

解释：

- S0 的安全建议往往合理，但没有检索证据，因此 evidence grounding 不加分。
- S1 的证据不足拒答很多，claim evidence coverage 无法计算。
- S1b 只在 P007 形成一个可支持 claim，但引用格式是 `[2, p.1]`，不符合我们要求的 `[chunk_id, p.page]`，因此 invalid citation rate 为 1.0。

## 4. 设计结论

当前结果支持继续做 S3 Full Workflow：

- Vanilla RAG 对证据不足很敏感，容易拒答。
- 增大上下文可以改善个别事实题，但不能系统解决安全题和引用格式。
- S3 的 Evidence Gate + Independent Auditor + Repair 可以直接针对这些失败模式。

## 5. 下一步

1. 按 `15_STAI2026_S3_full_workflow_protocol.md` 实现 `run_stai_s3_full_workflow.py`。
2. 优先在 3 条样本上 smoke：P007、P014、P011。
3. 通过后跑 15 条 S3。
4. 使用同一套 Codex-reviewed 标注规则生成 S3 指标。
