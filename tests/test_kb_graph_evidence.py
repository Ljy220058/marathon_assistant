from marathon_qa_assistant.services.kb.graph_evidence import evidence_from_graph_edge
from marathon_qa_assistant.services.knowledge_graph import GraphEngine


def test_graph_edge_maps_to_explanation_only_binding_by_default():
    binding = evidence_from_graph_edge(
        {
            "source": "long run",
            "target": "recovery",
            "relation": "requires",
            "canonical_relation": "requires",
            "evidence": {
                "source": "docs/product/half_marathon_hmp_protocol.md",
                "source_path": "docs/product/half_marathon_hmp_protocol.md",
                "page": 8,
                "chunk_id": "hm_chunk_8",
                "text_span": "Long runs require recovery before the next quality session.",
                "confidence": 0.84,
            },
        }
    )

    assert binding.evidence_id == "graph_hm_chunk_8"
    assert binding.knowledge_layer.value == "domain_graph"
    assert binding.retrieval_mode.value == "graph_local"
    assert binding.evidence_domain.value == "sports_science_reference"
    assert binding.prescription_permission.value == "explanation_only"
    assert binding.page == 8
    assert binding.score == 0.84
    assert binding.trace["canonical_relation"] == "requires"


def test_graph_edge_allows_core_only_for_protocol_or_action_library_domain():
    protocol_binding = evidence_from_graph_edge(
        {
            "relation": "parameterized_by",
            "evidence": {
                "source": "docs/product/half_marathon_hmp_protocol.md",
                "chunk_id": "protocol_rule_1",
                "text_span": "HMP protocol defines the workout rule.",
                "evidence_domain": "protocol",
            },
        }
    )
    llm_binding = evidence_from_graph_edge(
        {
            "relation": "related_to",
            "evidence": {
                "source": "model",
                "chunk_id": "llm_note",
                "text_span": "General model knowledge.",
                "evidence_domain": "llm_general_knowledge",
            },
        }
    )

    assert protocol_binding.prescription_permission.value == "can_write_core"
    assert llm_binding.prescription_permission.value == "blocked_needs_evidence"


def test_graph_engine_facade_preserves_legacy_dict_with_layered_metadata():
    engine = GraphEngine.__new__(GraphEngine)
    evidence = engine.map_edge_to_evidence(
        {
            "source": "tempo",
            "target": "threshold",
            "relation": "targets",
            "canonical_relation": "targets",
            "evidence": {
                "source": "action_library.pdf",
                "source_path": "docs/kb/action_library.pdf",
                "page": 6,
                "chunk_id": "action_6",
                "text_span": "Tempo runs target threshold development.",
                "confidence": 0.91,
                "evidence_domain": "action_library",
            },
        }
    )

    assert evidence["kind"] == "graph"
    assert evidence["evidence_id"] == "graph_action_6"
    assert evidence["knowledge_layer"] == "domain_graph"
    assert evidence["retrieval_mode"] == "graph_local"
    assert evidence["evidence_domain"] == "action_library"
    assert evidence["prescription_permission"] == "can_write_core"
    assert evidence["source_registry_id"].startswith("src_")
    assert evidence["trace"]["canonical_relation"] == "targets"
