# EvidenceGate Rules

EvidenceGate decides whether a claim may support exercise prescription.

## Evidence Layers

| Layer | Can Support Prescription? | Use |
|---|---|---|
| protocol_rule | yes | HMP protocol, FITT-VP, risk rules, progression limits |
| action_library | yes | approved workouts and substitutions |
| curated_guideline | yes, after rule mapping | ACSM-style guideline or clinician-reviewed boundary |
| academic_literature | no by default | explanation and related work unless curated into rules |
| general_kb | no | background explanation only |
| wiki_context | no | concept explanation only |
| none | no | triggers needs_evidence or clarification |

## Prescription Eligibility

A plan element is prescription-eligible only if it has:

```text
evidence_layer in {protocol_rule, action_library, curated_guideline}
AND evidence_id is present
AND applicable_population matches user profile
AND no triggered higher-priority risk rule blocks it
```

## Unsupported Claim Rule

If a candidate plan includes a training prescription without eligible evidence:

```text
audit_result = repair_required
repair = delete_or_replace_with_approved_action
```

If no replacement exists:

```text
status = partial_answer
trace.needs_evidence = true
```

## Knowledge Boundary

Academic papers can inspire discussion, but they cannot directly authorize a workout unless they are converted into a curated rule with:

- evidence_id
- population
- contraindications
- allowed prescription fields
- uncertainty notes
- review status

## Trace Requirements

Every prescription output must include:

- `evidence_ids`
- `action_ids`
- `evidence_layers`
- `unsupported_claims`
- `needs_evidence`
