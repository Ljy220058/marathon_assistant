from marathon_qa_assistant.core.evidence_bundle import build_evidence_bundle
from marathon_qa_assistant.nodes.common import build_rag_sources
from marathon_qa_assistant.nodes.profile_and_retrieval import build_ranked_evidence
from marathon_qa_assistant.services.kb.evidence_chain import build_evidence_chain_payload
from marathon_qa_assistant.services.vector_store import _doc_to_hit, _merge_ranked_hits

try:
    from langchain_core.documents import Document
except Exception:  # pragma: no cover - compatibility with older langchain splits
    from langchain.schema import Document


V2_HIT = {
    "chunk_id": "chunk-v2",
    "source_registry_id": "src_protocol_approved",
    "source_file": "approved-protocol.md",
    "source_path": "data/knowledge/approved-protocol.md",
    "source_url": "https://example.com/approved-protocol",
    "page": 7,
    "section": "week-structure",
    "text": "Approved protocol text for week structure.",
    "score": 0.92,
    "language": "en",
    "evidence_domain": "protocol",
    "knowledge_layer": "document_index",
    "domain_pack": "training_protocols",
    "allowed_use": "core_prescription",
    "prescription_permission": "can_write_core",
    "quality_tier": "approved",
    "review_status": "approved",
    "needs_review": False,
}


def test_build_rag_sources_preserves_v2_metadata():
    sources = build_rag_sources([V2_HIT])

    source = sources[0]
    assert source["source_registry_id"] == "src_protocol_approved"
    assert source["source_url"] == "https://example.com/approved-protocol"
    assert source["section"] == "week-structure"
    assert source["evidence_domain"] == "protocol"
    assert source["prescription_permission"] == "can_write_core"
    assert source["review_status"] == "approved"


def test_build_ranked_evidence_preserves_v2_metadata_for_vector_hits():
    ranked = build_ranked_evidence(
        query="half marathon week structure",
        vector_hits=[V2_HIT],
        graph_edges=[],
        entities=["half marathon", "week"],
        top_k=1,
    )

    item = ranked[0]
    assert item["source_registry_id"] == "src_protocol_approved"
    assert item["source_url"] == "https://example.com/approved-protocol"
    assert item["section"] == "week-structure"
    assert item["evidence_domain"] == "protocol"
    assert item["prescription_permission"] == "can_write_core"
    assert item["trace"]["source_url"] == "https://example.com/approved-protocol"
    assert item["trace"]["allowed_use"] == "core_prescription"


def test_v2_metadata_survives_bundle_to_canonical_evidence_chain():
    ranked = build_ranked_evidence(
        query="half marathon week structure",
        vector_hits=[V2_HIT],
        graph_edges=[],
        entities=["half marathon", "week"],
        top_k=1,
    )
    bundle = build_evidence_bundle(
        query="half marathon week structure",
        ranked_evidence=ranked,
        health={"index_schema_version": "chunk_schema_v2", "runtime_core_prescription_enabled": True},
    )
    chain = build_evidence_chain_payload(query="half marathon week structure", evidence_bundle=bundle)

    item = chain["items"][0]
    assert item["display_mode"] == "verified_source"
    assert item["source_registry_id"] == "src_protocol_approved"
    assert item["source_url"] == "https://example.com/approved-protocol"
    assert item["page"] == 7
    assert item["section"] == "week-structure"
    assert item["prescription_permission"] == "can_write_core"


def test_legacy_hit_is_explicitly_explanation_only_after_chain_projection():
    legacy_sources = build_rag_sources(
        [
            {
                "chunk_id": "legacy-1",
                "source_file": "legacy.pdf",
                "page": 1,
                "text": "Legacy text without v2 metadata.",
                "score": 0.8,
            }
        ]
    )
    bundle = build_evidence_bundle(
        query="legacy",
        rag_sources=legacy_sources,
        health={"index_schema_version": "legacy", "runtime_core_prescription_enabled": False},
    )
    chain = build_evidence_chain_payload(query="legacy", evidence_bundle=bundle)

    item = chain["items"][0]
    assert item["display_mode"] == "legacy_explanation"
    assert item["prescription_permission"] == "explanation_only"
    assert item["source_url"] == ""


def test_merge_ranked_hits_keeps_more_complete_metadata_for_same_chunk():
    first_hit = {
        "chunk_id": "same-chunk",
        "source_file": "legacy.pdf",
        "source_path": "data/vector_kb/default/legacy.pdf",
        "page": 1,
        "text": "Legacy sparse text.",
        "score": 0.95,
        "rank_score": 0.0,
        "distance": 0.05,
    }
    richer_hit = {
        **first_hit,
        "score": 0.72,
        "distance": 0.15,
        "source_registry_id": "src_protocol_approved",
        "source_url": "https://example.com/approved-protocol",
        "section": "week-structure",
        "evidence_domain": "protocol",
        "knowledge_layer": "document_index",
        "domain_pack": "training_protocols",
        "allowed_use": "core_prescription",
        "prescription_permission": "can_write_core",
        "quality_tier": "approved",
        "review_status": "approved",
        "needs_review": False,
    }

    merged = _merge_ranked_hits([[first_hit], [richer_hit]], top_k=1)

    item = merged[0]
    assert item["score"] == 0.95
    assert item["distance"] == 0.05
    assert item["source_registry_id"] == "src_protocol_approved"
    assert item["source_url"] == "https://example.com/approved-protocol"
    assert item["review_status"] == "approved"


def test_doc_to_hit_preserves_review_status_metadata():
    doc = Document(
        page_content="Approved protocol text.",
        metadata={
            "chunk_id": "doc-v2",
            "source_file": "approved.md",
            "source_registry_id": "src_protocol_approved",
            "source_url": "https://example.com/approved",
            "page": 3,
            "section": "threshold",
            "evidence_domain": "protocol",
            "knowledge_layer": "document_index",
            "prescription_permission": "can_write_core",
            "review_status": "approved",
        },
    )

    hit = _doc_to_hit(doc, distance=0.2)

    assert hit["source_registry_id"] == "src_protocol_approved"
    assert hit["review_status"] == "approved"
    assert hit["prescription_permission"] == "can_write_core"
