# STAI Run Summary: stai_ablation_no_repair_50q_run01

## Basic

- system: S3 / Full Workflow
- dataset: docs\paper_project\stai_benchmark_v0.2_50_question_draft.jsonl
- model: qwen2.5:latest
- evidence_mode: retrieval_plus_gold
- ablation_mode: no_repair
- rows / unique_qids: 50 / 50
- elapsed_sec: 1181.984

## Status Counts

- answered: 43
- refused: 7

## Gate / Audit / Repair

- gate: {"answerable": 32, "partial": 11, "unanswerable": 7}
- audit: {"repair_required": 26, "pass": 17, "refuse_required": 7}
- repair: {"skipped_repair_required": 26, "none": 17, "refused_due_to_insufficient_evidence_with_safety_deescalation": 3, "refused_due_to_insufficient_evidence": 4}

## Category x Status

- applied_reasoning: {"answered": 15}
- evidence_insufficient: {"refused": 5}
- fact: {"answered": 15}
- risk_safety: {"answered": 13, "refused": 2}

## Refusal Diagnostics

- designed_unanswerable_refused: 5 / 5
- verified_or_answerable_refused: 2 / 45
- citation_repair_count: 0
- refused_qids: STAI-P036, STAI-P040, STAI-P046, STAI-P047, STAI-P048, STAI-P049, STAI-P050

## Context / Latency

- avg_latency_sec: 23.639
- avg_evidence_contexts: 5.9
- avg_gold_contexts: 0.9
- avg_retrieved_contexts: 5
