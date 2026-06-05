from marathon_qa_assistant.services.kb.evidence_chain import (
    EVIDENCE_CHAIN_DISPLAY_MODES,
    build_evidence_chain_payload,
    build_model_general_knowledge_item,
    build_needs_evidence_item,
    validate_citation_faithfulness,
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


def test_evidence_confidence_downgrades_low_relevance_verified_source():
    payload = build_evidence_chain_payload(
        query="半马补给",
        evidence_bundle={
            "evidence_items": [
                {
                    "evidence_id": "low-relevance",
                    "citation_label": "[1]",
                    "source_file": "nutrition.md",
                    "page": 3,
                    "trace": {"source_url": "https://example.com/nutrition", "section": "fueling"},
                    "evidence_domain": "nutrition_race_fueling",
                    "prescription_permission": "can_write_core",
                    "relevance_score": 0.42,
                    "score_breakdown": {"relevance": 0.42},
                }
            ]
        },
    )

    item = payload["items"][0]
    assert item["confidence_level"] == "low"
    assert item["display_mode"] == "needs_evidence"
    assert payload["answer_source_mode"] == "needs_evidence"
    assert "相关度低于" in item["user_facing_summary"]


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
    from marathon_qa_assistant.apps.response_projection import _project_runner_query_response
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


def test_verified_explanation_source_bound_to_core_field_keeps_answer_in_needs_evidence_mode():
    payload = build_evidence_chain_payload(
        query="安排一次阈值跑",
        evidence_bundle={
            "evidence_items": [
                {
                    "evidence_id": "chunk-explanation",
                    "citation_label": "[1]",
                    "source_file": "candidate-training.url",
                    "page": 1,
                    "trace": {"source_url": "https://example.com/candidate", "section": "training"},
                    "evidence_domain": "protocol",
                    "retrieval_mode": "vector",
                    "prescription_permission": "explanation_only",
                    "allowed_use": "explanation",
                    "field_binding": {"day_key": "w1d2", "field": "main_set"},
                }
            ],
            "health": {"index_schema_version": "chunk_schema_v2", "runtime_core_prescription_enabled": True},
        },
        answer_text="候选资料只能解释，不能直接写主训练。",
    )

    item = payload["items"][0]
    assert payload["answer_source_mode"] == "needs_evidence"
    assert payload["core_permission_violations"][0]["field"] == "main_set"
    assert item["display_mode"] == "verified_source"
    assert "不能作为核心训练处方依据" in item["user_facing_summary"]


def test_medical_safety_explanation_source_sets_medical_referral_answer_mode():
    payload = build_evidence_chain_payload(
        query="跑步时胸痛怎么办",
        evidence_bundle={
            "evidence_items": [
                {
                    "evidence_id": "chunk-medical",
                    "citation_label": "[1]",
                    "source_file": "heat-illness.url",
                    "page": 1,
                    "trace": {"source_url": "https://example.com/heat", "section": "red-flags"},
                    "evidence_domain": "medical_safety",
                    "retrieval_mode": "vector",
                    "prescription_permission": "explanation_only",
                    "allowed_use": "risk_gate",
                }
            ],
            "health": {"index_schema_version": "chunk_schema_v2", "runtime_core_prescription_enabled": True},
        },
        answer_text="出现红旗症状应停止训练并寻求医疗帮助。",
    )

    item = payload["items"][0]
    assert payload["answer_source_mode"] == "medical_referral"
    assert item["display_mode"] == "verified_source"
    assert "风险提醒" in item["user_facing_summary"]


def test_validate_citation_faithfulness_blocks_unknown_numbered_reference():
    payload = build_evidence_chain_payload(
        query="threshold run",
        evidence_bundle={
            "evidence_items": [
                {
                    "evidence_id": "chunk-1",
                    "citation_label": "[1]",
                    "source_file": "approved.md",
                    "page": 2,
                    "trace": {"source_url": "https://example.com/approved", "section": "threshold"},
                    "evidence_domain": "protocol",
                    "prescription_permission": "can_write_core",
                }
            ]
        },
        answer_text="阈值跑可以这样安排 [99]。",
    )

    assert payload["fake_citation_violations"][0]["citation_label"] == "[99]"
    assert payload["fake_citation_violations"][0]["reason"] == "unknown_citation"


def test_validate_citation_faithfulness_blocks_model_and_legacy_citations():
    chain = {
        "items": [
            {
                **build_model_general_knowledge_item("模型常识"),
                "citation_label": "[1]",
            },
            {
                "evidence_id": "legacy-1",
                "citation_label": "[2]",
                "display_mode": "legacy_explanation",
                "source_label": "legacy.pdf",
                "source_url": "",
                "page": None,
                "section": "",
                "prescription_permission": "explanation_only",
            },
        ]
    }

    audit = validate_citation_faithfulness("说明 [1] 和背景 [2]。", chain)

    reasons = {item["reason"] for item in audit["violations"]}
    assert audit["status"] == "failed"
    assert audit["fake_citation_count"] == 2
    assert "model_general_knowledge_cited" in reasons
    assert "legacy_explanation_cited" in reasons


def test_validate_citation_faithfulness_allows_verified_located_source():
    audit = validate_citation_faithfulness(
        "已定位来源 [1]。",
        {
            "items": [
                {
                    "evidence_id": "chunk-1",
                    "citation_label": "[1]",
                    "display_mode": "verified_source",
                    "source_url": "https://example.com/approved",
                    "page": 2,
                    "section": "",
                    "prescription_permission": "can_write_core",
                }
            ]
        },
    )

    assert audit["status"] == "passed"
    assert audit["fake_citation_count"] == 0


def test_legacy_runtime_downgrade_preserves_safe_display_locator_fields():
    payload = build_evidence_chain_payload(
        query="nutrition plan",
        evidence_bundle={
            "evidence_items": [
                {
                    "evidence_id": "chunk-runtime-page-hint",
                    "citation_label": "[1]",
                    "source_file": "Nutrition for Marathon Running.pdf",
                    "page": 3,
                    "chunk_id": "2016+-+Nutrition+for+Marathon+Running_p0003_c0002",
                    "text": "Carbohydrate intake guidance for marathon runners.",
                    "trace": {"source_url": "https://example.com/nutrition", "section": "Fueling"},
                    "evidence_domain": "protocol",
                    "retrieval_mode": "vector",
                    "prescription_permission": "can_write_core",
                    "allowed_use": "core_prescription",
                }
            ],
            "health": {
                "index_schema_version": "legacy",
                "runtime_core_prescription_enabled": False,
            },
        },
    )

    item = payload["items"][0]
    assert item["display_mode"] == "legacy_explanation"
    assert item["source_label"] == "Nutrition for Marathon Running.pdf"
    assert item["text_span"] == "Carbohydrate intake guidance for marathon runners."
    assert item["chunk_id"] == "2016+-+Nutrition+for+Marathon+Running_p0003_c0002"
    assert item["source_url"] == ""
    assert item["page"] is None
    assert item["section"] == ""
    assert item["page_hint"] == 3
    assert "p.3" in item["locator_hint"]
    assert "source_path" not in item
    assert "local_path" not in item


def test_chunk_id_page_hint_does_not_become_verified_page_without_source_url():
    payload = build_evidence_chain_payload(
        query="nutrition plan",
        evidence_bundle={
            "evidence_items": [
                {
                    "evidence_id": "chunk-page-hint-only",
                    "source_file": "Nutrition for Marathon Running.pdf",
                    "page": None,
                    "chunk_id": "2016+-+Nutrition+for+Marathon+Running_p0003_c0002",
                    "text": "Fueling guidance.",
                    "evidence_domain": "sports_science_reference",
                    "retrieval_mode": "vector",
                    "prescription_permission": "explanation_only",
                    "allowed_use": "explanation",
                }
            ],
            "health": {
                "index_schema_version": "legacy",
                "runtime_core_prescription_enabled": False,
            },
        },
    )

    item = payload["items"][0]
    assert item["display_mode"] == "legacy_explanation"
    assert item["page"] is None
    assert item["page_hint"] == 3
    assert "p.3" in item["locator_hint"]
    assert item["source_url"] == ""


def test_legacy_runtime_downgrades_located_vector_source_to_legacy_explanation():
    payload = build_evidence_chain_payload(
        query="threshold run",
        evidence_bundle={
            "evidence_items": [
                {
                    "evidence_id": "chunk-legacy-runtime",
                    "citation_label": "[1]",
                    "source_file": "approved.md",
                    "page": 2,
                    "trace": {"source_url": "https://example.com/approved", "section": "threshold"},
                    "evidence_domain": "protocol",
                    "retrieval_mode": "vector",
                    "prescription_permission": "can_write_core",
                }
            ],
            "health": {
                "index_schema_version": "legacy",
                "runtime_core_prescription_enabled": False,
            },
        },
        answer_text="不应该可点击 [1]。",
    )

    item = payload["items"][0]
    assert item["display_mode"] == "legacy_explanation"
    assert item["source_url"] == ""
    assert payload["citation_gate"]["status"] == "failed"
    assert payload["fake_citation_violations"][0]["reason"] == "legacy_explanation_cited"


def test_evidence_chain_limits_visible_items_to_default_top_k():
    evidence_items = []
    for index in range(10):
        evidence_items.append(
            {
                "evidence_id": f"chunk-{index}",
                "citation_label": f"[{index + 1}]",
                "source_file": f"source-{index}.md",
                "page": index + 1,
                "trace": {"source_url": f"https://example.com/{index}", "section": "body"},
                "evidence_domain": "protocol",
                "retrieval_mode": "vector",
                "prescription_permission": "can_write_core",
            }
        )

    payload = build_evidence_chain_payload(
        query="threshold run",
        evidence_bundle={"evidence_items": evidence_items},
    )

    assert len(payload["items"]) == 8
    assert payload["items"][0]["citation_label"] == "[1]"
    assert payload["items"][-1]["citation_label"] == "[8]"
