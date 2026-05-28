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
DEFAULT_RELEASE_REPORT_PATH = GOVERNANCE_DIR / "kb_release_report.json"


def load_v2_preview_chunks(preview_path: Path = DEFAULT_PREVIEW_PATH) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    with Path(preview_path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            chunks.append(json.loads(line))
    return chunks


def _runtime_buildable_chunks(chunks: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[str]]:
    buildable: List[Dict[str, Any]] = []
    skipped_ids: List[str] = []
    for chunk in chunks:
        # Ollama 对空字符串会返回空 embedding，先过滤避免 FAISS 构建时崩溃。
        if str(chunk.get("text") or "").strip():
            buildable.append(chunk)
        else:
            skipped_ids.append(str(chunk.get("chunk_id") or ""))
    return buildable, skipped_ids


def _load_release_gate(path: Optional[Path]) -> Dict[str, Any]:
    if path is None or not Path(path).exists():
        return {}
    # 生产替换门禁以治理发布报告为准，避免 runtime manifest 继续写死审批计数。
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    approved_records = int(report.get("approved_records") or 0)
    ready_records = int(report.get("ready_records") or 0)
    commercial_release_ready = bool(report.get("commercial_release_ready"))
    blockers = report.get("replacement_blockers") or report.get("readiness_blockers") or report.get("blockers") or []
    if not commercial_release_ready and not blockers:
        blockers = ["commercial_release_ready=false"]
    return {
        "approved_records": approved_records,
        "ready_records": ready_records,
        "source_review_ready": approved_records > 0 and ready_records > 0,
        "can_replace_runtime": commercial_release_ready,
        "replacement_blockers": blockers,
        "first_batch_release_ready": bool(report.get("first_batch_release_ready")),
        "first_batch_ready_domain_packs": list(report.get("first_batch_ready_domain_packs") or []),
        "first_batch_blockers": list(report.get("first_batch_blockers") or []),
        "domain_gap_summary": dict(report.get("domain_gap_summary") or {}),
        "top_actionable_domain_gaps": list(report.get("actionable_domain_gaps") or [])[:5],
    }


def _default_release_gate() -> Dict[str, Any]:
    return {
        "approved_records": 0,
        "ready_records": 0,
        "source_review_ready": False,
        "can_replace_runtime": False,
        "replacement_blockers": [
            "approved_records=0",
            "ready_records=0",
            "v2 runtime is enabled for preview retrieval but not commercial-approved core prescription evidence",
        ],
        "first_batch_release_ready": False,
        "first_batch_ready_domain_packs": [],
        "first_batch_blockers": ["release_report_missing"],
        "domain_gap_summary": {},
        "top_actionable_domain_gaps": [],
    }


def build_v2_runtime_index(
    *,
    preview_path: Path = DEFAULT_PREVIEW_PATH,
    output_dir: Path = V2_VECTOR_DIR,
    manifest_path: Optional[Path] = DEFAULT_MANIFEST_PATH,
    release_report_path: Optional[Path] = DEFAULT_RELEASE_REPORT_PATH,
    commercial_staging: bool = False,
    save_func: Callable[[Path, List[Dict[str, Any]], Any, Any, Any], Dict[str, Any]] = save_outputs,
) -> Dict[str, Any]:
    chunks = load_v2_preview_chunks(preview_path)
    health = check_chunk_schema_v2_health(chunks)
    if health.get("status") != "ok" and not health.get("ok"):
        raise ValueError(f"v2 preview chunks are not runtime-buildable: {health}")

    runtime_chunks, skipped_empty_text_chunk_ids = _runtime_buildable_chunks(chunks)
    if not runtime_chunks:
        raise ValueError(
            "v2 preview chunks are schema-valid but no runtime-buildable v2 chunks contain non-empty text: "
            f"{skipped_empty_text_chunk_ids}"
        )

    outputs = save_func(Path(output_dir), runtime_chunks, None, None, None)
    release_gate = {**_default_release_gate(), **_load_release_gate(release_report_path)}
    if commercial_staging:
        release_gate.update(
            {
                "candidate_preview": False,
                "commercial_staging": True,
                "release_ready": False,
                "can_replace_runtime": False,
                "replacement_blockers": sorted(
                    set([*release_gate.get("replacement_blockers", []), "commercial_staging_not_release_runtime"])
                ),
            }
        )
    report = {
        "ok": True,
        "schema_version": "chunk_schema_v2",
        "status": "commercial_staging_ready" if commercial_staging else "runtime_preview_ready",
        "preview_path": str(preview_path),
        "current_runtime_vector_dir": str(output_dir),
        "runtime_vector_dir": str(output_dir),
        "preview_chunk_count": len(chunks),
        "runtime_chunk_count": len(runtime_chunks),
        "skipped_empty_text_chunk_count": len(skipped_empty_text_chunk_ids),
        "skipped_empty_text_chunk_ids": skipped_empty_text_chunk_ids,
        "metadata_completeness": float(health.get("metadata_completeness") or 0.0),
        "runtime_index_schema_version": "chunk_schema_v2",
        "runtime_use_enabled": True,
        "outputs": outputs,
        **release_gate,
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
