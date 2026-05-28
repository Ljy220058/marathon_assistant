# Enterprise Production Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the locally verified P0/P1 production-readiness gaps found by the DS4Pro MCP enterprise scan.

**Architecture:** Keep changes tightly scoped to existing FastAPI, SQLite, Docker, and Astro browser code. Use existing contract-test style: Python tests read source or call FastAPI TestClient; no new dependencies. Production behavior is controlled by environment variables and existing Fernet key material.

**Tech Stack:** Python 3.11/3.12, FastAPI, pytest, SQLite, cryptography.Fernet, Docker, Astro browser JavaScript.

---

## File Structure

- Modify `apps/backend/src/marathon_qa_assistant/apps/api_app.py`
  - Make expert health token comparison constant-time.
  - Make `/admin/health` status match dependency state.
- Modify `tests/test_health_contract.py`
  - Add tests for degraded admin health and valid token behavior.
- Modify `apps/backend/src/marathon_qa_assistant/services/google_calendar_provider.py`
  - Encrypt/decrypt `oauth_client_secret` using the existing `MARATHON_SYNC_KEY` Fernet helpers.
  - Preserve compatibility with empty legacy values.
- Modify `tests/test_provider_secret_contract.py`
  - Add tests proving Google client secret is not persisted in plaintext and can be read back.
- Modify `apps/web/src/scripts/app.js`
  - Remove legacy `ds_api_key` from `/query` request payload.
  - Add production-configurable API base from `window.MARATHON_API_BASE` / `data-api-base` while preserving localhost auto-detect fallback.
- Modify `tests/test_astro_frontend_contract.py`
  - Update frontend contract tests to require configurable API base and no request-body provider key.
- Modify `apps/backend/Dockerfile`
  - Add explicit timeout to Docker healthcheck.
- Modify `tests/test_infra_contracts.py`
  - Add source-level contract for Docker healthcheck timeout.
- Modify `apps/backend/src/marathon_qa_assistant/core/logging_middleware.py`
  - Add env-controlled client IP redaction while preserving current default behavior.
- Modify `tests/test_logging_contract.py`
  - Add tests for redacted client IP behavior.

---

### Task 1: Harden admin health authentication and status

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/apps/api_app.py:1334-1367`
- Test: `tests/test_health_contract.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_health_contract.py`:

```python
def test_admin_health_status_degrades_when_dependency_fails(client: TestClient, monkeypatch):
    monkeypatch.setenv("MARATHON_EXPERT_API_TOKEN", "expert-test-token")
    monkeypatch.setattr(
        "marathon_qa_assistant.apps.api_app.get_knowledge_base_health_snapshot",
        lambda: {"ready": False, "reason": "kb unavailable"},
    )
    monkeypatch.setattr("marathon_qa_assistant.apps.api_app._check_database_health", lambda: True)

    resp = client.get("/admin/health", headers={"Authorization": "Bearer expert-test-token"})

    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src GRAPHRAG_API_KEY=ci_test_token python -m pytest tests/test_health_contract.py::test_admin_health_status_degrades_when_dependency_fails -v
```

Expected: FAIL because `/admin/health` currently returns `"status": "healthy"`.

- [ ] **Step 3: Write minimal implementation**

In `apps/backend/src/marathon_qa_assistant/apps/api_app.py`, change `_require_expert_token` and `admin_health_check` to:

```python
def _require_expert_token(request: Request):
    """Validate Bearer token against MARATHON_EXPERT_API_TOKEN env var."""
    expert_token = os.getenv("MARATHON_EXPERT_API_TOKEN")
    if not expert_token:
        raise HTTPException(status_code=501, detail="Expert mode not configured.")
    auth = request.headers.get("Authorization", "")
    supplied = auth[len("Bearer "):] if auth.startswith("Bearer ") else ""
    if not supplied or not hmac.compare_digest(supplied, expert_token):
        raise HTTPException(status_code=403, detail="Expert access required.")


