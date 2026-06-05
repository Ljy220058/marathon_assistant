# STAI Run Summary: stai_s3_retrieval_plus_gold_50q_v02_run01

## Basic

- system: S3 / Full Workflow
- dataset: docs\paper_project\stai_benchmark_v0.2_50_question_draft.jsonl
- model: qwen2.5:latest
- evidence_mode: retrieval_plus_gold
- rows / unique_qids: 50 / 50
- elapsed_sec: None

## Status Counts

- partial_answer: 29
- answered: 14
- refused: 7

## Gate / Audit / Repair

- gate: {"answerable": 32, "partial": 11, "unanswerable": 7}
- audit: {"repair_required": 32, "pass": 16, "refuse_required": 2}
- repair: {"repaired_invalid_or_missing_citations": 29, "none": 14, "refused_due_to_insufficient_evidence_with_safety_deescalation": 3, "refused_due_to_insufficient_evidence": 4}

## Category x Status

- applied_reasoning: {"partial_answer": 11, "answered": 4}
- evidence_insufficient: {"refused": 5}
- fact: {"partial_answer": 11, "answered": 4}
- risk_safety: {"partial_answer": 7, "answered": 6, "refused": 2}

## Refusal Diagnostics

- designed_unanswerable_refused: 5 / 5
- verified_or_answerable_refused: 2 / 45
- citation_repair_count: 29
- refused_qids: STAI-P036, STAI-P040, STAI-P046, STAI-P047, STAI-P048, STAI-P049, STAI-P050

## Context / Latency

- avg_latency_sec: 28.765
- avg_evidence_contexts: 5.9
- avg_gold_contexts: 0.9
- avg_retrieved_contexts: 5
