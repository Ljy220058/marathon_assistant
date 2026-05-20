# RiskGate Rules

RiskGate determines whether the system may generate an individualized exercise prescription.

## Risk Levels

| Level | Meaning | System Behavior |
|---|---|---|
| R0 | General education or concept query | explain only; no individualized prescription |
| R1 | Low-risk individualized planning | generate plan within contract |
| R2 | Elevated risk | activate safety expert; downgrade, reduce, or ask clarification |
| R3 | Medical red flag | refuse training prescription; recommend professional evaluation |

## R3 Red Flags

Trigger `R3` when the request contains any of:

- chest pain, pressure, or unexplained shortness of breath during exercise
- syncope, near-syncope, fainting, or confusion
- palpitations with dizziness or chest symptoms
- suspected heat illness, collapse, or severe dehydration
- fever or acute illness while requesting hard training
- new neurological symptoms
- severe or worsening pain with inability to bear weight

Action:

```text
status = refused
allowed_output = safety boundary + seek medical evaluation
forbidden_output = workout plan, intensity target, race strategy
```

## R2 Elevated Risk

Trigger `R2` when the request contains any of:

- persistent pain, recurring injury, or pain worsening with running
- excessive fatigue, poor sleep, abnormal resting heart rate, or signs of overreaching
- recent race, recent high-volume block, or rapid mileage increase
- high heat, poor air quality, altitude stress, or risky environment
- conflicting wearable data that makes intensity prescription unreliable
- aggressive goal with insufficient training base

Action:

```text
status = partial_answer or downgraded_plan
activate = Rehab/Safety Expert
must = reduce intensity or volume; include monitoring and stop conditions
must_not = prescribe hard intervals or race-pace overload without evidence
```

## R1 Low Risk

R1 allows individualized planning only when:

- no red flags are present
- no unresolved injury/fatigue/environment constraints dominate the request
- user profile has enough training base information
- action library and protocol rules support the requested workout type

## R0 General Query

R0 is used for non-prescriptive questions:

- "What is tapering?"
- "How is half-marathon training usually structured?"
- "What does easy pace mean?"

R0 may explain concepts but must not fabricate user-specific prescription.
