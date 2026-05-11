# STAI Run Summary: stai_s3_gold_only_50q_run02

## Basic

- system: S3 / Full Workflow
- dataset: docs\paper_project\stai_benchmark_v0.2_50_question_draft.jsonl
- model: qwen2.5:latest
- evidence_mode: gold_only
- rows / unique_qids: 50 / 50
- elapsed_sec: 599.318

## Status Counts

- partial_answer: 24
- answered: 18
- refused: 8

## Gate / Audit / Repair

- gate: {"answerable": 34, "partial": 8, "unanswerable": 8}
- audit: {"repair_required": 26, "pass": 20, "refuse_required": 4}
- repair: {"repaired_invalid_or_missing_citations": 24, "none": 18, "refused_due_to_insufficient_evidence_with_safety_deescalation": 4, "refused_due_to_insufficient_evidence": 4}

## Category x Status

- applied_reasoning: {"answered": 6, "partial_answer": 9}
- evidence_insufficient: {"refused": 5}
- fact: {"partial_answer": 8, "answered": 7}
- risk_safety: {"partial_answer": 7, "answered": 5, "refused": 3}

## Refusal Diagnostics

- designed_unanswerable_refused: 5 / 5
- verified_or_answerable_refused: 3 / 45
- citation_repair_count: 24
- refused_qids: STAI-P036, STAI-P040, STAI-P045, STAI-P046, STAI-P047, STAI-P048, STAI-P049, STAI-P050

## Context / Latency

- avg_latency_sec: 11.985
- avg_evidence_contexts: 0.9
- avg_gold_contexts: 0.9
- avg_retrieved_contexts: 0
