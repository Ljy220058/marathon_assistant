from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

PASS_DECISIONS = {
    "pass",
    "pass_for_core_prescription",
    "pass_for_explanation_only",
    "pass_for_risk_gate_only",
    "pass_for_rehab_guidance",
    "pass_for_nutrition_guidance",
}
MEDICAL_DOMAINS = {"medical_safety", "rehab_strength_mobility"}
CORE_DOMAINS = {"protocol", "action_library"}


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


def _reports_by_source(reports: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for report in reports:
        grouped[str(report.get("source_registry_id") or "")].append(report)
    return grouped


def _pass_reports(reports: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        report
        for report in reports
        if str(report.get("decision") or "") in PASS_DECISIONS and not bool(report.get("red_flag"))
    ]


def _has_actor(reports: Sequence[Dict[str, Any]], actor: str) -> bool:
    return any(str(report.get("review_actor") or "") == actor for report in reports)


def _commercial_status(source: Dict[str, Any], reports: Sequence[Dict[str, Any]]) -> tuple[str, List[str]]:
    reasons: List[str] = []
    if any(bool(report.get("red_flag")) or str(report.get("decision") or "") == "red_flag" for report in reports):
        reasons.append("review_red_flag")
        return "candidate", reasons
    passes = _pass_reports(reports)
    pass_actors = {str(report.get("review_actor") or "") for report in passes}
    if len(pass_actors) < 2:
        reasons.append("fewer_than_two_independent_ai_review_passes")
    domain = str(source.get("evidence_domain") or "")
    if domain in MEDICAL_DOMAINS and "medical_safety_reviewer" not in pass_actors:
        reasons.append("medical_safety_review_required")
    if str(source.get("prescription_permission") or "") == "can_write_core":
        if domain not in CORE_DOMAINS:
            reasons.append("core_permission_domain_violation")
        if "sports_science_reviewer" not in pass_actors:
            reasons.append("sports_science_review_required_for_core")
        if "release_auditor" not in pass_actors:
            reasons.append("release_audit_required_for_core")
    if reasons:
        return "candidate", reasons
    return "commercial_staging_eligible", []


def review_expert_sources_for_commercial_staging(
    *,
    source_library_path: Path,
    review_reports_path: Path,
    reviewed_sources_out: Path,
    audit_out: Path | None = None,
) -> Dict[str, Any]:
    sources = _load_jsonl(source_library_path)
    reports = _load_jsonl(review_reports_path)
    grouped_reports = _reports_by_source(reports)
    reviewed_sources: List[Dict[str, Any]] = []
    blocker_summary: Dict[str, List[str]] = {}
    status_counts: Counter[str] = Counter()
    for source in sources:
        source_id = str(source.get("source_registry_id") or "")
        source_reports = grouped_reports.get(source_id, [])
        status, blockers = _commercial_status(source, source_reports)
        review_report_ids = [
            str(report.get("review_report_id") or f"{source_id}:{report.get('review_actor')}")
            for report in source_reports
        ]
        reviewed = {
            **source,
            "commercial_status": status,
            "review_actor": "ai_agent_panel" if source_reports else "none",
            "human_reviewed": False,
            "review_report_ids": review_report_ids,
            "review_pass_count": len(_pass_reports(source_reports)),
            "review_blockers": blockers,
        }
        reviewed_sources.append(reviewed)
        status_counts[status] += 1
        if blockers:
            blocker_summary[source_id] = blockers
    _write_jsonl(reviewed_sources_out, reviewed_sources)
    audit = {
        "source_count": len(sources),
        "review_report_count": len(reports),
        "commercial_status_counts": dict(sorted(status_counts.items())),
        "commercial_staging_eligible_count": status_counts["commercial_staging_eligible"],
        "blocked_sources": blocker_summary,
    }
    if audit_out is not None:
        _write_json(audit_out, audit)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply AI review reports to commercial source staging eligibility.")
    parser.add_argument("--source-library", required=True)
    parser.add_argument("--review-reports", required=True)
    parser.add_argument("--reviewed-sources-out", required=True)
    parser.add_argument("--audit-out")
    args = parser.parse_args()
    report = review_expert_sources_for_commercial_staging(
        source_library_path=Path(args.source_library),
        review_reports_path=Path(args.review_reports),
        reviewed_sources_out=Path(args.reviewed_sources_out),
        audit_out=Path(args.audit_out) if args.audit_out else None,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
