# STAI Paper Artifact Index v0.1

Purpose: final paper-facing artifact index for the current STAI manuscript. This file separates artifacts used for manuscript claims from exploratory development records. It should be used before any public release to avoid leaking local absolute paths or unrelated product files.

## Validation Status

Fresh validation commands run on 2026-05-11:

```powershell
python scripts\validate_stai_benchmark_questions.py --dataset docs\paper_project\stai_benchmark_v0.3_100_question_draft.jsonl --expected-count 100
```

Result: `ok=true`, rows `100`, category counts `fact=30`, `applied_reasoning=30`, `risk_safety=30`, `evidence_insufficient=10`; evidence status counts `verified_span=90`, `designed_unanswerable=10`.

```powershell
python scripts\validate_stai_safety_stress_benchmark.py --dataset docs\paper_project\stai_safety_stress_benchmark_v0.2_30_question.jsonl --expected-count 30
```

Result: `ok=true`, rows `30`, stress category counts `prompt_injection=6`, `unsafe_request=8`, `citation_hallucination=6`, `overclaim_request=6`, `evidence_conflict=4`.

```powershell
python scripts\validate_benchmark_kb.py --evidence-items docs\paper_project\benchmark_kb_v0.2\evidence_items_v0.1.jsonl --qid-map docs\paper_project\benchmark_kb_v0.2\qid_to_gold_evidence_v0.2.json
```

Result: `ok=true`, evidence items `45`, mapped qids `90`, all evidence items marked `verified`.

## Paper-Facing Artifacts

| Artifact | Role in paper | Local file / run | Status |
| --- | --- | --- | --- |
| A | Main 100-question pilot benchmark | `docs/paper_project/stai_benchmark_v0.3_100_question_draft.jsonl` | validated |
| B | 30-prompt safety-stress benchmark | `docs/paper_project/stai_safety_stress_benchmark_v0.2_30_question.jsonl` | validated |
| C | Main benchmark evidence KB | `docs/paper_project/benchmark_kb_v0.2/evidence_items_v0.1.jsonl` | validated |
| D | Main benchmark qid-to-evidence map | `docs/paper_project/benchmark_kb_v0.2/qid_to_gold_evidence_v0.2.json` | validated |
| E | Main 100-question qwen full-workflow trace | `docs/paper_project/runs/stai_s3_rpg_100q_v03_qwen_run01/` | metadata + 100 outputs present |
| F | Qwen safety-stress trace | `docs/paper_project/runs/stai_safety_stress_30q_hardened_v04_run03/` | metadata + 30 outputs present |
| G | Llama3 safety-stress trace | `docs/paper_project/runs/stai_safety_stress_30q_hardened_v04_llama3_run03/` | metadata + 30 outputs present |
| H | Llama3 40-question main-benchmark subset | `docs/paper_project/runs/stai_s3_rpg_40q_v03_llama3_run01/` | metadata + 40 outputs present |
| I | DeepSeek 40-question main-benchmark subset | `docs/paper_project/runs/stai_s3_rpg_40q_v03_deepseek_v4_pro_run02/` | metadata + 40 outputs present |
| J | Qwen no-gate ablation subset | `docs/paper_project/runs/stai_ablation_no_gate_40q_v03_qwen_run02/` | metadata + 40 outputs present |
| K | Qwen no-audit ablation subset | `docs/paper_project/runs/stai_ablation_no_audit_40q_v03_qwen_run01/` | metadata + 40 outputs present |
| L | Qwen no-repair ablation subset | `docs/paper_project/runs/stai_ablation_no_repair_40q_v03_qwen_run01/` | metadata + 40 outputs present |
| M | Supplementary evidence-boundary dataset | `docs/paper_project/stai_evidence_boundary_20q_v0.1.jsonl` | validated separately |
| N | Qwen evidence-boundary trace | `docs/paper_project/runs/stai_s3_evidence_boundary_20q_qwen_run01/` | metadata + 20 outputs present |
| O | Llama3 evidence-boundary subset trace | `docs/paper_project/runs/stai_s3_evidence_boundary_10q_llama3_run01/` | metadata + 10 outputs present |
| P | Manual evidence-boundary adjudication | `docs/paper_project/64_STAI_evidence_boundary_spotcheck_adjudication_v0.1.md` | paper-facing diagnostic note |

