from fastapi.testclient import TestClient

from marathon_qa_assistant.apps import api_app


client = TestClient(api_app.app)


class _FakeIntegratedApp:
    def __init__(self, result=None, error=None):
        self.calls = []
        self.result = result
        self.error = error

    async def ainvoke(self, initial_state, config=None):
        self.calls.append({"initial_state": initial_state, "config": config})
        if self.error:
            raise self.error
        if self.result is not None:
            return self.result
        return {
            "final_report": "测试报告",
            "structured_report": {
                "summary": "ok",
                "training_explanation_panel": {
                    "panel_version": "v2",
                    "coverage_status": "full",
                    "weeks": [],
                },
            },
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
    fake_app = _FakeIntegratedApp()
    monkeypatch.setattr(api_app, "integrated_app", fake_app)
    monkeypatch.setattr(api_app, "load_user_profile", lambda: {"goal": "维持健康"})
    monkeypatch.setattr(api_app, "ensure_knowledge_base_ready", lambda: False)

    response = client.post(
        "/query",
        json={
            "query": "帮我分析乳酸阈训练",
            "user_id": "default_user",
            "llm_provider": "deepseek",
            "llm_model": "deepseek-test",
            "ds_api_key": "sk-test",
            "timeout_sec": 12,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["report"] == "测试报告"
    assert payload["audit_scores"]["summary"] == "通过"
    assert payload["training_explanation_panel"] == {
        "panel_version": "v2",
        "coverage_status": "full",
        "weeks": [],
    }
    assert payload["structured_report"]["training_explanation_panel"] == payload["training_explanation_panel"]
    assert payload["llm_provider"] == "ds"
    assert payload["llm_model"] == "deepseek-test"
    assert fake_app.calls[0]["config"] == {
        "configurable": {
            "llm_provider": "ds",
            "llm_model": "deepseek-test",
            "ds_api_key": "sk-test",
            "llm_timeout_sec": 12,
        }
    }


def test_plan_query_skeleton_mode_returns_without_integrated_app(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    fake_app = _FakeIntegratedApp(error=AssertionError("skeleton mode should not call LLM workflow"))
    db = _Database(tmp_path / "plans.db")
    monkeypatch.setattr(api_app, "integrated_app", fake_app)
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    monkeypatch.setattr(
        api_app,
        "load_user_profile",
        lambda: {
            "goal": "半马 PB 1小时45分",
            "weekly_mileage": 35,
            "target_pace": "半马 1:45",
            "t_pace": "3:15/km",
        },
    )
    monkeypatch.setattr(api_app, "ensure_knowledge_base_ready", lambda: False)
    monkeypatch.setattr(
        api_app,
        "get_knowledge_base_health_snapshot",
        lambda: {"ok": True, "ready": True, "chunks_count": 1160, "faiss_ready": True, "source": "test"},
    )

    response = client.post(
        "/query",
        json={
            "query": "请给我生成 4 周半马训练计划",
            "user_id": "default_user",
            "response_mode": "skeleton",
            "llm_provider": "ollama",
            "timeout_sec": 15,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["generation_status"] == "skeleton_ready"
    assert payload["structured_training_plan"]["week_plans"]
    assert payload["structured_report"] is None
    assert payload["monthly_training_calendar"]["days"]
    assert payload["daily_schedule_cards"]
    hmp_cards = [card for card in payload["daily_schedule_cards"] if str(card.get("workout_type", "")).startswith("hm_")]
    assert hmp_cards
    assert hmp_cards[0]["evidence_tier"] == "protocol_rule"
    assert hmp_cards[0]["training_objective"]
    assert hmp_cards[0]["source"]
    assert payload["half_marathon_protocol_validation"]["active"] is True
    main_sets = [
        day["main_set"]
        for week in payload["structured_training_plan"]["week_plans"]
        for day in week["days"]
    ]
    assert all(not text.startswith("hm_") for text in main_sets)
    assert not any("3:15/km" in text or "3:20/km" in text for text in main_sets)
    assert payload["generation_timings"]["total_sec"] >= 0
    assert payload["training_plan_id"]
    assert db.get_plan(payload["training_plan_id"]) is not None
    assert fake_app.calls == []


def test_skeleton_plan_respects_explicit_profile_prompt_weeks_over_stale_profile(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    db = _Database(tmp_path / "plans.db")
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    monkeypatch.setattr(
        api_app,
        "load_user_profile",
        lambda: {
            "goal": "旧画像：半马破 120",
            "weekly_mileage": 70,
            "plan_duration_weeks": 4,
        },
    )
    monkeypatch.setattr(api_app, "ensure_knowledge_base_ready", lambda: False)
    monkeypatch.setattr(
        api_app,
        "get_knowledge_base_health_snapshot",
        lambda: {"ok": True, "ready": True, "chunks_count": 1160, "faiss_ready": True, "source": "test"},
    )

    response = client.post(
        "/query",
        json={
            "query": "请基于以下跑者画像生成训练计划：\n- 目标：半马 72 想破 70\n- 计划周期：12\n- 近4周平均周跑量：110 km",
            "user_id": "default_user",
            "response_mode": "skeleton",
            "llm_provider": "ollama",
            "timeout_sec": 15,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    meta = payload["structured_training_plan"]["plan_meta"]
    assert meta["requested_weeks"] == 12
    assert meta["actual_weeks"] == 12
    assert len(payload["structured_training_plan"]["week_plans"]) == 12


def test_english_skeleton_query_accepts_unit_profile_and_keeps_12_weeks(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    fake_app = _FakeIntegratedApp(error=AssertionError("english plan query should use skeleton path"))
    db = _Database(tmp_path / "plans.db")
    monkeypatch.setattr(api_app, "integrated_app", fake_app)
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    monkeypatch.setattr(
        api_app,
        "load_user_profile",
        lambda: {
            "goal": "Half marathon PB 71 min, target sub 69",
            "weekly_mileage": "105 km",
            "recent_four_week_mileage": "100 km",
            "max_session_minutes": "120 min",
            "plan_duration_weeks": "12 weeks",
            "target_race_date": "2026-06-08",
            "current_half_time": "1:11:00",
            "target_half_time": "1:08:59",
            "available_days": "周一 周二 周四 周六 周日",
        },
    )
    monkeypatch.setattr(api_app, "ensure_knowledge_base_ready", lambda: False)
    monkeypatch.setattr(
        api_app,
        "get_knowledge_base_health_snapshot",
        lambda: {"ok": True, "ready": True, "chunks_count": 1160, "faiss_ready": True, "source": "test"},
    )

    response = client.post(
        "/query",
        json={
            "query": "Generate a 12 week half marathon race prep plan for sub 69.",
            "user_id": "default_user",
            "response_mode": "skeleton",
            "llm_provider": "ollama",
            "timeout_sec": 15,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["generation_status"] == "skeleton_ready"
    assert payload["structured_training_plan"]["plan_meta"]["actual_weeks"] == 12
    assert len(payload["structured_training_plan"]["week_plans"]) == 12
    assert payload["monthly_training_calendar"]["total_days"] == 84
    assert fake_app.calls == []


def test_saved_skeleton_plan_keeps_action_library_trace(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    db = _Database(tmp_path / "plans.db")
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    monkeypatch.setattr(
        api_app,
        "load_user_profile",
        lambda: {
            "goal": "Half marathon PB 72 min, target sub 70",
            "weekly_mileage": "120",
            "recent_four_week_mileage": "110",
            "plan_duration_weeks": "4",
            "target_race_date": "2026-08-02",
            "current_half_time": "1:12:00",
            "target_pace": "1:09:59",
        },
    )
    monkeypatch.setattr(api_app, "ensure_knowledge_base_ready", lambda: False)
    monkeypatch.setattr(
        api_app,
        "get_knowledge_base_health_snapshot",
        lambda: {"ok": True, "ready": True, "chunks_count": 1160, "faiss_ready": True, "source": "test"},
    )

    response = client.post(
        "/query",
        json={
            "query": "请生成 4 周半马训练计划，目标破 70。",
            "user_id": "default_user",
            "response_mode": "skeleton",
            "llm_provider": "ollama",
            "timeout_sec": 15,
        },
    )

    assert response.status_code == 200
    plan_id = response.json()["training_plan_id"]
    detail = client.get(f"/plans/{plan_id}")

    assert detail.status_code == 200
    events = detail.json()["events"]
    action_events = [
        event for event in events
        if (event.get("field_sources") or {}).get("main_set", {}).get("source_type") == "action_library"
    ]
    assert action_events
    first = action_events[0]
    assert first["action_match"]["source"] == "动作库.pdf"
    assert first["action_match"]["action_id"]
    assert first["trace"]["action_match"]["source"] == "动作库.pdf"
    assert "3×10分钟有氧阈值" not in first["main_set"]


def test_plan_query_full_timeout_falls_back_to_skeleton(tmp_path, monkeypatch):
    import asyncio

    from marathon_qa_assistant.services.database import _Database

    fake_app = _FakeIntegratedApp(error=asyncio.TimeoutError())
    db = _Database(tmp_path / "plans.db")
    monkeypatch.setattr(api_app, "integrated_app", fake_app)
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    monkeypatch.setattr(api_app, "load_user_profile", lambda: {"goal": "完成首马", "weekly_mileage": 25})
    monkeypatch.setattr(api_app, "ensure_knowledge_base_ready", lambda: False)
    monkeypatch.setattr(
        api_app,
        "get_knowledge_base_health_snapshot",
        lambda: {"ok": True, "ready": True, "chunks_count": 1160, "faiss_ready": True, "source": "test"},
    )

    response = client.post(
        "/query",
        json={
            "query": "帮我制定 6 周全马备赛训练计划",
            "user_id": "default_user",
            "response_mode": "full",
            "timeout_sec": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["generation_status"] == "llm_timeout_skeleton"
    assert payload["structured_training_plan"]["week_plans"]
    assert payload["training_plan_id"]
    assert fake_app.calls[0]["config"]["configurable"]["llm_timeout_sec"] == 5


def test_profile_get_and_post_support_frontend_bootstrap(monkeypatch):
    saved_profiles = []

    monkeypatch.setattr(
        api_app,
        "load_user_profile",
        lambda: {"goal": "维持健康", "weekly_mileage": 30},
    )
    monkeypatch.setattr(api_app, "save_user_profile", lambda profile: saved_profiles.append(profile.copy()))

    response = client.get("/profile")

    assert response.status_code == 200
    assert response.json()["profile"]["goal"] == "维持健康"

    response = client.post(
        "/profile",
        json={
            "user_id": "default_user",
            "profile": {"goal": "半马 PB", "weekly_mileage": "42"},
        },
    )

    assert response.status_code == 200
    assert response.json()["profile"]["goal"] == "半马 PB"
    assert saved_profiles[-1]["weekly_mileage"] == "42"


def test_llm_options_support_frontend_model_controls(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:latest")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-pro")

    response = client.get("/llm-options")

    assert response.status_code == 200
    payload = response.json()
    assert payload["default"]["provider"] == "ollama"
    assert [item["id"] for item in payload["providers"]] == ["ollama", "ds"]


def test_plan_history_endpoints_support_frontend_persistence(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    db = _Database(tmp_path / "plans.db")
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    plan = {
        "plan_meta": {
            "goal": "半马 PB",
            "requested_weeks": 1,
            "actual_weeks": 1,
            "plan_type": "single_week",
        },
        "week_plans": [
            {
                "week_index": 1,
                "phase": "base",
                "load_level": "easy",
                "days": [
                    {"day": "周一", "training_type": "轻松跑", "main_set": "30 分钟 Z2"},
                ],
            }
        ],
    }

    response = client.get("/plans")
    assert response.status_code == 200
    assert response.json()["plans"] == []

    response = client.post(
        "/plans",
        json={
            "user_id": "default_user",
            "source_query": "生成1周计划",
            "structured_training_plan": plan,
        },
    )
    assert response.status_code == 200
    plan_id = response.json()["plan_id"]

    response = client.get("/plans")
    assert response.status_code == 200
    assert response.json()["plans"][0]["id"] == plan_id

    response = client.get(f"/plans/{plan_id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["structured_training_plan"]["plan_meta"]["goal"] == "半马 PB"
    assert detail["events"][0]["plan_id"] == plan_id


def test_feedback_endpoint_returns_adaptive_adjustment():
    response = client.post(
        "/feedback",
        json={
            "user_id": "default_user",
            "raw_text": "训练完成，但疲劳明显，膝盖有疼痛风险。",
            "feedback": {
                "completion": "已完成",
                "fatigue": "明显",
                "pain": "疼痛风险",
                "sleep": "一般",
                "notes": "希望降低下一次训练负荷。",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workout_feedback"]["pain_status"] == "risk"
    assert payload["risk_gate"]["status"] == "needs_protocol_recheck"
    assert payload["risk_gate"]["adjustment_action"] == "deescalate_or_refuse"
    assert payload["protocol_recheck"]["allowed"] is True
    assert payload["adaptive_adjustment"]["adjustment_required"] is True
    assert "pain_risk" in payload["adaptive_adjustment"]["reason_codes"]
    assert payload["adaptive_adjustment"]["adjustment_action"] == "deescalate_or_refuse"
    assert payload["plan_diff"]["workflow"] == ["risk_gate", "protocol_recheck", "adjustment", "plan_diff"]
    assert payload["plan_diff"]["downgraded"] >= 1
    assert "pain_risk" in payload["plan_diff"]["reason_codes"]


def test_feedback_endpoint_medical_risk_refuses_adjustment():
    response = client.post(
        "/feedback",
        json={
            "user_id": "default_user",
            "raw_text": "今天跑步时出现胸痛和头晕，还有中暑迹象。",
            "feedback": {
                "completion_status": "partial",
                "subjective_fatigue": "high",
                "pain_status": "risk",
                "sleep_quality": "poor",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_gate"]["status"] == "blocked"
    assert payload["risk_gate"]["product_status"] == "medical_referral"
    assert payload["risk_gate"]["adjustment_action"] == "deescalate_or_refuse"
    assert payload["protocol_recheck"]["allowed"] is False
    assert payload["generation_status"] == "medical_referral"
    assert payload["plan_diff"]["cancelled"] >= 1
    assert payload["plan_diff"]["workflow"] == ["risk_gate", "protocol_recheck", "adjustment", "plan_diff"]


def test_delete_plan_removes_plan_and_events(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    db = _Database(tmp_path / "plans.db")
    monkeypatch.setattr(api_app, "get_db", lambda: db)

    plan_id = db.save_training_plan(
        {
            "plan_meta": {
                "goal": "delete me",
                "requested_weeks": 1,
                "actual_weeks": 1,
                "plan_type": "single_week",
            },
            "week_plans": [
                {
                    "week_index": 1,
                    "phase": "base",
                    "load_level": "easy",
                    "days": [
                        {"day": "Mon", "training_type": "easy", "main_set": "30 min Z2"},
                    ],
                }
            ],
        },
        source_query="test delete",
    )

    response = client.delete(f"/plans/{plan_id}")

    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert db.get_plan(plan_id) is None
    assert db.list_events(plan_id) == []

    response = client.delete(f"/plans/{plan_id}")
    assert response.status_code == 404
