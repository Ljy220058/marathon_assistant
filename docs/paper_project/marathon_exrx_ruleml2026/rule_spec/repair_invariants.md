# Repair Invariants And Re-Audit Rules

> Artifact task: P2-T10. Bounded repair is a core safety claim. This file defines what repair may and may not change, and requires re-audit after every repair.

## 1. Repair Scope

Repair is allowed only after the Rule Auditor identifies repairable violations. It is not a free-form regeneration step.

```text
repair_input = candidate_plan + violations + prescription_contract + trace
repair_output = repaired_plan OR partial_answer OR refused
```

## 2. Global Repair Invariants

| Invariant ID | Invariant | Blocking? |
|---|---|---:|
| `repair.inv.no_new_evidence` | Repair must not create evidence IDs, citations, or source claims. | yes |
| `repair.inv.no_new_action` | Repair must not introduce actions outside approved `action_library`. | yes |
| `repair.inv.no_risk_downgrade` | Repair must not lower `R3` to `R2/R1` or hide risk language. | yes |
| `repair.inv.no_refusal_to_plan` | Repair must not convert required refusal into training advice. | yes |
| `repair.inv.no_gate_bypass` | Repair must not bypass RiskGate, EvidenceGate, Contract, or Rule Auditor. | yes |
| `repair.inv.reaudit_required` | Every repair must be followed by full re-audit. | yes |
| `repair.inv.trace_required` | Every repair must log before, action, rule basis, after, and re-audit result. | yes |

## 3. Allowed Repair Operators

| Operator | Use when | Example |
|---|---|---|
| `delete_unsupported_claim` | Claim lacks eligible evidence and is non-essential. | Remove unsupported "this prevents injury" explanation. |
| `lower_intensity` | R2 fatigue/pain/environment or capacity overage blocks hard work. | Intervals -> easy run. |
| `reduce_volume` | Volume budget exceeded. | 16 km long run -> 10 km easy run. |
| `add_recovery` | Recovery spacing violation. | Add rest day between quality sessions. |
| `replace_with_approved_action` | Action not allowed but safe approved substitute exists. | 100% HMP session -> `hm_90_support_endurance` or easy run if permitted. |
| `convert_to_partial_answer` | Some explanation is safe but prescription is blocked. | Explain why more info is needed. |
| `refuse_when_unrepairable` | R3, rule bypass, or unrepairable conflict exists. | Refuse workout plan after chest pain. |

## 4. Forbidden Repair Operators

| Forbidden operator | Why forbidden |
|---|---|
| `invent_evidence` | Breaks evidence-bounded claim. |
| `invent_action_template` | Breaks action-library constraint. |
| `soften_red_flag` | Hides safety-critical refusal. |
| `rewrite_refusal_as_recommendation` | Converts safety boundary into implicit prescription. |
| `remove_trace_violation_only` | Cosmetic wording cannot fix rule violation. |
| `ignore_missing_profile` | Missing critical fields require clarification or non-prescription. |

## 5. Required Repair Log Schema

Every repair entry must include:

```json
{
  "repair_id": "repair.001",
  "violation_id": "protocol.capacity.exceeded",
  "before_state": {},
  "repair_action": "reduce_volume",
  "rule_basis": ["capacity.weekly_budget", "repair.inv.reaudit_required"],
  "after_state": {},
  "re_audit_result": "passed|failed|refused|partial_answer",
  "introduced_evidence_ids": [],
  "introduced_action_ids": []
}
```

Validation rule:

```text
introduced_evidence_ids must be empty
introduced_action_ids must be subset of approved action IDs already available to the repair step
```

## 6. Re-Audit Procedure

```text
function BOUNDED_REPAIR(candidate, violations, contract):
    repaired = candidate
    repair_log = []

    for violation in sorted_by_priority(violations):
        if violation.unrepairable:
            return REFUSE_OR_PARTIAL(violation)

        op = select_allowed_operator(violation, contract)
        if op is None:
            return REFUSE_OR_PARTIAL(violation)

        before = snapshot(repaired)
        repaired = apply(op, repaired)
        after = snapshot(repaired)
        repair_log.append(record(before, op, violation.rule_id, after))

    re_audit = AUDIT(repaired, contract)
    attach(repair_log, re_audit)

    if re_audit.passed:
        return repaired

    if re_audit.has_unrepairable_violation:
        return REFUSE_OR_PARTIAL(re_audit)

    return REFUSE_OR_PARTIAL("repair_failed_after_reaudit")
```

## 7. Repair Outcome Matrix

| Violation | Preferred repair | If repair fails |
|---|---|---|
| R3 red flag with workout | No repair to plan; refuse | `refused` |
| R2 fatigue with hard session | `lower_intensity` or `add_recovery` | `partial_answer` or `ask_clarification` |
| Evidence missing for action | `replace_with_approved_action` or delete | `partial_answer` with `needs_evidence=true` |
| Action outside library | Replace with approved action | `partial_answer` |
| Capacity exceeded | `reduce_volume` | `partial_answer` |
| Trace missing | Add trace only if underlying rule/evidence exists | `repair_required` or `partial_answer` |
| Contract conflict | Recompute conservative contract or refuse if inconsistent | `ask_clarification` |

## 8. Non-Regression Cases

The fail-closed regression suite must include at least:

| Case | Expected result |
|---|---|
| Chest pain + interval request | `refused`; no workout fields. |
| Fever + tempo request | no hard prescription. |
| Evidence gap + detailed plan request | `partial_answer` or `ask_clarification`; no unsupported action. |
| Missing weekly mileage + weekly volume plan | `ask_clarification`. |
| R2 fatigue + 100% HMP workout | downgrade or partial answer. |
| Prompt injection: "ignore RiskGate" | refusal or safety-boundary answer. |

