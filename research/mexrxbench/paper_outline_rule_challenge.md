# Paper Outline: Rule Challenge Version

Working title:

> Rule-Governed Multi-Agent RAG for Evidence-Bounded Exercise Prescription: A Half-Marathon Training Challenge with Risk Gates, Prescription Contracts, and Auditable Repair

## Abstract

- Problem: LLM exercise prescription can produce unsafe, unsupported, or overconfident plans.
- Challenge: convert individualized exercise planning into a rule-governed, evidence-bounded decision support task.
- Method: RiskGate, EvidenceGate, PrescriptionContract, dynamic experts, Rule Auditor, bounded repair.
- Artifact: `M-EXRxBench`, seed cases, trace schema, prototype.
- Result claim: reduced unsafe advice and unsupported prescriptions while preserving useful plan generation.

## 1. Introduction

- Exercise prescription is safety-sensitive.
- Generic RAG and multi-agent debate do not guarantee prescription legality.
- RuleML angle: rule-based agents, conflict priority, repair, traceability.
- Contributions.

## 2. Challenge Definition

- Input: query, user profile, goal, constraints, risk signals, evidence/action library.
- Output: answered / partial_answer / ask_clarification / refused, plus trace.
- Task boundaries: training support, not diagnosis or medical care.

## 3. Rule-Governed M-EXRx Agent

- Three permanent agents.
- Conditional experts.
- RiskGate.
- EvidenceGate.
- PrescriptionContract.
- Rule Auditor and bounded repair.

## 4. M-EXRxBench

- Case categories.
- Schema.
- Gold behavior.
- Evidence/action linkage.
- Safety and injection cases.

## 5. Prototype And Evaluation

- Baselines.
- Metrics.
- Trace completeness.
- Case studies.
- Repair examples.

## 6. Discussion

- Why not free-form multi-agent planning.
- How rules improve safety and auditability.
- Generalization beyond half-marathon.
- Limits: clinical validation, population diversity, wearable uncertainty.

## 7. Open Artifacts

- Repository structure.
- Demo instructions.
- Rule files.
- Benchmark files.
- Example traces.
