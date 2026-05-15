# RuleML+RR 2026 Submission Hardening TODO v3

Goal: upgrade the M-EXRx Rule Challenge package from "Conditional Go" to a strong submission package with no known blocking defects.

Working boundary: all work stays inside this artifact directory. Do not modify or copy sources from unrelated manuscript workspaces.

## Hard Gates

| Gate | Required State | Evidence |
|---|---|---|
| A. Venue and format | CEURART English paper, 8-15 pages, correct venue line: Vilnius, Lithuania, 24-26 August 2026 | `paper/main.tex`, final named PDF, LaTeX log |
| B. Artifact release | Public GitHub target, code MIT, synthetic benchmark/data/docs CC BY 4.0 | `README.md`, license files, `open_science_release_plan.md`, `artifacts/artifact_manifest.json` |
| C. Reproducibility | One-command reproduction passes and prints both success sentinels | `reproducibility/run_all.ps1`, `artifacts/demo_runs/` |
| D. Safety and claim discipline | No clinical-validation claim; metrics described as synthetic benchmark rule-compliance signals | `paper/main.tex`, `ethics/`, `submission_go_no_go.md` |
| E. Reviewer UX | Reviewer can run validator, demo, benchmark, baselines, evaluator, and trace viewer from README | `README.md`, `demo/README.md`, `demo/static_trace_viewer.html` |
| F. Release hygiene | No local paths, secrets, stale markers, wrong venue date, or unintended unrelated manuscript content in release files | `demo/validate_artifacts.py`, pre-release text scan |

## Team Mode

Maximum 3 subagents per hardening round:

| Agent | Responsibility | Output |
|---|---|---|
| Venue Editor | CEURART, page count, venue/date, references, stale marker removal | archived review record |
| Artifact/Repro Auditor | licenses, manifest, reproducibility, local path/secrets/workspace-boundary scans | archived review record |
| Safety/Benchmark Reviewer | synthetic benchmark, gold split, evaluator claims, 1.000 result discipline | archived review record |

Integrated round output is retained with non-submission review records.

## Submission-Critical Tasks

- [x] Fix RuleML+RR 2026 venue/date in `paper/main.tex`.
- [x] Replace provisional repository/license metadata with the public GitHub target and selected licenses.
- [x] Add `LICENSE-CODE-MIT.txt` and `LICENSE-DATA-CC-BY-4.0.txt`.
- [x] Add reviewer quick path to `README.md` and `demo/README.md`.
- [x] Make demo outputs deterministic by removing wall-clock timestamps.
- [x] Strip gold-only `rationale` and `notes` fields from runner-visible cases.
- [x] Update `run_all.ps1` to use `conda run -n torch2.5.1 python`.
- [x] Recompute baseline eval files inside `run_all.ps1`.
- [x] Strengthen `demo/validate_artifacts.py` for release files, gold split, result/trace shape, manifest, metrics, local paths, workspace boundary, and secret scans.
- [x] Add release `.gitignore` for TeX/Python build products.
- [x] Add `requirements.txt` documenting that runtime uses Python standard library only.
- [x] Update paper claims so 1.000 results are described as deterministic synthetic benchmark compliance, not clinical validation.
- [x] Add static trace viewer visibility in artifact availability and README.
- [x] Record three reviewer reports and integrated hardening round review.
- [ ] Push the branch containing this artifact to the public GitHub repository.
- [ ] Run clean-clone reproduction from the public repository after push.

## Final Gate Commands

Run from the artifact root:

```powershell
conda run -n torch2.5.1 python demo\validate_artifacts.py
powershell -ExecutionPolicy Bypass -File reproducibility\run_all.ps1
conda run -n torch2.5.1 python demo\validate_artifacts.py
```

Paper compile gate:

```powershell
cd paper
latexmk -C main.tex
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
cd ..
```

Pre-release text scan: run `demo/validate_artifacts.py` and a repository-level
secret scan before upload.

## Acceptance Standard

Submit to Rule Challenge only when:

- PDF recompiles from current source and remains 8-15 pages.
- Validator and reproduction script pass after the last file edit.
- Public GitHub branch contains this artifact directory.
- README reviewer path works from a clean clone.
- No stale markers, local paths, wrong venue date, private credentials, or unintended unrelated manuscript content appear in release files.
- The manuscript avoids clinical validation claims and states the synthetic benchmark limitation clearly.
