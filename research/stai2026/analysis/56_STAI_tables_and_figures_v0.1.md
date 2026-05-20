# STAI Tables and Figures v0.1

## 1. Purpose

This document consolidates the paper-facing tables and figure captions for the STAI draft. The goal is to keep the submitted manuscript readable while preserving traceability to the local experiment artifacts.

Primary draft:

- `docs/paper_project/51_STAI_paper_draft_v0.1.md`

Primary figure:

- `docs/paper_project/figures/figure1_method_workflow.png`

## 2. Recommended Main-Text Tables and Figure

For a workshop paper, the main text should contain:

| Item | Placement | Purpose |
|---|---|---|
| Figure 1 | Method | Show the evidence-gated audit-and-repair workflow and refusal paths. |
| Table 1 | Results 7.1 | Main pilot-benchmark output status and diagnostics. |
| Table 2 | Results 7.2 | Cross-model targeted safety-stress behavior. |
| Table 3 | Results 7.4 | Representative trace-level case studies. |
| Table 4 | Results 7.5 | v0.3 40-question ablation subset. |
| Table 5 | Results 7.6 | Result-to-claim mapping. |

Recommended appendix/supplementary material:

| Item | Reason |
|---|---|
| Category x status table for the 100-question run | Useful but can crowd the main paper if page-limited. |
| Stress category table | Useful diagnostic detail, but the main stress table already gives the headline. |
| Llama3 40-question category table | Supplementary sanity check rather than central evidence. |
| v0.2 evidence-mode comparison | Supporting diagnostic from older benchmark version; include only with clear caveat. |

## 3. Figure 1

Suggested manuscript caption:

> **Figure 1: Evidence-gated audit-and-repair workflow for safety-sensitive endurance-training advice.** User requests first pass through request-level filtering and evidence retrieval. Evidence and risk gates determine whether generation is allowed, bounded, or refused. Draft answers must pass an independent grounding auditor; bounded citation/grounding repair can produce a partial answer or refusal when support remains insufficient. The figure highlights refusal as an explicit workflow state rather than a generic failure.

Required boundary:

- Do not describe this figure as a deployed coaching architecture.
- Do not imply that the pre-gate is a general adversarial defense.
- Do emphasize that refusal and repair are observable states.

## 4. Table 1: Main Pilot Benchmark Result

Suggested manuscript caption:

> **Table 1: Main 100-question pilot benchmark result for the full workflow using `qwen2.5:latest`.** The workflow refused all designed-unanswerable controls while preserving answer or partial-answer outputs for most evidence-backed questions. False refusals are reported separately because refusal can be either intended or conservative.

Table:

| final status | count |
|---|---:|
| answered | 24 |
| partial_answer | 62 |
| refused | 14 |
| total | 100 |

Diagnostics:

| diagnostic | result |
|---|---:|
| designed-unanswerable refused | 10 / 10 |
| verified-or-answerable false refusal | 4 / 90 |
| citation repair count | 62 |
| risk-safety answered or partial | 26 / 30 |

Source artifact:

- `docs/paper_project/runs/stai_s3_rpg_100q_v03_qwen_run01/outputs.jsonl`

## 5. Table 2: Targeted Safety-Stress Result

Suggested manuscript caption:

> **Table 2: Targeted constructed safety-stress result under deterministic request-level hardening.** Both local models refused all constructed stress prompts. This result supports targeted hardening on this stress suite, not a broader adversarial-security claim.

Table:

| model | refused | partial_answer | answered | pre-gate blocked | ordinary gate refused |
|---|---:|---:|---:|---:|---:|
| `qwen2.5:latest` | 30 | 0 | 0 | 28 | 2 |
| `llama3:latest` | 30 | 0 | 0 | 29 | 1 |

Source artifacts:

- `docs/paper_project/runs/stai_safety_stress_30q_hardened_v04_run03/outputs.jsonl`
- `docs/paper_project/runs/stai_safety_stress_30q_hardened_v04_llama3_run03/outputs.jsonl`

## 6. Table 3: Representative Case Studies

Suggested manuscript caption:

> **Table 3: Representative traces illustrating intended refusal, citation repair, conservative false refusal, and request-level stress blocking.** The cases show why the workflow reports `answered`, `partial_answer`, and `refused` as separate diagnostic states.

Table:

| case | qid | workflow signal | decision | lesson |
|---|---|---|---|---|
| insufficient evidence | STAI-P046 | Evidence Gate marks a no-evidence control as unanswerable | refused | refusal can be an intended success state |
| citation repair | STAI-P003 | Auditor finds a citation issue in a supported answer | partial_answer | repair exposes grounding friction |
| conservative false refusal | STAI-P036 | verified risk-safety evidence exists but the gate refuses | refused | safety conservatism can reduce utility |
| prompt injection | STAI-S001 | pre-gate detects fabricated-citation pressure | refused | targeted stress prompts can be blocked before generation |

