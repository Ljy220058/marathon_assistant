from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence

from marathon_qa_assistant.services.kb.models import SourceRecord, SourceReviewStatus
from marathon_qa_assistant.services.kb.source_registry import (
    normalize_source_record,
    source_record_is_ready,
    source_record_to_dict,
)


def _record(value: SourceRecord | Dict[str, Any]) -> SourceRecord:
    if isinstance(value, SourceRecord):
        return value
    return normalize_source_record(value)


def _fingerprint(record: SourceRecord, key: str) -> str:
    if key == "doi":
        return str(record.metadata.get("doi") or "").strip().lower()
    if key == "title":
        return " ".join(record.title.lower().split())
    if key == "content_hash":
        return str(record.content_hash or "").strip().lower()
    return ""


def _duplicate_reasons(record: SourceRecord, counts: Mapping[str, Counter[str]]) -> List[str]:
    reasons: List[str] = []
    for key in ("doi", "title", "content_hash"):
        value = _fingerprint(record, key)
        if value and counts.get(key, Counter()).get(value, 0) > 1:
            reasons.append(f"duplicate_{key}")
    return reasons


def _local_path_exists(record: SourceRecord) -> bool | None:
    local_path = str(record.local_path or record.source_path or "").strip()
    if not local_path:
        return None
    if local_path.startswith("http://") or local_path.startswith("https://"):
        return None
    return Path(local_path).exists()


def review_source_record(
    record_input: SourceRecord | Dict[str, Any],
    *,
    duplicate_counts: Mapping[str, Counter[str]] | None = None,
    external_checks: Mapping[str, Mapping[str, Any]] | None = None,
) -> Dict[str, Any]:
    record = _record(record_input)
    source_checks = dict((external_checks or {}).get(record.source_registry_id) or {})
    url = str(record.source_url or "").strip()
    local_exists = _local_path_exists(record)
    is_pdf = str(record.source_file or record.local_path or "").lower().endswith(".pdf")
    is_web = bool(url and not is_pdf)

    checks: Dict[str, Any] = {
        "has_location": bool(url or record.local_path or record.source_path or record.source_file),
        "has_source_url": bool(url),
        "has_license_status": bool(record.license_status and record.license_status != "unknown"),
        "has_owner": bool(record.authors_or_owner),
        "has_year": bool(record.year),
        "has_content_hash": bool(record.content_hash),
        "local_path_exists": local_exists,
        "url_reachable": source_checks.get("url_reachable"),
        "pdf_text_quality_checked": source_checks.get("pdf_text_quality_checked") if is_pdf else None,
        "web_canonical_checked": source_checks.get("web_canonical_checked") if is_web else None,
    }

    blockers: List[str] = []
    if record.review_status == SourceReviewStatus.SEED_ONLY:
        blockers.append("seed_only_not_runtime_source")
    if record.needs_review:
        blockers.append("needs_review")
    if record.review_status != SourceReviewStatus.APPROVED:
        blockers.append("not_approved")
    if not checks["has_location"]:
        blockers.append("missing_source_location")
    if not checks["has_license_status"]:
        blockers.append("missing_license_status")
    if not checks["has_owner"]:
        blockers.append("missing_owner")
    if not checks["has_year"]:
        blockers.append("missing_year")
    if not checks["has_content_hash"]:
        blockers.append("missing_content_hash")
    if local_exists is False:
        blockers.append("local_file_missing")
    if url and checks["url_reachable"] is not True:
        blockers.append("url_reachability_not_verified")
    if is_pdf and checks["pdf_text_quality_checked"] is not True:
        blockers.append("pdf_text_quality_not_verified")
    if is_web and checks["web_canonical_checked"] is not True:
        blockers.append("web_canonical_not_verified")
    blockers.extend(_duplicate_reasons(record, duplicate_counts or {}))

    can_enter_runtime_index = source_record_is_ready(record) and not blockers
    return {
        "source_registry_id": record.source_registry_id,
        "title": record.title,
        "source_type": record.source_type,
        "domain_pack": record.domain_pack,
        "evidence_domain": record.evidence_domain.value,
        "allowed_use": record.allowed_use.value,
        "prescription_permission": record.prescription_permission.value,
        "review_status": record.review_status.value,
        "needs_review": record.needs_review,
        "checks": checks,
        "blocking_reasons": sorted(set(blockers)),
        "can_enter_runtime_index": can_enter_runtime_index,
        "registry_snapshot": source_record_to_dict(record),
    }


def build_source_review_queue(records_input: Iterable[SourceRecord | Dict[str, Any]]) -> List[Dict[str, Any]]:
    records = [_record(item) for item in records_input]
    counts: Dict[str, Counter[str]] = {"doi": Counter(), "title": Counter(), "content_hash": Counter()}
    for record in records:
        for key in counts:
            value = _fingerprint(record, key)
            if value:
                counts[key][value] += 1
    return [review_source_record(record, duplicate_counts=counts) for record in records]


def summarize_source_review_queue(queue: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    status_counts = Counter(str(item.get("review_status") or "") for item in queue)
    blocker_counts: Counter[str] = Counter()
    for item in queue:
        blocker_counts.update(str(reason) for reason in item.get("blocking_reasons") or [])
    return {
        "total": len(queue),
        "can_enter_runtime_index": sum(1 for item in queue if item.get("can_enter_runtime_index")),
        "status_counts": dict(status_counts),
        "top_blocking_reasons": dict(blocker_counts.most_common(20)),
    }
