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
        has_plan_evidence = is_strength_query or (query_has_weekly and query_has_structure)
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

    if is_strength_query:
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

    # P0-4: QA 模式下营养类查询路由到 nutritionist 节点
    if state.get("category") == "nutritionist":
        return "nutritionist"

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

    # ── 裁判角色: 重试上限后强制放行，不阻塞输出 ──
    # 约定: auditor 最多审 3 次。之后无论结果，标注风险后直接输出。
    iteration_count = state.get("iteration_count", 0)
    if iteration_count >= 2:
        diagnosis = state.get("audit_diagnosis") or {}
        diag_summary = diagnosis.get("summary", "无诊断")
        logger.warning(
            f"[critic_auditor] 已审 {iteration_count} 轮，强制放行。诊断: {diag_summary}"
        )
        # 强制通过标记: 不绕 missing_info_handler，直接走 formatter
        state["is_approved"] = True
        state["review_feedback"] = (
            str(state.get("review_feedback") or "")
            + f"\n> 审计已执行 {iteration_count} 轮，剩余问题已标注，请自行判断。"
        )
        return "formatter"

    # P6: 分叉重试上限
    hard_retries = state.get("hard_rule_retry_count", 0)
    rag_retries = state.get("rag_audit_retry_count", 0)
    if hard_retries >= 1 or rag_retries >= 2:
        diagnosis = state.get("audit_diagnosis") or {}
        diag_summary = diagnosis.get("summary", "无诊断")
        logger.warning(
            f"[critic_auditor] 已达审计上限 "
            f"(hard={hard_retries}/1 rag={rag_retries}/2)，"
            f"强制放行。诊断: {diag_summary}"
        )
        state["is_approved"] = True
        state["review_feedback"] = (
            str(state.get("review_feedback") or "")
            + f"\n> 审计已达上限，剩余问题已标注，请自行判断。"
        )
        return "formatter"

    # P0-5: QA 模式下无证据时，审计未通过也直接走 formatter，避免重试死循环
    workflow_kind = state.get("workflow_kind") or state.get("intent_type") or "qa"
    if workflow_kind == "qa":
        evidence_bundle = state.get("evidence_bundle") if isinstance(state.get("evidence_bundle"), dict) else {}
        evidence_items = [item for item in (evidence_bundle.get("evidence_items") or []) if isinstance(item, dict)]
        if not evidence_items:
            logger.warning("[critic_auditor] QA 模式无证据，跳过重试，直接格式化输出")
            return "formatter"

    # AgentDoG P0: 从三元组诊断中提取定向修复建议，注入 state 供重试节点使用
    diagnosis = state.get("audit_diagnosis") or {}
    diagnoses = diagnosis.get("diagnoses") or []
    if diagnoses:
        targeted_fixes = [d.get("targeted_fix", "") for d in diagnoses if d.get("targeted_fix")]
        if targeted_fixes:
            fix_hint = "；".join(targeted_fixes[:3])
            existing_feedback = str(state.get("review_feedback") or "")
            if "定向修复" not in existing_feedback:
                state["review_feedback"] = f"{existing_feedback}\n[定向修复建议] {fix_hint}"

    if workflow_kind == "plan":
        # 计划骨架已生成但审计未放行时，直接格式化带审计说明的结果，避免 fallback 执行器反复重入 executor。
        if isinstance(state.get("structured_training_plan"), dict) and state.get("structured_training_plan"):
            return "formatter"
        return "executor"
    if workflow_kind == "research":
        return "research_analyst"
    if workflow_kind == "adaptive":
        return "adaptive_coach"
    return "coach"
