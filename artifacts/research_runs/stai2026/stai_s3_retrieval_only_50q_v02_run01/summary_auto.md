# STAI Run Summary: stai_s3_retrieval_only_50q_v02_run01

## Basic

- system: S3 / Full Workflow
- dataset: docs\paper_project\stai_benchmark_v0.2_50_question_draft.jsonl
- model: qwen2.5:latest
- evidence_mode: retrieval_only
- rows / unique_qids: 50 / 50
- elapsed_sec: 280.504

## Status Counts

- partial_answer: 15
- answered: 8
- refused: 27

## Gate / Audit / Repair

- gate: {"partial": 14, "answerable": 9, "unanswerable": 27}
- audit: {"repair_required": 41, "pass": 9}
- repair: {"repaired_invalid_or_missing_citations": 15, "none": 8, "refused_due_to_insufficient_evidence": 14, "refused_due_to_insufficient_evidence_with_safety_deescalation": 13}

## Category x Status

- applied_reasoning: {"partial_answer": 7, "refused": 5, "answered": 3}
- evidence_insufficient: {"refused": 5}
- fact: {"partial_answer": 7, "answered": 3, "refused": 5}
- risk_safety: {"refused": 12, "answered": 2, "partial_answer": 1}

## Refusal Diagnostics

- designed_unanswerable_refused: 5 / 5
- verified_or_answerable_refused: 22 / 45
- citation_repair_count: 15
- refused_qids: STAI-P008, STAI-P010, STAI-P011, STAI-P012, STAI-P013, STAI-P014, STAI-P017, STAI-P019, STAI-P021, STAI-P027, STAI-P028, STAI-P029, STAI-P033, STAI-P034, STAI-P036, STAI-P038, STAI-P039, STAI-P040, STAI-P041, STAI-P042, STAI-P043, STAI-P045, STAI-P046, STAI-P047, STAI-P048, STAI-P049, STAI-P050

## Context / Latency

- avg_latency_sec: 30.321
- avg_evidence_contexts: 5
- avg_gold_contexts: 0
- avg_retrieved_contexts: 5