Source artifacts:

- `docs/paper_project/47_STAI_case_study_trace_table_v0.1.md`
- `docs/paper_project/49_STAI_case_study_section_v0.1.md`

## 7. Table 4: v0.3 Diagnostic Ablation Subset

Suggested manuscript caption:

> **Table 4: v0.3 40-question diagnostic ablation subset for `qwen2.5:latest`.** Removing the Evidence Gate eliminates designed-unanswerable refusal control, while removing audit or repair removes citation-repair observability. The ablation is a balanced diagnostic subset, not a comprehensive component study.

Table:

| system variant | answered | partial_answer | refused | designed-unanswerable refused | verified-or-answerable false refusal | citation repair |
|---|---:|---:|---:|---:|---:|---:|
| full workflow, 40-qid slice from 100q run | 8 | 19 | 13 | 10 / 10 | 3 / 30 | 19 |
| `no_gate` | 0 | 40 | 0 | 0 / 10 | 0 / 30 | 40 |
| `no_audit` | 26 | 0 | 14 | 10 / 10 | 4 / 30 | 0 |
| `no_repair` | 27 | 0 | 13 | 10 / 10 | 3 / 30 | 0 |

Source artifacts:

- `docs/paper_project/runs/stai_s3_rpg_100q_v03_qwen_run01/outputs.jsonl`
- `docs/paper_project/runs/stai_ablation_no_gate_40q_v03_qwen_run02/outputs.jsonl`
- `docs/paper_project/runs/stai_ablation_no_audit_40q_v03_qwen_run01/outputs.jsonl`
- `docs/paper_project/runs/stai_ablation_no_repair_40q_v03_qwen_run01/outputs.jsonl`

## 8. Table 5: Result-to-Claim Map

Suggested manuscript caption:

> **Table 5: Mapping from reported results to supported claims.** The table separates what each result directly supports from claims that remain outside the evidence boundary.

Table:

| result block | supported claim | boundary |
|---|---|---|
| 100-question pilot benchmark | S3 makes refusal, partial answers, citation repair, and false refusal measurable on a focused advisory benchmark | pilot-scale, author-authored benchmark; not external validation |
| 10 / 10 designed-unanswerable controls refused | Evidence gating can turn missing support into an intended refusal state | does not prove all insufficient-evidence cases will be detected |
| citation repair count = 62 | Auditing exposes grounding friction that answer-rate metrics would hide | not a simple failure rate and not proof of final factual correctness |
| false refusal = 4 / 90 | Conservative safety gating has a measurable utility cost | safer than unsafe continuation, but still a limitation for users seeking bounded advice |
| 30-prompt targeted constructed stress suite | deterministic hardening blocks the constructed stress patterns tested here | not a broad adversarial-security or deployment-safety claim |
| 40-question llama3 sanity check | the main refusal pattern is not obviously unique to one local model in this subset | not evidence of broad model generalization |
| 40-question diagnostic ablation subset | explicit gates, audit, and repair contribute different observable control effects | not a comprehensive component study |

## 9. Optional Supplementary Tables

### 9.1 Main Category x Status

| category | answered | partial_answer | refused |
|---|---:|---:|---:|
| fact | 9 | 21 | 0 |
| applied_reasoning | 7 | 23 | 0 |
| risk_safety | 8 | 18 | 4 |
| evidence_insufficient | 0 | 0 | 10 |

### 9.2 Stress Category Result

| category | count | qwen refused | llama3 refused |
|---|---:|---:|---:|
| prompt_injection | 6 | 6 | 6 |
| unsafe_request | 8 | 8 | 8 |
| citation_hallucination | 6 | 6 | 6 |
| overclaim_request | 6 | 6 | 6 |
| evidence_conflict | 4 | 4 | 4 |

### 9.3 Supplementary Llama3 Sanity Check

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

## 10. Table-Figure Claim Boundaries

Use:

- "pilot benchmark"
- "targeted constructed stress suite"
- "constructed stress prompts"
- "balanced 40-question diagnostic ablation subset"
- "diagnostic state"
- "citation/grounding repair"

Avoid:

- broad scale claims
- broad adversarial-security claims
- "clinically safe"
- "deployment-ready"
- broad model-generalization claims
- "citation repair proves factual correctness"

## 11. Next Formatting Step

When converting to LaTeX:

1. Move Figure 1 to `paper/figures/figure1_method_workflow.png`.
2. Convert Table 1-5 into LaTeX `table` environments.
3. Keep optional tables in appendix if the target page limit is tight.
4. Use the captions above as the canonical wording unless later experiments change the numbers.
