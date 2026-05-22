from marathon_qa_assistant.services.kb.models import (
    EvidenceDomain,
    KnowledgeLayer,
    PrescriptionPermission,
    RetrievalMode,
    SourceRecord,
    SourceQuality,
)
from marathon_qa_assistant.services.kb.source_registry import (
    build_source_registry_id,
    normalize_source_record,
)


def test_kb_model_enums_are_stable_for_frontend_and_reviewers():
    assert EvidenceDomain.PROTOCOL.value == "protocol"
    assert EvidenceDomain.ACTION_LIBRARY.value == "action_library"
    assert EvidenceDomain.LLM_GENERAL_KNOWLEDGE.value == "llm_general_knowledge"
    assert KnowledgeLayer.SOURCE_REGISTRY.value == "source_registry"
    assert RetrievalMode.GRAPH_LOCAL.value == "graph_local"
    assert PrescriptionPermission.CAN_WRITE_CORE.value == "can_write_core"


def test_source_quality_has_required_review_fields():
    quality = SourceQuality(
        tier="protocol",
        freshness_status="current",
        applicability=["half_marathon", "advanced_runner"],
        contraindications=["acute_pain", "medical_red_flag"],
        notes="Internal HMP protocol source.",
    )

    assert quality.tier == "protocol"
    assert "acute_pain" in quality.contraindications


def test_source_record_requires_stable_id_and_domain():
    record = normalize_source_record(
        {
            "title": "Half Marathon HMP Protocol",
            "source_file": "docs/product/half_marathon_hmp_protocol.md",
            "evidence_domain": "protocol",
            "knowledge_layer": "source_registry",
            "source_path": "docs/product/half_marathon_hmp_protocol.md",
        }
    )

    assert isinstance(record, SourceRecord)
    assert record.source_registry_id == build_source_registry_id("docs/product/half_marathon_hmp_protocol.md")
    assert record.evidence_domain.value == "protocol"
    assert record.knowledge_layer.value == "source_registry"


def test_source_record_rejects_fake_empty_source():
    try:
        normalize_source_record({"title": "No source", "evidence_domain": "protocol"})
    except ValueError as exc:
        assert "source_file or source_path is required" in str(exc)
    else:
        raise AssertionError("source without path should fail")
