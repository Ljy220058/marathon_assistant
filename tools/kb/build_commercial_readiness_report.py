from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

CORE_DOMAINS = {"protocol", "action_library"}
REQUIRED_EVIDENCE_FIELDS = ["claim", "canonical_url", "section", "applicable_to", "contraindications"]
PASS_DECISIONS = {
    "pass",
    "pass_for_core_prescription",
    "pass_for_explanation_only",
    "pass_for_risk_gate_only",
    "pass_for_rehab_guidance",
    "pass_for_nutrition_guidance",
}


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _review_pass_counts(reports: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    actors_by_source: Dict[str, set[str]] = defaultdict(set)
    for report in reports:
        if str(report.get("decision") or "") not in PASS_DECISIONS or bool(report.get("red_flag")):
            continue
        actors_by_source[str(report.get("source_registry_id") or "")].add(str(report.get("review_actor") or ""))
    return {source_id: len(actors) for source_id, actors in actors_by_source.items()}


def _missing_evidence_fields(row: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    for field in REQUIRED_EVIDENCE_FIELDS:
        value = row.get(field)
        if isinstance(value, list):
            if not value:
                missing.append(field)
        elif not str(value or "").strip():
            missing.append(field)
    return missing


def build_commercial_readiness_report(
    *,
    source_audit_path: Path,
    review_reports_path: Path,
    evidence_path: Path,
    gold_qa_report_path: Path,
    manifest_path: Path,
    output_path: Path | None = None,
) -> Dict[str, Any]:
    source_audit = _load_json(source_audit_path)
    reports = _load_jsonl(review_reports_path)
    evidence_rows = _load_jsonl(evidence_path)
    gold = _load_json(gold_qa_report_path)
    manifest = _load_json(manifest_path)
    blockers: List[str] = []
    warnings: List[str] = []

    if source_audit.get("missing_required_audit_metadata"):
        blockers.append("source_audit_metadata_missing")
    if source_audit.get("duplicate_canonical_urls"):
        warnings.append("duplicate_canonical_urls_reported")

    review_counts = _review_pass_counts(reports)
    for row in evidence_rows:
        source_id = str(row.get("source_registry_id") or "")
        if row.get("commercial_status") == "candidate":
            blockers.append("candidate_evidence_in_commercial_staging")
        if bool(row.get("human_reviewed")):
            blockers.append("fake_human_review_flag")
        if review_counts.get(source_id, 0) < 2:
            blockers.append("source_missing_two_ai_review_passes")
        if str(row.get("evidence_domain") or "") == "medical_safety" and str(row.get("allowed_use") or "") not in {"risk_gate", "explanation"}:
            blockers.append("medical_source_overreach")
        if str(row.get("prescription_permission") or "") == "can_write_core" and str(row.get("evidence_domain") or "") not in CORE_DOMAINS:
            blockers.append("core_permission_domain_violation")
        if _missing_evidence_fields(row):
            blockers.append("evidence_required_fields_missing")
    if gold and not bool(gold.get("passed", False)):
        blockers.append("gold_qa_failed")
    if gold.get("red_flag_failures"):
        blockers.append("red_flag_regression_failed")
    if bool(manifest.get("can_replace_runtime")):
        blockers.append("staging_manifest_can_replace_runtime_true")

    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))
    domain_counts = Counter(str(row.get("domain_pack") or row.get("evidence_domain") or "unknown") for row in evidence_rows)
    explanation_only_domains = sorted(
        {
            str(row.get("domain_pack") or row.get("evidence_domain") or "unknown")
            for row in evidence_rows
            if row.get("prescription_permission") != "can_write_core"
        }
    )
    core_domains = sorted(
        {
            str(row.get("domain_pack") or row.get("evidence_domain") or "unknown")
            for row in evidence_rows
            if row.get("prescription_permission") == "can_write_core"
        }
    )
    report = {
        "commercial_staging_ready": not blockers,
        "release_ready": False,
        "can_replace_runtime": False,
        "domain_counts": dict(sorted(domain_counts.items())),
        "commercial_core_domains": core_domains,
        "explanation_or_risk_only_domains": explanation_only_domains,
        "source_license_limitations": source_audit.get("license_limitations") or ["link_only_or_summary_by_default"],
        "medical_referral_boundaries": [
            row.get("source_registry_id")
            for row in evidence_rows
            if row.get("requires_medical_referral") or row.get("evidence_domain") == "medical_safety"
        ],
        "cannot_claim": [
            "human_expert_reviewed",
            "release_runtime_replaceable",
            "medical_diagnosis_or_treatment",
        ],
        "release_blockers": blockers,
        "warnings": warnings,
    }
    if output_path is not None:
        _write_json(output_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build commercial readiness report for expert knowledge staging artifacts.")
    parser.add_argument("--source-audit", required=True)
    parser.add_argument("--review-reports", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--gold-qa-report", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = build_commercial_readiness_report(
        source_audit_path=Path(args.source_audit),
        review_reports_path=Path(args.review_reports),
        evidence_path=Path(args.evidence),
        gold_qa_report_path=Path(args.gold_qa_report),
        manifest_path=Path(args.manifest),
        output_path=Path(args.output),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
