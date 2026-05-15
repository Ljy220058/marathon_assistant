$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Cases = "benchmark\hard_system_visible_cases.jsonl"
$Gold = "benchmark\hard_gold_labels.jsonl"
$Pred = "artifacts\demo_runs\hard100_full_rule_governed.json"
$Eval = "artifacts\demo_runs\hard100_full_rule_governed_eval.json"
$Summary = "artifacts\demo_runs\hard100_full_rule_governed_eval_summary.md"

if (-not (Test-Path $Cases)) {
  throw "Hard100 system-visible cases not found: $Cases"
}
if (-not (Test-Path $Gold)) {
  throw "Hard100 gold labels not found: $Gold"
}

New-Item -ItemType Directory -Force -Path artifacts\demo_runs | Out-Null

$Python = @("conda", "run", "-n", "torch2.5.1", "python")

& $Python[0] $Python[1] $Python[2] $Python[3] $Python[4] demo\run_benchmark.py --cases $Cases --output $Pred
& $Python[0] $Python[1] $Python[2] $Python[3] $Python[4] demo\evaluate_results.py --gold $Gold --pred $Pred --output $Eval
& $Python[0] $Python[1] $Python[2] $Python[3] $Python[4] demo\summarize_results.py --eval $Eval --output $Summary

Write-Output "m_exrx_hard100_reproducibility_ok"
