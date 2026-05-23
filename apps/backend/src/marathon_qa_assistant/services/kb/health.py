from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List


CORE_ALLOWED_DOMAINS = {"protocol", "action_library"}
CHUNK_SCHEMA_V2_REQUIRED_FIELDS = {
    "chunk_id",
    "source_registry_id",
    "source_file",
    "source_url",
    "local_path",
    "page",
    "section",
    "text",
    "language",
    "evidence_domain",
    "knowledge_layer",
    "domain_pack",
    "allowed_use",
    "prescription_permission",
    "quality_tier",
}


def _as_dict(binding: Any) -> Dict[str, Any]:
    if isinstance(binding, dict):
        return binding
    return {
        "source_path": getattr(binding, "source_path", ""),
        "source_file": getattr(binding, "source_file", ""),
        "page": getattr(binding, "page", None),
        "evidence_domain": getattr(getattr(binding, "evidence_domain", ""), "value", getattr(binding, "evidence_domain", "")),
        "prescription_permission": getattr(
            getattr(binding, "prescription_permission", ""),
            "value",
            getattr(binding, "prescription_permission", ""),
        ),
    }


def check_evidence_bindings_health(bindings: List[Any]) -> Dict[str, Any]:
    normalized = [_as_dict(binding) for binding in bindings]
    total = len(normalized)
    missing_source_count = sum(
        1 for item in normalized if not (str(item.get("source_path") or "").strip() or str(item.get("source_file") or "").strip())
    )
    missing_page_count = sum(1 for item in normalized if item.get("page") in {None, "", 0})
    core_permission_violation_count = sum(
        1
        for item in normalized
        if str(item.get("prescription_permission") or "") == "can_write_core"
        and str(item.get("evidence_domain") or "") not in CORE_ALLOWED_DOMAINS
    )

    if total == 0:
        status = "empty"
    elif missing_source_count or core_permission_violation_count:
        status = "needs_review"
    else:
        status = "ok"

    return {
        "total": total,
        "missing_source_count": missing_source_count,
        "missing_page_count": missing_page_count,
        "core_permission_violation_count": core_permission_violation_count,
        "status": status,
    }


def _missing_fields(item: Dict[str, Any], required_fields: Iterable[str]) -> List[str]:
    return [
        field
        for field in required_fields
        if item.get(field) in {None, ""} or (field == "page" and item.get(field) == 0)
    ]


def check_chunk_schema_v2_health(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(chunks)
    missing_by_chunk: List[Dict[str, Any]] = []
    core_permission_violation_count = 0
    absolute_path_leak_count = 0
    for item in chunks:
        missing = _missing_fields(item, CHUNK_SCHEMA_V2_REQUIRED_FIELDS)
        if missing:
            missing_by_chunk.append({"chunk_id": item.get("chunk_id", ""), "missing": missing})
        if (
            str(item.get("prescription_permission") or "") == "can_write_core"
            and str(item.get("evidence_domain") or "") not in CORE_ALLOWED_DOMAINS
        ):
            core_permission_violation_count += 1
        local_path = str(item.get("local_path") or item.get("source_path") or "")
        if ":" in local_path[:4] or local_path.startswith("\\\\"):
            absolute_path_leak_count += 1

    status = "ok"
    if total == 0:
        status = "empty"
    elif missing_by_chunk or core_permission_violation_count or absolute_path_leak_count:
        status = "needs_review"
    return {
        "total": total,
        "metadata_complete_count": total - len(missing_by_chunk),
        "metadata_completeness": 1.0 if total == 0 else (total - len(missing_by_chunk)) / total,
        "missing_by_chunk": missing_by_chunk,
        "core_permission_violation_count": core_permission_violation_count,
        "absolute_path_leak_count": absolute_path_leak_count,
        "status": status,
    }


def summarize_runtime_index_schema(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(chunks)
    if total == 0:
        return {
            "total": 0,
            "index_schema_version": "empty",
            "metadata_complete_count": 0,
            "metadata_completeness": 0.0,
            "legacy_chunk_count": 0,
            "v2_chunk_count": 0,
            "mixed_schema": False,
            "core_permission_violation_count": 0,
            "runtime_core_prescription_enabled": False,
        }

    complete_count = 0
    core_permission_violation_count = 0
    for item in chunks:
        if not _missing_fields(item, CHUNK_SCHEMA_V2_REQUIRED_FIELDS):
            complete_count += 1
        if (
            str(item.get("prescription_permission") or "") == "can_write_core"
            and str(item.get("evidence_domain") or "") not in CORE_ALLOWED_DOMAINS
        ):
            core_permission_violation_count += 1

    legacy_count = total - complete_count
    if complete_count == total:
        index_schema_version = "chunk_schema_v2"
    elif complete_count == 0:
        index_schema_version = "legacy"
    else:
        index_schema_version = "mixed"

    return {
        "total": total,
        "index_schema_version": index_schema_version,
        "metadata_complete_count": complete_count,
        "metadata_completeness": complete_count / total,
        "legacy_chunk_count": legacy_count,
        "v2_chunk_count": complete_count,
        "mixed_schema": index_schema_version == "mixed",
        "core_permission_violation_count": core_permission_violation_count,
        "runtime_core_prescription_enabled": index_schema_version == "chunk_schema_v2"
        and core_permission_violation_count == 0,
    }


def summarize_legacy_chunk_index(chunks: List[Dict[str, Any]] | Path) -> Dict[str, Any]:
    import json

    if isinstance(chunks, Path):
        loaded: List[Dict[str, Any]] = []
        for line in chunks.read_text(encoding="utf-8").splitlines():
            if line.strip():
                loaded.append(json.loads(line))
        chunks = loaded
    total = len(chunks)
    keys = sorted({key for item in chunks for key in item.keys()})
    source_files = sorted({str(item.get("source_file") or "") for item in chunks if item.get("source_file")})
    has_v2 = CHUNK_SCHEMA_V2_REQUIRED_FIELDS.issubset(set(keys))
    return {
        "total": total,
        "source_file_count": len(source_files),
        "keys": keys,
        "is_legacy_index": not has_v2,
        "legacy_reason": "" if has_v2 else "chunks lack source_registry_id/domain_pack/allowed_use/prescription_permission metadata",
    }
