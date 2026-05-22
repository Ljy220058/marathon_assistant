from __future__ import annotations

import hashlib
from typing import Any, Dict

from marathon_qa_assistant.services.kb.models import (
    EvidenceBinding,
    EvidenceDomain,
    KnowledgeLayer,
    RetrievalMode,
)
from marathon_qa_assistant.services.kb.prescription_permissions import permission_for_domain
from marathon_qa_assistant.services.kb.source_registry import build_source_registry_id


def _domain(value: Any) -> EvidenceDomain:
    try:
        return EvidenceDomain(str(value or EvidenceDomain.SPORTS_SCIENCE_REFERENCE.value))
    except ValueError:
        return EvidenceDomain.SPORTS_SCIENCE_REFERENCE


def evidence_from_graph_edge(edge: Dict[str, Any], retrieval_mode: RetrievalMode = RetrievalMode.GRAPH_LOCAL) -> EvidenceBinding:
    evidence_raw = edge.get("evidence") if isinstance(edge.get("evidence"), dict) else {}
    chunk_id = str(evidence_raw.get("chunk_id") or "")
    text_span = str(evidence_raw.get("text_span") or "")
    source_file = str(evidence_raw.get("source_file") or evidence_raw.get("source") or "unknown_graph_source")
    source_path = str(evidence_raw.get("source_path") or evidence_raw.get("path") or "")
    source_key = source_path or source_file or "unknown_graph_source"
    domain = _domain(evidence_raw.get("evidence_domain"))
    confidence = float(evidence_raw.get("confidence") or 0.0)
    evidence_id_seed = chunk_id or hashlib.md5(text_span.encode("utf-8")).hexdigest()[:8]

    return EvidenceBinding(
        evidence_id=f"graph_{evidence_id_seed}",
        source_registry_id=build_source_registry_id(source_key),
        evidence_domain=domain,
        knowledge_layer=KnowledgeLayer.DOMAIN_GRAPH,
        retrieval_mode=retrieval_mode,
        prescription_permission=permission_for_domain(domain),
        source_file=source_file,
        source_path=source_path,
        page=evidence_raw.get("page"),
        chunk_id=chunk_id,
        snippet=text_span[:300],
        score=confidence,
        trace={
            "source": "graph_edge",
            "relation": str(edge.get("relation") or ""),
            "canonical_relation": str(edge.get("canonical_relation") or edge.get("relation") or ""),
            "source_node": str(edge.get("source") or ""),
            "target_node": str(edge.get("target") or ""),
        },
    )


def graph_binding_to_legacy_evidence(binding: EvidenceBinding) -> Dict[str, Any]:
    return {
        "evidence_id": binding.evidence_id,
        "kind": "graph",
        "source_registry_id": binding.source_registry_id,
        "knowledge_layer": binding.knowledge_layer.value,
        "evidence_domain": binding.evidence_domain.value,
        "retrieval_mode": binding.retrieval_mode.value,
        "prescription_permission": binding.prescription_permission.value,
        "source_file": binding.source_file,
        "source_path": binding.source_path,
        "page": binding.page,
        "chunk_id": binding.chunk_id,
        "snippet": binding.snippet,
        "text": binding.snippet,
        "vector_score": 0.0,
        "retrieval_score": 0.0,
        "graph_confidence": binding.score,
        "entity_overlap": 0.0,
        "fusion_bonus": 0.0,
        "hybrid_score": 0.0,
        "citation_label": "",
        "trace": binding.trace,
    }
