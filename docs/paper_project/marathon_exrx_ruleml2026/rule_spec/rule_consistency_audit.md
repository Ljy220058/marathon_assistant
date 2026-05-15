# Rule Consistency Audit

> Artifact task: P2-T7. This audit checks consistency across RiskGate, EvidenceGate, PrescriptionContract, HMP mapping, Audit/Repair, formal semantics, promotion protocol, repair invariants, and hazard model.

## 1. Audit Scope

| Source | Role in audit |
|---|---|
| `risk_gate_rules.md` | Risk levels, R2/R3 behavior, refusal/downgrade rules. |
| `evidence_gate_rules.md` | Evidence layers and prescription eligibility. |
| `prescription_contract_schema.json` | Contract fields and repair scope. |
| `rule_priority_ladder.md` | Conflict priority. |
| `audit_and_repair_contract.md` | Audit layers and bounded repair. |
| `hmp_rule_action_mapping.md` | HMP protocol/action eligibility. |
| `formal_rule_model.md` | Semi-formal predicates and dominance relation. |
| `executable_rule_semantics.md` | Implementation pseudocode. |
| `evidence_promotion_protocol.md` | Evidence-to-rule governance. |
| `repair_invariants.md` | Repair invariants and re-audit. |
| `hazard_model.md` | Hazard families and fail-closed defaults. |

## 2. Consistency Checks

| Check ID | Question | Result | Notes |
|---|---|---|---|
| `consistency.risk.r3_refusal` | Does every R3 rule forbid training prescription? | pass | RiskGate, hazard model, formal refusal condition, and repair invariants agree. |
| `consistency.risk.r2_downgrade` | Does R2 activate downgrade/clarification rather than hard prescription? | pass | R2 is repairable only when downgraded and re-audited. |
| `consistency.evidence.layers` | Do all documents agree that only `protocol_rule`, `action_library`, and promoted `curated_guideline` can support prescription? | pass | Promotion protocol clarifies academic/general KB default to explanation-only. |
| `consistency.repair.no_invention` | Is repair forbidden from inventing evidence/actions? | pass | Present in audit contract, formal model, and repair invariants. |
| `consistency.repair.reaudit` | Is re-audit mandatory after repair? | pass | Added as blocking invariant and executable algorithm. |
| `consistency.hmp.elite_scaling` | Does HMP mapping prevent copying elite Sub-70 capacity? | pass | `hmp.safety.no_sub70_copy` and capacity scaling rules included. |
| `consistency.profile.missing` | Do missing critical fields fail closed? | pass | Hazard model and executable semantics use ask-clarification/no prescription. |
| `consistency.trace.soundness` | Is trace required for answered outputs? | pass | Formal trace soundness and executable output envelope align. |

## 3. Known Gaps For Other Workers

These are outside this worker's allowed edit scope but should be handled by benchmark/demo workers:

| Gap | Required downstream artifact |
|---|---|
| Trace schema should encode repair log fields from `repair_invariants.md`. | `rule_spec/trace_schema.json` |
| Result schema should distinguish `baselines` from `ours/full_rule_governed`. | `benchmark/result_schema.json` |
| Gold split must keep `gold_risk_level`, `expected_behavior`, and `required_rules` evaluator-only. | `benchmark/system_visible_cases.jsonl`, `benchmark/gold_labels.jsonl` |
| Fail-closed regression must include cases from `repair_invariants.md` and `hazard_model.md`. | demo/evaluator test artifacts |

## 4. No-Conflict Assertions

```text
R3 refusal cannot be repaired into a plan.
R2 hard-session conflict can be repaired only by downgrade, clarification, partial answer, or refusal.
Academic literature cannot directly authorize prescription.
HMP action mapping cannot override RiskGate or EvidenceGate.
Repair cannot introduce new evidence or action IDs.
Answered outputs require contract satisfaction and trace soundness.
```

## 5. Audit Decision

Current rule set is internally consistent at the specification level for P2-T6 through P2-T11.

Status:

```text
rule_consistency_status = spec_pass
implementation_status = pending demo/evaluator enforcement
blocking_notes = downstream schemas and tests must implement these constraints before safety claims are made
```

