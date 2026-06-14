"""结构化记忆存储服务。

提供带来源标注、置信度控制和 CRUD 的用户记忆管理。
来源优先级: user_stated (1.0) > system_computed (0.9) > llm_inferred (0.5)。
向量检索：复用 nomic-embed-text 基础设施，每用户独立 FAISS 索引。
"""

import json
import logging
import shutil
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("workflow_engine")

SOURCE_PRIORITY = {
    "user_stated": 1.0,
    "system_computed": 0.9,
    "llm_inferred": 0.5,
}

VALID_CATEGORIES = {
    "injury", "performance", "preference", "context", "goal", "general",
}


def _get_db():
    from marathon_qa_assistant.services.database import get_db
    return get_db()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_dict(row) -> Dict[str, Any]:
    if row is None:
        return {}
    d = dict(row)
    if "tags" in d and isinstance(d["tags"], str):
        try:
            d["tags"] = json.loads(d["tags"])
        except (json.JSONDecodeError, TypeError):
            d["tags"] = []
    return d


class MemoryStore:
    """用户记忆的 CRUD + 质量控制。"""

    def add_memory(
        self,
        user_id: str,
        content: str,
        *,
        source: str = "llm_inferred",
        confidence: Optional[float] = None,
        category: str = "general",
        tags: Optional[List[str]] = None,
        expires_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        if source not in SOURCE_PRIORITY:
            source = "llm_inferred"
        if confidence is None:
            confidence = SOURCE_PRIORITY[source]
        if category not in VALID_CATEGORIES:
            category = "general"

        memory_id = f"mem-{uuid.uuid4().hex[:12]}"
        tags_json = json.dumps(tags or [], ensure_ascii=False)

        conn = _get_db()._get_conn()
        conn.execute(
            """INSERT INTO session_memories
               (id, user_id, content, source, confidence, category, tags, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (memory_id, user_id, content, source, confidence, category, tags_json, expires_at),
        )
        conn.commit()
        logger.info(f"记忆已写入: id={memory_id}, source={source}, category={category}")
        return {
            "id": memory_id,
            "user_id": user_id,
            "content": content,
            "source": source,
            "confidence": confidence,
            "category": category,
            "tags": tags or [],
        }

    def add_memory_safe(
        self,
        user_id: str,
        content: str,
        *,
        source: str = "llm_inferred",
        confidence: Optional[float] = None,
        category: str = "general",
        tags: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """写入前检查同类记忆的来源优先级，低置信度不覆盖高置信度。"""
        if confidence is None:
            confidence = SOURCE_PRIORITY.get(source, 0.5)

        existing = self.list_memories(user_id, category=category)
        for mem in existing:
            if mem.get("confidence", 0) > confidence and _content_similar(mem["content"], content):
                logger.info(
                    f"跳过低优先级记忆写入: existing.confidence={mem['confidence']} > new={confidence}"
                )
                return None

        return self.add_memory(
            user_id, content,
            source=source, confidence=confidence, category=category, tags=tags,
        )

    def get_memory(self, memory_id: str) -> Dict[str, Any]:
        conn = _get_db()._get_conn()
        row = conn.execute(
            "SELECT * FROM session_memories WHERE id = ?", (memory_id,)
        ).fetchone()
        return _row_to_dict(row)

    def list_memories(
        self,
        user_id: str,
        *,
        category: Optional[str] = None,
        active_only: bool = True,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        conn = _get_db()._get_conn()
        clauses = ["user_id = ?"]
        params: List[Any] = [user_id]
        if active_only:
            clauses.append("is_active = 1")
        if category:
            clauses.append("category = ?")
            params.append(category)
        where = " AND ".join(clauses)
        rows = conn.execute(
            f"SELECT * FROM session_memories WHERE {where} ORDER BY updated_at DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def update_memory(
        self,
        memory_id: str,
        *,
        content: Optional[str] = None,
        is_active: Optional[int] = None,
        source: Optional[str] = None,
        confidence: Optional[float] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        sets: List[str] = ["updated_at = datetime('now')"]
        params: List[Any] = []
        if content is not None:
            sets.append("content = ?")
            params.append(content)
        if is_active is not None:
            sets.append("is_active = ?")
            params.append(is_active)
        if source is not None:
            sets.append("source = ?")
            params.append(source)
        if confidence is not None:
            sets.append("confidence = ?")
            params.append(confidence)
        if tags is not None:
            sets.append("tags = ?")
            params.append(json.dumps(tags, ensure_ascii=False))
        params.append(memory_id)
        conn = _get_db()._get_conn()
        conn.execute(
            f"UPDATE session_memories SET {', '.join(sets)} WHERE id = ?",
            params,
        )
        conn.commit()
        return conn.total_changes > 0

    def delete_memory(self, memory_id: str) -> bool:
        conn = _get_db()._get_conn()
        conn.execute("DELETE FROM session_memories WHERE id = ?", (memory_id,))
        conn.commit()
        return conn.total_changes > 0

    def soft_delete_memory(self, memory_id: str) -> bool:
        return self.update_memory(memory_id, is_active=0)

    def export_memories(self, user_id: str) -> List[Dict[str, Any]]:
        return self.list_memories(user_id, active_only=False, limit=10000)

    def delete_all_user_memories(self, user_id: str) -> int:
        conn = _get_db()._get_conn()
        conn.execute("DELETE FROM session_memories WHERE user_id = ?", (user_id,))
        conn.commit()
        return conn.total_changes

    def count_memories(self, user_id: str, *, active_only: bool = True) -> int:
        conn = _get_db()._get_conn()
        clause = "user_id = ?"
        if active_only:
            clause += " AND is_active = 1"
        row = conn.execute(
            f"SELECT COUNT(*) as cnt FROM session_memories WHERE {clause}",
            (user_id,),
        ).fetchone()
        return row["cnt"] if row else 0

    # ---- 向量检索 ----

    def _memory_index_dir(self, user_id: str) -> Path:
        from marathon_qa_assistant.core.app_state import RUNTIME_DATA_DIR
        base = RUNTIME_DATA_DIR.parent / "memory_index"
        idx_dir = base / user_id / "faiss_db"
        idx_dir.mkdir(parents=True, exist_ok=True)
        return idx_dir

    def _get_embeddings(self):
        from marathon_qa_assistant.services.vector_store import get_embeddings
        return get_embeddings()

    def rebuild_memory_index(self, user_id: str) -> int:
        """全量重建用户记忆的 FAISS 索引。返回索引中的记忆条数。"""
        try:
            from langchain_community.vectorstores import FAISS
        except ImportError:
            logger.warning("langchain FAISS 不可用，跳过记忆索引重建")
            return 0

        memories = self.list_memories(user_id, active_only=True, limit=10000)
        if not memories:
            return 0

        embeddings = self._get_embeddings()
        texts = [m["content"] for m in memories]
        metadatas = [{"memory_id": m["id"], "source": m["source"], "confidence": m["confidence"], "category": m["category"]} for m in memories]
        ids = [m["id"] for m in memories]

        try:
            store = FAISS.from_texts(texts, embeddings, metadatas=metadatas, ids=ids)
            idx_dir = self._memory_index_dir(user_id)
            store.save_local(str(idx_dir))
            logger.info(f"记忆 FAISS 索引重建完成: user={user_id}, count={len(texts)}")
            return len(texts)
        except Exception as exc:
            logger.warning(f"记忆索引重建失败 (user={user_id}): {exc}")
            return 0

    def search_relevant_memories(
        self,
        user_id: str,
        query: str,
        *,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """用向量相似度检索最相关的记忆。回退到最近记忆列表。"""
        try:
            from langchain_community.vectorstores import FAISS
        except ImportError:
            return self._fallback_recent(user_id, top_k)

        idx_dir = self._memory_index_dir(user_id)
        index_file = idx_dir / "index.faiss"

        if not index_file.exists():
            count = self.rebuild_memory_index(user_id)
            if count == 0:
                return self._fallback_recent(user_id, top_k)

        try:
            embeddings = self._get_embeddings()
            store = FAISS.load_local(str(idx_dir), embeddings, allow_dangerous_deserialization=True)
            results = store.similarity_search_with_score(query, k=top_k)
            memories = []
            for doc, score in results:
                mem_id = doc.metadata.get("memory_id", "")
                full = self.get_memory(mem_id) if mem_id else {}
                if full and full.get("is_active", 0) == 1:
                    full["relevance_score"] = round(float(score), 4)
                    memories.append(full)
            return memories
        except Exception as exc:
            logger.warning(f"记忆向量检索失败 (user={user_id}): {exc}")
            return self._fallback_recent(user_id, top_k)

    def _fallback_recent(self, user_id: str, top_k: int) -> List[Dict[str, Any]]:
        return self.list_memories(user_id, limit=top_k)

    def delete_memory_index(self, user_id: str) -> None:
        idx_dir = self._memory_index_dir(user_id)
        if idx_dir.exists():
            shutil.rmtree(idx_dir, ignore_errors=True)
            logger.info(f"记忆索引已删除: user={user_id}")


def _content_similar(a: str, b: str) -> bool:
    """简单文本相似度：字符级 Jaccard > 0.5 视为重复。Phase 3 升级为向量相似度。"""
    a_lower, b_lower = a.lower().strip(), b.lower().strip()
    if not a_lower or not b_lower:
        return False
    sa = set(a_lower)
    sb = set(b_lower)
    intersection = sa & sb
    union = sa | sb
    return len(intersection) / len(union) > 0.5


_store_instance: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = MemoryStore()
    return _store_instance
