from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set


BOOK_REVIEW_MARKERS = ("book review", "section iv - book review", "section iv – book review")


def _preview(text: str, limit: int = 220) -> str:
    return " ".join(str(text or "").split())[:limit]


def _source_groups(chunks: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for chunk in chunks:
        source_file = str(chunk.get("source_file") or "unknown")
        groups[source_file].append(chunk)
    return dict(groups)


def _has_v2_metadata(chunk: Dict[str, Any]) -> bool:
    return bool(
        chunk.get("source_registry_id")
        and chunk.get("domain_pack")
        and chunk.get("allowed_use")
        and chunk.get("prescription_permission")
    )


def classify_legacy_runtime_source(source_file: str, chunks: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    combined_sample = " ".join(str(chunk.get("text") or "")[:500] for chunk in chunks[:5]).lower()
    sample_chunk = chunks[0] if chunks else {}
    reasons: List[str] = []
    decision = "explanation_only_legacy"

    if any(marker in combined_sample for marker in BOOK_REVIEW_MARKERS):
        decision = "quarantine"
        reasons.append("book_review_not_training_evidence")
    if not all(_has_v2_metadata(chunk) for chunk in chunks):
        reasons.append("legacy_chunk_missing_v2_metadata")
    if source_file in {"", "unknown"}:
        decision = "quarantine"
        reasons.append("unknown_source_file")

    return {
        "source_file": source_file,
        "chunk_count": len(chunks),
        "decision": decision,
        "reasons": sorted(set(reasons)),
        "sample_chunk_id": str(sample_chunk.get("chunk_id") or ""),
        "sample_preview": _preview(str(sample_chunk.get("text") or "")),
    }


def build_legacy_runtime_quarantine_report(chunks: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    groups = _source_groups(chunks)
    sources = [classify_legacy_runtime_source(source_file, source_chunks) for source_file, source_chunks in sorted(groups.items())]
    decision_counts = Counter(item["decision"] for item in sources)
    return {
        "total_sources": len(sources),
        "total_chunks": sum(item["chunk_count"] for item in sources),
        "decision_counts": dict(decision_counts),
        "quarantined_sources": [item["source_file"] for item in sources if item["decision"] == "quarantine"],
        "sources": sources,
    }


def quarantined_source_files_from_report(report: Dict[str, Any]) -> Set[str]:
    return {str(item) for item in report.get("quarantined_sources") or [] if str(item)}


def load_quarantined_source_files(report_path: str | Path) -> Set[str]:
    path = Path(report_path)
    if not path.exists():
        return set()
    report = json.loads(path.read_text(encoding="utf-8"))
    return quarantined_source_files_from_report(report)


def filter_quarantined_chunks(chunks: List[Dict[str, Any]], report_path: str | Path) -> List[Dict[str, Any]]:
    quarantined = load_quarantined_source_files(report_path)
    if not quarantined:
        return chunks
    return [chunk for chunk in chunks if str(chunk.get("source_file") or "") not in quarantined]
