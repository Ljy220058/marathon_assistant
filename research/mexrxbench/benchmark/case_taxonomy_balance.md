# M-EXRxBench v0.4 Case Taxonomy And Balance

M-EXRxBench v0.4 consists of the default 500-case balanced synthetic benchmark described below plus a supplemental 100-case hard stress subset (`v0.4-hard-100`). The supplemental subset is intended for reviewer-facing stress tests of rule priority, safety refusal, evidence boundary, and prompt/retrieval injection. It is not a clinical validation set, not external generalization proof, and not part of the default v0.4/500 benchmark metrics.

## Taxonomy

| Category | Definition | Primary Failure Mode Tested | Count |
|---|---|---|---:|
| `general_education` | Non-individualized exercise-prescription education. | Turning education into prescription. | 50 |
| `low_risk_plan` | Healthy runner with enough profile data and eligible actions. | Unbounded mileage/intensity or missing trace. | 50 |
| `fatigue_overload` | Excess load, poor sleep, exhaustion, or catch-up pressure. | Prescribing intensity despite fatigue. | 50 |
| `pain_injury` | Worsening pain, recent injury, sharp impact pain, neurological symptoms. | Training through pain or missing red flags. | 50 |
| `medical_red_flag` | Chest pain, syncope, fever, heat illness, palpitations. | Giving any training prescription. | 50 |
| `environment_risk` | Heat, AQI, ice, altitude, storm warning. | Ignoring environmental constraints. | 50 |
| `nutrition` | General fueling/hydration and medical nutrition boundary. | Medical nutrition therapy or unsafe diet advice. | 50 |
| `wearable_uncertainty` | HRV, GPS, HR, sleep, resting HR uncertainty. | Over-trusting noisy wearable data. | 50 |
| `evidence_gap` | Unsupported guarantees, missing profile, evidence pollution. | Free-form prescription without eligible evidence. | 50 |
| `prompt_injection` | Direct, priority-override, retrieval, fabrication, and trace-suppression attacks. | Obeying injected instructions over rules. | 50 |

## Difficulty Balance

| Difficulty | Count | Description |
|---|---:|---|
| `easy` | 150 | Clear label boundary; mostly canonical examples. |
| `medium` | 190 | Requires applying protocol, evidence, or environment constraints. |
| `hard` | 160 | Conflicting signals, prompt injection, missing profile, or medical boundary. |

## MVS Safety-Adversarial Coverage

The 500-case set folds the safety adversarial set into the main benchmark. The standalone file `m_exrxbench_safety_adversarial_cases.jsonl` is a subset index, not a separate gold-label source.

Required adversarial dimensions are covered as follows:

| Required Dimension | Example Case IDs |
|---|---|
| Ambiguous or worsening pain | `mexrx-016`, `mexrx-017`, `mexrx-018` |
| Recent injury | `mexrx-019` |
| Extreme or unsafe environment | `mexrx-024`, `mexrx-026`, `mexrx-027`, `mexrx-030` |
| Abnormal heart-rate/wearable signal | `mexrx-036`, `mexrx-038`, `mexrx-040` |
| Fever training request | `mexrx-023`, `mexrx-049` |
| Prompt injection | `mexrx-046`, `mexrx-047`, `mexrx-048`, `mexrx-050` |
| Retrieval evidence pollution | `mexrx-044`, `mexrx-049` |
| Unrealistic goal pressure | `mexrx-041`, `mexrx-042`, `mexrx-045` |
| Missing profile pressure | `mexrx-043` |
| Medical nutrition boundary | `mexrx-034` |

## Submission Minimum

For a minimum viable Rule Challenge artifact, the benchmark should be used as:

```text
system_visible_cases.jsonl -> system/baselines -> result_schema.json outputs
gold_labels.jsonl -> independent evaluator only
```

The full labeled file is retained for audit and paper-table generation, not as the default runner input.

## Supplemental Hard Stress Subset

Subset: `M-EXRxBench v0.4-hard-100`.

Scope:

- rule priority conflicts;
- safety refusal under high-risk or boundary-crossing requests;
- evidence boundary and unsupported-prescription pressure;
- prompt injection and retrieval injection attacks.

Current hard100 distribution: 10 categories x 10 cases, `R1=10`, `R2=55`, `R3=35`, `partial_answer=45`, `ask_clarification=20`, `refused=35`, and `hard=100`.

Current hard100 reference result: status accuracy 0.670, risk accuracy 0.720, unsafe-advice rate 0.090, unsupported-prescription rate 0.000, trace completeness 1.000.
