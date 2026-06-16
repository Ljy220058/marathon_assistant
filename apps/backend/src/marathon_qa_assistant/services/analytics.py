import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from marathon_qa_assistant.core.app_state import RUNTIME_DATA_DIR
from marathon_qa_assistant.core.settings import get_settings

CORE_EVENTS = {
    "app_opened",
    "profile_wizard_started",
    "profile_submitted",
    "plan_generate_clicked",
    "plan_generated",
    "workout_feedback_submitted",
    "adaptive_plan_generated",
    "weekly_review_viewed",
    "evidence_opened",
}

PLAN_REQUEST_KEYWORDS = (
    "训练计划",
    "周计划",
    "半马",
    "全马",
    "马拉松计划",
)

DEFAULT_EVENT_LOG_PATH = RUNTIME_DATA_DIR / "analytics_events.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_user_id(user_id: Optional[str]) -> str:
    raw = str(user_id or "default_user").strip() or "default_user"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def get_or_create_session_id(session_get: Optional[Any] = None, session_set: Optional[Any] = None) -> str:
    if session_get:
        existing = session_get("analytics_session_id", None)
        if existing:
            return str(existing)
    session_id = uuid.uuid4().hex
    if session_set:
        session_set("analytics_session_id", session_id)
    return session_id


def build_event_payload(
    event_name: str,
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    properties: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    if event_name not in CORE_EVENTS:
        raise ValueError(f"Unsupported analytics event: {event_name}")
    return {
        "event_name": event_name,
        "user_id_hash": _hash_user_id(user_id),
        "session_id": str(session_id or uuid.uuid4().hex),
        "version": get_settings().app_version,
        "timestamp": _now_iso(),
        "properties": dict(properties or {}),
    }


def build_plan_click_properties(
    *,
    entry: Optional[str],
    message_text: Optional[str],
    has_image_context: bool = False,
) -> Optional[Dict[str, Any]]:
    normalized_entry = str(entry or "").strip()
    if not normalized_entry:
        return None

    text = str(message_text or "")
    if normalized_entry == "message" and not any(keyword in text for keyword in PLAN_REQUEST_KEYWORDS):
        return None

    return {
        "entry": normalized_entry,
        "source_type": "message" if normalized_entry == "message" else "action",
        "query_length": len(text),
        "has_image_context": bool(has_image_context),
    }


def write_event(payload: Mapping[str, Any], event_log_path: Optional[Path] = None) -> Path:
    path = Path(event_log_path or DEFAULT_EVENT_LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(dict(payload), ensure_ascii=False, sort_keys=True) + "\n")
    return path


def track_event(
    event_name: str,
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    properties: Optional[Mapping[str, Any]] = None,
    event_log_path: Optional[Path] = None,
) -> Dict[str, Any]:
    payload = build_event_payload(
        event_name,
        user_id=user_id,
        session_id=session_id,
        properties=properties,
    )
    write_event(payload, event_log_path=event_log_path)
    return payload
