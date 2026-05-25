from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping


REPORT_SCHEMA_VERSION = "source_gap_report_v1"


def _safe_source_summary(item: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "source_registry_id": str(item.get("source_registry_id") or ""),
        "title": str(item.get("title") or ""),
        "domain_pack": str(item.get("domain_pack") or ""),
        "evidence_domain": str(item.get("evidence_domain") or ""),
        "prescription_permission": str(item.get("prescription_permission") or ""),
        "review_status": str(item.get("review_status") or ""),
        "blocking_reasons": [str(reason) for reason in item.get("blocking_reasons") or []],
    }


def _domain_pack_readiness(queue: Iterable[Mapping[str, Any]]) -> Dict[str, Dict[str, int]]:
    readiness: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {
            "total_records": 0,
            "approved_records": 0,
            "candidate_records": 0,
            "seed_records": 0,
            "runtime_ready_records": 0,
            "ready_core_records": 0,
        }
    )
    for item in queue:
        domain_pack = str(item.get("domain_pack") or "unknown")
        bucket = readiness[domain_pack]
        bucket["total_records"] += 1
        status = str(item.get("review_status") or "")
        if status == "approved":
            bucket["approved_records"] += 1
        elif status == "candidate":
            bucket["candidate_records"] += 1
        elif status == "seed_only":
            bucket["seed_records"] += 1
        if bool(item.get("can_enter_runtime_index")):
            bucket["runtime_ready_records"] += 1
            if str(item.get("prescription_permission") or "") == "can_write_core":
                bucket["ready_core_records"] += 1
    return {key: dict(value) for key, value in sorted(readiness.items())}


def _candidate_blocker_groups(
    queue: Iterable[Mapping[str, Any]],
    *,
    max_candidates_per_blocker: int,
) -> Dict[str, List[Dict[str, Any]]]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in queue:
        if bool(item.get("can_enter_runtime_index")):
            continue
        status = str(item.get("review_status") or "")
        if status not in {"candidate", "reviewed", "seed_only"}:
            continue
        summary = _safe_source_summary(item)
        for reason in item.get("blocking_reasons") or []:
            reason_text = str(reason)
            if len(groups[reason_text]) < max_candidates_per_blocker:
                groups[reason_text].append(summary)
    return {key: value for key, value in sorted(groups.items())}


def _domain_pack_external_source_needs(release_report: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = list(release_report.get("coverage_matrix_delta") or [])
    needs: List[Dict[str, Any]] = []
    for row in rows:
        target = int(row.get("target_source_count") or 0)
        current = int(row.get("current_source_count") or 0)
        needed = max(0, target - current)
        if needed <= 0:
            continue
        needs.append(
            {
                "domain_pack": str(row.get("domain_pack") or ""),
                "subdomain": str(row.get("subdomain") or ""),
                "gap_status": str(row.get("gap_status") or ""),
                "can_write_core": bool(row.get("can_write_core")),
                "current_source_count": current,
                "target_source_count": target,
                "needed_source_count": needed,
                "review_direction": (
                    "external_authoritative_or_internal_reviewed_core_sources"
                    if bool(row.get("can_write_core"))
                    else "external_authoritative_explanation_sources"
                ),
            }
        )
    gap_rank = {"gap": 0, "partial": 1, "covered": 2}
    return sorted(
        needs,
        key=lambda item: (
            gap_rank.get(str(item["gap_status"]), 9),
            -item["needed_source_count"],
            item["domain_pack"],
        ),
    )


def build_source_gap_report(
    *,
    source_review_queue: Iterable[Mapping[str, Any]],
    release_report: Mapping[str, Any],
    max_candidates_per_blocker: int = 10,
) -> Dict[str, Any]:
    queue = list(source_review_queue)
    return {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "total_source_records": len(queue),
        "domain_pack_readiness": _domain_pack_readiness(queue),
        "candidate_blocker_groups": _candidate_blocker_groups(
            queue,
            max_candidates_per_blocker=max_candidates_per_blocker,
        ),
        "domain_pack_external_source_needs": _domain_pack_external_source_needs(release_report),
        "redaction_policy": "machine paths, raw prompts, and private health text are omitted",
    }
