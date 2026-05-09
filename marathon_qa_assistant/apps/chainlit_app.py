import sys
from pathlib import Path

import chainlit as cl

# 将项目根目录添加到 sys.path 以支持包导入
current_file = Path(__file__).absolute()
_TMP_BASE = current_file.parents[2]
if str(_TMP_BASE) not in sys.path:
    sys.path.insert(0, str(_TMP_BASE))

from marathon_qa_assistant.core.workflow import IntegratedState, load_user_profile
from marathon_qa_assistant.core.app_state import (
    global_state,
)
from marathon_qa_assistant.core.kb_bootstrap import (
    bootstrap_knowledge_base,
    default_kb_candidate_dirs,
    get_knowledge_base_health_snapshot,
)
from marathon_qa_assistant.core.kb_provider import get_kb_runtime_state
from marathon_qa_assistant.apps.chainlit.setup import (
    show_profile_summary,
    update_sidebar,
)
from marathon_qa_assistant.apps.chainlit.logic import process_message, _track_chainlit_event
from marathon_qa_assistant.apps.chainlit.coach_state import apply_session_defaults

# 导入回调模块以完成 Action 注册；实际业务逻辑已拆分到 apps/chainlit/*
import marathon_qa_assistant.apps.chainlit.actions as _chainlit_actions  # noqa: F401

_KB_READY = False
_KB_VECTOR_DIR: Path | None = None


def _kb_candidate_dirs() -> list[Path]:
    return default_kb_candidate_dirs()


def init_knowledge_base() -> bool:
    global _KB_READY, _KB_VECTOR_DIR

    report = bootstrap_knowledge_base(_kb_candidate_dirs())
    snapshot = get_knowledge_base_health_snapshot()
    global_state.chunks = list(get_kb_runtime_state().get("chunks") or [])
    global_state.kb_chunks_len = int(snapshot.get("chunks_count") or 0)
    global_state.kb_source = str(snapshot.get("source") or "unknown")
    global_state.kb_health_reason = str(snapshot.get("reason") or "")
    _KB_READY = bool(report.get("ok"))
    _KB_VECTOR_DIR = Path(str(report.get("vector_dir"))) if report.get("vector_dir") else None
    return _KB_READY


def ensure_knowledge_base_ready() -> bool:
    if _KB_READY:
        return False
    return init_knowledge_base()


@cl.set_chat_profiles
async def set_chat_profiles():
    return [
        cl.ChatProfile(
            name="Coach Mode",
            markdown_description="**教练模式**：专注于自适应训练计划、跑步表现分析与伤病预防指导。",
            icon="https://api.dicebear.com/7.x/avataaars/svg?seed=Coach&backgroundColor=b6e3f4",
        ),
        cl.ChatProfile(
            name="Research Mode",
            markdown_description="**研究模式**：专注于知识图谱探索、多篇文献交叉研究与领域知识挖掘。",
            icon="https://api.dicebear.com/7.x/avataaars/svg?seed=Research&backgroundColor=c0aede",
        ),
    ]


def _build_initial_state(chat_profile: str, profile: dict) -> IntegratedState:
    initial_mode = "team" if chat_profile == "Coach Mode" else "research"
    return {
        "query": "",
        "mode": initial_mode,
        "intent_type": "qa",
        "category": "",
        "subtasks": [],
        "draft_plan": "",
        "review_feedback": "",
        "is_approved": False,
        "iteration_count": 0,
        "final_report": "",
        "structured_training_plan": None,
        "structured_report": None,
        "reasoning_log": [],
        "rag_sources": [],
        "graph_context": "",
        "wiki_context": "",
        "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "audit_scores": {"consistency": 0, "safety": 0, "roi": 0, "summary": ""},
        "roi_history": [],
        "risk_alert": "",
        "entities": [],
        "mermaid_graph": "",
        "guided_questions": [],
        "user_profile": profile,
        "adaptive_feedback": {},
        "adaptive_adjustment": {},
        "missing_info_status": "",
        "enhancement_missing_fields": [],
        "history": [],
    }


def _reset_chainlit_session_state() -> None:
    apply_session_defaults(cl.user_session.set)


@cl.on_chat_start
async def start():
    if cl.user_session.get("initialized"):
        return

    ensure_knowledge_base_ready()

    chat_profile = cl.user_session.get("chat_profile") or "Coach Mode"
    profile = load_user_profile()
    state = _build_initial_state(chat_profile, profile)

    cl.user_session.set("state", state)
    _reset_chainlit_session_state()
    _track_chainlit_event(
        "app_opened",
        {
            "entry": "chat_start",
            "chat_profile": chat_profile,
            "initial_mode": state.get("mode"),
            "has_user_profile": bool(profile),
            "profile_field_count": len(profile) if isinstance(profile, dict) else 0,
        },
    )

    await show_profile_summary(profile, chat_profile)
    await update_sidebar(profile)
    cl.user_session.set("initialized", True)


@cl.on_message
async def main(message: cl.Message):
    await process_message(message, plan_click_entry="message")


__all__ = [
    "ensure_knowledge_base_ready",
    "init_knowledge_base",
    "main",
    "set_chat_profiles",
    "show_profile_summary",
    "start",
    "update_sidebar",
]
