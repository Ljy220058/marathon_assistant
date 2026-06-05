import sys
from pathlib import Path


BASE_DIR = Path(__file__).absolute().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from marathon_qa_assistant.ui.coach_state import (  # noqa: E402
    apply_session_defaults,
    build_coach_ui_snapshot,
    render_coach_ui_status_md,
    sync_coach_ui_snapshot,
)


class FakeSession:
    def __init__(self):
        self.data = {"chat_profile": "Coach Mode"}
        apply_session_defaults(self.set)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value


def build_snapshot(session=None, workflow_state=None):
    session = session or FakeSession()
    return build_coach_ui_snapshot(session.get, workflow_state or {})


def assert_state(snapshot, page_state, message_state):
    assert snapshot["page_state"] == page_state
    assert snapshot["message_state"] == message_state


def test_required_profile_prompt_maps_to_explicit_page_and_message_state():
    session = FakeSession()
    workflow_state = {
        "mode": "team",
        "intent_type": "plan",
        "missing_info_status": "awaiting_profile",
        "final_report": "",
    }
    session.set("pending_missing_fields", ["goal", "weekly_mileage"])

    snapshot = build_coach_ui_snapshot(session.get, workflow_state)

    assert_state(snapshot, "awaiting_required_profile", "required_profile_prompt")
    assert snapshot["required_missing_count"] == 2


def test_enhancement_prompt_maps_to_plan_ready_with_enhancement():
    session = FakeSession()
    workflow_state = {
        "mode": "team",
        "intent_type": "plan",
        "missing_info_status": "",
        "final_report": "这里是一份基础计划",
    }
    session.set("pending_enhancement_fields", ["lthr", "t_pace", "vo2max"])

    snapshot = build_coach_ui_snapshot(session.get, workflow_state)

    assert_state(snapshot, "plan_ready_with_enhancement", "enhancement_prompt")
    assert snapshot["enhancement_missing_count"] == 3


def test_workflow_running_has_priority_over_ready_state():
    session = FakeSession()
    session.set("workflow_running", True)
    workflow_state = {
        "mode": "team",
        "intent_type": "plan",
        "final_report": "旧结果",
    }

    snapshot = build_coach_ui_snapshot(session.get, workflow_state)

    assert_state(snapshot, "workflow_running", "streaming_status")


def test_sync_snapshot_persists_labels_for_sidebar_render():
    session = FakeSession()
    workflow_state = {
        "mode": "team",
        "intent_type": "plan",
        "final_report": "这里是一份周计划",
    }
    session.set("pending_enhancement_fields", ["lthr"])

    snapshot = sync_coach_ui_snapshot(session.get, session.set, workflow_state)
    md = render_coach_ui_status_md(snapshot)

    assert session.get("coach_page_state") == "plan_ready_with_enhancement"
    assert session.get("coach_message_state") == "enhancement_prompt"
    assert "### 下一步" in md
    assert "补全高级画像" in md
    assert "待补高级字段" in md
    assert "`1`" in md


def test_state_flow_01_enter_coach_mode_defaults_to_idle_ready():
    session = FakeSession()

    snapshot = build_snapshot(session)

    assert_state(snapshot, "idle_ready", "welcome_ready")
    assert snapshot["chat_profile"] == "Coach Mode"
    assert snapshot["workflow_running"] is False
    assert "极速画像" in snapshot["next_step_hint"]


def test_state_flow_02_submit_plan_request_enters_workflow_running():
    session = FakeSession()
    session.set("workflow_running", True)
    session.set("last_error", None)
    workflow_state = {"mode": "team", "intent_type": "plan", "final_report": ""}

    snapshot = build_snapshot(session, workflow_state)

    assert_state(snapshot, "workflow_running", "streaming_status")
    assert snapshot["last_error"] is None


def test_state_flow_03_missing_required_profile_enters_required_prompt():
    session = FakeSession()
    session.set("pending_missing_fields", ["goal", "weekly_mileage", "available_days"])
    workflow_state = {
        "mode": "team",
        "intent_type": "plan",
        "missing_info_status": "awaiting_profile",
        "final_report": "",
    }

    snapshot = build_snapshot(session, workflow_state)

    assert_state(snapshot, "awaiting_required_profile", "required_profile_prompt")
    assert snapshot["missing_info_status"] == "awaiting_profile"
    assert snapshot["required_missing_count"] == 3
    assert "补齐后系统会自动继续生成基础计划" in snapshot["next_step_hint"]


def test_state_flow_04_required_field_input_is_tracked():
    session = FakeSession()
    session.set("pending_missing_fields", ["weekly_mileage", "available_days"])
    session.set("filling_field_key", "goal")
    session.set("filling_field_mode", "required")

    snapshot = build_snapshot(session)

    assert_state(snapshot, "filling_required_field", "field_input_prompt")
    assert snapshot["required_missing_count"] == 2


def test_state_flow_05_remaining_required_fields_keep_required_prompt():
    session = FakeSession()
    session.set("pending_missing_fields", ["available_days"])
    workflow_state = {
        "mode": "team",
        "intent_type": "plan",
        "missing_info_status": "awaiting_profile",
    }

    snapshot = build_snapshot(session, workflow_state)

    assert_state(snapshot, "awaiting_required_profile", "required_profile_prompt")
    assert snapshot["required_missing_count"] == 1


