# STAI Reviewer Attack and Risk Plan v0.1

Date: 2026-05-11

## Purpose

This note records the most likely reviewer attacks and the corresponding in-paper defenses. It is not a rebuttal draft; it is a pre-submission risk checklist for keeping the manuscript honest and harder to dismiss.

## Reviewer-Side Risk Matrix

| Reviewer lens | Likely attack | Severity | Current defense | Added or recommended defense |
| --- | --- | --- | --- | --- |
| EIC / workshop fit | The paper may be too application-specific for STAI or too small for a systems paper. | Major | The title, abstract, introduction, and limitations frame the work as a workflow-level diagnostic study for trustworthy advisory RAG. | Keep emphasizing secure/trustworthy relevance through refusal, grounding, audit, repair, and safety-boundary behavior rather than endurance training as the only contribution. |
| Methodology reviewer | The benchmark is only 100 main questions plus 30 stress prompts. | Major | Benchmark and limitations already call it pilot-scale and focused. | The limitations now state that proportions are internal diagnostics, not statistically powered population estimates. |
| Methodology reviewer | Labels and spot-checks are author-authored. | Major | Limitations acknowledge lack of external expert validation. | Future work should include external annotation or blind review; avoid claiming benchmark objectivity beyond its documented rubrics. |
| Methodology reviewer | Ablation is only a 40-question subset. | Major | Results call it a diagnostic subset. | Limitations now explicitly state that the ablation is not a comprehensive component study. |
| Domain reviewer | The paper may overstep into coaching efficacy or medical advice. | Critical | Introduction, ethics statement, and limitations reject clinical safety, diagnosis, and deployment readiness. | Keep examples phrased as boundary behavior, not as evidence that the system gives good real-world training advice. |
| Domain reviewer | Endurance-training evidence may be too narrow or not externally reviewed. | Major | Benchmark section says evidence map has verified items and no fabricated citations/results. | The limitations now call for externally reviewed domain evidence. The supplementary benchmark should not be reported as evidence-backed until evidence mapping is complete. |
| Security reviewer | Deterministic hardening could be oversold as a safety or prompt-injection defense. | Critical | Results and limitations say it is targeted request-level hardening, not general adversarial security. | Continue using "targeted constructed safety-stress suite" and never "robust defense" or "secure against prompt injection." |
| Security reviewer | Stress prompts are constructed and may not reflect adaptive attacks. | Major | Safety stress suite is described as targeted, not complete adversarial benchmark. | Future work should include multi-turn and adaptive stress tests. |
| Devil's Advocate | The strongest rejection reason is that the work recombines known RAG, verifier, and agent ideas with a small author-authored benchmark. | Critical | Related Work now cites RAG diagnostics, refusal/over-refusal, and RAG safety work; contribution is narrowed to measurable advisory workflow states. | The paper must keep saying "diagnostic decomposition" rather than "new agent framework." |
| Devil's Advocate | Results may look like rule engineering rather than research. | Major | Method defines reproducible control points and ablations. | The key research value should be framed as making failures observable and measurable, not as claiming a smarter generator. |

## Strongest Possible Rejection Argument

The strongest rejection argument is:

> The paper combines existing RAG, gating, verification, and refusal ideas in a small author-authored endurance-training benchmark. The hardening is deterministic, the ablation is small, and the primary experiment uses one model. Therefore, the paper is incremental and under-validated.

This argument is not fully avoidable. The best defense is not to inflate claims, but to make the paper clearly valuable as a workshop diagnostic study:

- narrow the claim to workflow-level observability and controllability;
- show refusal, partial answer, citation repair, and false refusal as explicit measured states;
- keep the benchmark pilot-scale but reproducible and traceable;
- use limitations proactively instead of hiding weaknesses;
- position supplementary benchmark expansion as future/auxiliary evidence until evidence mapping and runs are complete.

## Textual Claim Guardrails

Safe wording:

- "workflow-level diagnostic study"
- "focused pilot benchmark"
- "targeted constructed safety-stress suite"
- "explicit traceable control points"
- "observable refusal, repair, and safety-boundary states"

Unsafe wording:

- "general multi-agent framework"
- "clinical safety system"
- "deployment-ready coaching"
- "robust prompt-injection defense"
- "large-scale benchmark"
- "proves safety"
- "state-of-the-art performance"

## Current Status

The main manuscript now contains direct defenses for the most important reviewer attacks:

- pilot-scale benchmark scope;
- author-authored labels;
- one-primary-model limitation;
- diagnostic subset ablation boundary;
- deterministic hardening boundary;
- no clinical, coaching-efficacy, or deployment-readiness claim.
