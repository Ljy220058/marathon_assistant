# Evidence Gap Map v0.1

## 1. Purpose

This file converts current S1/S1b/S3 failures into evidence-base tasks. It is not a bibliography and does not claim that any pending source is verified.

## 2. Gap Table

| qid | topic | current evidence_id | current status | required evidence | priority |
|---|---|---|---|---|---|
| STAI-P001 | training_intensity_distribution | T02-E01 | pending | Evidence defining typical elite endurance athlete intensity distribution, ideally including polarized/pyramidal distribution or low-intensity dominance. | P0 |
| STAI-P002 | polarized_pyramidal_training | T03-E01 | pending | Evidence defining polarized training and pyramidal training as endurance training intensity-distribution concepts. | P0 |
| STAI-P003 | transfer_to_amateur_runners | T02-E01 | pending | Evidence or guideline explaining why elite athlete intensity distributions should not be directly copied by recreational runners without individualization. | P1 |
| STAI-P004 | stoggl_sperlich_9_week_result | T03-E01 | pending | Exact Stöggl/Sperlich 9-week study result comparing training models and key endurance variables. | P0 |
| STAI-P005 | stoggl_sperlich_9_week_arms | T03-E01 | pending | Exact study arms/training modes compared in the 9-week training study. | P0 |
| STAI-P006 | generalization_from_polarized_result | T03-E01 | pending | Evidence or reasoning basis that one study favoring polarized training does not imply universal prescription for all runners. | P1 |
| STAI-P007 | running_economy_definition | T12-E01 | pending but retrieved candidate exists | Exact definition of running economy with source metadata/page. | P0 |
| STAI-P008 | running_economy_multifactor | T12-E01 | pending | Evidence that running economy is multifactorial and should not be reduced to a single factor such as form. | P1 |
| STAI-P009 | running_economy_performance_relation | T12-E01 | pending | Evidence explaining relationship between running economy and performance, including that it is important but not the sole determinant. | P1 |
| STAI-P010 | heat_illness_red_flags | R11-E01 | pending | Official/medical guidance for confusion or abnormal symptoms after heat exposure/exertion and emergency response. | P0 |
| STAI-P011 | hot_weather_training_deescalation | R11-E01 | pending | Guidance for reducing intensity/duration, avoiding heat exposure, cooling/hydration, and cancelling/modifying high-intensity training in heat. | P0 |
| STAI-P012 | return_after_suspected_heat_illness | R11-E01 | pending | Guidance on not resuming normal training immediately after suspected exertional heat illness and seeking evaluation. | P0 |
| STAI-P013 | cardiovascular_condition_high_intensity | R13-E01 | pending | Guidance that people with cardiovascular disease or abnormal cardiac symptoms should not receive unsupervised high-intensity prescriptions. | P0 |
| STAI-P014 | chest_pain_syncope_palpitations | R13-E01 | pending | Official/medical red-flag guidance for chest pain, syncope, or palpitations during exercise: stop and seek medical evaluation. | P0 |
| STAI-P015 | cv_risk_goal_only_training | R13-E01 | pending | Evidence that training for cardiovascular-risk populations must consider health risk/medical clearance, not only performance goals. | P1 |

## 3. Priority Interpretation

- P0: blocks S3 full-run quality and core paper claims.
- P1: improves applied reasoning and failure analysis.
- P2: useful for expansion but not required for the next full run.

## 4. Immediate Source Targets

1. Training intensity distribution / polarized training:
   - Locate exact Stöggl and Sperlich source.
   - Locate review or paper defining polarized/pyramidal training.

2. Running economy:
   - Fill metadata for the retrieved candidate `36b5639a13f6f78e00f1c2ca46b86e854898.pdf`.
   - Extract exact definition and pages for P007-P009.

3. Heat illness:
   - Prefer CDC, ACSM, NATA, World Athletics, race medical guidance, or equivalent official source.

4. Cardiovascular red flags:
   - Prefer AHA/ACC/ACSM or equivalent medical/exercise participation guidance.

## 5. Rule

Do not mark any evidence as `verified` until exact source metadata and locatable evidence span are recorded in `benchmark_kb/evidence_items_v0.1.jsonl`.
