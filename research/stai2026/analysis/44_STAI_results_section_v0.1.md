# STAI Results Section v0.1

This draft converts current run artifacts into paper-facing results. All reported values are taken from existing local summaries.

## 1. Main Pilot Benchmark Result

The primary experiment evaluates the full S3 workflow on the 100-question v0.3 benchmark using `qwen2.5:latest` with `retrieval_plus_gold` evidence.

Run:

- `docs/paper_project/runs/stai_s3_rpg_100q_v03_qwen_run01`

### 1.1 Overall Status

| final status | count |
|---|---:|
| answered | 24 |
| partial_answer | 62 |
| refused | 14 |
| total | 100 |

Diagnostic counts:

| diagnostic | result |
|---|---:|
| designed-unanswerable refused | 10 / 10 |
| verified-or-answerable false refusal | 4 / 90 |
| citation repair count | 62 |
| risk-safety answered or partial | 26 / 30 |

Paper interpretation:

> The full workflow refused all designed-unanswerable controls while preserving non-refusal paths for most evidence-backed questions. The remaining 4 / 90 false refusals show a safety-conservative failure mode with a measurable utility cost rather than complete answerability.

### 1.2 Gate, Audit, and Repair

| component outcome | count |
|---|---:|
| evidence gate: answerable | 59 |
| evidence gate: partial | 27 |
| evidence gate: unanswerable | 14 |
| audit: pass | 24 |
| audit: repair_required | 62 |
| audit: refuse_required | 14 |
| repair: repaired_invalid_or_missing_citations | 62 |
| repair: refused_due_to_insufficient_evidence | 9 |
| repair: refused_due_to_insufficient_evidence_with_safety_deescalation | 5 |

Interpretation:

The large `repair_required` count indicates that citation and grounding repair is a major observable state in the workflow. This supports reporting `partial_answer` as a diagnostic category rather than collapsing it into success or failure. We treat the 62 repair cases as audit-exposed grounding friction, not as a simple answer-level failure rate.

### 1.3 Category x Status

| category | answered | partial_answer | refused |
|---|---:|---:|---:|
| fact | 9 | 21 | 0 |
| applied_reasoning | 7 | 23 | 0 |
| risk_safety | 8 | 18 | 4 |
| evidence_insufficient | 0 | 0 | 10 |

Interpretation:

The designed-unanswerable controls are cleanly separated from answerable categories. The false refusals occur in `risk_safety`, which is consistent with a conservative safety-oriented workflow but still represents utility loss.

## 2. Targeted Constructed Safety-Stress Suite

The targeted constructed stress suite evaluates request-level pressure under `hardening_v0_4`. Both qwen and llama3 runs used `retrieval_only` evidence mode.

### 2.1 Cross-Model Stress Results

| model | run | refused | partial_answer | answered |
|---|---|---:|---:|---:|
| `qwen2.5:latest` | `stai_safety_stress_30q_hardened_v04_run03` | 30 | 0 | 0 |
| `llama3:latest` | `stai_safety_stress_30q_hardened_v04_llama3_run03` | 30 | 0 | 0 |

Pre-gate and ordinary-gate split:

| model | pre-gate blocked | ordinary gate refused |
|---|---:|---:|
| `qwen2.5:latest` | 28 | 2 |
| `llama3:latest` | 29 | 1 |

Interpretation:

> Under the deterministic request-level hardening layer, both models refused all 30 targeted constructed stress prompts. Most refusals occurred before generation, with the remaining prompts refused by the ordinary evidence/risk gate.

Boundary:

This result supports targeted request-level hardening on the constructed stress suite. It does not establish broader adversarial-security robustness.

### 2.2 Stress Category Results

Both models refused every prompt in each stress category:

| category | count | qwen refused | llama3 refused |
|---|---:|---:|---:|
| prompt_injection | 6 | 6 | 6 |
| unsafe_request | 8 | 8 | 8 |
| citation_hallucination | 6 | 6 | 6 |
| overclaim_request | 6 | 6 | 6 |
| evidence_conflict | 4 | 4 | 4 |

This table is best used as a stress-suite diagnostic rather than as a broad security benchmark result.

## 3. Supplementary Llama3 Sanity Check

The supplementary 40-question llama3 run checks whether the main workflow behavior is obviously model-specific.

Run:

- `docs/paper_project/runs/stai_s3_rpg_40q_v03_llama3_run01`

Overall status:

| final status | count |
|---|---:|
| answered | 13 |
| partial_answer | 17 |
| refused | 10 |
| total | 40 |

Diagnostics:

| diagnostic | result |
|---|---:|
| designed-unanswerable refused | 10 / 10 |
| verified-or-answerable false refusal | 0 / 30 |
| citation repair count | 17 |

Category x status:

| category | answered | partial_answer | refused |
|---|---:|---:|---:|
| fact | 4 | 6 | 0 |
| applied_reasoning | 5 | 5 | 0 |
| risk_safety | 4 | 6 | 0 |
| evidence_insufficient | 0 | 0 | 10 |

Interpretation:

The llama3 subset preserves the intended refusal behavior on designed-unanswerable controls and shows no false refusal on the 30 answerable subset questions. Because the subset is only 40 questions, this should be reported as a sanity check rather than a model-generalization study.

## 4. Supporting Evidence-Mode Comparison

The older 50-question v0.2 evidence-mode comparison helps explain why curated evidence matters.

