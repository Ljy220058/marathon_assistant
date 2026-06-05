# Dataset Provenance And Annotation Agreement

## Dataset Status

`M-EXRxBench` v0.5 is a guideline/literature/rule-spec-informed synthetic benchmark for RuleML+RR Rule Challenge preparation. It adds a traceable labeled dataset layer over the 500-case benchmark across 10 exercise-prescription risk and governance categories.

It does not contain real patient records, wearable exports, clinical records, or private user data. All profiles and queries are synthetic and written to test rule-governed behavior, not to represent validated epidemiological distributions.

## Sources Used To Design Cases

The cases are derived from the paper workspace's rule-governed exercise-prescription concept:

- HMP protocol categories: base/build/taper, easy run, long run, tempo, recovery, progression limits.
- RiskGate levels: `R0`, `R1`, `R2`, `R3`.
- EvidenceGate policy: only eligible `protocol_rule`, `action_library`, and curated guideline-like IDs may support prescription.
- PrescriptionContract requirements: bounded action IDs, profile version, risk level, allowed/forbidden actions, trace.
- Audit/repair policy: downgrade, reschedule, delete unsupported content, ask clarification, or refuse.

The benchmark should be described as "expert-informed synthetic" unless future work adds external expert review or real-world de-identified cases under ethics approval.

## Traceable Labeling Contract

The v0.5 release separates four views:

| View | File | Purpose |
|---|---|---|
| Full labeled audit view | `m_exrxbench_v0.4_500_cases.jsonl` | Maintainer-facing full records with labels and synthetic provenance. |
| System-visible input | `system_visible_cases.jsonl` | Solver input only; gold labels and provenance fields are absent. |
| Evaluator-only labels | `gold_labels.jsonl` | Expected status, risk level, required rules, forbidden outputs, and rationale. |
| Rule-basis map | `case_to_rule_basis_map.jsonl` | Case-to-source traceability for evaluator-side labels. |

The supplemental hard set mirrors the same contract with `m_exrxbench_v0.4_hard_100_cases.jsonl`, `hard_system_visible_cases.jsonl`, `hard_gold_labels.jsonl`, and `hard_case_to_rule_basis_map.jsonl`.

Each evaluator-only gold label is linked to one or more `rule_basis_ids`. These identifiers resolve through `rule_basis_sources.json` and `rule_basis_sources.md` to guideline, literature, local protocol, action-library, or safety-boundary source families. The mapping is intended to reduce arbitrary labeling and support auditability. It is not evidence that the synthetic labels are clinically validated.

Release validation checks row counts, exact `case_id` alignment, absence of gold/provenance fields in system-visible inputs, rule-basis resolution, and R2/R3 basis coverage:

```powershell
conda run -n torch2.5.1 python benchmark\validate_traceable_dataset.py
```

## Annotation Agreement Plan

For v0.5, the initial pass is generated from the benchmark rule specifications and self-audited against the traceable labeling contract. The target process for a later camera-ready or extended release is:

| Step | Responsible Role | Output |
|---|---|---|
| Initial labeling | Benchmark worker | `gold_labels.jsonl` |
| Safety review | Safety/method reviewer | red-flag and fail-closed comments |
| Rule review | Rule auditor | rule-label consistency |
| Final reconciliation | Benchmark lead | updated labels and rationale |

Minimum agreement target before final release:

- 100% agreement on all `R3/refused` cases after reconciliation.
- No unresolved disagreement for cases containing chest pain, syncope, fever, heat-illness symptoms, palpitations, neurological symptoms, or medical nutrition therapy.
- At least 0.85 pairwise agreement on `expected_behavior` for non-R3 cases.
- All disagreements documented in a future `annotation_disagreements.md` if external reviewers are added.

## Current v0.5 Reconciliation Notes

The current case set intentionally includes:

- 10 categories with 50 cases each.
- Risk balance: `R0`=50, `R1`=120, `R2`=240, `R3`=90.
- Expected-behavior balance: `answered`=120, `partial_answer`=210, `ask_clarification`=70, `refused`=100.
- Difficulty balance: `easy`=150, `medium`=190, `hard`=160.
- At least 90 red-flag or medical-boundary risk cases.
- At least 20 safety-adversarial cases.
- Prompt-injection and retrieval-injection cases that must not override safety or trace requirements.
- Missing-profile and evidence-gap cases that should not produce detailed prescription.

## Claims Not Allowed

Do not claim that v0.5:

- is clinically validated;
- represents real patient incidence;
- is a medical device benchmark;
- proves prescription safety in deployment;
- replaces physician, physiotherapist, dietitian, or coach judgment.

Allowed claim:

> M-EXRxBench v0.5 is a traceable synthetic challenge benchmark for evaluating whether rule-governed exercise-prescription agents respect risk gates, evidence boundaries, prescription contracts, source-informed label mappings, and audit traces.
