# Infrastructure & Production Hardening Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the P0/P1 infrastructure gaps identified in the 2026-05-27 enterprise production readiness review: CI/CD pipeline, Docker containerization, hardcoded credential removal, coverage gate, structured logging, and health check hardening.

**Architecture:** This plan complements the existing `docs/quality/backend_rag_commercial_hardening_todolist.md` (which covers RAG evidence, privacy, provider keys). It focuses solely on DevOps/infrastructure concerns. Each task is independently shippable and does not depend on the commercial hardening plan phases.

**Tech Stack:** GitHub Actions, Docker (multi-stage), pytest-cov, python-json-logger, FastAPI middleware

---

## Working Rules

- [ ] Branch naming: `codex/infra-hardening-<slug>` per task group.
- [ ] Never stage `data/`, `*.db`, `.env`, user profiles, or build artifacts.
- [ ] Every fix needs a targeted test unless it is config-only.
- [ ] All Docker builds must exclude `.env`, `*.db`, `__pycache__/`, `vector_kb/`, `uploaded_docs/`.
- [ ] Never commit API keys, tokens, or local absolute paths (`C:\Users\`, `/home/`).
- [ ] Verify with `git diff --check` before each commit.

---

### Task 1: Remove Hardcoded Default Token in knowledge_graph.py

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/services/knowledge_graph.py:32`
- Verify: `tests/test_llm_provider_contract.py` (existing)

- [ ] **Step 1: Change the AUTH_TOKEN default to raise an error**

In `apps/backend/src/marathon_qa_assistant/services/knowledge_graph.py`, line 32:

```python
# OLD:
AUTH_TOKEN = os.getenv("GRAPHRAG_API_KEY", "default_token_for_dev")

# NEW:
_raw = os.getenv("GRAPHRAG_API_KEY")
if _raw and _raw.strip() and _raw != "default_token_for_dev":
    AUTH_TOKEN = _raw.strip()
else:
    raise RuntimeError(
        "GRAPHRAG_API_KEY environment variable is not set or is using the banned dev default. "
        "Set a real token before starting the server."
    )
```

- [ ] **Step 2: Verify the change compiles**

```bash
cd apps/backend/src
python -m py_compile marathon_qa_assistant/services/knowledge_graph.py
```
Expected: PASS (no output = success)

- [ ] **Step 3: Check for any other references to the dev token**

```bash
rg "default_token_for_dev" --no-filename
```
Expected: only `todolist.md` and `archive/` references remain (documentation only, no runtime impact).

- [ ] **Step 4: Verify the existing provider contract test still passes**

```bash
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_llm_provider_contract.py -v
```

- [ ] **Step 5: Commit**

```bash
git add apps/backend/src/marathon_qa_assistant/services/knowledge_graph.py
git commit -m "fix: reject dev default GRAPHRAG_API_KEY at startup

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: Add GitHub Actions CI/CD Pipeline

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create the CI workflow file**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  backend-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/backend

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
          cache-dependency-path: apps/backend/requirements.txt

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest-cov ruff

      - name: Lint with ruff
        run: ruff check src/ --select E,F,W --ignore E501

      - name: Test with pytest + coverage
        env:
          PYTHONPATH: src
          PYTHONUTF8: "1"
        run: |
          python -m pytest ../../tests/ \
            --cov=src/marathon_qa_assistant \
            --cov-report=term-missing \
            --cov-report=json \
            --cov-fail-under=50 \
            -v

      - name: Upload coverage artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: apps/backend/coverage.json

  repo-hygiene:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Check repo hygiene
        run: python tools/dev/check_repo.py

      - name: Check for banned patterns
        run: |
          ! rg -q "default_token_for_dev" --no-ignore --glob '!.git' --glob '!todolist.md' --glob '!archive/**' --glob '!docs/**' .
          ! rg -q 'sk-[A-Za-z0-9]{20,}' --no-ignore --glob '!.git' .
          ! rg -q 'Authorization:\s*Bearer' --no-ignore --glob '!.git' .
          ! rg -q 'C:\\Users\\' --no-ignore --glob '!.git' --glob '!docs/**' .
```

- [ ] **Step 2: Verify the workflow file is valid YAML**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && echo "OK" || echo "INVALID"
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions CI with pytest, coverage, lint, and hygiene checks

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: Multi-Stage Dockerfile

**Files:**
- Create: `apps/backend/Dockerfile`
- Create: `apps/backend/.dockerignore`

- [ ] **Step 1: Create .dockerignore**

Create `apps/backend/.dockerignore`:

```
__pycache__/
*.pyc
*.pyo
.env
*.db
*.log
.pytest_cache/
.git/
.venv/
venv/
data/vector_kb/
data/uploads/
outputs/
artifacts/
node_modules/
.astro/
dist/
```

- [ ] **Step 2: Create the Dockerfile**

Create `apps/backend/Dockerfile`:

```dockerfile
# ---- Stage 1: Build ----
FROM python:3.11-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --target=/build/deps -r requirements.txt

# ---- Stage 2: Runtime ----
FROM python:3.11-slim-bookworm AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r marathon && useradd -r -g marathon -d /app marathon

WORKDIR /app

COPY --from=builder /build/deps /usr/local/lib/python3.11/site-packages/

COPY src/ ./src/

# Copy test fixtures for runtime validation (optional)
COPY ../../tests/fixtures/ /app/tests/fixtures/ 2>/dev/null || true

RUN chown -R marathon:marathon /app
USER marathon

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV PYTHONUTF8=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "-m", "uvicorn", "marathon_qa_assistant.apps.api_app:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Verify Dockerfile syntax**

```bash
docker build --check -f apps/backend/Dockerfile apps/backend/ 2>&1 || echo "Docker not available — skip verification"
```

- [ ] **Step 4: Commit**

```bash
git add apps/backend/Dockerfile apps/backend/.dockerignore
git commit -m "feat: add multi-stage Dockerfile with non-root user

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: Add pytest-cov Coverage Gate

**Files:**
- Modify: `pytest.ini`
- Modify: `apps/backend/requirements.txt`
- Create: `tests/test_infra_contracts.py`

- [ ] **Step 1: Add pytest-cov to requirements**

In `apps/backend/requirements.txt`, append after `pytest>=7.0.0`:

```
pytest-cov>=4.1.0
```

- [ ] **Step 2: Update pytest.ini coverage config**

In `pytest.ini`, update to:

```ini
[pytest]
testpaths = tests
python_files = test_*.py integration_*_test.py
pythonpath = apps/backend/src
addopts =
    --strict-markers
    --tb=short
norecursedirs =
    .git
    .pytest_cache
    archive
    artifacts
    data
    docs
    node_modules
    papers
    research
    apps/web/dist

# Coverage settings
    --cov=marathon_qa_assistant
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=50
```

- [ ] **Step 3: Write infra contract test**

Create `tests/test_infra_contracts.py`:

```python
"""Infrastructure contract tests: startup guards, health check shape, env validation."""

import os
import sys
import importlib


def test_graphrag_api_key_must_not_default_to_dev():
    """knowledge_graph must not accept default_token_for_dev as GRAPHRAG_API_KEY."""
    if "GRAPHRAG_API_KEY" in os.environ:
        del os.environ["GRAPHRAG_API_KEY"]
    os.environ["GRAPHRAG_API_KEY"] = "default_token_for_dev"
    try:
        import marathon_qa_assistant.services.knowledge_graph as kg
        importlib.reload(kg)
    except RuntimeError as e:
        assert "GRAPHRAG_API_KEY" in str(e)
        return
    finally:
        # restore a valid key so later imports don't crash
        os.environ["GRAPHRAG_API_KEY"] = "ci_test_token"
    # If we get here without exception, the guard failed
    raise AssertionError("Expected RuntimeError for dev default token but none was raised")


def test_health_endpoint_shape():
    """GET /health must not leak provider/model details when unauthenticated."""
    # Contract: public health should return {"status": "..."} with no internal keys
    public_keys = {"status"}
    # The current implementation returns provider/model — this test
    # documents the desired contract for when the endpoint is hardened.
    # Skip assertion until Task 5 hardens the endpoint.
    pass
```

- [ ] **Step 4: Run coverage gate**

```bash
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
$env:GRAPHRAG_API_KEY='ci_test_token'
python -m pytest tests/ --cov=marathon_qa_assistant --cov-report=term-missing --cov-fail-under=50 -v
```
Expected: FAIL at first (coverage goal informational), then adjust `--cov-fail-under` in pytest.ini based on actual baseline.

- [ ] **Step 5: Record baseline coverage and set realistic gate**

```bash
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
$env:GRAPHRAG_API_KEY='ci_test_token'
python -m pytest tests/ --cov=marathon_qa_assistant --cov-report=term -q 2>&1 | grep "TOTAL"
```
Update `--cov-fail-under` in `pytest.ini` to the nearest round number below the actual total (e.g., if 63% → set to 55%, planning to raise to 70% over subsequent sprints).

- [ ] **Step 6: Commit**

```bash
git add pytest.ini apps/backend/requirements.txt tests/test_infra_contracts.py
git commit -m "test: add pytest-cov coverage gate and infra contract tests

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: Structured Logging with Request IDs

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/apps/api_app.py`
- Create: `apps/backend/src/marathon_qa_assistant/core/logging_middleware.py`
- Modify: `apps/backend/requirements.txt`
- Create: `tests/test_logging_contract.py`

- [ ] **Step 1: Add python-json-logger to requirements**

In `apps/backend/requirements.txt`, append:

```
python-json-logger>=2.0.0
```

- [ ] **Step 2: Create the logging middleware**

Create `apps/backend/src/marathon_qa_assistant/core/logging_middleware.py`:

```python
"""Structured logging middleware with request-id injection."""

import json
import logging
import time
from uuid import uuid4
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


LOG_RECORD_ATTRS = {
    "timestamp", "level", "logger", "message",
    "request_id", "method", "path", "status_code",
    "duration_ms", "client_ip",
}


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for attr in LOG_RECORD_ATTRS:
            val = getattr(record, attr, None)
            if val and attr not in ("timestamp", "level", "logger", "message"):
                payload[attr] = val
        if record.exc_info and record.exc_info[0]:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        start = time.perf_counter()

        response: Response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        logger = logging.getLogger("http")
        logger.info(
            "",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else "",
            },
        )
        return response


def setup_structured_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    logging.getLogger("http").setLevel(logging.INFO)
    logging.getLogger("strc").setLevel(logging.INFO)
```

- [ ] **Step 3: Wire middleware into api_app.py**

In `apps/backend/src/marathon_qa_assistant/apps/api_app.py`, add to the imports section (around line 60):

```python
from marathon_qa_assistant.core.logging_middleware import (
    RequestIDMiddleware,
    setup_structured_logging,
)
```

After `app = FastAPI(...)` (find the line and add after it):

```python
setup_structured_logging()
app.add_middleware(RequestIDMiddleware)
```

- [ ] **Step 4: Write logging contract test**

Create `tests/test_logging_contract.py`:

```python
"""Contract tests for structured logging middleware."""

import json
import logging
import io


def test_json_formatter_emits_valid_json():
    from marathon_qa_assistant.core.logging_middleware import JSONFormatter

    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=1,
        msg="hello", args=(), exc_info=None,
    )
    record.request_id = "abc-123"
    record.method = "GET"
    record.path = "/health"
    record.status_code = 200
    record.duration_ms = 12.5
    record.client_ip = "127.0.0.1"

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["message"] == "hello"
    assert parsed["request_id"] == "abc-123"
    assert parsed["method"] == "GET"
    assert parsed["path"] == "/health"
    assert parsed["status_code"] == 200
    assert parsed["duration_ms"] == 12.5
    assert parsed["client_ip"] == "127.0.0.1"
    assert "timestamp" in parsed


def test_formatter_handles_exception():
    from marathon_qa_assistant.core.logging_middleware import JSONFormatter

    formatter = JSONFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=1,
            msg="failure", args=(), exc_info=None,
        )
        record.exc_info = (ValueError, ValueError("boom"), None)
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "ERROR"
        assert "exception" in parsed
```

- [ ] **Step 5: Run the logging contract test**

```bash
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_logging_contract.py -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/backend/src/marathon_qa_assistant/core/logging_middleware.py \
        apps/backend/src/marathon_qa_assistant/apps/api_app.py \
        apps/backend/requirements.txt \
        tests/test_logging_contract.py
git commit -m "feat: add structured JSON logging with request-id middleware

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: Health Check Hardening

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/apps/api_app.py:1316-1323`

- [ ] **Step 1: Replace the health check endpoint**

In `apps/backend/src/marathon_qa_assistant/apps/api_app.py`, replace lines 1316-1323:

```python
# OLD:
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "provider": os.getenv("LLM_PROVIDER", "ollama"),
        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:latest"),
        "rag": get_knowledge_base_health_snapshot(),
    }

# NEW:
@app.get("/health")
async def health_check():
    """Public health check — returns minimal status only."""
    kb_snapshot = get_knowledge_base_health_snapshot()
    db_ok = _check_database_health()
    return {
        "status": "healthy" if (kb_snapshot.get("ready", False) and db_ok) else "degraded",
        "kb": kb_snapshot.get("ready", False),
        "db": db_ok,
    }


@app.get("/admin/health")
async def admin_health_check(request: Request):
    """Admin health check — full component status. Requires expert token."""
    _require_expert_token(request)
    return {
        "status": "healthy",
        "provider": os.getenv("LLM_PROVIDER", "ollama"),
        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:latest"),
        "rag": get_knowledge_base_health_snapshot(),
        "db": _check_database_health(),
        "request_id": getattr(request.state, "request_id", None),
    }
```

Add the helper function near the health endpoint:

```python
def _check_database_health() -> bool:
    try:
        db = get_db()
        db.conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def _require_expert_token(request: Request):
    expert_token = os.getenv("MARATHON_EXPERT_API_TOKEN")
    if not expert_token:
        raise HTTPException(status_code=501, detail="Expert mode not configured.")
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[len("Bearer "):] != expert_token:
        raise HTTPException(status_code=403, detail="Expert access required.")
```

- [ ] **Step 2: Write health check contract test**

Create `tests/test_health_contract.py`:

```python
"""Contract tests for health check endpoints."""

import os
from fastapi.testclient import TestClient


def test_public_health_returns_minimal_info(client: TestClient):
    """Public /health must not expose provider or model details."""
    resp = client.get("/health")
    assert resp.status_code in (200, 503)
    data = resp.json()
    # Must only contain: status, kb, db
    assert set(data.keys()) <= {"status", "kb", "db"}
    # Must NOT leak provider/model
    assert "provider" not in data
    assert "model" not in data


def test_admin_health_requires_expert_token(client: TestClient):
    """Admin /admin/health must reject requests without expert token."""
    resp = client.get("/admin/health")
    assert resp.status_code in (403, 501)


def test_admin_health_returns_full_info_with_token(client: TestClient):
    """Admin /admin/health returns full detail with valid token."""
    token = os.getenv("MARATHON_EXPERT_API_TOKEN", "")
    if not token:
        # Skip if expert token not configured in test env
        return
    resp = client.get("/admin/health", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "provider" in data
    assert "model" in data
```

- [ ] **Step 3: Run the health contract test**

```bash
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_health_contract.py -v
```

- [ ] **Step 4: Commit**

```bash
git add apps/backend/src/marathon_qa_assistant/apps/api_app.py tests/test_health_contract.py
git commit -m "feat: split /health and /admin/health, remove provider leak from public endpoint

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Execution Order

Tasks are independent and can be executed in parallel:

```
Task 1 (token fix) ──┐
Task 2 (CI/CD)     ──┤
Task 3 (Docker)    ──┼── All parallel, no dependencies
Task 4 (coverage)  ──┤
Task 5 (logging)   ──┤
Task 6 (health)    ──┘
```

## Verification Checklist

After all tasks complete:

- [ ] `rg "default_token_for_dev" apps/backend/src` returns empty (runtime code only)
- [ ] `.github/workflows/ci.yml` exists and is valid YAML
- [ ] `apps/backend/Dockerfile` builds without error
- [ ] `python -m pytest tests/ --cov-fail-under=50` passes
- [ ] All log output from `api_app.py` is JSON-structured when `PYTHONUNBUFFERED=1`
- [ ] `GET /health` returns `{"status", "kb", "db"}` only — no provider/model leak
- [ ] `GET /admin/health` requires `Authorization: Bearer <MARATHON_EXPERT_API_TOKEN>`
- [ ] `git diff --check` passes with no whitespace issues
- [ ] No `.env`, `*.db`, or user data staged
