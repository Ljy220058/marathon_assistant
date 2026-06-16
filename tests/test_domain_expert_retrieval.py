"""
测试多领域 Expert Resolver 检索链路：
- _infer_expert_domain() 映射正确性
- _expert_domain_policy() 按 category 返回正确专家域
- build_ranked_evidence() 在向量/融合/图谱/decision_gate 分支中保留 expert_domain
- filter_hits_for_intent_domain() 与专家域过滤的叠加行为
"""
import asyncio

from marathon_qa_assistant.nodes import profile_and_retrieval as profile_module
from marathon_qa_assistant.nodes.profile_and_retrieval import (
    _expert_domain_policy,
    _infer_expert_domain,
    build_ranked_evidence,
    filter_hits_for_intent_domain,
)
from marathon_qa_assistant.services.kb import conflict_governance
from marathon_qa_assistant.services.kb.evidence_chain import build_evidence_chain_payload


# ═══════════════════════════════════════════════════════════════════════════════
# _infer_expert_domain 单元测试
# ═══════════════════════════════════════════════════════════════════════════════

def test_infer_expert_domain_direct_match():
    """直接传入 6 个合法 expert_domain 应原样返回"""
    assert _infer_expert_domain("training_theory") == "training_theory"
    assert _infer_expert_domain("workout_prescription") == "workout_prescription"
    assert _infer_expert_domain("rehab_safety") == "rehab_safety"
    assert _infer_expert_domain("nutrition") == "nutrition"
    assert _infer_expert_domain("race_strategy") == "race_strategy"
    assert _infer_expert_domain("capacity_management") == "capacity_management"


def test_infer_expert_domain_from_evidence_domain():
    """evidence_domain 术语应映射到正确的 expert_domain"""
    # nutrition 相关 evidence_domain → nutrition
    assert _infer_expert_domain("nutrition_race_fueling") == "nutrition"
    assert _infer_expert_domain("race_fueling") == "nutrition"
    assert _infer_expert_domain("hydration") == "nutrition"

    # rehab/injury 相关 → rehab_safety
    assert _infer_expert_domain("medical_risk") == "rehab_safety"
    assert _infer_expert_domain("injury") == "rehab_safety"
    assert _infer_expert_domain("rehabilitation") == "rehab_safety"
    assert _infer_expert_domain("recovery") == "rehab_safety"

    # training 相关 → training_theory
    assert _infer_expert_domain("protocol") == "training_theory"
    assert _infer_expert_domain("training_protocols") == "training_theory"
    assert _infer_expert_domain("action_library") == "training_theory"
    assert _infer_expert_domain("workout") == "training_theory"
    assert _infer_expert_domain("training") == "training_theory"


def test_infer_expert_domain_unknown_falls_back_to_training_theory():
    """未知领域默认回落到 training_theory，不抛异常"""
    assert _infer_expert_domain("") == "training_theory"
    assert _infer_expert_domain("some_unknown_domain") == "training_theory"
    assert _infer_expert_domain(None) == "training_theory"


def test_infer_expert_domain_case_insensitive():
    """映射应大小写不敏感"""
    assert _infer_expert_domain("NUTRITION_RACE_FUELING") == "nutrition"
    assert _infer_expert_domain("Medical_Risk") == "rehab_safety"
    assert _infer_expert_domain("Protocol") == "training_theory"


# ═══════════════════════════════════════════════════════════════════════════════
# _expert_domain_policy 单元测试
# ═══════════════════════════════════════════════════════════════════════════════

def test_expert_domain_policy_coach():
    """Coach 应拿到训练理论 + 训练处方 + 比赛策略"""
    domains = _expert_domain_policy("coach")
    assert domains == {"training_theory", "workout_prescription", "race_strategy"}


def test_expert_domain_policy_therapist():
    """Therapist 应拿到康复安全 + 容量管理"""
    domains = _expert_domain_policy("therapist")
    assert domains == {"rehab_safety", "capacity_management"}


def test_expert_domain_policy_nutritionist():
    """Nutritionist 应拿到营养 + 比赛策略"""
    domains = _expert_domain_policy("nutritionist")
    assert domains == {"nutrition", "race_strategy"}


