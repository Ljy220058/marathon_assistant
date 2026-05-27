"""知识图谱注册脚本测试 — 验证幂等性和节点/边结构"""
import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.register_exercises_to_kg import (
    register_exercises,
    parse_exercise_from_chunk,
)


def _make_chunk(chunk_id, name, categories, objective, content="test content"):
    text_parts = [f"name：{name}"]
    if categories:
        text_parts.append(f"categories：{categories}")
    if content:
        text_parts.append(f"content：{content}")
    if objective:
        text_parts.append(f"objective：{objective}")
    return {
        "chunk_id": chunk_id,
        "source_file": "动作库.pdf",
        "page": 1,
        "text": "\n".join(text_parts),
    }


class TestParseExerciseFromChunk:
    def test_parse_basic(self):
        chunk = _make_chunk(
            "动作库_p0001_c0001",
            "轻松跑",
            "Aerobic, Base, Recovery",
            "建立有氧基础",
        )
        result = parse_exercise_from_chunk(chunk)
        assert result["name"] == "轻松跑"
        assert result["categories"] == ["Aerobic", "Base", "Recovery"]

    def test_parse_empty_categories(self):
        chunk = _make_chunk(
            "动作库_p0002_c0001",
            "测试动作",
            "",
            "测试目标",
        )
        result = parse_exercise_from_chunk(chunk)
        assert result["categories"] == []

    def test_parse_chinese_categories(self):
        chunk = _make_chunk(
            "动作库_p0003_c0001",
            "热身",
            "激活，有氧",
            "保证强度课质量",
        )
        result = parse_exercise_from_chunk(chunk)
        assert "激活" in result["categories"]
        assert "有氧" in result["categories"]


class TestRegisterExercises:
    def test_idempotent(self):
        chunks = [
            _make_chunk("动作库_p0001_c0001", "轻松跑", "Aerobic", "有氧基础"),
            _make_chunk("动作库_p0001_c0001", "轻松跑", "Aerobic", "有氧基础"),
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"nodes": {}, "edges": []}, f)
            kg_path = Path(f.name)

        try:
            result = register_exercises(chunks, kg_path)
            assert result["added_nodes"] == 1
            result2 = register_exercises(chunks, kg_path)
            assert result2["added_nodes"] == 0
        finally:
            kg_path.unlink(missing_ok=True)

    def test_creates_workout_template_node(self):
        chunks = [
            _make_chunk("动作库_p0001_c0001", "Tabata", "HIIT, Strength", "提升无氧代谢")
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"nodes": {}, "edges": []}, f)
            kg_path = Path(f.name)

        try:
            result = register_exercises(chunks, kg_path)
            assert result["added_nodes"] == 1

            kg = json.loads(kg_path.read_text(encoding="utf-8"))
            nodes = kg["nodes"]
            found = [n for n in nodes.values() if n.get("type") == "workout_template"]
            assert len(found) == 1
            assert found[0]["label"] == "Tabata"
        finally:
            kg_path.unlink(missing_ok=True)

    def test_has_category_edges(self):
        chunks = [
            _make_chunk("动作库_p0001_c0001", "间歇跑", "VO2max, Speed", "提升摄氧量")
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"nodes": {}, "edges": []}, f)
            kg_path = Path(f.name)

        try:
            register_exercises(chunks, kg_path)
            kg = json.loads(kg_path.read_text(encoding="utf-8"))
            edges = kg.get("edges", [])
            has_category_edges = [
                e for e in edges if e.get("relation") == "has_category"
            ]
            assert len(has_category_edges) >= 2
        finally:
            kg_path.unlink(missing_ok=True)
