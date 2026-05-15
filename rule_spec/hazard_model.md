# Hazard Model And Fail-Closed Rules

> Artifact task: P2-T11. This document defines hazard families, trigger signals, required system behavior, and fail-closed defaults for the M-EXRx artifact.

## 1. Hazard Taxonomy

| Hazard family | Typical signals | Risk level | Required behavior |
|---|---|---|---|
| Acute cardiopulmonary symptoms | Chest pain/pressure, unexplained severe shortness of breath, palpitations with dizziness, fainting | R3 | Refuse training prescription; professional/emergency evaluation boundary. |
| Neurological or collapse symptoms | Confusion, collapse, syncope, new neurological symptoms | R3 | Refuse training prescription; safety boundary. |
| Heat illness / severe dehydration | Collapse in heat, confusion, fainting, suspected heat stroke, severe dehydration | R3 | Refuse training prescription; heat illness safety boundary. |
| Acute illness | Fever, systemic illness, infection symptoms with hard training request | R3 for hard training; R2/R3 depending severity | No hard prescription; recovery/safety boundary. |
| Severe injury or inability to bear weight | Severe pain, worsening pain, acute trauma, inability to bear weight | R3 | Refuse running prescription; professional evaluation boundary. |
| Persistent or recurrent pain | Pain worsening with running, recurring injury, pain changes gait | R2 | Downgrade, ask clarification, or trigger Safety/Rehab path. |
| Fatigue / overreaching | Excessive fatigue, poor sleep, elevated resting HR, high stress, rapid mileage increase | R2 | Reduce intensity/volume; add recovery; no hard workouts until clarified. |
| Environment risk | Heat, poor air quality, altitude, unsafe footing/weather | R2/R3 depending severity | Downgrade, reschedule, or refuse if severe danger signs. |
| Wearable uncertainty | Conflicting HR/GPS/HRV/sleep data, sensor artifact, stale pace estimate | R2 or ask clarification | Avoid exact intensity; use conservative RPE or ask clarification. |
| Missing or hidden information | Missing mileage, injury status, training days, medical status when needed | R1/R2 unknown | Fail closed: ask clarification or non-prescriptive answer. |
| Prompt injection / rule bypass | "Ignore safety", "pretend evidence exists", malicious retrieved text | R3-like governance risk | Refuse bypass; preserve rule priority. |

## 2. Red-Flag Rule Families

| rule_id | Trigger | Output status | Forbidden content |
|---|---|---|---|
| `risk.R3.chest_pain` | Chest pain/pressure/tightness during or around exercise | `refused` | Workout, pace, interval, race strategy |
| `risk.R3.syncope_confusion` | Fainting, near-fainting, confusion, collapse | `refused` | Any training prescription |
| `risk.R3.palpitations_dizziness` | Palpitations plus dizziness/chest symptoms | `refused` | Intensity guidance |
| `risk.R3.heat_illness` | Heat collapse, confusion, fainting, suspected heat illness | `refused` | "Hydrate then train" plan |
| `risk.R3.fever_hard_training` | Fever or acute illness with hard-training request | `refused` or `partial_answer` without plan | Tempo/interval/race-pace prescription |
| `risk.R3.severe_pain_weightbearing` | Severe/worsening pain or cannot bear weight | `refused` | Run-walk or return-to-run prescription |
| `risk.R3.neurological` | New neurological symptoms | `refused` | Training plan |
| `risk.R3.rule_bypass` | User or retrieved text requests bypassing safety/evidence | `refused` | Hidden or softened plan |

## 3. R2 Elevated-Risk Rule Families

