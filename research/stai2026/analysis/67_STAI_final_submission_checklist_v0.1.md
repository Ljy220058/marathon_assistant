# STAI Final Submission Checklist v0.1

Date: 2026-05-13

Scope: final hygiene check for the current STAI workshop submission package.

## 1. Final PDFs

| File | Role | Current status |
| --- | --- | --- |
| `docs/paper_project/paper_stai2026/build_8p/main_8p.pdf` | Compact submission PDF | Built locally; 7 pages. |
| `docs/paper_project/paper_stai2026/build/main.pdf` | Full manuscript PDF | Built locally; 16 pages. |

The 8-page PDF is the recommended upload if the submission target requires a short workshop paper. The 16-page PDF remains the full LNCS-style manuscript.

## 2. Anonymous Submission State

| Item | Status |
| --- | --- |
| Author field | `Anonymous Author(s)` in both `main.tex` and `main_8p.tex`. |
| Running author | `Anonymous Author(s)` in both entry files. |
| Affiliation | `Paper under double-blind review`. |
| Acknowledgements | Not included in the review PDF. |
| Local paths in manuscript body | Not present in manuscript source. |
| Author-identifying URL | Not included in the manuscript. |

## 3. Claim Boundary

Supported claims:

- The paper studies a workflow-level diagnostic setup for safety-sensitive advisory RAG.
- The workflow separates request filtering, evidence gating, risk gating, evidence-constrained generation, independent grounding audit, bounded citation/grounding repair, refusal, and final answer states.
- The 100-question benchmark is a focused pilot benchmark, not a large-scale public benchmark.
- The 30-prompt safety suite is a targeted constructed stress suite, not a general adversarial benchmark.
- The qwen, llama3, and DeepSeek results are diagnostic and supplementary; they do not establish broad model generalization.

Forbidden or unsupported claims:

- Clinically safe, medically validated, deployment-ready, or coaching-efficacy validated.
- Robust against prompt injection or generally secure against adversarial attacks.
- Expert-validated benchmark.
- Large-scale benchmark.
- New foundation model or generally novel multi-agent architecture.

## 4. Claim-to-Evidence Map

| Manuscript claim | Supporting artifact | Boundary |
| --- | --- | --- |
| Main benchmark has 100 questions with 90 evidence-backed and 10 designed-unanswerable controls. | `stai_benchmark_v0.3_100_question_draft.jsonl`; validation recorded in `65_STAI_artifact_index_v0.1.md`. | Pilot, author-authored benchmark. |
| Full workflow produced 24 `answered`, 62 `partial_answer`, and 14 `refused` outputs with qwen2.5. | `runs/stai_s3_rpg_100q_v03_qwen_run01/outputs.jsonl`; numeric audit in `55_STAI_claim_evidence_audit_v0.1.md`. | Internal diagnostic measurement. |
| Designed-unanswerable controls were refused 10 / 10 in the main run. | Same main run and dataset evidence status. | Does not imply real-world refusal correctness. |
| Main run had 4 / 90 false refusals. | Same main run; qids listed in `55_STAI_claim_evidence_audit_v0.1.md`. | Utility-cost signal, not population estimate. |
| Safety-stress prompts were refused 30 / 30 for qwen and llama3. | `stai_safety_stress_30q_hardened_v04_run03`; `stai_safety_stress_30q_hardened_v04_llama3_run03`. | Targeted deterministic hardening only. |
| Llama3 and DeepSeek 40-question subsets provide supplementary model sanity checks. | `stai_s3_rpg_40q_v03_llama3_run01`; `stai_s3_rpg_40q_v03_deepseek_v4_pro_run02`. | Not a full multi-model evaluation. |
| Ablations show the diagnostic role of gates, audit, and repair. | `stai_ablation_no_gate_40q_v03_qwen_run02`; `stai_ablation_no_audit_40q_v03_qwen_run01`; `stai_ablation_no_repair_40q_v03_qwen_run01`. | 40-question subset only. |

## 5. Figure and Artifact State

| Item | Status |
| --- | --- |
| Figure 1 source | `figures/figure1_method_workflow_nature.svg`. |
| Figure 1 manuscript asset | `figures/figure1_method_workflow_nature.pdf`. |
| Figure 1 PNG preview | `figures/figure1_method_workflow_nature.png`. |
| Artifact index | `65_STAI_artifact_index_v0.1.md`. |
| Claim-evidence audit | `55_STAI_claim_evidence_audit_v0.1.md`. |

## 6. Build Verification

Commands used:

```powershell
cd docs\paper_project\paper_stai2026
C:\Users\26318\.codex\.tmp\bundled-marketplaces\openai-bundled\plugins\latex-tectonic\bin\tectonic.exe -k --keep-logs -o build_8p main_8p.tex
C:\Users\26318\.codex\.tmp\bundled-marketplaces\openai-bundled\plugins\latex-tectonic\bin\tectonic.exe -k --keep-logs -o build main.tex
```

Checks to repeat before upload:

- PDF opens.
- Page count matches the intended submission format.
- Log scan has no undefined citation/reference warnings.
- Log scan has no `Overfull \hbox` warnings.
- First page remains anonymous.

Latest verification result on 2026-05-13:

- `stai2026_submission_main_8p_anonymous.pdf`: 7 pages; first page contains `Anonymous Author(s)`; no `Luo Jinyuan` or `罗锦源`.
- `stai2026_submission_main_full_anonymous.pdf`: 16 pages; first page contains `Anonymous Author(s)`; no `Luo Jinyuan` or `罗锦源`.
- Log scan found no undefined citation/reference warnings.
- Log scan found no `Overfull \hbox` warnings.
- Strict source-zip scan found no local Windows path, author name, or `sk-...` style API key pattern.
- 25-item author-side spotcheck is recorded in `68_STAI_25_item_author_spotcheck_v0.1.md`; it must be described only as a diagnostic sanity check, not expert validation.

## 7. Remaining Human Submission Checks

- Confirm the exact STAI submission track and page limit at upload time.
- Confirm whether STAI/CMT requests anonymous or non-anonymous author metadata outside the PDF.
- If the submission form asks for authors, enter real metadata in the system while keeping the PDF anonymous unless instructed otherwise.
- Do not upload local build logs or README files containing local absolute paths if a strict anonymous source package is requested.
