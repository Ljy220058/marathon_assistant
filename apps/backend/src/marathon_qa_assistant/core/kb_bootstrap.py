from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from marathon_qa_assistant.core import app_state, kb_runtime
from marathon_qa_assistant.core.kb_provider import set_kb_data
from marathon_qa_assistant.core.settings import get_settings
from marathon_qa_assistant.services.label_matcher import label_matcher
from marathon_qa_assistant.services.vector_store import load_sharded_kb, load_vector_kb, probe_vector_kb_health, retrieve


_LAST_BOOTSTRAP_REPORT: Dict[str, Any] = {}


def _runtime_candidate_dirs(candidate_dirs: Optional[Iterable[Path]] = None) -> List[Path]:
    """运行时只扫描 v2 目录；拒绝 user/default/legacy fallback。"""
    candidates = list(candidate_dirs) if candidate_dirs is not None else [app_state.V2_VECTOR_DIR]
    v2_candidates: List[Path] = []
    for candidate in candidates:
        vector_path = Path(candidate)
        # 测试可传入临时 v2 路径，但路径名必须是 v2，避免 legacy 目录被探测或加载。
        if vector_path.name == "v2" and vector_path not in v2_candidates:
            v2_candidates.append(vector_path)
    return v2_candidates


def default_kb_candidate_dirs() -> List[Path]:
    return _runtime_candidate_dirs()


def bootstrap_knowledge_base(candidate_dirs: Optional[Iterable[Path]] = None) -> Dict[str, Any]:
    """统一加载 v2-only 知识库；不可用时进入空库模式，不回退 legacy。"""
    global _LAST_BOOTSTRAP_REPORT

    health_reports: List[Dict[str, Any]] = []
    settings = get_settings()
    for vector_dir in _runtime_candidate_dirs(candidate_dirs):
        vector_path = Path(vector_dir)
        health = probe_vector_kb_health(vector_path)
        health_reports.append(health)
        if not health.get("ok"):
            continue

        try:
            sharded_base = vector_path.parent / "v2_sharded"
            runtime_source = str(health.get("source") or "unknown")
            if settings.sharded_retrieval_enabled and sharded_base.exists():
                shard_stores, shard_chunks, chunks, bm25, _global_bm25 = load_sharded_kb(sharded_base)
                vectorizer = "faiss_sharded_vectorizer"
                matrix = shard_stores
                runtime_source = "v2_sharded"
                set_kb_data(chunks, vectorizer, matrix, retrieve, bm25=bm25, shard_chunks=shard_chunks)
            else:
                chunks, vectorizer, matrix, bm25 = load_vector_kb(vector_path)
                set_kb_data(chunks, vectorizer, matrix, retrieve, bm25=bm25)
        except Exception as exc:
            health["ok"] = False
            health["reason"] = f"知识库加载失败: {exc}"
            continue

        if not chunks or (matrix is None and not bm25):
            health["ok"] = False
            health["reason"] = "知识库加载后为空，且 FAISS/BM25 fallback 均不可用"
            continue

        # 预热 LabelMatcher
        try:
            from marathon_qa_assistant.services.knowledge_graph import graph_engine
            labels = []
            for node_info in getattr(graph_engine, "nodes", {}).values():
                label = node_info.get("label", "")
                if node_info.get("type", "") in ("workout", "template", "category") and label:
                    labels.append(label)
            label_matcher.warm_up(labels)
        except Exception:
            pass
        # 预热 reranker 模型，避免首次查询冷启动延迟 (~5s)
        try:
            from marathon_qa_assistant.services.reranker import _load_reranker
            _load_reranker()
        except Exception:
            pass
        faiss_ready = any(store is not None for store in matrix.values()) if isinstance(matrix, dict) else matrix is not None
        bm25_ready = any(index is not None for index in bm25.values()) if isinstance(bm25, dict) else bm25 is not None
        report = {
            "ok": True,
            "ready": True,
            "mode": "loaded_sharded" if runtime_source == "v2_sharded" else ("loaded" if faiss_ready else "degraded_fallback"),
            "vector_dir": str(sharded_base if runtime_source == "v2_sharded" else vector_path),
            "source": runtime_source,
            "reason": "" if faiss_ready else str(health.get("reason") or "FAISS unavailable; BM25 fallback active"),
            "chunks_count": len(chunks),
            "faiss_ready": faiss_ready,
            "bm25_ready": bm25_ready,
            "fallback_active": not faiss_ready and bm25_ready,
            "embedding_model": str(health.get("embedding_model") or ""),
            "chunking_strategy": str(health.get("chunking_strategy") or "unknown"),
            "eval_report_path": str(health.get("eval_report_path") or ""),
            "index_schema_version": str(health.get("index_schema_version") or "unknown"),
            "metadata_completeness": float(health.get("metadata_completeness") or 0.0),
            "runtime_core_prescription_enabled": bool(health.get("runtime_core_prescription_enabled")) and faiss_ready,
            "health_reports": health_reports,
        }
        _LAST_BOOTSTRAP_REPORT = report
        return report

    set_kb_data([], None, None, retrieve)
    reason = "; ".join(
        f"{item.get('source') or 'unknown'}:{item.get('reason') or 'unhealthy'}"
        for item in health_reports
    )
    report = {
        "ok": False,
        "ready": False,
        "mode": "empty",
        "vector_dir": "",
        "source": "empty",
        "reason": reason,
        "chunks_count": 0,
        "faiss_ready": False,
        "index_schema_version": "empty",
        "metadata_completeness": 0.0,
        "runtime_core_prescription_enabled": False,
        "health_reports": health_reports,
    }
    _LAST_BOOTSTRAP_REPORT = report
    return report


