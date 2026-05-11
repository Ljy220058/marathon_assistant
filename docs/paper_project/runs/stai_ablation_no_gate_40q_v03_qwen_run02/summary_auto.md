# STAI Run Summary: stai_ablation_no_gate_40q_v03_qwen_run02

## Basic

- system: S3 / Full Workflow
- dataset: docs\paper_project\stai_benchmark_v0.3_100_question_draft.jsonl
- model: qwen2.5:latest
- evidence_mode: retrieval_plus_gold
- ablation_mode: no_gate
- pre_gate_mode: off
- rows / unique_qids: 40 / 40
- elapsed_sec: 1159.122

## Status Counts

- partial_answer: 40

## Gate / Audit / Repair

- gate: {"answerable": 40}
- audit: {"repair_required": 40}
- repair: {"repaired_invalid_or_missing_citations": 40}
- pre_gate: {"not_triggered": 40}

## Category x Status

- applied_reasoning: {"partial_answer": 10}
- evidence_insufficient: {"partial_answer": 10}
- fact: {"partial_answer": 10}
- risk_safety: {"partial_answer": 10}

## Refusal Diagnostics

- unanswerable_control_refused: 0 / 10
- designed_unanswerable_refused: 0 / 10
- verified_or_answerable_refused: 0 / 30
- citation_repair_count: 40
- refused_qids: none

## Context / Latency

- avg_latency_sec: 28.978
- avg_evidence_contexts: 5.75
- avg_gold_contexts: 0.75
- avg_retrieved_contexts: 5
