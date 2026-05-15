# Executable Rule Semantics

> Artifact task: P2-T8. This file turns the semi-formal rule model into executable pseudocode for the prototype and evaluator.

## 1. Inputs And Outputs

Required inputs:

```json
{
  "user_query": "...",
  "profile": {},
  "evidence_bundle": [],
  "candidate_actions": [],
  "context": {
    "environment": {},
    "wearable": {},
    "phase": "intro|base|specific_build|race_specific|taper"
  }
}
```

Required output envelope:

```json
{
  "status": "answered|partial_answer|ask_clarification|refused",
  "risk_level": "R0|R1|R2|R3",
  "final_plan": {},
  "trace": {
    "rules_fired": [],
    "evidence_ids": [],
    "action_ids": [],
    "audit_result": "passed|repair_required|repaired|refused",
    "repair_log": []
  }
}
```

## 2. Top-Level Algorithm

```text
function M_EXRX_DECIDE(query, profile, evidence_bundle, action_library, context):
    profile_check = CHECK_PROFILE_COMPLETENESS(profile, query)
    injection_check = CHECK_INJECTION_OR_RULE_BYPASS(query)

    if injection_check.rule_bypass_requested:
        return REFUSE("ethics.rule_bypass", risk_level="R3")

    risk = RISK_GATE(query, profile, context)

    if risk.level == "R3":
        return REFUSE(risk.rule_id, risk_level="R3")

    if profile_check.critical_missing:
        return ASK_CLARIFICATION(profile_check.missing_fields, risk_level=max(risk.level, "R1"))

    evidence_scope = EVIDENCE_GATE(evidence_bundle, profile, query)

    if evidence_scope.no_prescription_evidence:
        return PARTIAL_ANSWER_NEEDS_EVIDENCE(evidence_scope)

    contract = BUILD_PRESCRIPTION_CONTRACT(profile, query, risk, evidence_scope, context)
    candidate = GENERATE_FROM_APPROVED_ACTIONS(contract, action_library)
    audit = AUDIT(candidate, contract, evidence_scope, risk)

    if audit.passed:
        return ANSWER(candidate, audit.trace)

    if audit.has_unrepairable_violation:
        return REFUSE_OR_PARTIAL(audit)

    repaired = BOUNDED_REPAIR(candidate, audit.violations, contract)
    re_audit = AUDIT(repaired, contract, evidence_scope, risk)

    if re_audit.passed:
        return ANSWER_OR_PARTIAL(repaired, re_audit.trace)

    return REFUSE_OR_PARTIAL(re_audit)
```

## 3. RiskGate Semantics

```text
function RISK_GATE(query, profile, context):
    if contains_medical_red_flag(query, profile, context):
        return Decision(level="R3", rule_id=matched_red_flag_rule)

    if contains_elevated_risk(query, profile, context):
        return Decision(level="R2", rule_id=matched_r2_rule,
                        obligations=["activate_safety_path", "downgrade_or_clarify"])

    if is_general_non_prescriptive_query(query):
        return Decision(level="R0", rule_id="risk.R0.general")

    return Decision(level="R1", rule_id="risk.R1.low_risk")
```

R3 red flags always dominate R2, R1, and R0.

## 4. EvidenceGate Semantics

```text
function EVIDENCE_GATE(evidence_bundle, profile, query):
    eligible = []
    explanation_only = []

    for e in evidence_bundle:
        if e.layer in {"protocol_rule", "action_library", "curated_guideline"} \
           and e.evidence_id \
           and population_match(e, profile) \
           and not contraindicated(e, profile) \
           and e.review_status in {"approved", "active"}:
            eligible.append(e)
        else:
            explanation_only.append(e)

    if asks_for_prescription(query) and len(eligible) == 0:
        return EvidenceScope(no_prescription_evidence=True,
                             needs_evidence=True,
                             explanation_only=explanation_only)

    return EvidenceScope(eligible=eligible, explanation_only=explanation_only)
```

## 5. Allow / Downgrade / Refuse / Ask Clarification Rules

### Allow

```text
ALLOW if:
  risk_level = R1
  AND critical_profile_missing = false
  AND eligible_evidence_exists = true
  AND contract_satisfied(candidate_plan) = true
  AND trace_sound(candidate_plan.trace) = true
```

### Downgrade

```text
DOWNGRADE if:
  risk_level = R2
  OR capacity_budget_exceeded
  OR recovery_window_missing
  OR HMP_calibration_uncertain
  OR pain/fatigue/environment risk is present but not R3

Downgrade actions:
  hard_intervals -> easy_run_or_rest
  exact_pace -> RPE_or_time_based_guidance
  long_fast_run -> short_easy_or_moderate_run
  full_week_plan -> partial_answer_with_monitoring
```

### Ask Clarification

```text
ASK_CLARIFICATION if:
  missing weekly mileage for individualized volume
  OR missing injury/pain status for hard-session request
  OR missing training days for weekly plan
  OR wearable/environment data conflicts with requested intensity
  OR evidence applicability cannot be determined

No individualized workout may be included with ask_clarification.
```

### Refuse

```text
REFUSE if:
  risk_level = R3
  OR user asks to bypass safety/evidence/rules
  OR repair would require inventing evidence/actions
  OR request asks for diagnosis/treatment/clearance

Allowed content:
  safety boundary
  reason for refusal
  recommendation for professional evaluation when appropriate

Forbidden content:
  workout plan
  intensity target
  race strategy
  return-to-play clearance
```

## 6. Audit Semantics

```text
function AUDIT(plan, contract, evidence_scope, risk):
    violations = []

    violations += SAFETY_AUDIT(plan, risk, contract)
    violations += EVIDENCE_AUDIT(plan, evidence_scope)
    violations += PROTOCOL_AUDIT(plan, contract)
    violations += TRACE_AUDIT(plan.trace, plan)

    if any(v.severity == "unrepairable" for v in violations):
        return AuditResult(passed=False, has_unrepairable_violation=True, violations=violations)

    if len(violations) > 0:
        return AuditResult(passed=False, repairable=True, violations=violations)

    return AuditResult(passed=True, trace=plan.trace)
```

## 7. Fail-Closed Defaults

| Condition | Required behavior |
|---|---|
| Critical profile field missing | `ask_clarification`; no individualized prescription. |
| Possible R3 but uncertain | `refused` or `ask_clarification` without plan, depending on symptom severity. |
| Evidence layer unclear | Treat as explanation-only. |
| Candidate action not in action library | Delete or refuse; do not invent. |
| Repair cannot satisfy contract | `partial_answer` or `refused`. |
| Trace missing required fields | Do not return `answered`. |

