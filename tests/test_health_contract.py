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


def test_admin_health_requires_token(client: TestClient):
    """Admin /admin/health must reject requests without expert token."""
    resp = client.get("/admin/health")
    assert resp.status_code in (403, 501)


def test_admin_health_returns_full_info_with_token(client: TestClient):
    """Admin /admin/health returns full detail with valid token."""
    token = os.getenv("MARATHON_EXPERT_API_TOKEN", "")
    if not token:
        return  # Skip if expert token not configured in test env
    resp = client.get("/admin/health", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "provider" in data
    assert "model" in data
