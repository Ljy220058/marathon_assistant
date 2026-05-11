from fastapi.testclient import TestClient

from marathon_qa_assistant.apps import api_app
from marathon_qa_assistant.core.training_plan_skeleton import build_structured_training_plan_skeleton
from marathon_qa_assistant.services.daily_schedule_generator import generate_daily_schedule


def _all_days(plan):
    return [
        day
        for week in plan.get("week_plans", [])
        for day in week.get("days", [])
    ]


def _training_days(calendar):
    return [day for day in calendar.days if not day.is_rest]


def _hmp_cards(calendar):
    return [day for day in calendar.days if str(day.workout_type).startswith("hm_")]


def test_half_marathon_pb_plan_uses_protocol_cards_not_generic_templates():
    plan = build_structured_training_plan_skeleton(
        query="请给我生成12周半马训练计划，目标1小时45分，每周二周四周日训练。",
        profile={
            "goal": "半马 PB 1小时45分",
            "experience_level": "进阶",
            "weekly_mileage": 35,
            "target_pace": "半马 1:45",
            "t_pace": "3:15/km",
            "available_days": "周二,周四,周日",
            "plan_duration_weeks": 12,
        },
        requested_weeks=12,
    )
    calendar = generate_daily_schedule(plan, enable_kb_fallback=False)
    main_sets = [day["main_set"] for day in _all_days(plan)]
    hmp_cards = _hmp_cards(calendar)

    assert plan["half_marathon_protocol"]["active"] is True
    assert plan["half_marathon_protocol_validation"]["passed"] is True
    assert hmp_cards, "半马计划应产生可追溯的 HMP 日卡"
    assert all(card.evidence_tier == "protocol_rule" for card in hmp_cards)
    assert all(card.source for card in hmp_cards)
    assert all(card.training_objective for card in hmp_cards)
    assert all(card.warmup and card.cooldown for card in hmp_cards)
    assert any(card.alternative for card in hmp_cards)
    assert not any("3×2000m" in text for text in main_sets)
    assert not any(text.startswith("hm_") for text in main_sets)
    assert not any("3:15/km" in text or "3:20/km" in text for text in main_sets)
    assert calendar.evidence_summary["protocol_rule"] >= len(hmp_cards)


def test_half_marathon_foundation_cards_keep_semantic_type_aligned_with_main_set():
    plan = build_structured_training_plan_skeleton(
        query="请给我生成4周半马训练计划，目标1小时45分。",
        profile={
            "goal": "半马 PB 1小时45分",
            "experience_level": "进阶",
            "weekly_mileage": 35,
            "target_pace": "半马 1:45",
            "available_days": "周二,周四,周日",
            "plan_duration_weeks": 4,
        },
        requested_weeks=4,
    )
    calendar = generate_daily_schedule(plan, enable_kb_fallback=False)
    threshold_cards = [
        card
        for card in _hmp_cards(calendar)
        if card.workout_type == "hm_base_threshold_progression"
    ]

    assert threshold_cards
    assert all(card.workout_type == "hm_base_threshold_progression" for card in threshold_cards)
    assert all("基础期阈值/渐速跑" in card.training_type_label for card in threshold_cards)
    assert all(card.field_sources["main_set"]["source_type"] == "action_library" for card in threshold_cards)
    assert all(card.action_match.get("protocol_workout_type") == "hm_base_threshold_progression" for card in threshold_cards)


def test_marathon_plan_does_not_get_polluted_by_hmp_protocol_layer():
    plan = build_structured_training_plan_skeleton(
        query="请给我生成12周全马训练计划，目标3小时30分。",
        profile={
            "goal": "全马 3小时30分",
            "experience_level": "进阶",
            "weekly_mileage": 55,
            "target_pace": "全马 3:30",
            "available_days": "周二,周四,周六,周日",
            "plan_duration_weeks": 12,
        },
        requested_weeks=12,
    )
    calendar = generate_daily_schedule(plan, enable_kb_fallback=False)

    assert plan.get("half_marathon_protocol", {}).get("active") is not True
    assert not _hmp_cards(calendar)
    assert calendar.evidence_summary.get("protocol_rule", 0) == 0
    assert all(not str(day.workout_type).startswith("hm_") for day in _training_days(calendar))


