"""PIPL 数据权利 API — 用户数据导出、删除和记忆管理。"""

from typing import Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel

from marathon_qa_assistant.apps.routers._shared import _resolve_user_id
from marathon_qa_assistant.apps.async_db import run_db
from marathon_qa_assistant.services.database import get_db
from marathon_qa_assistant.services.memory_store import get_memory_store
from marathon_qa_assistant.core.profile_store import load_user_profile

router = APIRouter(tags=["data-rights"])


class DeleteConfirmation(BaseModel):
    confirmation: str = "DELETE_ALL_MY_DATA"


class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    is_active: Optional[int] = None


class MemoryCreate(BaseModel):
    content: str
    source: str = "user_stated"
    category: str = "general"


@router.get("/user/{user_id}/data/export")
async def export_user_data(user_id: str, request: Request):
    resolved = _resolve_user_id(request)
    if resolved != user_id and resolved != "default_user":
        return {"error": "无权导出其他用户数据"}, 403

    db = get_db()
    profile = await run_db(load_user_profile, user_id)
    memories = await run_db(get_memory_store().export_memories, user_id)

    plans = await run_db(db.list_plans, user_id)
    plan_summaries = [
        {"id": p.get("id"), "title": p.get("title"), "created_at": p.get("created_at"), "status": p.get("status")}
        for p in plans
    ]

    compliance = await run_db(db.get_user_compliance, user_id)

    return {
        "user_id": user_id,
        "export_version": "1.0",
        "user_profile": profile,
        "memories": memories,
        "training_plans": plan_summaries,
        "consent_record": compliance,
    }


@router.post("/user/{user_id}/data/delete")
async def delete_user_data(user_id: str, body: DeleteConfirmation, request: Request):
    resolved = _resolve_user_id(request)
    if resolved != user_id and resolved != "default_user":
        return {"error": "无权删除其他用户数据"}, 403

    if body.confirmation != "DELETE_ALL_MY_DATA":
        return {"error": "请提供正确的确认字符串: DELETE_ALL_MY_DATA"}, 400

    db = get_db()
    ms = get_memory_store()

    deleted_memories = await run_db(ms.delete_all_user_memories, user_id)
    await run_db(ms.delete_memory_index, user_id)
    await run_db(db.delete_profile, user_id)

    conn = db._get_conn()
    await run_db(lambda: conn.execute("DELETE FROM training_event_feedback WHERE event_id IN (SELECT id FROM training_calendar_events WHERE plan_id IN (SELECT id FROM training_plans WHERE user_id = ?))", (user_id,)))
    await run_db(lambda: conn.execute("DELETE FROM training_calendar_events WHERE plan_id IN (SELECT id FROM training_plans WHERE user_id = ?)", (user_id,)))
    await run_db(lambda: conn.execute("DELETE FROM training_plans WHERE user_id = ?", (user_id,)))
    await run_db(lambda: conn.commit())

    return {
        "status": "deleted",
        "user_id": user_id,
        "deleted": {
            "profile": True,
            "memories": deleted_memories,
            "training_data": True,
            "memory_index": True,
        },
    }


@router.get("/user/{user_id}/memories")
async def list_user_memories(
    user_id: str,
    request: Request,
    category: Optional[str] = None,
    active_only: bool = True,
):
    ms = get_memory_store()
    memories = await run_db(ms.list_memories, user_id, category=category, active_only=active_only)
    return {"user_id": user_id, "count": len(memories), "memories": memories}


@router.post("/user/{user_id}/memories")
async def create_user_memory(user_id: str, body: MemoryCreate, request: Request):
    ms = get_memory_store()
    memory = await run_db(
        ms.add_memory_safe, user_id, body.content,
        source=body.source, category=body.category,
    )
    if memory is None:
        return {"status": "skipped", "reason": "已存在更高置信度的相似记忆"}
    return {"status": "created", "memory": memory}


@router.put("/user/{user_id}/memories/{memory_id}")
async def update_user_memory(user_id: str, memory_id: str, body: MemoryUpdate, request: Request):
    ms = get_memory_store()
    updated = await run_db(
        ms.update_memory, memory_id,
        content=body.content, is_active=body.is_active,
    )
    if not updated:
        return {"error": "记忆不存在或无变更"}, 404
    memory = await run_db(ms.get_memory, memory_id)
    return {"status": "updated", "memory": memory}


@router.delete("/user/{user_id}/memories/{memory_id}")
async def delete_user_memory(user_id: str, memory_id: str, request: Request):
    ms = get_memory_store()
    deleted = await run_db(ms.delete_memory, memory_id)
    if not deleted:
        return {"error": "记忆不存在"}, 404
    return {"status": "deleted", "memory_id": memory_id}
