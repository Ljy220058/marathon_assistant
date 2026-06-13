from marathon_qa_assistant.services.database import _Database


def _sample_plan():
    return {
        "plan_meta": {
            "requested_weeks": 1,
            "actual_weeks": 1,
            "goal": "半马训练",
            "experience_level": "进阶",
            "target_race_date": "4周后",
            "plan_type": "single_week",
            "render_version": "v1",
        },
        "week_plans": [
            {
                "week_index": 1,
                "phase": "基础期",
                "load_level": "medium",
                "days": [
                    {
                        "day": "周一",
                        "training_type": "休息",
                        "warmup": "",
                        "main_set": "休息",
                        "cooldown": "",
                        "venue": "",
                        "notes": "",
                    },
                    {
                        "day": "周二",
                        "training_type": "轻松跑",
                        "warmup": "10分钟慢跑",
                        "main_set": "30分钟 Z2",
                        "cooldown": "5分钟放松",
                        "venue": "操场",
                        "notes": "保持轻松",
                        "warmup_km": 1.0,
                        "main_km": 5.0,
                        "cooldown_km": 0.5,
                    },
                ],
            }
        ],
    }


def test_save_training_plan_creates_plan_and_calendar_events(tmp_path):
    db = _Database(tmp_path / "calendar.db")

    plan_id = db.save_training_plan(_sample_plan(), source_query="生成1周计划")

    plan = db.get_plan(plan_id)
    events = db.list_events(plan_id)
    unsynced = db.get_unsynced_events(plan_id)

    assert plan is not None
    assert plan["goal"] == "半马训练"
    assert plan["source_query"] == "生成1周计划"
    assert len(events) == 2
    assert len(unsynced) == 2
    assert events[0]["workout_type"] == "rest"
    assert events[1]["title"] == "第1周周二｜轻松跑"
    assert events[1]["duration_min"] == 30
    assert events[1]["total_km"] == 6.5
    assert events[1]["sync_status"] == "not_synced"


def test_save_training_plan_respects_calendar_start_date_and_default_time(tmp_path):
    db = _Database(tmp_path / "calendar.db")

    plan_id = db.save_training_plan(
        _sample_plan(),
        source_query="生成1周计划",
        training_start_date="2026-06-01",
        default_start_time="18:30",
    )

    plan = db.get_plan(plan_id)
    events = db.list_events(plan_id)

    assert plan["start_date"] == "2026-06-01"
    assert [event["scheduled_date"] for event in events] == ["2026-06-01", "2026-06-02"]
    assert [event["start_time"] for event in events] == ["18:30", "18:30"]


def test_update_event_schedule_marks_event_unsynced(tmp_path):
    db = _Database(tmp_path / "calendar.db")
    plan_id = db.save_training_plan(
        _sample_plan(),
        source_query="生成1周计划",
        training_start_date="2026-06-01",
        default_start_time="07:00",
    )
    event_id = db.list_events(plan_id)[1]["id"]

    updated = db.update_event_schedule(
        event_id,
        scheduled_date="2026-06-05",
        start_time="19:15",
        duration_min=45,
    )

    events = db.list_events(plan_id)
    event = next(item for item in events if item["id"] == event_id)
    assert updated is True
    assert event["scheduled_date"] == "2026-06-05"
    assert event["start_time"] == "19:15"
    assert event["duration_min"] == 45
    assert event["sync_status"] == "not_synced"


def test_update_event_sync_status_marks_event_synced(tmp_path):
    db = _Database(tmp_path / "calendar.db")
    plan_id = db.save_training_plan(_sample_plan(), source_query="生成1周计划")
    event_id = db.list_events(plan_id)[0]["id"]

    db.update_event_sync_status(event_id, external_event_id="google-event-1")

    events = db.list_events(plan_id)
    updated = next(e for e in events if e["id"] == event_id)
    assert updated["external_event_id"] == "google-event-1"
    assert updated["external_calendar_provider"] == "google"
    assert updated["sync_status"] == "synced"
    assert len(db.get_unsynced_events(plan_id)) == 1


def test_list_training_plans_returns_saved_plans(tmp_path):
    db = _Database(tmp_path / "calendar.db")
    db.save_training_plan(_sample_plan(), source_query="生成1周计划")
    plans = db.list_training_plans()
    assert len(plans) == 1
    assert plans[0]["goal"] == "半马训练"
    assert plans[0]["version"] == 1
    assert plans[0]["trigger"] == "initial"


def test_save_training_plan_creates_version_chain_and_rollback_record(tmp_path):
    db = _Database(tmp_path / "calendar.db")
    v1_id = db.save_training_plan(_sample_plan(), source_query="生成1周计划")
    v1 = db.get_plan(v1_id)

    updated_plan = _sample_plan()
    updated_plan["plan_meta"]["goal"] = "半马训练调整版"
    v2_id = db.save_training_plan(
        updated_plan,
        source_query="调整计划",
        lineage_id=v1["lineage_id"],
        parent_plan_id=v1_id,
        trigger="missed_adapt",
        trigger_detail="漏训后调整",
    )
    rollback_id = db.rollback_training_plan(v2_id, 1, trigger_detail="用户手动回退到 v1")

    v2 = db.get_plan(v2_id)
    rollback = db.get_plan(rollback_id)
    versions = db.list_plan_versions(v2_id)
    loaded_v1 = db.get_plan_version(v1["lineage_id"], 1)

    assert loaded_v1["id"] == v1_id
    assert v2["version"] == 2
    assert v2["parent_plan_id"] == v1_id
    assert v2["parent_version"] == 1
    assert v2["trigger"] == "missed_adapt"
    assert rollback["version"] == 3
    assert rollback["parent_plan_id"] == v1_id
    assert rollback["parent_version"] == 1
    assert rollback["trigger"] == "manual_rollback"
    assert rollback["trigger_detail"] == "用户手动回退到 v1"
    assert [item["version"] for item in versions] == [1, 2, 3]
    assert len(db.list_events(rollback_id)) == len(db.list_events(v1_id))


def test_build_calendar_props_from_db(tmp_path, monkeypatch):
    from marathon_qa_assistant.services.database import get_db as _get_db
    from marathon_qa_assistant.ui.plan_ui import build_calendar_props_from_db

    db = _Database(tmp_path / "calendar.db")
    monkeypatch.setattr("marathon_qa_assistant.services.database._db_instance", db, raising=False)
    plan_id = db.save_training_plan(_sample_plan(), source_query="生成1周计划")

    props = build_calendar_props_from_db(plan_id)
    assert props
    assert len(props["days"]) == 2
    assert props["days"][0]["workout_type"] == "rest"
    assert props["days"][1]["week_index"] == 1
    assert props["days"][1]["day_index"] == 2
    assert "MonthlyTrainingCalendar"  # 确认 props 结构兼容
