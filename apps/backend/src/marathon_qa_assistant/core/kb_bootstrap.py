from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from marathon_qa_assistant.core import kb_runtime
from marathon_qa_assistant.core.app_state import (
    DEFAULT_VECTOR_DIR,
    LEGACY_DEFAULT_VECTOR_DIR,
    LEGACY_USER_VECTOR_DIR,
    RUNTIME_USER_VECTOR_DIR,
    USER_VECTOR_DIR,
)
from marathon_qa_assistant.core.kb_provider import set_kb_data
from marathon_qa_assistant.services.vector_store import load_vector_kb, probe_vector_kb_health, retrieve


_LAST_BOOTSTRAP_REPORT: Dict[str, Any] = {}


def default_kb_candidate_dirs() -> List[Path]:
    return [
        USER_VECTOR_DIR,
        RUNTIME_USER_VECTOR_DIR,
        LEGACY_USER_VECTOR_DIR,
        DEFAULT_VECTOR_DIR,
        LEGACY_DEFAULT_VECTOR_DIR,
    ]


def bootstrap_knowledge_base(candidate_dirs: Optional[Iterable[Path]] = None) -> Dict[str, Any]:
    """统一加载知识库：优先用户库，失败后回退默认库，最终进入空库模式。"""
    global _LAST_BOOTSTRAP_REPORT

    health_reports: List[Dict[str, Any]] = []
    for vector_dir in candidate_dirs or default_kb_candidate_dirs():
        vector_path = Path(vector_dir)
        health = probe_vector_kb_health(vector_path)
        health_reports.append(health)
        if not health.get("ok"):
            continue

        try:
            chunks, vectorizer, matrix, bm25 = load_vector_kb(vector_path)
        except Exception as exc:
            health["ok"] = False
            health["reason"] = f"知识库加载失败: {exc}"
            continue

        if not chunks or matrix is None:
            health["ok"] = False
            health["reason"] = "知识库加载后为空或 FAISS 不可用"
            continue

        set_kb_data(chunks, vectorizer, matrix, retrieve, bm25=bm25)
        report = {
            "ok": True,
            "ready": True,
            "mode": "loaded",
            "vector_dir": str(vector_path),
            "source": str(health.get("source") or "unknown"),
            "reason": "",
            "chunks_count": len(chunks),
            "faiss_ready": True,
            "index_schema_version": str(health.get("index_schema_version") or "unknown"),
            "metadata_completeness": float(health.get("metadata_completeness") or 0.0),
            "runtime_core_prescription_enabled": bool(health.get("runtime_core_prescription_enabled")),
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
    return bool(kb_runtime.KB_CHUNKS and kb_runtime.KB_MATRIX is not None and kb_runtime.RETRIEVE_FUNC)


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
