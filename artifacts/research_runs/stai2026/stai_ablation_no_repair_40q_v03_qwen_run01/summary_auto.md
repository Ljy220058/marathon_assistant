# STAI Run Summary: stai_ablation_no_repair_40q_v03_qwen_run01

## Basic

- system: S3 / Full Workflow
- dataset: docs\paper_project\stai_benchmark_v0.3_100_question_draft.jsonl
- model: qwen2.5:latest
- evidence_mode: retrieval_plus_gold
- ablation_mode: no_repair
- pre_gate_mode: off
- rows / unique_qids: 40 / 40
- elapsed_sec: 716.436

## Status Counts

- answered: 27
- refused: 13

## Gate / Audit / Repair

- gate: {"answerable": 21, "partial": 6, "unanswerable": 13}
- audit: {"repair_required": 19, "pass": 8, "refuse_required": 13}
- repair: {"skipped_repair_required": 19, "none": 8, "refused_due_to_insufficient_evidence_with_safety_deescalation": 4, "refused_due_to_insufficient_evidence": 9}
- pre_gate: {"not_triggered": 40}

## Category x Status

- applied_reasoning: {"answered": 10}
- evidence_insufficient: {"refused": 10}
- fact: {"answered": 10}
- risk_safety: {"answered": 7, "refused": 3}

## Refusal Diagnostics

- unanswerable_control_refused: 10 / 10
- designed_unanswerable_refused: 10 / 10
- verified_or_answerable_refused: 3 / 30
- citation_repair_count: 0
- refused_qids: STAI-P036, STAI-P040, STAI-P081, STAI-P046, STAI-P047, STAI-P048, STAI-P049, STAI-P050, STAI-P096, STAI-P097, STAI-P098, STAI-P099, STAI-P100

## Context / Latency

- avg_latency_sec: 17.91
- avg_evidence_contexts: 5.75
- avg_gold_contexts: 0.75
- avg_retrieved_contexts: 5
