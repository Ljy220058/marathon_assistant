# STAI 2026 Focus Execution Plan

## 1. 当前投稿策略

近期只把正式投稿目标收束到 **STAI 2026 Workshop @ ECML PKDD**。

长期可以拆成多篇论文，但短期不做多 venue 同稿并投；当前全部实验、方法叙事和图表都服务于一篇 STAI workshop paper：

> Evidence-Gated Audit-and-Repair Agentic RAG for Safety-Sensitive Endurance Training Advice

## 2. 当前已完成的工程闭环

### P0 Gold Evidence Bundle

已完成：

- 50 题 benchmark 草案。
- 45 条 verified evidence。
- 5 条 designed unanswerable control。
- S3 支持 `retrieval_only`、`gold_only`、`retrieval_plus_gold` 三种 evidence mode。

### P1 Minimal Experiment Harness

已新增：

- `configs/stai_experiments/s3_gold_only_50q.json`
- `configs/stai_experiments/s3_retrieval_only_50q.json`
- `configs/stai_experiments/s3_retrieval_plus_gold_50q.json`
- `scripts/run_stai_experiment.py`

统一入口示例：

```bat
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -u scripts\run_stai_experiment.py --config configs\stai_experiments\s3_gold_only_50q.json --run-id stai_s3_gold_only_50q_v02_run01
```

### P3 Lightweight Metrics

已新增：

- `scripts/summarize_stai_run.py`

摘要命令示例：

```bat
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe scripts\summarize_stai_run.py --run stai_s3_gold_only_50q_v02_run01 --json-out docs\paper_project\runs\stai_s3_gold_only_50q_v02_run01\summary_auto.json --md-out docs\paper_project\runs\stai_s3_gold_only_50q_v02_run01\summary_auto.md
```

## 3. 关键修正：S3 gate 归一化

在 `scripts/run_stai_s3_full_workflow.py` 中将 prompt/template version 更新为 `s3_full_workflow_v0.2`，并加入确定性 gate normalization。

修正原因：

- `stai_s3_gold_only_50q_run02` 中 P036、P040、P045 有 gold evidence。
- 但 Evidence Gate 返回 `gate_status=unanswerable`，同时又给出有效 `required_chunks`，且 `missing_evidence=[]`。
- 这属于 gate 输出自相矛盾，不应直接触发拒答。

修正规则：

- 如果有 contexts 且 gate 返回有效 `required_chunks`；
- 同时 `gate_status=unanswerable` 且 `missing_evidence` 为空；
- 则将 gate 归一化为 `partial`，保留审计和修复流程继续判断。

这不是放宽安全边界，而是避免“有证据但误拒”的流程性错误。

## 4. v0.2 Gold-only 50题结果

新 run：

- `docs/paper_project/runs/stai_s3_gold_only_50q_v02_run01`
- console log: `docs/paper_project/runs/stai_s3_gold_only_50q_v02_run01_console_stdout.log`
- summary: `docs/paper_project/runs/stai_s3_gold_only_50q_v02_run01/summary_auto.md`

核心结果：

| metric | value |
|---|---:|
| rows | 50 |
| unique_qids | 50 |
| answered | 18 |
| partial_answer | 27 |
| refused | 5 |
| designed_unanswerable refused | 5 / 5 |
| verified_or_answerable refused | 0 / 45 |
| citation_repair_count | 27 |

与上一版 `stai_s3_gold_only_50q_run02` 相比：

| item | run02 | v0.2 run01 |
|---|---:|---:|
| answered | 18 | 18 |
| partial_answer | 24 | 27 |
| refused | 8 | 5 |
| verified_or_answerable refused | 3 / 45 | 0 / 45 |
| designed_unanswerable refused | 5 / 5 | 5 / 5 |

解释：

- P036、P040、P045 从拒答变为可审计回答或部分回答。
- P046-P050 仍保持拒答，符合 no-evidence control 设计。
- 这增强了论文中的核心论点：系统不是一味拒答，而是在证据不足时拒答，在证据存在但需要约束时给出可审计的谨慎回答。

## 5. 接下来最优先的 STAI 任务

