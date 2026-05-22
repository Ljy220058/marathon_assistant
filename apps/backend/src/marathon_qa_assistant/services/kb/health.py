from __future__ import annotations

from typing import Any, Dict, List


CORE_ALLOWED_DOMAINS = {"protocol", "action_library"}


def _as_dict(binding: Any) -> Dict[str, Any]:
    if isinstance(binding, dict):
        return binding
    return {
        "source_path": getattr(binding, "source_path", ""),
        "source_file": getattr(binding, "source_file", ""),
        "page": getattr(binding, "page", None),
        "evidence_domain": getattr(getattr(binding, "evidence_domain", ""), "value", getattr(binding, "evidence_domain", "")),
        "prescription_permission": getattr(
            getattr(binding, "prescription_permission", ""),
            "value",
            getattr(binding, "prescription_permission", ""),
        ),
    }


def check_evidence_bindings_health(bindings: List[Any]) -> Dict[str, Any]:
    normalized = [_as_dict(binding) for binding in bindings]
    total = len(normalized)
    missing_source_count = sum(
        1 for item in normalized if not (str(item.get("source_path") or "").strip() or str(item.get("source_file") or "").strip())
    )
    missing_page_count = sum(1 for item in normalized if item.get("page") in {None, "", 0})
    core_permission_violation_count = sum(
        1
        for item in normalized
        if str(item.get("prescription_permission") or "") == "can_write_core"
        and str(item.get("evidence_domain") or "") not in CORE_ALLOWED_DOMAINS
    )

    if total == 0:
        status = "empty"
    elif missing_source_count or core_permission_violation_count:
        status = "needs_review"
    else:
        status = "ok"

    return {
        "total": total,
        "missing_source_count": missing_source_count,
        "missing_page_count": missing_page_count,
        "core_permission_violation_count": core_permission_violation_count,
        "status": status,
    }
