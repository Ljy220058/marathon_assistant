# Dataset Provenance And Annotation Agreement

## Dataset Status

`M-EXRxBench` v0.4 is an expert-informed synthetic benchmark for RuleML+RR Rule Challenge preparation. It contains 500 cases across 10 exercise-prescription risk and governance categories.

It does not contain real patient records, wearable exports, clinical records, or private user data. All profiles and queries are synthetic and written to test rule-governed behavior, not to represent validated epidemiological distributions.

## Sources Used To Design Cases

The cases are derived from the paper workspace's rule-governed exercise-prescription concept:

- HMP protocol categories: base/build/taper, easy run, long run, tempo, recovery, progression limits.
- RiskGate levels: `R0`, `R1`, `R2`, `R3`.
- EvidenceGate policy: only eligible `protocol_rule`, `action_library`, and curated guideline-like IDs may support prescription.
- PrescriptionContract requirements: bounded action IDs, profile version, risk level, allowed/forbidden actions, trace.
- Audit/repair policy: downgrade, reschedule, delete unsupported content, ask clarification, or refuse.

The benchmark should be described as "expert-informed synthetic" unless future work adds external expert review or real-world de-identified cases under ethics approval.

## Annotation Agreement Plan

For v0.4, the initial pass is single-author generated and self-audited. The target process for the camera-ready artifact is:

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

## Current v0.4 Reconciliation Notes

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

Do not claim that v0.4:

- is clinically validated;
- represents real patient incidence;
- is a medical device benchmark;
- proves prescription safety in deployment;
- replaces physician, physiotherapist, dietitian, or coach judgment.

Allowed claim:

> M-EXRxBench v0.4 is a synthetic challenge benchmark for evaluating whether rule-governed exercise-prescription agents respect risk gates, evidence boundaries, prescription contracts, and audit traces.
