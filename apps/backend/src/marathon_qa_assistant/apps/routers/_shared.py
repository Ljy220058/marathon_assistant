"""Shared helpers for API routers.

These functions are extracted from api_app.py so that individual router modules
can import them without creating circular dependencies on api_app.py itself.
"""

import asyncio
import copy
import hmac
import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from marathon_qa_assistant.apps.response_projection import (
    _project_feedback_response_for_role as _shared_project_feedback_response_for_role,
    _project_plan_detail_response_for_role as _shared_project_plan_detail_response_for_role,
    _project_query_response_for_role as _shared_project_query_response_for_role,
    _project_training_calendar_response_for_role as _shared_project_training_calendar_response_for_role,
)
from marathon_qa_assistant.apps.security.response_role import _response_role as _shared_response_role
from marathon_qa_assistant.services.database import get_db
from marathon_qa_assistant.services.plan_query_classifier import (
    has_plan_generation_profile as _has_plan_generation_profile,
    is_plan_query as _is_plan_query,
)
from marathon_qa_assistant.core.profile_store import load_user_profile, save_user_profile, sync_user_zones
from marathon_qa_assistant.core.settings import get_settings
from marathon_qa_assistant.apps.schemas import QueryRequest


DEFAULT_API_USER_ID = "default_user"

# -------- auth / user resolution ---------------------------------------------

def _resolve_user_id(request: Request) -> str:
    """从请求状态或 API token 获取 user_id；未认证时返回默认用户。"""
    uid = getattr(request.state, "user_id", None)
    if uid:
        return str(uid)
    token = _request_api_token(request)
    if token:
        try:
            user = get_db().get_user_by_token(token)
            if user:
                return str(user["id"])
        except Exception:
            pass
        configured = _configured_api_token()
        if configured and hmac.compare_digest(token, configured):
            return DEFAULT_API_USER_ID
    return DEFAULT_API_USER_ID


def _configured_api_token() -> str:
    """保留向后兼容：检查是否配置了旧版单 token。"""
    return get_settings().api_token


def _is_production_mode() -> bool:
    return get_settings().is_production


def _auth_enabled() -> bool:
    """判断是否强制 API 认证。"""
    return get_settings().auth_enabled


def _require_default_user(user_id: str):
    """向后兼容：开发模式下允许 default_user，生产模式下由 token 中间件保证 user_id。"""
    if not _auth_enabled():
        return


def _request_api_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("X-Marathon-API-Key", "").strip()


_response_role = _shared_response_role
_project_query_response_for_role = _shared_project_query_response_for_role
_project_feedback_response_for_role = _shared_project_feedback_response_for_role
_project_plan_detail_response_for_role = _shared_project_plan_detail_response_for_role
_project_training_calendar_response_for_role = _shared_project_training_calendar_response_for_role


# -------- profile helpers ----------------------------------------------------

def _save_profile_patch(patch: Dict[str, Any], user_id: str = DEFAULT_API_USER_ID) -> Dict[str, Any]:
    old_profile = load_user_profile(user_id)
    profile = dict(old_profile)
    profile.update(patch or {})
    sync_user_zones(profile)
    save_user_profile(profile, user_id)
    try:
        from marathon_qa_assistant.services.memory_pipeline import write_profile_change_memories
        write_profile_change_memories(user_id, old_profile, profile)
    except Exception:
        pass
    return profile


def _profile_zones(profile: Dict[str, Any], user_id: str = DEFAULT_API_USER_ID) -> Dict[str, Dict[str, str]]:
    working = dict(profile or {})
    sync_user_zones(working)
    return {
        "hr_zones": working.get("hr_zones", {}) or {},
        "pace_zones": working.get("pace_zones", {}) or {},
    }


