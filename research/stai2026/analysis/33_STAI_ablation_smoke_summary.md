# STAI Ablation Smoke Summary

This note records the executable ablation tests for the S3 workflow. Smoke tests check whether the module boundaries behave as expected; full 50-question ablations are now available for all three module removals.

## 1. Smoke setup

Shared slice:

- `STAI-P005` as an answerable fact question
- `STAI-P046` as a designed-unanswerable control
- evidence mode: `retrieval_plus_gold`

### Runs

| run | ablation_mode | status pattern | note |
|---|---|---|---|
| `stai_ablation_no_audit_smoke01` | `no_audit` | answered / refused | Audit is skipped; gate refusal still works for the control item. |
| `stai_ablation_no_gate_smoke01` | `no_gate` | partial_answer / partial_answer | Gate is bypassed; the designed-unanswerable control is no longer refused. |
| `stai_ablation_no_repair_smoke01` | `no_repair` | answered / refused | Repair is skipped for answerable items but gate refusal still works. |

## 2. What this already tells us

- The `no_gate` mode is the strongest proof that the gate matters: it converts the control item from refusal to a non-refusal path.
- The `no_audit` mode keeps the gate behavior but removes the independent audit pass.
- The `no_repair` mode preserves answer generation while preventing citation repair from changing the final answer.

## 3. Smoke outputs

- `docs/paper_project/runs/stai_ablation_no_audit_smoke01/summary_auto.md`
- `docs/paper_project/runs/stai_ablation_no_gate_smoke01/summary_auto.md`
- `docs/paper_project/runs/stai_ablation_no_repair_smoke01/summary_auto.md`

## 4. Full-run next step

### Completed full run: no_gate

| run | N | ablation_mode | answered | partial_answer | refused | designed-unanswerable refused | citation repair |
|---|---:|---|---:|---:|---:|---:|---:|
| `stai_ablation_no_gate_50q_run01` | 50 | `no_gate` | 3 | 47 | 0 | 0 / 5 | 47 |

Interpretation:

- Without Evidence Gate, all 50 samples were forced into an answerable path.
- The 5 designed-unanswerable controls were no longer refused; all became `partial_answer`.
- This directly supports the paper claim that Evidence Gate contributes measurable refusal control, not just prompt complexity.

Artifact:

- `docs/paper_project/runs/stai_ablation_no_gate_50q_run01/summary_auto.md`

### Full runs

| run | N | ablation_mode | answered | partial_answer | refused | designed-unanswerable refused | verified-answerable false refusal | citation repair |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| `stai_ablation_no_gate_50q_run01` | 50 | `no_gate` | 3 | 47 | 0 | 0 / 5 | 0 / 45 | 47 |
| `stai_ablation_no_audit_50q_run01` | 50 | `no_audit` | 43 | 0 | 7 | 5 / 5 | 2 / 45 | 0 |
| `stai_ablation_no_repair_50q_run01` | 50 | `no_repair` | 43 | 0 | 7 | 5 / 5 | 2 / 45 | 0 |

Interpretation:

- `no_gate` is the strongest evidence for the value of Evidence Gate: it destroys refusal control and converts all designed-unanswerable controls into non-refusal outputs.
- `no_audit` shows that skipping audit preserves gate-based refusal behavior but removes the independent verification stage.
- `no_repair` shows that skipping repair preserves answer/refusal counts on this slice, but it prevents citation repair from changing `partial_answer` behavior.

Artifacts:

- `docs/paper_project/runs/stai_ablation_no_gate_50q_run01/summary_auto.md`
- `docs/paper_project/runs/stai_ablation_no_audit_50q_run01/summary_auto.md`
- `docs/paper_project/runs/stai_ablation_no_repair_50q_run01/summary_auto.md`

Recommended follow-up:

- Write a compact ablation results table for the paper.
- Add one sentence in the method section clarifying the meaning of each ablation mode.
- Keep the smoke section as an internal verification note, not as a paper table.
