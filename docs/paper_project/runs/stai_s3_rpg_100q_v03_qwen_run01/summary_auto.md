# STAI Run Summary: stai_s3_rpg_100q_v03_qwen_run01

## Basic

- system: S3 / Full Workflow
- dataset: docs\paper_project\stai_benchmark_v0.3_100_question_draft.jsonl
- model: qwen2.5:latest
- evidence_mode: retrieval_plus_gold
- ablation_mode: full
- pre_gate_mode: off
- rows / unique_qids: 100 / 100
- elapsed_sec: 2331.709

## Status Counts

- partial_answer: 62
- answered: 24
- refused: 14

## Gate / Audit / Repair

- gate: {"answerable": 59, "partial": 27, "unanswerable": 14}
- audit: {"repair_required": 62, "pass": 24, "refuse_required": 14}
- repair: {"repaired_invalid_or_missing_citations": 62, "none": 24, "refused_due_to_insufficient_evidence_with_safety_deescalation": 5, "refused_due_to_insufficient_evidence": 9}
- pre_gate: {"not_triggered": 100}

## Category x Status

- applied_reasoning: {"partial_answer": 23, "answered": 7}
- evidence_insufficient: {"refused": 10}
- fact: {"partial_answer": 21, "answered": 9}
- risk_safety: {"partial_answer": 18, "answered": 8, "refused": 4}

## Refusal Diagnostics

- unanswerable_control_refused: 10 / 10
- designed_unanswerable_refused: 10 / 10
- verified_or_answerable_refused: 4 / 90
- citation_repair_count: 62
- refused_qids: STAI-P036, STAI-P040, STAI-P046, STAI-P047, STAI-P048, STAI-P049, STAI-P050, STAI-P081, STAI-P086, STAI-P096, STAI-P097, STAI-P098, STAI-P099, STAI-P100

## Context / Latency

- avg_latency_sec: 23.317
- avg_evidence_contexts: 5.9
- avg_gold_contexts: 0.9
- avg_retrieved_contexts: 5