def _extract_profile_suggestions(text: str) -> Dict[str, Any]:
    """从明确表达中提取画像变更建议；只返回建议，不写盘。"""
    content = str(text or "")
    suggestions: Dict[str, Any] = {}

    mileage_match = re.search(r"(?:周跑量|跑量)[^\d]{0,8}(\d{1,3}(?:\.\d+)?)\s*(?:km|公里)?", content, re.I)
    if mileage_match:
        suggestions["weekly_mileage"] = mileage_match.group(1)

    lthr_match = re.search(r"(?:LTHR|乳酸阈心率|阈心率)[^\d]{0,8}(\d{2,3})", content, re.I)
    if lthr_match:
        suggestions["lthr"] = lthr_match.group(1)

    t_pace_match = re.search(r"(?:T配速|T-Pace|阈值配速)[^\d]{0,8}(\d[:：]\d{2})(?:\s*/?\s*km|/公里)?", content, re.I)
    if t_pace_match:
        suggestions["t_pace"] = t_pace_match.group(1).replace("：", ":") + "/km"

    goal_match = re.search(r"(?:目标|冲|想|准备)[^，。；\n]{0,12}((?:半马|全马|10K|5K)\s*(?:sub\s*)?\d{2,3})", content, re.I)
    if goal_match:
        suggestions["goal"] = goal_match.group(1).strip()

    return suggestions


# -------- plan persistence helpers -------------------------------------------

