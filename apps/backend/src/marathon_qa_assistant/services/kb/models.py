from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EvidenceDomain(str, Enum):
    PROTOCOL = "protocol"
    ACTION_LIBRARY = "action_library"
    SPORTS_SCIENCE_REFERENCE = "sports_science_reference"
    MEDICAL_SAFETY = "medical_safety"
    REHAB_STRENGTH_MOBILITY = "rehab_strength_mobility"
    NUTRITION_RACE_FUELING = "nutrition_race_fueling"
    ENVIRONMENT_RACE_CONTEXT = "environment_race_context"
    COMPETITOR_PRODUCT_REFERENCE = "competitor_product_reference"
    USER_PROFILE_CASE = "user_profile_case"
    LLM_GENERAL_KNOWLEDGE = "llm_general_knowledge"


class KnowledgeLayer(str, Enum):
    SOURCE_REGISTRY = "source_registry"
    DOCUMENT_INDEX = "document_index"
    DOMAIN_GRAPH = "domain_graph"
    PRESCRIPTION_LIBRARY = "prescription_library"
    EVALUATION = "evaluation"
    DOMAIN_PACK = "domain_pack"


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


class AllowedUse(str, Enum):
    CORE_PRESCRIPTION = "core_prescription"
    EXPLANATION = "explanation"
    RISK_GATE = "risk_gate"
    REHAB_GUIDANCE = "rehab_guidance"
    NUTRITION_GUIDANCE = "nutrition_guidance"
    PRODUCT_DESIGN_REFERENCE = "product_design_reference"
    EVALUATION_ONLY = "evaluation_only"


class EvidenceDisplayMode(str, Enum):
    VERIFIED_SOURCE = "verified_source"
    MODEL_GENERAL_KNOWLEDGE = "model_general_knowledge"
    NEEDS_EVIDENCE = "needs_evidence"
    GRAPH_HINT = "graph_hint"
    LEGACY_EXPLANATION = "legacy_explanation"
    REJECTED_SOURCE = "rejected_source"


class SourceReviewStatus(str, Enum):
    CANDIDATE = "candidate"
    EXTRACTED = "extracted"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    BLOCKED = "blocked"
    SEED_ONLY = "seed_only"


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
    source_type: str = ""
    authors_or_owner: str = ""
    year: str = ""
    source_url: str = ""
    local_path: str = ""
    license_status: str = "unknown"
    download_status: str = "unknown"
    content_hash: str = ""
    domain_pack: str = ""
    allowed_use: AllowedUse = AllowedUse.EXPLANATION
    prescription_permission: PrescriptionPermission = PrescriptionPermission.EXPLANATION_ONLY
    quality_tier: str = "unknown"
    freshness_status: str = "unknown"
    applicable_runner_segments: List[str] = field(default_factory=list)
    contraindications: List[str] = field(default_factory=list)
    needs_review: bool = True
    review_status: SourceReviewStatus = SourceReviewStatus.CANDIDATE
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


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    source_registry_id: str
    source_file: str
    source_url: str
    local_path: str
    page: Optional[int]
    section: str
    paragraph_index: Optional[int]
    char_start: Optional[int]
    char_end: Optional[int]
    text: str
    language: str
    evidence_domain: EvidenceDomain
    knowledge_layer: KnowledgeLayer
    domain_pack: str
    allowed_use: AllowedUse
    prescription_permission: PrescriptionPermission
    quality_tier: str
    exclude_from_training_generation: bool = False
    needs_review: bool = False


@dataclass(frozen=True)
class CoverageRow:
    domain_pack: str
    subdomain: str
    target_source_count: int
    current_source_count: int
    target_rule_count: int
    current_rule_count: int
    target_question_count: int
    current_question_count: int
    minimum_quality_tier: str
    can_write_core: bool
    gap_status: str


@dataclass(frozen=True)
class EvidenceDrawerPayload:
    source_label: str
    source_url: str
    page: Optional[int]
    section: str
    evidence_domain: str
    prescription_permission: str
    display_mode: EvidenceDisplayMode
    user_facing_summary: str
    expert_metadata: Dict[str, Any] = field(default_factory=dict)
