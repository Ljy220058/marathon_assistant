from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List

LIBRARY_FILES = {
    "commercial_core_prescription_library": "commercial_core_prescription_library_20260528.jsonl",
    "commercial_risk_gate_library": "commercial_risk_gate_library_20260528.jsonl",
    "commercial_explanation_library": "commercial_explanation_library_20260528.jsonl",
    "commercial_nutrition_library": "commercial_nutrition_library_20260528.jsonl",
    "commercial_rehab_return_to_run_library": "commercial_rehab_return_to_run_library_20260528.jsonl",
}
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


def _eligible_for_library(row: Dict[str, Any]) -> bool:
    if row.get("commercial_status") != "commercial_staging_eligible":
        return False
    if bool(row.get("human_reviewed")):
        return False
    if str(row.get("prescription_permission") or "") == "can_write_core":
        return str(row.get("evidence_domain") or "") in CORE_DOMAINS
    return True


def _chunk_from_evidence(row: Dict[str, Any], index: int) -> Dict[str, Any]:
    text = " ".join(
        part.strip()
        for part in [
            str(row.get("claim") or ""),
            str(row.get("quote_or_snippet") or ""),
            f"Applicable to: {', '.join(row.get('applicable_to') or [])}.",
            f"Contraindications: {', '.join(row.get('contraindications') or [])}.",
        ]
        if part and part.strip()
    )
    evidence_id = str(row.get("evidence_id") or f"commercial_evidence_{index:04d}")
    return {
        "chunk_id": f"commercial_{evidence_id}",
        "evidence_id": evidence_id,
        "source_registry_id": str(row.get("source_registry_id") or ""),
        "source_file": f"{row.get('source_registry_id') or evidence_id}.evidence.json",
        "source_url": str(row.get("canonical_url") or ""),
        "local_path": "data/knowledge/governance/expert_evidence_20260528_b.jsonl",
        "page": 1,
        "section": str(row.get("section") or ""),
        "paragraph_index": 0,
        "char_start": 0,
        "char_end": len(text),
        "text": text,
        "language": "en",
        "evidence_domain": str(row.get("evidence_domain") or ""),
        "knowledge_layer": "document_index",
        "domain_pack": str(row.get("domain_pack") or ""),
        "allowed_use": str(row.get("allowed_use") or ""),
        "prescription_permission": str(row.get("prescription_permission") or ""),
        "quality_tier": "commercial_staging_eligible",
        "commercial_status": str(row.get("commercial_status") or ""),
        "exclude_from_training_generation": str(row.get("prescription_permission") or "") != "can_write_core",
        "needs_review": False,
        "review_status": "reviewed",
    }


def build_commercial_libraries(
    *,
    evidence_path: Path,
    output_dir: Path,
    staging_chunks_out: Path | None = None,
    audit_out: Path | None = None,
) -> Dict[str, Any]:
    evidence_rows = _load_jsonl(evidence_path)
    libraries: Dict[str, List[Dict[str, Any]]] = {name: [] for name in LIBRARY_FILES}
    blocked: Dict[str, List[str]] = {}
    for row in evidence_rows:
        evidence_id = str(row.get("evidence_id") or "")
        if not _eligible_for_library(row):
            blocked[evidence_id] = ["not_eligible_for_commercial_library"]
            continue
        target = str(row.get("target_library") or "commercial_explanation_library")
        if target not in libraries:
            target = "commercial_explanation_library"
        libraries[target].append(row)
    for library_name, filename in LIBRARY_FILES.items():
        _write_jsonl(output_dir / filename, libraries[library_name])
    staging_rows = [row for rows in libraries.values() for row in rows]
    chunks = [_chunk_from_evidence(row, index) for index, row in enumerate(staging_rows, start=1)]
    if staging_chunks_out is not None:
        _write_jsonl(staging_chunks_out, chunks)
    counts = {name: len(rows) for name, rows in sorted(libraries.items())}
    domain_counts = Counter(str(row.get("evidence_domain") or "unknown") for row in staging_rows)
    report = {
        "evidence_count": len(evidence_rows),
        "commercial_staging_evidence_count": len(staging_rows),
        "library_counts": counts,
        "domain_counts": dict(sorted(domain_counts.items())),
        "blocked_evidence": blocked,
        "staging_chunks_out": str(staging_chunks_out or ""),
    }
    if audit_out is not None:
        _write_json(audit_out, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Split structured evidence into commercial usage-boundary libraries.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--staging-chunks-out")
    parser.add_argument("--audit-out")
    args = parser.parse_args()
    report = build_commercial_libraries(
        evidence_path=Path(args.evidence),
        output_dir=Path(args.output_dir),
        staging_chunks_out=Path(args.staging_chunks_out) if args.staging_chunks_out else None,
        audit_out=Path(args.audit_out) if args.audit_out else None,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
