from fastapi.testclient import TestClient

from marathon_qa_assistant.apps import api_app


client = TestClient(api_app.app)


class _FakeIntegratedApp:
    async def ainvoke(self, initial_state):
        return {
            "final_report": "测试报告",
            "structured_report": {"summary": "ok"},
            "token_usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            "audit_scores": {"consistency": 85, "safety": 90, "roi": 60, "summary": "通过"},
            "guided_questions": ["后续问题"],
        }


def test_query_rejects_unsupported_user_id():
    response = client.post(
        "/query",
        json={"query": "帮我分析乳酸阈训练", "user_id": "alice"},
    )

    assert response.status_code == 400
    assert "仅支持单用户画像" in response.json()["detail"]


def test_query_accepts_audit_scores_with_summary(monkeypatch):
    monkeypatch.setattr(api_app, "integrated_app", _FakeIntegratedApp())
    monkeypatch.setattr(api_app, "load_user_profile", lambda: {"goal": "维持健康"})

    response = client.post(
        "/query",
        json={"query": "帮我分析乳酸阈训练", "user_id": "default_user"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["report"] == "测试报告"
    assert payload["audit_scores"]["summary"] == "通过"
