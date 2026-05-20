# HMP Rule And Action Mapping

> Artifact task: P2-T6. Source: `sources/copied_docs/half_marathon_hmp_protocol.md`. This file maps the HMP protocol into prescription-eligible `protocol_rule` and `action_library` entries. It does not authorize use when RiskGate, EvidenceGate, or capacity budget blocks the action.

## Mapping Fields

| Field | Meaning |
|---|---|
| `rule_id` | Machine-readable rule identifier. |
| `action_id` | Approved action or workout template identifier. |
| Phase | HMP phase where the action may be considered. |
| Prescription use | What the action can support. |
| Must conditions | Required profile, risk, evidence, or scheduling constraints. |
| Forbidden conditions | Conditions that block the action. |
| Evidence source | Source layer and local evidence ID. |

## Mapping Table

| # | rule_id | action_id | Phase | Prescription use | Must conditions | Forbidden conditions | Evidence source |
|---:|---|---|---|---|---|---|---|
| 1 | `hmp.intro.recovery_run` | `hm_recovery_easy_run` | Intro / recovery | Very easy recovery run | R1 or R2-downgraded; no red flags; low fatigue or explicit recovery objective | R3; fever; severe pain; heat illness signs | `protocol_rule:hmp.section_2_3_7` |
| 2 | `hmp.intro.trail_easy` | `hm_intro_trail_easy` | Intro | Low-pressure aerobic return | Stable footing; no acute injury; intensity by RPE | Unstable injury; severe weather; user asks for pace target through pain | `protocol_rule:hmp.section_3_1` |
| 3 | `hmp.intro.fartlek_hills` | `hm_intro_fartlek_hills` | Intro | Reintroduce speed feel without fixed pace | Current fatigue acceptable; short controlled bouts; at least one easy day after | Recent marathon with high fatigue; pain worsening; R3 | `action_library:hm_intro_fartlek_hills` |
| 4 | `hmp.base.easy_run` | `hm_easy_aerobic_run` | Base | Build aerobic volume | Weekly volume budget available; R1; no injury escalation | Missing weekly mileage; pain > mild; R2 without downgrade | `protocol_rule:hmp.section_2_3_7` |
| 5 | `hmp.base.long_easy` | `hm_long_easy_run` | Base | Extend endurance | Long-run cap from capacity budget; recovery day after when needed | Rapid jump beyond progression limit; recent race fatigue | `protocol_rule:hmp.section_3_2_7_10` |
| 6 | `hmp.base.threshold_progression` | `hm_base_threshold_progression` | Base | Aerobic power / threshold support | Prior easy volume stable; eligible action; no R2 fatigue | R3; acute illness; insufficient base; hard workout within 48h | `action_library:hm_base_threshold_progression` |
| 7 | `hmp.base.moderate_run` | `hm_moderate_aerobic_run` | Base | Medium aerobic load at 75-85% HMP | HMP estimate available; user tolerates moderate load | HMP uncalibrated and user demands exact pace; R2 injury | `protocol_rule:hmp.section_2` |
| 8 | `hmp.base.progression_run` | `hm_progression_run` | Base | Controlled progression from easy to moderate | Clear stop conditions; no worsening pain | Fatigue/high stress; heat risk; no recovery window | `protocol_rule:hmp.section_3_2` |
| 9 | `hmp.base.strides` | `hm_strides` | Base | Running economy / neuromuscular touch | Very short; full recovery; not a hard workout | Acute calf/hamstring pain; severe fatigue | `protocol_rule:hmp.section_3_2` |
| 10 | `hmp.base.hill_strides` | `hm_short_hill_repeats` | Intro / Base | Low-volume strength-speed stimulus | Short controlled repeats; stable injury status | Achilles/calf pain; R3; no warmup capacity | `protocol_rule:hmp.section_3_1_3_2` |
| 11 | `hmp.build.support_90` | `hm_90_support_endurance` | Specific build | Support 95% HMP endurance | Prior base complete; HMP estimate reliable; budget permits | Recent marathon; R2 fatigue; 48h recovery unavailable | `action_library:hm_90_support_endurance` |
| 12 | `hmp.build.short_95` | `hm_95_short_fast_run` | Specific build | Introductory 95% HMP endurance | Start with short distance; capacity-scaled | Jumping to 20-25 km; R2 pain/fatigue; R3 | `protocol_rule:hmp.section_6_1` |
| 13 | `hmp.build.long_95` | `hm_95_long_fast_run` | Race-specific | Half-marathon specific endurance | Progressed through shorter 95% work; high enough weekly volume; recovery after | Ordinary runner directly copying 20-25 km elite upper bound; recent marathon; R2 unresolved | `action_library:hm_95_long_fast_run` |
| 14 | `hmp.build.float_100_1k` | `hm_100_float_intervals_1k` | Specific build | Early HMP metabolic efficiency | HMP calibrated; prior 90/95 support; controlled total HMP volume | Uncalibrated pace; insufficient base; hard session within 48h | `protocol_rule:hmp.section_6_2` |
| 15 | `hmp.race.float_100_long` | `hm_100_float_intervals` | Race-specific late | Core HMP workout with float recovery | Near late specific phase; cumulative HMP volume within budget; no red flags | Too early in cycle; no 90/95 support; R2 fatigue/injury; exceeding budget | `action_library:hm_100_float_intervals` |
| 16 | `hmp.build.speed_105_short` | `hm_105_specific_speed_short` | Specific build | 8K/10K speed reserve | Short reps first; 5K/10K calibration preferred | Endurance-only user forced to 105% without calibration; R2 | `protocol_rule:hmp.section_6_3` |
| 17 | `hmp.race.speed_105_medium` | `hm_105_specific_speed` | Specific / Race-specific | Specific speed reserve | Total fast volume capped; recovery window exists | R3; acute illness; insufficient base; too close to key 100% session | `action_library:hm_105_specific_speed` |
| 18 | `hmp.support.speed_107_110` | `hm_110_support_speed` | Intro / Base / Build | VO2max / speed ceiling support | Current short-distance ability supports pace; reduce to 107-108% when needed | Mechanical 110% target without calibration; injury-prone profile | `action_library:hm_110_support_speed` |
| 19 | `hmp.race.taper_key_session` | `hm_100_late_key_session` | Late race-specific | Final core HMP readiness session | 10-15 days before race; prior progression complete; recovery protected | Inside unsafe proximity to race; fatigue high; red flags; budget exceeded | `protocol_rule:hmp.section_3_4_6_2` |
| 20 | `hmp.safety.no_sub70_copy` | `hm_capacity_scaled_template` | All phases | Scale elite protocol to user capacity | Weekly mileage, training days, recovery and history are present | Copying 70-90 miles/week or elite limits by default | `protocol_rule:hmp.section_7_10` |
| 21 | `hmp.safety.recent_marathon_intro` | `hm_post_marathon_intro_block` | Intro | Post-marathon transition | Recent marathon -> recovery/import phase first | Immediate long 95% HMP fast run or 100% HMP large workout | `protocol_rule:hmp.section_3_1_7` |
| 22 | `hmp.safety.recovery_48h` | `hm_recovery_gap_rule` | All phases | Scheduling safety | High-quality workouts separated by sufficient recovery, normally at least 48h | Back-to-back hard sessions without explicit safe context | `protocol_rule:hmp.section_7` |
| 23 | `hmp.safety.dynamic_hmp_calibration` | `hm_pace_recalibration_check` | All phases | Prevent stale pace prescription | Current HMP estimate or recent race/TT/wearable confidence available | Exact HMP percentages from stale goal pace only | `protocol_rule:hmp.section_7` |
| 24 | `hmp.safety.injury_fatigue_downgrade` | `hm_downgrade_to_easy_or_rest` | All phases | Safe downgrade action | Pain/fatigue signals trigger R2; plan can be reduced | Any attempt to preserve hard target despite risk signal | `protocol_rule:hmp.section_7` |

## Execution Notes

1. `hmp.safety.*` rules are guard rules. They can block or modify other actions but do not create a hard workout.
2. `hm_95_long_fast_run`, `hm_100_float_intervals`, and `hm_105_specific_speed` require both protocol evidence and capacity-budget approval.
3. If HMP calibration is missing, exact HMP percentage pace targets must be replaced by RPE/time-based explanations or `ask_clarification`.
4. If a higher-priority RiskGate rule fires, the mapping table cannot be used to authorize prescription.

