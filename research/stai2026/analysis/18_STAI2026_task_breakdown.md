# STAI 2026 Task Breakdown

## 0. 当前主线

论文定位：

> Evidence-Gated Audit-and-Repair Agentic RAG for safety-sensitive advisory tasks, evaluated on endurance training advice.

当前策略：

- 方法抽象成通用框架：Evidence-Gated Audit-and-Repair Agentic RAG。
- 实验落在单领域 pilot：endurance training / marathon advice。
- 不夸大泛化结论，只在 discussion 中说明可迁移到 broader safety-sensitive wellness advice。

## 1. Milestone 总览

| Milestone | 目标 | 状态 | 主要产物 |
|---|---|---|---|
| M1 Evidence Base | 补足关键证据覆盖 | todo | 证据补充表、更新后的 benchmark KB |
| M2 S3 Full Run | 跑完整 15 题 S3 | todo | S3 outputs/metadata/trace |
| M3 Review & Metrics | 统一复核 S0/S1/S1b/S3 | todo | reviewed annotations、metrics |
| M4 Ablation | 验证 agent workflow 组件贡献 | todo | A3/A4/A5 输出与指标 |
| M5 Paper Draft | 形成 STAI 6 页短文 | todo | paper outline、section draft、tables |

## 2. M1 Evidence Base

### T1.1 证据缺口列表

目标：把 S1/S1b/S3 暴露出的证据缺口转成可补充清单。

输入：

- `docs/paper_project/16_STAI2026_current_stage_summary.md`
- `docs/paper_project/17_STAI2026_S3_smoke_summary.md`
- S1/S1b/S3 retrieved contexts

输出：

- `docs/paper_project/19_evidence_gap_to_fill.md`

验收标准：

- 至少覆盖 3 类缺口：training intensity distribution、heat illness / hot weather safety、cardiovascular red flags。
- 每个缺口包含：问题 qid、缺失证据类型、候选来源、是否必须加入 benchmark KB。

优先级：P0

### T1.2 补充证据来源

目标：为缺口补充可靠来源，不编造文献或页码。

输出：

- 更新 `07_benchmark专用证据库候选文献.md`
- 更新 `08_v0.1证据段落抽取表.md`

验收标准：

- 每条新增 evidence 有来源、可定位页码/段落或官方网页锚点。
- 无法定位原文的来源不得进入 verified evidence。

优先级：P0

### T1.3 构建或整理 benchmark KB

目标：让 S3 的 Evidence Gate 能检索到 benchmark 需要的核心证据。

输出：

- benchmark 专用 KB 或明确的 evidence bundle 文件
- KB 构建记录

验收标准：

- P001-P015 每题至少有一个可定位 evidence source。
- 风险题必须优先使用官方/权威医学或赛事安全来源。

优先级：P0

## 3. M2 S3 Full Run

### T2.1 修正 S3 smoke 中发现的问题

目标：让 S3 full run 更稳定。

需要修正：

- Evidence Gate 的 `missing_evidence` 字段语义收紧：不要把“检索到但不足”的 chunk 当作缺失证据。
- P007 答案中 “中等强度跑步” 改为更准确的 “submaximal intensities / specific running speeds”。
- Auditor JSON 失败时加入重试或 fallback。

输出：

- 更新 `scripts/run_stai_s3_full_workflow.py`

验收标准：

- `python -m py_compile scripts/run_stai_s3_full_workflow.py` 通过。
- S3 smoke 仍能跑通 P007/P014/P011。

优先级：P0

### T2.2 S3 full 15 题运行

目标：跑完整 S3 trace。

输出：

- `docs/paper_project/runs/stai_s3_full_workflow_qwen2_5_full01/outputs.jsonl`
- `metadata.json`

验收标准：

- 15 rows、15 unique qids。
- 每条都有：retrieved_contexts、evidence_gate、risk_gate、draft_generation、audit、repair、final_answer、final_status。
- 无空 final_answer。

优先级：P0

### T2.3 S3 full run 总结

输出：

- `docs/paper_project/20_STAI2026_S3_full_run_summary.md`

验收标准：

