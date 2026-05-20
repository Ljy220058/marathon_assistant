# Rule Contract Coverage Check

Owner section: Agent 1, Challenge/Formalism Lead.

Date: 2026-05-16.

## Formal Contract Surface

The rule contract is already represented across:

- `rule_spec/formal_rule_model.md`
- `rule_spec/executable_rule_semantics.md`
- `rule_spec/risk_gate_rules.md`
- `rule_spec/evidence_gate_rules.md`
- `rule_spec/prescription_contract_schema.json`
- `rule_spec/audit_and_repair_contract.md`
- `rule_spec/repair_invariants.md`
- `rule_spec/trace_schema.json`
- `paper/main.tex`
- `submission_package/paper/main.tex`

## Contract Element Coverage

| Element | Formalism source | Paper source | Coverage status |
|---|---|---|---|
| RiskGate | `risk_gate_rules.md`; `formal_rule_model.md`; `executable_rule_semantics.md` | `Risk and Evidence Gates`; architecture caption | Covered. R0/R1/R2/R3 meanings are explicit. |
| EvidenceGate | `evidence_gate_rules.md`; `formal_rule_model.md`; `executable_rule_semantics.md` | `Risk and Evidence Gates` | Covered. Evidence eligibility is separated from explanation-only material. |
| PrescriptionContract | `prescription_contract_schema.json`; `formal_rule_model.md` | `Prescription Contract` | Covered. Allowed/forbidden actions, risk, evidence, audit, and repair scope appear. |
| Rule Auditor | `audit_and_repair_contract.md`; `executable_rule_semantics.md` | `Rule Auditor and Bounded Repair` | Covered. Safety, evidence, protocol, and trace audits are named. |
| Bounded Repair | `audit_and_repair_contract.md`; `formal_rule_model.md`; `executable_rule_semantics.md` | `Rule Auditor and Bounded Repair`; example flow table | Covered. Repairs are constrained and fail closed when unrepairable. |
| Trace contract | `trace_schema.json`; `formal_rule_model.md` | `Trace Requirements`; metrics paragraph | Covered. Required trace fields are explicit. |

## RiskGate Checklist

| Requirement | Coverage |
|---|---|
| R0 means explain-only. | `risk_gate_rules.md` and annotation protocol define R0 as general education/non-prescriptive. |
| R1 allows contract-bound prescription. | `risk_gate_rules.md` and paper state R1 permits contract-bounded prescription. |
| R2 means downgrade, clarify, or expert-boundary behavior. | `risk_gate_rules.md`, `executable_rule_semantics.md`, and paper describe downgrade/clarification/expert activation. |
| R3 means refusal or professional-evaluation boundary. | `risk_gate_rules.md` and paper define R3 as refusal/professional boundary. |

## EvidenceGate Checklist

| Requirement | Coverage |
|---|---|
| Evidence can explain. | `evidence_gate_rules.md` allows academic/general sources for explanation-only use. |
| Evidence can authorize prescription only when eligible. | `evidence_gate_rules.md` defines eligible layers and ID/population/review requirements. |
| Evidence insufficiency triggers clarification/refusal or partial answer. | `evidence_gate_rules.md` and `executable_rule_semantics.md` define `needs_evidence`, partial answer, and clarification behavior. |
| General knowledge cannot invent prescription actions. | `evidence_gate_rules.md` and `formal_rule_model.md` prohibit unsupported prescription authorization. |

## PrescriptionContract Checklist

| Requirement | Coverage |
|---|---|
| Allowed actions | `prescription_contract_schema.json` requires `allowed_actions`. |
| Prohibited actions | `prescription_contract_schema.json` requires `forbidden_actions`. |
| Risk level | `prescription_contract_schema.json` requires `risk_level`. |
| Evidence IDs / requirements | Contract schema requires `evidence_requirements`; trace schema requires `evidence_ids`. |
| Action IDs | Contract schema requires allowed/forbidden actions; trace schema requires `action_ids`. |
| Final status | Result schema requires `status`; trace schema requires `final_status`. |
| Trace requirements | `trace_schema.json` requires the auditable trace surface. |

## Rule Auditor Checklist

| Auditor check | Coverage |
|---|---|
| Unsupported prescription | `demo/evaluate_results.py` and `evidence_gate_rules.md` define unsupported-prescription checks. |
| Forbidden outputs | `demo/evaluate_results.py` compares against evaluator-only `forbidden_outputs`. |
| Risk/status conflict | `demo/evaluate_results.py` checks status and trace risk against gold labels; `risk_gate_rules.md` defines status boundaries. |
| Missing trace fields | `trace_schema.json` and `demo/validate_artifacts.py` require trace keys and final-status consistency. |

## Bounded Repair Checklist

| Repair rule | Coverage |
|---|---|
| R2 can be repaired by downgrade/restrict wording. | `audit_and_repair_contract.md` allows lower intensity, reduce volume, add recovery, convert to partial answer. |
| R3 cannot be repaired into a training plan. | `risk_gate_rules.md`, `formal_rule_model.md`, and `executable_rule_semantics.md` require refusal for R3/red-flag boundaries. |
| Failed repair becomes refusal or clarification/partial answer. | `executable_rule_semantics.md` returns fail-closed results when repair cannot satisfy the contract. |

## Formalism Conclusion

The paper makes clear that the LLM/reference generator drafts within a pre-generation and post-generation rule contract. The permission boundary is assigned to RiskGate, EvidenceGate, PrescriptionContract, Rule Auditor, and bounded repair; it is not set by free-form generation.

## Integration Note

Agent 2 should attach exact executable coverage evidence from validators and runner checks. This file currently records formal/semi-formal coverage and code-path evidence visible from static inspection.

