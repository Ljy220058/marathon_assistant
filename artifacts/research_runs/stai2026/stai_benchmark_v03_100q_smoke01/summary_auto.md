# STAI Run Summary: stai_benchmark_v03_100q_smoke01

## Basic

- system: S3 / Full Workflow
- dataset: docs\paper_project\stai_benchmark_v0.3_100_question_draft.jsonl
- model: qwen2.5:latest
- evidence_mode: retrieval_plus_gold
- ablation_mode: full
- pre_gate_mode: off
- rows / unique_qids: 3 / 3
- elapsed_sec: 43.644

## Status Counts

- partial_answer: 1
- refused: 2

## Gate / Audit / Repair

- gate: {"answerable": 1, "unanswerable": 2}
- audit: {"repair_required": 1, "refuse_required": 2}
- repair: {"repaired_invalid_or_missing_citations": 1, "refused_due_to_insufficient_evidence_with_safety_deescalation": 1, "refused_due_to_insufficient_evidence": 1}
- pre_gate: {"not_triggered": 3}

## Category x Status

- evidence_insufficient: {"refused": 1}
- fact: {"partial_answer": 1}
- risk_safety: {"refused": 1}

## Refusal Diagnostics

- unanswerable_control_refused: 1 / 1
- designed_unanswerable_refused: 1 / 1
- verified_or_answerable_refused: 1 / 2
- citation_repair_count: 1
- refused_qids: STAI-P081, STAI-P096

## Context / Latency

- avg_latency_sec: 14.547
- avg_evidence_contexts: 5.667
- avg_gold_contexts: 0.667
- avg_retrieved_contexts: 5
