# Formal Rule Model

> Artifact task: P2-T8. This is a semi-formal model for the Rule-Governed M-EXRx artifact. It is intentionally implementation-ready while remaining readable for a Rule Challenge paper.

## 1. Core Sets

```text
U  = user profile states
Q  = user requests
E  = evidence records
A  = approved actions
C  = prescription contracts
R  = rules
O  = outputs
T  = traces
```

Allowed final statuses:

```text
S = {answered, partial_answer, ask_clarification, refused}
```

Risk levels:

```text
K = {R0, R1, R2, R3}
R3 > R2 > R1 > R0
```

## 2. Rule Tuple

Each rule is represented as:

```text
rule = (
  rule_id,
  layer,
  priority,
  condition,
  decision,
  obligations,
  prohibitions,
  evidence_requirements,
  trace_requirements
)
```

| Field | Meaning |
|---|---|
| `rule_id` | Stable identifier, e.g. `risk.R3.chest_pain`. |
| `layer` | `risk`, `evidence`, `protocol`, `capacity`, `repair`, `trace`, `ethics`. |
| `priority` | Ordered priority used for conflict arbitration. |
| `condition` | Predicate over profile, request, candidate plan, evidence, and context. |
| `decision` | `allow`, `downgrade`, `ask_clarification`, `repair_required`, `refuse`. |
| `obligations` | Requirements that must be added to the contract/output. |
| `prohibitions` | Actions or claims that must not appear. |
| `evidence_requirements` | Evidence layers and IDs required for prescription eligibility. |
| `trace_requirements` | Trace fields that must record the rule firing and result. |

## 3. Priority Relation

The strict priority order is:

```text
medical_red_flags
> safety_injury_fatigue_environment
> ethics_scope_boundary
> evidence_sufficiency
> protocol_hard_constraints
> capacity_budget
> temporal_progression
> user_constraints
> performance_optimization
> natural_language_preference
```

Conflict rule:

```text
IF rule_i and rule_j conflict
AND priority(rule_i) > priority(rule_j)
THEN decision(rule_i) dominates decision(rule_j).
```

Example:

```text
risk.R3.chest_pain dominates user.preference.do_intervals
=> final status = refused
=> interval workout is forbidden.
```

## 4. Evidence Eligibility Predicate

```text
eligible(e, u, claim) :=
  e.layer in {protocol_rule, action_library, curated_guideline}
  AND e.evidence_id is present
  AND population_match(e, u)
  AND not contraindicated(e, u)
  AND review_status(e) in {approved, active}
```

A prescription claim is valid only when:

```text
prescription_valid(claim) :=
  exists e in E: eligible(e, U, claim)
  AND claim.action_id in approved_actions(C)
  AND no higher_priority_rule_blocks(claim)
```

## 5. Contract Satisfaction

PrescriptionContract satisfaction is defined as:

```text
satisfies(plan, C) :=
  all must(C) are satisfied
  AND no must_not(C) is violated
  AND every prescription claim has eligible evidence
  AND every action is in allowed_actions(C)
  AND no action is in forbidden_actions(C)
  AND volume(plan) <= volume_budget(C)
  AND intensity(plan) <= intensity_budget(C)
  AND progression(plan) <= progression_limit(C)
  AND recovery_requirements(C) are satisfied
```

If `satisfies(plan, C) = false`, the output cannot be `answered`.

## 6. Decision Semantics

| Decision | Semantics |
|---|---|
| `allow` | Candidate may proceed if all lower-level constraints also pass. |
| `downgrade` | Candidate must reduce risk, intensity, volume, specificity, or certainty. |
| `ask_clarification` | Missing or conflicting fields prevent prescription. No individualized plan is allowed. |
| `repair_required` | Candidate has repairable violations. Only bounded repair operations may run. |
| `refuse` | No training prescription is allowed. Safety/ethics boundary only. |

## 7. Refusal Condition

```text
refusal_required(U, Q, C) :=
  risk_level(U, Q) = R3
  OR ethics_scope_violation(U, Q)
  OR repair_conflict_unrepairable(C)
  OR user_requests_rule_bypass(Q)
```

When `refusal_required = true`:

```text
status = refused
forbidden = {workout_plan, intensity_target, race_strategy, return_to_play_clearance}
required_trace = {risk_level, rules_fired, refusal_reason}
```

## 8. Repair Operator

Repair is a bounded transformation:

```text
repair: candidate_plan x violations x contract -> repaired_plan OR refusal
```

Allowed transformation classes:

```text
delete_unsupported_claim
lower_intensity
reduce_volume
add_recovery
replace_with_approved_action
convert_to_partial_answer
refuse_when_unrepairable
```

Invariant:

```text
repair(plan) must not introduce any new action, evidence_id, medical claim, or lower risk level.
```

## 9. Trace Soundness

The trace is sound if:

```text
trace_sound(T, O) :=
  every prescription claim in O maps to evidence_ids/action_ids in T
  AND every blocking rule appears in rules_fired
  AND every repair action appears in repair_log
  AND final_status in T equals output status
```

If trace soundness fails, output status must be `partial_answer` or `repair_required`; it cannot be final `answered`.

