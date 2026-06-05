# STAI Run Summary: stai_s3_gold_only_gate_norm_smoke01

## Basic

- system: S3 / Full Workflow
- dataset: docs\paper_project\stai_benchmark_v0.2_50_question_draft.jsonl
- model: qwen2.5:latest
- evidence_mode: gold_only
- rows / unique_qids: 3 / 3
- elapsed_sec: 37.286

## Status Counts

- partial_answer: 2
- answered: 1

## Gate / Audit / Repair

- gate: {"partial": 3}
- audit: {"repair_required": 2, "pass": 1}
- repair: {"repaired_invalid_or_missing_citations": 2, "none": 1}

## Category x Status

- risk_safety: {"partial_answer": 2, "answered": 1}

## Refusal Diagnostics

- designed_unanswerable_refused: 0 / 0
- verified_or_answerable_refused: 0 / 3
- citation_repair_count: 2
- refused_qids: none

## Context / Latency

- avg_latency_sec: 12.429
- avg_evidence_contexts: 1
- avg_gold_contexts: 1
- avg_retrieved_contexts: 0
