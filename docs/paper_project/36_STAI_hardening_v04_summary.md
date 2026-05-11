# STAI Hardening v0.4 Summary

This document records the second hardening pass after the v0.4 cross-model safety-stress check exposed residual model-dependent failures.

## 1. Motivation

Hardening v0.3 corrected the original qwen2.5 safety-stress failures, but it remained a narrow deterministic rule set. We therefore made two changes:

- converted pre-gate detection into a policy registry so individual request-level safety rules are explicit and auditable;
- added false-positive controls and cross-model safety-stress checks using `qwen2.5:latest` and `llama3:latest`.

## 2. v0.4 Policy Classes

Hardening v0.4 detects:

- instruction injection or evidence fabrication pressure;
- unsupported performance guarantees or precise individual predictions;
- red-flag symptoms paired with requests to continue or prescribe training;
- suppression or cherry-picking of safety/risk evidence.

The detector is still deterministic and request-level. It should not be described as a general prompt-injection defense.

## 3. False-Positive Control

Regression tests include verified answerable benchmark questions to check that v0.4 does not block ordinary factual or applied-reasoning questions.

Relevant test file:

- `tests/test_stai_s3_pre_gate.py`

## 4. Cross-Model Safety Stress Result

Both runs use the same 15-question safety stress benchmark with `pre_gate_mode=hardening_v0_4`.

| run | model | refused | partial_answer | answered | pre-gate blocked | ordinary gate refused |
|---|---|---:|---:|---:|---:|---:|
| `stai_safety_stress_15q_hardened_v04_run02` | `qwen2.5:latest` | 15 | 0 | 0 | 14 | 1 |
| `stai_safety_stress_15q_hardened_v04_llama3_run02` | `llama3:latest` | 15 | 0 | 0 | 14 | 1 |

Pre-gate rule counts were identical in the two runs:

| rule | count |
|---|---:|
| instruction_injection_or_fabrication | 6 |
| suppressed_safety_advice | 4 |
| unsupported_performance_guarantee | 3 |
| red_flag_training_continuation | 1 |
| not_triggered | 1 |

## 5. Paper Interpretation

Safe wording:

> A policy-registry pre-gate filter improved request-level safety handling on the stress benchmark. In a supplementary cross-model check, both qwen2.5 and llama3 refused all 15 safety-stress requests under hardening v0.4, with 14/15 requests blocked before generation and one refused by the ordinary evidence gate.

Avoid:

- claiming broad or adaptive prompt-injection robustness;
- claiming the filter covers all paraphrases or adversarial attacks;
- claiming medical or coaching safety validation;
- presenting the 15-question stress set as a large-scale benchmark.

## 6. Artifacts

- `configs/stai_experiments/s3_safety_stress_15q_hardened_v04.json`
- `configs/stai_experiments/s3_safety_stress_15q_hardened_v04_llama3.json`
- `docs/paper_project/runs/stai_safety_stress_15q_hardened_v04_run02/summary_auto.md`
- `docs/paper_project/runs/stai_safety_stress_15q_hardened_v04_llama3_run02/summary_auto.md`
