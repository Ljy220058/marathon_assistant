# STAI Paper Positioning v0.1

## 1. Working Title

Primary candidate:

**Evidence-Gated Audit-and-Repair Agentic RAG for Safety-Sensitive Endurance Training Advice**

Alternative titles:

1. **A Request-Gated Agentic RAG Workflow for Trustworthy Endurance Training Advice**
2. **Auditable Evidence Gating and Repair for Safety-Sensitive Training Recommendation RAG**
3. **From Retrieval to Refusal: A Pilot Benchmark for Trustworthy Endurance Training Advice**

Recommended title for STAI:

**Evidence-Gated Audit-and-Repair Agentic RAG for Safety-Sensitive Endurance Training Advice**

Reason: it foregrounds the method, the safety-sensitive setting, and the workflow-level contribution without overclaiming general robustness.

## 2. One-Sentence Paper Identity

This paper studies a request-level, evidence-gated audit-and-repair workflow for safety-sensitive advisory RAG, evaluated on a focused endurance-training pilot benchmark and targeted safety-stress suite.

## 3. Target Venue and Paper Type

Target:

- STAI 2026 Workshop @ ECML PKDD

Preferred submission type:

- Regular workshop paper if the final manuscript can fit the full method, benchmark, experiments, and limitations clearly.
- Short research statement only if time becomes too tight or if the paper needs to be framed as early-stage exploratory work.

Positioning:

- system/workflow paper;
- pilot benchmark paper;
- safety-stress diagnostic paper.

Not positioning:

- not a large-scale benchmark paper;
- not a clinical validation paper;
- not a general prompt-injection defense paper;
- not a sports-science efficacy trial.

## 4. Core Problem

LLM/RAG systems used for endurance-training advice face several linked trustworthiness risks:

- retrieved evidence may be missing, noisy, or insufficient;
- generated answers may attach citations to weakly supported claims;
- users may request unsupported guarantees, fabricated evidence, or unsafe continuation of training;
- ordinary answer-rate metrics hide important distinctions between correct refusal, false refusal, partial answer, and repaired citation behavior.

The paper asks whether an agentic workflow with request filtering, evidence gating, risk gating, generation, independent audit, and repair/refusal can make these failure modes more observable and controllable.

## 5. Main Research Claim

Safe claim:

> In safety-sensitive advisory RAG, an evidence-gated audit-and-repair workflow can expose and reduce grounding, refusal, and safety-boundary failures on a focused endurance-training benchmark, while preserving traceable refusal behavior for insufficient-evidence and safety-stress requests.

More specific evidence-supported claims:

- On the 100-question pilot benchmark, the S3 workflow refused all 10 designed-unanswerable controls.
- On the same run, 4 / 90 verified-answerable questions were falsely refused, showing a conservative residual failure mode.
- On the 30-question safety-stress suite, hardening v0.4 refused all 30 stress prompts for both `qwen2.5:latest` and `llama3:latest`.
- The llama3 40-question main benchmark subset refused all 10 designed-unanswerable controls and had 0 / 30 false refusals on verified-answerable questions.
- The workflow frequently used citation repair, so `partial_answer` should be treated as a diagnostic category rather than collapsed into simple success/failure.

## 6. Contribution Claims

Contribution 1: Agentic RAG workflow

- A modular workflow combining pre-gate request filtering, evidence retrieval/gold evidence modes, evidence gate, risk gate, evidence-constrained generation, independent audit, and repair/refusal.
- The contribution is the workflow and diagnostic control structure, not a new foundation model.

Contribution 2: Focused pilot benchmark

- A 100-question endurance-training advisory benchmark with 90 evidence-backed questions and 10 designed-unanswerable controls.
- Categories: fact, applied reasoning, risk safety, evidence insufficient.
- The benchmark is versioned and intentionally designed for expansion.

Contribution 3: Safety-stress suite

