# M-EXRxBench v0.4 Benchmark Audit Table

## File-Level Audit

| File | Purpose | Case Count | Gold Fields Present | System Runner Should Read |
|---|---|---:|---|---|
| `m_exrxbench_v0.4_500_cases.jsonl` | Active full labeled benchmark for audit and paper tables | 500 | Yes | No |
| `system_visible_cases.jsonl` | Inputs for systems and baselines | 500 | No | Yes |
| `gold_labels.jsonl` | Evaluator-only labels | 500 | Yes | No |
| `m_exrxbench_v0.3_100_cases.jsonl` | Historical labeled archive | 100 | Yes | No |
| `m_exrxbench_safety_adversarial_cases.jsonl` | Safety adversarial subset index | 20 | No | Optional for subset selection |

## Category Balance

| Category | Count | Main Risk Focus |
|---|---:|---|
| `general_education` | 50 | R0 explanation-only boundary |
| `low_risk_plan` | 50 | R1 contract-bound prescription |
| `fatigue_overload` | 50 | R2 load/fatigue downgrade |
| `pain_injury` | 50 | R2/R3 injury boundary |
| `medical_red_flag` | 50 | R3 refusal |
| `environment_risk` | 50 | R2 environmental downgrade |
| `nutrition` | 50 | nutrition scope and medical boundary |
| `wearable_uncertainty` | 50 | uncertainty-aware conservative action |
| `evidence_gap` | 50 | evidence insufficiency and unsupported claims |
| `prompt_injection` | 50 | instruction/retrieval injection resistance |

## Expected Behavior Balance

| Expected Behavior | Count |
|---|---:|
| `answered` | 120 |
| `partial_answer` | 210 |
| `ask_clarification` | 70 |
| `refused` | 100 |

## Risk-Level Balance

| Risk Level | Count |
|---|---:|
| `R0` | 50 |
| `R1` | 120 |
| `R2` | 240 |
| `R3` | 90 |

## Difficulty Balance

| Difficulty | Count |
|---|---:|
| `easy` | 150 |
| `medium` | 190 |
| `hard` | 160 |

## Audit Checklist

- [x] 500 total cases.
- [x] 10 categories.
- [x] 50 cases per category.
- [x] At least 20 safety-adversarial cases.
- [x] At least 90 R3 or medical-boundary risk cases.
- [x] Prompt-injection cases include direct instruction injection, developer-message injection, evidence/action fabrication pressure, retrieval injection, and trace suppression.
- [x] `system_visible_cases.jsonl` excludes `expected_behavior`, `gold_risk_level`, `required_rules`, `forbidden_outputs`, `rationale`, `notes`, `case_family`, `variation_type`, `source_seed_id`, and `annotation_notes`.
- [x] `gold_labels.jsonl` is keyed by `case_id` and contains evaluator-only labels.
