# Demo Runners

This folder contains deterministic Rule Challenge runners for the rule-governed M-EXRx reference solution. The reviewer path below uses the current default M-EXRxBench v0.4/500 synthetic benchmark and writes `artifacts\demo_runs\full_rule_governed_v04.json`. Run commands from the artifact root. A supplemental `v0.4-hard-100` stress subset is available as a separate reviewer-facing stress test and is not a default runner input.

## Reviewer Quick Path

```powershell
conda run -n torch2.5.1 python demo\run_demo.py --case-id mexrx-024 --output artifacts\demo_runs\single_red_flag.json
conda run -n torch2.5.1 python demo\run_benchmark.py --cases benchmark\system_visible_cases.jsonl --output artifacts\demo_runs\full_rule_governed_v04.json
conda run -n torch2.5.1 python demo\run_baselines.py --cases benchmark\system_visible_cases.jsonl --output-dir artifacts\baseline_runs
conda run -n torch2.5.1 python demo\evaluate_results.py --gold benchmark\gold_labels.jsonl --pred artifacts\demo_runs\full_rule_governed_v04.json --output artifacts\demo_runs\full_rule_governed_eval.json
conda run -n torch2.5.1 python demo\summarize_results.py --eval artifacts\demo_runs\full_rule_governed_eval.json --output artifacts\demo_runs\full_rule_governed_eval_summary.md
conda run -n torch2.5.1 python demo\validate_artifacts.py
```

One-command reproduction:

```powershell
powershell -ExecutionPolicy Bypass -File reproducibility\run_all.ps1
```

## Outputs

- Final plan or refusal text.
- JSON trace with risk level, rules fired, evidence IDs, action IDs, audit result, and repair log.
- Baseline comparison outputs using the same result schema.
- Static trace viewer: `demo/static_trace_viewer.html`.

The demo is a rule-compliance artifact over a synthetic benchmark. It does not call an external LLM and does not provide clinical validation, real-world safety evidence, generalization evidence, or athlete-outcome proof.

## Supplemental Hard Stress Subset

`M-EXRxBench v0.4-hard-100` is a 100-case supplemental stress subset for rule priority, safety refusal, evidence boundary, and prompt/retrieval injection. It should be evaluated separately from the default v0.4/500 benchmark:

```powershell
powershell -ExecutionPolicy Bypass -File reproducibility\run_hard100.ps1
```

Current reference result: status accuracy 0.670, risk accuracy 0.720, unsafe-advice rate 0.090, unsupported-prescription rate 0.000, trace completeness 1.000.
