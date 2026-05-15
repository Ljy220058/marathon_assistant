# RuleML+RR 2026 Acceptance Criteria

## Track Decision

Primary target: Rule Challenge.

The submission is positioned as a hybrid Challenge Proposal and Challenge Solution. The contribution is not a new general-purpose coaching chatbot; it is a reproducible rule-governed challenge package for evidence-bounded exercise prescription.

| Track | Fit | Main Requirement | Risk |
|---|---|---|---|
| Main Track | Medium | formal rule reasoning contribution | May read as an application paper if theory depth is insufficient |
| Rule Challenge | High | challenge definition, benchmark, metrics, demo, open artifacts | Best fit for M-EXRxBench plus executable evaluator |
| Industry Track | Medium | deployment evidence and operational lessons | We do not claim real-world deployment |

## Rule Challenge Must-Haves

1. Clear challenge definition: evidence-bounded exercise prescription.
2. Benchmark: `M-EXRxBench v0.4` with 500 synthetic cases.
3. Evaluation metrics: safety, evidence, rule compliance, trace, and repair.
4. Concrete use cases: normal planning, R2 downgrade/clarification, R3 refusal, evidence gaps, prompt injection.
5. Tool or interface: deterministic runner, batch runner, evaluator, and static trace viewer.
6. Open artifacts: schemas, cases, rules, trace examples, release manifest.
7. Novelty: rule-governed multi-agent RAG, not a generic plan generator.
8. Failure analysis: unsafe generation, evidence gaps, repair/refusal, gold leakage.
9. Reproducibility: one-command local script and saved outputs.
10. Clear relation to rule-based agents and explainable decision support.

## Acceptance Bar For This Paper

Pre-upload package gate:

- The default submitted artifact is `M-EXRxBench v0.4` with 500 synthetic cases across 10 categories.
- Historical v0.3/v0.2 files are archive snapshots only, not default runner inputs.
- Every case has expected behavior: `answered`, `partial_answer`, `ask_clarification`, or `refused`.
- Every generated output has a trace: `profile_version`, `risk_level`, `evidence_ids`, `action_ids`, `rules_fired`, `audit_result`, `repair_log`, and `final_status`.
- Four compared systems are reported: `naked_llm`, `vanilla_rag`, `multi_agent_no_rule_gate`, and `full_rule_governed`.
- Metrics include unsafe advice rate, unsupported prescription rate, rule violation rate, trace completeness, status accuracy, risk accuracy, and repair success rate.
- The CEURART manuscript stays within 8-15 pages.
- Claims remain limited to synthetic benchmark rule compliance, not clinical validation.

## Writing Position

Do not frame the paper as:

> An AI marathon coach that generates personalized plans.

Frame it as:

> A rule-governed benchmark and prototype for evidence-bounded exercise prescription, where LLM outputs are constrained by risk gates, evidence eligibility, prescription contracts, and auditable repair rules.