def _load_structured_plan(plan_row: Dict[str, Any]) -> Dict[str, Any]:
    raw = plan_row.get("structured_plan_json")
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _event_with_content_trace(event: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(event)
    raw_content = enriched.get("content_json")
    content: Dict[str, Any] = {}
    if isinstance(raw_content, str) and raw_content.strip():
        try:
            parsed = json.loads(raw_content)
            if isinstance(parsed, dict):
                content = parsed
        except json.JSONDecodeError:
            content = {}
    elif isinstance(raw_content, dict):
        content = raw_content

    if content:
        enriched["content"] = content
        passthrough_keys = {
            "training_type", "training_type_label", "workout_type", "zone_range",
            "zone_label", "intensity_target", "main_set", "warmup", "cooldown",
            "alternative", "training_objective", "evidence_tier", "evidence_tier_label",
            "source", "evidence_ids", "is_rest", "duration_min", "training_load",
            "training_load_method", "training_load_factors", "card_status",
            "field_sources", "protocol_check", "action_match", "kb_fallback",
            "risk_gate", "workflow_trace", "trace", "feedback_effect",
            "latest_feedback_effect", "feedback_replan", "generation_status",
            "adjustment_hint",
        }
        for key in passthrough_keys:
            if key in content and content[key] not in (None, ""):
                enriched[key] = content[key]
    return enriched


def _event_with_latest_feedback(event: Dict[str, Any]) -> Dict[str, Any]:
    from marathon_qa_assistant.core.state_models import build_workflow_trace

    enriched = _event_with_content_trace(event)
    latest = get_db().get_latest_event_feedback(str(event.get("id") or ""))
    if latest:
        latest["workflow_trace"] = build_workflow_trace(
            query="training_event_feedback",
            workflow_kind="adaptive",
            intent_type="feedback",
            status=(latest.get("risk_gate") or {}).get("product_status", "generated"),
            risk_gate=latest.get("risk_gate"),
            protocol_recheck=latest.get("protocol_recheck"),
            adaptive_feedback={
                "reason_codes": latest.get("reason_codes") or [],
                "source": "stored_event_feedback",
            },
            adaptive_adjustment=_feedback_summary_to_adaptive_adjustment(latest),
            feedback_id=latest.get("id"),
            feedback_persisted=True,
        )
        enriched["latest_feedback"] = latest
    return enriched


# -------- feedback helpers ---------------------------------------------------

def _normalize_frontend_feedback(payload: Dict[str, Any]) -> Dict[str, Any]:
    completion_map = {"已完成": "completed", "部分完成": "partial", "未完成": "missed"}
    fatigue_map = {"轻微": "mild", "中等": "mild", "明显": "high", "高疲劳": "high"}
    pain_map = {"没有疼痛": "none", "轻微不适": "watch", "疼痛风险": "risk"}
    sleep_map = {"良好": "good", "一般": "ok", "较差": "poor"}
    return {
        "completion_status": completion_map.get(str(payload.get("completion") or "").strip(), payload.get("completion_status", "")),
        "subjective_fatigue": fatigue_map.get(str(payload.get("fatigue") or "").strip(), payload.get("subjective_fatigue", "")),
        "pain_status": pain_map.get(str(payload.get("pain") or "").strip(), payload.get("pain_status", "")),
        "sleep_quality": sleep_map.get(str(payload.get("sleep") or "").strip(), payload.get("sleep_quality", "")),
        "notes": payload.get("notes", ""),
    }


def _feedback_summary_to_adaptive_adjustment(feedback: Dict[str, Any]) -> Dict[str, Any]:
    reason_codes = list(feedback.get("reason_codes") or [])
    return {
        "adjustment_required": bool(reason_codes),
        "primary_reason_code": reason_codes[0] if reason_codes else "",
        "reason_codes": reason_codes,
        "next_day_adjustment": feedback.get("next_day_adjustment") or "",
        "weekly_adjustment": feedback.get("weekly_adjustment") or "",
        "alternative_workout": feedback.get("alternative_workout") or "",
        "risk_alert": feedback.get("risk_alert") or "",
        "rationale": feedback.get("rationale") or "",
        "adjustment_action": (feedback.get("risk_gate") or {}).get("adjustment_action", "none"),
    }


def _build_feedback_plan_diff(
    *,
    risk_gate: Dict[str, Any],
    protocol_recheck: Dict[str, Any],
    adaptive_adjustment: Dict[str, Any],
    reason_codes: List[str],
) -> Dict[str, Any]:
    status = str(risk_gate.get("product_status") or "generated")
    blocked = status == "medical_referral" or protocol_recheck.get("allowed") is False
    needs_adjustment = bool(adaptive_adjustment.get("adjustment_required") or reason_codes or blocked)
    downgraded = 1 if needs_adjustment and not blocked else 0
    cancelled = 1 if blocked else 0
    affected_days = downgraded + cancelled
    return {
        "workflow": ["risk_gate", "protocol_recheck", "adjustment", "plan_diff"],
        "status": status,
        "affected_days": affected_days,
        "kept": 0 if needs_adjustment else 1,
        "downgraded": downgraded,
        "cancelled": cancelled,
        "reason_codes": list(reason_codes),
        "adjustment_action": risk_gate.get("adjustment_action", "none"),
        "decision_reason": risk_gate.get("decision_reason", ""),
    }


def _affected_events_after_feedback(events: List[Dict[str, Any]], event_id: str, limit: int = 3) -> List[Dict[str, Any]]:
    index = next((idx for idx, event in enumerate(events) if str(event.get("id")) == str(event_id)), -1)
    if index < 0:
        return []
    affected: List[Dict[str, Any]] = []
    for event in events[index + 1:]:
        effect = event.get("feedback_effect") if isinstance(event, dict) else None
        if not isinstance(effect, dict):
            if str(event.get("workout_type") or "").lower() == "rest":
                continue
        affected.append({
            "event_id": event.get("id"),
            "day_label": event.get("day_label"),
            "scheduled_date": event.get("scheduled_date"),
            "title": event.get("title"),
            "workout_type": event.get("workout_type"),
            "feedback_effect": effect if isinstance(effect, dict) else None,
        })
        if len(affected) >= limit:
            break
    return affected


def _plan_diff_from_affected_events(
    plan_diff: Dict[str, Any],
    affected_events: List[Dict[str, Any]],
    *,
    blocked: bool,
    needs_adjustment: bool,
) -> Dict[str, Any]:
    updated = dict(plan_diff or {})
    count = len(affected_events or [])
    if count:
        updated["affected_days"] = count
        updated["cancelled"] = count if blocked else 0
        updated["downgraded"] = 0 if blocked else count
        updated["kept"] = 0
    else:
        updated["affected_days"] = 0
        updated["cancelled"] = 0
        updated["downgraded"] = 0
        updated["kept"] = 0 if needs_adjustment else 1
    return updated


def _medical_referral_adjustment(adaptive_adjustment: Dict[str, Any]) -> Dict[str, Any]:
    adjusted = dict(adaptive_adjustment)
    adjusted["adjustment_required"] = True
    adjusted["next_day_adjustment"] = "停止训练，优先休息并进行专业医疗评估；评估前不要安排下一次跑步训练。"
    adjusted["weekly_adjustment"] = "本周暂停强度训练；只有在症状解除且专业评估允许后，才考虑恢复低强度训练。"
    adjusted["alternative_workout"] = "不生成跑步替代课；专业评估通过前只保留休息，必要活动应非常轻柔。"
    adjusted["risk_alert"] = "胸痛、头晕/晕厥或热病迹象属于医疗红旗，需要停止运动并寻求专业医疗帮助。"
    adjusted["rationale"] = "医疗红旗优先于训练连续性，本次反馈将停止训练并建议专业医疗评估。"
    return adjusted


# -------- schedule / day-name helpers ----------------------------------------

_DAY_NAME_ALIASES = {
    "monday": "Monday", "mon": "Monday", "周一": "Monday", "星期一": "Monday",
    "tuesday": "Tuesday", "tue": "Tuesday", "周二": "Tuesday", "星期二": "Tuesday",
    "wednesday": "Wednesday", "wed": "Wednesday", "周三": "Wednesday", "星期三": "Wednesday",
    "thursday": "Thursday", "thu": "Thursday", "周四": "Thursday", "星期四": "Thursday",
    "friday": "Friday", "fri": "Friday", "周五": "Friday", "星期五": "Friday",
    "saturday": "Saturday", "sat": "Saturday", "周六": "Saturday", "星期六": "Saturday",
    "sunday": "Sunday", "sun": "Sunday", "周日": "Sunday", "星期日": "Sunday",
    "周天": "Sunday", "星期天": "Sunday",
    "礼拜一": "Monday", "礼拜二": "Tuesday", "礼拜三": "Wednesday",
    "礼拜四": "Thursday", "礼拜五": "Friday", "礼拜六": "Saturday", "礼拜天": "Sunday",
}

_GLOBAL_CONSTRAINT_PATTERNS: List[Tuple[re.Pattern, str, callable]] = [
    (re.compile(r"本周(完全|都)?没空|这周(都)?不行|整周不可用"), "blocked_entire_week",
     lambda: {"unavailable_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], "scope": "blocked_entire_week"}),
    (re.compile(r"仅(周末|周六日|周六周日)有空|只有(周末|周六日|周六周日)能跑|只能(周末|周六日)"), "weekend_only",
     lambda: {"unavailable_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], "scope": "weekend_only"}),
    (re.compile(r"只能(晨跑|早上跑|早晨跑)|只有(早上|早晨)能跑"), "morning_only",
     lambda: {"time_window": "morning"}),
    (re.compile(r"只能(晚上跑|夜跑)|只有(晚上|傍晚)能跑"), "evening_only",
     lambda: {"time_window": "evening"}),
]


def _parse_schedule_constraints(raw_text: str = "", feedback: Optional[Dict[str, Any]] = None, override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    feedback = feedback or {}
    raw_constraints = override if isinstance(override, dict) and override else feedback.get("schedule_constraints")
    if not isinstance(raw_constraints, dict):
        raw_constraints = {}
    notes = " ".join(
        str(item or "")
        for item in [raw_text, raw_constraints.get("notes"), raw_constraints.get("reason")]
        if str(item or "").strip()
    )
    unavailable: List[str] = []
    for day in raw_constraints.get("unavailable_days") or []:
        normalized = _DAY_NAME_ALIASES.get(str(day or "").strip().lower()) or _DAY_NAME_ALIASES.get(str(day or "").strip())
        if normalized and normalized not in unavailable:
            unavailable.append(normalized)
    for token, normalized in _DAY_NAME_ALIASES.items():
        if token in notes and normalized not in unavailable:
            unavailable.append(normalized)
    time_window = str(raw_constraints.get("time_window") or "").strip()
    scope = str(raw_constraints.get("scope") or "this_week")
    for pattern, pattern_scope, handler in _GLOBAL_CONSTRAINT_PATTERNS:
        if pattern.search(notes):
            result = handler()
            if "unavailable_days" in result and not unavailable:
                unavailable = result["unavailable_days"]
            if result.get("scope"):
                scope = result["scope"]
            if result.get("time_window"):
                time_window = time_window or result["time_window"]
    return {
        "unavailable_days": unavailable,
        "reason": str(raw_constraints.get("reason") or raw_constraints.get("notes") or notes or "").strip(),
        "scope": scope,
        "time_window": time_window,
    }


def _event_day_name(event: Dict[str, Any]) -> str:
    label = str(event.get("day_label") or event.get("day") or "").strip()
    normalized = _DAY_NAME_ALIASES.get(label.lower()) or _DAY_NAME_ALIASES.get(label)
    if normalized:
        return normalized
    try:
        return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][int(event.get("day_no") or 0) - 1]
    except Exception:
        return ""


def _event_original_payload(event: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": str(event.get("title") or ""),
        "main_set": str(event.get("main_set") or ""),
        "duration_min": int(event.get("duration_min") or 0),
        "workout_type": str(event.get("workout_type") or ""),
    }


DOWNGRADE_LADDER = {
    "vo2max": {"title": "阈值跑", "main_set": "3 x 6 min 阈值配速，组间慢跑 3 min", "duration_min": 40, "workout_type": "threshold"},
    "threshold": {"title": "节奏跑", "main_set": "20 min 节奏跑，配速比阈值慢 5-8s/km", "duration_min": 35, "workout_type": "tempo"},
    "intervals": {"title": "轻松跑", "main_set": "30 min 轻松跑 + 10 min 动态拉伸", "duration_min": 40, "workout_type": "easy"},
    "tempo": {"title": "有氧耐力跑", "main_set": "40 min 有氧耐力跑，保持可完整说话的强度", "duration_min": 40, "workout_type": "aerobic"},
    "aerobic": {"title": "轻松跑", "main_set": "30 min 轻松跑，保持能完整说话的轻松强度", "duration_min": 30, "workout_type": "easy"},
    "long_run": {"title": "中等距离跑", "main_set": "50 min 有氧耐力跑，比平时长距离短且慢", "duration_min": 50, "workout_type": "aerobic"},
    "easy": {"title": "恢复轻松跑", "main_set": "恢复轻松跑 20 分钟 + 静态拉伸 10 分钟", "duration_min": 30, "workout_type": "recovery"},
    "recovery": {"title": "完全休息或散步", "main_set": "完全休息，或 20 min 散步 + 泡沫轴放松", "duration_min": 20, "workout_type": "rest"},
}


def _recovery_suggestion(reason: str, workout_type: str = "") -> Dict[str, Any]:
    fallback = {
        "title": "恢复轻松跑",
        "main_set": "恢复轻松跑 30 分钟，保持能完整说话的轻松强度。",
        "duration_min": 30,
        "workout_type": "recovery",
    }
    key = (workout_type or "").strip().lower().replace(" ", "_").replace("-", "_")
    suggestion = dict(DOWNGRADE_LADDER.get(key, fallback))
    suggestion["reason"] = reason
    return suggestion


def _replan_no_safe_slot(
    *,
    feedback_id: str,
    schedule_constraints: Dict[str, Any],
    previous_replan_id: str = "",
) -> Dict[str, Any]:
    replan = {
        "replan_id": str(uuid4()),
        "source_feedback_id": feedback_id,
        "status": "needs_manual_choice",
        "strategy": "no_available_safe_slot",
        "schedule_constraints": schedule_constraints,
        "patches": [],
        "audit": {"allowed": False, "blocked_reason": "本周没有可安全安排的训练日，需要手动选择可训练时间或先休息。"},
        "user_action": "manual_choice_required",
    }
    if previous_replan_id:
        replan["previous_replan_id"] = previous_replan_id
    return replan


def _find_next_safe_target_event(events: List[Dict[str, Any]], start_index: int, unavailable: set, excluded_ids: set) -> Optional[Dict[str, Any]]:
    for candidate in events[start_index + 1:]:
        candidate_id = str(candidate.get("id") or "")
        if candidate_id in excluded_ids:
            continue
        if str(candidate.get("workout_type") or "").lower() == "rest":
            continue
        if _event_day_name(candidate) in unavailable:
            continue
        return candidate
    return None


def _find_applied_feedback_replan(events: List[Dict[str, Any]], feedback_id: str) -> Dict[str, Any]:
    for event in events:
        enriched = _event_with_content_trace(event)
        replan = enriched.get("feedback_replan")
        if not isinstance(replan, dict):
            continue
        if str(replan.get("source_feedback_id") or "") == str(feedback_id) and replan.get("status") == "applied":
            return replan
    return {}


def _build_feedback_replan(
    *,
    plan_id: str,
    event_id: str,
    feedback_id: str,
    events: List[Dict[str, Any]],
    workout_feedback: Dict[str, Any],
    risk_gate: Dict[str, Any],
    protocol_recheck: Dict[str, Any],
    adaptive_adjustment: Dict[str, Any],
    schedule_constraints: Dict[str, Any],
    status: str = "suggested",
) -> Dict[str, Any]:
    if str(risk_gate.get("product_status") or "") == "medical_referral" or protocol_recheck.get("allowed") is False:
        return {
            "replan_id": str(uuid4()),
            "source_feedback_id": feedback_id,
            "status": "blocked_medical",
            "strategy": "medical_referral_stop",
            "schedule_constraints": schedule_constraints,
            "patches": [],
            "audit": {"allowed": False, "blocked_reason": "停止训练，并先完成专业医疗评估后再考虑恢复。"},
            "user_action": "blocked",
        }

    index = next((idx for idx, row in enumerate(events) if str(row.get("id")) == str(event_id)), -1)
    unavailable = set(schedule_constraints.get("unavailable_days") or [])
    reason = str(adaptive_adjustment.get("rationale") or "训练反馈显示恢复压力偏高，下一次训练应保守降级。")
    patches: List[Dict[str, Any]] = []
    moved_event_ids: set = set()
    future_events = events[index + 1:] if index >= 0 else []

    for move_index, event in enumerate(future_events, start=index + 1):
        if str(event.get("workout_type") or "").lower() == "rest":
            continue
        event_day = _event_day_name(event)
        if event_day not in unavailable:
            continue
        target = _find_next_safe_target_event(events, move_index, unavailable, moved_event_ids | {str(event.get("id") or "")})
        if not target:
            continue
        patches.append({
            "event_id": event.get("id"),
            "action": "move",
            "target_event_id": target.get("id"),
            "target_day": _event_day_name(target),
            "original": _event_original_payload(event),
            "suggested": _event_original_payload(event),
            "reason": f"{event_day} 在本周不可训练安排内，建议移到 {_event_day_name(target)}，避免和周二/周四等个人安排冲突。",
        })
        moved_event_ids.add(str(event.get("id") or ""))

    for event in future_events:
        event_id_value = str(event.get("id") or "")
        if event_id_value in moved_event_ids:
            continue
        if str(event.get("workout_type") or "").lower() == "rest":
            continue
        if _event_day_name(event) in unavailable:
            continue
        suggested = _recovery_suggestion(reason, str(event.get("workout_type") or ""))
        patches.append({
            "event_id": event.get("id"),
            "action": "downgrade",
            "original": _event_original_payload(event),
            "suggested": suggested,
            "reason": reason,
        })

    if not patches:
        return _replan_no_safe_slot(feedback_id=feedback_id, schedule_constraints=schedule_constraints)

    return {
        "replan_id": str(uuid4()),
        "source_feedback_id": feedback_id,
        "status": status,
        "strategy": "move_and_downgrade_local_window" if any(patch.get("action") == "move" for patch in patches) else "downgrade_next_available_workout",
        "schedule_constraints": schedule_constraints,
        "patches": patches,
        "audit": {"allowed": True, "blocked_reason": ""},
        "user_action": "pending" if status == "suggested" else status,
    }


def _build_adjustment_history(plan_id: str, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    history: List[Dict[str, Any]] = []
    for feedback in get_db().list_plan_feedback(plan_id):
        risk_gate = feedback.get("risk_gate") or {}
        protocol_recheck = feedback.get("protocol_recheck") or {}
        adaptive_adjustment = _feedback_summary_to_adaptive_adjustment(feedback)
        reason_codes = list(feedback.get("reason_codes") or [])
        affected_events = _affected_events_after_feedback(events, str(feedback.get("event_id") or ""))
        blocked = str(risk_gate.get("product_status") or "") == "medical_referral" or protocol_recheck.get("allowed") is False
        plan_diff = _plan_diff_from_affected_events(
            _build_feedback_plan_diff(
                risk_gate=risk_gate,
                protocol_recheck=protocol_recheck,
                adaptive_adjustment=adaptive_adjustment,
                reason_codes=reason_codes,
            ),
            affected_events,
            blocked=blocked,
            needs_adjustment=bool(adaptive_adjustment.get("adjustment_required") or reason_codes or blocked),
        )
        feedback_replan = next(
            (event.get("feedback_replan") for event in affected_events if isinstance(event.get("feedback_replan"), dict)),
            {},
        )
        if feedback_replan:
            plan_diff["feedback_replan_status"] = feedback_replan.get("status")
        history.append({
            "feedback_id": feedback.get("id"),
            "created_at": feedback.get("created_at"),
            "plan_id": feedback.get("plan_id"),
            "event_id": feedback.get("event_id"),
            "day_key": feedback.get("event_id"),
            "reason_codes": reason_codes,
            "risk_gate": risk_gate,
            "protocol_recheck": protocol_recheck,
            "adaptive_adjustment": adaptive_adjustment,
            "plan_diff": plan_diff,
            "affected_events": affected_events,
            "feedback_replan": feedback_replan,
        })
    return history
