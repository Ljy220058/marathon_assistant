"""test_label_matcher.py — L1 alias + L2 embedding semantic matching"""
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np

os.environ.setdefault("GRAPHRAG_API_KEY", "ci_test_token")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _make_mock_embeddings(labels_to_vectors: dict[str, list[float]]):
    """构造 mock embedding 实例，返回预定义向量"""
    mock = MagicMock()
    mock.model = "bge-m3"

    def embed_documents(texts):
        results = []
        for t in texts:
            if t in labels_to_vectors:
                results.append(labels_to_vectors[t])
            else:
                results.append([0.0] * 4)
        return results

    mock.embed_documents = embed_documents

    def embed_query(text):
        return embed_documents([text])[0]

    mock.embed_query = embed_query
    return mock


class TestSemanticMatchEntities:
    def test_l1_exact_match_returns_standard_label(self):
        """L1: "慢跑" → "轻松跑" """
        from marathon_qa_assistant.nodes.common import ALIAS_TABLE, semantic_match_entities

        assert "慢跑" in ALIAS_TABLE
        assert ALIAS_TABLE["慢跑"] == "轻松跑"

        result = semantic_match_entities("我想慢跑恢复")
        assert "轻松跑" in result

    def test_l1_no_match_falls_to_l2(self):
        """L1 无匹配 → L2 embedding → "HIIT" (>0.6)"""
        from marathon_qa_assistant.nodes.common import semantic_match_entities
        from marathon_qa_assistant.services.label_matcher import label_matcher

        with patch.object(label_matcher, "match", return_value=[("HIIT", 0.82)]):
            result = semantic_match_entities("想暴汗")
            assert "HIIT" in result

    def test_entity_extraction_merges_semantic_entities(self):
        from marathon_qa_assistant.nodes import profile_and_retrieval as module

        async def fake_get_context(query, top_k=4):
            return []

        class FakeGraphEngine:
            @staticmethod
            def search_graph(entities, max_hops=2):
                assert "HIIT" in entities
                assert "轻松跑" in entities
                return {"edges": []}

        state = {
            "query": "想暴汗后慢跑恢复",
            "selected_entities": [],
            "intent_type": "qa",
            "token_usage": {},
        }

        with patch.object(module, "get_context", side_effect=fake_get_context), \
            patch.object(module, "semantic_match_entities", return_value=["HIIT", "轻松跑"]), \
            patch.object(module, "graph_engine", FakeGraphEngine()), \
            patch.object(module, "get_graph_context", return_value=("", "flowchart TD\n  Empty[No Graph]")):
            result = __import__("asyncio").run(module.entity_extraction_node(state, {}))

        assert "HIIT" in result["entities"]
        assert "轻松跑" in result["entities"]
        assert result["selected_entities"] == result["entities"]

    def test_vector_store_uses_bge_m3_embedding_model(self):
        from marathon_qa_assistant.services import vector_store

        assert vector_store.EMBEDDING_MODEL == "bge-m3"

    def test_l2_below_threshold_returns_empty(self):
        """余弦相似度 < 0.6 → 返回空列表"""
        from marathon_qa_assistant.services.label_matcher import LabelMatcher

        matcher = LabelMatcher.__new__(LabelMatcher)
        matcher._label_vectors = {
            "轻松跑": np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32),
        }
        matcher._labels = ["轻松跑"]
        matcher._threshold = 0.6
        matcher._warmed = True

        matcher._embeddings = _make_mock_embeddings({})
        matcher._embeddings.embed_query = lambda q: [1.0, 0.0, 0.0, 0.0]

        result = matcher.match("今天天气不错")
        assert result == []

    def test_embedding_cached_across_calls(self):
        """LabelMatcher.warm_up() batch embed 一次，match() 复用缓存向量"""
        from marathon_qa_assistant.services.label_matcher import LabelMatcher

        matcher = LabelMatcher.__new__(LabelMatcher)
        labels = ["HIIT", "轻松跑"]
        call_count = [0]

        mock_emb = MagicMock()
        mock_emb.model = "bge-m3"

        def embed_docs(texts):
            call_count[0] += 1
            return [[1.0, 0.0] for _ in texts]

        mock_emb.embed_documents = embed_docs
        mock_emb.embed_query = lambda q: [0.9, 0.1]
        matcher._embeddings = mock_emb
        matcher._threshold = 0.6

        matcher.warm_up(labels)
        assert call_count[0] == 1  # batch embed 一次

        matcher.match("测试查询")
        matcher.match("另一个查询")
        assert call_count[0] == 1  # match() 不触发 embed_documents
