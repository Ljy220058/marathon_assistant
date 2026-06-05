import json

import pytest

from marathon_qa_assistant.services.database import _Database


def _plan_with_invalid_event_value():
    return {
        "plan_meta": {
            "requested_weeks": 1,
            "actual_weeks": 1,
            "goal": "事务回滚测试",
            "experience_level": "进阶",
            "plan_type": "single_week",
        },
        "week_plans": [
            {
                "week_index": 1,
                "days": [
                    {
                        "day": "周一",
                        "training_type": "轻松跑",
                        "main_set": "30分钟 Z2",
                        "warmup_km": "boom",
                        "main_km": 5.0,
                        "cooldown_km": 0.5,
                    }
                ],
            }
        ],
    }


def _sample_plan():
    return {
        "plan_meta": {
            "requested_weeks": 1,
            "actual_weeks": 1,
            "goal": "反馈回滚测试",
            "experience_level": "进阶",
            "plan_type": "single_week",
        },
        "week_plans": [
            {
                "week_index": 1,
                "days": [
                    {
                        "day": "周一",
                        "training_type": "轻松跑",
                        "main_set": "30分钟 Z2",
                        "warmup_km": 1.0,
                        "main_km": 5.0,
                        "cooldown_km": 0.5,
                    }
                ],
            }
        ],
    }


def test_save_training_plan_rolls_back_when_event_write_fails(tmp_path):
    db = _Database(tmp_path / "transactions.db")

    with pytest.raises(ValueError):
        db.save_training_plan(_plan_with_invalid_event_value(), source_query="tx rollback")

    plans = db.list_training_plans()
    rows = db._get_conn().execute("SELECT COUNT(*) AS count FROM training_calendar_events").fetchone()

    assert plans == []
    assert rows["count"] == 0


def test_save_feedback_replan_rolls_back_when_exception_insert_fails(tmp_path, monkeypatch):
    db = _Database(tmp_path / "transactions.db")
    plan_id = db.save_training_plan(_sample_plan(), source_query="feedback tx rollback")
    event_id = db.list_events(plan_id)[0]["id"]

    real_conn = db._get_conn()
    original_content = db.get_event(plan_id, event_id)["content_json"]

    class FailingConn:
        def __init__(self, conn):
            self._conn = conn

        def __getattr__(self, name):
            return getattr(self._conn, name)

        def execute(self, sql, params=()):
            normalized = " ".join(str(sql).split()).upper()
            if "INSERT INTO TRAINING_EVENT_EXCEPTIONS" in normalized:
                raise RuntimeError("boom during exception insert")
            return self._conn.execute(sql, params)

    failing_conn = FailingConn(real_conn)
    monkeypatch.setattr(db, "_get_conn", lambda: failing_conn)

    with pytest.raises(RuntimeError, match="boom during exception insert"):
        db.save_feedback_replan(
            plan_id=plan_id,
            feedback_id="feedback-1",
            user_id="default_user",
            feedback_replan={
                "patches": [
                    {
                        "event_id": event_id,
                        "suggested": {"main_set": "降级为 20 分钟轻松跑"},
                    }
                ]
            },
            apply_patch=True,
        )

    event = db.get_event(plan_id, event_id)
    exceptions = real_conn.execute(
        "SELECT COUNT(*) AS count FROM training_event_exceptions WHERE plan_id = ?",
        (plan_id,),
    ).fetchone()

    assert event["content_json"] == original_content
    assert json.loads(event["content_json"]).get("feedback_replan") is None
    assert exceptions["count"] == 0