- A 30-question stress suite covering prompt injection, unsafe requests, citation hallucination pressure, overclaim requests, and evidence-conflict/cherry-picking attacks.
- The suite tests refusal and safety-boundary behavior rather than answer completeness.

Contribution 4: Diagnostic evaluation

- Evidence-mode comparison, ablation, full 100-question run, cross-model stress check, and second-model 40-question subset.
- Metrics include answered, partial_answer, refused, designed-unanswerable refusal, false refusal, citation repair, and pre-gate rule counts.

## 7. Current Experimental Evidence

Main 100-question run:

- run: `stai_s3_rpg_100q_v03_qwen_run01`
- model: `qwen2.5:latest`
- evidence mode: `retrieval_plus_gold`
- answered: 24
- partial_answer: 62
- refused: 14
- designed-unanswerable refused: 10 / 10
- verified-or-answerable false refusal: 4 / 90
- citation repair count: 62

Safety stress 30-question runs:

| model | refused | partial_answer | answered |
|---|---:|---:|---:|
| `qwen2.5:latest` | 30 | 0 | 0 |
| `llama3:latest` | 30 | 0 | 0 |

Second-model main subset:

- model: `llama3:latest`
- subset size: 40
- answered: 13
- partial_answer: 17
- refused: 10
- designed-unanswerable refused: 10 / 10
- verified-or-answerable false refusal: 0 / 30

## 8. Claim Boundaries

Do not claim:

- broad prompt-injection robustness;
- medical safety validation;
- coaching efficacy;
- real-world deployment readiness;
- large-scale benchmark coverage;
- expert-validated labels;
- superiority over all RAG baselines;
- that deterministic hardening covers all adversarial paraphrases.

Use these phrases instead:

- focused pilot benchmark;
- targeted safety-stress suite;
- request-level deterministic pre-gate;
- workflow-level diagnostic evaluation;
- author sanity check rather than expert validation;
- preliminary cross-model sanity check.

## 9. Expansion Slots

The paper should leave explicit space for later extensions:

1. More models
   - Extend from `qwen2.5` and `llama3` to additional open and API models.
   - Keep current results as primary local reproducible results.

2. Larger benchmark
   - Extend from 100 main questions to 150-200.
   - Extend safety stress from 30 to 50.
   - Preserve the current versioned benchmark design.

3. Expert review
   - Add coach, sports-science, or clinical safety review for a sample of outputs.
   - Use it as validation, not as a replacement for evidence traceability.

4. Stronger baselines
   - Add S0/S1 reruns on v0.3 if time allows.
   - Add pure LLM, vanilla RAG, and no-audit/no-repair comparisons.

5. Learned or hybrid safety filter
   - Current hardening is deterministic.
   - Future work can compare rule-based, LLM-as-judge, and hybrid request filters.

## 10. Recommended Abstract Shape

The abstract should have five moves:

1. Safety-sensitive RAG advice requires more than fluent generation.
2. Endurance-training advice has evidence, citation, overclaim, and safety-boundary risks.
3. We propose an evidence-gated audit-and-repair agentic workflow.
4. We evaluate it on a 100-question pilot benchmark and 30-question safety-stress suite.
5. Results show strong control refusal and stress refusal behavior, while error analysis identifies residual conservative false refusals and frequent citation repair.

## 11. Acceptance Strategy

Best framing for STAI:

- Emphasize trustworthiness diagnostics, not raw performance.
- Treat refusal as a first-class outcome.
- Make limitations visible and specific.
- Present the benchmark as expandable, versioned, and domain-focused.
- Make the method figure central.

Risk if written poorly:

- Reviewers may see the paper as a small handcrafted benchmark plus prompt rules.

How to avoid that:

- Center the agentic workflow and audit/repair/refusal control loop.
- Report ablations and stress failures before hardening.
- Keep every claim tied to run artifacts.
- Use limitations to show scientific restraint.
