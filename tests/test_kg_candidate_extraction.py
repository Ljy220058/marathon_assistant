"""
测试 KG 候选三元组抽取和合并管线的核心契约。
"""
import json
import tempfile
from pathlib import Path

from marathon_qa_assistant.services.kb.kg_extraction import (
    ALLOWED_RELATIONS,
    _build_candidate_id,
    _entity_in_text,
    _normalize_relation,
    _validate_triple,
    load_candidate_queue,
    queue_stats,
    save_candidates,
)
from marathon_qa_assistant.services.knowledge_graph import (
    GraphEngine,
    _infer_bridge_type,
    _node_type_for_entity,
)


# ═══════════════════════════════════════════════════════════════════════════════
# _normalize_relation
# ═══════════════════════════════════════════════════════════════════════════════

def test_all_allowed_relations_are_valid():
    for rel in ALLOWED_RELATIONS:
        assert _normalize_relation(rel) == rel


def test_chinese_aliases_map_correctly():
    assert _normalize_relation("促进") == "supports"
    assert _normalize_relation("限制") == "constrains"
    assert _normalize_relation("需要") == "requires"
    assert _normalize_relation("调整") == "adjusts"
    assert _normalize_relation("风险") == "risks"
    assert _normalize_relation("改善") == "improves"
    assert _normalize_relation("减少") == "reduces"
    assert _normalize_relation("桥接") == "bridges_to"


def test_unknown_relation_returns_none():
    assert _normalize_relation("") is None
    assert _normalize_relation("invalid") is None
    assert _normalize_relation("causes") is None


# ═══════════════════════════════════════════════════════════════════════════════
# _entity_in_text
# ═══════════════════════════════════════════════════════════════════════════════

def test_exact_entity_match():
    assert _entity_in_text("碳水", "比赛前需要碳水加载")


def test_entity_not_in_text():
    assert not _entity_in_text("蛋白质", "比赛前需要碳水加载")


def test_fuzzy_match_with_80_percent_threshold():
    # 5 个字符中有 5 个匹配 = 100%，应通过
    assert _entity_in_text("碳水加载", "比赛前碳水加载很重要")
    # 少于 80% 匹配应拒绝
    assert not _entity_in_text("蛋白质补充策略", "碳水是主要能量来源")


def test_empty_entity_rejected():
    assert not _entity_in_text("", "some text")
    assert not _entity_in_text("abc", "")


# ═══════════════════════════════════════════════════════════════════════════════
# _validate_triple
# ═══════════════════════════════════════════════════════════════════════════════

def test_valid_triple_passes_validation():
    errors = _validate_triple(
        {"head_entity": "碳水补给", "relation": "improves", "tail_entity": "耐力表现", "confidence": 0.85},
        "马拉松比赛中碳水补给能改善耐力表现。",
    )
    assert errors == []


def test_invalid_relation_rejected():
    errors = _validate_triple(
        {"head_entity": "碳水", "relation": "causes_magic", "tail_entity": "耐力", "confidence": 0.5},
        "碳水 causes_magic 耐力。",
    )
    assert any("invalid_relation" in e for e in errors)


def test_self_loop_rejected():
    errors = _validate_triple(
        {"head_entity": "碳水", "relation": "supports", "tail_entity": "碳水", "confidence": 0.5},
        "碳水支持碳水。",
    )
    assert "self_loop" in errors


def test_entity_not_in_text_rejected():
    errors = _validate_triple(
        {"head_entity": "核聚变引擎", "relation": "supports", "tail_entity": "马拉松", "confidence": 0.9},
        "碳水支持耐力表现。",
    )
    assert any("head_not_in_text" in e for e in errors)
    assert any("tail_not_in_text" in e for e in errors)


def test_low_confidence_rejected():
    errors = _validate_triple(
        {"head_entity": "碳水", "relation": "supports", "tail_entity": "耐力", "confidence": 1.5},
        "碳水支持耐力。",
    )
    assert any("invalid_confidence" in e for e in errors)


# ═══════════════════════════════════════════════════════════════════════════════
# candidate queue I/O
# ═══════════════════════════════════════════════════════════════════════════════

def test_save_and_load_candidates_dedup():
    with tempfile.TemporaryDirectory() as tmpdir:
        queue_path = Path(tmpdir) / "test_candidates.jsonl"

        candidates = [
            {
                "candidate_id": "cand_001",
                "head_entity": "碳水",
                "relation": "supports",
                "tail_entity": "耐力",
                "expert_domain": "nutrition",
                "status": "candidate",
            },
            {
                "candidate_id": "cand_001",  # 重复 ID
                "head_entity": "碳水",
                "relation": "supports",
                "tail_entity": "耐力",
                "status": "candidate",
            },
            {
                "candidate_id": "cand_002",
                "head_entity": "间歇跑",
                "relation": "improves",
                "tail_entity": "VO2max",
                "expert_domain": "training_theory",
                "status": "candidate",
            },
        ]

        new_count = save_candidates(candidates, queue_path)
        assert new_count == 2  # 去重后只有 2 条

        loaded = load_candidate_queue(queue_path)
        assert len(loaded) == 2

        stats = queue_stats(queue_path)
        assert stats["total"] == 2
        assert stats["by_status"]["candidate"] == 2
        assert stats["by_expert_domain"]["nutrition"] == 1
        assert stats["by_expert_domain"]["training_theory"] == 1


def test_load_empty_queue():
    with tempfile.TemporaryDirectory() as tmpdir:
        queue_path = Path(tmpdir) / "nonexistent.jsonl"
        assert load_candidate_queue(queue_path) == []


