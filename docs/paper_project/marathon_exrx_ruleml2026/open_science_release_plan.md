# Open Science And Resource Release Plan

## Release Goal

Provide enough material for Rule Challenge reviewers to inspect, run, and extend the challenge without relying on private files.

Public artifact repository: https://github.com/Ljy220058/m-exrxbench

Artifact path: branch root.

## Public Resources

| Resource | Path | Release Status |
|---|---|---|
| CEURART paper | `paper/main.tex`, `submission_package/A_Trace-Governed_Rule_Challenge_for_Evidence-Bounded_Exercise_Prescription.pdf` | ready for final polish |
| Benchmark schema | `benchmark/m_exrxbench_schema.json` | present |
| Default 500-case benchmark | `benchmark/m_exrxbench_v0.4_500_cases.jsonl` | present |
| System-visible cases | `benchmark/system_visible_cases.jsonl` | present |
| Gold labels | `benchmark/gold_labels.jsonl` | present, evaluator-only |
| Rule specifications | `rule_spec/*.md`, `rule_spec/*.json` | present |
| Demo runner | `demo/run_demo.py` | present |
| Benchmark and baseline runners | `demo/run_benchmark.py`, `demo/run_baselines.py` | present |
| Independent evaluator | `demo/evaluate_results.py` | present |
| Sample traces and outputs | `artifacts/sample_trace.json`, `artifacts/demo_runs/` | present |
| Static trace viewer | `demo/static_trace_viewer.html` | present |

## License Policy

- Code: MIT License.
- Synthetic benchmark data and documentation: Creative Commons Attribution 4.0 International (CC BY 4.0).
- Paper text follows the submission venue's author copyright and CC BY policy.
- Third-party references are cited only and are not redistributed unless their license permits redistribution.

## Data Format

- Default artifact: M-EXRxBench v0.4 with 500 synthetic cases. v0.3/v0.2 files are retained only as historical/archive benchmark snapshots, not reviewer runner inputs.
- Cases: JSONL.
- Gold labels: JSONL, separated from system-visible input.
- Trace: JSON.
- Result summaries: JSON plus Markdown summary.
- Paper: CEURART LaTeX and PDF.

## Extension Points

- Add new exercise domains by replacing protocol rules and action library.
- Add curated guidelines through the evidence-to-rule promotion protocol.
- Add new risk families through the hazard model.
- Add new baselines when they emit `benchmark/result_schema.json`.

## Non-Public Or Excluded Content

- Unrelated manuscript sources and outputs.
- Real user health/profile data.
- Private API keys, local environment files, model credentials, cookies, or tokens.
- Large generated figure variants unless needed for final submission.

## Release Checklist Before Upload

- [x] Public GitHub release target identified.
- [x] README includes one-command reproduction and reviewer quick path.
- [x] Code license selected: MIT.
- [x] Benchmark/data/documentation license selected: CC BY 4.0.
- [x] Gold split documented.
- [x] Artifact manifest generated.
- [ ] Clean-clone reproduction run recorded after pushing the public branch.
- [ ] Final citation and page-layout check completed after last manuscript edit.
