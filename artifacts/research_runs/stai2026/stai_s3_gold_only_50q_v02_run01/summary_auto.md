# STAI Run Summary: stai_s3_gold_only_50q_v02_run01

## Basic

- system: S3 / Full Workflow
- dataset: docs\paper_project\stai_benchmark_v0.2_50_question_draft.jsonl
- model: qwen2.5:latest
- evidence_mode: gold_only
- rows / unique_qids: 50 / 50
- elapsed_sec: 711.25

## Status Counts

- partial_answer: 27
- answered: 18
- refused: 5

## Gate / Audit / Repair

- gate: {"answerable": 34, "partial": 11, "unanswerable": 5}
- audit: {"repair_required": 29, "pass": 18, "refuse_required": 3}
- repair: {"repaired_invalid_or_missing_citations": 27, "none": 18, "refused_due_to_insufficient_evidence": 4, "refused_due_to_insufficient_evidence_with_safety_deescalation": 1}

## Category x Status

- applied_reasoning: {"answered": 7, "partial_answer": 8}
- evidence_insufficient: {"refused": 5}
- fact: {"partial_answer": 8, "answered": 7}
- risk_safety: {"partial_answer": 11, "answered": 4}

## Refusal Diagnostics

- designed_unanswerable_refused: 5 / 5
- verified_or_answerable_refused: 0 / 45
- citation_repair_count: 27
- refused_qids: STAI-P046, STAI-P047, STAI-P048, STAI-P049, STAI-P050

## Context / Latency

- avg_latency_sec: 14.225
- avg_evidence_contexts: 0.9
- avg_gold_contexts: 0.9
- avg_retrieved_contexts: 0
