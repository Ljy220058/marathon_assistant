from __future__ import annotations

from typing import Any, Dict, List


CORE_ALLOWED_PERMISSIONS = {"can_write_core"}


def _as_dict(binding: Any) -> Dict[str, Any]:
    if isinstance(binding, dict):
        return binding
    return {
        "evidence_domain": getattr(getattr(binding, "evidence_domain", ""), "value", getattr(binding, "evidence_domain", "")),
        "prescription_permission": getattr(
            getattr(binding, "prescription_permission", ""),
            "value",
            getattr(binding, "prescription_permission", ""),
        ),
        "snippet": getattr(binding, "snippet", ""),
        "score": getattr(binding, "score", 0.0),
    }


def _snippet_supported(answer: str, evidence_bindings: List[Dict[str, Any]]) -> bool:
    answer_lower = str(answer or "").lower()
    for binding in evidence_bindings:
        snippet = str(binding.get("snippet") or "").strip().lower()
        if not snippet:
            continue
        tokens = [token for token in snippet.replace("-", " ").replace(".", " ").split() if len(token) >= 4]
        if tokens and any(token in answer_lower for token in tokens[:8]):
            return True
    return False


def evaluate_evidence_answer(
    question: str,
    answer: str,
    evidence_bindings: List[Any],
    core_fields: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    core_fields = core_fields or {}
    normalized_bindings = [_as_dict(binding) for binding in evidence_bindings]
    retrieval_hit = bool(normalized_bindings)
    source_coverage = 0.0 if not retrieval_hit else min(1.0, len(normalized_bindings) / 3.0)
    core_prescription_supported = not core_fields or any(
        str(binding.get("prescription_permission") or "") in CORE_ALLOWED_PERMISSIONS
        for binding in normalized_bindings
    )
    faithfulness_proxy = 1.0 if retrieval_hit and _snippet_supported(answer, normalized_bindings) else 0.0

    failure_modes: List[str] = []
    if not retrieval_hit:
        failure_modes.append("retrieval_miss")
    if retrieval_hit and faithfulness_proxy == 0.0:
        failure_modes.append("answer_unsupported")
    if not core_prescription_supported:
        failure_modes.append("core_prescription_missing_evidence")

    return {
        "question": question,
        "retrieval_hit": retrieval_hit,
        "context_precision_proxy": source_coverage,
        "source_coverage": source_coverage,
        "faithfulness_proxy": faithfulness_proxy,
        "core_prescription_supported": core_prescription_supported,
        "needs_review": bool(failure_modes),
        "failure_modes": failure_modes,
    }
