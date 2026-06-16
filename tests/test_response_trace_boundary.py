from marathon_qa_assistant.apps.response_builders import _query_response_from_state
from marathon_qa_assistant.apps.schemas import QueryRequest


def test_query_response_keeps_workflow_trace_out_of_structured_training_plan():
    result = {
        "final_report": "结构化计划已生成。",
        "workflow_kind": "plan",
        "intent_type": "plan",
        "token_usage": {},
        "audit_scores": {},
        "guided_questions": [],
        "structured_training_plan": {
            "plan_meta": {"goal": "半马 PB", "actual_weeks": 4},
            "week_plans": [{"week_index": 1, "days": [{"day": "周二", "training_type": "轻松跑", "main_set": "30分钟轻松跑"}]}],
        },
        "evidence_bundle": {"evidence_items": [], "health": {"ready": False, "source": "empty"}},
    }

    response = _query_response_from_state(
        result,
        QueryRequest(query="请生成 4 周半马训练计划", response_mode="skeleton", timeout_sec=10),
        generation_status="skeleton_ready",
    )

    assert response.workflow_trace
    assert "workflow_trace" not in (response.structured_training_plan or {})


def test_query_response_marks_plan_persist_failure_in_workflow_trace(monkeypatch):
    class FailingDb:
        def save_training_plan(self, *_args, **_kwargs):
            raise RuntimeError("db boom")

    monkeypatch.setattr("marathon_qa_assistant.apps.response_builders.get_db", lambda: FailingDb())

    result = {
        "final_report": "结构化计划已生成。",
        "workflow_kind": "plan",
        "intent_type": "plan",
        "token_usage": {},
        "audit_scores": {},
        "guided_questions": [],
        "structured_training_plan": {
            "plan_meta": {"goal": "半马 PB", "actual_weeks": 4},
            "week_plans": [{"week_index": 1, "days": [{"day": "周二", "training_type": "轻松跑", "main_set": "30分钟轻松跑"}]}],
        },
        "evidence_bundle": {"evidence_items": [], "health": {"ready": False, "source": "empty"}},
        "workflow_trace": {},
    }

    response = _query_response_from_state(
        result,
        QueryRequest(query="请生成 4 周半马训练计划", response_mode="skeleton", timeout_sec=10),
        generation_status="skeleton_ready",
    )

    assert response.training_plan_id is None
    assert response.workflow_trace["persistence"]["plan_save_status"] == "failed"
