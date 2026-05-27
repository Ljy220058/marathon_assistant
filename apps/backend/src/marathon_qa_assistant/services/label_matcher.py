"""label_matcher.py — KG 标签语义匹配：向量缓存 + cosine 检索"""
import logging
import os
from typing import Dict, List

import numpy as np

try:
    from langchain_ollama import OllamaEmbeddings
except ImportError:
    OllamaEmbeddings = None  # type: ignore[assignment]

logger = logging.getLogger("workflow_engine")

_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """手算余弦相似度，避免引入 scipy 依赖"""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class LabelMatcher:
    """KG 标签语义匹配器：启动时预热向量缓存，查询时 cosine 检索"""

    def __init__(self, embedding_model: str = "bge-m3"):
        if OllamaEmbeddings is None:
            raise RuntimeError("langchain_ollama 不可用，无法初始化 LabelMatcher")
        self._embeddings = OllamaEmbeddings(model=embedding_model, base_url=_OLLAMA_BASE_URL)
        self._label_vectors: Dict[str, np.ndarray] = {}
        self._labels: List[str] = []
        self._threshold: float = 0.6
        self._warmed: bool = False

    def warm_up(self, labels: List[str], threshold: float = 0.6) -> None:
        """启动时调用。batch embed 所有 KG 标签，缓存向量"""
        self._threshold = threshold
        if not labels:
            self._warmed = True
            return
        self._labels = list(labels)
        try:
            vectors = self._embeddings.embed_documents(self._labels)
        except Exception as exc:
            raise RuntimeError(
                f"LabelMatcher 预热失败: 无法 embed {len(self._labels)} 个标签。"
                f"请检查 Ollama 是否运行且模型 {self._embeddings.model} 已拉取。"
            ) from exc
        for label, vec in zip(self._labels, vectors):
            self._label_vectors[label] = np.array(vec, dtype=np.float32)
        self._warmed = True
        logger.info("[label_matcher] 预热完成，已缓存 %d 个标签向量 (threshold=%.2f)", len(self._label_vectors), self._threshold)

    def match(self, query: str, top_k: int = 3) -> List[tuple[str, float]]:
        """L2 语义匹配。返回 [(label, cosine_score), ...]，低于 threshold 的被过滤"""
        if not self._warmed:
            return []
        if not self._label_vectors or not query.strip():
            return []
        try:
            query_vec = np.array(self._embeddings.embed_query(query), dtype=np.float32)
        except Exception as exc:
            logger.warning("[label_matcher] embedding 查询失败: %s，回退到空结果", exc)
            return []
        scored = []
        for label, label_vec in self._label_vectors.items():
            sim = _cosine_similarity(query_vec, label_vec)
            if sim >= self._threshold:
                scored.append((label, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


label_matcher = LabelMatcher()
