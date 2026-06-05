# Case-To-Rule-Basis Map Summary

This file summarizes source-informed rule-basis coverage for the traceable labeled dataset. Counts are mapping coverage counts, not clinical evidence strength.

- Rows: 500
- Mapping status: reviewed internal consistency pass
- Claim boundary: synthetic Rule Challenge labels; not clinical validation.

## Coverage By Category

| Category | Cases | Most frequent basis IDs |
|---|---:|---|
| `environment_risk` | 50 | basis.environment_risk.rule.001.v01 (50), basis.environment_risk.rule.002.v01 (50), basis.repair.bounded.001.v01 (50), basis.evidence.gate.001.v01 (50) |
| `evidence_gap` | 50 | basis.evidence_gap.rule.001.v01 (50), basis.evidence_gap.rule.002.v01 (50), basis.repair.bounded.001.v01 (50), basis.evidence.gate.001.v01 (50), basis.trace.completeness.001.v01 (10), basis.protocol.hmp.001.v01 (4) |
| `fatigue_overload` | 50 | basis.fatigue_overload.rule.001.v01 (50), basis.fatigue_overload.rule.002.v01 (50), basis.repair.bounded.001.v01 (50), basis.evidence.gate.001.v01 (50), basis.protocol.hmp.001.v01 (50), basis.evidence_gap.rule.001.v01 (14) |
| `general_education` | 50 | basis.general_education.rule.001.v01 (50), basis.general_education.rule.002.v01 (50), basis.evidence.gate.001.v01 (50), basis.trace.completeness.001.v01 (50), basis.trace.completeness.002.v01 (50), basis.protocol.hmp.001.v01 (40) |
| `low_risk_plan` | 50 | basis.low_risk_plan.rule.001.v01 (50), basis.low_risk_plan.rule.002.v01 (50), basis.protocol.hmp.001.v01 (50), basis.evidence.gate.001.v01 (50), basis.repair.bounded.001.v01 (42), basis.trace.completeness.001.v01 (32) |
| `medical_red_flag` | 50 | basis.medical_red_flag.rule.001.v01 (50), basis.medical_red_flag.rule.002.v01 (50), basis.repair.bounded.001.v01 (50), basis.trace.completeness.001.v01 (50) |
| `nutrition` | 50 | basis.nutrition.rule.001.v01 (50), basis.nutrition.rule.002.v01 (50), basis.trace.completeness.001.v01 (48), basis.repair.bounded.001.v01 (44), basis.evidence.gate.001.v01 (40), basis.low_risk_plan.rule.001.v01 (38) |
| `pain_injury` | 50 | basis.pain_injury.rule.001.v01 (50), basis.pain_injury.rule.002.v01 (50), basis.repair.bounded.001.v01 (50), basis.evidence.gate.001.v01 (40), basis.medical_red_flag.rule.001.v01 (10), basis.medical_red_flag.rule.002.v01 (10) |
| `prompt_injection` | 50 | basis.prompt_injection.rule.001.v01 (50), basis.prompt_injection.rule.002.v01 (50), basis.trace.completeness.001.v01 (50), basis.repair.bounded.001.v01 (40), basis.low_risk_plan.rule.001.v01 (30), basis.evidence.gate.001.v01 (30) |
| `wearable_uncertainty` | 50 | basis.wearable_uncertainty.rule.001.v01 (50), basis.wearable_uncertainty.rule.002.v01 (50), basis.repair.bounded.001.v01 (50), basis.evidence.gate.001.v01 (50), basis.evidence_gap.rule.001.v01 (20), basis.protocol.hmp.001.v01 (2) |

## Most Frequent Basis IDs

| Rule basis ID | Count |
|---|---:|
| `basis.repair.bounded.001.v01` | 466 |
| `basis.evidence.gate.001.v01` | 410 |
| `basis.trace.completeness.001.v01` | 250 |
| `basis.protocol.hmp.001.v01` | 180 |
| `basis.low_risk_plan.rule.001.v01` | 120 |
| `basis.evidence_gap.rule.001.v01` | 96 |
| `basis.medical_red_flag.rule.001.v01` | 90 |
| `basis.medical_red_flag.rule.002.v01` | 90 |
| `basis.general_education.rule.001.v01` | 50 |
| `basis.general_education.rule.002.v01` | 50 |
| `basis.trace.completeness.002.v01` | 50 |
| `basis.low_risk_plan.rule.002.v01` | 50 |
| `basis.fatigue_overload.rule.001.v01` | 50 |
| `basis.fatigue_overload.rule.002.v01` | 50 |
| `basis.pain_injury.rule.001.v01` | 50 |
| `basis.pain_injury.rule.002.v01` | 50 |
| `basis.environment_risk.rule.001.v01` | 50 |
| `basis.environment_risk.rule.002.v01` | 50 |
| `basis.nutrition.rule.001.v01` | 50 |
| `basis.nutrition.rule.002.v01` | 50 |
| `basis.wearable_uncertainty.rule.001.v01` | 50 |
| `basis.wearable_uncertainty.rule.002.v01` | 50 |
| `basis.evidence_gap.rule.002.v01` | 50 |
| `basis.prompt_injection.rule.001.v01` | 50 |
| `basis.prompt_injection.rule.002.v01` | 50 |

## Status Counts

| Expected behavior | Count |
|---|---:|
| `answered` | 120 |
| `ask_clarification` | 70 |
| `partial_answer` | 210 |
| `refused` | 100 |
