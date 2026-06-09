import gc
import logging
from typing import Any

logger = logging.getLogger("workflow_engine")

KB_CHUNKS: list[dict[str, Any]] = []
KB_VECTORIZER = None
KB_MATRIX = None
KB_BM25 = None
RETRIEVE_FUNC = None


def set_kb_data(chunks, vectorizer, matrix, retrieve_fn, bm25=None):
    """设置知识库运行时状态。"""
    global KB_VECTORIZER, KB_MATRIX, RETRIEVE_FUNC, KB_BM25
    KB_CHUNKS.clear()
    KB_CHUNKS.extend(chunks or [])
    KB_VECTORIZER = vectorizer
    KB_MATRIX = matrix
    KB_BM25 = bm25
    RETRIEVE_FUNC = retrieve_fn


def clear_kb_data():
    """清除知识库状态并释放可能残留的文件句柄。"""
    global KB_VECTORIZER, KB_MATRIX, RETRIEVE_FUNC, KB_BM25
    if KB_MATRIX is not None:
        try:
            if hasattr(KB_MATRIX, "_client"):
                try:
                    KB_MATRIX._client.close()
                except Exception:
                    pass
        except Exception as exc:
            logger.warning(f"释放 Chroma 客户端失败: {exc}")

    KB_CHUNKS.clear()
    KB_VECTORIZER = None
    KB_MATRIX = None
    KB_BM25 = None
    RETRIEVE_FUNC = None
    # 无效化 KG 实体标签缓存，避免 KG 重建后使用过期标签
    try:
        from marathon_qa_assistant.nodes.common import _KG_ENTITY_LABELS_CACHE
        import marathon_qa_assistant.nodes.common as common_module
        common_module._KG_ENTITY_LABELS_CACHE = None
    except Exception:
        pass
    gc.collect()
