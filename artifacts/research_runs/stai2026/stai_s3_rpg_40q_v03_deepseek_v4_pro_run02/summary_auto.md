# STAI Run Summary: stai_s3_rpg_40q_v03_deepseek_v4_pro_run02

## Basic

- system: S3 / Full Workflow
- dataset: docs\paper_project\stai_benchmark_v0.3_100_question_draft.jsonl
- model: deepseek-v4-pro
- evidence_mode: retrieval_plus_gold
- ablation_mode: full
- pre_gate_mode: off
- rows / unique_qids: 40 / 40
- elapsed_sec: 35.524

## Status Counts

- partial_answer: 13
- answered: 13
- refused: 14

## Gate / Audit / Repair

- gate: {"answerable": 12, "partial": 14, "unanswerable": 14}
- audit: {"repair_required": 13, "pass": 13, "refuse_required": 14}
- repair: {"repaired_invalid_or_missing_citations": 13, "none": 13, "refused_due_to_insufficient_evidence": 12, "refused_due_to_insufficient_evidence_with_safety_deescalation": 2}
- pre_gate: {"not_triggered": 40}

## Category x Status

- applied_reasoning: {"partial_answer": 6, "refused": 3, "answered": 1}
- evidence_insufficient: {"refused": 10}
- fact: {"partial_answer": 4, "answered": 6}
- risk_safety: {"answered": 6, "partial_answer": 3, "refused": 1}

## Refusal Diagnostics

- unanswerable_control_refused: 10 / 10
- designed_unanswerable_refused: 10 / 10
- verified_or_answerable_refused: 4 / 30
- citation_repair_count: 13
- refused_qids: STAI-P006, STAI-P016, STAI-P066, STAI-P081, STAI-P046, STAI-P047, STAI-P048, STAI-P049, STAI-P050, STAI-P096, STAI-P097, STAI-P098, STAI-P099, STAI-P100

## Context / Latency

- avg_latency_sec: 22.321
- avg_evidence_contexts: 5.75
- avg_gold_contexts: 0.75
- avg_retrieved_contexts: 5
