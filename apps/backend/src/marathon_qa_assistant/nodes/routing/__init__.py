import logging
import re
from typing import Any, Dict, List

from marathon_qa_assistant.core.state_models import IntegratedState

logger = logging.getLogger("workflow_engine")

WEEKLY_PATTERN = (
    r"("
    r"\u5468\u4e00|\u5468\u4e8c|\u5468\u4e09|\u5468\u56db|\u5468\u4e94|\u5468\u516d|\u5468\u65e5|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"mon\b|tue\b|wed\b|thu\b|fri\b|sat\b|sun\b|"
    r"\u7b2c\s*[1-9\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]+\s*\u5468|"
    r"week\s*\d+|session\s*\d+|workout\s*\d+|microcycle"
    r")"
)
PRESCRIPTION_PATTERN = (
    r"("
    r"\d+(\.\d+)?\s*(km|\u516c\u91cc|bpm|min/km|/km|\u5206\u949f|min|\u5c0f\u65f6|hour|hours)"
    r")"
)
STRUCTURE_PATTERN = r"(\d+\s*[xX*]\s*\d+|\u95f4\u6b47|\u91cd\u590d|\u5faa\u73af|\u7ec4\u6570)"
NUMERIC_PRESCRIPTION_PATTERN = r"(\d+[:\uFF1A]\d+\s*(min/km|/km)|[1-9]\d{1,2}\s*bpm)"
STRENGTH_QUERY_KEYWORDS = [
    "\u529b\u91cf",
    "\u52a8\u4f5c\u5e93",
    "\u6838\u5fc3",
    "\u4e13\u9879",
    "\u51b2\u5761",
]
TRAINING_PLAN_KEYWORDS = [
    "\u8bad\u7ec3\u8ba1\u5212",
    "\u5468\u8ba1\u5212",
    "\u8bfe\u8868",
    "\u5b89\u6392",
    "\u8ba1\u5212",
    "training plan",
    "weekly plan",
]
PLAN_DURATION_PATTERN = r"(\d+\s*(\u5468|weeks?)|week\s*\d+|macrocycle)"
RACE_GOAL_PATTERN = (
    r"("
    r"\u5168\u9a6c|\u534a\u9a6c|\u9a6c\u62c9\u677e|10k|5k|\u76ee\u6807|"
    r"sub\s*\d+|\d+\s*(\u5c0f\u65f6|hours?)|\d+[:\uFF1A]\d+"
    r")"
)


def _workflow_kind(state: IntegratedState) -> str:
    return str(state.get("workflow_kind") or state.get("intent_type") or "qa").strip().lower()


def _adaptive_adjustment_payload(state: IntegratedState) -> Dict[str, Any]:
    adjustment = state.get("adaptive_adjustment")
    return adjustment if isinstance(adjustment, dict) else {}


def _adaptive_envelope_ready(state: IntegratedState) -> bool:
    if _workflow_kind(state) != "adaptive":
        return False

    adaptation_type = str(state.get("adaptation_type") or "").strip().upper()
    adjustment = _adaptive_adjustment_payload(state)
    has_medical_constraints = isinstance(state.get("medical_constraints"), dict) and bool(state.get("medical_constraints"))
    therapist_reviewed = "therapist_passed" in state
    return bool(adaptation_type or adjustment or has_medical_constraints or therapist_reviewed)