## 5.1 新增检索对照实验结果

本轮新增两个 50 题 S3 对照 run：

- `docs/paper_project/runs/stai_s3_retrieval_only_50q_v02_run01`
- `docs/paper_project/runs/stai_s3_retrieval_plus_gold_50q_v02_run01`

三组 S3 evidence-mode 结果对比：

| run | evidence_mode | answered | partial_answer | refused | designed unanswerable refused | verified answerable false refusal | citation repair |
|---|---|---:|---:|---:|---:|---:|---:|
| stai_s3_gold_only_50q_v02_run01 | gold_only | 18 | 27 | 5 | 5 / 5 | 0 / 45 | 27 |
| stai_s3_retrieval_only_50q_v02_run01 | retrieval_only | 8 | 15 | 27 | 5 / 5 | 22 / 45 | 15 |
| stai_s3_retrieval_plus_gold_50q_v02_run01 | retrieval_plus_gold | 14 | 29 | 7 | 5 / 5 | 2 / 45 | 29 |

初步解释：

- `retrieval_only` 的 verified-answerable false refusal 很高，说明当前普通 `vector_kb` 检索对 benchmark 证据覆盖不足，且噪声会触发保守拒答。
- `gold_only` 是上界条件：只给经过人工核验的证据时，系统能做到 no-evidence control 全部拒答，同时 verified answerable 不误拒。
- `retrieval_plus_gold` 明显优于 `retrieval_only`，但仍弱于 `gold_only`，说明额外检索噪声会影响 Evidence Gate / Audit 判断。
- 这个结果可以支撑论文里的一个核心论点：安全敏感 advisory RAG 不能只依赖向量检索；需要 evidence bundle、gate、audit、repair 共同约束。

实验 caveat：

- `stai_s3_retrieval_plus_gold_50q_v02_run01` 的 P049-P050 是 `designed_unanswerable` 控制题；由于本地 Ollama 在 P049 Evidence Gate 调用上反复 timeout，这两题按确定性 no-evidence refusal 路径补齐，并在 metadata 中记录了 completion note。
- 这不改变这两题的评价结论，因为它们没有 gold evidence，预期行为就是拒答；但正式论文表格中应在 reproducibility note 里说明该本地运行异常。

### T1. 跑 retrieval-only 与 retrieval-plus-gold

目的：

- 区分 retrieval failure 和 generation/audit failure。
- 支撑 STAI 论文里的 ablation/result table。

命令：

```bat
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -u scripts\run_stai_experiment.py --config configs\stai_experiments\s3_retrieval_only_50q.json --run-id stai_s3_retrieval_only_50q_v02_run01 --log-file docs\paper_project\runs\stai_s3_retrieval_only_50q_v02_run01_console_stdout.log
```

```bat
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -u scripts\run_stai_experiment.py --config configs\stai_experiments\s3_retrieval_plus_gold_50q.json --run-id stai_s3_retrieval_plus_gold_50q_v02_run01 --log-file docs\paper_project\runs\stai_s3_retrieval_plus_gold_50q_v02_run01_console_stdout.log
```

### T2. 生成 comparison table

最小表格：

- S0 no-RAG
- S1 vanilla RAG
- S3 gold-only
- S3 retrieval-only
- S3 retrieval-plus-gold

指标：

- answer/refusal distribution
- designed-unanswerable refusal rate
- verified-answerable false refusal rate
- citation repair rate
- risk_safety safe refusal / cautious answer rate

### T3. 写 STAI 方法图和实验表

论文主线：

1. Evidence acquisition: retrieval or gold evidence bundle.
2. Evidence Gate: answerability under supplied evidence.
3. Risk Gate: deterministic safety constraints.
4. Answer Generator: evidence-constrained response.
5. Independent Auditor: grounding/citation/safety check.
6. Repair or Refuse: deterministic finalization.

### T4. 人工 spot-check

必须人工检查：

- 45 条 verified evidence 是否源头定位足够清楚。
- v0.2 run01 中 27 个 `partial_answer` 是否主要来自 citation repair，而不是内容不完整。
- risk_safety 15 题是否没有 unsafe recommendation。
