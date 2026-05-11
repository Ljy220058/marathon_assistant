# STAI Experimental Setup v0.1

This draft records the paper-facing experimental setup. It separates primary runs from supplementary diagnostics and avoids overstating cross-model coverage.

## 1. Systems

The main evaluated system is S3, the full evidence-gated audit-and-repair workflow.

S3 includes:

- request-level pre-gate filter;
- evidence retrieval and/or curated gold evidence loading;
- evidence gate;
- risk gate;
- evidence-constrained generation;
- independent grounding auditor;
- bounded citation/grounding repair;
- final answer or refusal.

The paper should compare this workflow against diagnostic variants rather than claiming broad superiority over all possible RAG systems.

## 2. Evidence Modes

| evidence mode | description | paper role |
|---|---|---|
| `gold_only` | curated benchmark evidence only | curated-evidence upper bound |
| `retrieval_only` | vector-retrieved knowledge-base contexts only | retrieval-noise diagnostic |
| `retrieval_plus_gold` | retrieved contexts plus curated benchmark evidence | main full-workflow setting |

The 100-question primary run uses `retrieval_plus_gold`.

The older 50-question v0.2 evidence-mode comparison remains useful as a supporting diagnostic. It should be clearly labeled as a v0.2 comparison if included in the Results section.

## 3. Models

Primary local model:

- `qwen2.5:latest`

Supplementary model:

- `llama3:latest`

Model use:

| run type | model | role |
|---|---|---|
| 100-question main benchmark | `qwen2.5:latest` | primary result |
| 30-question safety stress | `qwen2.5:latest` | primary stress result |
| 30-question safety stress | `llama3:latest` | cross-model stress sanity check |
| 40-question main subset | `llama3:latest` | supplementary main-benchmark sanity check |

Boundary:

- this is not a full multi-model evaluation;
- llama3 results are used as a sanity check, not as evidence of broad model generalization.

## 4. Primary Runs

### 4.1 Main 100-Question Run

Run:

- `docs/paper_project/runs/stai_s3_rpg_100q_v03_qwen_run01`

Settings:

| field | value |
|---|---|
| system | S3 / Full Workflow |
| dataset | `docs\paper_project\stai_benchmark_v0.3_100_question_draft.jsonl` |
| model | `qwen2.5:latest` |
| evidence mode | `retrieval_plus_gold` |
| ablation mode | `full` |
| pre-gate mode | `off` |
| prompt template | `s3_full_workflow_v0.2` |
| retrieval top-k | 5 |
| context max chars | 500 |
| gold context max chars | 800 |
| num_ctx | 4096 |
| num_batch | 4 |
| num_predict | 300 |
| elapsed_sec | 2331.709 |

The pre-gate is off in this run because the main benchmark is intended to test ordinary evidence and risk gating behavior without the stress-specific hardening layer.

### 4.2 Safety Stress, Qwen

Run:

- `docs/paper_project/runs/stai_safety_stress_30q_hardened_v04_run03`

Settings:

| field | value |
|---|---|
| dataset | `docs\paper_project\stai_safety_stress_benchmark_v0.2_30_question.jsonl` |
| model | `qwen2.5:latest` |
| evidence mode | `retrieval_only` |
| ablation mode | `full` |
| pre-gate mode | `hardening_v0_4` |
| prompt template | `s3_full_workflow_v0.2` |
| elapsed_sec | 32.468 |

### 4.3 Safety Stress, Llama3

Run:

- `docs/paper_project/runs/stai_safety_stress_30q_hardened_v04_llama3_run03`

Settings:

| field | value |
|---|---|
| dataset | `docs\paper_project\stai_safety_stress_benchmark_v0.2_30_question.jsonl` |
| model | `llama3:latest` |
| evidence mode | `retrieval_only` |
| ablation mode | `full` |
| pre-gate mode | `hardening_v0_4` |
| prompt template | `s3_full_workflow_v0.2` |
| elapsed_sec | 14.808 |

## 5. Supplementary Main-Benchmark Sanity Check

Run:

- `docs/paper_project/runs/stai_s3_rpg_40q_v03_llama3_run01`

Settings:

| field | value |
|---|---|
| dataset | `docs\paper_project\stai_benchmark_v0.3_100_question_draft.jsonl` |
| model | `llama3:latest` |
| sample count | 40 |
| evidence mode | `retrieval_plus_gold` |
| ablation mode | `full` |
| pre-gate mode | `off` |
| prompt template | `s3_full_workflow_v0.2` |
| elapsed_sec | 578.799 |

Subset composition:

- 10 fact;
- 10 applied_reasoning;
- 10 risk_safety;
- 10 evidence_insufficient.

The subset is balanced by category and should be reported as supplementary evidence only.

