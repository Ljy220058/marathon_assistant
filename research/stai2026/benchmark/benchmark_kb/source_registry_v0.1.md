# Benchmark KB Source Registry v0.1

## Purpose

This registry tracks sources considered for the benchmark-specific evidence base. A source may enter `evidence_items_v0.1.jsonl` as `verified` only after exact source metadata and locatable evidence spans are available.

## Candidate Source Groups

| source_id | topic | source_type | status | notes |
|---|---|---|---|---|
| T01 | exercise_prescription | official_guideline | verified_partial | Official ACSM/EIM PDF located; P031-P032 evidence spans added for prescription dimensions and individualization. |
| T02 | training_intensity_distribution | academic_paper | verified_partial | Frontiers full text located; P001-P003 evidence spans added for intensity distribution concepts and transfer boundary. |
| T03 | polarized_pyramidal_training | academic_paper | verified_partial | Frontiers full text located; P004-P006 evidence spans added for 9-week result, training arms, and generalization boundary. |
| T07 | precompetition_taper | academic_paper | verified_partial | LWW full-text page located; P033-P034 spans added for taper as load reduction and recovery-oriented competition preparation. |
| T09 | world_class_distance_runner_training | academic_paper | verified_partial | Open-access Springer page located; P016-P018 evidence spans added for volume, low-intensity role, and periodization. |
| T10 | training_load_fatigue_monitoring | academic_paper | verified_partial | Open-access Springer page located; P019-P021 evidence spans added for internal/external load, multifactorial fatigue, and conservative monitoring use. |
| T12 | running_economy | academic_paper | verified_partial | Sports Medicine - Open full text located; P007-P009 spans added for definition, multifactorial determinants, and performance boundary. |
| T13 | strength_training_running_performance | academic_paper | verified_partial | Open-access Springer/PubMed Central article located; P022-P024 evidence spans added for strength-training benefit and dose/fatigue boundaries. |
| R01 | overtraining_syndrome | official_guideline | verified_partial | PubMed/publisher metadata located; P035-P036 spans added for prolonged maladaptation and conservative handling of persistent fatigue. |
| R02 | load_and_injury_risk | official_guideline | verified_partial | IOC Part 1 PDF located; P037-P038 spans added for load-management nuance. |
| R03 | load_and_illness_risk | official_guideline | verified_partial | IOC Part 2 open repository PDF located; P039-P040 spans added for load/recovery/illness safety. |
| R05 | training_load_change_running_injury | academic_paper | verified_partial | Public full-text PDF located; P025-P027 upgraded from pending to verified candidate spans, with caution about limited evidence. |
| R07 | lower_extremity_running_injuries | academic_paper | verified_partial | BJSM article page located; P043-P044 spans added for persistent pain and generalization boundaries. |
| R08 | running_injury_incidence | academic_paper | verified_partial | Open-access Springer page located; P028-P030 evidence spans added for per-1000h incidence, runner-type differences, and limitations. |
| R10 | exertional_heat_illness_acsm | official_guideline | verified_partial | Official ACSM PDF located; P045 span added for gradual heat acclimatization/intensity adjustment. |
| R11 | heat_illness_safety | official_guideline | verified_partial | NATA PDF located; P010-P012 spans added for emergency response, heat-risk de-escalation, and return-to-activity boundary. |
| R12 | exercise_preparticipation_screening | official_guideline | verified_partial | LWW full-text page located; P041-P042 spans added for screening and vigorous-exercise clearance boundaries. |
| R13 | cardiovascular_red_flags | official_guideline | verified_partial | ESC guideline page located; P013-P015 spans added for cardiovascular risk assessment, red flags, and individualized decision-making. |

## Verification Rule

- Do not mark as `verified` without a locatable page, section, paragraph, URL anchor, or exact source file path.
- Do not infer page numbers from model output.
- Keep quotes short and use paraphrase for longer content.
