from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from marathon_qa_assistant.core.state_models import IntegratedState
from marathon_qa_assistant.core.strength_conditioning_constraints import build_training_capacity_envelope
from marathon_qa_assistant.nodes.common import ensure_usage

try:
    from langchain_core.runnables import RunnableConfig
except Exception:  # pragma: no cover
    RunnableConfig = Any  # type: ignore


def _trace_step(state: IntegratedState, envelope: Dict[str, Any]) -> Dict[str, Any]:
    flags = [item for item in envelope.get("capacity_risk_flags") or [] if isinstance(item, dict)]
    ceiling = envelope.get("load_ceiling") if isinstance(envelope.get("load_ceiling"), dict) else {}
    return {
        "node": "conditioning_constraints",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_snapshot": {
            "workflow_kind": state.get("workflow_kind") or state.get("intent_type"),
            "has_profile": bool(state.get("user_profile")),
            "ranked_evidence_count": len(state.get("ranked_evidence") or []),
            "has_medical_constraints": bool(state.get("medical_constraints")),
        },
        "output_snapshot": {
            "weekly_load_cap_km": ceiling.get("weekly_load_cap_km"),
            "max_long_run_km": ceiling.get("max_long_run_km"),
            "quality_sessions_max": ceiling.get("quality_sessions_max"),
            "capacity_flag_count": len(flags),
        },
        "decision": "S&C capacity envelope generated before planner/executor",
    }


def _conditioning_expert_trace(envelope: Dict[str, Any]) -> Dict[str, Any]:
    evidence_refs = [ref for ref in envelope.get("evidence_refs") or [] if str(ref or "").strip()]
    return {
        "role": "conditioning_constraints",
        "status": "verified" if evidence_refs else "needs_evidence",
        "evidence_refs": evidence_refs,
        "note": "S&C capacity envelope is derived from knowledge-base evidence and profile signals.",
    }


async def conditioning_constraints_node(state: IntegratedState, config: RunnableConfig) -> Dict[str, Any]:
    del config
    envelope = build_training_capacity_envelope(
        profile=state.get("user_profile") or {},
        query=state.get("query", ""),
        ranked_evidence=state.get("ranked_evidence") or [],
        medical_constraints=state.get("medical_constraints") if isinstance(state.get("medical_constraints"), dict) else None,
        current_plan=state.get("structured_training_plan") if isinstance(state.get("structured_training_plan"), dict) else None,
    )
    flags = [item for item in envelope.get("capacity_risk_flags") or [] if isinstance(item, dict)]
    needs_therapist = any(item.get("code") == "requires_therapist_review" for item in flags)
    return {
        "training_capacity_envelope": envelope,
        "s_and_c_constraints": envelope,
        "s_and_c_done": True,
        "needs_therapist_review": needs_therapist,
        "expert_evidence_trace": {
            **(state.get("expert_evidence_trace") if isinstance(state.get("expert_evidence_trace"), dict) else {}),
            "conditioning_constraints": _conditioning_expert_trace(envelope),
        },
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": [
            "[conditioning_constraints] 已生成 S&C 训练容量边界",
            "[conditioning_constraints] 检测到医疗/疼痛信号，交由 therapist 边界处理" if needs_therapist else "[conditioning_constraints] 未检测到需要 therapist 接管的红旗",
        ],
        "execution_trace": [_trace_step(state, envelope)],
    }


__all__ = ["conditioning_constraints_node"]
