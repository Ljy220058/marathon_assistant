from marathon_qa_assistant.services.kb.evidence_chain import (
    EVIDENCE_CHAIN_DISPLAY_MODES,
    build_evidence_chain_payload,
    build_model_general_knowledge_item,
    build_needs_evidence_item,
)


def test_evidence_chain_preserves_verified_source_metadata_without_public_source_path():
    payload = build_evidence_chain_payload(
        query="threshold run",
        evidence_bundle={
            "evidence_items": [
                {
                    "evidence_id": "chunk-1",
                    "source_registry_id": "src_protocol_approved",
                    "source_file": "approved-protocol.md",
                    "source_path": "C:/private/kb/approved-protocol.md",
                    "page": 4,
                    "chunk_id": "chunk-1",
                    "text": "Reviewed protocol text.",
                    "score": 0.91,
                    "trace": {
                        "source_url": "https://example.com/protocol",
                        "section": "week-structure",
                        "retrieval_mode": "vector",
                    },
                    "evidence_domain": "protocol",
                    "knowledge_layer": "document_index",
                    "allowed_use": "core_prescription",
                    "prescription_permission": "can_write_core",
                    "quality_tier": "approved",
                    "review_status": "approved",
                }
            ],
            "health": {"index_schema_version": "chunk_schema_v2", "runtime_core_prescription_enabled": True},
        },
    )

    item = payload["items"][0]
    assert item["display_mode"] == "verified_source"
    assert item["source_url"] == "https://example.com/protocol"
    assert item["page"] == 4
    assert item["section"] == "week-structure"
    assert item["source_registry_id"] == "src_protocol_approved"
    assert "source_path" not in item
    assert item["expert_metadata"]["source_path"] == "C:/private/kb/approved-protocol.md"
    assert payload["answer_source_mode"] == "verified_rag"
    assert payload["source_path_leak_count"] == 0


def test_model_general_knowledge_item_has_no_fake_citation_fields():
    item = build_model_general_knowledge_item("缺少本地证据时的保守说明。")

    assert item["display_mode"] == "model_general_knowledge"
    assert item["source_label"] == "模型常识说明"
    assert item["source_url"] == ""
    assert item["page"] is None
    assert item["chunk_id"] == ""
    assert item["prescription_permission"] == "blocked_needs_evidence"


def test_needs_evidence_item_blocks_core_prescription():
    item = build_needs_evidence_item(
        "missing_action_library_match",
        field_binding={"day_key": "w1d2", "field": "main_set"},
    )

    assert item["display_mode"] == "needs_evidence"
    assert item["field_binding"]["field"] == "main_set"
    assert item["prescription_permission"] == "blocked_needs_evidence"
    assert item["source_url"] == ""


def test_empty_payload_can_return_model_general_knowledge_without_citation():
    payload = build_evidence_chain_payload(
        query="如何理解轻松跑",
        answer_source_mode="model_general_knowledge",
        evidence_bundle={"evidence_items": [], "health": {"index_schema_version": "legacy"}},
    )

    assert payload["answer_source_mode"] == "model_general_knowledge"
    assert payload["items"][0]["display_mode"] == "model_general_knowledge"
    assert payload["items"][0]["source_url"] == ""
    assert payload["runtime_index_schema_version"] == "legacy"


def test_display_modes_include_graph_and_legacy_boundaries():
    assert EVIDENCE_CHAIN_DISPLAY_MODES == [
        "verified_source",
        "model_general_knowledge",
        "needs_evidence",
        "graph_hint",
        "legacy_explanation",
        "rejected_source",
    ]


def test_runner_projection_hides_expert_evidence_fields():
    from marathon_qa_assistant.apps.api_app import _project_runner_query_response
    from marathon_qa_assistant.apps.schemas import QueryResponse

    response = QueryResponse(
        report="answer",
        token_usage={},
        audit_scores={},
        guided_questions=[],
        evidence_chain=build_evidence_chain_payload(
            query="q",
            evidence_bundle={
                "evidence_items": [
                    {
                        "evidence_id": "chunk-1",
                        "source_registry_id": "src_secret",
                        "source_file": "approved.md",
                        "source_path": "C:/private/approved.md",
                        "page": 1,
                        "chunk_id": "chunk-1",
                        "trace": {"source_url": "https://example.com/approved"},
                        "evidence_domain": "protocol",
                        "prescription_permission": "can_write_core",
                    }
                ]
            },
        ),
    )

    projected = _project_runner_query_response(response)
    item = projected["evidence_chain"]["items"][0]
    assert "source_registry_id" not in item
    assert "chunk_id" not in item
    assert "expert_metadata" not in item
    assert "C:/private/approved.md" not in str(projected)
