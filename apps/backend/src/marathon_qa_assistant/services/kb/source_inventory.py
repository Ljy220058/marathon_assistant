from __future__ import annotations

import copy
import json
import threading
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

BODY_SECTIONS = {"document_paragraph", "pdf_paragraph_candidate"}
REGISTRY_SECTIONS = {"registry_preview", "expert_source_registry", "source_registry"}
_SUMMARY_CACHE_LOCK = threading.Lock()
_SUMMARY_CACHE: Dict[str, Dict[str, Any]] = {}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _source_id(chunk: Dict[str, Any]) -> str:
    return _clean(
        chunk.get("source_registry_id")
        or chunk.get("source_file")
        or chunk.get("source")
        or "unknown_source"
    )


def classify_source_status(chunks: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(chunks or [])
    sections = Counter(_clean(row.get("section")) for row in rows)
    body_chunk_count = sum(count for section, count in sections.items() if section in BODY_SECTIONS)
    registry_chunk_count = sum(count for section, count in sections.items() if section in REGISTRY_SECTIONS)
    has_full_text = body_chunk_count > 0
    if has_full_text:
        source_status = "ready"
        evidence_policy = "answerable"
    elif rows:
        source_status = "registry_only"
        evidence_policy = "line_only"
    else:
        source_status = "missing_text"
        evidence_policy = "not_answerable"

    first = rows[0] if rows else {}
    return {
        "source_registry_id": _source_id(first),
        "source_file": _clean(first.get("source_file")),
        "source_label": _clean(first.get("source_label")) or _clean(first.get("source_file")) or _source_id(first),
        "domain_pack": _clean(first.get("domain_pack")),
        "source_status": source_status,
        "has_full_text": has_full_text,
        "evidence_policy": evidence_policy,
        "chunk_count": len(rows),
        "body_chunk_count": body_chunk_count,
        "registry_chunk_count": registry_chunk_count,
        "sections": dict(sorted(sections.items())),
        "sample_text": _clean(first.get("text"))[:240],
    }


def summarize_sources_from_chunks(chunks: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    total_chunks = 0
    for chunk in chunks or []:
        total_chunks += 1
        grouped[_source_id(chunk)].append(chunk)

    sources = [classify_source_status(rows) for _, rows in sorted(grouped.items())]
    status_counts = Counter(item["source_status"] for item in sources)
    domain_counts = Counter(item.get("domain_pack") or "unknown" for item in sources)
    return {
        "total_sources": len(sources),
        "total_chunks": total_chunks,
        "ready_sources": int(status_counts.get("ready", 0)),
        "registry_only_sources": int(status_counts.get("registry_only", 0)),
        "missing_text_sources": int(status_counts.get("missing_text", 0)),
        "status_counts": dict(status_counts),
        "domain_pack_counts": dict(domain_counts),
        "sources": sources,
    }


def load_chunks_jsonl(chunks_path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with Path(chunks_path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _chunks_signature(chunks_path: Path) -> Tuple[str, int, int]:
    stat = Path(chunks_path).stat()
    return (str(Path(chunks_path).absolute()), int(stat.st_mtime_ns), int(stat.st_size))


def load_source_inventory_summary(chunks_path: Path) -> Dict[str, Any]:
    path = Path(chunks_path)
    signature = _chunks_signature(path)
    cache_key = str(path.absolute())
    with _SUMMARY_CACHE_LOCK:
        cached = _SUMMARY_CACHE.get(cache_key)
        if cached and cached.get("signature") == signature:
            return copy.deepcopy(cached["summary"])

    summary = summarize_sources_from_chunks(load_chunks_jsonl(path))
    with _SUMMARY_CACHE_LOCK:
        _SUMMARY_CACHE[cache_key] = {"signature": signature, "summary": copy.deepcopy(summary)}
    return copy.deepcopy(summary)


def warm_source_inventory_cache(chunks_path: Path) -> Dict[str, Any]:
    path = Path(chunks_path)
    if not path.exists():
        return {
            "total_sources": 0,
            "total_chunks": 0,
            "ready_sources": 0,
            "registry_only_sources": 0,
            "missing_text_sources": 0,
            "status_counts": {},
            "domain_pack_counts": {},
            "sources": [],
        }
    return load_source_inventory_summary(path)


def public_source_inventory_summary(chunks_path: Path) -> Dict[str, Any]:
    summary = load_source_inventory_summary(chunks_path)
    summary["sources"] = []
    return summary


def reset_source_inventory_cache_for_tests() -> None:
    with _SUMMARY_CACHE_LOCK:
        _SUMMARY_CACHE.clear()
