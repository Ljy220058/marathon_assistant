from typing import Any, Dict, Tuple

from marathon_qa_assistant.core import kb_runtime

KB_CHUNKS = kb_runtime.KB_CHUNKS
set_kb_data = kb_runtime.set_kb_data
clear_kb_data = kb_runtime.clear_kb_data


def get_kb_data() -> Tuple[list[dict[str, Any]], Any, Any, Any]:
    """返回当前运行时知识库对象，避免跨模块导入静态快照。"""
    return (
        kb_runtime.KB_CHUNKS,
        kb_runtime.KB_VECTORIZER,
        kb_runtime.KB_MATRIX,
        kb_runtime.KB_BM25,
    )


def get_kb_runtime_state() -> Dict[str, Any]:
    """为调用方提供统一的知识库运行时只读视图。"""
    chunks, vectorizer, matrix, bm25 = get_kb_data()
    return {
        "chunks": chunks,
        "vectorizer": vectorizer,
        "matrix": matrix,
        "bm25": bm25,
    }
