from fastapi.testclient import TestClient

from marathon_qa_assistant.apps import api_app


client = TestClient(api_app.app)


def test_request_id_is_echoed_on_health_response():
    response = client.get("/health", headers={"X-Request-ID": "req-test-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-test-123"


def test_ops_metrics_tracks_requests_and_generation_statuses():
    before = client.get("/ops/metrics").json()

    response = client.get("/health", headers={"X-Request-ID": "metrics-health"})
    assert response.status_code == 200

    after = client.get("/ops/metrics").json()

    assert after["requests_total"] >= before["requests_total"] + 1
    assert "errors_total" in after
    assert "generation_status_counts" in after
    assert "feedback_risk_reason_counts" in after
    assert "llm_provider_error_counts" in after
    assert "plan_generation_duration_buckets" in after
    assert "request_route_counts" in after


def test_ops_metrics_uses_route_templates_for_dynamic_paths():
    missing_plan_id = "plan-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    response = client.get(f"/plans/{missing_plan_id}", headers={"X-Request-ID": "metrics-route-template"})
    assert response.status_code == 404

    metrics = client.get("/ops/metrics").json()
    route_counts = metrics["request_route_counts"]
    assert "GET /plans/{plan_id}" in route_counts
    assert all(missing_plan_id not in route for route in route_counts)


def test_ops_metrics_collapses_unknown_routes_without_leaking_segments():
    raw_segment = "sk-secret-user-query-with-many-words"

    response = client.get(f"/unknown/{raw_segment}", headers={"X-Request-ID": "metrics-unknown-route"})
    assert response.status_code == 404

    metrics = client.get("/ops/metrics").json()
    route_counts = metrics["request_route_counts"]
    assert "GET /__unmatched__" in route_counts
    assert all(raw_segment not in route for route in route_counts)


def test_feedback_updates_observability_risk_metrics():
    before = client.get("/ops/metrics").json()["medical_referral_total"]

    response = client.post(
        "/feedback",
        json={
            "raw_text": "胸痛并头晕，停止训练",
            "feedback": {
                "completion_status": "skipped",
                "pain_status": "chest_pain",
                "subjective_fatigue": "high",
            },
        },
        headers={"X-Request-ID": "metrics-feedback"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "metrics-feedback"
    assert response.json()["generation_status"] == "medical_referral"
    after = client.get("/ops/metrics").json()
    assert after["medical_referral_total"] >= before + 1
    assert after["generation_status_counts"]["medical_referral"] >= 1
