from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from marathon_qa_assistant.services.kb.models import (
    EvidenceDomain,
    KnowledgeLayer,
    SourceQuality,
    SourceRecord,
)


def build_source_registry_id(source: str) -> str:
    normalized = " ".join(str(source or "").replace("\\", "/").split()).strip().lower()
    if not normalized:
        raise ValueError("source is required")
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"src_{digest}"


def _quality_from_dict(value: Any) -> Optional[SourceQuality]:
    if not isinstance(value, dict):
        return None
    return SourceQuality(
        tier=str(value.get("tier") or "unknown"),
        freshness_status=str(value.get("freshness_status") or "unknown"),
        applicability=[str(item) for item in value.get("applicability") or []],
        contraindications=[str(item) for item in value.get("contraindications") or []],
        notes=str(value.get("notes") or ""),
    )


def normalize_source_record(payload: Dict[str, Any]) -> SourceRecord:
    source_file = str(payload.get("source_file") or "").strip()
    source_path = str(payload.get("source_path") or "").strip()
    source_key = source_path or source_file
    if not source_key:
        raise ValueError("source_file or source_path is required")

    evidence_domain = EvidenceDomain(str(payload.get("evidence_domain") or EvidenceDomain.SPORTS_SCIENCE_REFERENCE.value))
    knowledge_layer = KnowledgeLayer(str(payload.get("knowledge_layer") or KnowledgeLayer.SOURCE_REGISTRY.value))
    source_registry_id = str(payload.get("source_registry_id") or build_source_registry_id(source_key))

    return SourceRecord(
        source_registry_id=source_registry_id,
        title=str(payload.get("title") or source_file or source_path),
        evidence_domain=evidence_domain,
        knowledge_layer=knowledge_layer,
        source_file=source_file,
        source_path=source_path,
        published_at=str(payload.get("published_at") or ""),
        updated_at=str(payload.get("updated_at") or ""),
        quality=_quality_from_dict(payload.get("quality")),
        metadata=dict(payload.get("metadata") or {}),
    )
