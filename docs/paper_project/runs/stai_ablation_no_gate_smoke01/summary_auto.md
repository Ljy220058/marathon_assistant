# STAI Run Summary: stai_ablation_no_gate_smoke01

## Basic

- system: S3 / Full Workflow
- dataset: docs\paper_project\stai_benchmark_v0.2_50_question_draft.jsonl
- model: qwen2.5:latest
- evidence_mode: retrieval_plus_gold
- ablation_mode: no_gate
- rows / unique_qids: 2 / 2
- elapsed_sec: 59.305

## Status Counts

- partial_answer: 2

## Gate / Audit / Repair

- gate: {"answerable": 2}
- audit: {"repair_required": 2}
- repair: {"repaired_invalid_or_missing_citations": 2}

## Category x Status

- evidence_insufficient: {"partial_answer": 1}
- fact: {"partial_answer": 1}

## Refusal Diagnostics

- designed_unanswerable_refused: 0 / 1
- verified_or_answerable_refused: 0 / 1
- citation_repair_count: 2
- refused_qids: none

## Context / Latency

- avg_latency_sec: 29.652
- avg_evidence_contexts: 5.5
- avg_gold_contexts: 0.5
- avg_retrieved_contexts: 5
