# Evidence-To-Rule Promotion Protocol

> Artifact task: P2-T9. This protocol prevents ordinary RAG snippets or isolated papers from being treated as direct exercise-prescription authority.

## 1. Promotion Principle

Evidence can support prescription only after it is promoted into a curated rule or approved action with explicit applicability, contraindications, and review status.

```text
retrieved_text != prescription_rule
academic_literature != prescription_rule by default
```

## 2. Evidence States

| State | Meaning | Can support prescription? |
|---|---|---:|
| `raw_retrieved` | Retrieved text, PDF chunk, webpage, or note. | no |
| `screened_reference` | Bibliographic metadata and relevance checked. | no |
| `candidate_rule` | Potential rule drafted with population and contraindications. | no |
| `reviewed_rule` | Human/domain review completed; conflicts checked. | conditional |
| `approved_rule` | Versioned rule with evidence ID and scope. | yes |
| `deprecated_rule` | Outdated or superseded rule. | no |

## 3. Promotion Record Schema

```json
{
  "promotion_id": "promote.acsm.screening.001",
  "source_id": "ref_or_guideline_id",
  "source_type": "guideline|review|trial|protocol|expert_protocol|local_hmp_protocol",
  "candidate_rule_id": "risk.R3.chest_pain",
  "evidence_layer_after_promotion": "curated_guideline|protocol_rule|action_library",
  "population": "adult recreational runners",
  "contraindications": [],
  "allowed_prescription_fields": [],
  "forbidden_prescription_fields": [],
  "reviewer": "human_or_domain_reviewer_id",
  "review_date": "YYYY-MM-DD",
  "version": "v0.1",
  "status": "candidate_rule|reviewed_rule|approved_rule|deprecated_rule",
  "uncertainty_notes": ""
}
```

## 4. Promotion Criteria

| Criterion | Required check |
|---|---|
| Source reliability | Prefer established guidelines, consensus statements, protocol documents, or well-scoped systematic evidence. |
| Applicability | Population, age group, sport, training level, health status, and setting must match the intended rule scope. |
| Actionability | The rule must define allowed/forbidden prescription fields, not just background rationale. |
| Contraindications | Conditions that block or downgrade the rule must be explicit. |
| Conflict scan | Compare against RiskGate, EvidenceGate, HMP protocol, capacity budget, and ethics boundary. |
| Versioning | Rule ID, reviewer, date, and source IDs must be recorded. |
| Traceability | The promoted rule must be citeable by `evidence_id` in trace output. |

## 5. Source-Type Rules

| Source type | Default layer | Promotion path |
|---|---|---|
| Local HMP protocol | `protocol_rule` | Map into HMP rule/action table, then consistency audit. |
| Approved workout template | `action_library` | Register action ID, phase, capacity limits, and forbidden conditions. |
| Clinical or public-health guideline | `curated_guideline` after review | Extract risk boundary or screening rule; do not overfit to training performance. |
| Academic literature | `academic_literature` | Use for discussion unless reviewed and transformed into a narrow rule. |
| General KB / wiki | `general_kb` or `wiki_context` | Explanation only; cannot be promoted without independent reliable source. |
| User anecdote | `profile_context` | Can inform constraints but cannot become general rule. |

## 6. Conflict Handling

If evidence conflicts:

```text
1. Prefer higher safety priority over performance optimization.
2. Prefer guideline/protocol boundary over isolated study.
3. Prefer narrower applicable population over broad but mismatched source.
4. If conflict remains unresolved, mark rule as candidate only and block prescription use.
```

Conflict outcomes:

| Conflict | Outcome |
|---|---|
| Safety rule conflicts with performance rule | Safety rule dominates. |
| Two eligible rules disagree on intensity/volume | Choose conservative lower load or ask clarification. |
| New source weakens an existing safety boundary | Do not weaken until human review and versioned approval. |
| Evidence applicability uncertain | Explanation only; no prescription support. |

## 7. Expiration And Review Cadence

| Rule type | Review trigger |
|---|---|
| Safety/red-flag rule | Any new guideline, adverse-case audit, or benchmark failure. |
| HMP protocol rule | Protocol revision or capacity-budget conflict. |
| Action-library template | New injury/fatigue violation or phase mismatch. |
| Nutrition/environment rule | New guideline or user-risk case family. |

Every approved rule must have:

```text
status = active
version
last_reviewed
next_review_due OR review_trigger
```

If review status is missing or expired:

```text
EvidenceGate treats the rule as explanation-only until renewed.
```

## 8. Promotion Denial Conditions

Do not promote evidence when:

- source is unverifiable or citation metadata is missing
- population does not match the intended user group
- rule would authorize training through red flags
- source only supports a mechanism, not a prescription decision
- conclusion depends on a single small or highly specific study without review
- promotion would require medical diagnosis, treatment, or clearance

