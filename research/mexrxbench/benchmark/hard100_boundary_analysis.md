# Hard100 Boundary Analysis

## Scope

`v0.4-hard-100` is a supplemental reviewer stress set. It is not merged into the default 500-case benchmark score, and it is not clinical validation, deployment evidence, or an athlete-outcome claim. Its purpose is to expose where the current deterministic reference solver is still brittle under hard wording, missing prerequisites, conflicting signals, evidence pressure, and refusal boundaries.

Sources used for this note:

- System-visible input: `benchmark/hard_system_visible_cases.jsonl`
- Evaluator-only labels: `benchmark/hard_gold_labels.jsonl`
- Reference predictions: `artifacts/demo_runs/hard100_full_rule_governed.json`
- Evaluation summary: `artifacts/demo_runs/hard100_full_rule_governed_eval.json`
- Hard-set design: `benchmark/hard_case_design.md`
- Rule-basis summary: `benchmark/hard_case_to_rule_basis_map_summary.md`

## Current Hard100 Metrics

| Metric | Value | Reviewer interpretation |
|---|---:|---|
| `case_count` | 100 | Separate stress-set denominator. |
| `status_accuracy` | 0.670 | The reference solver preserves many status boundaries but still misses hard ask/refuse/downgrade distinctions. |
| `risk_accuracy` | 0.720 | RiskGate is useful but not sufficient for hard general-education, low-risk-looking, and R3-disguised cases. |
| `unsafe_advice_rate` | 0.090 | Nine R3-labeled stress cases were not refused; this is the main boundary concern. |
| `unsupported_prescription_rate` | 0.000 | The current solver did not emit supported-looking prescriptions with empty evidence/action traces. |
| `rule_violation_rate` | 0.000 | No forbidden-output string match was found by the current evaluator. |
| `trace_completeness` | 1.000 | Required trace fields are present; this is a field-presence check, not semantic trace correctness. |
| `repair_success_rate` | 1.000 | Partial-answer outputs include repair logs when the evaluator treats repair as needed. |

## Boundary Pattern By Category

| Category | Status acc. | Risk acc. | Boundary reading |
|---|---:|---:|---|
| `environment_risk` | 1.00 | 1.00 | Heat/AQI/weather stressors are currently handled conservatively. |
| `evidence_gap` | 0.00 | 0.50 | The solver tends to answer partially when the gold behavior asks for clarification under insufficient evidence. |
| `fatigue_overload` | 1.00 | 1.00 | Load-spike and recovery downgrade cases are the strongest hard-set behavior. |
| `general_education` | 0.10 | 0.00 | The solver often classifies education-only prompts as R0/answered, while hard labels require R1/partial boundaries because the prompt pressures personalization or certainty. |
| `low_risk_plan` | 1.00 | 0.10 | Final status is often acceptable, but risk is under-called as R1 when the hard label expects R2 due to hidden/missing/contradictory constraints. |
| `medical_red_flag` | 1.00 | 1.00 | Clear red flags are refused reliably in the current hard set. |
| `nutrition` | 0.60 | 0.60 | Medication/supplement/medical nutrition boundaries remain mixed. |
| `pain_injury` | 1.00 | 1.00 | Pain and injury hard cases are handled conservatively in this run. |
| `prompt_injection` | 1.00 | 1.00 | Direct rule-override attacks are resisted in this run. |
| `wearable_uncertainty` | 0.00 | 1.00 | Risk is recognized, but the solver chooses partial answers when gold labels require clarification under contradictory wearable signals. |

## Confusion Summary

Status confusion shows the main failure mode:

| Gold status -> predicted status | Count | Interpretation |
|---|---:|---|
| `partial_answer -> partial_answer` | 36 | Most repairable/downgrade cases remain within partial-answer authority. |
| `refused -> refused` | 26 | Most explicit R3 refusals are preserved. |
| `ask_clarification -> partial_answer` | 15 | The solver often downgrades when it should ask first. |
| `partial_answer -> answered` | 9 | Education-like or apparently safe requests are over-permitted. |
| `ask_clarification -> ask_clarification` | 5 | Clarification is recognized in a minority of hard clarification cases. |
| `refused -> answered/partial_answer/ask_clarification` | 9 | These are the unsafe-advice boundary failures counted by the evaluator. |

Risk confusion shows the complementary pattern:

| Gold risk -> predicted risk | Count | Interpretation |
|---|---:|---|
| `R2 -> R2` | 46 | R2 recognition is generally strong. |
| `R3 -> R3` | 26 | Clear R3 recognition is strong but not complete. |
| `R1 -> R0` | 9 | Hard education cases are treated as general explanation rather than limited prescription authority. |
| `R2 -> R1` | 9 | Low-risk-looking cases are under-called when hard labels encode missing or conflicting constraints. |
| `R3 -> R2/R1` | 9 | Red-flag disguised or boundary-crossing cases still leak below refusal. |

## Reviewer-Facing Interpretation

Hard100 should be presented as a stress-test appendix, not as the main benchmark. The default benchmark demonstrates that the released pipeline, schema, runner, evaluator, and trace contract are executable. Hard100 demonstrates that the same pipeline can expose reference-solver boundary failures instead of hiding them behind fluent outputs.

The strongest evidence-presentation point is not that Hard100 is solved; it is that the artifact reports failures with separate metrics, category slices, trace completeness, and repair behavior. This helps reviewers see that the benchmark can pressure:

- status authority: answer, partial answer, clarification, or refusal;
- risk priority: especially R3 refusal over performance goals;
- evidence authority: whether evidence/action IDs can support prescription;
- repair scope: whether a partial answer is downgraded rather than expanded;
- trace field presence: whether audit fields exist for independent checking.

## Limitations To State Near Any Hard100 Table

- Hard100 labels are synthetic Rule Challenge labels, not clinical ground truth.
- `trace_completeness = 1.000` means required fields are present, not that the reasoning is semantically complete.
- `rule_violation_rate = 0.000` reflects the current evaluator's forbidden-output checks, not a comprehensive safety proof.
- `unsafe_advice_rate = 0.090` should be foregrounded as a remaining boundary failure of the reference solver.
- Hard100 is not a replacement for external validation, prospective testing, clinician review, or real athlete outcome evaluation.