## 6. Ablation and Evidence-Mode Diagnostics

### 6.1 v0.3 40-Question Ablation Subset

The main ablation evidence now comes from a balanced 40-question v0.3 subset:

| run | N | ablation_mode | answered | partial_answer | refused | designed-unanswerable refused | verified-answerable false refusal | citation repair |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| 40-qid slice from `stai_s3_rpg_100q_v03_qwen_run01` | 40 | `full` | 8 | 19 | 13 | 10 / 10 | 3 / 30 | 19 |
| `stai_ablation_no_gate_40q_v03_qwen_run02` | 40 | `no_gate` | 0 | 40 | 0 | 0 / 10 | 0 / 30 | 40 |
| `stai_ablation_no_audit_40q_v03_qwen_run01` | 40 | `no_audit` | 26 | 0 | 14 | 10 / 10 | 4 / 30 | 0 |
| `stai_ablation_no_repair_40q_v03_qwen_run01` | 40 | `no_repair` | 27 | 0 | 13 | 10 / 10 | 3 / 30 | 0 |

One earlier diagnostic run, `stai_ablation_no_gate_40q_v03_qwen_run01`, used the default old benchmark evidence map and should not be reported as a paper result.

### 6.2 Older v0.2 Ablations

Existing 50-question v0.2 ablations:

| run | N | ablation_mode | answered | partial_answer | refused | designed-unanswerable refused | verified-answerable false refusal | citation repair |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| `stai_ablation_no_gate_50q_run01` | 50 | `no_gate` | 3 | 47 | 0 | 0 / 5 | 0 / 45 | 47 |
| `stai_ablation_no_audit_50q_run01` | 50 | `no_audit` | 43 | 0 | 7 | 5 / 5 | 2 / 45 | 0 |
| `stai_ablation_no_repair_50q_run01` | 50 | `no_repair` | 43 | 0 | 7 | 5 / 5 | 2 / 45 | 0 |

Existing 50-question v0.2 evidence-mode comparison:

| evidence mode | answered | partial_answer | refused | designed-unanswerable refused | verified-answerable false refusal | citation repair |
|---|---:|---:|---:|---:|---:|---:|
| `gold_only` | 18 | 27 | 5 | 5 / 5 | 0 / 45 | 27 |
| `retrieval_only` | 8 | 15 | 27 | 5 / 5 | 22 / 45 | 15 |
| `retrieval_plus_gold` | 14 | 29 | 7 | 5 / 5 | 2 / 45 | 29 |

These tables should be treated as diagnostic support, not as the primary result, unless rerun on the v0.3 100-question benchmark.

## 7. Metrics

Primary output statuses:

- `answered`: answer passes gate and audit;
- `partial_answer`: answer released after bounded citation or grounding repair;
- `refused`: system refuses due to insufficient evidence, safety risk, or pre-gate policy.

Refusal diagnostics:

- designed-unanswerable refused;
- verified-answerable false refusal;
- refused qids.

Grounding diagnostics:

- citation repair count;
- audit status;
- repair status.

Safety diagnostics:

- safety-stress refusal count;
- pre-gate rule counts;
- ordinary gate refusal after pre-gate non-trigger.

Runtime diagnostics:

- elapsed time;
- average latency;
- average evidence contexts;
- average gold contexts;
- average retrieved contexts.

## 8. Reproducibility Commands

Benchmark validation:

```bat
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe scripts\validate_stai_benchmark_questions.py --dataset docs\paper_project\stai_benchmark_v0.3_100_question_draft.jsonl --expected-count 100
```

Safety-stress validation:

```bat
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe scripts\validate_stai_safety_stress_benchmark.py --dataset docs\paper_project\stai_safety_stress_benchmark_v0.2_30_question.jsonl --expected-count 30
```

Benchmark KB validation:

```bat
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe scripts\validate_benchmark_kb.py --evidence-items docs\paper_project\benchmark_kb_v0.2\evidence_items_v0.1.jsonl --qid-map docs\paper_project\benchmark_kb_v0.2\qid_to_gold_evidence_v0.2.json
```

Pre-gate and ablation tests:

```bat
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -m pytest tests\test_stai_s3_pre_gate.py tests\test_stai_s3_ablation_modes.py -q
```

## 9. Disclosure Boundary

The experiment should be described as local, reproducible, and diagnostic:

> We report a local workflow-level diagnostic evaluation using Ollama-hosted open models. The primary result uses qwen2.5 on the full 100-question benchmark. Llama3 is included for safety-stress and subset sanity checks, not as a comprehensive multi-model study.

Avoid:

- "state-of-the-art model comparison";
- "general model robustness";
- "deployment-ready clinical or coaching evaluation";
- "expert-validated benchmark".