- 对比 S1/S1b 的拒答、可答、风险降级、引用格式。
- 明确哪些结果可用于论文，哪些还需人工复核。

优先级：P1

## 4. M3 Review & Metrics

### T3.1 统一生成 S3 codex-reviewed 标注

输出：

- `stai2026_claim_annotation_s3_codex_reviewed_v0.1.jsonl`

验收标准：

- 15 rows。
- 每条至少一个 claim 或明确 refusal/safety claim。
- safety_required=true 的题必须填 response_safety。

优先级：P0

### T3.2 合并 S0/S1/S1b/S3 指标

输出：

- `stai2026_claim_annotation_codex_reviewed_with_s3_v0.1.jsonl`
- `stai2026_claim_metrics_codex_reviewed_with_s3_v0.1.json`

验收标准：

- by_system 包含 S0/S1/S1b/S3。
- 指标解释不把 `not_applicable` 误读为成功。

优先级：P0

### T3.3 人工抽查清单

目标：降低 Codex-reviewed 偏差风险。

输出：

- `docs/paper_project/21_human_spotcheck_checklist.md`

验收标准：

- 至少列出 10 条必须人工确认的记录。
- 优先覆盖：S3 answered、S3 refused、S1b P007、风险题。

优先级：P1

## 5. M4 Ablation

### T4.1 A3 w/o Evidence Gate

目标：验证 Evidence Gate 是否降低 unsupported claim。

实现：

- 保留 retrieval、generation、auditor、repair。
- 不做 evidence_gate 阻断。

输出：

- `run_stai_a3_without_evidence_gate.py` 或 S3 runner 参数化版本。

验收标准：

- 至少跑 15 题。
- 可与 S3 对齐比较 unsupported claim、unsafe advice、invalid citation。

优先级：P1

### T4.2 A4 w/o Independent Auditor

目标：验证 auditor 是否减少无效引用和不安全建议。

实现：

- 保留 evidence_gate 和 risk_gate。
- 生成后不审计，直接输出。

优先级：P1

### T4.3 A5 w/o Repair

目标：验证 repair/refusal 是否把审计失败转成安全输出。

实现：

- 保留 evidence_gate、risk_gate、auditor。
- audit 失败后不修复，只记录失败并输出 draft。

优先级：P2

## 6. M5 Paper Draft

### T5.1 论文结构

建议结构：

1. Introduction
2. Related Work
3. Method: Evidence-Gated Audit-and-Repair Agentic RAG
4. Pilot Benchmark
5. Experiments
6. Findings and Failure Analysis
7. Limitations
8. Conclusion

输出：

- `docs/paper_project/22_STAI2026_paper_outline.md`

优先级：P0

### T5.2 图表

必需图表：

- Workflow diagram：retrieval → evidence gate → risk gate → generator → auditor → repair/refusal
- Experiment table：S0/S1/S1b/S3/A3/A4/A5
- Metrics table：evidence coverage、unsupported rate、safe de-escalation、invalid citation
- Failure case table：P007、P011、P014

输出：

- `docs/paper_project/23_STAI2026_tables_and_figures_plan.md`

优先级：P1

### T5.3 正文草稿

输出：

- `docs/paper_project/24_STAI2026_short_paper_draft.md`

验收标准：

- 不写虚构结果。
- 所有数值来自已保存 metrics。
- 所有文献来自 verified bibliography。

优先级：P1

## 7. 推荐执行顺序

立即下一步：

1. T2.1 修正 S3 runner。
2. T2.2 跑 S3 full 15 题。
3. T3.1/T3.2 生成 S3 标注和合并指标。
4. T1.1 反向整理证据缺口。
5. T5.1 写 paper outline。

原因：

- S3 是论文核心创新，必须先有 full run。
- 证据缺口可以根据 S3 full trace 更精确地补。
- outline 越早固定，后续实验不会发散。

## 8. 决策点

如果 S3 full 运行后仍大量 refused，有两条路线：

- 路线 A：先补证据库，再重跑 S3。
- 路线 B：把拒答能力作为核心发现，强调 evidence insufficiency detection 和 safe de-escalation。

当前建议：优先路线 A，但保留路线 B 作为论文叙事备选。