def test_expert_domain_policy_planner():
    """Planner 应拿到训练理论 + 训练处方 + 容量管理"""
    domains = _expert_domain_policy("planner")
    assert domains == {"training_theory", "workout_prescription", "capacity_management"}


def test_expert_domain_policy_auditor():
    """Auditor 应拿到所有领域"""
    domains = _expert_domain_policy("auditor")
    assert domains == {
        "training_theory",
        "workout_prescription",
        "rehab_safety",
        "nutrition",
        "race_strategy",
        "capacity_management",
        "sport_psychology",
    }


def test_expert_domain_policy_unknown_category_defaults_to_coach():
    """未知 category 默认回落到 coach 领域集"""
    domains = _expert_domain_policy("unknown_role")
    assert domains == {"training_theory", "workout_prescription", "race_strategy"}
    domains_empty = _expert_domain_policy("")
    assert domains_empty == {"training_theory", "workout_prescription", "race_strategy"}


# ═══════════════════════════════════════════════════════════════════════════════
# build_ranked_evidence — expert_domain 传播测试
# ═══════════════════════════════════════════════════════════════════════════════

def test_vector_evidence_carries_expert_domain():
    """向量命中应携带 expert_domain 到输出 Evidence"""
    ranked = build_ranked_evidence(
        query="马拉松补给策略",
        vector_hits=[
            {
                "chunk_id": "nutrition-chunk-1",
                "source_file": "nutrition_guide.pdf",
                "text": "比赛前 3 天开始碳水加载。",
                "score": 0.92,
                "evidence_domain": "nutrition_race_fueling",
                "domain_pack": "nutrition_race_fueling",
                "source_status": "ready",
                "has_full_text": True,
                "section": "document_paragraph",
                "prescription_permission": "explanation_only",
            }
        ],
        graph_edges=[],
        entities=["补给", "碳水"],
        top_k=None,
    )

    assert len(ranked) == 1
    assert ranked[0]["expert_domain"] == "nutrition"
    assert ranked[0]["trace"]["expert_domain"] == "nutrition"


def test_graph_evidence_carries_expert_domain():
    """图谱命中（非融合）应携带 expert_domain"""
    ranked = build_ranked_evidence(
        query="伤后恢复跑步",
        vector_hits=[],
        graph_edges=[
            {
                "source": "injury",
                "target": "return_to_run",
                "relation": "guides",
                "canonical_relation": "guides",
                "evidence": {
                    "source": "rehab_guide.pdf",
                    "chunk_id": "rehab-chunk-5",
                    "text_span": "Gradual return to run after injury.",
                    "confidence": 0.85,
                    "evidence_domain": "rehab_strength_mobility",
                },
            }
        ],
        entities=["恢复", "跑步"],
        top_k=None,
    )

    assert len(ranked) == 1
    assert ranked[0]["kind"] == "graph"
    assert ranked[0]["expert_domain"] == "rehab_safety"
    assert ranked[0]["trace"]["expert_domain"] == "rehab_safety"


def test_fusion_preserves_expert_domain_from_both_sources():
    """向量+图谱融合时 expert_domain 应从两侧合并（图谱优先）"""
    ranked = build_ranked_evidence(
        query="比赛日补给",
        vector_hits=[
            {
                "chunk_id": "shared-chunk",
                "source_file": "race_nutrition.md",
                "text": "比赛日碳水摄入策略。",
                "score": 0.88,
                "evidence_domain": "nutrition_race_fueling",
                "section": "document_paragraph",
                "prescription_permission": "can_write_core",
            }
        ],
        graph_edges=[
            {
                "source": "race_day",
                "target": "fueling",
                "relation": "requires",
                "canonical_relation": "requires",
                "evidence": {
                    "source": "race_nutrition.md",
                    "chunk_id": "shared-chunk",
                    "text_span": "Race day fueling requires carb loading.",
                    "confidence": 0.82,
                    "evidence_domain": "nutrition_race_fueling",
                },
            }
        ],
        entities=["补给", "比赛日"],
        top_k=None,
    )

    assert len(ranked) == 1
    assert ranked[0]["kind"] == "fusion"
    assert ranked[0]["expert_domain"] == "nutrition"
    assert ranked[0]["trace"]["expert_domain"] == "nutrition"
    assert ranked[0]["trace"]["graph_hit"] is True