@app.get("/admin/health")
async def admin_health_check(request: Request):
    """Admin health check — full component status. Requires expert token."""
    _require_expert_token(request)
    kb_snapshot = get_knowledge_base_health_snapshot()
    db_ok = _check_database_health()
    return {
        "status": "healthy" if (kb_snapshot.get("ready", False) and db_ok) else "degraded",
        "provider": os.getenv("LLM_PROVIDER", "ollama"),
        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:latest"),
        "rag": kb_snapshot,
        "db": db_ok,
        "request_id": getattr(request.state, "request_id", None),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src GRAPHRAG_API_KEY=ci_test_token python -m pytest tests/test_health_contract.py -v
```

Expected: PASS.

---

### Task 2: Encrypt Google OAuth client secret at rest

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/services/google_calendar_provider.py:115-153`
- Test: `tests/test_provider_secret_contract.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_provider_secret_contract.py`:

```python
def test_google_calendar_client_secret_is_encrypted_before_persistence(monkeypatch):
    from cryptography.fernet import Fernet
    from marathon_qa_assistant.services import google_calendar_provider as provider

    key = Fernet.generate_key().decode()
    monkeypatch.setenv("MARATHON_SYNC_KEY", key)

    saved = {}

    class FakeCredentials:
        token = "access-token"
        refresh_token = "refresh-token"
        expiry = None
        client_id = "client-id"
        client_secret = "plain-client-secret"
        token_uri = "https://oauth2.googleapis.com/token"

    class FakeDB:
        def save_sync_token(self, user_id, provider_name, data):
            saved.update(data)

    calendar = provider.GoogleCalendarProvider(credentials_path=__import__("pathlib").Path("client.json"))
    calendar._credentials = FakeCredentials()
    monkeypatch.setattr(calendar, "_db", FakeDB())

    calendar._persist_credentials()

    assert saved["oauth_client_secret"] != "plain-client-secret"
    assert provider._decrypt_token(saved["oauth_client_secret"]) == "plain-client-secret"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src GRAPHRAG_API_KEY=ci_test_token python -m pytest tests/test_provider_secret_contract.py::test_google_calendar_client_secret_is_encrypted_before_persistence -v
```

Expected: FAIL because `oauth_client_secret` is currently persisted as plaintext.

- [ ] **Step 3: Write minimal implementation**

In `apps/backend/src/marathon_qa_assistant/services/google_calendar_provider.py`, add helper:

```python
def _decrypt_optional_token(cipher: str) -> str:
    if not cipher:
        return ""
    try:
        return _decrypt_token(cipher)
    except Exception:
        return cipher
```

Then update credential load and persist:

```python
client_secret = _decrypt_optional_token(str(row.get("oauth_client_secret") or ""))
creds = Credentials(
    token=access_token,
    refresh_token=refresh_token,
    token_uri=row.get("oauth_token_uri", "https://oauth2.googleapis.com/token"),
    client_id=row.get("oauth_client_id", ""),
    client_secret=client_secret,
    scopes=SCOPES,
)
```

and:

```python
data["oauth_client_secret"] = _encrypt_token(self._credentials.client_secret) if self._credentials.client_secret else ""
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src GRAPHRAG_API_KEY=ci_test_token python -m pytest tests/test_provider_secret_contract.py -v
```

Expected: PASS.

---

### Task 3: Remove request-body provider secret and make frontend API base production-configurable

**Files:**
- Modify: `apps/web/src/scripts/app.js:1-2, 5023-5035`
- Test: `tests/test_astro_frontend_contract.py`

- [ ] **Step 1: Write the failing tests**

Modify `test_astro_defaults_to_8010_and_auto_detects_fallback_port` in `tests/test_astro_frontend_contract.py` to include:

```python
    assert "window.MARATHON_API_BASE" in source
    assert "document.body?.dataset?.apiBase" in source
```

Append a new test:

```python
def test_astro_query_payload_does_not_send_provider_api_keys():
    source = _index_source()

    payload_body = source[source.index("function buildQueryPayload") : source.index("function requestQueryPayloadFromBase")]
    assert "ds_api_key" not in payload_body
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_astro_frontend_contract.py::test_astro_defaults_to_8010_and_auto_detects_fallback_port tests/test_astro_frontend_contract.py::test_astro_query_payload_does_not_send_provider_api_keys -v
```

Expected: FAIL because configurable base references do not exist and `ds_api_key` is currently present.

- [ ] **Step 3: Write minimal implementation**

At the top of `apps/web/src/scripts/app.js`, replace the default API base constants with:

```javascript
const LOCAL_API_BASE = "http://127.0.0.1:8010";
const CONFIGURED_API_BASE = String(
  window.MARATHON_API_BASE || document.body?.dataset?.apiBase || ""
).trim().replace(/\/$/, "");
const DEFAULT_API_BASE = CONFIGURED_API_BASE || LOCAL_API_BASE;
const API_BASE_CANDIDATES = [DEFAULT_API_BASE, LOCAL_API_BASE, "http://127.0.0.1:8011", "http://127.0.0.1:8000"];
```

In `buildQueryPayload`, remove the `ds_api_key` line so it returns:

```javascript
  return {
    query,
    mode: "team",
    user_id: "default_user",
    stream: false,
    llm_provider: llmProviderInput.value,
    llm_model: llmModelInput.value.trim(),
    response_mode: responseMode,
    timeout_sec: timeoutSec,
  };
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_astro_frontend_contract.py::test_astro_defaults_to_8010_and_auto_detects_fallback_port tests/test_astro_frontend_contract.py::test_astro_query_payload_does_not_send_provider_api_keys -v
```

Expected: PASS.

---

### Task 4: Add Docker healthcheck timeout contract

**Files:**
- Modify: `apps/backend/Dockerfile:41-42`
- Test: `tests/test_infra_contracts.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_infra_contracts.py`:

```python
def test_backend_docker_healthcheck_has_internal_timeout():
    from pathlib import Path

    dockerfile = Path("apps/backend/Dockerfile").read_text(encoding="utf-8")

    assert "urlopen('http://localhost:8000/health', timeout=3)" in dockerfile
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src GRAPHRAG_API_KEY=ci_test_token python -m pytest tests/test_infra_contracts.py::test_backend_docker_healthcheck_has_internal_timeout -v
```

Expected: FAIL because healthcheck currently lacks the `timeout=3` argument.

- [ ] **Step 3: Write minimal implementation**

Change `apps/backend/Dockerfile` healthcheck command to:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src GRAPHRAG_API_KEY=ci_test_token python -m pytest tests/test_infra_contracts.py::test_backend_docker_healthcheck_has_internal_timeout -v
```

Expected: PASS.

---

### Task 5: Add configurable client IP redaction in request logs

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/core/logging_middleware.py:1-70`
- Test: `tests/test_logging_contract.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_logging_contract.py`:

```python
def test_client_ip_can_be_redacted(monkeypatch):
    from marathon_qa_assistant.core.logging_middleware import _log_client_ip

    monkeypatch.setenv("MARATHON_LOG_CLIENT_IP", "0")

    assert _log_client_ip("127.0.0.1") == "redacted"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src GRAPHRAG_API_KEY=ci_test_token python -m pytest tests/test_logging_contract.py::test_client_ip_can_be_redacted -v
```

Expected: FAIL because `_log_client_ip` does not exist.

- [ ] **Step 3: Write minimal implementation**

In `apps/backend/src/marathon_qa_assistant/core/logging_middleware.py`, import `os`, add:

```python
def _log_client_ip(client_ip: str) -> str:
    if str(os.getenv("MARATHON_LOG_CLIENT_IP") or "1").strip() == "0":
        return "redacted"
    return client_ip
```

Then change middleware extra value to:

```python
"client_ip": _log_client_ip(request.client.host if request.client else ""),
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src GRAPHRAG_API_KEY=ci_test_token python -m pytest tests/test_logging_contract.py -v
```

Expected: PASS.

---

## Final Verification

Run:

```bash
PYTHONUTF8=1 PYTHONPATH=apps/backend/src GRAPHRAG_API_KEY=ci_test_token python -m pytest \
  tests/test_health_contract.py \
  tests/test_provider_secret_contract.py \
  tests/test_astro_frontend_contract.py \
  tests/test_infra_contracts.py \
  tests/test_logging_contract.py \
  tests/test_api_cli_startup_contract.py -v
```

Run:

```bash
git diff --check
```

Expected: all tests pass and no whitespace errors.
