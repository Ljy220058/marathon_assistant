# RuleML+RR 2026 Official Requirements

## Sources

- RuleML+RR 2026 Rule Challenge: <https://2026.declarativeai.net/ruleml-rr/rule-challenge>
- RuleML+RR 2026 Main Track: <https://2026.declarativeai.net/ruleml-rr/main-track>
- RuleML+RR 2026 Industry Track: <https://2026.declarativeai.net/ruleml-rr/industry-track>

## Rule Challenge Summary

| Item | Requirement |
|---|---|
| Track | Rule Challenge |
| Venue | RuleML+RR 2026, Vilnius, Lithuania, 24-26 August 2026 |
| Paper type | Challenge Proposal and/or Challenge Solution; this work is positioned as a hybrid |
| Page range | 8-15 pages |
| Format | CEURART one-column variant |
| Language | English |
| Submission system | Microsoft CMT, Rule Challenge track |
| Publication | CEUR Workshop Proceedings |

## Mapping To This Work

| Official Concern | This Paper's Response |
|---|---|
| Define the problem | Evidence-bounded exercise prescription with explicit answer/downgrade/clarify/refuse statuses and trace requirements. |
| Highlight innovation | The rule layer is the reasoner of record; `RiskGate`, `EvidenceGate`, `PrescriptionContract`, rule priority, Rule Auditor, and bounded repair govern prescription eligibility. |
| Illustrate use cases | Normal low-risk planning, R2 fatigue/pain/environment downgrade, R3 red-flag refusal, evidence-gap clarification, prompt-injection resistance. |
| Accessibility | CLI demo, batch runner, evaluator, baseline controls, static trace viewer, schemas, and reproducibility script. |
| User experience | Output includes not only a plan but also `risk_level`, `rules_fired`, `evidence_ids`, `action_ids`, `audit_result`, and `repair_log`. |
| Open science | Public repository target, MIT code license, CC BY 4.0 synthetic data/docs license, artifact manifest, and release checklist. |
| Resources | `M-EXRxBench v0.4` 500-case benchmark, gold split, rule docs, runners, evaluator, sample traces, and paper source. |

## Acceptance Gate Used Locally

Minimum submission package:

- M-EXRxBench v0.4 with 500 expert-informed synthetic cases.
- At least three ablation controls plus the proposed rule-governed system.
- Independent evaluator is the only component that reads gold labels.
- At least three interpretable example classes: normal plan, R2 downgrade/clarification, and R3 refusal.
- Trace completeness >= 0.95.
- R3 unsafe advice rate = 0.000 for the proposed system.
- CEURART English manuscript within 8-15 pages.
- Artifact checklist and reproducibility command, with reviewer output regenerated as `artifacts/demo_runs/full_rule_governed_v04.json`.

Non-negotiable claim boundary:

- The artifact evaluates rule compliance on a synthetic benchmark.
- It does not establish clinical safety, medical efficacy, real-world coaching quality, or athletic outcome improvement.
