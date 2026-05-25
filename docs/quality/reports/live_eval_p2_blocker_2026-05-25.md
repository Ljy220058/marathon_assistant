# Live Eval P2 Blocker - 2026-05-25

## Scope

This report records the first P2 preflight for `docs/quality/backend_rag_commercial_hardening_todolist.md`.

## Completed Before Blocker

- Confirmed the golden fixture contains exactly 200 questions.
- Confirmed the fixture distribution matches the planned proof split:
  - `training_protocols=20`
  - `action_library=20`
  - `training_load=20`
  - `medical_risk=20`
  - `rehab_return_to_run=20`
  - `strength_conditioning=18`
  - `mobility_recovery=18`
  - `nutrition_race_fueling=18`
  - `environment_race_context=16`
  - `competitor_product_tasks=15`
  - `user_profile_cases=15`
- Fixed P1 so artifact capture now sends `user_id=default_user` by default.
- Added `--user-id` to `tools/kb/build_live_eval_answer_artifacts.py`.
- Added HTTP status-aware error reporting for `/query` artifact capture failures.
- Verified P1 tests:

```text
python -m pytest tests/test_kb_live_eval_artifacts.py tests/test_kb_live_eval_contract.py -q
16 passed
```

- Verified live eval summary helpers:

```text
python -m pytest tests/test_kb_rag_vs_base_eval.py tests/test_kb_live_eval_contract.py tests/test_kb_live_eval_artifacts.py -q
17 passed
```

## Blocker

The current shell environment does not expose a usable GPT key:

```text
GPT_API_KEY=missing
OPENAI_API_KEY=missing
GPT_BASE_URL=missing
GPT_MODEL=missing
```

Per the plan, this run must not use keys pasted in chat history and must not write keys into repository files, reports, or logs.

## Required Human/Environment Action

Set one of these before rerunning P2:

```powershell
$env:GPT_API_KEY='<redacted>'
$env:GPT_BASE_URL='https://api.aisz.mom/v1'
$env:GPT_MODEL='gpt-5.5'
```

or:

```powershell
$env:OPENAI_API_KEY='<redacted>'
$env:OPENAI_BASE_URL='https://api.aisz.mom/v1'
$env:OPENAI_MODEL='gpt-5.5'
```

Do not commit these values. Do not place them in `.env`, docs, JSON reports, shell history snippets, or frontend localStorage.

## Next Command After Key Is Present

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python tools/kb/build_live_eval_answer_artifacts.py --provider gpt --max-questions 3 --resume --user-id default_user
python tools/kb/run_live_rag_vs_base_eval.py --provider gpt --artifact-input data/knowledge/governance/live_rag_vs_base_answer_artifacts.jsonl --max-questions 3
```

Only after the 3-question smoke passes should the 200-question run start.
