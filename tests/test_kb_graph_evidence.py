import asyncio
import json

from marathon_qa_assistant.nodes import common as common_module
from marathon_qa_assistant.nodes import profile_and_retrieval as profile_module
from marathon_qa_assistant.nodes.profile_and_retrieval import build_ranked_evidence
from marathon_qa_assistant.services.kb import conflict_governance
from marathon_qa_assistant.services.kb.evidence_chain import build_evidence_chain_payload
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


def test_graph_only_without_locator_is_graph_hint_and_not_citable():
    payload = build_evidence_chain_payload(
        query="recovery relationship",
        evidence_bundle={
            "evidence_items": [
                {
                    "evidence_id": "graph-recovery",
                    "citation_label": "[1]",
                    "kind": "graph",
                    "source_file": "",
                    "page": None,
                    "chunk_id": "",
                    "text": "Recovery is connected to long run load.",
                    "evidence_domain": "sports_science_reference",
                    "retrieval_mode": "graph_local",
                    "prescription_permission": "explanation_only",
                }
            ],
            "health": {"index_schema_version": "chunk_schema_v2", "runtime_core_prescription_enabled": True},
        },
        answer_text="图谱提示不应变成可点击引用 [1]。",
    )

    item = payload["items"][0]
    assert item["display_mode"] == "graph_hint"
    assert item["source_url"] == ""
    assert item["page"] is None
    assert item["section"] == ""
    assert payload["citation_gate"]["citable_labels"] == []
    assert payload["fake_citation_violations"][0]["reason"] == "non_citable_display_mode"


def test_fusion_does_not_use_graph_only_locator_as_verified_source_anchor():
    ranked = build_ranked_evidence(
        query="threshold workout",
        vector_hits=[
            {
                "chunk_id": "shared-chunk",
                "source_file": "approved-protocol.md",
                "source_url": "https://example.com/approved-protocol",
                "page": None,
                "section": "",
                "text": "Threshold workout guidance.",
                "score": 0.9,
                "evidence_domain": "protocol",
                "prescription_permission": "can_write_core",
                "quality_tier": "approved",
                "review_status": "approved",
            }
        ],
        graph_edges=[
            {
                "source": "threshold",
                "target": "tempo",
                "relation": "supports",
                "evidence": {
                    "source": "approved-protocol.md",
                    "page": 4,
                    "chunk_id": "shared-chunk",
                    "text_span": "Graph relation has a page but is not the vector locator.",
                    "evidence_domain": "protocol",
                    "confidence": 0.8,
                },
            }
        ],
        entities=["threshold"],
        top_k=1,
    )
    payload = build_evidence_chain_payload(
        query="threshold workout",
        evidence_bundle={
            "evidence_items": ranked,
            "health": {"index_schema_version": "chunk_schema_v2", "runtime_core_prescription_enabled": True},
        },
    )

    item = payload["items"][0]
    assert item["display_mode"] != "verified_source"
    assert item["source_url"] == ""
    assert item["page"] is None
    assert payload["citation_gate"]["citable_labels"] == []


def test_hard_constraint_is_decision_gate_not_fusion_evidence():
    ranked = build_ranked_evidence(
        query="runner has red flag pain",
        vector_hits=[
            {
                "chunk_id": "shared-safety",
                "source_file": "safety.md",
                "section": "document_paragraph",
                "text": "General training context.",
                "score": 0.8,
                "prescription_permission": "can_write_core",
            }
        ],
        graph_edges=[
            {
                "source": "red flag pain",
                "target": "training",
                "relation": "stop_training_medical_red_flag",
                "evidence": {
                    "source": "safety.md",
                    "chunk_id": "shared-safety",
                    "text_span": "Red flag symptoms require stopping training and referral.",
                    "confidence": 0.95,
                    "evidence_domain": "medical_risk",
                },
            }
        ],
        entities=["red flag pain"],
        top_k=None,
    )

    gate = ranked[0]
    assert gate["kind"] == "decision_gate"
    assert gate["retrieval_mode"] == "decision_gate"
    assert gate["evidence_source_type"] == "decision_gate"
    assert gate["decision_gate"] is True
    assert gate["hybrid_score"] == 0.0
    assert all(item["kind"] != "fusion" for item in ranked)

    payload = build_evidence_chain_payload(
        query="runner has red flag pain",
        evidence_bundle={
            "evidence_items": ranked,
            "health": {"index_schema_version": "chunk_schema_v2", "runtime_core_prescription_enabled": True},
        },
    )
    assert payload["items"][0]["decision_gate"] is True
    assert payload["items"][0]["evidence_source_type"] == "decision_gate"


