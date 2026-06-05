# STAI Supplementary Generalization and Boundary Benchmark v0.1

Date: 2026-05-11

## Purpose

This supplementary benchmark draft expands the current STAI pilot evaluation beyond the original endurance-training main benchmark.

It is designed to test two reviewer-facing weaknesses:

- whether the workflow generalizes beyond the original half-marathon/endurance-training prompt distribution;
- whether the workflow can expose harder evidence-boundary behavior, especially partial support, unsupported precision, fabricated citations, and unsafe continuation pressure.

This file should be described as a supplementary diagnostic set, not as a large-scale benchmark.

## Artifact

Dataset:

`docs/paper_project/stai_supplementary_generalization_boundary_v0.1_60_question_draft.jsonl`

Validator:

`scripts/validate_stai_supplementary_benchmark.py`

Validation command:

```powershell
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe scripts\validate_stai_supplementary_benchmark.py --dataset docs\paper_project\stai_supplementary_generalization_boundary_v0.1_60_question_draft.jsonl --expected-count 60
```

Validation result:

- ok: true
- rows: 60
- first qid: STAI-X001
- last qid: STAI-X060

## Category Split

| Category | Count | Purpose |
| --- | ---: | --- |
| `cross_domain_advisory` | 30 | Generalization beyond the original endurance-training benchmark into adjacent fitness, recovery, race-preparation, sleep, heat, strength, mobility, and cross-training advice. |
| `evidence_boundary` | 20 | Harder evidence-boundary prompts involving unsupported precision, fabricated citations, evidence conflict, population mismatch, overgeneralization, and insufficient support for individualized prescriptions. |
| `additional_safety_stress` | 10 | Additional refusal-targeted prompts for prompt injection, unsafe continuation, symptom concealment, fabricated expert support, and high-risk training pressure. |

## Evidence Status Split

| Evidence status | Count | Meaning |
| --- | ---: | --- |
| `needs_evidence_mapping` | 40 | Answerable or partially answerable prompts that still require curated gold evidence mapping before gold-mode experiments. |
| `designed_unanswerable` | 10 | Prompts intentionally designed to require refusal because the requested precision, citation, or claim is unsupported. |
| `safety_stress_unanswerable` | 10 | Prompts intentionally designed to require refusal for safety or fabrication reasons. |

## Target Output-State Split

| Target state | Count | Diagnostic role |
| --- | ---: | --- |
| `answered` | 20 | Tests ordinary supported general-advisory answers. |
| `partial_answer` | 20 | Tests bounded answers under partial evidence, missing personalization data, or overclaim pressure. |
| `refused` | 20 | Tests unsupported precision, fabricated citation, and unsafe continuation refusal. |

## Important Scope Boundary

The 40 `needs_evidence_mapping` items are honest drafts, not verified gold-evidence items yet. They should not be reported as evidence-backed results until curated evidence IDs and spans are mapped.

Recommended next step:

1. Map 40 `needs_evidence_mapping` items to curated evidence spans.
2. Run a small supplementary workflow experiment.
3. Report it as an optional supplementary diagnostic result, not as the paper's main result.
