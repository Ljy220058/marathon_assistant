"""Core API app contract tests.

Covers: /health, /query, /feedback, /plans/{plan_id}, /ops/metrics,
request-id, CORS defaults, and structured response shape.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from marathon_qa_assistant.apps import api_app

client = TestClient(api_app.app)


# ---- Health endpoints ----

def test_health_returns_200_with_component_status():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "kb" in data
    assert "db" in data
    assert "ollama" in data
    assert data["status"] in ("healthy", "degraded")


def test_health_returns_x_request_id():
    response = client.get("/health", headers={"X-Request-ID": "health-rid"})
    assert response.headers["X-Request-ID"] == "health-rid"


# ---- /query skeleton-first ----

def test_query_returns_skeleton_plan():
    response = client.post(
        "/query",
        json={
            "query": "请生成 8 周半马训练计划，目标配速 5:30/km",
            "timeout_sec": 10,
        },
        headers={"X-Request-ID": "query-skeleton"},
    )
    assert response.status_code == 200
    data = response.json()
    assert response.headers["X-Request-ID"] == "query-skeleton"
    assert data["generation_status"] in ("skeleton", "complete", "partial", "llm_timeout_skeleton")
    assert "structured_training_plan" in data
    assert "monthly_training_calendar" in data
    assert "daily_schedule_cards" in data


# ---- /feedback ----

def test_feedback_accepts_minimal_payload():
    response = client.post(
        "/feedback",
        json={
            "raw_text": "今天轻松跑完成，感觉良好",
            "feedback": {
                "completion_status": "completed",
                "subjective_fatigue": "mild",
            },
        },
        headers={"X-Request-ID": "feedback-minimal"},
    )
    assert response.status_code == 200
    data = response.json()
    assert response.headers["X-Request-ID"] == "feedback-minimal"
    assert "risk_gate" in data
    assert "generation_status" in data


def test_feedback_rejects_partial_plan_event():
    response = client.post(
        "/feedback",
        json={
            "plan_id": "plan-missing-event",
            "raw_text": "测试",
            "feedback": {"completion_status": "completed"},
        },
        headers={"X-Request-ID": "feedback-partial"},
    )
    assert response.status_code == 400
    assert response.headers["X-Request-ID"] == "feedback-partial"


# ---- /plans/{plan_id} ----

def test_plan_detail_returns_structured_shape():
    # First create a plan via /query save
    resp = client.post(
        "/query",
        json={
            "query": "生成 2 周轻松跑计划",
            "timeout_sec": 10,
        },
        headers={"X-Request-ID": "plan-create"},
    )
    # Skeleton-first returns 504 on LLM timeout but may still save plan
    if resp.status_code not in (200, 504):
        resp.raise_for_status()
    plan_id = resp.json().get("training_plan_id")
    if plan_id:
        detail = client.get(
            f"/plans/{plan_id}",
            headers={"X-Request-ID": "plan-detail"},
        )
        assert detail.status_code == 200
        data = detail.json()
        assert "plan" in data
        assert "events" in data
        assert "execution_status_summary" in data
        assert "adjustment_history" in data
        assert detail.headers["X-Request-ID"] == "plan-detail"


def test_plan_list_returns_array():
    response = client.get("/plans", headers={"X-Request-ID": "plan-list"})
    assert response.status_code == 200
    data = response.json()
    assert "plans" in data
    assert isinstance(data["plans"], list)


# ---- /ops/metrics ----

def test_ops_metrics_returns_stable_shape():
    response = client.get("/ops/metrics", headers={"X-Request-ID": "ops-metrics"})
    assert response.status_code == 200
    data = response.json()
    assert "requests_total" in data
    assert "errors_total" in data
    assert "generation_status_counts" in data
    assert "feedback_risk_reason_counts" in data
    assert "llm_provider_error_counts" in data
    assert "plan_generation_duration_buckets" in data
    assert "medical_referral_total" in data


# ---- CORS origin defaults ----

def test_cors_defaults_are_restrictive(monkeypatch):
    monkeypatch.delenv("MARATHON_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("MARATHON_DEV_PERMISSIVE_CORS", raising=False)
    origins = api_app._allowed_cors_origins()
    assert "*" not in origins
    assert "http://127.0.0.1:4321" in origins
    assert "http://localhost:4321" in origins


def test_cors_env_var_takes_list(monkeypatch):
    monkeypatch.setenv("MARATHON_ALLOWED_ORIGINS", "http://custom1.example,http://custom2.example")
    monkeypatch.delenv("MARATHON_DEV_PERMISSIVE_CORS", raising=False)
    origins = api_app._allowed_cors_origins()
    assert "http://custom1.example" in origins
    assert "http://custom2.example" in origins
    assert "*" not in origins


# ---- Profile endpoints ----

def test_profile_get_returns_user_profile():
    response = client.get("/profile", headers={"X-Request-ID": "profile-get"})
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert "profile" in data


# ---- Profile save ----

def test_profile_save_updates_and_reflects():
    patch = {"goal": "半马 sub135", "weekly_mileage": "60"}
    save = client.post(
        "/profile",
        json={"profile": patch},
        headers={"X-Request-ID": "profile-save"},
    )
    assert save.status_code == 200
    saved = save.json()
    assert saved["profile"].get("goal") == patch["goal"]

    get_response = client.get("/profile", headers={"X-Request-ID": "profile-get-2"})
    assert get_response.status_code == 200
    assert get_response.json()["profile"].get("goal") == patch["goal"]


# ---- /llm-options ----

def test_llm_options_returns_providers():
    response = client.get("/llm-options")
    assert response.status_code == 200
    data = response.json()
    assert "default" in data
    assert "providers" in data


# ---- /zone-reference / evidence-tier-reference ----

def test_workout_template_reference_endpoints():
    zone_resp = client.get("/zone-reference")
    tier_resp = client.get("/evidence-tier-reference")

    assert zone_resp.status_code == 200
    assert tier_resp.status_code == 200
    assert "zones" in zone_resp.json() or "zones" in tier_resp.json() or "tiers" in tier_resp.json()


# ---- Request ID on all endpoints ----

@pytest.mark.parametrize("method,url,payload", [
    ("GET", "/health", None),
    ("POST", "/query", {"query": "测试", "timeout_sec": 5}),
    ("POST", "/feedback", {"raw_text": "测试", "feedback": {"completion_status": "completed"}}),
    ("GET", "/plans", None),
    ("GET", "/ops/metrics", None),
    ("GET", "/profile", None),
    ("GET", "/llm-options", None),
])
def test_all_public_endpoints_return_x_request_id(method, url, payload):
    headers = {"X-Request-ID": f"rid-{url.replace('/', '-').strip('-')}"}
    if method == "GET":
        response = client.get(url, headers=headers)
    else:
        response = client.post(url, json=payload, headers=headers)
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] == headers["X-Request-ID"]
