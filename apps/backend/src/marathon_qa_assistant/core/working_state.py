from __future__ import annotations

from typing import Any, Dict, List, Optional

from marathon_qa_assistant.core.kb_bootstrap import get_knowledge_base_health_snapshot
from marathon_qa_assistant.core.state_models import WorkingState


def build_working_state(
    *,
    query: str = "",
    user_profile: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, str]]] = None,
    adaptive_feedback: Optional[Dict[str, Any]] = None,
    kb_health: Optional[Dict[str, Any]] = None,
) -> WorkingState:
    """为每轮请求构造干净运行态，避免上一轮 mode/draft/approval 污染。"""

    health = kb_health if isinstance(kb_health, dict) else get_knowledge_base_health_snapshot()
    return {
        "query": str(query or ""),
        "mode": "team",
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
        "final_report": "",
        "structured_training_plan": None,
        "structured_report": None,
        "reasoning_log": [],
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
        "graph_context": "",
        "wiki_context": "",
        "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "audit_scores": {"consistency": 0, "safety": 0, "roi": 0, "summary": "", "score_sources": {}},
        "roi_history": [],
        "risk_alert": "",
        "entities": [],
        "mermaid_graph": "",
        "guided_questions": [],
        "user_profile": user_profile or {},
        "adaptive_feedback": adaptive_feedback or {},
        "adaptive_adjustment": {},
        "workflow_trace": {},
        "requested_weeks": None,
        "missing_fields": [],
        "enhancement_missing_fields": [],
        "missing_info_status": "",
        "history": list(history or []),
        "used_fallback": False,
        "fallback_reason": "",
        "validation_result": {},
        "repair_suggestions": [],
        "repair_attempts": 0,
        "nutritionist_done": False,
        "needs_nutrition_review": False,
    }


__all__ = ["build_working_state"]
