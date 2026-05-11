# STAI Abstract and Introduction Revision v0.1

## 1. Purpose

This document records the C-stage revision of the paper draft's Abstract and Introduction. The goal was to make the paper easier for a STAI workshop reviewer to understand quickly while preserving the claim boundaries established in the claim-evidence audit.

Updated draft:

- `docs/paper_project/51_STAI_paper_draft_v0.1.md`

Input documents:

- `docs/paper_project/38_STAI_paper_positioning_v0.1.md`
- `docs/paper_project/55_STAI_claim_evidence_audit_v0.1.md`
- `docs/paper_project/56_STAI_tables_and_figures_v0.1.md`

## 2. Selected Writing Strategy

Chosen strategy:

> Contribution-first framing.

Rejected alternatives:

- Purely cautious framing: safer, but less memorable for reviewers.
- Result-first framing: punchier, but risks making the paper look like a small experiment report rather than a workflow paper.

## 3. Abstract Structure

The revised abstract follows this sequence:

1. Problem: safety-sensitive advisory RAG needs more than fluent generation.
2. Method: evidence-gated audit-and-repair workflow with explicit traceable stages.
3. Evaluation: 100-question pilot benchmark plus 30-prompt safety-stress suite.
4. Results: main qwen result, stress result, and llama3 subset result.
5. Boundary: workflow-level diagnostic evaluation, not deployment-ready coaching or clinical safety.

Key boundary language added:

- "constructed stress prompts"
- "workflow-level diagnostic evaluation"
- "rather than a deployment-ready coaching or clinical safety system"

## 4. Introduction Structure

The revised introduction now has five paragraphs:

1. Domain motivation: endurance-training advice combines factual, applied, and safety-sensitive requests.
2. RAG gap: ordinary RAG can hide citation, evidence, overclaim, and unsafe-continuation failures.
3. Workflow question and method: explicit gates, audit, repair, and refusal.
4. Contribution identity: output states and workflow traceability are the core contribution.
5. Contribution list plus scope boundary: pilot-scale, author-authored, local-model, targeted hardening.

## 5. Claim Boundaries Preserved

The revision avoids these unsupported claims:

- broad prompt-injection robustness;
- clinical safety validation;
- coaching efficacy;
- real-world deployment readiness;
- large-scale benchmark coverage;
- expert-validated labels;
- general superiority over all RAG baselines;
- novelty from "multi-agent" or "RAG" alone.

## 6. Reviewer-Facing Improvement

Expected improvement:

- Reviewers should identify the paper as a workflow-level diagnostic paper within the first two paragraphs.
- The contribution is no longer buried behind general RAG motivation.
- Limitations are introduced early enough to reduce overclaim risk.
- The abstract now separates main benchmark results from constructed safety-stress behavior.

## 7. Remaining Work

Next recommended paper-hardening step:

- Run a short abstract/introduction peer-review pass after the full paper is converted to LaTeX, because page limits may force compression.

Possible later refinements:

- Compress the abstract if the target template has a strict word limit.
- Add a final sentence in the introduction that names STAI-style trustworthiness explicitly if the venue instructions favor thematic alignment.