def evaluate_plan_evidence(gate_hits: List[Dict[str, Any]], query: str, intent_type: str) -> Dict[str, Any]:
    if intent_type != "plan":
        return {"required": False, "has_plan_evidence": True}

    normalized_query = str(query or "").lower()
    is_strength_query = any(keyword.lower() in normalized_query for keyword in STRENGTH_QUERY_KEYWORDS)
    is_training_plan_request = any(keyword.lower() in normalized_query for keyword in TRAINING_PLAN_KEYWORDS)
    query_has_plan_duration = bool(re.search(PLAN_DURATION_PATTERN, normalized_query))
    query_has_race_goal = bool(re.search(RACE_GOAL_PATTERN, normalized_query))

    if not gate_hits:
        query_has_weekly = bool(re.search(WEEKLY_PATTERN, normalized_query))
        query_has_structure = (
            bool(re.search(PRESCRIPTION_PATTERN, normalized_query))
            or bool(re.search(STRUCTURE_PATTERN, normalized_query))
            or bool(re.search(NUMERIC_PRESCRIPTION_PATTERN, normalized_query))
        )
        query_is_explicit_macrocycle = is_training_plan_request and query_has_plan_duration and query_has_race_goal
        has_plan_evidence = is_strength_query or query_is_explicit_macrocycle or (query_has_weekly and query_has_structure)
        return {
            "required": True,
            "has_plan_evidence": has_plan_evidence,
            "has_weekly": query_has_weekly,
            "has_prescription": bool(re.search(PRESCRIPTION_PATTERN, normalized_query)),
            "has_structure": query_has_structure,
            "has_numeric_prescription": bool(re.search(NUMERIC_PRESCRIPTION_PATTERN, normalized_query)),
            "is_strength_query": is_strength_query,
            "is_training_plan_request": is_training_plan_request,
            "has_plan_duration": query_has_plan_duration,
            "has_race_goal": query_has_race_goal,
        }

    combined_text = "".join(str(hit.get("text", "")) for hit in gate_hits).lower()
    kb_has_weekly = bool(re.search(WEEKLY_PATTERN, combined_text))
    kb_has_prescription = bool(re.search(PRESCRIPTION_PATTERN, combined_text))
    kb_has_structure = bool(re.search(STRUCTURE_PATTERN, combined_text))
    kb_has_numeric = bool(re.search(NUMERIC_PRESCRIPTION_PATTERN, combined_text))

    query_has_weekly = bool(re.search(WEEKLY_PATTERN, normalized_query))
    query_has_prescription = bool(re.search(PRESCRIPTION_PATTERN, normalized_query))
    query_has_structure = bool(re.search(STRUCTURE_PATTERN, normalized_query))
    query_has_numeric = bool(re.search(NUMERIC_PRESCRIPTION_PATTERN, normalized_query))
    query_is_explicit_macrocycle = is_training_plan_request and query_has_plan_duration and query_has_race_goal

    has_weekly = kb_has_weekly or query_has_weekly
    has_prescription = kb_has_prescription or query_has_prescription
    has_structure = kb_has_structure or query_has_structure
    has_numeric_prescription = kb_has_numeric or query_has_numeric

    if is_strength_query:
        has_plan_evidence = True
    else:
        has_plan_evidence = query_is_explicit_macrocycle or (
            has_weekly and (has_prescription or has_structure or has_numeric_prescription)
        )

    return {
        "required": True,
        "has_plan_evidence": has_plan_evidence,
        "has_weekly": has_weekly,
        "has_prescription": has_prescription,
        "has_structure": has_structure,
        "has_numeric_prescription": has_numeric_prescription,
        "is_strength_query": is_strength_query,
        "is_training_plan_request": is_training_plan_request,
        "has_plan_duration": query_has_plan_duration,
        "has_race_goal": query_has_race_goal,
    }


def gate_decision(state: IntegratedState) -> str:
    if state.get("mode") == "intercepted":
        return "blocked"
    return "router"


async def supervisor_node(state: IntegratedState, config=None) -> Dict[str, Any]:
    del config
    decision = after_supervisor_route(state)
    from datetime import datetime, timezone

    return {
        "supervisor_decision": decision,
        "reasoning_log": [f"[supervisor] next={decision}"],
        "execution_trace": [
            {
                "node": "supervisor",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "input_snapshot": {
                    "workflow_kind": state.get("workflow_kind") or state.get("intent_type"),
                    "category": state.get("category", ""),
                    "has_audit_diagnosis": bool(state.get("audit_diagnosis")),
                    "s_and_c_done": bool(state.get("s_and_c_done")),
                    "is_adaptive_workflow": _workflow_kind(state) == "adaptive",
                },
                "output_snapshot": {"next": decision},
                "decision": f"dispatch_to_{decision}",
            }
        ],
    }


