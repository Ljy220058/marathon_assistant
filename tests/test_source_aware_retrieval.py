from marathon_qa_assistant.nodes.profile_and_retrieval import build_ranked_evidence
from marathon_qa_assistant.services.kb.evidence_chain import build_evidence_chain_payload


def test_ready_body_evidence_ranks_above_registry_only_for_same_score():
    vector_hits = [
        {
            "chunk_id": "registry-1",
            "source_file": "registry.metadata",
            "source_registry_id": "src_registry",
            "section": "registry_preview",
            "text": "Training Errors and Running Related Injuries: A Systematic Review.",
            "score": 0.8,
            "source_status": "registry_only",
            "has_full_text": False,
        },
        {
            "chunk_id": "body-1",
            "source_file": "body.md",
            "source_registry_id": "src_body",
            "section": "document_paragraph",
            "text": "Running injuries are associated with abrupt training load changes.",
            "score": 0.8,
            "source_status": "ready",
            "has_full_text": True,
        },
    ]

    ranked = build_ranked_evidence(
        query="running injury training load",
        vector_hits=vector_hits,
        graph_edges=[],
        entities=["running", "injury"],
        top_k=None,
    )

    assert ranked[0]["chunk_id"] == "body-1"
    assert ranked[0]["source_status"] == "ready"
    assert ranked[0]["has_full_text"] is True
    assert ranked[0]["evidence_kind"] == "body_chunk"
    assert ranked[1]["display_mode"] == "legacy_explanation"
    assert ranked[1]["evidence_kind"] == "source_registry_line"


def test_registry_only_evidence_is_marked_not_core_writable():
    ranked = build_ranked_evidence(
        query="injury prevention",
        vector_hits=[
            {
                "chunk_id": "registry-1",
                "source_file": "registry.metadata",
                "source_registry_id": "src_registry",
                "section": "registry_preview",
                "text": "A paper exists about injury prevention.",
                "score": 0.9,
                "source_status": "registry_only",
                "has_full_text": False,
            }
        ],
        graph_edges=[],
        entities=["injury"],
        top_k=None,
    )

    assert ranked[0]["source_status"] == "registry_only"
    assert ranked[0]["has_full_text"] is False
    assert ranked[0]["can_write_core"] is False
    assert ranked[0]["explanation_only"] is True
    assert ranked[0]["display_mode"] == "legacy_explanation"
    assert ranked[0]["evidence_kind"] == "source_registry_line"


def test_evidence_chain_preserves_source_status_fields():
    chain = build_evidence_chain_payload(
        query="injury prevention",
        evidence_bundle={
            "evidence_items": [
                {
                    "chunk_id": "body-1",
                    "source_file": "body.md",
                    "source_registry_id": "src_body",
                    "source_status": "ready",
                    "has_full_text": True,
                    "evidence_kind": "body_chunk",
                    "text_span": "Running injuries are associated with training load.",
                    "display_mode": "verified_source",
                }
            ]
        },
        answer_source_mode="verified_rag",
    )

    item = chain["items"][0]
    assert item["source_status"] == "ready"
    assert item["has_full_text"] is True
    assert item["evidence_kind"] == "body_chunk"