## Run Metadata Summary

| Run id | Sample count | Model | Evidence mode | Pre-gate mode | Ablation mode | Prompt template |
| --- | ---: | --- | --- | --- | --- | --- |
| `stai_s3_rpg_100q_v03_qwen_run01` | 100 | `qwen2.5:latest` | `retrieval_plus_gold` | `off` | `full` | `s3_full_workflow_v0.2` |
| `stai_safety_stress_30q_hardened_v04_run03` | 30 | `qwen2.5:latest` | `retrieval_only` | `hardening_v0_4` | `full` | `s3_full_workflow_v0.2` |
| `stai_safety_stress_30q_hardened_v04_llama3_run03` | 30 | `llama3:latest` | `retrieval_only` | `hardening_v0_4` | `full` | `s3_full_workflow_v0.2` |
| `stai_s3_rpg_40q_v03_llama3_run01` | 40 | `llama3:latest` | `retrieval_plus_gold` | `off` | `full` | `s3_full_workflow_v0.2` |
| `stai_s3_rpg_40q_v03_deepseek_v4_pro_run02` | 40 | `deepseek-v4-pro` | `retrieval_plus_gold` | `off` | `full` | `s3_full_workflow_v0.2` |
| `stai_ablation_no_gate_40q_v03_qwen_run02` | 40 | `qwen2.5:latest` | `retrieval_plus_gold` | `off` | `no_gate` | `s3_full_workflow_v0.2` |
| `stai_ablation_no_audit_40q_v03_qwen_run01` | 40 | `qwen2.5:latest` | `retrieval_plus_gold` | `off` | `no_audit` | `s3_full_workflow_v0.2` |
| `stai_ablation_no_repair_40q_v03_qwen_run01` | 40 | `qwen2.5:latest` | `retrieval_plus_gold` | `off` | `no_repair` | `s3_full_workflow_v0.2` |
| `stai_s3_evidence_boundary_20q_qwen_run01` | 20 | `qwen2.5:latest` | `gold_only` | `off` | `full` | `s3_full_workflow_v0.2` |
| `stai_s3_evidence_boundary_10q_llama3_run01` | 10 | `llama3:latest` | `gold_only` | `off` | `full` | `s3_full_workflow_v0.2` |

Evaluation runner:

`scripts/run_stai_s3_full_workflow.py`

Validation scripts:

- `scripts/validate_stai_benchmark_questions.py`
- `scripts/validate_stai_safety_stress_benchmark.py`
- `scripts/validate_benchmark_kb.py`
- `scripts/validate_stai_evidence_boundary_pack.py`

## Development-Only Records

These files are useful for project history but should not be treated as final paper artifacts:

- early 50-question v0.2 run directories;
- smoke-test run directories;
- console stdout/stderr logs;
- product UI files and non-paper application code;
- local absolute-path build logs;
- exploratory draft notes before `40_STAI_method_section_v0.1.md`;
- generated local PDF build outputs unless required for submission.

## Minimal Public Reproducibility Package

Recommended include list:

- `docs/paper_project/paper_stai2026/main.tex`
- `docs/paper_project/paper_stai2026/sections/`
- `docs/paper_project/paper_stai2026/figures/`
- `docs/paper_project/paper_stai2026/references.bib`
- `docs/paper_project/paper_stai2026/llncs.cls`
- `docs/paper_project/paper_stai2026/splncs04.bst`
- paper-facing benchmark JSONL files listed above;
- benchmark KB files listed above;
- paper-facing run directories listed above, with `metadata.json` and `outputs.jsonl`;
- validation and runner scripts listed above;
- this artifact index.

Recommended exclude list:

- local build directories such as `build/`;
- Windows absolute paths in README or logs;
- Ollama model caches;
- unrelated application/product files;
- exploratory failed run directories unless explicitly documented as failure cases;
- private notes containing author identity or local environment details.

## P2 Expansion Decision Snapshot

For the current STAI target, the artifact base is sufficient for a workshop diagnostic paper if the claims remain conservative. Additional experiments should be chosen only if they answer a likely reviewer objection without expanding the page budget.
