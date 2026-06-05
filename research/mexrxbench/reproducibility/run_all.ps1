$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

New-Item -ItemType Directory -Force -Path artifacts\demo_runs, artifacts\baseline_runs | Out-Null

if ($env:MEXRX_PYTHON) {
  $Python = @($env:MEXRX_PYTHON)
} else {
  $Python = @("python")
}
function Invoke-Python {
  & $Python[0] @($Python | Select-Object -Skip 1) @args
}

Invoke-Python benchmark\validate_traceable_dataset.py
Invoke-Python demo\run_demo.py --case-id mexrx-024 --output artifacts\demo_runs\single_red_flag.json
Invoke-Python demo\run_benchmark.py --cases benchmark\system_visible_cases.jsonl --output artifacts\demo_runs\full_rule_governed_v04.json
Invoke-Python demo\run_baselines.py --cases benchmark\system_visible_cases.jsonl --output-dir artifacts\baseline_runs

$BaselineSystems = @(
  "naked_llm",
  "vanilla_rag",
  "multi_agent_no_rule_gate",
  "full_rule_governed",
  "no_risk_gate",
  "no_evidence_gate",
  "no_contract",
  "no_repair",
  "no_auditor"
)
foreach ($System in $BaselineSystems) {
  Invoke-Python demo\evaluate_results.py --gold benchmark\gold_labels.jsonl --pred "artifacts\baseline_runs\$System.json" --output "artifacts\baseline_runs\$System.eval.json"
}

Invoke-Python demo\evaluate_results.py --gold benchmark\gold_labels.jsonl --pred artifacts\demo_runs\full_rule_governed_v04.json --output artifacts\demo_runs\full_rule_governed_eval.json
Invoke-Python demo\summarize_results.py --eval artifacts\demo_runs\full_rule_governed_eval.json --output artifacts\demo_runs\full_rule_governed_eval_summary.md
Invoke-Python benchmark\validate_traceable_dataset.py
Invoke-Python demo\validate_artifacts.py

Write-Output "m_exrx_reproducibility_ok"
