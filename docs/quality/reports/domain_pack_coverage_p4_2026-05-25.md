# P4 Domain Pack Coverage Report - 2026-05-25

## Scope

This pass raised the short-term approved-source floor for key non-core domain packs. It did not approve any new source for core prescription fields.

## Result

| Domain pack | Approved ready sources after P4 | Boundary |
| --- | ---: | --- |
| `training_load` | 3 | explanation only |
| `medical_risk` | 3 | risk gate / explanation only |
| `rehab_return_to_run` | 3 | rehab guidance / explanation only |
| `strength_conditioning` | 3 | rehab-strength guidance / explanation only |
| `mobility_recovery` | 3 | recovery explanation only |
| `nutrition_race_fueling` | 3 | nutrition guidance / explanation only |
| `environment_race_context` | 3 | environment risk gate / explanation only |
| `competitor_product_tasks` | 4 | product design reference only |
| `training_protocols` | 5 | existing internal reviewed pilot only |
| `action_library` | 5 | existing internal reviewed pilot only |
| `user_profile_cases` | 0 | still blocked until anonymized reviewed cases exist |

## Important Boundaries

- P4 did not create fake user cases. `user_profile_cases` remains 0 because real cases require anonymization, consent/retention policy, and privacy review.
- P4 did not promote medical, rehab, nutrition, environment, or competitor references to `can_write_core`.
- P4 kept all newly approved external sources as `explanation_only`.
- One candidate, `src_external_ioc_load_injury_2016`, was not approved because the URL check returned HTTP 403 from the local verifier.

## Verification Snapshot

- `approved`: 35
- `candidate`: 32
- `seed_only`: 699
- `can_enter_runtime_index`: 35
- `approved` local path missing count: 0

## Remaining Commercial Blockers

- Live GPT RAG-vs-Base proof is still blocked by missing `GPT_API_KEY` / `OPENAI_API_KEY`.
- `user_profile_cases` still requires a privacy-reviewed ingestion path.
- Core domains still need thicker commercial-grade reviewed packs:
  - `training_protocols`: target 20, current 5
  - `action_library`: target 20, current 5
- Non-core domains are improved to 3 each but still below long-term target 12.
