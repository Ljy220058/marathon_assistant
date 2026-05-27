"""test_label_matcher.py — L1 alias + L2 embedding semantic matching"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np

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

        # 确保别名表存在
        assert "慢跑" in ALIAS_TABLE
        assert ALIAS_TABLE["慢跑"] == "轻松跑"

    def test_l1_no_match_falls_to_l2(self):
        """L1 无匹配 → L2 embedding → "HIIT" (>0.6)"""
        from marathon_qa_assistant.nodes.common import semantic_match_entities
        from marathon_qa_assistant.services.label_matcher import label_matcher

        with patch.object(label_matcher, "_embeddings", _make_mock_embeddings({
            "HIIT": [0.9, 0.1, 0.0, 0.0],
            "轻松跑": [0.0, 0.9, 0.0, 0.1],
        })):
            label_matcher._label_vectors = {
                "HIIT": np.array([0.9, 0.1, 0.0, 0.0], dtype=np.float32),
                "轻松跑": np.array([0.0, 0.9, 0.0, 0.1], dtype=np.float32),
            }
            label_matcher._labels = ["HIIT", "轻松跑"]
            label_matcher._threshold = 0.6
            label_matcher._warmed = True

            with patch.object(label_matcher, "_embeddings") as emb:
                emb.embed_query = lambda q: [0.85, 0.15, 0.0, 0.05]

                result = semantic_match_entities("想暴汗")
                # L1: "暴汗运动" IN query "想暴汗" — NO because "暴汗运动" is the key not value
                # L2: embed("想暴汗") vs labels → HIIT (0.85*0.9 + 0.15*0.1 ≈ 0.78 > 0.6)
                assert "HIIT" in result

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
