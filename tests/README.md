# Test Matrix

> Each test group protects a specific contract.  Run the most relevant
> group before committing changes in the corresponding area.

## Test Groups

### Product / API Contract Tests

Protect the FastAPI public surface: routes, request/response schemas,
error contracts, and CLI startup guarantees.

| File | What it protects |
|---|---|
| `test_api_app.py` | `/query`, `/feedback`, `/plans/{plan_id}` HTTP contracts |
| `test_api_cli_startup_contract.py` | `api_app:app` import and CLI bootstrap |
| `test_api_plan_validation.py` | Plan save/load validation rules |
| `test_openapi_contract.py` | OpenAPI schema snapshot and field presence |

Run command:

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_api_app.py tests/test_api_cli_startup_contract.py tests/test_api_plan_validation.py -q
```

### Training Plan Skeleton Tests

Protect the structured plan generation: skeleton output,
volume allocation, and weekly schedule generation.

| File | What it protects |
|---|---|
| `test_training_plan_skeleton.py` | Structured plan skeleton fields and defaults |
| `test_volume_allocation.py` | Weekly volume allocation rules and constraints |
| `test_daily_schedule_generator.py` | Monthly calendar, evidence cards, and risk gates |
| `test_half_marathon_capacity_budget.py` | Half-marathon capacity budget calculations |
| `test_half_marathon_protocol.py` | Half-marathon protocol rules |
| `test_half_marathon_schedule_composer.py` | Half-marathon schedule composition |

Run command:

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_training_plan_skeleton.py tests/test_volume_allocation.py tests/test_daily_schedule_generator.py -q
```

### Frontend Contract Tests

Protect the Astro UI: DOM contract, data attributes, API client
behaviour, and component display props.

| File | What it protects |
|---|---|
| `test_astro_frontend_contract.py` | Key DOM ids, data attributes, script entry points |
| `test_plan_ui_display_props.py` | Plan display properties on the UI |
| `test_coach_ui_state_contract.py` | Coach panel UI state transitions |

Run command:

```powershell
cd apps/web; npm run build; cd ../..; $env:PYTHONUTF8='1'; python -m pytest tests/test_astro_frontend_contract.py -q
```

### Security and Observability Tests

Protect security guards and observability contracts.

| File | What it protects |
|---|---|
| `test_security_guards.py` | CORS defaults, API key handling, log sanitisation |
| `test_observability_contract.py` | Request IDs, structured logs, metrics endpoint |
| `test_high_risk_contracts.py` | Medical referral fail-closed behaviour |

Run command:

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_security_guards.py tests/test_observability_contract.py tests/test_high_risk_contracts.py -q
```

### Database Migration Tests

Protect the SQLite migration system and schema versioning.

| File | What it protects |
|---|---|
| `test_database_migrations.py` | Migration application, upgrade from old schema, idempotency |

Run command:

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_database_migrations.py -q
```

### RAG / Retrieval Tests

Protect RAG evaluation metrics and retrieval quality.

| File | What it protects |
|---|---|
| `test_evaluate_rag_ragas_metrics.py` | Ragas metric computation and output format |
| `test_evidence_chain_contract.py` | Evidence chain structure and citation format |

Run command:

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_evaluate_rag_ragas_metrics.py tests/test_evidence_chain_contract.py -q
```

### Repository Governance Tests

Protect monorepo structure, paths, and hygiene.

| File | What it protects |
|---|---|
| `test_monorepo_paths.py` | PROJECT_ROOT, MARATHON_DATA_DIR, vector KB paths, legacy fallbacks |
| `test_kb_bootstrap.py` | Knowledge base bootstrap and health checks |

Run command:

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_monorepo_paths.py tests/test_kb_bootstrap.py -q
```

### Research Script Smokes

Protect research scripts from regressions (not product behaviour).

| File | What it protects |
|---|---|
| `minimal_import_test.py` | Core module can be imported without errors |
| `integration_workflow_test.py` | Full workflow integration smoke |

Run command:

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/minimal_import_test.py tests/integration_workflow_test.py -q
```

## Pre-Commit Minimum

```powershell
# Always run these before committing:
python tools/dev/check_repo.py
git diff --check
git status --short --branch

# Then run the group most relevant to your change type
# (see CONTRIBUTING.md for the full matrix).
```