# ═══════════════════════════════════════════════════════════════════════════════
# candidate_id 稳定性
# ═══════════════════════════════════════════════════════════════════════════════

def test_candidate_id_is_stable():
    cid1 = _build_candidate_id("chunk_a", "碳水", "supports", "耐力")
    cid2 = _build_candidate_id("chunk_a", "碳水", "supports", "耐力")
    cid3 = _build_candidate_id("chunk_b", "碳水", "supports", "耐力")
    assert cid1 == cid2
    assert cid1 != cid3
    assert cid1.startswith("cand_")


# ═══════════════════════════════════════════════════════════════════════════════
# merge_validated_candidates
# ═══════════════════════════════════════════════════════════════════════════════

def test_merge_skips_candidate_and_rejected(monkeypatch, tmp_path):
    """只有 status=validated 的候选才合并进入主图。"""
    engine = GraphEngine.__new__(GraphEngine)
    engine.nodes = {}
    engine.edges = []
    engine.processed_chunks = {}
    engine.GRAPH_DATA_PATH = tmp_path / "test_kg.json"

    queue_path = tmp_path / "test_queue.jsonl"
    queue_path.write_text(
        "\n".join([
            json.dumps({
                "candidate_id": "cand_skip",
                "head_entity": "carbs",
                "relation": "supports",
                "tail_entity": "endurance",
                "expert_domain": "nutrition",
                "confidence": 0.8,
                "status": "candidate",
            }),
            json.dumps({
                "candidate_id": "cand_reject",
                "head_entity": "sugar",
                "relation": "improves",
                "tail_entity": "speed",
                "expert_domain": "nutrition",
                "confidence": 0.3,
                "status": "rejected",
            }),
            json.dumps({
                "candidate_id": "cand_merge",
                "head_entity": "interval run",
                "relation": "improves",
                "tail_entity": "VO2max",
                "expert_domain": "training_theory",
                "confidence": 0.9,
                "status": "validated",
                "source_file": "training_theory.pdf",
                "chunk_id": "chunk_abc",
                "evidence_span": "Interval run improves VO2max.",
                "evidence_domain": "protocol",
            }),
        ]) + "\n"
    )

    result = engine.merge_validated_candidates(queue_path, min_confidence=0.5)

    assert result["merged"] == 1
    assert result["skipped"] == 2

    # 验证图中有新节点和边
    assert len(engine.nodes) == 2
    assert len(engine.edges) == 1
    assert engine.edges[0]["relation"] == "improves"
    assert engine.edges[0].get("expert_domain") == "training_theory"


def test_merge_low_confidence_skipped(tmp_path):
    """confidence 低于阈值的 validated 候选也不合并。"""
    engine = GraphEngine.__new__(GraphEngine)
    engine.nodes = {}
    engine.edges = []
    engine.processed_chunks = {}
    engine.GRAPH_DATA_PATH = tmp_path / "test_kg_lowconf.json"

    queue_path = tmp_path / "test_queue_lowconf.jsonl"
    queue_path.write_text(
        json.dumps({
            "candidate_id": "cand_low",
            "head_entity": "carbs",
            "relation": "supports",
            "tail_entity": "endurance",
            "expert_domain": "nutrition",
            "confidence": 0.3,
            "status": "validated",
        }) + "\n"
    )

    result = engine.merge_validated_candidates(queue_path, min_confidence=0.5)
    assert result["merged"] == 0
    assert result["skipped"] == 1


def test_merge_bridge_edge_gets_bridge_type(tmp_path):
    """bridges_to 边应自动推断 bridge_type。"""
    engine = GraphEngine.__new__(GraphEngine)
    engine.nodes = {}
    engine.edges = []
    engine.processed_chunks = {}
    engine.GRAPH_DATA_PATH = tmp_path / "test_kg_bridge.json"

    queue_path = tmp_path / "test_queue_bridge.jsonl"
    queue_path.write_text(
        json.dumps({
            "candidate_id": "cand_bridge",
            "head_entity": "knee pain",
            "relation": "bridges_to",
            "tail_entity": "training plan adjustment",
            "expert_domain": "rehab_safety",
            "confidence": 0.9,
            "status": "validated",
            "source_file": "rehab.pdf",
            "chunk_id": "chunk_xyz",
            "evidence_span": "Knee pain bridges to training adjustment.",
            "evidence_domain": "medical_safety",
        }) + "\n"
    )

    result = engine.merge_validated_candidates(queue_path, min_confidence=0.5)
    assert result["merged"] == 1
    assert engine.edges[0]["relation"] == "bridges_to"
    assert engine.edges[0].get("bridge_type") == "causal"


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════

def test_node_type_for_nutrition_entity():
    assert _node_type_for_entity("碳水补给", "nutrition") == "nutrition"
    assert _node_type_for_entity("水合策略", "nutrition") == "nutrition"
    assert _node_type_for_entity("蛋白质摄入", "nutrition") == "nutrition"


def test_node_type_for_workout_entity():
    assert _node_type_for_entity("间歇跑", "training_theory") == "workout"
    assert _node_type_for_entity("长距离慢跑", "training_theory") == "workout"


def test_node_type_for_injury_entity():
    assert _node_type_for_entity("膝盖疼痛", "rehab_safety") == "injury"
    assert _node_type_for_entity("跟腱炎", "rehab_safety") == "injury"


def test_node_type_for_physiology_entity():
    assert _node_type_for_entity("乳酸阈值", "training_theory") == "physiology"
    assert _node_type_for_entity("VO2max", "training_theory") == "physiology"


def test_node_type_default_is_concept():
    assert _node_type_for_entity("周期化训练", "training_theory") == "concept"
    assert _node_type_for_entity("比赛策略", "race_strategy") == "concept"
