"""Contract tests for health check endpoints."""

import json
import os
from fastapi.testclient import TestClient


def test_public_health_returns_minimal_info(client: TestClient):
    """Public /health must not expose provider or model details."""
    resp = client.get("/health")
    assert resp.status_code in (200, 503)
    data = resp.json()
    # Must only contain: status, kb, db, ollama
    assert set(data.keys()) <= {"status", "kb", "db", "ollama"}
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


def test_admin_kb_governance_requires_token(client: TestClient):
    resp = client.get("/admin/kb-governance")

    assert resp.status_code in (403, 501)


def test_admin_kb_governance_returns_release_gate_summary(client: TestClient, monkeypatch, tmp_path):
    governance_dir = tmp_path / "knowledge" / "governance"
    governance_dir.mkdir(parents=True)
    (governance_dir / "kb_release_report.json").write_text(
        json.dumps(
            {
                "commercial_release_ready": False,
                "readiness_blockers": ["all_domain_packs_still_have_gaps"],
                "domain_gap_summary": {"domain_packs_with_source_deficits": 11},
                "actionable_domain_gaps": [
                    {
                        "domain_pack": "user_profile_cases",
                        "needed_source_count": 100,
                        "next_action": "collect_privacy_reviewed_user_profile_cases",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (governance_dir / "source_gap_report.json").write_text(
        json.dumps(
            {
                "release_work_queue": [
                    {
                        "domain_pack": "user_profile_cases",
                        "needed_source_count": 100,
                        "required_quality_tier": "privacy_reviewed",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (governance_dir / "runtime_index_v2_manifest.json").write_text(
        json.dumps(
            {
                "status": "runtime_preview_ready",
                "can_replace_runtime": False,
                "first_batch_release_ready": False,
                "replacement_blockers": ["all_domain_packs_still_have_gaps"],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MARATHON_EXPERT_API_TOKEN", "expert-test-token")
    monkeypatch.setattr("marathon_qa_assistant.apps.api_app.DATA_DIR", tmp_path)

    resp = client.get("/admin/kb-governance", headers={"Authorization": "Bearer expert-test-token"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "blocked"
    assert data["runtime"]["can_replace_runtime"] is False
    assert data["release_gate"]["commercial_release_ready"] is False
    assert data["release_gate"]["readiness_blockers"] == ["all_domain_packs_still_have_gaps"]
    assert data["domain_gap_summary"]["domain_packs_with_source_deficits"] == 11
    assert data["top_actionable_domain_gaps"][0]["domain_pack"] == "user_profile_cases"
    assert data["release_work_queue"][0]["required_quality_tier"] == "privacy_reviewed"
    assert "C:/Users" not in str(data)
    assert "local_path" not in str(data)


def test_admin_kb_governance_reports_missing_artifacts(client: TestClient, monkeypatch, tmp_path):
    monkeypatch.setenv("MARATHON_EXPERT_API_TOKEN", "expert-test-token")
    monkeypatch.setattr("marathon_qa_assistant.apps.api_app.DATA_DIR", tmp_path)

    resp = client.get("/admin/kb-governance", headers={"Authorization": "Bearer expert-test-token"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "unavailable"
    assert set(data["artifacts"].values()) == {"missing"}


