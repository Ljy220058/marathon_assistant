$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

New-Item -ItemType Directory -Force -Path artifacts\demo_runs, artifacts\baseline_runs | Out-Null

$Python = @("conda", "run", "-n", "torch2.5.1", "python")

& $Python[0] $Python[1] $Python[2] $Python[3] $Python[4] demo\run_demo.py --case-id mexrx-024 --output artifacts\demo_runs\single_red_flag.json
& $Python[0] $Python[1] $Python[2] $Python[3] $Python[4] demo\run_benchmark.py --cases benchmark\system_visible_cases.jsonl --output artifacts\demo_runs\full_rule_governed_v04.json
& $Python[0] $Python[1] $Python[2] $Python[3] $Python[4] demo\run_baselines.py --cases benchmark\system_visible_cases.jsonl --output-dir artifacts\baseline_runs

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
  & $Python[0] $Python[1] $Python[2] $Python[3] $Python[4] demo\evaluate_results.py --gold benchmark\gold_labels.jsonl --pred "artifacts\baseline_runs\$System.json" --output "artifacts\baseline_runs\$System.eval.json"
}

& $Python[0] $Python[1] $Python[2] $Python[3] $Python[4] demo\evaluate_results.py --gold benchmark\gold_labels.jsonl --pred artifacts\demo_runs\full_rule_governed_v04.json --output artifacts\demo_runs\full_rule_governed_eval.json
& $Python[0] $Python[1] $Python[2] $Python[3] $Python[4] demo\summarize_results.py --eval artifacts\demo_runs\full_rule_governed_eval.json --output artifacts\demo_runs\full_rule_governed_eval_summary.md
& $Python[0] $Python[1] $Python[2] $Python[3] $Python[4] demo\validate_artifacts.py

Write-Output "m_exrx_reproducibility_ok"
