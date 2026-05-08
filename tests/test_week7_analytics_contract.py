import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from marathon_qa_assistant.services.analytics import (  # noqa: E402
    CORE_EVENTS,
    build_plan_click_properties,
    build_event_payload,
    get_or_create_session_id,
    track_event,
)


class FakeSession:
    def __init__(self):
        self.data = {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value


def test_week7_core_event_contract_has_route_map_events():
    assert {
        "app_opened",
        "profile_wizard_started",
        "profile_submitted",
        "plan_generate_clicked",
        "plan_generated",
        "workout_feedback_submitted",
        "adaptive_plan_generated",
        "weekly_review_viewed",
        "evidence_opened",
    }.issubset(CORE_EVENTS)


def test_week7_event_payload_has_public_fields():
    payload = build_event_payload(
        "plan_generated",
        user_id="default_user",
        session_id="session-1",
        properties={"has_final_report": True},
    )

    assert payload["event_name"] == "plan_generated"
    assert payload["user_id_hash"]
    assert payload["user_id_hash"] != "default_user"
    assert payload["session_id"] == "session-1"
    assert payload["version"]
    assert payload["timestamp"]
    assert payload["properties"] == {"has_final_report": True}


def test_week7_track_event_writes_jsonl(tmp_path):
    log_path = tmp_path / "events.jsonl"

    payload = track_event(
        "workout_feedback_submitted",
        user_id="runner-1",
        session_id="session-2",
        properties={"completion_status": "completed"},
        event_log_path=log_path,
    )

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    stored = json.loads(lines[0])
    assert stored == payload
    assert stored["event_name"] == "workout_feedback_submitted"
    assert stored["properties"]["completion_status"] == "completed"


def test_week7_session_id_is_reused_in_chainlit_like_session():
    session = FakeSession()

    first = get_or_create_session_id(session.get, session.set)
    second = get_or_create_session_id(session.get, session.set)

    assert first == second
    assert session.get("analytics_session_id") == first


def test_week7_plan_click_tracks_only_explicit_message_entry():
    payload = build_plan_click_properties(
        entry="message",
        message_text="请帮我生成 12 周马拉松训练计划",
        has_image_context=False,
    )

    assert payload == {
        "entry": "message",
        "source_type": "message",
        "query_length": len("请帮我生成 12 周马拉松训练计划"),
        "has_image_context": False,
    }


def test_week7_plan_click_skips_automatic_continuation():
    payload = build_plan_click_properties(
        entry=None,
        message_text="【训练计划请求】用户画像已完善。原始请求：请帮我生成 12 周马拉松训练计划",
        has_image_context=False,
    )

    assert payload is None


def test_week7_plan_click_accepts_explicit_button_sources():
    payload = build_plan_click_properties(
        entry="profile_submit",
        message_text="请为我生成第一周训练计划",
        has_image_context=False,
    )

    assert payload == {
        "entry": "profile_submit",
        "source_type": "action",
        "query_length": len("请为我生成第一周训练计划"),
        "has_image_context": False,
    }


def test_week7_remaining_route_map_events_write_jsonl(tmp_path):
    log_path = tmp_path / "events.jsonl"
    events = [
        "app_opened",
        "profile_wizard_started",
        "profile_submitted",
        "adaptive_plan_generated",
        "weekly_review_viewed",
        "evidence_opened",
    ]

    for event_name in events:
        track_event(
            event_name,
            user_id="runner-1",
            session_id="session-3",
            properties={"entry": "contract_test"},
            event_log_path=log_path,
        )

    stored = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert [item["event_name"] for item in stored] == events
    assert {item["session_id"] for item in stored} == {"session-3"}
    assert all(item["properties"]["entry"] == "contract_test" for item in stored)


def test_week7_plan_click_has_source_type():
    payload = build_plan_click_properties(
        entry="cancel_fill",
        message_text="请帮我生成训练计划",
        has_image_context=False,
    )

    assert payload["source_type"] == "action"


def test_week7_refined_event_properties_shapes():
    """验证细化后各事件的 properties 字段口径"""

    app_opened = build_event_payload(
        "app_opened",
        user_id="runner-1",
        session_id="s1",
        properties={
            "entry": "chat_start",
            "chat_profile": "Coach Mode",
            "initial_mode": "team",
            "has_user_profile": True,
            "profile_field_count": 5,
        },
    )
    assert app_opened["properties"]["entry"] == "chat_start"
    assert app_opened["properties"]["initial_mode"] == "team"
    assert app_opened["properties"]["profile_field_count"] == 5

    wizard_started = build_event_payload(
        "profile_wizard_started",
        user_id="runner-1",
        session_id="s1",
        properties={
            "entry": "experience_level",
            "wizard_mode": "full",
            "has_existing_profile": True,
            "pre_filled_field_count": 3,
        },
    )
    assert wizard_started["properties"]["wizard_mode"] == "full"
    assert wizard_started["properties"]["has_existing_profile"] is True
    assert wizard_started["properties"]["pre_filled_field_count"] == 3

    profile_submitted = build_event_payload(
        "profile_submitted",
        user_id="runner-1",
        session_id="s1",
        properties={
            "wizard_mode": "quick",
            "filled_fields": 3,
            "total_fields_available": 17,
            "will_generate_plan": True,
        },
    )
    assert profile_submitted["properties"]["filled_fields"] == 3
    assert profile_submitted["properties"]["total_fields_available"] == 17

    plan_generated = build_event_payload(
        "plan_generated",
        user_id="runner-1",
        session_id="s1",
        properties={
            "missing_info_status": "complete",
            "has_final_report": True,
            "final_report_length": 1234,
            "has_structured_training_plan": True,
            "plan_type": "multi_week",
            "actual_weeks": 4,
            "rag_source_count": 5,
            "has_training_explanation_panel": True,
        },
    )
    assert plan_generated["properties"]["plan_type"] == "multi_week"
    assert plan_generated["properties"]["actual_weeks"] == 4
    assert plan_generated["properties"]["rag_source_count"] == 5
    assert plan_generated["properties"]["final_report_length"] == 1234

    fb_text = build_event_payload(
        "workout_feedback_submitted",
        user_id="runner-1",
        session_id="s1",
        properties={
            "entry": "free_text",
            "source_type": "text",
            "completed": True,
            "completion_status": "completed",
            "feedback_length": 42,
            "has_keywords": True,
        },
    )
    assert fb_text["properties"]["source_type"] == "text"
    assert fb_text["properties"]["feedback_length"] == 42

    fb_action = build_event_payload(
        "workout_feedback_submitted",
        user_id="runner-1",
        session_id="s1",
        properties={
            "entry": "quick_action",
            "source_type": "action",
            "completed": False,
            "completion_status": "incomplete",
        },
    )
    assert fb_action["properties"]["source_type"] == "action"

    adaptive = build_event_payload(
        "adaptive_plan_generated",
        user_id="runner-1",
        session_id="s1",
        properties={
            "entry": "adaptive_context",
            "has_adjustment_summary": True,
            "has_recommendations": True,
            "recommendation_count": 3,
            "has_training_feedback": True,
        },
    )
    assert adaptive["properties"]["recommendation_count"] == 3
    assert adaptive["properties"]["has_training_feedback"] is True

    weekly = build_event_payload(
        "weekly_review_viewed",
        user_id="runner-1",
        session_id="s1",
        properties={
            "entry": "start_first_week",
            "week_index": 1,
            "has_key_workouts": True,
            "workout_count": 3,
        },
    )
    assert weekly["properties"]["workout_count"] == 3

    evidence = build_event_payload(
        "evidence_opened",
        user_id="runner-1",
        session_id="s1",
        properties={
            "entry": "view_pdf",
            "source_type": "action",
            "source_name": "test.pdf",
            "page": 1,
            "has_snippet": True,
            "snippet_length": 128,
            "file_type": "pdf",
        },
    )
    assert evidence["properties"]["source_type"] == "action"
    assert evidence["properties"]["snippet_length"] == 128
    assert evidence["properties"]["file_type"] == "pdf"
