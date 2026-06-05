# STAI Run Summary: stai_ablation_no_repair_smoke01

## Basic

- system: S3 / Full Workflow
- dataset: docs\paper_project\stai_benchmark_v0.2_50_question_draft.jsonl
- model: qwen2.5:latest
- evidence_mode: retrieval_plus_gold
- ablation_mode: no_repair
- rows / unique_qids: 2 / 2
- elapsed_sec: 28.761

## Status Counts

- answered: 1
- refused: 1

## Gate / Audit / Repair

- gate: {"answerable": 1, "unanswerable": 1}
- audit: {"pass": 1, "refuse_required": 1}
- repair: {"none": 1, "refused_due_to_insufficient_evidence": 1}

## Category x Status

- evidence_insufficient: {"refused": 1}
- fact: {"answered": 1}

## Refusal Diagnostics

- designed_unanswerable_refused: 1 / 1
- verified_or_answerable_refused: 0 / 1
- citation_repair_count: 0
- refused_qids: STAI-P046

## Context / Latency

- avg_latency_sec: 14.38
- avg_evidence_contexts: 5.5
- avg_gold_contexts: 0.5
- avg_retrieved_contexts: 5
