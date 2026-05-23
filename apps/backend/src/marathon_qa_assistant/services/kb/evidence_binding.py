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


def _knowledge_layer(value: str) -> KnowledgeLayer:
    try:
        return KnowledgeLayer(value)
    except ValueError:
        return KnowledgeLayer.DOCUMENT_INDEX


def _prescription_permission(value: str) -> PrescriptionPermission:
    try:
        return PrescriptionPermission(value)
    except ValueError:
        return PrescriptionPermission.EXPLANATION_ONLY


def evidence_from_vector_hit(hit: Dict[str, Any], evidence_domain: str = "sports_science_reference") -> EvidenceBinding:
    source_path = str(hit.get("source_path") or "")
    source_file = str(hit.get("source_file") or "")
    source_key = source_path or source_file or "unknown_vector_source"
    chunk_id = str(hit.get("chunk_id") or "")
    evidence_id = chunk_id or build_source_registry_id(source_key)
    hit_domain = str(hit.get("evidence_domain") or evidence_domain)
    source_registry_id = str(hit.get("source_registry_id") or build_source_registry_id(source_key))

    return EvidenceBinding(
        evidence_id=evidence_id,
        source_registry_id=source_registry_id,
        evidence_domain=_domain(hit_domain),
        knowledge_layer=_knowledge_layer(str(hit.get("knowledge_layer") or KnowledgeLayer.DOCUMENT_INDEX.value)),
        retrieval_mode=RetrievalMode.VECTOR,
        prescription_permission=_prescription_permission(str(hit.get("prescription_permission") or "")),
        source_file=source_file,
        source_path=source_path,
        page=hit.get("page"),
        chunk_id=chunk_id,
        snippet=str(hit.get("text") or hit.get("snippet") or ""),
        score=float(hit.get("score") or 0.0),
        trace={
            "source": "vector_hit",
            "source_url": str(hit.get("source_url") or ""),
            "section": str(hit.get("section") or ""),
            "domain_pack": str(hit.get("domain_pack") or ""),
            "allowed_use": str(hit.get("allowed_use") or ""),
            "quality_tier": str(hit.get("quality_tier") or ""),
        },
    )
