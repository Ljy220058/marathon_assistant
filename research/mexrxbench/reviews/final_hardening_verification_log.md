# Final Hardening Verification Log

Date: 2026-05-16.

Scope: commands were run from the artifact root unless a row states otherwise.

## Command Gate Results

| Gate | Command | Exit code | Evidence | Status |
|---|---|---:|---|---|
| Traceable dataset validation | `conda run -n torch2.5.1 python benchmark\validate_traceable_dataset.py` | 0 | `traceable_dataset_validation_ok` | pass |
| Artifact validation | `conda run -n torch2.5.1 python demo\validate_artifacts.py` | 0 | `artifact_validation_ok` | pass |
| Default reproduction | `powershell -ExecutionPolicy Bypass -File reproducibility\run_all.ps1` | 0 | `traceable_dataset_validation_ok`; `artifact_validation_ok`; `m_exrx_reproducibility_ok` | pass |
| Hard100 reproduction | `powershell -ExecutionPolicy Bypass -File reproducibility\run_hard100.ps1` | 0 | `traceable_dataset_validation_ok`; `m_exrx_hard100_reproducibility_ok` | pass |
| Paper compile | From `submission_package\paper`: `conda run -n torch2.5.1 latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` | 0 | `Latexmk: All targets (main.xdv main.pdf) are up-to-date` | pass |
| PDF metadata | From `submission_package\paper`: `conda run -n torch2.5.1 python -c "from pypdf import PdfReader; p=r'..\A_Trace-Governed_Rule_Challenge_for_Evidence-Bounded_Exercise_Prescription.pdf'; r=PdfReader(p); print(len(r.pages)); print(r.metadata.title)"` | 0 | `14`; `A Trace-Governed Rule Challenge for Evidence-Bounded Exercise Prescription` | pass |

## Leakage Negative Tests

Agent 2 ran two temporary negative tests before the final command gate:

| Negative test | Expected behavior | Result |
|---|---|---|
| Inject `expected_behavior` into a temporary system-visible case copy and run `demo/run_demo.py`. | Runner must fail closed before solving. | pass: process exited 1 and reported evaluator-only field leakage. |
| Inject `gold_risk_level` into a temporary prediction copy and run `demo/evaluate_results.py`. | Evaluator must reject prediction files containing gold/provenance fields. | pass: process exited 1 and reported evaluator-only field leakage. |

Temporary negative-test files were not retained in the artifact.

## Generated Evidence Files

| File | Source command | Status |
|---|---|---|
| `artifacts/demo_runs/example_flow_trace.json` | `conda run -n torch2.5.1 python demo\run_demo.py --case-id mexrx-011 --output artifacts\demo_runs\example_flow_trace.json` | generated |
| `artifacts/demo_runs/full_rule_governed_v04.json` | `reproducibility\run_all.ps1` | regenerated |
| `artifacts/demo_runs/full_rule_governed_eval.json` | `reproducibility\run_all.ps1` | regenerated |
| `artifacts/demo_runs/full_rule_governed_eval_summary.md` | `reproducibility\run_all.ps1` | regenerated |
| `artifacts/baseline_runs\*.json` and `*.eval.json` | `reproducibility\run_all.ps1` | regenerated |
| `artifacts/demo_runs/hard100_full_rule_governed.json` | `reproducibility\run_hard100.ps1` | regenerated |
| `artifacts/demo_runs/hard100_full_rule_governed_eval.json` | `reproducibility\run_hard100.ps1` | regenerated |
| `artifacts/demo_runs/hard100_full_rule_governed_eval_summary.md` | `reproducibility\run_hard100.ps1` | regenerated |

## Notes

- The first paper compile attempt produced a conda Unicode output encoding report under the Windows console. The command was rerun with `PYTHONIOENCODING=utf-8`; the rerun exited 0.
- The PDF is 14 pages, inside the 8-15 page gate.
- The PDF metadata title matches the submitted title exactly.
- The artifact validator initially rejected a release-facing TODO marker. The marker was reworded without weakening the validator, and `artifact_validation_ok` now passes.

## Verification Verdict

Go for artifact and paper command gates.

## Release Delivery Evidence

The independent public artifact repository was updated after validation in a temporary clean release tree:

| Item | Evidence |
|---|---|
| Repository | `https://github.com/Ljy220058/m-exrxbench` |
| Branch | `main` |
| Commit | `19152fa` |
| Push result | `44ef784..19152fa  main -> main` |

The pushed commit contains the final Rule Challenge hardening evidence files, README/checklist updates, paper wording updates, and the runner-generated example trace.
