from __future__ import annotations

from typing import Any, Dict

from marathon_qa_assistant.services.kb.models import (
    EvidenceBinding,
    EvidenceDomain,
    KnowledgeLayer,
    PrescriptionPermission,
    RetrievalMode,
)
from marathon_qa_assistant.services.kb.source_registry import build_source_registry_id


def _domain(value: str) -> EvidenceDomain:
    try:
        return EvidenceDomain(value)
    except ValueError:
        return EvidenceDomain.SPORTS_SCIENCE_REFERENCE


def evidence_from_vector_hit(hit: Dict[str, Any], evidence_domain: str = "sports_science_reference") -> EvidenceBinding:
    source_path = str(hit.get("source_path") or "")
    source_file = str(hit.get("source_file") or "")
    source_key = source_path or source_file or "unknown_vector_source"
    chunk_id = str(hit.get("chunk_id") or "")
    evidence_id = chunk_id or build_source_registry_id(source_key)

    return EvidenceBinding(
        evidence_id=evidence_id,
        source_registry_id=build_source_registry_id(source_key),
        evidence_domain=_domain(evidence_domain),
        knowledge_layer=KnowledgeLayer.DOCUMENT_INDEX,
        retrieval_mode=RetrievalMode.VECTOR,
        prescription_permission=PrescriptionPermission.EXPLANATION_ONLY,
        source_file=source_file,
        source_path=source_path,
        page=hit.get("page"),
        chunk_id=chunk_id,
        snippet=str(hit.get("text") or hit.get("snippet") or ""),
        score=float(hit.get("score") or 0.0),
        trace={"source": "vector_hit"},
    )
