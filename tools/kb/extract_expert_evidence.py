from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

CORE_DOMAINS = {"protocol", "action_library"}
REQUIRED_EVIDENCE_FIELDS = ["claim", "canonical_url", "section", "applicable_to", "contraindications"]


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _reports_by_source(reports: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for report in reports:
        grouped[str(report.get("source_registry_id") or "")].append(report)
    return grouped


def _target_library(source: Dict[str, Any]) -> str:
    allowed_use = str(source.get("allowed_use") or "")
    domain = str(source.get("evidence_domain") or "")
    permission = str(source.get("prescription_permission") or "")
    if permission == "can_write_core" and domain in CORE_DOMAINS:
        return "commercial_core_prescription_library"
    if allowed_use == "risk_gate" or domain in {"medical_safety", "environment_race_context"}:
        return "commercial_risk_gate_library"
    if allowed_use == "nutrition_guidance" or domain == "nutrition_race_fueling":
        return "commercial_nutrition_library"
    if allowed_use == "rehab_guidance" or domain == "rehab_strength_mobility":
        return "commercial_rehab_return_to_run_library"
    return "commercial_explanation_library"


def _list_field(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if str(value or "").strip():
        return [str(value)]
    return []


def _evidence_from_source(source: Dict[str, Any], reports: List[Dict[str, Any]], index: int) -> Dict[str, Any]:
    metadata = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
    source_id = str(source.get("source_registry_id") or "")
    evidence_id = str(metadata.get("evidence_id") or f"ev_{source_id}_{index:03d}")
    return {
        "evidence_id": evidence_id,
        "source_registry_id": source_id,
        "title": str(source.get("title") or ""),
        "claim": str(metadata.get("claim") or metadata.get("summary") or metadata.get("selection_reason") or ""),
        "canonical_url": str(metadata.get("canonical_url") or source.get("source_url") or ""),
        "section": str(metadata.get("section") or "expert_source_registry"),
        "page_or_heading": str(metadata.get("page_or_heading") or metadata.get("section") or ""),
        "quote_or_snippet": str(metadata.get("quote_or_snippet") or metadata.get("summary") or "")[:800],
        "applicable_to": _list_field(metadata.get("applicable_to") or source.get("applicable_runner_segments") or ["runner"]),
        "not_applicable_to": _list_field(metadata.get("not_applicable_to")),
        "contraindications": _list_field(metadata.get("contraindications") or source.get("contraindications") or ["red_flag_symptoms"]),
        "red_flags": _list_field(metadata.get("red_flags")),
        "allowed_use": str(source.get("allowed_use") or "explanation"),
        "prescription_permission": str(source.get("prescription_permission") or "explanation_only"),
        "evidence_domain": str(source.get("evidence_domain") or ""),
        "domain_pack": str(source.get("domain_pack") or ""),
        "requires_medical_referral": str(source.get("evidence_domain") or "") == "medical_safety" or str(source.get("allowed_use") or "") == "risk_gate",
        "requires_coach_review": str(source.get("prescription_permission") or "") == "can_write_core",
        "target_library": _target_library(source),
        "commercial_status": str(source.get("commercial_status") or "candidate"),
        "human_reviewed": bool(source.get("human_reviewed")),
        "review_report_ids": list(source.get("review_report_ids") or [str(report.get("review_report_id") or "") for report in reports]),
        "source_license_status": str(source.get("license_status") or ""),
        "authority_tier": str(metadata.get("authority_tier") or ""),
    }


def _missing_fields(evidence: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    for field in REQUIRED_EVIDENCE_FIELDS:
        value = evidence.get(field)
        if isinstance(value, list):
            if not value:
                missing.append(field)
        elif not str(value or "").strip():
            missing.append(field)
    return missing


def extract_expert_evidence(
    *,
    reviewed_sources_path: Path,
    review_reports_path: Path,
    evidence_out: Path,
    audit_out: Path | None = None,
) -> Dict[str, Any]:
    sources = _load_jsonl(reviewed_sources_path)
    reports = _load_jsonl(review_reports_path)
    grouped_reports = _reports_by_source(reports)
    evidence_rows: List[Dict[str, Any]] = []
    blocked_sources: Dict[str, List[str]] = {}
    for index, source in enumerate(sources, start=1):
        source_id = str(source.get("source_registry_id") or "")
        if source.get("commercial_status") != "commercial_staging_eligible":
            blocked_sources[source_id] = ["not_commercial_staging_eligible"]
            continue
        evidence = _evidence_from_source(source, grouped_reports.get(source_id, []), index)
        missing = _missing_fields(evidence)
        if missing:
            blocked_sources[source_id] = [f"missing_{field}" for field in missing]
            continue
        evidence_rows.append(evidence)
    _write_jsonl(evidence_out, evidence_rows)
    library_counts = Counter(str(row.get("target_library") or "unknown") for row in evidence_rows)
    audit = {
        "source_count": len(sources),
        "evidence_count": len(evidence_rows),
        "library_counts": dict(sorted(library_counts.items())),
        "blocked_sources": blocked_sources,
        "required_evidence_fields": REQUIRED_EVIDENCE_FIELDS,
    }
    if audit_out is not None:
        _write_json(audit_out, audit)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract structured evidence from commercial-staging-eligible reviewed sources.")
    parser.add_argument("--reviewed-sources", required=True)
    parser.add_argument("--review-reports", required=True)
    parser.add_argument("--evidence-out", required=True)
    parser.add_argument("--audit-out")
    args = parser.parse_args()
    report = extract_expert_evidence(
        reviewed_sources_path=Path(args.reviewed_sources),
        review_reports_path=Path(args.review_reports),
        evidence_out=Path(args.evidence_out),
        audit_out=Path(args.audit_out) if args.audit_out else None,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
