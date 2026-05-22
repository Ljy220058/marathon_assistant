# Layered KB P10 Cross-Test Review

Owner role: Backend / Engineering Coordinator

Branch: `codex/layered-kb-p10-cross-test-review`

## Scope

This review closes the P0-P10 layered KB / GraphRAG backend evidence-kernel implementation pass. It does not sign off frontend UI, product design, or unrelated dirty worktree files.

## Verification Commands

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -m pytest tests/test_kb_source_registry.py tests/test_kb_evidence_binding.py tests/test_kb_graph_evidence.py tests/test_kb_evaluation.py tests/test_kb_health.py -q
```

Result: `16 passed`.

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -m pytest tests/test_daily_schedule_generator.py tests/test_workout_template_retriever.py tests/test_training_plan_review.py tests/test_openapi_contract.py tests/test_api_app.py -q
```

Result: `98 passed, 2 warnings`. The warnings are existing FAISS/distutils deprecation warnings.

```powershell
git diff --check
```

Result: passed with no output.

```powershell
$env:PYTHONUTF8='1'
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe tools/dev/check_repo.py --scope hygiene
```

Result: exit 0 with known warnings about unexpected root items, dirty version-excluded paths, legacy path literals, and large-file candidates.

## Version Boundary

Committed P0-P9 changes are limited to the layered KB source registry, evidence binding, action-library metadata, daily-card `kb_metadata`, graph evidence mapping, KB evaluation, training-plan review metadata, golden questions, KB health checks, and docs/shared contract.

Excluded and not staged in P10:

- `data/vector_kb/default/user_profile.json`
- `data/vector_kb/default/knowledge_graph.json`
- `apps/web/dist/`
- `.pytest_cache/`
- frontend agent files under `apps/web/`
- unrelated product docs, papers, OCR notes, and artifacts

## Cross-Agent Note For Frontend Owner

Backend now emits additive evidence metadata intended for future expert-layer UI:

- `daily_schedule_cards[].kb_metadata`
- `training_plan_review.dimensions.layered_kb`
- `knowledge_layer`
- `evidence_domain`
- `source_registry_id`
- `retrieval_mode`
- `prescription_permission`
- `rag_eval`

Normal user mode must not show raw metadata. Show short labels such as protocol basis, action library, knowledge-base explanation, model general knowledge, or needs evidence. Expert mode can show raw fields and audit details.

## Subagent Usage

Subagents opened in this P0-P10 continuation: `0`.

## Remaining Risks

- The current working tree remains dirty because unrelated backend, frontend, docs, data, and artifact files are being edited by other agents.
- This review does not claim the whole commercial app is complete.
- Full shared-contract exit still requires frontend owner and QA/reviewer sign-off.
