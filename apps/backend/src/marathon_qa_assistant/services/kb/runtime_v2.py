from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from marathon_qa_assistant.core.app_state import DATA_DIR, V2_VECTOR_DIR
from marathon_qa_assistant.services.kb.health import check_chunk_schema_v2_health
from marathon_qa_assistant.services.vector_store import save_outputs


GOVERNANCE_DIR = DATA_DIR / "knowledge" / "governance"
DEFAULT_PREVIEW_PATH = GOVERNANCE_DIR / "chunk_schema_v2_preview.jsonl"
DEFAULT_MANIFEST_PATH = GOVERNANCE_DIR / "runtime_index_v2_manifest.json"


def load_v2_preview_chunks(preview_path: Path = DEFAULT_PREVIEW_PATH) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    with Path(preview_path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            chunks.append(json.loads(line))
    return chunks


def build_v2_runtime_index(
    *,
    preview_path: Path = DEFAULT_PREVIEW_PATH,
    output_dir: Path = V2_VECTOR_DIR,
    manifest_path: Optional[Path] = DEFAULT_MANIFEST_PATH,
    save_func: Callable[[Path, List[Dict[str, Any]], Any, Any, Any], Dict[str, Any]] = save_outputs,
) -> Dict[str, Any]:
    chunks = load_v2_preview_chunks(preview_path)
    health = check_chunk_schema_v2_health(chunks)
    if health.get("status") != "ok" and not health.get("ok"):
        raise ValueError(f"v2 preview chunks are not runtime-buildable: {health}")

    outputs = save_func(Path(output_dir), chunks, None, None, None)
    report = {
        "ok": True,
        "schema_version": "chunk_schema_v2",
        "status": "runtime_preview_ready",
        "preview_path": str(preview_path),
        "current_runtime_vector_dir": str(output_dir),
        "runtime_vector_dir": str(output_dir),
        "runtime_chunk_count": len(chunks),
        "metadata_completeness": float(health.get("metadata_completeness") or 0.0),
        "runtime_index_schema_version": "chunk_schema_v2",
        "runtime_use_enabled": True,
        "can_replace_runtime": False,
        "replacement_blockers": [
            "approved_records=0",
            "ready_records=0",
            "v2 runtime is enabled for preview retrieval but not commercial-approved core prescription evidence",
        ],
        "outputs": outputs,
    }
    if manifest_path is not None:
        _write_manifest(Path(manifest_path), report)
    return report


def _write_manifest(path: Path, update: Dict[str, Any]) -> None:
    existing: Dict[str, Any] = {}
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
    merged = {**existing, **update}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