def test_state_flow_06_required_profile_completion_resumes_workflow():
    session = FakeSession()
    session.set("pending_plan_query", "帮我生成 4 周半马训练计划")
    session.set("pending_missing_fields", [])
    session.set("workflow_running", True)
    workflow_state = {"mode": "team", "intent_type": "plan", "missing_info_status": ""}

    snapshot = build_snapshot(session, workflow_state)

    assert_state(snapshot, "workflow_running", "streaming_status")
    assert snapshot["required_missing_count"] == 0


def test_state_flow_07_basic_plan_ready_with_enhancement_prompt():
    session = FakeSession()
    session.set("pending_enhancement_fields", ["lthr", "t_pace"])
    workflow_state = {
        "mode": "team",
        "intent_type": "plan",
        "missing_info_status": "",
        "final_report": "基础训练计划已生成",
    }

    snapshot = build_snapshot(session, workflow_state)

    assert_state(snapshot, "plan_ready_with_enhancement", "enhancement_prompt")
    assert snapshot["has_final_report"] is True
    assert snapshot["enhancement_missing_count"] == 2


def test_state_flow_08_single_enhancement_field_input_keeps_current_plan_context():
    session = FakeSession()
    session.set("pending_enhancement_fields", ["lthr"])
    session.set("filling_field_key", "lthr")
    session.set("filling_field_mode", "enhancement")
    workflow_state = {
        "mode": "team",
        "intent_type": "plan",
        "final_report": "当前计划仍在消息历史中",
    }

    snapshot = build_snapshot(session, workflow_state)

    assert_state(snapshot, "filling_enhancement_field", "field_input_prompt")
    assert snapshot["has_final_report"] is True
    assert snapshot["enhancement_missing_count"] == 1
    assert "保留当前计划" in snapshot["next_step_hint"]


def test_state_flow_09_enhancement_wizard_uses_wizard_prompt():
    session = FakeSession()
    session.set("profile_wizard_mode", "enhancement")
    session.set("profile_current_step", "lthr")
    session.set("profile_step_field_key", "lthr")

    snapshot = build_snapshot(session)

    assert_state(snapshot, "profile_wizard_enhancement", "wizard_prompt")
    assert snapshot["wizard_mode"] == "enhancement"


def test_state_flow_10_enhancement_completion_returns_to_plan_ready():
    session = FakeSession()
    session.set("pending_enhancement_fields", [])
    session.set("workflow_running", False)
    workflow_state = {
        "mode": "team",
        "intent_type": "plan",
        "final_report": "补全高级画像前生成的当前计划",
    }

    snapshot = build_snapshot(session, workflow_state)

    assert_state(snapshot, "plan_ready", "report_rendered")
    assert snapshot["enhancement_missing_count"] == 0


def test_state_flow_11_manual_regeneration_enters_workflow_running():
    session = FakeSession()
    session.set("pending_plan_query", "帮我基于最新画像重生成计划")
    session.set("workflow_running", True)
    session.set("last_error", None)
    workflow_state = {"mode": "team", "intent_type": "plan"}

    snapshot = build_snapshot(session, workflow_state)

    assert_state(snapshot, "workflow_running", "streaming_status")
    assert snapshot["last_error"] is None


def test_state_flow_12_regenerated_plan_ready_without_enhancement_fields():
    session = FakeSession()
    workflow_state = {
        "mode": "team",
        "intent_type": "plan",
        "final_report": "基于最新画像生成的新计划",
    }

    snapshot = build_snapshot(session, workflow_state)

    assert_state(snapshot, "plan_ready", "report_rendered")
    assert snapshot["has_final_report"] is True


def test_state_flow_12_regenerated_plan_ready_with_enhancement_fields():
    session = FakeSession()
    session.set("pending_enhancement_fields", ["vo2max"])
    workflow_state = {
        "mode": "team",
        "intent_type": "plan",
        "final_report": "基于最新画像生成的新计划",
    }

    snapshot = build_snapshot(session, workflow_state)

    assert_state(snapshot, "plan_ready_with_enhancement", "enhancement_prompt")
    assert snapshot["enhancement_missing_count"] == 1


def test_state_flow_13_error_fallback_has_priority_and_renders_error():
    session = FakeSession()
    session.set("workflow_running", False)
    session.set("last_error", "模拟异常")
    workflow_state = {"mode": "team", "intent_type": "plan", "final_report": "旧计划"}

    snapshot = sync_coach_ui_snapshot(session.get, session.set, workflow_state)
    md = render_coach_ui_status_md(snapshot)

    assert_state(snapshot, "error_fallback", "error_message")
    assert session.get("coach_page_state") == "error_fallback"
    assert session.get("last_error") == "模拟异常"
    assert "### 下一步" in md


def test_state_flow_14_non_coach_entry_does_not_show_coach_sidebar_status():
    session = FakeSession()
    session.set("chat_profile", "Research Mode")
    workflow_state = {"mode": "research", "intent_type": "qa", "final_report": "研究回答"}

    snapshot = build_snapshot(session, workflow_state)
    md = render_coach_ui_status_md(snapshot)

    assert_state(snapshot, "non_coach_mode", "report_rendered")
    assert md == ""
