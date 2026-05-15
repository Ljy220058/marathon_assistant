# Rule Challenge Artifact Checklist

Public repository: https://github.com/Ljy220058/marathon_assistant

Artifact path: this directory in the public repository.

## Submission-Critical Gates

| Gate | Required Evidence | Status |
|---|---|---|
| Venue/format | CEURART paper, 8-15 pages, correct RuleML+RR 2026 venue line | ready for final compile check |
| Challenge definition | `challenge_positioning.md`, `paper/main.tex` | present |
| Rules and auditability | `rule_spec/`, `paper/rule_examples.tex` | present |
| Benchmark | 500 synthetic cases plus system/gold split | present |
| Supplemental hard stress subset | v0.4-hard-100 reviewer-facing stress cases and separate evaluation | present; evaluated separately |
| Evaluation | baselines, proposed system output, independent evaluator | present |
| Reproducibility | `reproducibility/run_all.ps1`, validation logs | present |
| Open science | public GitHub target, MIT code license, CC BY 4.0 data/docs license | present |
| Safety boundary | ethics/scope files and manuscript limitation text | present |

## Core Technical Artifacts

| Artifact | Path | Note |
|---|---|---|
| Default 500-case benchmark | `benchmark/m_exrxbench_v0.4_500_cases.jsonl` | synthetic cases |
| System-visible split | `benchmark/system_visible_cases.jsonl` | no gold labels |
| Gold labels | `benchmark/gold_labels.jsonl` | evaluator-only |
| Supplemental hard subset | `benchmark/m_exrxbench_v0.4_hard_100_cases.jsonl` | 100 hard stress cases |
| Result schema | `benchmark/result_schema.json` | shared by all systems |
| Trace schema | `rule_spec/trace_schema.json` | audit trace contract |
| Demo runner | `demo/run_demo.py` | single-case output |
| Benchmark runner | `demo/run_benchmark.py` | proposed reference system |
| Baseline runner | `demo/run_baselines.py` | ablation baselines |
| Independent evaluator | `demo/evaluate_results.py` | reads gold labels |
| Validator | `demo/validate_artifacts.py` | schema and file checks |
| Trace viewer | `demo/static_trace_viewer.html` | reviewer UX surface |
| CEURART manuscript | `paper/main.tex`, `paper/main.pdf` | paper package |

## Reviewer Commands

Run from the artifact root:

```powershell
conda run -n torch2.5.1 python demo\validate_artifacts.py
powershell -ExecutionPolicy Bypass -File reproducibility\run_all.ps1
powershell -ExecutionPolicy Bypass -File reproducibility\run_hard100.ps1
```

The reproduction script must regenerate the proposed-system reviewer output at:

```text
artifacts\demo_runs\full_rule_governed_v04.json
```

Paper compile gate:

```powershell
cd paper
latexmk -C main.tex
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

Pre-release text scan: run `demo/validate_artifacts.py` and a repository-level
secret scan before upload.

## Open Science Notes

- Benchmark cases are synthetic and must be described as synthetic.
- The default submitted artifact is M-EXRxBench v0.4 with 500 synthetic cases; v0.3/v0.2 files are historical/archive inputs only.
- M-EXRxBench v0.4 consists of the default 500-case balanced synthetic benchmark plus a supplemental 100-case hard stress subset. The hard100 subset is for reviewer-facing stress testing of rule priority, safety refusal, evidence boundary, and prompt/retrieval injection; it is not clinical validation, external generalization proof, or a replacement for the default v0.4/500 benchmark.
- Current hard100 reference result: status accuracy 0.670, risk accuracy 0.720, unsafe-advice rate 0.090, unsupported-prescription rate 0.000, trace completeness 1.000.
- Gold labels are evaluator-only and must not be provided to systems.
- Reported metrics are benchmark rule-compliance signals, not clinical validation.
- Unrelated manuscript materials are excluded from this artifact package.
- Code license: MIT. Synthetic benchmark data and documentation license: CC BY 4.0.