def after_supervisor_route(state: IntegratedState) -> str:
    if state.get("missing_fields"):
        return "missing_info_handler"

    workflow_kind = _workflow_kind(state)
    if workflow_kind == "adaptive":
        return "adaptive_coach"
    if workflow_kind == "plan":
        return "planner"
    return "coach"


def after_conditioning_route(state: IntegratedState) -> str:
    if _adaptive_envelope_ready(state):
        return "planner"
    return "supervisor"


def after_planner_route(state: IntegratedState) -> str:
    if not state.get("subtasks"):
        raise RuntimeError("planner produced no subtasks; missing information should have been intercepted before supervisor")
    return "executor"


def after_executor_route(state: IntegratedState) -> str:
    return "nutritionist"


def after_adaptive_coach_route(state: IntegratedState) -> str:
    adaptation_type = str(state.get("adaptation_type") or "").strip().upper()
    adjustment = _adaptive_adjustment_payload(state)
    if not adaptation_type:
        adaptation_type = str(adjustment.get("adaptation_type") or "").strip().upper()
    if adaptation_type in {"INJURY", "FATIGUE"} or state.get("needs_therapist_review"):
        return "therapist"
    return "conditioning_constraints"


def after_router_route(state: IntegratedState) -> str:
    return "context_fanout"


def after_context_fanout_route(state: IntegratedState) -> str:
    del state
    return "evidence_retriever"


def after_rule_checker_route(state: IntegratedState) -> str:
    if isinstance(state.get("workflow_error"), dict) and state.get("workflow_error"):
        return "workflow_error"
    rule_check = state.get("rule_check_result") if isinstance(state.get("rule_check_result"), dict) else {}
    if rule_check and not bool(rule_check.get("passed")):
        return "workflow_error"
    return "critic_auditor"


def after_critic_auditor_route(state: IntegratedState) -> str:
    if isinstance(state.get("workflow_error"), dict) and state.get("workflow_error"):
        return "workflow_error"
    if state.get("is_approved"):
        return "safety_out"

    iteration_count = int(state.get("iteration_count", 0) or 0)
    diagnosis = state.get("audit_diagnosis") if isinstance(state.get("audit_diagnosis"), dict) else {}
    diag_summary = str(diagnosis.get("summary") or "no diagnosis")
    audit_verdict = str(state.get("audit_verdict") or "").strip().lower()

    hard_retries = int(state.get("hard_rule_retry_count", 0) or 0)
    rag_retries = int(state.get("rag_audit_retry_count", 0) or 0)
    if audit_verdict == "fail" or iteration_count >= 2 or hard_retries >= 1 or rag_retries >= 2:
        logger.warning(
            "[critic_auditor] fail loud after retry budget exhausted "
            "(iterations=%s hard=%s rag=%s): %s",
            iteration_count,
            hard_retries,
            rag_retries,
            diag_summary,
        )
        state["workflow_error"] = {
            "status": "failed",
            "error_code": "AUDIT_RETRY_EXHAUSTED",
            "node": "critic_auditor",
            "message": "审计重试次数已耗尽，工作流终止。",
            "diagnosis": diagnosis,
            "iteration_count": iteration_count,
        }
        return "workflow_error"

    diagnoses = diagnosis.get("diagnoses") if isinstance(diagnosis.get("diagnoses"), list) else []
    targeted_fixes = [
        str(item.get("targeted_fix") or "")
        for item in diagnoses
        if isinstance(item, dict) and item.get("targeted_fix")
    ]
    if targeted_fixes:
        fix_hint = "; ".join(targeted_fixes[:3])
        existing_feedback = str(state.get("review_feedback") or "")
        if "[targeted_fix]" not in existing_feedback:
            state["review_feedback"] = f"{existing_feedback}\n[targeted_fix] {fix_hint}".strip()

    return "supervisor"


__all__ = [
    "after_adaptive_coach_route",
    "after_conditioning_route",
    "after_context_fanout_route",
    "after_critic_auditor_route",
    "after_executor_route",
    "after_planner_route",
    "after_rule_checker_route",
    "after_router_route",
    "after_supervisor_route",
    "evaluate_plan_evidence",
    "gate_decision",
    "supervisor_node",
]
