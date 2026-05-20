# STAI v0.3 Ablation Results v0.1

This document records the v0.3 ablation subset requested after the case-study stage.

## 1. Purpose

The goal is to test whether the v0.2 ablation pattern still holds on a v0.3 benchmark subset. The runs are diagnostic rather than full benchmark results.

Key question:

> Do the Evidence Gate, Auditor, and Repair modules produce measurable workflow-state differences on the expanded v0.3 benchmark?

## 2. Subset Design

Dataset:

- `docs/paper_project/stai_benchmark_v0.3_100_question_draft.jsonl`

Subset size:

- 40 questions

Composition:

| category | count |
|---|---:|
| fact | 10 |
| applied_reasoning | 10 |
| risk_safety | 10 |
| evidence_insufficient | 10 |
| total | 40 |

The subset is the same balanced qid set used for the previous llama3 40-question sanity check.

Shared settings:

| field | value |
|---|---|
| model | `qwen2.5:latest` |
| evidence_mode | `retrieval_plus_gold` |
| pre_gate_mode | `off` |
| benchmark KB | `docs\paper_project\benchmark_kb_v0.2` |
| qid evidence map | `docs\paper_project\benchmark_kb_v0.2\qid_to_gold_evidence_v0.2.json` |
| top_k | 5 |
| context_max_chars | 500 |
| gold_context_max_chars | 800 |
| num_ctx | 4096 |
| num_batch | 4 |
| num_predict | 300 |

## 3. Runs

Primary full-workflow subset is extracted from:

- `docs/paper_project/runs/stai_s3_rpg_100q_v03_qwen_run01`

Ablation runs:

| run | ablation_mode | status |
|---|---|---|
| `stai_ablation_no_gate_40q_v03_qwen_run02` | `no_gate` | valid |
| `stai_ablation_no_audit_40q_v03_qwen_run01` | `no_audit` | valid |
| `stai_ablation_no_repair_40q_v03_qwen_run01` | `no_repair` | valid |

Misconfigured diagnostic run:

| run | issue | use |
|---|---|---|
| `stai_ablation_no_gate_40q_v03_qwen_run01` | used default old `benchmark_kb` and `qid_to_gold_evidence_v0.1.json`; v0.3-added qids missed gold evidence | do not report as paper result |

## 4. Main Ablation Table

| system variant | answered | partial_answer | refused | designed-unanswerable refused | verified-or-answerable false refusal | citation repair |
|---|---:|---:|---:|---:|---:|---:|
| full workflow, 40-qid slice from 100q run | 8 | 19 | 13 | 10 / 10 | 3 / 30 | 19 |
| `no_gate` | 0 | 40 | 0 | 0 / 10 | 0 / 30 | 40 |
| `no_audit` | 26 | 0 | 14 | 10 / 10 | 4 / 30 | 0 |
| `no_repair` | 27 | 0 | 13 | 10 / 10 | 3 / 30 | 0 |

## 5. Gate / Audit / Repair Diagnostics

| variant | evidence gate | audit | repair |
|---|---|---|---|
| full workflow slice | answerable 21 / partial 6 / unanswerable 13 | repair_required 19 / pass 8 / refuse_required 13 | repaired citations 19 / none 8 / refused 13 |
| `no_gate` | answerable 40 | repair_required 40 | repaired citations 40 |
| `no_audit` | answerable 21 / partial 5 / unanswerable 14 | skipped 26 / refuse_required 14 | skipped_audit 26 / refused 14 |
| `no_repair` | answerable 21 / partial 6 / unanswerable 13 | repair_required 19 / pass 8 / refuse_required 13 | skipped_repair_required 19 / none 8 / refused 13 |

## 6. Interpretation

### 6.1 Evidence Gate

The `no_gate` ablation is the clearest signal. Removing the Evidence Gate converts all 40 items into non-refusal outputs. Most importantly, designed-unanswerable refusal drops from 10 / 10 in the full workflow slice to 0 / 10.

Paper wording:

> Removing the Evidence Gate destroys refusal control for designed-unanswerable items, converting all no-evidence controls into non-refusal outputs.

### 6.2 Auditor

The `no_audit` ablation preserves Evidence Gate refusals but skips independent audit for 26 non-refused items. This removes the `partial_answer` state entirely and turns outputs that would have required repair into `answered`.

Paper wording:

> Removing the Auditor does not remove gate-based refusal, but it hides citation and grounding friction by releasing non-refused outputs without independent audit.

### 6.3 Repair

The `no_repair` ablation preserves gate and audit decisions but disables repair. It removes citation repair as an output transition, producing 27 answered and 13 refused outputs with no partial answers. In this subset, `no_repair` has the same designed-unanswerable refusal count as the full workflow, but it loses the diagnostic distinction between repaired and unrepaired answers.

Paper wording:

> Removing Repair preserves refusal counts on this subset but eliminates the explicit repaired-output state, confirming that `partial_answer` is a workflow-state artifact rather than a raw answerability label.

## 7. Paper Use

Recommended use:

- Include this v0.3 40-question ablation table in the main Results section.
- Keep the older v0.2 50-question ablation table as background or appendix only.
- Clearly label this as a balanced 40-question subset, not a full 100-question ablation.

Safe claim:

> On a balanced 40-question v0.3 subset, removing the Evidence Gate eliminated all designed-unanswerable refusals, while removing the Auditor or Repair preserved gate-based refusals but removed citation-repair observability.

Avoid:

- claiming these are full 100-question ablations;
- claiming `no_audit` or `no_repair` proves answer correctness;
- treating the misconfigured `run01` as a paper result.

## 8. Follow-Up Decision

Current recommendation:

- Do not immediately run full 100-question ablations unless time and compute budget are comfortable.
- The 40-question subset already supports the method claim in a workshop paper.
- Full 100-question ablations would strengthen the paper but are not strictly necessary before drafting.
