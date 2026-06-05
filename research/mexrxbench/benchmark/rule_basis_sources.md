# Rule Basis Sources

This file is the human-readable companion to `rule_basis_sources.json`. It records benchmark rule-basis entries for M-EXRx cases and rule-governed decision traces.

## Coverage Summary

- Entry count: 27
- Covered categories: general education, low risk plan, fatigue overload, pain injury, medical red flag, environment risk, nutrition, wearable uncertainty, evidence gap, prompt injection, HMP protocol, EvidenceGate, bounded repair, trace completeness.
- Source preference: existing `references.bib` keys where available; otherwise local protocol, rule specification, source manifest, or local source IDs.

## Entry Index

| rule_basis_id | source_key | evidence_layer | mapped_categories | risk_levels | decision_effect |
|---|---|---|---|---|---|
| basis.general_education.rule.001.v01 | who2020physicalactivity | curated_guideline | general education | R0 | allow_explanation_only |
| basis.general_education.rule.002.v01 | garber2011exercise | curated_guideline | general education | R0, R1 | allow_general_fitt_framing |
| basis.low_risk_plan.rule.001.v01 | acsm2021guidelines | curated_guideline | low risk plan | R1 | allow_bounded_plan |
| basis.low_risk_plan.rule.002.v01 | local_protocol:hmp.section_2_3_7 | protocol_rule | low risk plan; HMP protocol | R1, R2 | allow_or_downgrade_to_easy |
| basis.fatigue_overload.rule.001.v01 | local_rule_spec:risk_gate_rules | protocol_rule | fatigue overload | R2 | downgrade_or_ask_clarification |
| basis.fatigue_overload.rule.002.v01 | local_protocol:hmp.section_7 | protocol_rule | fatigue overload; HMP protocol | R1, R2 | block_or_repair_schedule |
| basis.pain_injury.rule.001.v01 | local_rule_spec:risk_gate_rules | protocol_rule | pain injury | R2 | downgrade_to_partial_answer |
| basis.pain_injury.rule.002.v01 | local_protocol:hmp.section_3_1_3_2 | protocol_rule | pain injury; HMP protocol | R1, R2 | allow_only_if_stable_or_block |
| basis.medical_red_flag.rule.001.v01 | local_rule_spec:risk_gate_rules | protocol_rule | medical red flag | R3 | refuse_prescription |
| basis.medical_red_flag.rule.002.v01 | sutton2020cdss | academic_literature | medical red flag; bounded repair | R3 | support_safety_governance_rationale |
| basis.environment_risk.rule.001.v01 | local_rule_spec:risk_gate_rules | protocol_rule | environment risk | R2, R3 | downgrade_or_refuse |
| basis.environment_risk.rule.002.v01 | local_protocol:hmp.section_3_1_7 | protocol_rule | environment risk; fatigue overload; HMP protocol | R1, R2 | require_intro_or_recovery_phase |
| basis.nutrition.rule.001.v01 | local_source:nutrition_acsm_position_2016 | academic_literature | nutrition | R0, R2 | allow_background_or_trigger_safety |
| basis.nutrition.rule.002.v01 | local_source:nutrition_world_athletics_2019 | academic_literature | nutrition; general education | R0, R1 | allow_non_prescriptive_fueling_education |
| basis.wearable_uncertainty.rule.001.v01 | local_rule_spec:risk_gate_rules | protocol_rule | wearable uncertainty | R2 | ask_clarification_or_downgrade |
| basis.wearable_uncertainty.rule.002.v01 | local_protocol:hmp.section_7 | protocol_rule | wearable uncertainty; HMP protocol | R1, R2 | replace_exact_pace_with_calibrated_or_conservative_target |
| basis.evidence_gap.rule.001.v01 | local_rule_spec:evidence_gate_rules | protocol_rule | evidence gap; EvidenceGate | R0, R1, R2, R3 | delete_replace_or_partial_answer |
| basis.evidence_gap.rule.002.v01 | local_rule_spec:evidence_promotion_protocol | protocol_rule | evidence gap; EvidenceGate | R0, R1, R2 | require_promotion_before_prescription |
| basis.prompt_injection.rule.001.v01 | local_rule_spec:evidence_gate_rules | protocol_rule | prompt injection; EvidenceGate | R0, R1, R2, R3 | ignore_untrusted_instruction |
| basis.prompt_injection.rule.002.v01 | lewis2020rag | academic_literature | prompt injection; EvidenceGate | R0, R1, R2, R3 | support_architecture_rationale |
| basis.protocol.hmp.001.v01 | local_protocol:hmp_rule_action_mapping | protocol_rule | HMP protocol | R1, R2 | authorize_mapped_action_if_gates_pass |
| basis.protocol.hmp.002.v01 | source_manifest:copied_docs/half_marathon_hmp_protocol.md | protocol_rule | HMP protocol; low risk plan | R1, R2 | require_capacity_scaled_protocol_use |
| basis.evidence.gate.001.v01 | local_rule_spec:evidence_gate_rules | protocol_rule | EvidenceGate; trace completeness | R0, R1, R2, R3 | gate_prescription_claims |
| basis.repair.bounded.001.v01 | local_rule_spec:audit_and_repair_contract | protocol_rule | bounded repair | R1, R2, R3 | repair_or_refuse_with_log |
| basis.repair.bounded.002.v01 | local_protocol:half_marathon_repair_executor | action_library | bounded repair | R1, R2, R3 | support_repair_execution_trace |
| basis.trace.completeness.001.v01 | local_rule_spec:trace_schema | protocol_rule | trace completeness | R0, R1, R2, R3 | fail_or_repair_trace |
| basis.trace.completeness.002.v01 | liu2024exmo | academic_literature | trace completeness; general education | R0, R1 | support_trace_vocabulary_rationale |

## Governance Notes

- `academic_literature` entries are intentionally non-prescription-authorizing unless they are promoted into a curated or protocol rule.
- R3 medical red flags always outrank performance goals, HMP actions, and repair attempts.
- HMP actions are only eligible after RiskGate, EvidenceGate, capacity, and forbidden-condition checks pass.
- Prompt-injection entries treat retrieved or source text as data, not executable instructions.
- Trace completeness is required for auditability, but schema completion does not prove the clinical correctness of the decision.