def test_decision_gate_carries_expert_domain():
    """硬约束 gate 也应携带 expert_domain"""
    ranked = build_ranked_evidence(
        query="膝盖剧痛还能跑吗",
        vector_hits=[
            {
                "chunk_id": "safety-chunk",
                "source_file": "safety.md",
                "text": "疼痛时需要停止训练。",
                "score": 0.75,
                "evidence_domain": "medical_safety",
                "section": "document_paragraph",
                "prescription_permission": "can_write_core",
            }
        ],
        graph_edges=[
            {
                "source": "severe knee pain",
                "target": "training",
                "relation": "stop_training_medical_red_flag",
                "canonical_relation": "stop_training_medical_red_flag",
                "evidence": {
                    "source": "medical_safety.pdf",
                    "chunk_id": "safety-chunk",
                    "text_span": "Severe knee pain is a medical red flag.",
                    "confidence": 0.95,
                    "evidence_domain": "medical_safety",
                },
            }
        ],
        entities=["膝盖", "疼痛"],
        top_k=None,
    )

    gates = [ev for ev in ranked if ev["kind"] == "decision_gate"]
    assert len(gates) >= 1
    gate = gates[0]
    assert gate["expert_domain"] == "rehab_safety"
    assert gate["trace"]["expert_domain"] == "rehab_safety"
    assert gate["decision_gate"] is True


def test_graph_hint_without_vector_carries_expert_domain():
    """纯图谱命中（无向量对应）应标记为 graph_hint 并携带 expert_domain"""
    ranked = build_ranked_evidence(
        query="如何提高乳酸阈值",
        vector_hits=[],
        graph_edges=[
            {
                "source": "tempo_run",
                "target": "lactate_threshold",
                "relation": "improves",
                "canonical_relation": "improves",
                "evidence": {
                    "source": "training_theory.pdf",
                    "chunk_id": "tempo-chunk",
                    "text_span": "Tempo runs improve lactate threshold.",
                    "confidence": 0.78,
                    "evidence_domain": "protocol",
                },
            }
        ],
        entities=["乳酸阈值", "节奏跑"],
        top_k=None,
    )

    assert len(ranked) == 1
    assert ranked[0]["kind"] == "graph"
    assert ranked[0]["expert_domain"] == "training_theory"
    assert ranked[0]["display_mode"] == "graph_hint"


def test_expert_domain_in_evidence_chain_payload():
    """evidence_chain 输出应保留 expert_domain"""
    ranked = build_ranked_evidence(
        query="碳水补给时机",
        vector_hits=[
            {
                "chunk_id": "fuel-chunk",
                "source_file": "fueling_guide.pdf",
                "source_url": "https://example.com/fueling",
                "page": 3,
                "text": "比赛前 2 小时摄入碳水。",
                "score": 0.91,
                "evidence_domain": "nutrition_race_fueling",
                "section": "document_paragraph",
                "prescription_permission": "can_write_core",
            }
        ],
        graph_edges=[],
        entities=["碳水", "补给"],
        top_k=None,
    )

    payload = build_evidence_chain_payload(
        query="碳水补给时机",
        evidence_bundle={
            "evidence_items": ranked,
            "health": {"index_schema_version": "chunk_schema_v2", "runtime_core_prescription_enabled": True},
        },
    )

    item = payload["items"][0]
    assert item["expert_domain"] == "nutrition"
    assert item["display_mode"] == "verified_source"


# ═══════════════════════════════════════════════════════════════════════════════
# filter_hits_for_intent_domain + 专家域过滤 叠加行为
# ═══════════════════════════════════════════════════════════════════════════════

