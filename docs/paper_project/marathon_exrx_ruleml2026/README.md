# Rule-Governed M-EXRx Agent

RuleML+RR 2026 Rule Challenge artifact for evidence-bounded exercise-prescription agents.

Core claim:

> The LLM is not the reasoner of record. Exercise prescription is generated only within a rule-governed, evidence-bounded, auditable contract.

Public repository: https://github.com/Ljy220058/marathon_assistant

Artifact path in the repository: this directory.

## 5-Minute Reviewer Path

Run from the artifact directory:

```powershell
conda run -n torch2.5.1 python demo\validate_artifacts.py
powershell -ExecutionPolicy Bypass -File reproducibility\run_all.ps1
powershell -ExecutionPolicy Bypass -File reproducibility\run_hard100.ps1
```

Inspect the main outputs from the current v0.4/500 synthetic benchmark run:

```text
artifacts/demo_runs/single_red_flag.json
artifacts/demo_runs/full_rule_governed_v04.json
artifacts/demo_runs/full_rule_governed_eval_summary.md
artifacts/demo_runs/hard100_full_rule_governed_eval_summary.md
artifacts/baseline_runs/
demo/static_trace_viewer.html
paper/main.pdf
```

Open the static trace viewer directly in a browser:

```text
demo/static_trace_viewer.html
```

## What This Artifact Contains

- `M-EXRxBench v0.4`: 500 synthetic cases for rule-governed exercise-prescription decisions.
- Supplemental subset: `M-EXRxBench v0.4-hard-100`, a reviewer-facing 100-case hard stress subset for rule priority, safety refusal, evidence boundary, and prompt/retrieval injection. It is evaluated separately from the default v0.4/500 benchmark.
- Current hard100 reference result: status accuracy 0.670, risk accuracy 0.720, unsafe-advice rate 0.090, unsupported-prescription rate 0.000, trace completeness 1.000.
- System-visible and evaluator-only gold splits.
- RiskGate, EvidenceGate, PrescriptionContract, Rule Auditor, and bounded repair specifications.
- Deterministic demo runner, benchmark runner, baselines, evaluator, schema validator, and trace viewer.
- CEURART manuscript source and compiled PDF.

## Scope Boundary

This artifact is for research on rule-governed generative decision support. It is not a medical diagnosis, treatment, emergency, or clinical rehabilitation system. Reported 1.000 metrics are deterministic benchmark compliance signals on the synthetic v0.4/500 benchmark, not clinical validation, real-world safety evidence, generalization evidence, or athlete-outcome proof. The v0.4-hard-100 subset is a separate reviewer stress test; its current measured results show the intended pressure on the reference solver and should not be interpreted as clinical validation or external generalization evidence.

## Licenses

- Code: MIT License, see `LICENSE-CODE-MIT.txt`.
- Synthetic benchmark data and documentation: CC BY 4.0, see `LICENSE-DATA-CC-BY-4.0.txt`.
- Third-party papers, guidelines, and templates are cited or included only where their licenses permit.

## Workspace Boundary

This directory must stay independent from other manuscript workspaces. Do not copy unrelated manuscript sources, experiment outputs, benchmark files, or private Overleaf packages into this artifact.
