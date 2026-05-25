# P5 Provider Secret Boundary Report - 2026-05-25

## Scope

This pass removed the active DeepSeek API key path from `/query` request bodies. Provider keys must come from the server-side environment or secure backend configuration, not from browser JSON payloads.

## Changes

- `QueryRequest` no longer exposes `ds_api_key`.
- `_build_llm_config()` no longer copies a request-body key into workflow config.
- Legacy clients that still send `ds_api_key` are ignored by the request model instead of becoming an active secret path.
- Added `tests/test_provider_secret_contract.py` to lock the OpenAPI and config behavior.

## Boundary

- This pass does not remove internal test helpers that pass provider keys directly into lower-level LLM invocation functions.
- This pass does not modify frontend code because frontend files are actively being changed by another agent. The frontend contract remains: do not send provider keys in `/query`.

## Verification

- `python -m pytest tests/test_provider_secret_contract.py -q`
- `rg -n 'request\\.ds_api_key|ds_api_key:|"ds_api_key"\\s*:\\s*request' apps/backend/src/marathon_qa_assistant/apps apps/backend/src/marathon_qa_assistant/nodes tests/test_provider_secret_contract.py -S`