def test_intent_domain_filter_ranks_nutrition_first():
    """营养相关 query 应把 nutrition_race_fueling 域命中排在前面"""
    hits = [
        {"chunk_id": "a", "text": "碳水补给", "score": 0.7, "evidence_domain": "nutrition_race_fueling"},
        {"chunk_id": "b", "text": "阈值训练", "score": 0.9, "evidence_domain": "protocol"},
        {"chunk_id": "c", "text": "水合策略", "score": 0.6, "evidence_domain": "nutrition_race_fueling"},
    ]

    filtered = filter_hits_for_intent_domain(hits, category="nutritionist", query="比赛怎么补给")

    # nutrition 域命中应排在前面
    assert filtered[0]["chunk_id"] == "a"
    assert filtered[1]["chunk_id"] == "c"
    assert filtered[2]["chunk_id"] == "b"
    assert filtered[0]["retrieval_domain_match"] == "nutrition"
    assert filtered[2]["retrieval_domain_mismatch"] == "nutrition"


def test_intent_domain_filter_preserves_order_without_match():
    """无匹配 policy 时原样返回"""
    hits = [
        {"chunk_id": "a", "text": "跑姿", "score": 0.8, "evidence_domain": "protocol"},
        {"chunk_id": "b", "text": "跑鞋", "score": 0.7, "evidence_domain": "sports_science_reference"},
    ]

    filtered = filter_hits_for_intent_domain(hits, category="coach", query="跑姿分析")

    assert len(filtered) == 2
    assert filtered[0]["chunk_id"] == "a"


