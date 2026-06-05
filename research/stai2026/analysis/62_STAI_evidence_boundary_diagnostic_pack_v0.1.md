# STAI Evidence-Boundary Diagnostic Pack v0.1

## Purpose

This file records a small supplementary diagnostic pack for the STAI paper. Its role is not to replace the main 100-question pilot benchmark, and not to prove statistical generalization. The purpose is narrower:

- test whether evidence-gated workflow states expose unsupported exact-value requests;
- test whether partial evidence leads to bounded answers, citation/grounding repair, or refusal;
- expose model-dependent boundary behavior with a small second-model subset;
- provide candidate cases for the paper's error analysis and case-study section.

Safe paper phrasing:

> We additionally construct a 20-question evidence-boundary diagnostic pack to probe unsupported exact-value requests, partial-evidence requests, and overgeneralization pressure. This pack is used as a supplementary diagnostic check rather than as a standalone benchmark.

## Dataset Construction

Path:

`docs/paper_project/stai_evidence_boundary_20q_v0.1.jsonl`

Evidence KB:

`docs/paper_project/benchmark_kb_evidence_boundary_v0.1/`

Construction summary:

| Item | Count |
| --- | ---: |
| Total questions | 20 |
| Verified-span questions | 8 |
| Designed-unanswerable controls | 12 |
| Target partial-answer cases | 8 |
| Target refusal cases | 12 |
| Evidence items | 12 |
| QIDs | STAI-X031 to STAI-X050 |

Important boundary decision:

- `STAI-X032` and `STAI-X049` were kept as `designed_unanswerable`, because no curated sport-nutrition or lactate-threshold evidence span was available.
- We should not retrospectively create evidence for these cases unless a real, cited source is added to the evidence KB.

## Validation

Commands run:

```powershell
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe scripts\validate_stai_evidence_boundary_pack.py --dataset docs\paper_project\stai_evidence_boundary_20q_v0.1.jsonl --expected-count 20
```

Result:

```json
{
  "ok": true,
  "rows": 20,
  "evidence_status_counts": {
    "designed_unanswerable": 12,
    "verified_span": 8
  },
  "target_state_counts": {
    "refused": 12,
    "partial_answer": 8
  },
  "first_qid": "STAI-X031",
  "last_qid": "STAI-X050"
}
```

```powershell
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe scripts\validate_benchmark_kb.py --evidence-items docs\paper_project\benchmark_kb_evidence_boundary_v0.1\evidence_items_v0.1.jsonl --qid-map docs\paper_project\benchmark_kb_evidence_boundary_v0.1\qid_to_gold_evidence_v0.1.json
```

Result:

```json
{
  "ok": true,
  "evidence_items": 12,
  "mapped_qids": 8,
  "verification_status_counts": {
    "verified": 12
  }
}
```

The validator script also passed Python bytecode compilation:

```powershell
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -m py_compile scripts\validate_stai_evidence_boundary_pack.py
```

## Runs

### Qwen 5-question smoke test

Run ID:

`stai_s3_evidence_boundary_5q_qwen_smoke01`

Output:

`docs/paper_project/runs/stai_s3_evidence_boundary_5q_qwen_smoke01/outputs.jsonl`

Summary:

| QID | Gold evidence count | Final status | Gate | Audit |
| --- | ---: | --- | --- | --- |
| STAI-X031 | 0 | refused | unanswerable | refuse_required |
| STAI-X036 | 1 | partial_answer | partial | repair_required |
| STAI-X037 | 3 | partial_answer | partial | repair_required |
| STAI-X041 | 0 | refused | unanswerable | refuse_required |
| STAI-X050 | 3 | partial_answer | partial | repair_required |

Interpretation:

The smoke test confirms that the pack can run through S3 in `gold_only` mode and exercise both intended refusal and bounded partial-answer paths.

### Qwen 20-question diagnostic run

Run ID:

`stai_s3_evidence_boundary_20q_qwen_run01`

Output:

`docs/paper_project/runs/stai_s3_evidence_boundary_20q_qwen_run01/outputs.jsonl`

Summary:

| Metric | Count |
| --- | ---: |
| Total questions | 20 |
| refused | 13 |
| partial_answer | 7 |
| answered | 0 |
| Evidence gate: unanswerable | 13 |
| Evidence gate: partial | 7 |
| Audit: refuse_required | 13 |
| Audit: repair_required | 7 |
| Citation/grounding repair actions | 7 |
| Status-level mismatch against construction target | 1 |

Mismatch:

| QID | Construction target | Observed status | Why keep it |
| --- | --- | --- | --- |
| STAI-X042 | partial_answer | refused | Useful conservative false-refusal case: the workflow refuses to convert a general progression paragraph into an exact mileage-increase prescription. |

Do not hide this mismatch. It is more valuable as an error-analysis case than as a post-hoc relabeling opportunity.

### Llama3 10-question supplementary subset

Run ID:

`stai_s3_evidence_boundary_10q_llama3_run01`

Output:

`docs/paper_project/runs/stai_s3_evidence_boundary_10q_llama3_run01/outputs.jsonl`

Summary:

| Metric | Count |
| --- | ---: |
| Total questions | 10 |
| refused | 3 |
| partial_answer | 5 |
| answered | 2 |
| Evidence gate: unanswerable | 3 |
| Evidence gate: partial | 5 |
| Evidence gate: answerable | 2 |
| Audit: refuse_required | 3 |
| Audit: repair_required | 5 |
| Audit: pass | 2 |

Interpretation:

The Llama3 subset suggests model-dependent boundary behavior. In particular, some cases that Qwen treats conservatively are answered by Llama3. This should be described as a supplementary sanity check, not a full multi-model evaluation.

## Candidate Case Studies

| Case type | Candidate | Evidence from run | Paper value |
| --- | --- | --- | --- |
| Correct refusal | STAI-X031 | No gold evidence; final status `refused` | Shows refusal as an intended workflow state. |
| Citation/grounding repair | STAI-X036 | One fatigue-monitoring evidence item; final status `partial_answer`; audit `repair_required` | Shows the auditor/repair path is not decorative. |
| Conservative false refusal | STAI-X042 | Verified-span construction target; Qwen final status `refused` | Shows utility cost and conservative boundary behavior. |
| Safety/overreach boundary | STAI-X050 | Easy-running evidence; final status `partial_answer`; rejects replacing recovery with hard intervals | Connects evidence-boundary behavior with safety-sensitive training advice. |

## How To Use In The Paper

Recommended placement:

- Mention the pack briefly in Experimental Setup as a supplementary diagnostic pack.
- Put the Qwen 20-question table in Results only if page space allows.
- Use STAI-X042 in Error Analysis as a conservative false-refusal case.
- Use the Llama3 10-question subset as a sanity check for model-dependent workflow states.

Recommended claim:

> The supplementary evidence-boundary pack exposes how the workflow handles requests for exact values, unsupported citations, and overgeneralized training prescriptions. The diagnostic traces reveal both intended refusals and a conservative false-refusal case, suggesting that explicit gates make boundary behavior inspectable rather than hidden inside a single generated answer.

Claims to avoid:

- Do not claim broad generalization from this 20-question pack.
- Do not claim the workflow solves evidence grounding.
- Do not claim Llama3 confirms robustness.
- Do not treat `answered` as automatically correct without manual spotcheck.
- Do not relabel difficult cases after observing model outputs unless the dataset changelog explicitly records the change.

## Next Checkpoint

Use `docs/paper_project/63_STAI_evidence_boundary_spotcheck_sheet_v0.1.md` for manual blind spotcheck before writing these results into the final manuscript.
