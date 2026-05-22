from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EvidenceDomain(str, Enum):
    PROTOCOL = "protocol"
    ACTION_LIBRARY = "action_library"
    SPORTS_SCIENCE_REFERENCE = "sports_science_reference"
    MEDICAL_SAFETY = "medical_safety"
    COMPETITOR_PRODUCT_REFERENCE = "competitor_product_reference"
    USER_PROFILE_CASE = "user_profile_case"
    LLM_GENERAL_KNOWLEDGE = "llm_general_knowledge"


class KnowledgeLayer(str, Enum):
    SOURCE_REGISTRY = "source_registry"
    DOCUMENT_INDEX = "document_index"
    DOMAIN_GRAPH = "domain_graph"
    PRESCRIPTION_LIBRARY = "prescription_library"
    EVALUATION = "evaluation"


class RetrievalMode(str, Enum):
    VECTOR = "vector"
    LEXICAL = "lexical"
    GRAPH_LOCAL = "graph_local"
    GRAPH_GLOBAL = "graph_global"
    GRAPH_DRIFT = "graph_drift"
    ACTION_LIBRARY = "action_library"
    PROTOCOL_RULE = "protocol_rule"
    NONE = "none"


class PrescriptionPermission(str, Enum):
    CAN_WRITE_CORE = "can_write_core"
    EXPLANATION_ONLY = "explanation_only"
    BLOCKED_NEEDS_EVIDENCE = "blocked_needs_evidence"


@dataclass(frozen=True)
class SourceQuality:
    tier: str
    freshness_status: str
    applicability: List[str] = field(default_factory=list)
    contraindications: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class SourceRecord:
    source_registry_id: str
    title: str
    evidence_domain: EvidenceDomain
    knowledge_layer: KnowledgeLayer
    source_file: str = ""
    source_path: str = ""
    published_at: str = ""
    updated_at: str = ""
    quality: Optional[SourceQuality] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceBinding:
    evidence_id: str
    source_registry_id: str
    evidence_domain: EvidenceDomain
    knowledge_layer: KnowledgeLayer
    retrieval_mode: RetrievalMode
    prescription_permission: PrescriptionPermission
    source_file: str = ""
    source_path: str = ""
    page: Optional[int] = None
    chunk_id: str = ""
    snippet: str = ""
    score: float = 0.0
    trace: Dict[str, Any] = field(default_factory=dict)