def test_evidence_retriever_expert_domain_filter_by_category(monkeypatch):
    """不同 category 的 evidence_retriever_node 应拿到不同的 expert_domain 过滤命中"""
    # 构造命中：一半 nutrition，一半 training
    fake_hits = [
        {"chunk_id": "n1", "text": "碳水", "score": 0.9, "evidence_domain": "nutrition_race_fueling"},
        {"chunk_id": "n2", "text": "补给", "score": 0.8, "evidence_domain": "nutrition_race_fueling"},
        {"chunk_id": "t1", "text": "阈值", "score": 0.85, "evidence_domain": "protocol"},
        {"chunk_id": "t2", "text": "间歇", "score": 0.75, "evidence_domain": "action_library"},
        {"chunk_id": "r1", "text": "康复", "score": 0.7, "evidence_domain": "rehabilitation"},
    ]

    async def fake_get_context(*_args, **_kwargs):
        return list(fake_hits)

    monkeypatch.setattr(profile_module, "infer_entities", lambda *_args, **_kwargs: ["训练", "补给"])
    monkeypatch.setattr(profile_module, "semantic_match_entities", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(profile_module, "expand_entities_for_kg", lambda entities: entities)
    monkeypatch.setattr(profile_module, "graph_fusion_runtime_enabled", lambda: False)
    monkeypatch.setattr(profile_module, "get_context", fake_get_context)
    monkeypatch.setattr(profile_module, "build_rag_sources", lambda hits: hits)
    monkeypatch.setattr(profile_module, "build_ranked_evidence", lambda **kwargs: kwargs["vector_hits"])
    monkeypatch.setattr(profile_module, "evaluate_plan_evidence", lambda *_args, **_kwargs: {"required": False, "has_plan_evidence": True})
    monkeypatch.setattr(profile_module, "build_evidence_bundle", lambda **_kwargs: {"query": "test", "evidence_items": [], "health": {}})

    # nutritionist 应只拿到 nutrition 域命中
    result_nutrition = asyncio.run(
        profile_module.evidence_retriever_node(
            {"query": "补给策略", "entities": ["训练", "补给"], "selected_entities": [], "intent_type": "qa", "category": "nutritionist", "token_usage": {}},
            None,
        )
    )

    # 检查 ranked_evidence 中的 expert_domain
    for ev in result_nutrition.get("ranked_evidence", []):
        assert ev["expert_domain"] == "nutrition", f"nutritionist 不应拿到 {ev['expert_domain']} 域证据"


def test_coach_does_not_get_nutrition_only_evidence(monkeypatch):
    """Coach 不应拿到纯营养域的证据"""
    fake_hits = [
        {"chunk_id": "n1", "text": "碳水加载", "score": 0.9, "evidence_domain": "nutrition_race_fueling"},
        {"chunk_id": "t1", "text": "阈值训练", "score": 0.85, "evidence_domain": "protocol"},
    ]

    async def fake_get_context(*_args, **_kwargs):
        return list(fake_hits)

    monkeypatch.setattr(profile_module, "infer_entities", lambda *_args, **_kwargs: ["训练", "碳水"])
    monkeypatch.setattr(profile_module, "semantic_match_entities", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(profile_module, "expand_entities_for_kg", lambda entities: entities)
    monkeypatch.setattr(profile_module, "graph_fusion_runtime_enabled", lambda: False)
    monkeypatch.setattr(profile_module, "get_context", fake_get_context)
    monkeypatch.setattr(profile_module, "build_rag_sources", lambda hits: hits)
    monkeypatch.setattr(profile_module, "build_ranked_evidence", lambda **kwargs: kwargs["vector_hits"])
    monkeypatch.setattr(profile_module, "evaluate_plan_evidence", lambda *_args, **_kwargs: {"required": False, "has_plan_evidence": True})
    monkeypatch.setattr(profile_module, "build_evidence_bundle", lambda **_kwargs: {"query": "test", "evidence_items": [], "health": {}})

    result_coach = asyncio.run(
        profile_module.evidence_retriever_node(
            {"query": "训练和补给", "entities": ["训练", "碳水"], "selected_entities": [], "intent_type": "qa", "category": "coach", "token_usage": {}},
            None,
        )
    )

    for ev in result_coach.get("ranked_evidence", []):
        assert ev["expert_domain"] in {"training_theory", "workout_prescription", "race_strategy"}, \
            f"coach 不应拿到 {ev['expert_domain']} 域证据"


def test_auditor_gets_all_domains(monkeypatch):
    """Auditor 应拿到所有领域的证据"""
    fake_hits = [
        {"chunk_id": "n1", "text": "碳水", "score": 0.9, "evidence_domain": "nutrition_race_fueling"},
        {"chunk_id": "t1", "text": "阈值", "score": 0.85, "evidence_domain": "protocol"},
        {"chunk_id": "r1", "text": "康复", "score": 0.7, "evidence_domain": "rehabilitation"},
    ]

    async def fake_get_context(*_args, **_kwargs):
        return list(fake_hits)

    monkeypatch.setattr(profile_module, "infer_entities", lambda *_args, **_kwargs: ["训练", "补给", "康复"])
    monkeypatch.setattr(profile_module, "semantic_match_entities", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(profile_module, "expand_entities_for_kg", lambda entities: entities)
    monkeypatch.setattr(profile_module, "graph_fusion_runtime_enabled", lambda: False)
    monkeypatch.setattr(profile_module, "get_context", fake_get_context)
    monkeypatch.setattr(profile_module, "build_rag_sources", lambda hits: hits)
    monkeypatch.setattr(profile_module, "build_ranked_evidence", lambda **kwargs: kwargs["vector_hits"])
    monkeypatch.setattr(profile_module, "evaluate_plan_evidence", lambda *_args, **_kwargs: {"required": False, "has_plan_evidence": True})
    monkeypatch.setattr(profile_module, "build_evidence_bundle", lambda **_kwargs: {"query": "test", "evidence_items": [], "health": {}})

    result_auditor = asyncio.run(
        profile_module.evidence_retriever_node(
            {"query": "全面审查", "entities": ["训练", "补给", "康复"], "selected_entities": [], "intent_type": "qa", "category": "auditor", "token_usage": {}},
            None,
        )
    )

    domains_seen = {ev["expert_domain"] for ev in result_auditor.get("ranked_evidence", [])}
    # auditor 应看到多个域
    assert len(domains_seen) >= 2, f"auditor 只看到 {domains_seen}，应看到多领域证据"


def test_empty_category_still_filters_to_coach_domains(monkeypatch):
    """空 category 时应回退到 coach 领域集过滤"""
    fake_hits = [
        {"chunk_id": "n1", "text": "碳水", "score": 0.9, "evidence_domain": "nutrition_race_fueling"},
        {"chunk_id": "t1", "text": "阈值", "score": 0.85, "evidence_domain": "protocol"},
    ]

    async def fake_get_context(*_args, **_kwargs):
        return list(fake_hits)

    monkeypatch.setattr(profile_module, "infer_entities", lambda *_args, **_kwargs: ["训练", "碳水"])
    monkeypatch.setattr(profile_module, "semantic_match_entities", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(profile_module, "expand_entities_for_kg", lambda entities: entities)
    monkeypatch.setattr(profile_module, "graph_fusion_runtime_enabled", lambda: False)
    monkeypatch.setattr(profile_module, "get_context", fake_get_context)
    monkeypatch.setattr(profile_module, "build_rag_sources", lambda hits: hits)
    monkeypatch.setattr(profile_module, "build_ranked_evidence", lambda **kwargs: kwargs["vector_hits"])
    monkeypatch.setattr(profile_module, "evaluate_plan_evidence", lambda *_args, **_kwargs: {"required": False, "has_plan_evidence": True})
    monkeypatch.setattr(profile_module, "build_evidence_bundle", lambda **_kwargs: {"query": "test", "evidence_items": [], "health": {}})

    result_default = asyncio.run(
        profile_module.evidence_retriever_node(
            {"query": "训练", "entities": ["训练", "碳水"], "selected_entities": [], "intent_type": "qa", "category": "", "token_usage": {}},
            None,
        )
    )

    for ev in result_default.get("ranked_evidence", []):
        assert ev["expert_domain"] in {"training_theory", "workout_prescription", "race_strategy"}, \
            f"空 category 下不应拿到 {ev['expert_domain']}"


# ═══════════════════════════════════════════════════════════════════════════════
# 回归：现有证据链契约不受破坏
# ═══════════════════════════════════════════════════════════════════════════════

def test_expert_domain_not_exposed_in_runner_projection():
    """expert_domain 不应泄露到跑者端投影"""
    from marathon_qa_assistant.apps.response_projection import _project_runner_query_response
    from marathon_qa_assistant.apps.schemas import QueryResponse

    response = QueryResponse(
        report="训练建议",
        token_usage={},
        audit_scores={},
        guided_questions=[],
        evidence_chain=build_evidence_chain_payload(
            query="阈值跑",
            evidence_bundle={
                "evidence_items": [
                    {
                        "evidence_id": "chunk-1",
                        "source_registry_id": "src_1",
                        "source_file": "protocol.md",
                        "source_path": "C:/private/protocol.md",
                        "page": 1,
                        "chunk_id": "chunk-1",
                        "trace": {"source_url": "https://example.com/protocol"},
                        "evidence_domain": "protocol",
                        "expert_domain": "training_theory",
                        "prescription_permission": "can_write_core",
                    }
                ]
            },
        ),
    )

    projected = _project_runner_query_response(response)
    item = projected["evidence_chain"]["items"][0]
    # 跑者端不应暴露 expert_domain
    assert "expert_domain" not in item
    assert "expert_metadata" not in item


def test_source_status_priority_still_holds_with_expert_domain():
    """ready 源仍应排在 registry_only 源之前，且 expert_domain 不改变此优先级"""
    ranked = build_ranked_evidence(
        query="running injury",
        vector_hits=[
            {
                "chunk_id": "reg-1",
                "source_file": "registry.jsonl",
                "text": "Paper title about injury.",
                "score": 0.95,
                "source_status": "registry_only",
                "has_full_text": False,
                "evidence_domain": "rehabilitation",
            },
            {
                "chunk_id": "body-1",
                "source_file": "body.md",
                "text": "Training load and injury risk.",
                "score": 0.80,
                "source_status": "ready",
                "has_full_text": True,
                "evidence_domain": "protocol",
                "section": "document_paragraph",
                "prescription_permission": "explanation_only",
            },
        ],
        graph_edges=[],
        entities=["injury"],
        top_k=None,
    )

    # body-1 应有更高的 relevance（full_text bonus），排前面
    assert ranked[0]["chunk_id"] == "body-1"
    assert ranked[0]["source_status"] == "ready"
    assert ranked[0]["has_full_text"] is True
    assert ranked[0]["expert_domain"] == "training_theory"

    # reg-1 应被标记为 legacy_explanation
    assert ranked[1]["chunk_id"] == "reg-1"
    assert ranked[1]["display_mode"] == "legacy_explanation"
    assert ranked[1]["expert_domain"] == "rehab_safety"
