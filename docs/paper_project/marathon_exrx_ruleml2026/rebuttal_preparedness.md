# Rebuttal And Camera-Ready Preparedness Notes

This note prepares short reviewer-facing responses for the v0.5 traceable labeled dataset layer. It is not part of the solver input.

## Why Synthetic Cases?

M-EXRxBench is synthetic by design because the artifact targets rule compliance, evidence boundaries, refusal behavior, and trace completeness under controlled Rule Challenge conditions. It does not estimate real-world prevalence, intervention effectiveness, or athlete outcomes.

## How Were Labels Determined?

Each evaluator-only gold label is linked to explicit `rule_basis_ids`. These identifiers resolve to documented guideline, literature, protocol, or safety-boundary source families in `benchmark/rule_basis_sources.json` and `benchmark/rule_basis_sources.md`. The mapping files connect case IDs, required rules, expected behavior, risk level, and rule-basis links.

## How Is Label Leakage Prevented?

The benchmark separates system-visible inputs from evaluator-only labels and provenance metadata. Release validation checks that fields such as `expected_behavior`, `gold_risk_level`, `required_rules`, `forbidden_outputs`, `rationale`, `rule_basis_ids`, and mapping metadata are absent from `benchmark/system_visible_cases.jsonl` and hard-set visible inputs. The runner also fails closed if a supplied case file contains evaluator-only fields.

## Are These Clinically Validated?

No. The benchmark is a source-informed synthetic Rule Challenge artifact. It is not clinical validation, medical advice, deployment readiness evidence, real-world safety evidence, or proof of improved athlete outcomes. Any real deployment would require expert review, prospective validation, local governance, privacy review, and escalation pathways for red-flag symptoms.

## Can Reviewers Reproduce The Artifact?

Yes. Reviewers can run:

```powershell
python benchmark\validate_traceable_dataset.py
python demo\validate_artifacts.py
powershell -ExecutionPolicy Bypass -File reproducibility\run_all.ps1
powershell -ExecutionPolicy Bypass -File reproducibility\run_hard100.ps1
```

The expected success sentinels are `traceable_dataset_validation_ok`, `artifact_validation_ok`, `m_exrx_reproducibility_ok`, and `m_exrx_hard100_reproducibility_ok`.