def test_user_requested_workout_types_keep_requested_semantics_in_skeleton_cards():
    cases = [
        ("今天安排有氧阈值训练", "aerobic_threshold", "动作库.pdf"),
        ("今天安排无氧阈跑", "anaerobic_threshold", "动作库.pdf"),
        ("今天安排节奏跑", "tempo_run", "动作库.pdf"),
        ("今天安排间歇跑", "interval_run", "动作库.pdf"),
        ("今天安排摄氧量训练", "vo2max_interval", "动作库.pdf"),
    ]

    for request_text, expected_workout_type, expected_source in cases:
        plan = build_structured_training_plan_skeleton(
            query=f"请给我生成1周训练计划，{request_text}，每周二周四周日训练。",
            profile={
                "goal": "半马 PB 1小时45分",
                "experience_level": "进阶",
                "weekly_mileage": 35,
                "target_pace": "半马 1:45",
                "available_days": "周二,周四,周日",
                "plan_duration_weeks": 1,
            },
            requested_weeks=1,
        )
        calendar = generate_daily_schedule(plan, enable_kb_fallback=False)
        first_training_day = _training_days(calendar)[0]

        assert first_training_day.workout_type == expected_workout_type
        assert first_training_day.evidence_tier == "action_library"
        assert expected_source in " / ".join(first_training_day.source)
        assert first_training_day.main_set
        assert "动作库证据不足" not in first_training_day.main_set
        assert "主课" not in first_training_day.main_set
        assert first_training_day.warmup


def test_low_mileage_half_marathon_plan_keeps_quality_load_conservative():
    plan = build_structured_training_plan_skeleton(
        query="请给我生成8周半马完赛训练计划，最近疲劳偏高。",
        profile={
            "goal": "半马完赛",
            "experience_level": "新手",
            "weekly_mileage": 18,
            "available_days": "周二,周四,周日",
            "injury_or_fatigue": "最近疲劳偏高",
            "plan_duration_weeks": 8,
        },
        requested_weeks=8,
    )
    validation = plan["half_marathon_protocol_validation"]
    weeks = plan.get("week_plans", [])

    assert validation["active"] is True
    assert validation["passed"] is True
    for week in weeks:
        signature = week.get("repeat_guard_signature", {})
        assert int(signature.get("quality_session_count") or 0) <= 2
        assert int(signature.get("hard_day_count") or 0) <= 2
    assert not validation.get("issues")


def test_api_skeleton_response_matches_frontend_calendar_contract(tmp_path, monkeypatch):
    client = TestClient(api_app.app)
    from marathon_qa_assistant.services.database import _Database

    class _FailingIntegratedApp:
        async def ainvoke(self, *_args, **_kwargs):
            raise AssertionError("skeleton mode should not call the full LLM workflow")

    db = _Database(tmp_path / "plans.db")
    monkeypatch.setattr(api_app, "integrated_app", _FailingIntegratedApp())
    monkeypatch.setattr(api_app, "get_db", lambda: db)
    monkeypatch.setattr(
        api_app,
        "load_user_profile",
        lambda: {
            "goal": "半马 PB 1小时45分",
            "weekly_mileage": 35,
            "target_pace": "半马 1:45",
            "available_days": "周二,周四,周日",
            "plan_duration_weeks": 4,
        },
    )
    monkeypatch.setattr(
        api_app,
        "get_knowledge_base_health_snapshot",
        lambda: {"ok": True, "ready": True, "chunks_count": 1398, "faiss_ready": True, "source": "test"},
    )

    response = client.post(
        "/query",
        json={
            "query": "请给我生成4周半马训练计划",
            "user_id": "default_user",
            "response_mode": "skeleton",
            "timeout_sec": 15,
        },
    )

    payload = response.json()
    cards = payload.get("daily_schedule_cards") or []
    calendar_days = (payload.get("monthly_training_calendar") or {}).get("days") or []

    assert response.status_code == 200
    assert payload["generation_status"] == "skeleton_ready"
    assert payload["structured_report"] is None
    assert calendar_days
    assert cards
    assert len(cards) == len(calendar_days)
    assert payload["generation_timings"]["calendar_enrich_sec"] >= 0
    assert any(card.get("evidence_tier") == "protocol_rule" for card in cards)
    assert any(card.get("training_objective") for card in cards)
    assert any(card.get("warmup") and card.get("cooldown") for card in cards)
    assert payload["training_plan_id"]
