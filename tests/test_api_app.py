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


def _one_week_calendar_contract_plan():
    return {
        "plan_meta": {
            "goal": "半马 PB",
            "requested_weeks": 1,
            "actual_weeks": 1,
            "plan_type": "single_week",
        },
        "phase_summary": [
            {"phase": "基础期", "start_week": 1, "end_week": 1, "objective": "建立有氧基础"},
        ],
        "week_plans": [
            {
                "week_index": 1,
                "phase": "基础期",
                "load_level": "easy",
                "days": [
                    {"day": "周二", "training_type": "VO2max", "main_set": ""},
                ],
            }
        ],
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
    assert payload["workflow_trace"]["trace_version"] == "workflow_trace.v1"
    assert payload["workflow_trace"]["status"] == "complete"
    assert payload["structured_report"]["workflow_trace"]["run_id"] == payload["workflow_trace"]["run_id"]
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


def test_query_full_plan_backfills_calendar_contract_when_report_omits_it(monkeypatch):
    structured_plan = _one_week_calendar_contract_plan()
    fake_app = _FakeIntegratedApp(
        result={
            "final_report": "已生成训练计划。",
            "structured_training_plan": structured_plan,
            "structured_report": {"summary": "workflow report without calendar"},
            "workflow_trace": {
                "trace_version": "workflow_trace.v1",
                "run_id": "state-level-trace",
                "workflow_kind": "plan",
                "intent_type": "plan",
                "status": "complete",
            },
            "token_usage": {},
            "audit_scores": {"consistency": 90, "safety": 90, "roi": 70, "summary": "通过"},
            "guided_questions": [],
        }
    )
    monkeypatch.setattr(api_app, "integrated_app", fake_app)
    monkeypatch.setattr(api_app, "load_user_profile", lambda: {"goal": "半马 PB"})
    monkeypatch.setattr(api_app, "ensure_knowledge_base_ready", lambda: False)

    response = client.post(
        "/query",
        json={
            "query": "请给我生成 1 周半马训练计划",
            "user_id": "default_user",
            "response_mode": "full",
            "timeout_sec": 15,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    calendar = payload["monthly_training_calendar"]
    cards = payload["daily_schedule_cards"]
    assert calendar["days"]
    assert cards
    assert len(cards) == len(calendar["days"]) == calendar["total_days"]
    assert payload["phases"] == calendar["phases"]
    assert payload["training_load_summary"] == calendar["training_load_summary"]
    assert payload["structured_report"]["monthly_training_calendar"] == calendar
    assert payload["structured_report"]["daily_schedule_cards"] == cards
    assert payload["workflow_trace"]["run_id"] == "state-level-trace"
    assert payload["structured_report"]["workflow_trace"]["run_id"] == "state-level-trace"


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
    assert payload["workflow_trace"]["trace_version"] == "workflow_trace.v1"
    assert payload["workflow_trace"]["status"] == "skeleton_ready"
    assert payload["structured_training_plan"]["workflow_trace"]["run_id"] == payload["workflow_trace"]["run_id"]
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
    daily_card_main_sets = [str(card.get("main_set") or "") for card in payload["daily_schedule_cards"]]
    assert all(not text.startswith("hm_") for text in daily_card_main_sets)
    assert not any("3×2000m" in text or "3:15/km" in text or "3:20/km" in text for text in daily_card_main_sets)
    assert set(payload["generation_timings"]) >= {
        "skeleton_build_sec",
        "calendar_enrich_sec",
        "save_plan_sec",
        "total_sec",
    }
    assert all(isinstance(payload["generation_timings"][key], (int, float)) for key in payload["generation_timings"])
    assert payload["generation_timings"]["total_sec"] >= 0
    assert payload["training_plan_id"]
    assert payload["training_plan_review"]["review_version"] == "training_plan_review.v1"
    assert payload["training_plan_review"]["dimensions"]["training_load"]["source_type"] == "planned_load_proxy"
    assert payload["training_plan_review"]["dimensions"]["training_load"]["not_device_metric"] is True
    assert set(payload["training_plan_review"]["dimensions"]) >= {
        "training_load",
        "plan_structure",
        "periodization",
        "injury_recovery",
        "rehabilitation",
        "strength_conditioning",
        "mobility_recovery",
        "injury_prevention",
        "evidence_control",
        "rag_vs_base_model",
    }
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


def test_skeleton_plan_prompt_profile_fields_override_stale_profile_pollution(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    fake_app = _FakeIntegratedApp(error=AssertionError("skeleton mode should not call LLM workflow"))
    db = _Database(tmp_path / "plans.db")
    monkeypatch.setattr(api_app, "integrated_app", fake_app)
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    monkeypatch.setattr(
        api_app,
        "load_user_profile",
        lambda: {
            "goal": "旧画像：全马 3小时30分",
            "weekly_mileage": 20,
            "recent_four_week_mileage": 18,
            "available_days": "周一",
            "target_pace": "全马 3:30",
            "injury_or_fatigue": "膝盖疼痛",
            "plan_duration_weeks": 4,
            "target_race_date": "",
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
            "query": "\n".join(
                [
                    "请基于以下跑者画像生成训练计划：",
                    "- goal: 半马 PB 1小时25分，目标破 1小时20分",
                    "- target_race_date: 12周",
                    "- weekly_mileage: 90 km",
                    "- recent_four_week_mileage: 60 km",
                    "- available_days: 周二, 周三, 周五, 周日",
                    "- target_pace: 半马 1:20",
                    "- injury_or_fatigue: 无",
                ]
            ),
            "user_id": "default_user",
            "response_mode": "skeleton",
            "timeout_sec": 15,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    plan = payload["structured_training_plan"]
    meta = plan["plan_meta"]
    first_week_training_days = [
        day["day"]
        for day in plan["week_plans"][0]["days"]
        if day["training_type"] != "休息"
    ]
    hm_protocol = plan["half_marathon_protocol"]
    capacity_budget = hm_protocol["capacity_budget"]

    assert payload["generation_status"] == "skeleton_ready"
    assert meta["goal"].startswith("半马 PB")
    assert meta["target_race_date"] == "12周"
    assert meta["actual_weeks"] == 12
    assert set(first_week_training_days).issubset({"周二", "周三", "周五", "周日"})
    assert hm_protocol["active"] is True
    assert hm_protocol["input_weekly_mileage_km"] == 90.0
    assert hm_protocol["input_recent_four_week_mileage_km"] == 60.0
    assert capacity_budget["volume_basis"] == "recent_four_week_mileage"
    assert capacity_budget["quality_sessions_max"] == 2
    assert fake_app.calls == []


def test_skeleton_plan_accepts_unified_profile_contract_fields(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    fake_app = _FakeIntegratedApp(error=AssertionError("skeleton mode should not call LLM workflow"))
    db = _Database(tmp_path / "plans.db")
    monkeypatch.setattr(api_app, "integrated_app", fake_app)
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    monkeypatch.setattr(
        api_app,
        "load_user_profile",
        lambda: {
            "goal": "旧画像：半马完赛",
            "weekly_mileage": 25,
            "recent_four_week_mileage": 18,
            "available_days": "周一",
            "target_pace": "半马 1:55",
            "target_half_time": "1:55:00",
            "current_half_time": "2:00:00",
            "injury": "有",
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
            "query": "\n".join(
                [
                    "请基于以下跑者画像生成训练计划：",
                    "- goal: 半马 PB 1小时25分，目标破 1小时20分",
                    "- target_race_date: 12周",
                    "- weekly_mileage: 90 km",
                    "- last_month_mileage: 260 km",
                    "- available_days: 周二, 周三, 周五, 周日",
                    "- current_half_time: 1:25:00",
                    "- target_half_time: 1:20:00",
                    "- target_pace: 半马 1:20",
                    "- injury: none",
                    "- recovery_state: normal",
                ]
            ),
            "user_id": "default_user",
            "response_mode": "skeleton",
            "timeout_sec": 15,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    plan = payload["structured_training_plan"]
    calibration = plan["plan_meta"]["performance_calibration"]
    protocol = plan["half_marathon_protocol"]
    capacity_budget = protocol["capacity_budget"]

    assert payload["generation_status"] == "skeleton_ready"
    assert plan["plan_meta"]["actual_weeks"] == 12
    assert protocol["input_weekly_mileage_km"] == 90.0
    assert abs(protocol["input_recent_four_week_mileage_km"] - 59.8) < 0.1
    assert capacity_budget["quality_sessions_max"] == 2
    assert not any("疲劳或伤病风险" in note for note in capacity_budget["notes"])
    assert calibration["status"] == "ambitious_target"
    assert calibration["current_half_time_seconds"] == 5100
    assert calibration["target_half_time_seconds"] == 4800
    assert calibration["gap_seconds_per_km"] == 14
    assert calibration["time_gap_seconds"] == 300
    assert calibration["source_fields"] == ["current_half_time", "target_half_time"]
    assert fake_app.calls == []


def test_empty_skeleton_query_uses_existing_profile_for_plan_generation(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    fake_app = _FakeIntegratedApp(error=AssertionError("empty skeleton query should not call LLM workflow"))
    db = _Database(tmp_path / "plans.db")
    monkeypatch.setattr(api_app, "integrated_app", fake_app)
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    monkeypatch.setattr(
        api_app,
        "load_user_profile",
        lambda: {
            "goal": "半马 PB 1小时45分",
            "weekly_mileage": 35,
            "recent_four_week_mileage": 32,
            "available_days": "周二,周四,周日",
            "target_pace": "半马 1:45",
            "target_race_date": "1个月",
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
            "query": "",
            "user_id": "default_user",
            "response_mode": "skeleton",
            "timeout_sec": 15,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["generation_status"] == "skeleton_ready"
    assert payload["structured_training_plan"]["plan_meta"]["goal"] == "半马 PB 1小时45分"
    assert payload["structured_training_plan"]["plan_meta"]["target_race_date"] == "1个月"
    assert payload["structured_training_plan"]["plan_meta"]["actual_weeks"] == 4
    assert payload["monthly_training_calendar"]["total_days"] == 28
    assert payload["daily_schedule_cards"]
    assert payload["training_plan_id"]
    assert fake_app.calls == []


def test_empty_skeleton_query_with_single_goal_field_still_generates_plan(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    fake_app = _FakeIntegratedApp(error=AssertionError("empty skeleton query should not call LLM workflow"))
    db = _Database(tmp_path / "plans.db")
    monkeypatch.setattr(api_app, "integrated_app", fake_app)
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    monkeypatch.setattr(api_app, "load_user_profile", lambda: {"goal": "完成首马"})
    monkeypatch.setattr(api_app, "ensure_knowledge_base_ready", lambda: False)
    monkeypatch.setattr(
        api_app,
        "get_knowledge_base_health_snapshot",
        lambda: {"ok": True, "ready": True, "chunks_count": 1160, "faiss_ready": True, "source": "test"},
    )

    response = client.post(
        "/query",
        json={
            "query": "",
            "user_id": "default_user",
            "response_mode": "skeleton",
            "timeout_sec": 15,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["generation_status"] == "skeleton_ready"
    assert payload["structured_training_plan"]["plan_meta"]["goal"] == "完成首马"
    assert payload["monthly_training_calendar"]["days"]
    assert payload["daily_schedule_cards"]
    assert fake_app.calls == []


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


def test_plan_query_full_error_falls_back_to_error_skeleton(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    fake_app = _FakeIntegratedApp(error=RuntimeError("model provider failed"))
    db = _Database(tmp_path / "plans.db")
    monkeypatch.setattr(api_app, "integrated_app", fake_app)
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    monkeypatch.setattr(api_app, "load_user_profile", lambda: {"goal": "半马完赛", "weekly_mileage": 28})
    monkeypatch.setattr(api_app, "ensure_knowledge_base_ready", lambda: False)
    monkeypatch.setattr(
        api_app,
        "get_knowledge_base_health_snapshot",
        lambda: {"ok": True, "ready": True, "chunks_count": 1160, "faiss_ready": True, "source": "test"},
    )

    response = client.post(
        "/query",
        json={
            "query": "帮我制定 8 周半马训练计划",
            "user_id": "default_user",
            "response_mode": "full",
            "timeout_sec": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["generation_status"] == "llm_error_skeleton"
    assert payload["message"].startswith("完整 LLM 工作流异常")
    assert "model provider failed" not in payload["message"]
    assert payload["message"] != "完整工作流已返回。"
    assert payload["monthly_training_calendar"]["days"]
    assert payload["daily_schedule_cards"]
    assert payload["training_plan_id"]


def test_plan_query_provider_error_message_does_not_leak_raw_details(tmp_path, monkeypatch):
    from marathon_qa_assistant.nodes.common import LLMProviderError
    from marathon_qa_assistant.services.database import _Database

    fake_app = _FakeIntegratedApp(
        error=LLMProviderError(
            provider="openai",
            error_code="rate_limited",
            status_code=429,
            message="OpenAI 原始错误体 sk-secret should not leak",
        )
    )
    db = _Database(tmp_path / "plans.db")
    monkeypatch.setattr(api_app, "integrated_app", fake_app)
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    monkeypatch.setattr(api_app, "load_user_profile", lambda: {"goal": "半马完赛", "weekly_mileage": 28})
    monkeypatch.setattr(api_app, "ensure_knowledge_base_ready", lambda: False)

    response = client.post(
        "/query",
        json={
            "query": "帮我制定 8 周半马训练计划",
            "user_id": "default_user",
            "response_mode": "full",
            "timeout_sec": 5,
            "llm_provider": "openai",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["generation_status"] == "llm_error_skeleton"
    assert "openai/rate_limited" in payload["message"]
    assert "sk-secret" not in payload["message"]
    assert "原始错误体" not in payload["message"]


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


def test_profile_user_endpoints_patch_zones_and_nlu_preview(monkeypatch):
    stored_profile = {"goal": "维持健康", "weekly_mileage": 30, "lthr": 0, "t_pace": ""}
    saved_profiles = []

    def fake_load():
        return stored_profile.copy()

    def fake_save(profile):
        stored_profile.clear()
        stored_profile.update(profile)
        saved_profiles.append(profile.copy())

    monkeypatch.setattr(api_app, "load_user_profile", fake_load)
    monkeypatch.setattr(api_app, "save_user_profile", fake_save)

    response = client.get("/profile/default_user")
    assert response.status_code == 200
    assert response.json()["profile"]["goal"] == "维持健康"

    response = client.patch(
        "/profile/default_user/fields/lthr",
        json={"value": "168"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"]["lthr"] == "168"
    assert len(payload["profile"]["hr_zones"]) == 9
    assert saved_profiles[-1]["lthr"] == "168"

    response = client.get("/profile/default_user/zones")
    assert response.status_code == 200
    assert len(response.json()["hr_zones"]) == 9

    response = client.post(
        "/profile/default_user/nlu-extract",
        json={"text": "我最近周跑量提升到 50km，目标半马 sub90。"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["requires_confirmation"] is True
    assert payload["suggested_changes"]["weekly_mileage"] == "50"
    assert stored_profile["weekly_mileage"] == 30


def test_llm_options_support_frontend_model_controls(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:latest")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.2")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("MARATHON_API_TOKEN", raising=False)

    response = client.get("/llm-options")

    assert response.status_code == 200
    payload = response.json()
    assert payload["default"]["provider"] == "ollama"
    assert [item["id"] for item in payload["providers"]] == ["ollama", "ds", "openai"]
    openai = next(item for item in payload["providers"] if item["id"] == "openai")
    assert openai["default_model"] == "gpt-5.2"
    assert openai["api_key_configured"] is True


def test_llm_options_masks_provider_key_status_when_token_guard_is_enabled(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-ds-test")
    monkeypatch.setenv("MARATHON_API_TOKEN", "guard-token")

    public_response = client.get("/llm-options")
    private_response = client.get("/llm-options", headers={"Authorization": "Bearer guard-token"})

    assert public_response.status_code == 200
    public_payload = public_response.json()
    for provider_id in {"ds", "openai"}:
        item = next(item for item in public_payload["providers"] if item["id"] == provider_id)
        assert item["api_key_config_visible"] is False
        assert item["api_key_configured"] is False

    assert private_response.status_code == 200
    private_payload = private_response.json()
    openai = next(item for item in private_payload["providers"] if item["id"] == "openai")
    assert openai["api_key_config_visible"] is True
    assert openai["api_key_configured"] is True


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


def test_runner_role_plan_detail_trims_expert_audit_fields(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    db = _Database(tmp_path / "runner-plan-projection.db")
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    monkeypatch.setenv("MARATHON_API_TOKEN", "runner-token")
    monkeypatch.delenv("MARATHON_EXPERT_API_TOKEN", raising=False)
    plan = {
        "plan_meta": {
            "goal": "Half marathon projection",
            "requested_weeks": 1,
            "actual_weeks": 1,
            "plan_type": "single_week",
        },
        "workflow_trace": {"trace_version": "workflow_trace.v1", "run_id": "internal-run"},
        "week_plans": [
            {
                "week_index": 1,
                "phase": "base",
                "load_level": "easy",
                "days": [
                    {
                        "day": "Mon",
                        "training_type": "Easy run",
                        "main_set": "30 min Z2",
                        "evidence_tier": "action_library",
                        "training_load": {"source_type": "planned_load_proxy", "not_device_metric": True},
                        "field_sources": {"main_set": {"source_type": "action_library"}},
                        "protocol_check": {"allowed": True},
                        "action_match": {"matched": True},
                        "kb_fallback": {"used": False},
                        "risk_gate": {"status": "not_evaluated"},
                        "workflow_trace": {"run_id": "day-run"},
                        "trace": {"final_card": True},
                    },
                ],
            }
        ],
    }
    plan_id = db.save_training_plan(plan, source_query="projection")
    event_id = db.list_events(plan_id)[0]["id"]

    feedback = client.post(
        "/feedback",
        headers={"Authorization": "Bearer runner-token"},
        json={
            "user_id": "default_user",
            "plan_id": plan_id,
            "event_id": event_id,
            "raw_text": "Partial session with high fatigue.",
            "feedback": {
                "completion_status": "partial",
                "subjective_fatigue": "high",
                "pain_status": "none",
                "sleep_quality": "poor",
            },
        },
    )
    assert feedback.status_code == 200

    response = client.get(f"/plans/{plan_id}", headers={"Authorization": "Bearer runner-token"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_trace"] == {}
    assert "workflow_trace" not in payload["structured_training_plan"]
    event = payload["events"][0]
    assert event["main_set"] == "30 min Z2"
    assert event["evidence_tier"] == "action_library"
    assert event["training_load"]["source_type"] == "planned_load_proxy"
    for key in {"field_sources", "protocol_check", "action_match", "kb_fallback", "risk_gate", "workflow_trace", "trace"}:
        assert key not in event
    latest = event["latest_feedback"]
    assert latest["next_day_adjustment"]
    for key in {"raw_text", "risk_gate", "protocol_recheck", "workflow_trace"}:
        assert key not in latest
    history = payload["adjustment_history"][0]
    assert history["adaptive_adjustment"]["next_day_adjustment"]
    for key in {"risk_gate", "protocol_recheck"}:
        assert key not in history


def test_expert_role_plan_detail_preserves_audit_fields_with_expert_key(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    db = _Database(tmp_path / "expert-plan-projection.db")
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    monkeypatch.setenv("MARATHON_API_TOKEN", "runner-token")
    monkeypatch.setenv("MARATHON_EXPERT_API_TOKEN", "expert-token")
    plan = {
        "plan_meta": {
            "goal": "Half marathon expert projection",
            "requested_weeks": 1,
            "actual_weeks": 1,
            "plan_type": "single_week",
        },
        "workflow_trace": {"trace_version": "workflow_trace.v1", "run_id": "internal-run"},
        "week_plans": [
            {
                "week_index": 1,
                "phase": "base",
                "load_level": "easy",
                "days": [
                    {
                        "day": "Mon",
                        "training_type": "Easy run",
                        "main_set": "30 min Z2",
                        "field_sources": {"main_set": {"source_type": "action_library"}},
                        "risk_gate": {"status": "not_evaluated"},
                        "workflow_trace": {"run_id": "day-run"},
                    },
                ],
            }
        ],
    }
    plan_id = db.save_training_plan(plan, source_query="expert projection")

    response = client.get(
        f"/plans/{plan_id}",
        headers={
            "Authorization": "Bearer runner-token",
            "X-Marathon-Response-Role": "expert",
            "X-Marathon-Expert-Key": "expert-token",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_trace"]["run_id"] == "internal-run"
    assert payload["structured_training_plan"]["workflow_trace"]["run_id"] == "internal-run"
    assert payload["events"][0]["field_sources"]["main_set"]["source_type"] == "action_library"
    assert payload["events"][0]["risk_gate"]["status"] == "not_evaluated"


def test_invalid_expert_role_header_is_rejected_when_expert_key_configured(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    db = _Database(tmp_path / "invalid-expert-role.db")
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    monkeypatch.setenv("MARATHON_API_TOKEN", "runner-token")
    monkeypatch.setenv("MARATHON_EXPERT_API_TOKEN", "expert-token")
    plan_id = db.save_training_plan(
        {
            "plan_meta": {"goal": "reject expert spoof", "requested_weeks": 1, "actual_weeks": 1},
            "week_plans": [
                {
                    "week_index": 1,
                    "days": [{"day": "Mon", "training_type": "Easy run", "main_set": "30 min Z2"}],
                }
            ],
        },
        source_query="reject",
    )

    response = client.get(
        f"/plans/{plan_id}",
        headers={
            "Authorization": "Bearer runner-token",
            "X-Marathon-Response-Role": "expert",
            "X-Marathon-Expert-Key": "wrong-token",
        },
    )

    assert response.status_code == 403
    assert "专家响应" in response.json()["detail"]


def test_invalid_response_role_header_is_rejected(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    db = _Database(tmp_path / "invalid-response-role.db")
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    monkeypatch.setenv("MARATHON_API_TOKEN", "runner-token")
    plan_id = db.save_training_plan(
        {
            "plan_meta": {"goal": "invalid response role", "requested_weeks": 1, "actual_weeks": 1},
            "week_plans": [
                {
                    "week_index": 1,
                    "days": [{"day": "Mon", "training_type": "Easy run", "main_set": "30 min Z2"}],
                }
            ],
        },
        source_query="invalid role",
    )

    response = client.get(
        f"/plans/{plan_id}",
        headers={
            "Authorization": "Bearer runner-token",
            "X-Marathon-Response-Role": "admin",
        },
    )

    assert response.status_code == 400
    assert "response role" in response.json()["detail"]


def test_runner_role_query_projection_trims_nested_audit_fields(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    db = _Database(tmp_path / "runner-query-projection.db")
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    monkeypatch.setenv("MARATHON_API_TOKEN", "runner-token")
    monkeypatch.delenv("MARATHON_EXPERT_API_TOKEN", raising=False)
    monkeypatch.setattr(
        api_app,
        "load_user_profile",
        lambda: {
            "goal": "半马 PB 1小时45分",
            "weekly_mileage": 35,
            "target_pace": "半马 1:45",
        },
    )
    monkeypatch.setattr(
        api_app,
        "get_knowledge_base_health_snapshot",
        lambda: {"ok": True, "ready": True, "chunks_count": 1160, "faiss_ready": True, "source": "test"},
    )

    response = client.post(
        "/query",
        headers={"Authorization": "Bearer runner-token"},
        json={
            "query": "请给我生成 4 周半马训练计划",
            "user_id": "default_user",
            "response_mode": "skeleton",
            "timeout_sec": 15,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_trace"] == {}
    assert payload["token_usage"] == {}
    assert payload["audit_scores"] == {}
    assert "workflow_trace" not in payload["structured_training_plan"]
    assert payload["daily_schedule_cards"]
    assert any(str(card.get("main_set") or "").strip() for card in payload["daily_schedule_cards"])
    assert any(str(card.get("evidence_tier") or "").strip() for card in payload["daily_schedule_cards"])
    for card in payload["daily_schedule_cards"]:
        for key in {"field_sources", "protocol_check", "action_match", "kb_fallback", "risk_gate", "workflow_trace", "trace"}:
            assert key not in card
    for day in payload["monthly_training_calendar"]["days"]:
        for key in {"field_sources", "protocol_check", "action_match", "kb_fallback", "risk_gate", "workflow_trace", "trace"}:
            assert key not in day


def test_runner_role_training_calendar_projection_trims_daily_audit_fields(monkeypatch):
    structured_plan = _one_week_calendar_contract_plan()
    fake_app = _FakeIntegratedApp(result={"structured_training_plan": structured_plan})
    monkeypatch.setattr(api_app, "integrated_app", fake_app)
    monkeypatch.setattr(api_app, "load_user_profile", lambda: {"goal": "半马 PB"})
    monkeypatch.setenv("MARATHON_API_TOKEN", "runner-token")

    response = client.post(
        "/training-calendar",
        headers={"Authorization": "Bearer runner-token"},
        json={
            "query": "请给我生成 1 周半马训练计划",
            "user_id": "default_user",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["daily_schedule_cards"]
    for card in payload["daily_schedule_cards"]:
        assert "training_load" in card
        for key in {"field_sources", "protocol_check", "action_match", "kb_fallback", "risk_gate", "workflow_trace", "trace"}:
            assert key not in card
    for day in payload["monthly_training_calendar"]["days"]:
        for key in {"field_sources", "protocol_check", "action_match", "kb_fallback", "risk_gate", "workflow_trace", "trace"}:
            assert key not in day


def test_plan_save_accepts_calendar_settings_and_event_schedule_patch(tmp_path, monkeypatch):
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
                    {"day": "周二", "training_type": "休息", "main_set": "休息"},
                ],
            }
        ],
    }

    response = client.post(
        "/plans",
        json={
            "user_id": "default_user",
            "source_query": "生成1周计划",
            "structured_training_plan": plan,
            "calendar_settings": {
                "training_start_date": "2026-06-01",
                "default_start_time": "18:30",
            },
        },
    )

    assert response.status_code == 200
    plan_id = response.json()["plan_id"]
    detail = client.get(f"/plans/{plan_id}").json()
    assert detail["plan"]["start_date"] == "2026-06-01"
    assert detail["events"][0]["scheduled_date"] == "2026-06-01"
    assert detail["events"][0]["start_time"] == "18:30"

    event_id = detail["events"][0]["id"]
    patch_response = client.patch(
        f"/plans/{plan_id}/events/{event_id}",
        json={
            "scheduled_date": "2026-06-03",
            "start_time": "19:15",
            "duration_min": 45,
        },
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["updated"] is True
    updated_detail = client.get(f"/plans/{plan_id}").json()
    updated_event = updated_detail["events"][0]
    assert updated_event["scheduled_date"] == "2026-06-03"
    assert updated_event["start_time"] == "19:15"
    assert updated_event["duration_min"] == 45


def test_plan_save_accepts_calendar_days_and_preserves_audit_chain(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    db = _Database(tmp_path / "plans.db")
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    plan = {
        "plan_meta": {"goal": "半马 PB", "requested_weeks": 1, "actual_weeks": 1},
        "week_plans": [
            {
                "week_index": 1,
                "phase": "base",
                "days": [{"day": "周二", "training_type": "VO2max", "main_set": "骨架候选"}],
            }
        ],
    }
    calendar_day = {
        "week_index": 1,
        "day_index": 2,
        "day_label": "周二",
        "training_type": "VO2max",
        "training_type_label": "VO2max 间歇",
        "workout_type": "vo2max_interval",
        "main_set": "4x1000m",
        "evidence_tier": "action_library",
        "card_status": "generated",
        "field_sources": {"main_set": {"source_type": "action_library", "source_id": "动作库.pdf"}},
        "protocol_check": {"allowed": True},
        "action_match": {"action_id": "vo2max_interval_foundation", "source": "动作库.pdf"},
        "kb_fallback": {"used": False},
        "risk_gate": {"status": "not_evaluated"},
        "trace": {"action_match": {"action_id": "vo2max_interval_foundation"}},
    }

    response = client.post(
        "/plans",
        json={
            "user_id": "default_user",
            "source_query": "生成1周计划",
            "structured_training_plan": plan,
            "calendar_days": [calendar_day],
        },
    )

    assert response.status_code == 200
    detail = client.get(f"/plans/{response.json()['plan_id']}").json()
    event = detail["events"][0]
    assert event["main_set"] == "4x1000m"
    assert event["field_sources"]["main_set"]["source_type"] == "action_library"
    assert event["protocol_check"]["allowed"] is True
    assert event["action_match"]["action_id"] == "vo2max_interval_foundation"
    assert event["kb_fallback"]["used"] is False
    assert event["risk_gate"]["status"] == "not_evaluated"
    assert event["trace"]["action_match"]["action_id"] == "vo2max_interval_foundation"


def test_training_calendar_response_exposes_full_calendar_and_daily_card_contract(monkeypatch):
    structured_plan = _one_week_calendar_contract_plan()
    fake_app = _FakeIntegratedApp(result={"structured_training_plan": structured_plan})
    monkeypatch.setattr(api_app, "integrated_app", fake_app)
    monkeypatch.setattr(api_app, "load_user_profile", lambda: {"goal": "半马 PB"})

    response = client.post(
        "/training-calendar",
        json={
            "query": "请给我生成 1 周半马训练计划",
            "user_id": "default_user",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    calendar = payload["monthly_training_calendar"]
    cards = payload["daily_schedule_cards"]
    assert calendar["days"]
    assert len(cards) == len(calendar["days"]) == calendar["total_days"]
    assert payload["phases"] == calendar["phases"]
    assert payload["training_load_summary"] == calendar["training_load_summary"]

    required_card_fields = {
        "warmup",
        "main_set",
        "cooldown",
        "intensity",
        "duration",
        "training_load",
        "training_objective",
        "risk_gate",
        "field_sources",
    }
    assert required_card_fields <= set(cards[0])
    assert cards[0]["risk_gate"]
    assert cards[0]["field_sources"]


def test_training_calendar_error_does_not_leak_raw_exception(monkeypatch):
    fake_app = _FakeIntegratedApp(error=RuntimeError("database sk-secret should not leak"))
    monkeypatch.setattr(api_app, "integrated_app", fake_app)
    monkeypatch.setattr(api_app, "load_user_profile", lambda: {"goal": "半马 PB"})

    response = client.post(
        "/training-calendar",
        json={
            "query": "请给我生成 1 周半马训练计划",
            "user_id": "default_user",
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "模型服务暂不可用"


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
    assert payload["workflow_trace"]["trace_version"] == "workflow_trace.v1"
    assert payload["workflow_trace"]["feedback_state"]["has_feedback"] is True
    assert payload["workflow_trace"]["feedback_state"]["risk_gate"]["status"] == "needs_protocol_recheck"
    assert payload["workflow_trace"]["risk_state"]["fail_closed"] is False
    assert payload["adaptive_adjustment"]["adjustment_required"] is True
    assert "pain_risk" in payload["adaptive_adjustment"]["reason_codes"]
    assert payload["adaptive_adjustment"]["adjustment_action"] == "deescalate_or_refuse"
    assert payload["plan_diff"]["workflow"] == ["risk_gate", "protocol_recheck", "adjustment", "plan_diff"]
    assert payload["plan_diff"]["downgraded"] >= 1
    assert "pain_risk" in payload["plan_diff"]["reason_codes"]


def test_runner_role_feedback_projection_keeps_user_actions_and_hides_trace(monkeypatch):
    monkeypatch.setenv("MARATHON_API_TOKEN", "runner-token")

    response = client.post(
        "/feedback",
        headers={"Authorization": "Bearer runner-token"},
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
    assert payload["risk_gate"]["status"] == "needs_protocol_recheck"
    assert payload["risk_gate"]["adjustment_action"] == "deescalate_or_refuse"
    assert payload["protocol_recheck"] == {
        "allowed": True,
        "risk_gate_status": "needs_protocol_recheck",
    }
    assert payload["adaptive_adjustment"]["next_day_adjustment"]
    assert payload["plan_diff"]["affected_days"] >= 1
    assert payload["workflow_trace"] == {}
    assert "raw_text" not in payload["adaptive_feedback"]
    assert "workflow" not in payload["adaptive_feedback"]
    assert "workout_feedback" not in payload["adaptive_feedback"]


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
    assert payload["workflow_trace"]["risk_state"]["fail_closed"] is True
    assert payload["workflow_trace"]["feedback_state"]["protocol_recheck"]["allowed"] is False
    assert payload["generation_status"] == "medical_referral"
    assert payload["plan_diff"]["cancelled"] >= 1
    assert payload["plan_diff"]["workflow"] == ["risk_gate", "protocol_recheck", "adjustment", "plan_diff"]


def test_feedback_endpoint_without_plan_event_fields_keeps_contract():
    response = client.post(
        "/feedback",
        json={
            "user_id": "default_user",
            "raw_text": "Completed as planned.",
            "feedback": {
                "completion_status": "completed",
                "subjective_fatigue": "low",
                "pain_status": "none",
                "sleep_quality": "good",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert {
        "workout_feedback",
        "risk_gate",
        "protocol_recheck",
        "adaptive_feedback",
        "adaptive_adjustment",
        "plan_diff",
        "generation_status",
    } <= set(payload)
    assert payload["feedback_id"] is None
    assert payload["generation_status"] == "generated"


def test_feedback_endpoint_rejects_invalid_plan_event_fields():
    response = client.post(
        "/feedback",
        json={
            "user_id": "default_user",
            "plan_id": "missing-plan",
            "event_id": "missing-event",
            "day_key": "2026-06-01",
            "raw_text": "Completed as planned.",
            "feedback": {
                "completion_status": "completed",
                "subjective_fatigue": "low",
                "pain_status": "none",
                "sleep_quality": "good",
            },
        },
    )

    assert response.status_code == 404
    assert "训练日历事件不存在" in response.json()["detail"]


def test_feedback_endpoint_maps_four_feedback_inputs_to_reason_codes():
    cases = [
        (
            {
                "completion_status": "completed",
                "subjective_fatigue": "mild",
                "pain_status": "none",
                "sleep_quality": "ok",
            },
            "mild_fatigue",
        ),
        (
            {
                "completion_status": "partial",
                "subjective_fatigue": "high",
                "pain_status": "none",
                "sleep_quality": "poor",
            },
            "high_fatigue",
        ),
        (
            {
                "completion_status": "completed",
                "subjective_fatigue": "low",
                "pain_status": "risk",
                "sleep_quality": "ok",
            },
            "pain_risk",
        ),
        (
            {
                "completion_status": "missed",
                "subjective_fatigue": "low",
                "pain_status": "none",
                "sleep_quality": "ok",
            },
            "missed_workout",
        ),
    ]

    for feedback, expected_code in cases:
        response = client.post(
            "/feedback",
            json={
                "user_id": "default_user",
                "raw_text": "",
                "feedback": feedback,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert expected_code in payload["adaptive_adjustment"]["reason_codes"]
        assert expected_code in payload["plan_diff"]["reason_codes"]


def test_feedback_endpoint_downgrades_pain_and_medical_alternatives():
    unsafe_terms = ["threshold", "interval", "high intensity", "vo2", "tempo"]
    safe_terms = ["low impact", "rest", "swim", "bike", "cycling", "elliptical", "休息", "停止训练", "专业医疗评估"]

    for raw_text, feedback in [
        (
            "Knee pain after training.",
            {
                "completion_status": "completed",
                "subjective_fatigue": "low",
                "pain_status": "risk",
                "sleep_quality": "ok",
            },
        ),
        (
            "Chest pain and dizzy during a hot session, possible heat illness.",
            {
                "completion_status": "partial",
                "subjective_fatigue": "high",
                "pain_status": "risk",
                "sleep_quality": "poor",
            },
        ),
    ]:
        response = client.post(
            "/feedback",
            json={"user_id": "default_user", "raw_text": raw_text, "feedback": feedback},
        )

        assert response.status_code == 200
        alternative = response.json()["adaptive_adjustment"]["alternative_workout"].lower()
        assert any(term in alternative for term in safe_terms)
        assert not any(term in alternative for term in unsafe_terms)


def test_feedback_endpoint_persists_latest_event_feedback_summary(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    db = _Database(tmp_path / "feedback.db")
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    plan = {
        "plan_meta": {
            "goal": "Half marathon PB",
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
                    {"day": "Mon", "training_type": "Easy run", "main_set": "30 min Z2"},
                ],
            }
        ],
    }
    plan_id = db.save_training_plan(plan, source_query="save plan")
    event_id = db.list_events(plan_id)[0]["id"]

    response = client.post(
        "/feedback",
        json={
            "user_id": "default_user",
            "plan_id": plan_id,
            "event_id": event_id,
            "day_key": "2026-06-01",
            "raw_text": "Partial session with high fatigue.",
            "feedback": {
                "completion_status": "partial",
                "subjective_fatigue": "high",
                "pain_status": "none",
                "sleep_quality": "poor",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["feedback_id"]

    detail = client.get(f"/plans/{plan_id}").json()
    latest = detail["events"][0]["latest_feedback"]
    assert latest["id"] == payload["feedback_id"]
    assert latest["completion_status"] == "partial"
    assert "high_fatigue" in latest["reason_codes"]
    assert latest["next_day_adjustment"]
    assert latest["raw_text"] == "Partial session with high fatigue."
    assert latest["risk_gate"]["status"] == "needs_protocol_recheck"
    assert latest["risk_gate"]["adjustment_action"] == "deescalate"
    assert "high_fatigue" in latest["risk_gate"]["triggers"]
    assert latest["protocol_recheck"]["allowed"] is True
    assert "high_fatigue" in latest["protocol_recheck"]["violations"]


def test_get_plan_returns_execution_status_and_adjustment_history(tmp_path, monkeypatch):
    from datetime import date, timedelta

    from marathon_qa_assistant.services.database import _Database

    db = _Database(tmp_path / "execution-status.db")
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    week_start = date.today() - timedelta(days=date.today().weekday())
    plan = {
        "plan_meta": {
            "goal": "Half marathon status loop",
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
                    {"day": "Mon", "training_type": "Easy run", "main_set": "30 min Z2"},
                    {"day": "Tue", "training_type": "Threshold", "main_set": "3 x 8 min"},
                    {"day": "Wed", "training_type": "Easy run", "main_set": "30 min Z2"},
                    {"day": "Thu", "training_type": "Rest", "main_set": "Rest"},
                ],
            }
        ],
    }
    plan_id = db.save_training_plan(plan, source_query="status loop", training_start_date=week_start.isoformat())
    events = db.list_events(plan_id)

    first = client.post(
        "/feedback",
        json={
            "user_id": "default_user",
            "plan_id": plan_id,
            "event_id": events[0]["id"],
            "raw_text": "Completed as planned.",
            "feedback": {
                "completion_status": "completed",
                "subjective_fatigue": "low",
                "pain_status": "none",
                "sleep_quality": "good",
            },
        },
    )
    second = client.post(
        "/feedback",
        json={
            "user_id": "default_user",
            "plan_id": plan_id,
            "event_id": events[1]["id"],
            "raw_text": "Partial session with high fatigue and poor sleep.",
            "feedback": {
                "completion_status": "partial",
                "subjective_fatigue": "high",
                "pain_status": "none",
                "sleep_quality": "poor",
            },
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200

    detail = client.get(f"/plans/{plan_id}").json()

    summary = detail["execution_status_summary"]
    assert summary["planned_count"] == 3
    assert summary["completed_count"] == 1
    assert summary["partial_count"] == 1
    assert summary["missed_feedback_count"] == 1
    assert summary["completion_rate"] == 50
    assert summary["risk_level"] == "deescalate"
    assert "high_fatigue" in summary["risk_reasons"]
    assert summary["risk_rule_source"] == "deterministic_feedback_rules"

    history = detail["adjustment_history"]
    assert len(history) == 2
    assert history[0]["feedback_id"] == second.json()["feedback_id"]
    assert history[0]["event_id"] == events[1]["id"]
    assert "high_fatigue" in history[0]["reason_codes"]
    assert history[0]["risk_gate"]["status"] == "needs_protocol_recheck"
    assert history[0]["protocol_recheck"]["allowed"] is True
    assert history[0]["adaptive_adjustment"]["next_day_adjustment"]
    assert history[0]["plan_diff"]["workflow"] == ["risk_gate", "protocol_recheck", "adjustment", "plan_diff"]
    assert history[0]["affected_events"][0]["event_id"] == events[2]["id"]


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


def test_delete_plan_refuses_plan_owned_by_another_user(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import _Database

    db = _Database(tmp_path / "foreign_plan.db")
    monkeypatch.setattr(api_app, "get_db", lambda: db)

    plan_id = db.save_training_plan(
        {
            "plan_meta": {
                "goal": "foreign",
                "requested_weeks": 1,
                "actual_weeks": 1,
                "plan_type": "single_week",
            },
            "week_plans": [
                {
                    "week_index": 1,
                    "phase": "base",
                    "load_level": "easy",
                    "days": [{"day": "Mon", "training_type": "easy", "main_set": "30 min Z2"}],
                }
            ],
        },
        source_query="foreign delete",
        user_id="another_user",
    )

    response = client.delete(f"/plans/{plan_id}")

    assert response.status_code == 404
    assert db.get_plan(plan_id) is not None
