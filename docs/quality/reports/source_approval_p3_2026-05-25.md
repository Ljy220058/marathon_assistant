# P3 Source Approval Report - 2026-05-25

## Scope

This P3 pass only approved sources that were already present in `source_registry_v2.jsonl`, had a local `.url` pointer, and could be checked against a public official page. It did not approve any source for core training prescription.

## Approved Sources

| source_registry_id | Domain pack | Source | Permission | Review result |
| --- | --- | --- | --- | --- |
| `src_external_strava_training_log` | `competitor_product_tasks` | Strava Support: Training Log | `product_design_reference`, `explanation_only` | Approved |
| `src_external_strava_instant_workouts` | `competitor_product_tasks` | Strava Support: Instant Workouts | `product_design_reference`, `explanation_only` | Approved |

## Evidence Boundary

- These sources can support product decisions such as training history display, progress review, personalized workout recommendation UX, difficulty/focus filtering, and device handoff expectations.
- These sources cannot write `main_set`, `intensity`, `duration`, `progression`, `risk_downgrade`, or any other core training prescription field.
- The review deliberately kept both records in `competitor_product_reference`, not `protocol` or `action_library`.

## Metrics After Regeneration

- `approved`: 21
- `candidate`: 36
- `seed_only`: 699
- `can_enter_runtime_index`: 21

## Remaining Blockers

- Domain-pack thickness is still insufficient for commercial launch, especially `user_profile_cases`, `medical_risk`, `rehab_return_to_run`, `training_load`, `strength_conditioning`, `mobility_recovery`, `nutrition_race_fueling`, and `environment_race_context`.
- Live GPT RAG-vs-Base proof is still blocked because the current shell has no `GPT_API_KEY` or `OPENAI_API_KEY`.
- `competitor_product_tasks` improved, but it is still below its target of 12 approved sources.

## Process Note

Do not run multiple `review_source_record.py --write` commands in parallel against the same JSONL registry. The script loads, modifies, and rewrites the whole file; concurrent writes can overwrite each other. Same-registry approvals must run serially.
