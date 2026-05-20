# M-EXRxBench v0.5 Traceable Upgrade Audit

Reviewer-facing status: baseline audit for upgrading the current M-EXRxBench v0.4 synthetic benchmark into a v0.5 traceable labeled dataset.

## Scope

This audit covers only the benchmark artifact under `docs/paper_project/marathon_exrx_ruleml2026/`. It does not modify the benchmark generator, runner, evaluator, manuscript, source registry, or schema. The intended v0.5 change is traceability of evaluator-only gold labels, not a change in the solver-visible case prompts or the underlying clinical status of the dataset.

M-EXRxBench remains a guideline/literature-informed synthetic Rule Challenge benchmark. It is not real patient data, not real athlete telemetry, not a clinical validation set, and not evidence that any deployed exercise-prescription system is safe or effective.

## Baseline Files Audited

| Split | File | Rows | Role |
|---|---|---:|---|
| Default full labeled | `benchmark/m_exrxbench_v0.4_500_cases.jsonl` | 500 | Audit and table-generation view containing visible fields plus gold labels. |
| Default system-visible | `benchmark/system_visible_cases.jsonl` | 500 | Solver input view. |
| Default evaluator gold | `benchmark/gold_labels.jsonl` | 500 | Evaluator-only labels. |
| Hard full labeled | `benchmark/m_exrxbench_v0.4_hard_100_cases.jsonl` | 100 | Supplemental hard stress audit view. |
| Hard system-visible | `benchmark/hard_system_visible_cases.jsonl` | 100 | Solver input view for hard100. |
| Hard evaluator gold | `benchmark/hard_gold_labels.jsonl` | 100 | Evaluator-only labels for hard100. |

Current commit recorded for this audit: `d404bad8`.

## Baseline Label Distribution

### Default 500-Case Split

| Field | Distribution |
|---|---|
| Category | 10 categories x 50 cases: `general_education`, `low_risk_plan`, `fatigue_overload`, `pain_injury`, `medical_red_flag`, `environment_risk`, `nutrition`, `wearable_uncertainty`, `evidence_gap`, `prompt_injection`. |
| Risk | `R0`=50, `R1`=120, `R2`=240, `R3`=90. |
| Expected behavior | `answered`=120, `partial_answer`=210, `ask_clarification`=70, `refused`=100. |
| Difficulty | `easy`=150, `medium`=190, `hard`=160. |

Risk/status combinations:

| Combination | Count | Review note |
|---|---:|---|
| `R0/answered` | 50 | Education-only answers. |
| `R1/answered` | 70 | Low-risk contract-bound prescriptions. |
| `R1/partial_answer` | 40 | Non-intuitive; requires explicit review because risk is low but some contract, evidence, or protocol boundary blocks a full answer. |
| `R1/ask_clarification` | 10 | Non-intuitive; requires explicit review because missing profile/evidence can block prescription without raising risk to R2. |
| `R2/partial_answer` | 170 | Elevated risk with safe downgrade or restriction. |
| `R2/ask_clarification` | 60 | Elevated risk or missing context blocks detailed prescription. |
| `R2/refused` | 10 | Non-intuitive; requires explicit review because refusal is allowed only when the R2 case crosses an unrepairable scope, medical-boundary, or governance boundary without meeting R3 red-flag criteria. |
| `R3/refused` | 90 | Red-flag or medical-boundary refusal. |

### Supplemental Hard100 Split

| Field | Distribution |
|---|---|
| Category | 10 categories x 10 cases. |
| Risk | `R1`=10, `R2`=55, `R3`=35. |
| Expected behavior | `partial_answer`=45, `ask_clarification`=20, `refused`=35. |
| Difficulty | `hard`=100. |

Risk/status combinations:

| Combination | Count | Review note |
|---|---:|---|
| `R1/partial_answer` | 10 | Full review required because low-risk cases still have trace, evidence, protocol, or contract boundaries. |
| `R2/partial_answer` | 35 | Full review as part of hard100. |
| `R2/ask_clarification` | 20 | Full review as part of hard100. |
| `R3/refused` | 35 | Full review required. |

## Leakage Baseline

The current system-visible files were checked for gold/provenance fields including `expected_behavior`, `gold_risk_level`, `required_rules`, `forbidden_outputs`, `rationale`, `case_family`, `variation_type`, `source_seed_id`, `annotation_notes`, and `notes`.

| File | Result |
|---|---|
| `benchmark/system_visible_cases.jsonl` | No checked gold/provenance fields found. |
| `benchmark/hard_system_visible_cases.jsonl` | No checked gold/provenance fields found. |

The default full, visible, and gold files have matching `case_id` sets. The hard full, visible, and gold files also have matching `case_id` sets. Case IDs are unique in the audited full labeled files.

## Baseline Validator Note

`demo/validate_artifacts.py` was run as a baseline read-only check. It did not reach the success sentinel because the current artifact tree contains an unrelated workspace marker in `TODO.md`:

```text
ValueError: unexpected unrelated workspace marker in TODO.md
```

This audit records the current state only. It does not change `TODO.md` or validator code. Later v0.5 engineering work should decide whether the marker is expected development context or should be excluded from the release artifact.

## What v0.5 Changes

v0.5 should add traceability around existing gold labels:

- evaluator-only rule-basis identifiers for each gold label;
- a source registry resolving every `rule_basis_id`;
- explicit mapping from `required_rules` to source-informed rule bases where possible;
- manifest hashes, row counts, split roles, and schema references;
- validation that gold labels and provenance fields are absent from system-visible inputs;
- reviewer-facing annotation protocol language that explains scope, labels, forbidden outputs, conflicts, and review sampling.

## What v0.5 Does Not Change

v0.5 does not by itself:

- convert the dataset into clinical validation data;
- add real patient records or real athlete telemetry;
- prove deployed safety, medical effectiveness, coaching effectiveness, or improved athlete outcomes;
- allow solver inputs to include gold labels, rule-basis mappings, rationales, or provenance fields;
- change the meaning of `R0` through `R3` or the four expected behavior labels;
- remove the need for human review of red-flag and non-intuitive label combinations.

## Annotation Review Focus

The annotation lead should prioritize:

1. All `R3/refused` rows in both default and hard splits.
2. All hard100 rows.
3. All non-intuitive combinations: `R1/partial_answer`, `R1/ask_clarification`, and `R2/refused`.
4. A stratified sample covering every category, every expected behavior label, and every risk level.
5. Cases whose `forbidden_outputs` could be interpreted too broadly or too vaguely.

## Claim Boundary

Allowed reviewer-facing claim:

> M-EXRxBench v0.5 is a synthetic, traceable Rule Challenge benchmark for testing whether exercise-prescription agents respect risk gates, evidence boundaries, prescription contracts, forbidden-output constraints, and evaluator-only traceability requirements.

Forbidden reviewer-facing claims:

- clinically validated benchmark;
- real-world safety proof;
- medical device evaluation;
- representative patient or athlete incidence estimate;
- proof of coaching effectiveness;
- evidence that a deployed system improves athlete outcomes;
- replacement for physician, physiotherapist, dietitian, or coach judgment.
