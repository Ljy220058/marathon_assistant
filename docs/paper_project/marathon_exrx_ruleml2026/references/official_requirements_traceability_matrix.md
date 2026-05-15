# Official Requirements Traceability Matrix

| Official Requirement | Current Artifact Evidence | Current Status | Remaining Gate |
|---|---|---|---|
| Define the Problem | `paper/main.tex`, `challenge_positioning.md` | pass | Final wording check before upload |
| Relevant Datasets | `benchmark/m_exrxbench_v0.4_500_cases.jsonl`, `benchmark/system_visible_cases.jsonl`, `benchmark/gold_labels.jsonl` | pass | Keep v0.4 as default runner input; v0.3/v0.2 are archive snapshots only |
| Evaluation Criteria | `benchmark/scoring_rubric.md`, `demo/evaluate_results.py`, `artifacts/demo_runs/full_rule_governed_eval_summary.md` | pass | Clean-clone reproduction |
| Highlight Innovation | `paper/main.tex`, `references/novelty_gap_review.md`, `rule_spec/*` | pass | Avoid overclaiming clinical safety |
| Illustrate Use Cases | `artifacts/sample_trace.json`, `demo/static_trace_viewer.html`, `paper/main.tex` | pass | Final figure/table placement check |
| Accessibility | `README.md`, `demo/README.md`, `artifact_checklist.md` | pass | Confirm reviewer path on a fresh clone |
| User Experience | `artifacts/sample_final_plan.md`, `demo/static_trace_viewer.html` | pass | Keep trace viewer link visible in README |
| Open Science | `open_science_release_plan.md`, `artifacts/artifact_manifest.json`, license files | pass | Publish final branch/release |
| Resources | `artifact_checklist.md`, `submission_go_no_go.md`, `reproducibility/run_all.ps1` | pass | Last venue/format check |
| Original English Paper | `paper/main.tex`, final named PDF | pass | PDF inspection after final edits |
| CEURART 8-15 pages | `submission_package/A_Trace-Governed_Rule_Challenge_for_Evidence-Bounded_Exercise_Prescription.pdf` | pass, 14 pages | Maintain page range |

## Current Submission Evidence

```text
benchmark/system_visible_cases.jsonl -> 500 system-visible cases
benchmark/gold_labels.jsonl -> 500 evaluator-only labels
artifacts/demo_runs/full_rule_governed_v04.json -> proposed-system reviewer output
reproducibility/run_all.ps1 -> artifact_validation_ok + m_exrx_reproducibility_ok
submission_package/A_Trace-Governed_Rule_Challenge_for_Evidence-Bounded_Exercise_Prescription.pdf -> 14-page CEURART PDF
```

## Pre-Upload Must-Recheck Items

- CMT Rule Challenge track selection.
- RuleML+RR 2026 official deadline, template, and author-policy page.
- Public repository branch/release URL.
- Clean-clone reproduction command output.
- Benchmark v0.4 file count and optional hashes.
