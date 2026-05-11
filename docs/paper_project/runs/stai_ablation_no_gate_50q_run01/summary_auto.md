# STAI Run Summary: stai_ablation_no_gate_50q_run01

## Basic

- system: S3 / Full Workflow
- dataset: docs\paper_project\stai_benchmark_v0.2_50_question_draft.jsonl
- model: qwen2.5:latest
- evidence_mode: retrieval_plus_gold
- ablation_mode: no_gate
- rows / unique_qids: 50 / 50
- elapsed_sec: 1544.409

## Status Counts

- partial_answer: 47
- answered: 3

## Gate / Audit / Repair

- gate: {"answerable": 50}
- audit: {"repair_required": 47, "pass": 3}
- repair: {"repaired_invalid_or_missing_citations": 47, "none": 3}

## Category x Status

- applied_reasoning: {"partial_answer": 14, "answered": 1}
- evidence_insufficient: {"partial_answer": 5}
- fact: {"partial_answer": 14, "answered": 1}
- risk_safety: {"partial_answer": 14, "answered": 1}

## Refusal Diagnostics

- designed_unanswerable_refused: 0 / 5
- verified_or_answerable_refused: 0 / 45
- citation_repair_count: 47
- refused_qids: none

## Context / Latency

- avg_latency_sec: 30.888
- avg_evidence_contexts: 5.9
- avg_gold_contexts: 0.9
- avg_retrieved_contexts: 5
