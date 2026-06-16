from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable

from marathon_qa_assistant.core.app_state import DATA_DIR


DEFAULT_CONFLICT_REVIEW_QUEUE = DATA_DIR / "knowledge" / "governance" / "evidence_conflict_review_queue.jsonl"


def stable_conflict_id(*, query: str, reason: str, sources: Iterable[Any]) -> str:
    source_key = "|".join(sorted(str(source or "") for source in sources if str(source or "").strip()))
    seed = "\n".join([str(query or "").strip().lower(), str(reason or "").strip().lower(), source_key])
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"conflict_{digest}"


def record_conflict_review_item(
    *,
    query: str,
    reason: str,
    sources: Iterable[Dict[str, Any]] | Iterable[Any],
    queue_path: Path | None = None,
) -> Dict[str, Any]:
    normalized_sources = []
    source_ids = []
    for source in sources or []:
        if isinstance(source, dict):
            source_id = str(
                source.get("evidence_id")
                or source.get("chunk_id")
                or source.get("source_registry_id")
                or source.get("source_file")
                or ""
            )
            normalized_sources.append(
                {
                    "evidence_id": str(source.get("evidence_id") or ""),
                    "chunk_id": str(source.get("chunk_id") or ""),
                    "source_registry_id": str(source.get("source_registry_id") or ""),
                    "source_file": str(source.get("source_file") or ""),
                    "graph_relation_strength": str(source.get("graph_relation_strength") or ""),
                }
            )
        else:
            source_id = str(source or "")
            normalized_sources.append({"source": source_id})
        if source_id:
            source_ids.append(source_id)

    item = {
        "conflict_id": stable_conflict_id(query=query, reason=reason, sources=source_ids),
        "query": str(query or ""),
        "reason": str(reason or ""),
        "sources": normalized_sources,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "governance_action": "review_for_kg_source_registry_or_index_update",
    }

    path = Path(queue_path or DEFAULT_CONFLICT_REVIEW_QUEUE)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_ids = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                existing = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(existing, dict) and existing.get("conflict_id"):
                existing_ids.add(str(existing["conflict_id"]))
    if item["conflict_id"] not in existing_ids:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    return item
