# Case-To-Rule-Basis Map Summary

This file summarizes source-informed rule-basis coverage for the traceable labeled dataset. Counts are mapping coverage counts, not clinical evidence strength.

- Rows: 100
- Mapping status: reviewed internal consistency pass
- Claim boundary: synthetic Rule Challenge labels; not clinical validation.

## Coverage By Category

| Category | Cases | Most frequent basis IDs |
|---|---:|---|
| `environment_risk` | 10 | basis.environment_risk.rule.001.v01 (10), basis.environment_risk.rule.002.v01 (10), basis.repair.bounded.001.v01 (10), basis.evidence.gate.001.v01 (10) |
| `evidence_gap` | 10 | basis.evidence_gap.rule.001.v01 (10), basis.evidence_gap.rule.002.v01 (10), basis.repair.bounded.001.v01 (10), basis.evidence.gate.001.v01 (5), basis.medical_red_flag.rule.001.v01 (5), basis.medical_red_flag.rule.002.v01 (5) |
| `fatigue_overload` | 10 | basis.fatigue_overload.rule.001.v01 (10), basis.fatigue_overload.rule.002.v01 (10), basis.repair.bounded.001.v01 (10), basis.evidence.gate.001.v01 (10), basis.protocol.hmp.001.v01 (10) |
| `general_education` | 10 | basis.general_education.rule.001.v01 (10), basis.general_education.rule.002.v01 (10), basis.low_risk_plan.rule.001.v01 (10), basis.evidence.gate.001.v01 (10), basis.repair.bounded.001.v01 (10), basis.trace.completeness.002.v01 (10) |
| `low_risk_plan` | 10 | basis.low_risk_plan.rule.001.v01 (10), basis.low_risk_plan.rule.002.v01 (10), basis.protocol.hmp.001.v01 (10), basis.repair.bounded.001.v01 (10), basis.evidence.gate.001.v01 (10) |
| `medical_red_flag` | 10 | basis.medical_red_flag.rule.001.v01 (10), basis.medical_red_flag.rule.002.v01 (10), basis.repair.bounded.001.v01 (10), basis.trace.completeness.001.v01 (10) |
| `nutrition` | 10 | basis.nutrition.rule.001.v01 (10), basis.nutrition.rule.002.v01 (10), basis.repair.bounded.001.v01 (10), basis.evidence_gap.rule.001.v01 (5), basis.evidence.gate.001.v01 (5), basis.medical_red_flag.rule.001.v01 (5) |
| `pain_injury` | 10 | basis.pain_injury.rule.001.v01 (10), basis.pain_injury.rule.002.v01 (10), basis.repair.bounded.001.v01 (10), basis.evidence.gate.001.v01 (5), basis.medical_red_flag.rule.001.v01 (5), basis.medical_red_flag.rule.002.v01 (5) |
| `prompt_injection` | 10 | basis.prompt_injection.rule.001.v01 (10), basis.prompt_injection.rule.002.v01 (10), basis.medical_red_flag.rule.001.v01 (10), basis.medical_red_flag.rule.002.v01 (10), basis.repair.bounded.001.v01 (10), basis.trace.completeness.001.v01 (10) |
| `wearable_uncertainty` | 10 | basis.wearable_uncertainty.rule.001.v01 (10), basis.wearable_uncertainty.rule.002.v01 (10), basis.repair.bounded.001.v01 (10), basis.evidence_gap.rule.001.v01 (10), basis.evidence.gate.001.v01 (10) |

## Most Frequent Basis IDs

| Rule basis ID | Count |
|---|---:|
| `basis.repair.bounded.001.v01` | 100 |
| `basis.evidence.gate.001.v01` | 65 |
| `basis.medical_red_flag.rule.001.v01` | 35 |
| `basis.medical_red_flag.rule.002.v01` | 35 |
| `basis.trace.completeness.001.v01` | 35 |
| `basis.evidence_gap.rule.001.v01` | 25 |
| `basis.low_risk_plan.rule.001.v01` | 20 |
| `basis.protocol.hmp.001.v01` | 20 |
| `basis.general_education.rule.001.v01` | 10 |
| `basis.general_education.rule.002.v01` | 10 |
| `basis.trace.completeness.002.v01` | 10 |
| `basis.low_risk_plan.rule.002.v01` | 10 |
| `basis.fatigue_overload.rule.001.v01` | 10 |
| `basis.fatigue_overload.rule.002.v01` | 10 |
| `basis.pain_injury.rule.001.v01` | 10 |
| `basis.pain_injury.rule.002.v01` | 10 |
| `basis.environment_risk.rule.001.v01` | 10 |
| `basis.environment_risk.rule.002.v01` | 10 |
| `basis.nutrition.rule.001.v01` | 10 |
| `basis.nutrition.rule.002.v01` | 10 |
| `basis.wearable_uncertainty.rule.001.v01` | 10 |
| `basis.wearable_uncertainty.rule.002.v01` | 10 |
| `basis.evidence_gap.rule.002.v01` | 10 |
| `basis.prompt_injection.rule.001.v01` | 10 |
| `basis.prompt_injection.rule.002.v01` | 10 |

## Status Counts

| Expected behavior | Count |
|---|---:|
| `ask_clarification` | 20 |
| `partial_answer` | 45 |
| `refused` | 35 |
