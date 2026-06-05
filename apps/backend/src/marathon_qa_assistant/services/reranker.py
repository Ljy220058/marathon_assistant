"""Reranker（二阶段精排）：FAISS 粗排 → bge-reranker-base 精选。

使用 sentence_transformers.CrossEncoder 加载 bge-reranker-base 对 top-N 候选逐条打分，
将 FAISS 语义相似度与 reranker 交叉编码器分数融合，输出精排结果。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("reranker")

_RERANKER_INSTANCE: Any = None
_RERANKER_AVAILABLE: bool | None = None


def _load_reranker() -> Any:
    """延迟加载 bge-reranker-base，全局单例避免重复加载（约 278MB）。"""
    global _RERANKER_INSTANCE, _RERANKER_AVAILABLE
    if _RERANKER_AVAILABLE is not None:
        return _RERANKER_INSTANCE
    try:
        from sentence_transformers import CrossEncoder

        _RERANKER_INSTANCE = CrossEncoder(
            "BAAI/bge-reranker-base",
        )
        _RERANKER_AVAILABLE = True
        logger.info("bge-reranker-base (CrossEncoder) 加载成功")
    except Exception as exc:
        _RERANKER_INSTANCE = None
        _RERANKER_AVAILABLE = False
        logger.warning("bge-reranker-base 不可用: %s，跳过重排序", exc)
    return _RERANKER_INSTANCE


def rerank_hits(
    query: str,
    hits: list[dict[str, Any]],
    top_k: int = 5,
    *,
    fusion_weight: float = 0.3,
) -> list[dict[str, Any]]:
    """对 FAISS 粗排结果用 bge-reranker 精排。

    Args:
        query: 用户原始查询（不经过 variant 增强）。
        hits: FAISS 粗排的 top-N 候选列表（建议 top-20）。
        top_k: 精排后保留的命中数。
        fusion_weight: 原始 FAISS 分数在融合中的权重（0-1）。
                      0 = 纯 reranker，1 = 纯 FAISS，0.3 = 70% reranker + 30% FAISS。

    Returns:
        精排后的 top_k 命中列表，每项额外带 reranker_score 和 reranker_rank 字段。
    """
    if not hits:
        return []

    reranker = _load_reranker()
    if reranker is None:
        logger.info("Reranker 不可用，降级为 FAISS 原始排序 top-%d", top_k)
        return hits[:top_k]

    # 构建 (query, text) pairs，截断长文本避免超限
    pairs = [[query, str(hit.get("text") or "")[:2000]] for hit in hits]

    try:
        scores = reranker.predict(pairs)
        if hasattr(scores, 'tolist'):
            scores = scores.tolist()
    except Exception as exc:
        logger.error("Reranker 打分失败: %s，降级为原始排序", exc)
        return hits[:top_k]

    # 确保 scores 是列表
    if not isinstance(scores, list):
        scores = [float(scores)]

    # 融合 FAISS 原始分数和 reranker 分数
    for hit, rerank_score in zip(hits, scores):
        original_score = float(hit.get("score") or 0.0)
        hit["reranker_score"] = round(float(rerank_score), 6)
        hit["reranker_raw_score"] = round(float(rerank_score), 6)
        # 加权融合: FAISS × fusion_weight + reranker × (1-fusion_weight)
        hit["score"] = round(
            fusion_weight * original_score + (1 - fusion_weight) * float(rerank_score),
            6,
        )
        breakdown = hit.get("score_breakdown") if isinstance(hit.get("score_breakdown"), dict) else {}
        breakdown.update(
            {
                "reranker_score": hit["reranker_score"],
                "original_faiss_score": original_score,
                "fusion_weight": fusion_weight,
            }
        )
        hit["score_breakdown"] = breakdown

    # 精排
    reranked = sorted(hits, key=lambda h: float(h.get("score") or 0), reverse=True)[:top_k]
    for rank, hit in enumerate(reranked, start=1):
        hit["reranker_rank"] = rank
        hit["retrieval_mode"] = (hit.get("retrieval_mode", "vector") + "+reranker")

    return reranked


def reranker_available() -> bool:
    """检查 reranker 是否可用。"""
    _load_reranker()
    return bool(_RERANKER_AVAILABLE)