| evidence mode | answered | partial_answer | refused | designed-unanswerable refused | verified-answerable false refusal | citation repair |
|---|---:|---:|---:|---:|---:|---:|
| `gold_only` | 18 | 27 | 5 | 5 / 5 | 0 / 45 | 27 |
| `retrieval_only` | 8 | 15 | 27 | 5 / 5 | 22 / 45 | 15 |
| `retrieval_plus_gold` | 14 | 29 | 7 | 5 / 5 | 2 / 45 | 29 |

Interpretation:

The `retrieval_only` condition created a high false-refusal regime. Adding curated evidence reduced false refusals from 22 / 45 to 2 / 45, while `gold_only` produced 0 / 45 false refusals. This supports the paper's argument that trustworthy advisory RAG needs explicit evidence control and diagnostics.

Version caveat:

This table uses the v0.2 50-question benchmark and should be labeled as supporting evidence unless rerun on v0.3.

## 5. Diagnostic Ablation Subset

We ran a balanced 40-question v0.3 diagnostic ablation subset using the same qids as the llama3 main-benchmark sanity check. The subset contains 10 fact, 10 applied-reasoning, 10 risk-safety, and 10 evidence-insufficient items.

| system variant | answered | partial_answer | refused | designed-unanswerable refused | verified-or-answerable false refusal | citation repair |
|---|---:|---:|---:|---:|---:|---:|
| full workflow, 40-qid slice from 100q run | 8 | 19 | 13 | 10 / 10 | 3 / 30 | 19 |
| `no_gate` | 0 | 40 | 0 | 0 / 10 | 0 / 30 | 40 |
| `no_audit` | 26 | 0 | 14 | 10 / 10 | 4 / 30 | 0 |
| `no_repair` | 27 | 0 | 13 | 10 / 10 | 3 / 30 | 0 |

Interpretation:

The `no_gate` diagnostic ablation is the clearest diagnostic: removing the Evidence Gate destroys refusal control on designed-unanswerable items, converting all 10 no-evidence controls into non-refusal outputs. The `no_audit` and `no_repair` variants preserve gate-based refusal, but remove the observability of citation repair. This supports the claim that the workflow's behavior comes from explicit control points rather than a single generation prompt.

Run caveat:

These are 40-question v0.3 diagnostic subset ablations, not comprehensive component studies. The detailed ablation note is in `docs/paper_project/50_STAI_v03_ablation_results_v0.1.md`.

## 6. Result-to-Claim Map

| result block | supported claim | boundary |
|---|---|---|
| 100-question pilot benchmark | S3 makes refusal, partial answers, citation repair, and false refusal measurable on a focused advisory benchmark | pilot-scale, author-authored benchmark; not external validation |
| 10 / 10 designed-unanswerable controls refused | Evidence gating can turn missing support into an intended refusal state | does not prove all insufficient-evidence cases will be detected |
| citation repair count = 62 | Auditing exposes grounding friction that answer-rate metrics would hide | not a simple failure rate and not proof of final factual correctness |
| false refusal = 4 / 90 | Conservative safety gating has a measurable utility cost | safer than unsafe continuation, but still a limitation for users seeking bounded advice |
| 30-prompt targeted constructed stress suite | deterministic hardening blocks the constructed stress patterns tested here | not a broad adversarial-security or deployment-safety claim |
| 40-question llama3 sanity check | the main refusal pattern is not obviously unique to one local model in this subset | not evidence of broad model generalization |
| 40-question diagnostic ablation subset | explicit gates, audit, and repair contribute different observable control effects | not a comprehensive component study |

## 7. Case Study Integration

The selected case-study subsection is drafted in:

- `docs/paper_project/49_STAI_case_study_section_v0.1.md`

Recommended placement:

- after the main result tables;
- before the error-analysis subsection.

Selected cases:

| case | qid | workflow signal | paper role |
|---|---|---|---|
| correct refusal | STAI-P046 | no gold evidence -> evidence gate unanswerable -> refusal | shows refusal as success |
| citation repair | STAI-P003 | answerable claim -> audit citation issue -> repaired partial answer | shows audit/repair behavior |
| conservative false refusal | STAI-P036 | verified risk-safety evidence exists but gate refuses | shows utility cost of safety conservatism |
| safety stress | STAI-S001 | fabricated-citation pressure -> pre-gate refusal | shows targeted request-level hardening |

Interpretation:

These cases make the quantitative results more interpretable. They show that `refused` contains both intended refusals and false refusals, and that `partial_answer` often corresponds to bounded citation repair rather than unsupported generation.

## 8. Candidate Results Paragraph

On the 100-question pilot benchmark, the full S3 workflow with `qwen2.5:latest` produced 24 answered, 62 partial-answer, and 14 refused outputs. All 10 designed-unanswerable controls were refused, while 4 of 90 evidence-backed questions were falsely refused. The false refusals occurred in the risk-safety category, indicating a safety-conservative failure mode with a measurable utility cost. Citation repair was frequent: 62 outputs required repair for invalid or missing citations, motivating the use of `partial_answer` as a grounding-friction diagnostic state rather than a binary failure label. On the 30-prompt targeted constructed stress suite, the hardened request-level pre-gate and downstream gates refused all stress prompts for both qwen2.5 and llama3. These results support the workflow as a diagnostic control structure for safety-sensitive advisory RAG, while leaving open broader questions about scale, expert validation, and model generality.
