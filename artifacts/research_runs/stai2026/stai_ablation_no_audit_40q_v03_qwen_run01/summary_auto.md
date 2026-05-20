# STAI Run Summary: stai_ablation_no_audit_40q_v03_qwen_run01

## Basic

- system: S3 / Full Workflow
- dataset: docs\paper_project\stai_benchmark_v0.3_100_question_draft.jsonl
- model: qwen2.5:latest
- evidence_mode: retrieval_plus_gold
- ablation_mode: no_audit
- pre_gate_mode: off
- rows / unique_qids: 40 / 40
- elapsed_sec: 394.989

## Status Counts

- answered: 26
- refused: 14

## Gate / Audit / Repair

- gate: {"answerable": 21, "partial": 5, "unanswerable": 14}
- audit: {"skipped": 26, "refuse_required": 14}
- repair: {"skipped_audit": 26, "refused_due_to_insufficient_evidence": 10, "refused_due_to_insufficient_evidence_with_safety_deescalation": 4}
- pre_gate: {"not_triggered": 40}

## Category x Status

- applied_reasoning: {"answered": 9, "refused": 1}
- evidence_insufficient: {"refused": 10}
- fact: {"answered": 10}
- risk_safety: {"answered": 7, "refused": 3}

## Refusal Diagnostics

- unanswerable_control_refused: 10 / 10
- designed_unanswerable_refused: 10 / 10
- verified_or_answerable_refused: 4 / 30
- citation_repair_count: 0
- refused_qids: STAI-P066, STAI-P036, STAI-P040, STAI-P081, STAI-P046, STAI-P047, STAI-P048, STAI-P049, STAI-P050, STAI-P096, STAI-P097, STAI-P098, STAI-P099, STAI-P100

## Context / Latency

- avg_latency_sec: 9.874
- avg_evidence_contexts: 5.75
- avg_gold_contexts: 0.75
- avg_retrieved_contexts: 5
