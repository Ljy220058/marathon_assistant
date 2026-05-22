from __future__ import annotations

import threading
from collections import Counter
from typing import Any, Dict, Optional


_LOCK = threading.Lock()
_REQUEST_COUNTS = Counter()
_GENERATION_STATUS_COUNTS = Counter()
_FEEDBACK_RISK_REASON_COUNTS = Counter()
_PLAN_DURATION_BUCKETS = Counter()
_LLM_PROVIDER_ERROR_COUNTS = Counter()
_MEDICAL_REFERRAL_TOTAL = 0


def _duration_bucket(duration_sec: Optional[float]) -> str:
    if duration_sec is None:
        return "unknown"
    if duration_sec < 1:
        return "lt_1s"
    if duration_sec < 5:
        return "lt_5s"
    if duration_sec < 30:
        return "lt_30s"
    return "gte_30s"


def route_template(path: str) -> str:
    normalized = str(path or "/").strip() or "/"
    parts = []
    for part in normalized.split("/"):
        if not part:
            continue
        if _looks_dynamic_path_segment(part):
            parts.append("{id}")
        else:
            parts.append(part)
    return "/" + "/".join(parts)


def _looks_dynamic_path_segment(part: str) -> bool:
    value = str(part or "").strip()
    if not value:
        return False
    if len(value) >= 24 and any(ch.isdigit() for ch in value) and any(ch.isalpha() for ch in value):
        return True
    if len(value) >= 8 and "-" in value and any(ch.isdigit() for ch in value):
        return True
    return value.isdigit()


def record_request(*, method: str, path: str, status_code: int, duration_ms: float, error_type: str = "") -> None:
    with _LOCK:
        _REQUEST_COUNTS["requests_total"] += 1
        if status_code >= 500 or error_type:
            _REQUEST_COUNTS["errors_total"] += 1
        _REQUEST_COUNTS[f"status_{status_code}"] += 1
        _REQUEST_COUNTS[f"{method.upper()} {route_template(path)}"] += 1


def record_generation_status(status: str, *, duration_sec: Optional[float] = None) -> None:
    normalized = str(status or "unknown").strip() or "unknown"
    with _LOCK:
        _GENERATION_STATUS_COUNTS[normalized] += 1
        _PLAN_DURATION_BUCKETS[_duration_bucket(duration_sec)] += 1


def record_feedback_risk(risk_gate: Dict[str, Any]) -> None:
    global _MEDICAL_REFERRAL_TOTAL
    gate = risk_gate if isinstance(risk_gate, dict) else {}
    triggers = gate.get("triggers") or []
    product_status = str(gate.get("product_status") or "")
    with _LOCK:
        for trigger in triggers:
            _FEEDBACK_RISK_REASON_COUNTS[str(trigger)] += 1
        if product_status == "medical_referral":
            _MEDICAL_REFERRAL_TOTAL += 1


def record_llm_provider_error(provider: str, error_code: str) -> None:
    safe_provider = str(provider or "unknown").strip().lower() or "unknown"
    safe_code = str(error_code or "provider_error").strip().lower() or "provider_error"
    with _LOCK:
        _LLM_PROVIDER_ERROR_COUNTS[f"{safe_provider}.{safe_code}"] += 1


def metrics_snapshot() -> Dict[str, Any]:
    with _LOCK:
        return {
            "requests_total": int(_REQUEST_COUNTS["requests_total"]),
            "errors_total": int(_REQUEST_COUNTS["errors_total"]),
            "request_route_counts": {
                key: value
                for key, value in _REQUEST_COUNTS.items()
                if " " in key
            },
            "generation_status_counts": dict(_GENERATION_STATUS_COUNTS),
            "feedback_risk_reason_counts": dict(_FEEDBACK_RISK_REASON_COUNTS),
            "llm_provider_error_counts": dict(_LLM_PROVIDER_ERROR_COUNTS),
            "plan_generation_duration_buckets": dict(_PLAN_DURATION_BUCKETS),
            "medical_referral_total": int(_MEDICAL_REFERRAL_TOTAL),
        }
