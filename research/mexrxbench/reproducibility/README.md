# Reproducibility

Run from the artifact root. The reference artifact is deterministic and uses
only the Python standard library. The recommended local command uses the
workspace conda environment, but the scripts do not require PyTorch, GPU access,
network access, an external LLM API, or private data.

## Environment

- Operating system used for the submitted reviewer path: Windows.
- Python: 3.10 or later is sufficient for the standard-library scripts.
- Tested command prefix in this workspace:

```powershell
conda run -n torch2.5.1 python
```

- Dependency file: `requirements.txt`. It intentionally contains no third-party
  runtime dependency; it records that the runtime uses the Python standard
  library only.

## One-Command Default Reproduction

```powershell
powershell -ExecutionPolicy Bypass -File reproducibility\run_all.ps1
```

The script runs:

1. one red-flag demo case
2. the proposed full rule-governed system
3. baseline/proposed-system batch outputs, including fine-grained component ablations
4. independent evaluation
5. Markdown summary rendering
6. artifact validation

The expected terminal sentinel is:

```text
m_exrx_reproducibility_ok
```

The default script regenerates:

```text
artifacts\demo_runs\single_red_flag.json
artifacts\demo_runs\full_rule_governed_v04.json
artifacts\demo_runs\full_rule_governed_eval.json
artifacts\demo_runs\full_rule_governed_eval_summary.md
artifacts\baseline_runs\*.json
artifacts\baseline_runs\*.eval.json
```

## Supplemental Hard-100 Stress Set

Run the hard stress subset separately:

```powershell
powershell -ExecutionPolicy Bypass -File reproducibility\run_hard100.ps1
```

The expected outputs are:

```text
artifacts\demo_runs\hard100_full_rule_governed.json
artifacts\demo_runs\hard100_full_rule_governed_eval.json
artifacts\demo_runs\hard100_full_rule_governed_eval_summary.md
```

## Evaluator and Gold-Label Boundary

The independent evaluator is:

```text
demo\evaluate_results.py
```

It reads `benchmark\gold_labels.jsonl`. System runners read only
`benchmark\system_visible_cases.jsonl`. The validator checks that evaluator-only
fields are absent from the system-visible split.

## Randomness and Seeds

No runtime random seed is required for the reported metrics. The runner and
baselines do not sample, shuffle, call stochastic models, or use randomized
search. Cases are processed in file order, rule branches are deterministic, and
trace timestamps are fixed metadata. Fields such as `source_seed_id` are
synthetic-case provenance labels, not runtime random seeds.

No external model is required for this deterministic Rule Challenge reference artifact.
