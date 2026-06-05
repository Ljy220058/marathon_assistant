import copy
from typing import Any, Dict, List, Optional

from marathon_qa_assistant.apps.schemas import QueryResponse, TrainingCalendarResponse


_RUNNER_EXPERT_ONLY_NESTED_KEYS = {
    "content_json",
    "protocol_recheck",
    "workflow_trace",
    "trace",
    "raw_text",
    "expert_metadata",
    "source_registry_id",
    "retrieval_mode",
    "score",
    "source_path",
    "local_path",
    "chunk_id",
    "rag_eval",
    "source_quality",
}


def _response_payload(value: Any) -> Dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return dict(value or {})


def _drop_expert_keys_deep(value: Any, keys: Optional[set] = None) -> Any:
    blocked = keys or _RUNNER_EXPERT_ONLY_NESTED_KEYS
    if isinstance(value, dict):
        return {
            key: _drop_expert_keys_deep(item, blocked)
            for key, item in value.items()
            if key not in blocked
        }
    if isinstance(value, list):
        return [_drop_expert_keys_deep(item, blocked) for item in value]
    return value


def _public_risk_gate(risk_gate: Dict[str, Any]) -> Dict[str, Any]:
    gate = risk_gate if isinstance(risk_gate, dict) else {}
    return {
        key: gate.get(key)
        for key in ("status", "product_status", "adjustment_action", "decision_reason", "triggers")
        if gate.get(key) not in (None, "", [])
    }


def _public_protocol_recheck(protocol_recheck: Dict[str, Any]) -> Dict[str, Any]:
    recheck = protocol_recheck if isinstance(protocol_recheck, dict) else {}
    return {
        "allowed": bool(recheck.get("allowed", True)),
        "risk_gate_status": str(recheck.get("risk_gate_status") or ""),
    }


def _project_runner_training_plan_review(review: Dict[str, Any]) -> Dict[str, Any]:
    public_review = _drop_expert_keys_deep(copy.deepcopy(review or {}))
    summary = public_review.get("summary")
    if isinstance(summary, dict):
        summary["review_scope"] = [
            item
            for item in summary.get("review_scope", [])
            if str(item) not in {"field_sources", "workflow_trace", "risk_gate", "protocol_recheck"}
        ]
    return public_review


def _public_day_card_contract(day: Dict[str, Any]) -> Dict[str, Any]:
    return _drop_expert_keys_deep(copy.deepcopy(day or {}))


def _project_runner_query_response(response: QueryResponse) -> Dict[str, Any]:
    payload = _response_payload(response)
    payload["workflow_trace"] = {}
    payload["token_usage"] = {}
    payload["audit_scores"] = {}
    payload["half_marathon_protocol_validation"] = None
    for key in (
        "structured_training_plan",
        "structured_report",
        "training_explanation_panel",
        "monthly_training_calendar",
        "daily_schedule_cards",
        "phases",
        "training_load_summary",
    ):
        value = payload.get(key)
        if key == "daily_schedule_cards" and isinstance(value, list):
            payload[key] = [_public_day_card_contract(item) for item in value]
        else:
            payload[key] = _drop_expert_keys_deep(value)
    payload["training_plan_review"] = _project_runner_training_plan_review(payload.get("training_plan_review") or {})
    payload["evidence_chain"] = _drop_expert_keys_deep(payload.get("evidence_chain") or {})
    return payload


def _project_query_response_for_role(response: QueryResponse, role: str) -> Any:
    if role == "expert":
        return response
    return _project_runner_query_response(response)


def _project_runner_feedback_summary(feedback: Dict[str, Any]) -> Dict[str, Any]:
    latest = feedback if isinstance(feedback, dict) else {}
    allowed_keys = {
        "id",
        "feedback_id",
        "event_id",
        "plan_id",
        "completion_status",
        "completion_quality",
        "subjective_fatigue",
        "pain_status",
        "sleep_quality",
        "notes",
        "reason_codes",
        "next_day_adjustment",
        "weekly_adjustment",
        "alternative_workout",
        "risk_alert",
        "rationale",
        "created_at",
    }
    return {
        key: _drop_expert_keys_deep(value)
        for key, value in latest.items()
        if key in allowed_keys and value not in (None, "")
    }


def _project_runner_feedback_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    projected = copy.deepcopy(payload)
    projected["risk_gate"] = _public_risk_gate(projected.get("risk_gate") or {})
    projected["protocol_recheck"] = _public_protocol_recheck(projected.get("protocol_recheck") or {})
    adaptive_feedback = projected.get("adaptive_feedback") if isinstance(projected.get("adaptive_feedback"), dict) else {}
    projected["adaptive_feedback"] = {
        key: _drop_expert_keys_deep(value)
        for key, value in adaptive_feedback.items()
        if key in {"reason_codes", "reasons", "source"}
    }
    projected["workflow_trace"] = {}
    return projected


def _project_feedback_response_for_role(payload: Dict[str, Any], role: str) -> Dict[str, Any]:
    if role == "expert":
        return payload
    return _project_runner_feedback_response(payload)


def _project_runner_plan_event(event: Dict[str, Any]) -> Dict[str, Any]:
    projected = _drop_expert_keys_deep(copy.deepcopy(event or {}))
    latest = event.get("latest_feedback") if isinstance(event, dict) else None
    if isinstance(latest, dict):
        projected["latest_feedback"] = _project_runner_feedback_summary(latest)
    return projected


def _project_runner_adjustment_history(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    projected = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        public_item = {
            key: _drop_expert_keys_deep(value)
            for key, value in item.items()
            if key not in {"risk_gate", "protocol_recheck"}
        }
        projected.append(public_item)
    return projected


def _project_runner_plan_detail_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    projected = copy.deepcopy(payload)
    plan = dict(projected.get("plan") or {})
    plan.pop("structured_plan_json", None)
    projected["plan"] = plan
    projected["structured_training_plan"] = _drop_expert_keys_deep(projected.get("structured_training_plan") or {})
    projected["workflow_trace"] = {}
    projected["events"] = [_project_runner_plan_event(event) for event in projected.get("events") or []]
    projected["adjustment_history"] = _project_runner_adjustment_history(projected.get("adjustment_history") or [])
    projected["execution_status_summary"] = _drop_expert_keys_deep(projected.get("execution_status_summary") or {})
    projected["training_plan_review"] = _project_runner_training_plan_review(projected.get("training_plan_review") or {})
    projected["evidence_chain"] = _drop_expert_keys_deep(projected.get("evidence_chain") or {})
    return projected


def _project_plan_detail_response_for_role(payload: Dict[str, Any], role: str) -> Dict[str, Any]:
    if role == "expert":
        return payload
    return _project_runner_plan_detail_response(payload)


def _project_runner_training_calendar_response(response: TrainingCalendarResponse) -> Dict[str, Any]:
    payload = _response_payload(response)
    for key in ("days", "phases", "monthly_training_calendar", "daily_schedule_cards", "training_load_summary"):
        payload[key] = _drop_expert_keys_deep(payload.get(key))
    payload["training_plan_review"] = _project_runner_training_plan_review(payload.get("training_plan_review") or {})
    payload["evidence_chain"] = _drop_expert_keys_deep(payload.get("evidence_chain") or {})
    return payload


def _project_training_calendar_response_for_role(response: TrainingCalendarResponse, role: str) -> Any:
    if role == "expert":
        return response
    return _project_runner_training_calendar_response(response)
