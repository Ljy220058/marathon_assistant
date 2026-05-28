from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "apps" / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from marathon_qa_assistant.services.kb.source_registry import normalize_source_record  # noqa: E402


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


def _expert_chunk_text(record: Dict[str, Any]) -> str:
    metadata = dict(record.get("metadata") or {})
    parts = [
        str(record.get("title") or ""),
        f"Domain pack: {record.get('domain_pack') or ''}.",
        f"Evidence domain: {record.get('evidence_domain') or ''}.",
        f"Permission: {record.get('prescription_permission') or ''}.",
        str(metadata.get("summary") or metadata.get("purpose") or ""),
    ]
    return " ".join(part.strip() for part in parts if part and part.strip())


def _record_to_chunk(record: Dict[str, Any], index: int) -> Dict[str, Any]:
    normalized = normalize_source_record(record)
    data = {
        "chunk_id": f"chunkv2_{normalized.source_registry_id}_{index:04d}",
        "source_registry_id": normalized.source_registry_id,
        "source_file": normalized.source_file,
        "source_url": normalized.source_url or f"internal://{normalized.source_registry_id}",
        "local_path": normalized.local_path or normalized.source_path or f"data/knowledge/external_candidates/{normalized.source_file}",
        "page": 1,
        "section": "expert_source_registry",
        "paragraph_index": 0,
        "char_start": 0,
        "char_end": None,
        "text": _expert_chunk_text(record),
        "language": str(record.get("language") or "en"),
        "evidence_domain": normalized.evidence_domain.value,
        "knowledge_layer": "document_index",
        "domain_pack": normalized.domain_pack,
        "allowed_use": normalized.allowed_use.value,
        "prescription_permission": normalized.prescription_permission.value,
        "quality_tier": normalized.quality_tier,
        "exclude_from_training_generation": normalized.prescription_permission.value != "can_write_core",
        "needs_review": normalized.needs_review,
        "review_status": normalized.review_status.value,
    }
    data["char_end"] = len(data["text"])
    return data


def build_expert_preview_chunks(
    *,
    registry_path: Path,
    base_preview_path: Path,
    preview_out: Path,
) -> Dict[str, Any]:
    base_chunks = _load_jsonl(base_preview_path)
    registry_rows = _load_jsonl(registry_path)
    existing_source_ids = {str(chunk.get("source_registry_id") or "") for chunk in base_chunks}
    expert_records = [row for row in registry_rows if str(row.get("source_registry_id") or "") not in existing_source_ids]
    expert_chunks = [_record_to_chunk(record, index) for index, record in enumerate(expert_records, start=1)]
    all_chunks = [*base_chunks, *expert_chunks]
    _write_jsonl(preview_out, all_chunks)
    return {
        "base_chunk_count": len(base_chunks),
        "expert_chunk_count": len(expert_chunks),
        "total_chunk_count": len(all_chunks),
        "preview_out": str(preview_out),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build expert-source chunk_schema_v2 preview without replacing v2 runtime.")
    parser.add_argument("--registry", required=True)
    parser.add_argument("--base-preview", default=str(ROOT / "data" / "knowledge" / "governance" / "chunk_schema_v2_preview.jsonl"))
    parser.add_argument("--preview-out", required=True)
    args = parser.parse_args()
    report = build_expert_preview_chunks(
        registry_path=Path(args.registry),
        base_preview_path=Path(args.base_preview),
        preview_out=Path(args.preview_out),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
