# STAI Benchmark v0.3 Expansion Summary

This document records the benchmark expansion requested for the STAI paper project.

## 1. Main Benchmark

New dataset:

- `docs/paper_project/stai_benchmark_v0.3_100_question_draft.jsonl`

Scale and composition:

| category | count |
|---|---:|
| fact | 30 |
| applied_reasoning | 30 |
| risk_safety | 30 |
| evidence_insufficient | 10 |
| total | 100 |

Evidence status:

| evidence_status | count |
|---|---:|
| verified_span | 90 |
| designed_unanswerable | 10 |

The 50 new questions reuse existing verified benchmark evidence. No new paper, page number, DOI, or experimental result was invented.

## 2. Expanded Gold Evidence Map

New benchmark KB directory:

- `docs/paper_project/benchmark_kb_v0.2`

Files:

- `docs/paper_project/benchmark_kb_v0.2/evidence_items_v0.1.jsonl`
- `docs/paper_project/benchmark_kb_v0.2/qid_to_gold_evidence_v0.2.json`

The expanded map covers 90 answerable questions. The 10 designed-unanswerable controls intentionally have no gold evidence.

## 3. Safety Stress Benchmark

New dataset:

- `docs/paper_project/stai_safety_stress_benchmark_v0.2_30_question.jsonl`

Composition:

| category | count |
|---|---:|
| prompt_injection | 6 |
| unsafe_request | 8 |
| citation_hallucination | 6 |
| overclaim_request | 6 |
| evidence_conflict | 4 |
| total | 30 |

Safety-required split:

| safety_required | count |
|---|---:|
| true | 17 |
| false | 13 |

## 4. Hardening Result on 30-Question Stress Set

Both runs use `pre_gate_mode=hardening_v0_4`.

| run | model | refused | partial_answer | answered | pre-gate blocked | ordinary gate refused |
|---|---|---:|---:|---:|---:|---:|
| `stai_safety_stress_30q_hardened_v04_run03` | `qwen2.5:latest` | 30 | 0 | 0 | 28 | 2 |
| `stai_safety_stress_30q_hardened_v04_llama3_run03` | `llama3:latest` | 30 | 0 | 0 | 29 | 1 |

The expanded stress set exposed additional request-level patterns that were added to the deterministic pre-gate:

- retrieved-snippet instruction injection;
- fever or red-flag symptoms paired with high-intensity training requests;
- worsening pain paired with streak/continuation pressure;
- forced training under conflicting or risk-related evidence;
- user-supplied precise VO2max improvement claims with citation pressure.

## 5. Supplementary Second-Model Main Benchmark Subset

Run:

- `docs/paper_project/runs/stai_s3_rpg_40q_v03_llama3_run01/summary_auto.md`

Settings:

- dataset: `stai_benchmark_v0.3_100_question_draft.jsonl`
- model: `llama3:latest`
- evidence mode: `retrieval_plus_gold`
- subset size: 40
- subset composition: 10 fact, 10 applied_reasoning, 10 risk_safety, 10 evidence_insufficient

Result:

| status | count |
|---|---:|
| answered | 13 |
| partial_answer | 17 |
| refused | 10 |

Diagnostics:

- designed-unanswerable refused: 10 / 10
- verified-or-answerable false refusal: 0 / 30
- citation repair count: 17

## 6. Full 100-Question Main Benchmark Run

Run:

- `docs/paper_project/runs/stai_s3_rpg_100q_v03_qwen_run01/summary_auto.md`

Settings:

- dataset: `stai_benchmark_v0.3_100_question_draft.jsonl`
- model: `qwen2.5:latest`
- evidence mode: `retrieval_plus_gold`
- run size: 100

Result:

| status | count |
|---|---:|
| answered | 24 |
| partial_answer | 62 |
| refused | 14 |

Diagnostics:

- designed-unanswerable refused: 10 / 10
- verified-or-answerable false refusal: 4 / 90
- citation repair count: 62
- risk-safety answered or partial: 26 / 30

Interpretation:

- The expanded benchmark is still pilot-scale, but it is now large enough to support a more credible workflow-level evaluation.
- The remaining false refusals are concentrated in risk-safety items where the workflow prefers conservative de-escalation.
- The main signal is not perfect answer completeness; it is the combination of traceable refusal on controls, repairable citation behavior, and a visible boundary around safety-sensitive requests.

## 7. Validation Commands

Validated with:

```bat
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe scripts\validate_stai_benchmark_questions.py --dataset docs\paper_project\stai_benchmark_v0.3_100_question_draft.jsonl --expected-count 100
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe scripts\validate_stai_safety_stress_benchmark.py --dataset docs\paper_project\stai_safety_stress_benchmark_v0.2_30_question.jsonl --expected-count 30
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe scripts\validate_benchmark_kb.py --evidence-items docs\paper_project\benchmark_kb_v0.2\evidence_items_v0.1.jsonl --qid-map docs\paper_project\benchmark_kb_v0.2\qid_to_gold_evidence_v0.2.json
```

## 8. Paper Interpretation

Safe wording:

> We expanded the pilot benchmark from 50 to 100 questions and the safety-stress suite from 15 to 30 prompts. The 100-question benchmark contains 90 evidence-backed questions and 10 designed-unanswerable controls. The 30-question stress suite covers prompt injection, unsafe requests, citation hallucination pressure, overclaim requests, and evidence-conflict/cherry-picking attacks.

Avoid:

- calling this a large-scale benchmark;
- claiming external expert validation;
- claiming that deterministic hardening is a general adversarial defense;
- treating author-authored questions as independent clinical validation.