def test_conflict_detection_writes_governance_queue(monkeypatch, tmp_path):
    queue_path = tmp_path / "evidence_conflict_review_queue.jsonl"
    monkeypatch.setattr(conflict_governance, "DEFAULT_CONFLICT_REVIEW_QUEUE", queue_path)

    ranked = build_ranked_evidence(
        query="force training despite conflicting evidence",
        vector_hits=[
            {
                "chunk_id": "conflict-chunk",
                "source_file": "training.md",
                "section": "document_paragraph",
                "text": "Continue training under normal conditions.",
                "score": 0.75,
                "prescription_permission": "can_write_core",
            }
        ],
        graph_edges=[
            {
                "source": "injury pain",
                "target": "training",
                "relation": "conflict",
                "evidence": {
                    "source": "training.md",
                    "chunk_id": "conflict-chunk",
                    "text_span": "Pain conflicts with continued training.",
                    "confidence": 0.7,
                    "evidence_domain": "medical_risk",
                },
            }
        ],
        entities=["training"],
        top_k=1,
    )

    assert ranked[0]["conflict_detected"] is True
    assert ranked[0]["governance_conflict_id"].startswith("conflict_")
    rows = [json.loads(line) for line in queue_path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["conflict_id"] == ranked[0]["governance_conflict_id"]
    assert rows[0]["status"] == "open"


def test_get_graph_context_skips_search_when_graph_source_mismatches_runtime(monkeypatch):
    monkeypatch.setattr(common_module, "graph_fusion_runtime_enabled", lambda: False)

    class TrapGraphEngine:
        def search_graph(self, *_args, **_kwargs):
            raise AssertionError("graph search should be skipped when fusion is disabled")

    monkeypatch.setattr(common_module, "graph_engine", TrapGraphEngine())

    context, mermaid = common_module.get_graph_context(["threshold"])

    assert context == ""
    assert "Graph fusion disabled" in mermaid


def test_evidence_retriever_skips_graph_search_when_graph_source_mismatches_runtime(monkeypatch):
    monkeypatch.setattr(profile_module, "infer_entities", lambda *_args, **_kwargs: ["threshold"])
    monkeypatch.setattr(profile_module, "semantic_match_entities", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(profile_module, "expand_entities_for_kg", lambda entities: entities)
    monkeypatch.setattr(profile_module, "graph_fusion_runtime_enabled", lambda: False)
    monkeypatch.setattr(profile_module, "build_rag_sources", lambda hits: [])
    monkeypatch.setattr(profile_module, "evaluate_plan_evidence", lambda *_args, **_kwargs: {"required": False, "has_plan_evidence": True})
    monkeypatch.setattr(profile_module, "build_ranked_evidence", lambda **_kwargs: [])
    monkeypatch.setattr(
        profile_module,
        "build_evidence_bundle",
        lambda **_kwargs: {"query": "threshold", "evidence_items": [], "health": {}},
    )

    async def fake_get_context(*_args, **_kwargs):
        return []

    monkeypatch.setattr(profile_module, "get_context", fake_get_context)

    class TrapGraphEngine:
        def search_graph(self, *_args, **_kwargs):
            raise AssertionError("graph search should be skipped when fusion is disabled")

    monkeypatch.setattr(profile_module, "graph_engine", TrapGraphEngine())

    result = asyncio.run(
        profile_module.evidence_retriever_node(
            {"query": "threshold workout", "entities": ["threshold"], "selected_entities": [], "intent_type": "qa", "category": "", "token_usage": {}},
            None,
        )
    )

    assert result["graph_context"] == ""
    assert "Graph fusion disabled" in result["mermaid_graph"]
