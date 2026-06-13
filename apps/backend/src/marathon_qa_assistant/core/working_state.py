from __future__ import annotations

from typing import Any, Dict, List, Optional

from marathon_qa_assistant.core.kb_bootstrap import get_knowledge_base_health_snapshot
from marathon_qa_assistant.core.state_models import WorkingState


def build_working_state(
    *,
    query: str = "",
    mode: str = "",
    user_profile: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, str]]] = None,
    adaptive_feedback: Optional[Dict[str, Any]] = None,
    kb_health: Optional[Dict[str, Any]] = None,
) -> WorkingState:
    """为每轮请求构造干净运行态，避免上一轮 mode/draft/approval 污染。"""

    health = kb_health if isinstance(kb_health, dict) else get_knowledge_base_health_snapshot()
    # P1-1: 使用 API 传来的 mode 参数，非空时不再硬编码 "team"；router_node 可后续覆写
    effective_mode = str(mode).strip() if mode else "team"
    return {
        "query": str(query or ""),
        "mode": effective_mode,
        "intent_labels": [],
        "intent_priority": "",
        "workflow_kind": "",
        "intent_type": "qa",
        "selected_entities": [],
        "category": "",
        "subtasks": [],
        "draft_plan": "",
        "draft_ready": False,
        "review_feedback": "",
        "is_approved": False,
        "iteration_count": 0,
        "node_visit_count": {},
        "final_report": "",
        "structured_training_plan": None,
        "structured_report": None,
        "reasoning_log": [],
        "execution_trace": [],  # AgentDoG P0: 结构化节点执行轨迹
        "audit_diagnosis": {},  # AgentDoG P0: 三元组诊断
        "safety_constraints": [],  # P1: KG 安全约束
        "training_capacity_envelope": {},
        "s_and_c_constraints": {},
        "s_and_c_done": False,
        "needs_therapist_review": False,
        "gate_hits": [],
        "rag_sources": [],
        "ranked_evidence": [],
        "evidence_bundle": {
            "query": str(query or ""),
            "evidence_items": [],
            "health": {
                "kb_ready": bool(health.get("ready") or health.get("ok")),
                "source": str(health.get("source") or health.get("mode") or ""),
                "chunks_count": int(health.get("chunks_count") or 0),
                "faiss_ready": bool(health.get("faiss_ready")),
            },
        },
        "expert_evidence_trace": {},
        "graph_context": "",
        "wiki_context": "",
        "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "rule_check_result": {},
        "audit_scores": {"consistency": 0, "safety": 0, "roi": 0, "summary": "", "score_sources": {}},
        "roi_history": [],
        "risk_alert": "",
        "entities": [],
        "mermaid_graph": "",
        "guided_questions": [],
        "user_profile": user_profile or {},
        "adaptive_feedback": adaptive_feedback or {},
        "adaptive_adjustment": {},
        "adaptation_type": "",
        "adaptation_context": {},
        "workflow_trace": {},
        "supervisor_decision": "",
        "requested_weeks": None,
        "missing_fields": [],
        "enhancement_missing_fields": [],
        "missing_info_status": "",
        "workflow_pause": {},
        "workflow_error": {},
        "history": list(history or []),
        "used_fallback": False,
        "fallback_reason": "",
        "validation_result": {},
        "repair_suggestions": [],
        "repair_attempts": 0,
        "nutritionist_done": False,
        "needs_nutrition_review": False,
        "psychologist_done": False,
        "needs_psychology_review": False,
    }


__all__ = ["build_working_state"]