def is_kb_runtime_ready() -> bool:
    return bool(kb_runtime.KB_CHUNKS and (kb_runtime.KB_MATRIX is not None or kb_runtime.KB_BM25 is not None) and kb_runtime.RETRIEVE_FUNC)


def ensure_knowledge_base_ready(candidate_dirs: Optional[Iterable[Path]] = None) -> bool:
    if is_kb_runtime_ready():
        return False
    return bool(bootstrap_knowledge_base(candidate_dirs).get("ok"))


def get_knowledge_base_health_snapshot() -> Dict[str, Any]:
    if is_kb_runtime_ready():
        return {
            "ok": True,
            "ready": True,
            "mode": "runtime",
            "vector_dir": str(_LAST_BOOTSTRAP_REPORT.get("vector_dir") or ""),
            "source": str(_LAST_BOOTSTRAP_REPORT.get("source") or "runtime"),
            "reason": "",
            "chunks_count": len(kb_runtime.KB_CHUNKS),
            "faiss_ready": kb_runtime.KB_MATRIX is not None,
            "bm25_ready": kb_runtime.KB_BM25 is not None,
            "fallback_active": kb_runtime.KB_MATRIX is None and kb_runtime.KB_BM25 is not None,
            "embedding_model": str(_LAST_BOOTSTRAP_REPORT.get("embedding_model") or ""),
            "chunking_strategy": str(_LAST_BOOTSTRAP_REPORT.get("chunking_strategy") or "unknown"),
            "eval_report_path": str(_LAST_BOOTSTRAP_REPORT.get("eval_report_path") or ""),
            "index_schema_version": str(_LAST_BOOTSTRAP_REPORT.get("index_schema_version") or "unknown"),
            "metadata_completeness": float(_LAST_BOOTSTRAP_REPORT.get("metadata_completeness") or 0.0),
            "runtime_core_prescription_enabled": bool(_LAST_BOOTSTRAP_REPORT.get("runtime_core_prescription_enabled")),
        }
    if _LAST_BOOTSTRAP_REPORT:
        return {
            key: _LAST_BOOTSTRAP_REPORT.get(key)
            for key in (
                "ok",
                "ready",
                "mode",
                "vector_dir",
                "source",
                "reason",
                "chunks_count",
                "faiss_ready",
                "bm25_ready",
                "fallback_active",
                "embedding_model",
                "chunking_strategy",
                "eval_report_path",
                "index_schema_version",
                "metadata_completeness",
                "runtime_core_prescription_enabled",
            )
        }
    return {
        "ok": False,
        "ready": False,
        "mode": "uninitialized",
        "vector_dir": "",
        "source": "unknown",
        "reason": "知识库尚未初始化",
        "chunks_count": 0,
        "faiss_ready": False,
        "bm25_ready": False,
        "fallback_active": False,
        "embedding_model": "",
        "chunking_strategy": "unknown",
        "eval_report_path": "",
        "index_schema_version": "uninitialized",
        "metadata_completeness": 0.0,
        "runtime_core_prescription_enabled": False,
    }


__all__ = [
    "bootstrap_knowledge_base",
    "default_kb_candidate_dirs",
    "ensure_knowledge_base_ready",
    "get_knowledge_base_health_snapshot",
    "is_kb_runtime_ready",
]
