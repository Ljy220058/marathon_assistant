from marathon_qa_assistant.services.kb.evidence_binding import evidence_from_vector_hit
from marathon_qa_assistant.services.kb.models import EvidenceDomain
from marathon_qa_assistant.services.kb.prescription_permissions import permission_for_domain


def test_vector_hit_becomes_explanation_only_evidence_binding():
    binding = evidence_from_vector_hit(
        {
            "source_file": "马拉松训练原理.pdf",
            "source_path": "C:/kb/马拉松训练原理.pdf",
            "page": 12,
            "chunk_id": "chunk_12",
            "text": "Long run should be placed with recovery around it.",
            "score": 0.82,
        },
        evidence_domain="sports_science_reference",
    )

    assert binding.evidence_id == "chunk_12"
    assert binding.evidence_domain.value == "sports_science_reference"
    assert binding.knowledge_layer.value == "document_index"
    assert binding.retrieval_mode.value == "vector"
    assert binding.prescription_permission.value == "explanation_only"
    assert binding.page == 12
    assert binding.score == 0.82


def test_v2_vector_hit_preserves_source_registry_and_permission_metadata():
    binding = evidence_from_vector_hit(
        {
            "source_registry_id": "src_protocol_approved",
            "source_file": "approved-protocol.md",
            "source_url": "https://example.com/approved-protocol",
            "page": 4,
            "section": "week-structure",
            "chunk_id": "chunk_v2",
            "text": "A reviewed protocol may define structure boundaries.",
            "score": 0.91,
            "evidence_domain": "protocol",
            "knowledge_layer": "document_index",
            "domain_pack": "training_protocols",
            "allowed_use": "core_prescription",
            "prescription_permission": "can_write_core",
            "quality_tier": "approved",
        }
    )

    assert binding.source_registry_id == "src_protocol_approved"
    assert binding.evidence_domain.value == "protocol"
    assert binding.prescription_permission.value == "can_write_core"
    assert binding.trace["source_url"] == "https://example.com/approved-protocol"
    assert binding.trace["section"] == "week-structure"
    assert binding.trace["domain_pack"] == "training_protocols"


def test_only_protocol_and_action_library_can_write_core_fields():
    assert permission_for_domain(EvidenceDomain.PROTOCOL).value == "can_write_core"
    assert permission_for_domain(EvidenceDomain.ACTION_LIBRARY).value == "can_write_core"
    assert permission_for_domain(EvidenceDomain.SPORTS_SCIENCE_REFERENCE).value == "explanation_only"
    assert permission_for_domain(EvidenceDomain.LLM_GENERAL_KNOWLEDGE).value == "blocked_needs_evidence"
