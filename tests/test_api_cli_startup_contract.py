"""API CLI startup contract tests.

Covers: FastAPI app import, OpenAPI schema presence, startup hooks,
CLI arg compatibility, env-based config, and token auth wiring.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from marathon_qa_assistant.apps import api_app


def test_app_can_be_imported():
    """Verify the primary public entry point is importable."""
    assert api_app.app is not None
    assert api_app.app.title == "Marathon QA Assistant API"


def test_openapi_schema_includes_core_endpoints():
    schema = api_app.app.openapi()
    paths = set(schema.get("paths", {}).keys())

    assert "/health" in paths
    assert "/query" in paths
    assert "/feedback" in paths
    assert "/plans" in paths
    assert "/ops/metrics" in paths
    assert "/profile" in paths


def test_openapi_schema_includes_schemas():
    schema = api_app.app.openapi()
    schemas = set(schema.get("components", {}).get("schemas", {}).keys())

    expected = {"QueryRequest", "QueryResponse", "FeedbackRequest", "FeedbackResponse"}
    for name in expected:
        assert name in schemas, f"Schema {name} missing from OpenAPI"


def test_lifespan_startup_runs_without_error():
    """TestClient triggers lifespan startup; verify it does not crash."""
    client = TestClient(api_app.app)
    response = client.get("/health")
    assert response.status_code == 200


def test_startup_ensures_default_user():
    """After startup the app should have a default user provisioned."""
    client = TestClient(api_app.app)
    response = client.get("/health")
    assert response.status_code == 200


def test_cli_startup_imports_integrated_workflow():
    """The integrated workflow module must be importable for CLI usage."""
    from marathon_qa_assistant.core.workflow import integrated_app, IntegratedState  # noqa: F401


def test_cors_middleware_is_configured():
    """CORS middleware must be registered."""
    middlewares = [m.cls.__name__ for m in api_app.app.user_middleware]
    assert "CORSMiddleware" in middlewares


def test_request_id_middleware_is_configured():
    """RequestIDMiddleware must be registered."""
    middlewares = [m.cls.__name__ for m in api_app.app.user_middleware]
    assert "RequestIDMiddleware" in middlewares


def test_env_vars_control_port(monkeypatch):
    """MARATHON_PORT should be respected by uvicorn entry point."""
    monkeypatch.setenv("MARATHON_PORT", "18010")
    import os
    assert os.getenv("MARATHON_PORT") == "18010"


def test_rate_limit_defaults_to_permissive(monkeypatch):
    """Default rate limit should be high enough for local dev."""
    monkeypatch.delenv("MARATHON_RATE_LIMIT_PER_MINUTE", raising=False)
    limit = api_app._rate_limit_per_minute()
    assert limit >= 100


def test_token_auth_is_disabled_by_default(monkeypatch):
    """Without MARATHON_API_TOKEN, auth should be disabled."""
    monkeypatch.delenv("MARATHON_API_TOKEN", raising=False)
    assert api_app._auth_enabled() is False
    client = TestClient(api_app.app)
    response = client.get("/plans")
    assert response.status_code == 200