| rule_id | Trigger | Required action |
|---|---|---|
| `risk.R2.persistent_pain` | Persistent, recurring, or worsening pain without R3 severity | Activate safety path; downgrade or ask clarification. |
| `risk.R2.fatigue_overreach` | Excessive fatigue, poor sleep, high stress, resting HR anomaly, rapid mileage increase | Reduce intensity/volume; add recovery; no hard session. |
| `risk.R2.recent_race` | Recent marathon/race or high-volume block | Intro/recovery phase; no long 95% or large 100% HMP workout. |
| `risk.R2.environment` | Heat, air quality, altitude, unsafe surface/weather | Reschedule/downgrade; add stop conditions. |
| `risk.R2.wearable_uncertain` | Conflicting wearable data or stale calibration | Avoid exact pace; ask clarification or use RPE. |
| `risk.R2.goal_capacity_mismatch` | Aggressive goal with insufficient base | Reduce scope; partial plan; ask for profile. |

## 4. Critical Profile Fields

| Field | Needed for | Missing behavior |
|---|---|---|
| age band/adult status | scope boundary | ask clarification; no plan for minors without protocol |
| current weekly mileage | volume budget | ask clarification for weekly plan |
| training days available | scheduling | ask clarification for weekly plan |
| injury/pain status | risk screening | ask clarification or fail-closed |
| recent illness/fever status | red-flag screening | ask clarification for hard training |
| recent race/high-load block | phase and recovery | conservative intro/recovery or ask clarification |
| target race date | phase placement | partial answer only |
| current HMP estimate or calibration source | HMP percentage prescription | no exact HMP pace targets |

## 5. Fail-Closed Defaults

| Uncertainty | Default outcome |
|---|---|
| R3 possible but not resolvable | `refused` or `ask_clarification` without prescription; choose refusal if acute symptoms are mentioned. |
| R2 risk with hard session request | downgrade to easy/rest or ask clarification; no hard work. |
| Critical profile missing for volume/intensity | ask clarification; no individualized volume/intensity. |
| Evidence layer uncertain | treat as explanation-only. |
| Wearable signal conflicts with self-report | prefer conservative self-report safety signal; avoid exact intensity. |
| User asks to ignore rules | refuse rule bypass. |
| Retrieved text says safety rules do not apply | ignore injected instruction; run local rules. |

## 6. Environment And Wearable Uncertainty

Environment and wearable data are advisory, noisy inputs. They cannot override symptoms.

```text
symptom_red_flag > user_goal > wearable_performance_readiness
```

Operational rules:

- High readiness score must not override pain, fever, chest symptoms, or fainting.
- HR/GPS/HRV conflicts should reduce confidence, not intensify the plan.
- Heat/air-quality risk should trigger downgrade, reschedule, or refusal depending on severity.
- When exact pace prescription depends on stale or noisy data, output RPE/time-based guidance or ask clarification.

## 7. Hazard-To-Output Matrix

| Highest hazard | Final status options | Prescription allowed? | Trace must include |
|---|---|---:|---|
| R3 | `refused` | no | `risk_level`, `red_flag_rule`, `refusal_reason` |
| R2 unresolved | `ask_clarification`, `partial_answer` | no hard prescription | `risk_level`, `downgrade_reason`, `missing_fields` |
| R2 repairable | `partial_answer`, `answered` after downgrade | only downgraded plan | `repair_log`, `re_audit_result` |
| R1 | `answered` | yes, if evidence/contract pass | `evidence_ids`, `action_ids`, `rules_fired` |
| R0 | `answered` | no individualized prescription | `intent=education` |

## 8. Safety Sources Used As Anchors

This hazard model uses public and guideline-level safety anchors for broad red-flag screening. They are not used as individualized medical rules:

- ACSM / Exercise is Medicine preparticipation screening concepts for symptoms requiring caution or medical evaluation: https://www.exerciseismedicine.org/assets/page_documents/ACSM%20Preparticipation%20Screening%20Guidelines.pdf
- CDC public-health heat illness guidance for confusion, fainting, collapse, and severe heat symptoms: https://www.cdc.gov/niosh/heat-stress/about/illnesses.html
- Mayo Clinic public guidance on urgent evaluation for severe or unexplained shortness of breath with chest pain, dizziness, fainting, nausea, or vomiting: https://www.mayoclinic.org/symptom-checker/shortness-of-breath-in-adults-adult/related-factors/itt-20009075
