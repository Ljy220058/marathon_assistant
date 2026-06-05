# STAI Run Summary: stai_s3_rpg_40q_v03_llama3_run01

## Basic

- system: S3 / Full Workflow
- dataset: docs\paper_project\stai_benchmark_v0.3_100_question_draft.jsonl
- model: llama3:latest
- evidence_mode: retrieval_plus_gold
- ablation_mode: full
- pre_gate_mode: off
- rows / unique_qids: 40 / 40
- elapsed_sec: 578.799

## Status Counts

- partial_answer: 17
- answered: 13
- refused: 10

## Gate / Audit / Repair

- gate: {"answerable": 24, "partial": 6, "unanswerable": 10}
- audit: {"repair_required": 17, "pass": 13, "refuse_required": 10}
- repair: {"repaired_invalid_or_missing_citations": 17, "none": 13, "refused_due_to_insufficient_evidence": 9, "refused_due_to_insufficient_evidence_with_safety_deescalation": 1}
- pre_gate: {"not_triggered": 40}

## Category x Status

- applied_reasoning: {"answered": 5, "partial_answer": 5}
- evidence_insufficient: {"refused": 10}
- fact: {"partial_answer": 6, "answered": 4}
- risk_safety: {"answered": 4, "partial_answer": 6}

## Refusal Diagnostics

- unanswerable_control_refused: 10 / 10
- designed_unanswerable_refused: 10 / 10
- verified_or_answerable_refused: 0 / 30
- citation_repair_count: 17
- refused_qids: STAI-P046, STAI-P047, STAI-P048, STAI-P049, STAI-P050, STAI-P096, STAI-P097, STAI-P098, STAI-P099, STAI-P100

## Context / Latency

- avg_latency_sec: 14.469
- avg_evidence_contexts: 5.75
- avg_gold_contexts: 0.75
- avg_retrieved_contexts: 5
