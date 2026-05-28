from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "apps" / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from marathon_qa_assistant.services.kb.models import (  # noqa: E402
    AllowedUse,
    EvidenceDomain,
    KnowledgeLayer,
    PrescriptionPermission,
    SourceReviewStatus,
)
from marathon_qa_assistant.services.kb.source_registry import (  # noqa: E402
    normalize_source_record,
    source_record_to_dict,
    validate_source_registry_v2,
)
from marathon_qa_assistant.services.kb.source_review import (  # noqa: E402
    build_source_review_queue,
    summarize_source_review_queue,
)

REQUIRED_AUDIT_METADATA = [
    "accessed_at",
    "date_basis",
    "canonical_url",
    "authority_tier",
    "selection_reason",
    "gap_target",
]
REQUIRED_DOMAIN_PACKS = {
    "training_protocols",
    "action_library",
    "environment_race_context",
    "medical_risk",
    "nutrition_race_fueling",
    "rehab_return_to_run",
}
STRICT_ENUM_FIELDS = {
    "evidence_domain": EvidenceDomain,
    "knowledge_layer": KnowledgeLayer,
    "allowed_use": AllowedUse,
    "prescription_permission": PrescriptionPermission,
    "review_status": SourceReviewStatus,
}


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _strict_enum_errors(row: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for field_name, enum_cls in STRICT_ENUM_FIELDS.items():
        raw = row.get(field_name)
        if raw in (None, ""):
            continue
        try:
            enum_cls(str(raw))
        except ValueError:
            errors.append(f"invalid_enum:{field_name}={raw}")
    return errors


def _normalized_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    errors: Dict[str, List[str]] = {}
    for row in rows:
        source_id = str(row.get("source_registry_id") or row.get("source_file") or row.get("source_url") or "unknown")
        enum_errors = _strict_enum_errors(row)
        if enum_errors:
            errors[source_id] = enum_errors
            continue
        record = normalize_source_record(row)
        validation_errors = validate_source_registry_v2(record)
        if validation_errors:
            errors[record.source_registry_id] = validation_errors
        normalized.append(source_record_to_dict(record))
    if errors:
        raise ValueError(f"expert source registry validation failed: {errors}")
    return normalized


def _merge_by_source_id(existing: Iterable[Dict[str, Any]], batch: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for row in existing:
        source_id = str(row.get("source_registry_id") or "")
        if source_id:
            merged[source_id] = row
    for row in batch:
        source_id = str(row.get("source_registry_id") or "")
        if source_id:
            merged[source_id] = row
    return [merged[key] for key in sorted(merged)]


def _duplicate_groups(rows: Sequence[Dict[str, Any]], key_fields: Sequence[str], *, metadata_key: str = "") -> List[Dict[str, Any]]:
    grouped: Dict[str, List[str]] = defaultdict(list)
    labels: Dict[str, Dict[str, str]] = {}
    for row in rows:
        values: List[str] = []
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        for field in key_fields:
            value = metadata.get(field) if metadata_key == "metadata" else row.get(field)
            values.append(str(value or "").strip().lower())
        if not all(values):
            continue
        key = "|".join(values)
        grouped[key].append(str(row.get("source_registry_id") or ""))
        labels[key] = {field: values[index] for index, field in enumerate(key_fields)}
    return [
        {**labels[key], "source_registry_ids": sorted(source_ids)}
        for key, source_ids in sorted(grouped.items())
        if len(set(source_ids)) > 1
    ]


def _is_homepage_like(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    return bool(parsed.netloc) and path in {"", "home", "index.html", "index.htm"}


def _counter_from_rows(rows: Sequence[Dict[str, Any]], field: str, *, metadata_key: str = "") -> Dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        value = metadata.get(field) if metadata_key == "metadata" else row.get(field)
        if str(value or "").strip():
            counts[str(value)] += 1
    return dict(sorted(counts.items()))


def _commercial_risk_counts(rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        risks = metadata.get("commercial_risks") or []
        if not isinstance(risks, list):
            risks = [risks]
        for risk in risks:
            if str(risk or "").strip():
                counts[str(risk)] += 1
    return dict(sorted(counts.items()))


def _deep_link_issue_source_ids(rows: Sequence[Dict[str, Any]]) -> List[str]:
    issue_ids: List[str] = []
    for row in rows:
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        canonical_url = str(metadata.get("canonical_url") or row.get("source_url") or "")
        if _is_homepage_like(canonical_url):
            issue_ids.append(str(row.get("source_registry_id") or ""))
    return sorted(source_id for source_id in issue_ids if source_id)


def build_source_audit(rows: Sequence[Dict[str, Any]], batch_files: Sequence[Path]) -> Dict[str, Any]:
    missing_metadata: Dict[str, List[str]] = {}
    domain_counts: Counter[str] = Counter()
    permission_counts: Counter[str] = Counter()
    batch_counts: Dict[str, int] = {}
    source_ids_by_batch: Dict[str, List[str]] = {}
    for row in rows:
        source_id = str(row.get("source_registry_id") or "")
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        missing = [field for field in REQUIRED_AUDIT_METADATA if not str(metadata.get(field) or "").strip()]
        if missing:
            missing_metadata[source_id] = missing
        domain_counts[str(row.get("domain_pack") or row.get("evidence_domain") or "unknown")] += 1
        permission_counts[str(row.get("review_status") or "unknown")] += 1
    for batch_file in batch_files:
        batch_rows = _load_jsonl(batch_file)
        batch_counts[str(batch_file)] = len(batch_rows)
        source_ids_by_batch[str(batch_file)] = sorted(str(row.get("source_registry_id") or "") for row in batch_rows if row.get("source_registry_id"))
    duplicate_canonical_urls = _duplicate_groups(rows, ["canonical_url"], metadata_key="metadata")
    duplicate_owner_title_pairs = _duplicate_groups(rows, ["authors_or_owner", "title"])
    deep_link_issues = _deep_link_issue_source_ids(rows)
    canonical_urls = {
        str((row.get("metadata") if isinstance(row.get("metadata"), dict) else {}).get("canonical_url") or row.get("source_url") or "").strip().lower()
        for row in rows
        if str((row.get("metadata") if isinstance(row.get("metadata"), dict) else {}).get("canonical_url") or row.get("source_url") or "").strip()
    }
    domain_gaps = sorted(REQUIRED_DOMAIN_PACKS - set(domain_counts))
    return {
        "required_audit_metadata": REQUIRED_AUDIT_METADATA,
        "batch_files": [str(path) for path in batch_files],
        "batch_counts": batch_counts,
        "source_ids_by_batch": source_ids_by_batch,
        "candidate_source_count": len(rows),
        "unique_canonical_url_count": len(canonical_urls),
        "per_domain_counts": dict(sorted(domain_counts.items())),
        "authority_tier_counts": _counter_from_rows(rows, "authority_tier", metadata_key="metadata"),
        "license_status_counts": _counter_from_rows(rows, "license_status"),
        "commercial_risk_counts": _commercial_risk_counts(rows),
        "deep_link_issue_source_ids": deep_link_issues,
        "duplicate_canonical_urls": duplicate_canonical_urls,
        "duplicate_owner_title_pairs": duplicate_owner_title_pairs,
        "missing_required_audit_metadata": missing_metadata,
        "domain_gaps": domain_gaps,
        "coverage_ready": not missing_metadata and not deep_link_issues and not duplicate_canonical_urls and not domain_gaps,
        "selected_for_review_source_ids": [],
        "not_selected_reasons": {},
        "candidate_permission_boundary_counts": dict(sorted(permission_counts.items())),
    }


def register_expert_source_batch(
    *,
    registry_path: Path,
    batch_file: Path | None = None,
    batch_files: Sequence[Path] | None = None,
    registry_out: Path,
    queue_out: Path | None = None,
    summary_out: Path | None = None,
    audit_out: Path | None = None,
) -> Dict[str, Any]:
    selected_batch_files = list(batch_files or ([] if batch_file is None else [batch_file]))
    existing_rows = _normalized_rows(_load_jsonl(registry_path))
    raw_batch_rows: List[Dict[str, Any]] = []
    for selected in selected_batch_files:
        raw_batch_rows.extend(_load_jsonl(Path(selected)))
    batch_rows = _normalized_rows(raw_batch_rows)
    merged_rows = _merge_by_source_id(existing_rows, batch_rows)
    queue = build_source_review_queue(merged_rows)
    summary = summarize_source_review_queue(queue)
    audit = build_source_audit(batch_rows, [Path(path) for path in selected_batch_files])

    _write_jsonl(registry_out, merged_rows)
    if queue_out is not None:
        _write_jsonl(queue_out, queue)
    if summary_out is not None:
        _write_json(summary_out, summary)
    if audit_out is not None:
        _write_json(audit_out, audit)

    return {
        "existing_records": len(existing_rows),
        "batch_records": len(batch_rows),
        "merged_records": len(merged_rows),
        "queue_records": len(queue),
        "can_enter_runtime_index": summary["can_enter_runtime_index"],
        "registry_out": str(registry_out),
        "queue_out": str(queue_out or ""),
        "summary_out": str(summary_out or ""),
        "audit_out": str(audit_out or ""),
        "source_audit": audit,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Register expert source batches without replacing the current registry.")
    parser.add_argument("--registry", default=str(ROOT / "data" / "knowledge" / "governance" / "source_registry_v2.jsonl"))
    parser.add_argument("--batch-file", action="append", required=True)
    parser.add_argument("--registry-out", required=True)
    parser.add_argument("--queue-out")
    parser.add_argument("--summary-out")
    parser.add_argument("--audit-out")
    args = parser.parse_args()

    report = register_expert_source_batch(
        registry_path=Path(args.registry),
        batch_files=[Path(path) for path in args.batch_file],
        registry_out=Path(args.registry_out),
        queue_out=Path(args.queue_out) if args.queue_out else None,
        summary_out=Path(args.summary_out) if args.summary_out else None,
        audit_out=Path(args.audit_out) if args.audit_out else None,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
