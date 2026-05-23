from marathon_qa_assistant.services.kb.models import (
    AllowedUse,
    EvidenceDomain,
    KnowledgeLayer,
    PrescriptionPermission,
    RetrievalMode,
    SourceReviewStatus,
    SourceRecord,
    SourceQuality,
)
from marathon_qa_assistant.services.kb.source_registry import (
    build_registry_v2_from_paper_cards,
    build_source_registry_id,
    load_paper_cards,
    normalize_source_record,
    source_record_is_ready,
    validate_source_registry_v2,
)


def test_kb_model_enums_are_stable_for_frontend_and_reviewers():
    assert EvidenceDomain.PROTOCOL.value == "protocol"
    assert EvidenceDomain.ACTION_LIBRARY.value == "action_library"
    assert EvidenceDomain.LLM_GENERAL_KNOWLEDGE.value == "llm_general_knowledge"
    assert EvidenceDomain.REHAB_STRENGTH_MOBILITY.value == "rehab_strength_mobility"
    assert EvidenceDomain.NUTRITION_RACE_FUELING.value == "nutrition_race_fueling"
    assert EvidenceDomain.ENVIRONMENT_RACE_CONTEXT.value == "environment_race_context"
    assert KnowledgeLayer.SOURCE_REGISTRY.value == "source_registry"
    assert RetrievalMode.GRAPH_LOCAL.value == "graph_local"
    assert PrescriptionPermission.CAN_WRITE_CORE.value == "can_write_core"
    assert AllowedUse.CORE_PRESCRIPTION.value == "core_prescription"
    assert SourceReviewStatus.SEED_ONLY.value == "seed_only"
    assert SourceReviewStatus.APPROVED.value == "approved"


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
    assert record.prescription_permission.value == "explanation_only"
    assert record.content_hash


def test_source_record_rejects_fake_empty_source():
    try:
        normalize_source_record({"title": "No source", "evidence_domain": "protocol"})
    except ValueError as exc:
        assert "source_file or source_path is required" in str(exc)
    else:
        raise AssertionError("source without path should fail")


def test_source_registry_v2_rejects_core_permission_outside_protocol_or_action_library():
    record = normalize_source_record(
        {
            "title": "General sports science note",
            "source_file": "sports_science.md",
            "evidence_domain": "sports_science_reference",
            "knowledge_layer": "source_registry",
            "allowed_use": "core_prescription",
            "prescription_permission": "can_write_core",
        }
    )

    assert "core_permission_domain_violation" in validate_source_registry_v2(record)


def test_internal_seed_records_are_not_ready_even_if_marked_reviewed_false():
    record = normalize_source_record(
        {
            "title": "Seed Action Card",
            "source_file": "seed/action-card.json",
            "source_type": "internal_structured_rule_seed",
            "evidence_domain": "action_library",
            "knowledge_layer": "domain_pack",
            "allowed_use": "core_prescription",
            "prescription_permission": "can_write_core",
            "needs_review": False,
            "review_status": "approved",
        }
    )

    assert record.review_status == SourceReviewStatus.SEED_ONLY
    assert record.needs_review is True
    assert source_record_is_ready(record) is False


def test_only_approved_valid_sources_are_release_ready():
    reviewed = normalize_source_record(
        {
            "title": "Reviewed Protocol",
            "source_file": "protocol-reviewed.md",
            "evidence_domain": "protocol",
            "knowledge_layer": "source_registry",
            "allowed_use": "core_prescription",
            "prescription_permission": "can_write_core",
            "needs_review": False,
            "review_status": "reviewed",
        }
    )
    approved = normalize_source_record(
        {
            "title": "Approved Protocol",
            "source_file": "protocol-approved.md",
            "evidence_domain": "protocol",
            "knowledge_layer": "source_registry",
            "allowed_use": "core_prescription",
            "prescription_permission": "can_write_core",
            "needs_review": False,
            "review_status": "approved",
        }
    )

    assert reviewed.needs_review is True
    assert source_record_is_ready(reviewed) is False
    assert approved.needs_review is False
    assert source_record_is_ready(approved) is True


def test_paper_cards_can_generate_registry_v2_records_without_marking_mojibake_ready():
    cards = load_paper_cards("data/knowledge/curated/academic_literature/paper_cards.jsonl")
    records = build_registry_v2_from_paper_cards(cards)

    assert len(records) >= 33
    assert all(record.source_registry_id for record in records)
    assert all(not validate_source_registry_v2(record) for record in records)
    assert not any(source_record_is_ready(record) for record in records if "????" in record.metadata.get("purpose", ""))
