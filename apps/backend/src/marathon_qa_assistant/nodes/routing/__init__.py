import logging
import re
from typing import Any, Dict, List

from marathon_qa_assistant.core.state_models import IntegratedState

logger = logging.getLogger("workflow_engine")

WEEKLY_PATTERN = r"(周[一二三四五六日]|monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon\b|tue\b|wed\b|thu\b|fri\b|sat\b|sun\b|第\s*[1-9一二三四五六七八九十]+\s*周|day\s*\d+|session\s*\d+|workout\s*\d+|microcycle)"
PRESCRIPTION_PATTERN = r"(\d+(\.\d+)?\s*(km|公里|公里/小时|bpm|次/分)|[1-9]\d{0,2}[:：][0-5]\d\s*(min/km|/km|配速)?)"
STRUCTURE_PATTERN = r"(\d+\s*[xX*脳]\s*\d+|间歇|重复|循环|组数)"
NUMERIC_PRESCRIPTION_PATTERN = r"\d+[:：]\d+\s*(min/km|/km)|[1-9]\d{1,2}\s*bpm"
STRENGTH_QUERY_KEYWORDS = ["力量", "动作库", "核心", "专项", "冲坡"]
TRAINING_PLAN_KEYWORDS = ["训练计划", "周计划", "课表", "安排", "计划"]


def evaluate_plan_evidence(gate_hits: List[Dict[str, Any]], query: str, intent_type: str) -> Dict[str, Any]:
    if intent_type != "plan":
        return {"required": False, "has_plan_evidence": True}

    normalized_query = (query or "").lower()
    is_strength_query = any(keyword in normalized_query for keyword in STRENGTH_QUERY_KEYWORDS)
    is_training_plan_request = any(keyword in normalized_query for keyword in TRAINING_PLAN_KEYWORDS)

    if not gate_hits:
        query_has_weekly = bool(re.search(WEEKLY_PATTERN, normalized_query))
        query_has_structure = (bool(re.search(PRESCRIPTION_PATTERN, normalized_query))
                               or bool(re.search(STRUCTURE_PATTERN, normalized_query))
                               or bool(re.search(NUMERIC_PRESCRIPTION_PATTERN, normalized_query)))
        has_plan_evidence = is_strength_query or is_training_plan_request or (query_has_weekly and query_has_structure)
        return {
            "required": True,
            "has_plan_evidence": has_plan_evidence,
            "has_weekly": query_has_weekly,
            "has_prescription": bool(re.search(PRESCRIPTION_PATTERN, normalized_query)),
            "has_structure": query_has_structure,
            "has_numeric_prescription": bool(re.search(NUMERIC_PRESCRIPTION_PATTERN, normalized_query)),
            "is_strength_query": is_strength_query,
            "is_training_plan_request": is_training_plan_request,
        }

    combined_text = "".join(hit.get("text", "") for hit in gate_hits).lower()
    kb_has_weekly = bool(re.search(WEEKLY_PATTERN, combined_text))
    kb_has_prescription = bool(re.search(PRESCRIPTION_PATTERN, combined_text))
    kb_has_structure = bool(re.search(STRUCTURE_PATTERN, combined_text))
    kb_has_numeric = bool(re.search(NUMERIC_PRESCRIPTION_PATTERN, combined_text))

    query_has_weekly = bool(re.search(WEEKLY_PATTERN, normalized_query))
    query_has_prescription = bool(re.search(PRESCRIPTION_PATTERN, normalized_query))
    query_has_structure = bool(re.search(STRUCTURE_PATTERN, normalized_query))
    query_has_numeric = bool(re.search(NUMERIC_PRESCRIPTION_PATTERN, normalized_query))

    has_weekly = kb_has_weekly or query_has_weekly
    has_prescription = kb_has_prescription or query_has_prescription
    has_structure = kb_has_structure or query_has_structure
    has_numeric_prescription = kb_has_numeric or query_has_numeric

    if is_strength_query or is_training_plan_request:
        has_plan_evidence = True
    else:
        has_plan_evidence = has_weekly and (has_prescription or has_structure or has_numeric_prescription)

    return {
        "required": True,
        "has_plan_evidence": has_plan_evidence,
        "has_weekly": has_weekly,
        "has_prescription": has_prescription,
        "has_structure": has_structure,
        "has_numeric_prescription": has_numeric_prescription,
        "is_strength_query": is_strength_query,
        "is_training_plan_request": is_training_plan_request,
    }


def gate_decision(state: IntegratedState):
    if state.get("mode") == "intercepted":
        return "formatter"
    return "router"


def entity_route_decision(state: IntegratedState):
    if state.get("missing_fields"):
        return "missing_info_handler"

    gate_hits = state.get("gate_hits", [])
    evidence = evaluate_plan_evidence(gate_hits, state.get("query", ""), state.get("intent_type", "qa"))
    is_plan_missing_evidence = evidence.get("required", False) and not evidence.get("has_plan_evidence", True)

    if is_plan_missing_evidence and state.get("mode") != "research":
        return "missing_info_handler"

    workflow_kind = state.get("workflow_kind") or state.get("intent_type")
    if workflow_kind == "research":
        return "research_analyst"
    if workflow_kind == "adaptive":
        return "adaptive_coach"
    if workflow_kind == "plan":
        return "planner"
    return "coach"


def after_planner_route(state: IntegratedState):
    if not state.get("subtasks"):
        return "missing_info_handler"
    return "executor"


def after_executor_route(state: IntegratedState):
    """训练计划生成后，若包含长距离训练日 (>=90min)，先路由到营养师再审计。"""
    if state.get("needs_nutrition_review") and not state.get("nutritionist_done"):
        return "nutritionist"
    return "critic_auditor"


def after_therapist_route(state: IntegratedState):
    if state.get("category") == "nutritionist" and not state.get("nutritionist_done"):
        return "nutritionist"
    return "critic_auditor"


def after_router_route(state: IntegratedState):
    """根据意图类型决定跳转到画像更新节点还是传统提取节点"""
    if state.get("intent_type") == "profile_update":
        return "profile_update"
    return "profiler"


def after_profile_update_route(state: IntegratedState):
    """画像更新节点后的路由：如果已更新则跳到格式化，否则进入传统流程"""
    if state.get("profile_update__is_update"):
        return "formatter"
    return "profiler"


def after_critic_auditor_route(state: IntegratedState):
    if state.get("is_approved"):
        return "formatter"

    if state.get("iteration_count", 0) >= 2:
        logger.warning(f"[critic_auditor] 已达最大审计迭代次数 ({state['iteration_count']})，强制转入引导节点")
        return "missing_info_handler"

    if (state.get("workflow_kind") or state.get("intent_type")) == "plan":
        return "executor"
    if (state.get("workflow_kind") or state.get("intent_type")) == "research":
        return "research_analyst"
    if (state.get("workflow_kind") or state.get("intent_type")) == "adaptive":
        return "adaptive_coach"
    return "coach"
