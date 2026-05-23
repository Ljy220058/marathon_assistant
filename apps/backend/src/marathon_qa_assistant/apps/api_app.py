import json
import os
import sys
import asyncio
import time
import hmac
import ipaddress
import copy
from contextlib import asynccontextmanager
from uuid import uuid4
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 将项目根目录添加到 sys.path
current_file = Path(__file__).absolute()
BASE_DIR = current_file.parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from marathon_qa_assistant.core.workflow import (
    integrated_app,
    IntegratedState,
)
from marathon_qa_assistant.core.profile_store import load_user_profile, save_user_profile, sync_user_zones
from marathon_qa_assistant.core.working_state import build_working_state
from marathon_qa_assistant.core.evidence_bundle import build_evidence_bundle
from marathon_qa_assistant.core.training_plan_context import merge_plan_profile_overrides
from marathon_qa_assistant.core.training_plan_skeleton import build_structured_training_plan_skeleton
from marathon_qa_assistant.core.state_models import (
    build_execution_status_summary,
    build_adaptive_adjustment_contract,
    build_feedback_protocol_recheck,
    build_feedback_risk_gate,
    build_workflow_trace,
    derive_adaptive_reasons,
    normalize_workout_feedback,
)
from marathon_qa_assistant.core.observability import (
    metrics_snapshot,
    record_feedback_risk,
    record_generation_status,
    record_request,
)
from marathon_qa_assistant.core.kb_bootstrap import (
    bootstrap_knowledge_base,
    ensure_knowledge_base_ready,
    get_knowledge_base_health_snapshot,
)
from marathon_qa_assistant.services.daily_schedule_generator import generate_daily_schedule
from marathon_qa_assistant.services.database import get_db
from marathon_qa_assistant.services.kb.evidence_chain import (
    ANSWER_SOURCE_MODES,
    EVIDENCE_CHAIN_DISPLAY_MODES,
    build_evidence_chain_payload,
)
from marathon_qa_assistant.services.training_plan_review import build_training_plan_review
from marathon_qa_assistant.services.workout_template_retriever import (
    WORKOUT_TEMPLATE_REGISTRY,
    ZONE_LABELS,
    ZONE_LABELS_DETAIL,
    EVIDENCE_TIER_LABELS,
)
from marathon_qa_assistant.apps.schemas import (
    DayDetailResponse,
    EventScheduleRequest,
    FeedbackRequest,
    FeedbackResponse,
    NluExtractRequest,
    OpsMetricsResponse,
    PlanDetailResponse,
    ProfileFieldRequest,
    ProfileRequest,
    QueryRequest,
    QueryResponse,
    SavePlanRequest,
    TrainingCalendarResponse,
    ZoneReference,
)

DEFAULT_API_USER_ID = "default_user"


@asynccontextmanager
async def _lifespan(app_instance: FastAPI):
    app_instance.state.rag_bootstrap = bootstrap_knowledge_base()
    yield


app = FastAPI(title="Marathon QA Assistant API", version="1.0.0", lifespan=_lifespan)

_RATE_LIMIT_BUCKETS: Dict[Tuple[str, str, str], List[float]] = {}
_RATE_LIMITED_PREFIXES = ("/query", "/feedback", "/training-calendar", "/plans", "/profile")
_PUBLIC_API_PREFIXES = ("/health", "/zone-reference", "/evidence-tier-reference", "/llm-options", "/docs", "/openapi.json")


def _rate_limit_per_minute() -> int:
    raw = os.getenv("MARATHON_RATE_LIMIT_PER_MINUTE", "600").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 600


def _rate_limit_client_id(request: Request) -> str:
    if str(os.getenv("MARATHON_TRUST_PROXY_HEADERS") or "").strip() == "1":
        forwarded = request.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
        if forwarded:
            try:
                return str(ipaddress.ip_address(forwarded))
            except ValueError:
                return "invalid-forwarded-for"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _rate_limit_route_key(request: Request) -> Optional[Tuple[str, str]]:
    method = request.method.upper()
    if method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    path = request.url.path or "/"
    for prefix in _RATE_LIMITED_PREFIXES:
        if path == prefix or path.startswith(f"{prefix}/"):
            return method, prefix
    return None


def _reset_rate_limit_state_for_tests() -> None:
    _RATE_LIMIT_BUCKETS.clear()


def _rate_limit_max_buckets() -> int:
    raw = os.getenv("MARATHON_RATE_LIMIT_MAX_BUCKETS", "4096").strip()
    try:
        return max(128, int(raw))
    except ValueError:
        return 4096


def _prune_rate_limit_buckets(now: float) -> None:
    expired_keys = [
        key
        for key, stamps in _RATE_LIMIT_BUCKETS.items()
        if not any(now - stamp < 60 for stamp in stamps)
    ]
    for key in expired_keys:
        _RATE_LIMIT_BUCKETS.pop(key, None)
    max_buckets = _rate_limit_max_buckets()
    if len(_RATE_LIMIT_BUCKETS) <= max_buckets:
        return
    oldest = sorted(
        _RATE_LIMIT_BUCKETS,
        key=lambda key: min(_RATE_LIMIT_BUCKETS.get(key) or [now]),
    )
    for key in oldest[: len(_RATE_LIMIT_BUCKETS) - max_buckets]:
        _RATE_LIMIT_BUCKETS.pop(key, None)


def _configured_api_token() -> str:
    return os.getenv("MARATHON_API_TOKEN", "").strip()


def _request_api_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("X-Marathon-API-Key", "").strip()


def _configured_expert_api_token() -> str:
    return os.getenv("MARATHON_EXPERT_API_TOKEN", "").strip()


def _request_expert_api_token(request: Request) -> str:
    return request.headers.get("X-Marathon-Expert-Key", "").strip()


def _request_has_expert_response_access(request: Request) -> bool:
    expected = _configured_expert_api_token()
    supplied = _request_expert_api_token(request)
    return bool(expected and supplied and hmac.compare_digest(supplied, expected))


def _response_role(request: Request) -> str:
    requested = str(request.headers.get("X-Marathon-Response-Role") or "").strip().lower()
    if requested == "runner":
        return "runner"
    if requested == "expert":
        if _request_has_expert_response_access(request):
            return "expert"
        if not _configured_api_token() and not _configured_expert_api_token():
            return "expert"
        raise HTTPException(status_code=403, detail="专家响应需要有效专家凭据。")
    if requested:
        raise HTTPException(status_code=400, detail="无效 response role。")
    if _configured_api_token() or _configured_expert_api_token():
        return "runner"
    return "expert"


def _requires_api_token(request: Request) -> bool:
    if not _configured_api_token():
        return False
    if request.method.upper() == "OPTIONS":
        return False
    path = request.url.path or "/"
    return not any(path == prefix or path.startswith(f"{prefix}/") for prefix in _PUBLIC_API_PREFIXES)

def _allowed_cors_origins() -> List[str]:
    if str(os.getenv("MARATHON_DEV_PERMISSIVE_CORS") or "").strip() == "1":
        return ["*"]
    raw = str(os.getenv("MARATHON_ALLOWED_ORIGINS") or "").strip()
    if raw:
        origins = [item.strip() for item in raw.split(",") if item.strip()]
        return origins or ["http://127.0.0.1:4321", "http://localhost:4321"]
    return ["http://127.0.0.1:4321", "http://localhost:4321"]

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_cors_origins(),
    # Browsers reject "*" + credentials, so keep the API permissive but stateless.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _rate_limit_middleware(request: Request, call_next):
    limit = _rate_limit_per_minute()
    route_key = _rate_limit_route_key(request)
    if limit <= 0 or route_key is None:
        return await call_next(request)

    now = time.monotonic()
    _prune_rate_limit_buckets(now)
    bucket_key = (_rate_limit_client_id(request), route_key[0], route_key[1])
    recent = [stamp for stamp in _RATE_LIMIT_BUCKETS.get(bucket_key, []) if now - stamp < 60]
    if len(recent) >= limit:
        return JSONResponse(
            {"detail": "请求过于频繁，请稍后再试。"},
            status_code=429,
            headers={"Retry-After": "60"},
        )
    recent.append(now)
    _RATE_LIMIT_BUCKETS[bucket_key] = recent
    return await call_next(request)


@app.middleware("http")
async def _api_token_middleware(request: Request, call_next):
    if not _requires_api_token(request):
        return await call_next(request)
    expected = _configured_api_token()
    supplied = _request_api_token(request)
    if not supplied or not hmac.compare_digest(supplied, expected):
        return JSONResponse(
            {"detail": "API 访问需要有效凭据。"},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await call_next(request)


@app.middleware("http")
async def _request_observability_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req-{uuid4().hex}"
    request.state.request_id = request_id
    route_path = getattr(request.scope.get("route"), "path", None) or "/__unmatched__"
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        route_path = getattr(request.scope.get("route"), "path", None) or route_path
        record_request(
            method=request.method,
            path=route_path,
            status_code=500,
            duration_ms=(time.perf_counter() - started) * 1000,
            error_type=exc.__class__.__name__,
        )
        raise
    route_path = getattr(request.scope.get("route"), "path", None) or route_path
    response.headers["X-Request-ID"] = request_id
    record_request(
        method=request.method,
        path=route_path,
        status_code=response.status_code,
        duration_ms=(time.perf_counter() - started) * 1000,
    )
    return response

def _require_default_user(user_id: str):
    if user_id != DEFAULT_API_USER_ID:
        raise HTTPException(
            status_code=400,
            detail=f"当前 API 仅支持单用户画像，user_id 必须为 {DEFAULT_API_USER_ID!r}。",
        )


def _load_structured_plan(plan_row: Dict[str, Any]) -> Dict[str, Any]:
    raw = plan_row.get("structured_plan_json")
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


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


def _save_profile_patch(patch: Dict[str, Any]) -> Dict[str, Any]:
    profile = load_user_profile()
    profile.update(patch or {})
    sync_user_zones(profile)
    save_user_profile(profile)
    return profile


def _profile_zones(profile: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    working = dict(profile or {})
    sync_user_zones(working)
    return {
        "hr_zones": working.get("hr_zones", {}) or {},
        "pace_zones": working.get("pace_zones", {}) or {},
    }


def _extract_profile_suggestions(text: str) -> Dict[str, Any]:
    """从明确表达中提取画像变更建议；只返回建议，不写盘。"""
    import re

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


PLAN_QUERY_KEYWORDS = (
    "训练计划",
    "周计划",
    "月历",
    "日历",
    "课表",
    "生成计划",
    "制定",
    "安排",
    "备赛",
    "半马",
    "全马",
    "马拉松",
    "half marathon",
    "marathon",
    "training plan",
    "training feedback",
    "adjust next week",
    "adjusted plan",
    "adaptive plan",
    "race prep",
    "race preparation",
    "sub ",
    "pb",
)


def _is_plan_query(query: str) -> bool:
    text = str(query or "").lower()
    return any(keyword.lower() in text for keyword in PLAN_QUERY_KEYWORDS)


def _has_plan_generation_profile(profile: Dict[str, Any]) -> bool:
    if not isinstance(profile, dict):
        return False
    plan_fields = (
        profile.get("goal"),
        profile.get("current_half_time"),
        profile.get("target_half_time"),
        profile.get("target_race_date"),
        profile.get("weekly_mileage"),
        profile.get("recent_four_week_mileage"),
        profile.get("recent_4_week_mileage"),
        profile.get("last_month_mileage"),
        profile.get("available_days"),
        profile.get("target_pace"),
        profile.get("injury_or_fatigue"),
        profile.get("injury"),
        profile.get("recovery_state"),
    )
    return any(value not in (None, "", []) for value in plan_fields)


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


def _affected_events_after_feedback(events: List[Dict[str, Any]], event_id: str, limit: int = 3) -> List[Dict[str, Any]]:
    index = next((idx for idx, event in enumerate(events) if str(event.get("id")) == str(event_id)), -1)
    if index < 0:
        return []
    affected: List[Dict[str, Any]] = []
    for event in events[index + 1 :]:
        if str(event.get("workout_type") or "").lower() == "rest":
            continue
        affected.append(
            {
                "event_id": event.get("id"),
                "day_label": event.get("day_label"),
                "scheduled_date": event.get("scheduled_date"),
                "title": event.get("title"),
                "workout_type": event.get("workout_type"),
            }
        )
        if len(affected) >= limit:
            break
    return affected


def _build_adjustment_history(plan_id: str, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    history: List[Dict[str, Any]] = []
    for feedback in get_db().list_plan_feedback(plan_id):
        risk_gate = feedback.get("risk_gate") or {}
        protocol_recheck = feedback.get("protocol_recheck") or {}
        adaptive_adjustment = _feedback_summary_to_adaptive_adjustment(feedback)
        reason_codes = list(feedback.get("reason_codes") or [])
        history.append(
            {
                "feedback_id": feedback.get("id"),
                "created_at": feedback.get("created_at"),
                "plan_id": feedback.get("plan_id"),
                "event_id": feedback.get("event_id"),
                "day_key": feedback.get("event_id"),
                "reason_codes": reason_codes,
                "risk_gate": risk_gate,
                "protocol_recheck": protocol_recheck,
                "adaptive_adjustment": adaptive_adjustment,
                "plan_diff": _build_feedback_plan_diff(
                    risk_gate=risk_gate,
                    protocol_recheck=protocol_recheck,
                    adaptive_adjustment=adaptive_adjustment,
                    reason_codes=reason_codes,
                ),
                "affected_events": _affected_events_after_feedback(events, str(feedback.get("event_id") or "")),
            }
        )
    return history


def _medical_referral_adjustment(adaptive_adjustment: Dict[str, Any]) -> Dict[str, Any]:
    adjusted = dict(adaptive_adjustment)
    adjusted["adjustment_required"] = True
    adjusted["next_day_adjustment"] = (
        "停止训练，优先休息并进行专业医疗评估；评估前不要安排下一次跑步训练。"
    )
    adjusted["weekly_adjustment"] = (
        "本周暂停强度训练；只有在症状解除且专业评估允许后，才考虑恢复低强度训练。"
    )
    adjusted["alternative_workout"] = (
        "不生成跑步替代课；专业评估通过前只保留休息，必要活动应非常轻柔。"
    )
    adjusted["risk_alert"] = (
        "胸痛、头晕/晕厥或热病迹象属于医疗红旗，需要停止运动并寻求专业医疗帮助。"
    )
    adjusted["rationale"] = "医疗红旗优先于训练连续性，本次反馈将停止训练并建议专业医疗评估。"
    return adjusted


def _normalize_provider(provider: str) -> str:
    normalized = str(provider or "ollama").strip().lower()
    if normalized in {"ds", "deepseek"}:
        return "ds"
    if normalized in {"openai", "gpt"}:
        return "openai"
    return "ollama"


def _selected_model(request: QueryRequest) -> str:
    provider = _normalize_provider(request.llm_provider)
    if request.llm_model:
        return request.llm_model.strip()
    if provider == "ds":
        return os.getenv("DEEPSEEK_MODEL", os.getenv("DS_MODEL", "deepseek-v4-pro"))
    if provider == "openai":
        return os.getenv("OPENAI_MODEL", "gpt-5.5")
    return os.getenv("OLLAMA_MODEL", "qwen2.5:latest")


def _safe_workflow_error_summary(exc: Exception) -> str:
    provider = str(getattr(exc, "provider", "") or "").strip()
    error_code = str(getattr(exc, "error_code", "") or "").strip()
    if provider and error_code:
        return f"模型服务暂不可用（{provider}/{error_code}）"
    if isinstance(exc, TimeoutError):
        return "模型服务请求超时"
    return "模型服务暂不可用"


def _build_llm_config(request: QueryRequest) -> Dict[str, Any]:
    provider = _normalize_provider(request.llm_provider)
    return {
        "configurable": {
            "llm_provider": provider,
            "llm_model": _selected_model(request),
            "ds_api_key": request.ds_api_key,
            "llm_timeout_sec": request.timeout_sec,
        }
    }


def _save_plan_if_ready(
    structured_plan: Optional[Dict[str, Any]],
    request: QueryRequest,
    calendar_days: Optional[List[Dict[str, Any]]] = None,
) -> Optional[str]:
    if not isinstance(structured_plan, dict) or not structured_plan.get("week_plans"):
        return None
    try:
        return get_db().save_training_plan(
            structured_plan,
            source_query=request.query,
            user_id=request.user_id,
            calendar_days=calendar_days,
        )
    except Exception:
        return None


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
            "training_type",
            "training_type_label",
            "workout_type",
            "zone_range",
            "zone_label",
            "intensity_target",
            "main_set",
            "warmup",
            "cooldown",
            "alternative",
            "training_objective",
            "evidence_tier",
            "evidence_tier_label",
            "source",
            "evidence_ids",
            "is_rest",
            "duration_min",
            "training_load",
            "training_load_method",
            "training_load_factors",
            "card_status",
            "field_sources",
            "protocol_check",
            "action_match",
            "kb_fallback",
            "risk_gate",
            "workflow_trace",
            "trace",
        }
        for key in passthrough_keys:
            if key in content and content[key] not in (None, ""):
                enriched[key] = content[key]
    return enriched


def _event_with_latest_feedback(event: Dict[str, Any]) -> Dict[str, Any]:
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


_RUNNER_EXPERT_ONLY_NESTED_KEYS = {
    "content_json",
    "field_sources",
    "protocol_check",
    "action_match",
    "kb_fallback",
    "risk_gate",
    "protocol_recheck",
    "workflow_trace",
    "trace",
    "training_load_factors",
    "raw_text",
    "expert_metadata",
    "source_registry_id",
    "retrieval_mode",
    "score",
    "source_path",
    "local_path",
    "chunk_id",
    "rag_eval",
    "source_quality",
}


def _response_payload(value: Any) -> Dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return dict(value or {})


def _drop_expert_keys_deep(value: Any, keys: Optional[set] = None) -> Any:
    blocked = keys or _RUNNER_EXPERT_ONLY_NESTED_KEYS
    if isinstance(value, dict):
        return {
            key: _drop_expert_keys_deep(item, blocked)
            for key, item in value.items()
            if key not in blocked
        }
    if isinstance(value, list):
        return [_drop_expert_keys_deep(item, blocked) for item in value]
    return value


def _public_risk_gate(risk_gate: Dict[str, Any]) -> Dict[str, Any]:
    gate = risk_gate if isinstance(risk_gate, dict) else {}
    return {
        key: gate.get(key)
        for key in ("status", "product_status", "adjustment_action", "decision_reason", "triggers")
        if gate.get(key) not in (None, "", [])
    }


def _public_protocol_recheck(protocol_recheck: Dict[str, Any]) -> Dict[str, Any]:
    recheck = protocol_recheck if isinstance(protocol_recheck, dict) else {}
    return {
        "allowed": bool(recheck.get("allowed", True)),
        "risk_gate_status": str(recheck.get("risk_gate_status") or ""),
    }


def _project_runner_training_plan_review(review: Dict[str, Any]) -> Dict[str, Any]:
    public_review = _drop_expert_keys_deep(copy.deepcopy(review or {}))
    summary = public_review.get("summary")
    if isinstance(summary, dict):
        summary["review_scope"] = [
            item
            for item in summary.get("review_scope", [])
            if str(item) not in {"field_sources", "workflow_trace", "risk_gate", "protocol_recheck"}
        ]
    return public_review


def _project_runner_query_response(response: QueryResponse) -> Dict[str, Any]:
    payload = _response_payload(response)
    payload["workflow_trace"] = {}
    payload["token_usage"] = {}
    payload["audit_scores"] = {}
    payload["half_marathon_protocol_validation"] = None
    for key in (
        "structured_training_plan",
        "structured_report",
        "training_explanation_panel",
        "monthly_training_calendar",
        "daily_schedule_cards",
        "phases",
        "training_load_summary",
    ):
        payload[key] = _drop_expert_keys_deep(payload.get(key))
    payload["training_plan_review"] = _project_runner_training_plan_review(payload.get("training_plan_review") or {})
    payload["evidence_chain"] = _drop_expert_keys_deep(payload.get("evidence_chain") or {})
    return payload


def _project_query_response_for_role(response: QueryResponse, role: str) -> Any:
    if role == "expert":
        return response
    return _project_runner_query_response(response)


def _project_runner_feedback_summary(feedback: Dict[str, Any]) -> Dict[str, Any]:
    latest = feedback if isinstance(feedback, dict) else {}
    allowed_keys = {
        "id",
        "feedback_id",
        "event_id",
        "plan_id",
        "completion_status",
        "completion_quality",
        "subjective_fatigue",
        "pain_status",
        "sleep_quality",
        "notes",
        "reason_codes",
        "next_day_adjustment",
        "weekly_adjustment",
        "alternative_workout",
        "risk_alert",
        "rationale",
        "created_at",
    }
    return {
        key: _drop_expert_keys_deep(value)
        for key, value in latest.items()
        if key in allowed_keys and value not in (None, "")
    }


def _project_runner_feedback_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    projected = copy.deepcopy(payload)
    projected["risk_gate"] = _public_risk_gate(projected.get("risk_gate") or {})
    projected["protocol_recheck"] = _public_protocol_recheck(projected.get("protocol_recheck") or {})
    adaptive_feedback = projected.get("adaptive_feedback") if isinstance(projected.get("adaptive_feedback"), dict) else {}
    projected["adaptive_feedback"] = {
        key: _drop_expert_keys_deep(value)
        for key, value in adaptive_feedback.items()
        if key in {"reason_codes", "reasons", "source"}
    }
    projected["workflow_trace"] = {}
    return projected


def _project_feedback_response_for_role(payload: Dict[str, Any], role: str) -> Dict[str, Any]:
    if role == "expert":
        return payload
    return _project_runner_feedback_response(payload)


def _project_runner_plan_event(event: Dict[str, Any]) -> Dict[str, Any]:
    projected = _drop_expert_keys_deep(copy.deepcopy(event or {}))
    latest = event.get("latest_feedback") if isinstance(event, dict) else None
    if isinstance(latest, dict):
        projected["latest_feedback"] = _project_runner_feedback_summary(latest)
    return projected


def _project_runner_adjustment_history(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    projected = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        public_item = {
            key: _drop_expert_keys_deep(value)
            for key, value in item.items()
            if key not in {"risk_gate", "protocol_recheck"}
        }
        projected.append(public_item)
    return projected


def _project_runner_plan_detail_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    projected = copy.deepcopy(payload)
    plan = dict(projected.get("plan") or {})
    plan.pop("structured_plan_json", None)
    projected["plan"] = plan
    projected["structured_training_plan"] = _drop_expert_keys_deep(projected.get("structured_training_plan") or {})
    projected["workflow_trace"] = {}
    projected["events"] = [_project_runner_plan_event(event) for event in projected.get("events") or []]
    projected["adjustment_history"] = _project_runner_adjustment_history(projected.get("adjustment_history") or [])
    projected["execution_status_summary"] = _drop_expert_keys_deep(projected.get("execution_status_summary") or {})
    projected["training_plan_review"] = _project_runner_training_plan_review(projected.get("training_plan_review") or {})
    projected["evidence_chain"] = _drop_expert_keys_deep(projected.get("evidence_chain") or {})
    return projected


def _project_plan_detail_response_for_role(payload: Dict[str, Any], role: str) -> Dict[str, Any]:
    if role == "expert":
        return payload
    return _project_runner_plan_detail_response(payload)


def _project_runner_training_calendar_response(response: TrainingCalendarResponse) -> Dict[str, Any]:
    payload = _response_payload(response)
    for key in ("days", "phases", "monthly_training_calendar", "daily_schedule_cards", "training_load_summary"):
        payload[key] = _drop_expert_keys_deep(payload.get(key))
    payload["training_plan_review"] = _project_runner_training_plan_review(payload.get("training_plan_review") or {})
    payload["evidence_chain"] = _drop_expert_keys_deep(payload.get("evidence_chain") or {})
    return payload


def _project_training_calendar_response_for_role(response: TrainingCalendarResponse, role: str) -> Any:
    if role == "expert":
        return response
    return _project_runner_training_calendar_response(response)


def _compose_skeleton_report(structured_plan: Dict[str, Any], status_message: str) -> str:
    meta = structured_plan.get("plan_meta", {}) if isinstance(structured_plan, dict) else {}
    weeks = structured_plan.get("week_plans", []) if isinstance(structured_plan, dict) else []
    first_week = weeks[0] if weeks else {}
    key_workouts = first_week.get("key_workouts") or []
    key_lines = "\n".join(f"- {item}" for item in key_workouts[:4]) or "- 首周关键训练将在日历卡片中展示。"
    return (
        "## 结构化训练计划已生成\n\n"
        f"{status_message}\n\n"
        f"- 目标：{meta.get('goal', '未设置')}\n"
        f"- 周期：{meta.get('actual_weeks', len(weeks) or '-') } 周\n"
        f"- 计划类型：{meta.get('plan_type', 'multi_week')}\n"
        f"- 首周阶段：{first_week.get('phase', '待生成')}\n"
        f"- 首周负荷：{first_week.get('load_level', '待生成')}\n\n"
        "### 首周关键训练\n"
        f"{key_lines}\n\n"
        "LLM 解释和更多证据会由前端异步补充；当前结果先保证日历、强度区间和规则骨架可用。"
    )


def _build_skeleton_state(request: QueryRequest, profile: Dict[str, Any]) -> IntegratedState:
    state: IntegratedState = build_working_state(query=request.query, user_profile=profile)
    state.update(
        {
            "mode": "subagent",
            "workflow_kind": "plan",
            "intent_type": "plan",
            "category": "coach",
            "skip_calendar_kb_fallback": True,
            "reasoning_log": ["[api] 已启用 Astro skeleton-first 快速计划路径"],
        }
    )
    structured_plan = build_structured_training_plan_skeleton(
        query=request.query,
        profile=profile,
        requested_weeks=state.get("requested_weeks"),
    )
    state["structured_training_plan"] = structured_plan
    state["evidence_bundle"] = build_evidence_bundle(
        query=request.query,
        structured_training_plan=structured_plan,
        health=get_knowledge_base_health_snapshot(),
    )
    return state


def _has_calendar_source_plan(structured_plan: Any) -> bool:
    return isinstance(structured_plan, dict) and bool(structured_plan.get("week_plans"))


def _calendar_contract_from_plan(structured_plan: Dict[str, Any]) -> Dict[str, Any]:
    calendar = generate_daily_schedule(structured_plan, enable_kb_fallback=True)
    calendar_payload = calendar.to_dict() if calendar else None
    daily_schedule_cards = list((calendar_payload or {}).get("days") or [])
    training_load_summary = dict((calendar_payload or {}).get("training_load_summary") or {})
    return {
        "monthly_training_calendar": calendar_payload,
        "daily_schedule_cards": daily_schedule_cards,
        "phases": list((calendar_payload or {}).get("phases") or []),
        "training_load_summary": training_load_summary,
        "training_plan_review": build_training_plan_review(
            structured_training_plan=structured_plan,
            daily_schedule_cards=daily_schedule_cards,
            training_load_summary=training_load_summary,
        ),
    }


def _answer_source_mode_from_result(
    result: Dict[str, Any],
    structured_plan: Any,
    generation_status: str,
) -> str:
    if generation_status == "medical_referral":
        return "medical_referral"
    if isinstance(structured_plan, dict) and structured_plan.get("week_plans"):
        return "structured_plan_rule"
    report = str(result.get("final_report") or result.get("report") or "")
    if "source_type: llm_general_knowledge" in report or "模型通用知识回答" in report:
        return "model_general_knowledge"
    bundle = result.get("evidence_bundle") if isinstance(result.get("evidence_bundle"), dict) else {}
    if bundle.get("evidence_items"):
        return ""
    return "model_general_knowledge"


def _build_response_evidence_chain(
    *,
    query: str,
    evidence_bundle: Any = None,
    answer_source_mode: str = "",
) -> Dict[str, Any]:
    return build_evidence_chain_payload(
        query=query,
        evidence_bundle=evidence_bundle if isinstance(evidence_bundle, dict) else None,
        answer_source_mode=answer_source_mode,
        health=get_knowledge_base_health_snapshot(),
    )


async def _build_skeleton_plan_response(
    request: QueryRequest,
    profile: Dict[str, Any],
    *,
    generation_status: str,
    message: str,
) -> QueryResponse:
    started = time.perf_counter()
    state = await asyncio.to_thread(_build_skeleton_state, request, profile)
    build_elapsed = time.perf_counter() - started
    structured_plan = state["structured_training_plan"]
    calendar_started = time.perf_counter()
    monthly_training_calendar = await asyncio.to_thread(
        generate_daily_schedule,
        structured_plan,
        enable_kb_fallback=True,
    )
    calendar_elapsed = time.perf_counter() - calendar_started
    daily_schedule_cards = [
        item.to_dict() if hasattr(item, "to_dict") else item
        for item in (monthly_training_calendar.days if monthly_training_calendar else [])
    ]
    calendar_payload = monthly_training_calendar.to_dict() if monthly_training_calendar else None
    phases = list((calendar_payload or {}).get("phases") or [])
    training_load_summary = dict((calendar_payload or {}).get("training_load_summary") or {})
    training_plan_review = build_training_plan_review(
        structured_training_plan=structured_plan,
        daily_schedule_cards=daily_schedule_cards,
        training_load_summary=training_load_summary,
    )
    report = _compose_skeleton_report(structured_plan, message)
    audit_scores = {
        "consistency": 90,
        "safety": 90,
        "roi": 70,
        "summary": "规则骨架已生成，等待可选 LLM 解释补充。",
        "score_sources": {"path": "astro_skeleton_first"},
    }
    workflow_trace = build_workflow_trace(
        query=request.query,
        workflow_kind=state.get("workflow_kind", "plan"),
        intent_type=state.get("intent_type", "plan"),
        status=generation_status,
        evidence_bundle=state.get("evidence_bundle"),
        structured_training_plan=structured_plan,
    )
    state["workflow_trace"] = workflow_trace
    if isinstance(structured_plan, dict):
        structured_plan["workflow_trace"] = workflow_trace
    evidence_chain = _build_response_evidence_chain(
        query=request.query,
        evidence_bundle=state.get("evidence_bundle"),
        answer_source_mode="structured_plan_rule",
    )
    save_started = time.perf_counter()
    training_plan_id = _save_plan_if_ready(structured_plan, request, daily_schedule_cards)
    save_elapsed = time.perf_counter() - save_started
    total_elapsed = time.perf_counter() - started
    response = QueryResponse(
        report=report,
        structured_training_plan=structured_plan,
        structured_report=None,
        training_explanation_panel=None,
        monthly_training_calendar=calendar_payload,
        daily_schedule_cards=daily_schedule_cards,
        phases=phases,
        training_load_summary=training_load_summary,
        training_plan_review=training_plan_review,
        token_usage={},
        audit_scores=audit_scores,
        guided_questions=[],
        training_plan_id=training_plan_id,
        generation_status=generation_status,
        llm_provider=_normalize_provider(request.llm_provider),
        llm_model=_selected_model(request),
        message=message,
        generation_timings={
            "skeleton_build_sec": round(build_elapsed, 3),
            "calendar_enrich_sec": round(calendar_elapsed, 3),
            "save_plan_sec": round(save_elapsed, 3),
            "total_sec": round(total_elapsed, 3),
        },
        half_marathon_protocol_validation=structured_plan.get("half_marathon_protocol_validation")
        if isinstance(structured_plan, dict)
        else None,
        workflow_trace=workflow_trace,
        evidence_chain=evidence_chain,
    )
    record_generation_status(generation_status, duration_sec=total_elapsed)
    return response


def _query_response_from_state(
    result: Dict[str, Any],
    request: QueryRequest,
    *,
    generation_status: str,
    message: str = "",
    training_plan_id: Optional[str] = None,
) -> QueryResponse:
    raw_structured_report = result.get("structured_report")
    structured_report = dict(raw_structured_report) if isinstance(raw_structured_report, dict) else raw_structured_report
    structured_plan = result.get("structured_training_plan")
    training_explanation_panel = None
    monthly_training_calendar = None
    daily_schedule_cards = None
    phases: List[Dict[str, Any]] = []
    training_load_summary: Dict[str, Any] = {}
    training_plan_review: Dict[str, Any] = {}
    if isinstance(structured_report, dict):
        training_explanation_panel = structured_report.get("training_explanation_panel")
        monthly_training_calendar = structured_report.get("monthly_training_calendar")
        daily_schedule_cards = structured_report.get("daily_schedule_cards")
        phases = list(structured_report.get("phases") or [])
        training_load_summary = dict(structured_report.get("training_load_summary") or {})
        training_plan_review = dict(structured_report.get("training_plan_review") or {})

    if (not monthly_training_calendar or not daily_schedule_cards) and _has_calendar_source_plan(structured_plan):
        contract = _calendar_contract_from_plan(structured_plan)
        monthly_training_calendar = monthly_training_calendar or contract["monthly_training_calendar"]
        daily_schedule_cards = daily_schedule_cards or contract["daily_schedule_cards"]
        phases = phases or contract["phases"]
        training_load_summary = training_load_summary or contract["training_load_summary"]
        training_plan_review = training_plan_review or contract["training_plan_review"]
        if isinstance(structured_report, dict):
            structured_report["monthly_training_calendar"] = monthly_training_calendar
            structured_report["daily_schedule_cards"] = daily_schedule_cards
            structured_report["phases"] = phases
            structured_report["training_load_summary"] = training_load_summary
            structured_report["training_plan_review"] = training_plan_review
    elif isinstance(monthly_training_calendar, dict):
        phases = phases or list(monthly_training_calendar.get("phases") or [])
        training_load_summary = training_load_summary or dict(monthly_training_calendar.get("training_load_summary") or {})
        training_plan_review = training_plan_review or dict(monthly_training_calendar.get("training_plan_review") or {})

    if not training_plan_review and _has_calendar_source_plan(structured_plan):
        training_plan_review = build_training_plan_review(
            structured_training_plan=structured_plan,
            daily_schedule_cards=daily_schedule_cards or [],
            training_load_summary=training_load_summary,
        )
        if isinstance(structured_report, dict):
            structured_report["training_plan_review"] = training_plan_review

    workflow_trace: Dict[str, Any] = {}
    if isinstance(result.get("workflow_trace"), dict):
        workflow_trace = result["workflow_trace"]
    elif isinstance(structured_report, dict) and isinstance(structured_report.get("workflow_trace"), dict):
        workflow_trace = structured_report["workflow_trace"]
    elif isinstance(structured_plan, dict) and isinstance(structured_plan.get("workflow_trace"), dict):
        workflow_trace = structured_plan["workflow_trace"]
    if not workflow_trace:
        workflow_trace = build_workflow_trace(
            query=request.query,
            workflow_kind=str(result.get("workflow_kind") or result.get("category") or ""),
            intent_type=str(result.get("intent_type") or ""),
            status=generation_status,
            evidence_bundle=result.get("evidence_bundle") if isinstance(result.get("evidence_bundle"), dict) else None,
            structured_training_plan=structured_plan if isinstance(structured_plan, dict) else None,
            adaptive_feedback=result.get("adaptive_feedback") if isinstance(result.get("adaptive_feedback"), dict) else None,
            adaptive_adjustment=result.get("adaptive_adjustment") if isinstance(result.get("adaptive_adjustment"), dict) else None,
        )
    if isinstance(structured_report, dict):
        structured_report["workflow_trace"] = workflow_trace
    if isinstance(structured_plan, dict):
        structured_plan["workflow_trace"] = workflow_trace
    evidence_chain = result.get("evidence_chain") if isinstance(result.get("evidence_chain"), dict) else {}
    if not evidence_chain:
        evidence_chain = _build_response_evidence_chain(
            query=request.query,
            evidence_bundle=result.get("evidence_bundle"),
            answer_source_mode=_answer_source_mode_from_result(result, structured_plan, generation_status),
        )

    response = QueryResponse(
        report=result.get("final_report", ""),
        structured_training_plan=structured_plan,
        structured_report=structured_report,
        training_explanation_panel=training_explanation_panel,
        monthly_training_calendar=monthly_training_calendar,
        daily_schedule_cards=daily_schedule_cards,
        phases=phases,
        training_load_summary=training_load_summary,
        training_plan_review=training_plan_review,
        token_usage=result.get("token_usage", {}),
        audit_scores=result.get("audit_scores", {}),
        guided_questions=result.get("guided_questions", []),
        training_plan_id=training_plan_id or _save_plan_if_ready(structured_plan, request, daily_schedule_cards),
        generation_status=generation_status,
        llm_provider=_normalize_provider(request.llm_provider),
        llm_model=_selected_model(request),
        message=message,
        half_marathon_protocol_validation=structured_plan.get("half_marathon_protocol_validation")
        if isinstance(structured_plan, dict)
        else None,
        workflow_trace=workflow_trace,
        evidence_chain=evidence_chain,
    )
    record_generation_status(generation_status)
    return response

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "provider": os.getenv("LLM_PROVIDER", "ollama"),
        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:latest"),
        "rag": get_knowledge_base_health_snapshot(),
    }


@app.get("/ops/metrics", response_model=OpsMetricsResponse)
async def get_ops_metrics():
    return metrics_snapshot()


@app.delete("/plans/{plan_id}")
async def delete_plan(plan_id: str, user_id: str = DEFAULT_API_USER_ID):
    """删除已保存的训练计划及其日历事件。"""
    _require_default_user(user_id)
    plan = get_db().get_plan(plan_id)
    if not plan or plan.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="训练计划不存在。")
    if not get_db().delete_training_plan(plan_id):
        raise HTTPException(status_code=404, detail="训练计划不存在。")
    return {"deleted": True, "plan_id": plan_id}


@app.get("/profile")
async def get_profile(user_id: str = DEFAULT_API_USER_ID):
    """返回当前单用户跑者画像，供 Astro 工作台初始化。"""
    _require_default_user(user_id)
    return {"user_id": user_id, "profile": load_user_profile()}


@app.post("/profile")
async def save_profile(request: ProfileRequest):
    """保存 Astro 工作台提交的跑者画像草稿。"""
    _require_default_user(request.user_id)
    profile = _save_profile_patch(request.profile or {})
    return {"user_id": request.user_id, "profile": profile}


@app.get("/profile/{user_id}")
async def get_profile_by_user(user_id: str):
    """按设计文档路径返回完整用户画像。"""
    _require_default_user(user_id)
    return {"user_id": user_id, "profile": load_user_profile()}


@app.put("/profile/{user_id}")
async def put_profile_by_user(user_id: str, request: ProfileRequest):
    """按设计文档路径更新用户画像；当前单用户模式下采用合并写入。"""
    _require_default_user(user_id)
    _require_default_user(request.user_id)
    profile = _save_profile_patch(request.profile or {})
    return {"user_id": user_id, "profile": profile}


@app.patch("/profile/{user_id}/fields/{field_key}")
async def patch_profile_field(user_id: str, field_key: str, request: ProfileFieldRequest):
    """更新单个画像字段，并同步由画像衍生的强度区间。"""
    _require_default_user(user_id)
    if not field_key or field_key.startswith("_"):
        raise HTTPException(status_code=400, detail="画像字段名无效。")
    profile = _save_profile_patch({field_key: request.value})
    return {"user_id": user_id, "field_key": field_key, "profile": profile}


@app.get("/profile/{user_id}/zones")
async def get_profile_zones(user_id: str):
    """从当前画像实时衍生 LTHR 九区和配速区间。"""
    _require_default_user(user_id)
    zones = _profile_zones(load_user_profile())
    return {"user_id": user_id, **zones}


@app.post("/profile/{user_id}/nlu-extract")
async def preview_profile_nlu_extract(user_id: str, request: NluExtractRequest):
    """从自然语言中提取画像变更建议；需要用户确认后才写入。"""
    _require_default_user(user_id)
    suggestions = _extract_profile_suggestions(request.text)
    return {
        "user_id": user_id,
        "suggested_changes": suggestions,
        "requires_confirmation": True,
    }


@app.get("/llm-options")
async def get_llm_options(request: Request):
    """返回前端模型选择控件所需的可用模型清单。"""
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:latest")
    deepseek_model = os.getenv("DEEPSEEK_MODEL", os.getenv("DS_MODEL", "deepseek-v4-pro"))
    openai_model = os.getenv("OPENAI_MODEL", "gpt-5.5")
    default_provider = _normalize_provider(os.getenv("LLM_PROVIDER", "ollama"))
    default_model = {
        "ds": deepseek_model,
        "openai": openai_model,
    }.get(default_provider, ollama_model)
    configured_token = _configured_api_token()
    can_show_private_config = not configured_token or hmac.compare_digest(_request_api_token(request), configured_token)
    return {
        "default": {
            "provider": default_provider,
            "model": default_model,
        },
        "providers": [
            {
                "id": "ollama",
                "label": "Ollama",
                "default_model": ollama_model,
                "models": [ollama_model],
            },
            {
                "id": "ds",
                "label": "DeepSeek",
                "default_model": deepseek_model,
                "models": [deepseek_model],
                "api_key_configured": bool(os.getenv("DEEPSEEK_API_KEY") or os.getenv("DS_API_KEY")) if can_show_private_config else False,
                "api_key_config_visible": bool(can_show_private_config),
            },
            {
                "id": "openai",
                "label": "OpenAI GPT",
                "default_model": openai_model,
                "models": [openai_model],
                "api_key_configured": bool(os.getenv("OPENAI_API_KEY")) if can_show_private_config else False,
                "api_key_config_visible": bool(can_show_private_config),
            },
        ],
    }


@app.get("/plans")
async def list_plans(user_id: str = DEFAULT_API_USER_ID):
    """列出本地已保存训练计划。空列表表示暂无历史，不应返回 404。"""
    _require_default_user(user_id)
    return {"plans": get_db().list_training_plans(user_id=user_id)}


@app.post("/plans")
async def save_plan(request: SavePlanRequest):
    """保存前端当前结构化训练计划，并同步生成本地日历事件。"""
    _require_default_user(request.user_id)
    if not request.structured_training_plan:
        raise HTTPException(status_code=400, detail="structured_training_plan 不能为空。")
    calendar_settings = request.calendar_settings or {}
    plan_id = get_db().save_training_plan(
        request.structured_training_plan,
        source_query=request.source_query,
        user_id=request.user_id,
        calendar_days=request.calendar_days,
        training_start_date=str(calendar_settings.get("training_start_date") or ""),
        default_start_time=str(calendar_settings.get("default_start_time") or "07:00"),
    )
    return {"plan_id": plan_id, "saved": True}


@app.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest, http_request: Request):
    """根据训练反馈返回自适应调整建议，供 Astro 反馈面板使用。"""
    _require_default_user(request.user_id)
    workout_feedback = normalize_workout_feedback(
        _normalize_frontend_feedback(request.feedback or {}),
        raw_text=request.raw_text,
    )
    risk_gate = build_feedback_risk_gate(workout_feedback, raw_text=request.raw_text)
    protocol_recheck = build_feedback_protocol_recheck(risk_gate)
    reasons = derive_adaptive_reasons(workout_feedback, raw_text=request.raw_text)
    adaptive_adjustment = build_adaptive_adjustment_contract(workout_feedback, raw_text=request.raw_text)
    if risk_gate.get("product_status") == "medical_referral":
        adaptive_adjustment = _medical_referral_adjustment(adaptive_adjustment)
    adaptive_adjustment["adjustment_action"] = risk_gate.get("adjustment_action", "none")
    adaptive_adjustment["workflow_status"] = risk_gate.get("product_status", "generated")
    reason_codes = [reason["code"] for reason in reasons]
    plan_diff = _build_feedback_plan_diff(
        risk_gate=risk_gate,
        protocol_recheck=protocol_recheck,
        adaptive_adjustment=adaptive_adjustment,
        reason_codes=reason_codes,
    )
    feedback_id = None
    if bool(request.plan_id) != bool(request.event_id):
        raise HTTPException(status_code=400, detail="保存训练反馈需要同时提供 plan_id 和 event_id。")
    if request.plan_id and request.event_id:
        if not get_db().get_event(request.plan_id, request.event_id, request.user_id):
            raise HTTPException(status_code=404, detail="训练日历事件不存在，反馈未保存。")
        feedback_id = get_db().save_training_event_feedback(
            plan_id=request.plan_id,
            event_id=request.event_id,
            user_id=request.user_id,
            workout_feedback=workout_feedback,
            reason_codes=reason_codes,
            adaptive_adjustment=adaptive_adjustment,
            risk_gate=risk_gate,
            protocol_recheck=protocol_recheck,
            raw_text=request.raw_text,
        )
    adaptive_feedback = {
        "workout_feedback": workout_feedback,
        "reason_codes": reason_codes,
        "reasons": reasons,
        "raw_text": request.raw_text,
        "source": "astro_feedback_form",
        "workflow": ["risk_gate", "protocol_recheck", "adjustment"],
    }
    workflow_trace = build_workflow_trace(
        query=request.raw_text,
        workflow_kind="adaptive",
        intent_type="feedback",
        status=risk_gate.get("product_status", "generated"),
        risk_gate=risk_gate,
        protocol_recheck=protocol_recheck,
        adaptive_feedback=adaptive_feedback,
        adaptive_adjustment=adaptive_adjustment,
        feedback_id=feedback_id,
        feedback_persisted=bool(feedback_id),
    )
    generation_status = risk_gate.get("product_status", "generated")
    record_feedback_risk(risk_gate)
    record_generation_status(generation_status)
    response_payload = {
        "workout_feedback": workout_feedback,
        "risk_gate": risk_gate,
        "protocol_recheck": protocol_recheck,
        "adaptive_feedback": adaptive_feedback,
        "adaptive_adjustment": adaptive_adjustment,
        "plan_diff": plan_diff,
        "generation_status": generation_status,
        "feedback_id": feedback_id,
        "workflow_trace": workflow_trace,
    }
    return _project_feedback_response_for_role(response_payload, _response_role(http_request))


@app.get("/plans/{plan_id}", response_model=PlanDetailResponse)
async def get_plan(plan_id: str, http_request: Request, user_id: str = DEFAULT_API_USER_ID):
    """返回单个已保存训练计划及其日历事件。"""
    _require_default_user(user_id)
    plan = get_db().get_plan(plan_id)
    if not plan or plan.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="训练计划不存在。")
    structured_plan = _load_structured_plan(plan)
    events = [_event_with_latest_feedback(event) for event in get_db().list_events(plan_id)]
    calendar_day_contract = events
    training_plan_review = (
        build_training_plan_review(
            structured_training_plan=structured_plan,
            daily_schedule_cards=calendar_day_contract,
        )
        if isinstance(structured_plan, dict)
        else {}
    )
    response_payload = {
        "plan": plan,
        "structured_training_plan": structured_plan,
        "workflow_trace": structured_plan.get("workflow_trace", {}) if isinstance(structured_plan, dict) else {},
        "events": events,
        "execution_status_summary": build_execution_status_summary(
            events,
            plan={**plan, **(structured_plan.get("plan_meta") or {})},
        ),
        "adjustment_history": _build_adjustment_history(plan_id, events),
        "training_plan_review": training_plan_review,
        "evidence_chain": _build_response_evidence_chain(
            query=str(plan.get("source_query") or ""),
            evidence_bundle=(structured_plan.get("evidence_bundle") if isinstance(structured_plan, dict) else None),
            answer_source_mode="structured_plan_rule" if isinstance(structured_plan, dict) else "",
        ),
    }
    return _project_plan_detail_response_for_role(response_payload, _response_role(http_request))


@app.patch("/plans/{plan_id}/events/{event_id}")
async def update_plan_event_schedule(
    plan_id: str,
    event_id: str,
    request: EventScheduleRequest,
    user_id: str = DEFAULT_API_USER_ID,
):
    """更新已保存训练日历事件的日期、开始时间和时长。"""
    _require_default_user(user_id)
    plan = get_db().get_plan(plan_id)
    if not plan or plan.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="训练计划不存在。")
    events = get_db().list_events(plan_id)
    if not any(event.get("id") == event_id for event in events):
        raise HTTPException(status_code=404, detail="训练日历事件不存在。")
    updated = get_db().update_event_schedule(
        event_id,
        scheduled_date=request.scheduled_date,
        start_time=request.start_time,
        duration_min=request.duration_min,
    )
    return {"updated": updated}


@app.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest, http_request: Request):
    """查询接口。Astro 计划生成默认可走 skeleton-first，避免前端长时间空等。"""
    _require_default_user(request.user_id)

    profile = merge_plan_profile_overrides(request.query, load_user_profile())
    response_mode = str(request.response_mode or "full").strip().lower()
    skeleton_requested = response_mode in {"skeleton", "skeleton_first"}
    empty_profile_plan = not str(request.query or "").strip() and _has_plan_generation_profile(profile)
    plan_query = _is_plan_query(request.query) or empty_profile_plan

    if plan_query and (skeleton_requested or empty_profile_plan):
        return _project_query_response_for_role(
            await _build_skeleton_plan_response(
                request,
                profile,
                generation_status="skeleton_ready",
                message="已先返回确定性结构化计划骨架，避免模型长时间生成导致前端卡住。",
            ),
            _response_role(http_request),
        )

    ensure_knowledge_base_ready()
    initial_state: IntegratedState = build_working_state(query=request.query, user_profile=profile)
    config = _build_llm_config(request)

    try:
        result = await asyncio.wait_for(
            integrated_app.ainvoke(initial_state, config=config),
            timeout=float(request.timeout_sec),
        )
        return _project_query_response_for_role(
            _query_response_from_state(
                result,
                request,
                generation_status="complete",
                message="完整工作流已返回。",
            ),
            _response_role(http_request),
        )
    except asyncio.TimeoutError:
        if plan_query:
            return _project_query_response_for_role(
                await _build_skeleton_plan_response(
                    request,
                    profile,
                    generation_status="llm_timeout_skeleton",
                    message=f"完整 LLM 工作流超过 {request.timeout_sec} 秒，已回退到结构化规则骨架。",
                ),
                _response_role(http_request),
            )
        raise HTTPException(status_code=504, detail=f"完整 LLM 工作流超过 {request.timeout_sec} 秒。")
    except Exception as e:
        if plan_query:
            return _project_query_response_for_role(
                await _build_skeleton_plan_response(
                    request,
                    profile,
                    generation_status="llm_error_skeleton",
                    message=f"完整 LLM 工作流异常，已回退到结构化规则骨架：{_safe_workflow_error_summary(e)}。",
                ),
                _response_role(http_request),
            )
        raise HTTPException(status_code=500, detail=_safe_workflow_error_summary(e))


@app.get("/zone-reference", response_model=ZoneReference)
async def get_zone_reference():
    """返回 Z1-Z9 强度区间中文术语参考表"""
    return ZoneReference(
        zones=ZONE_LABELS,
        zones_detail=ZONE_LABELS_DETAIL,
    )


@app.get("/evidence-tier-reference")
async def get_evidence_tier_reference():
    """返回证据分层标记的中文映射"""
    return {
        "evidence_tiers": EVIDENCE_TIER_LABELS,
        "evidence_drawer_contract": {
            "display_modes": EVIDENCE_CHAIN_DISPLAY_MODES,
            "answer_source_modes": ANSWER_SOURCE_MODES,
            "public_fields": [
                "evidence_id",
                "display_mode",
                "source_label",
                "source_url",
                "page",
                "section",
                "evidence_domain",
                "prescription_permission",
                "user_facing_summary",
            ],
            "expert_only_fields": [
                "source_registry_id",
                "retrieval_mode",
                "score",
                "chunk_id",
                "rag_eval",
                "source_quality",
                "expert_metadata",
            ],
            "no_fake_citation_rule": "When source_url/page/section are missing, display model_general_knowledge or needs_evidence instead of a citation badge.",
        },
        "core_prescription_permissions": {
            "allowed_domains": ["protocol", "action_library"],
            "required_permission": "can_write_core",
            "blocked_sources": ["llm_general_knowledge", "sports_science_reference_without_structured_rule"],
        },
        "descriptions": {
            "action_library": "课表数据来自动作库直接证据，训练方案经过验证。",
            "protocol_rule": "课表由 HMP 基石协议确定性排课，动作库注册表提供执行细节和替代方案。",
            "kb_fallback": "动作库中未找到该训练类型的直接证据，已基于其他知识库内容生成参考课表。",
            "needs_evidence": "当前训练类型缺少可绑定动作库证据，暂不向用户展示模板化主课。",
            "plan_only": "当前训练类型在知识库中暂无充分证据支撑，基于训练计划骨架生成。",
        },
    }


@app.post("/training-calendar", response_model=TrainingCalendarResponse)
async def get_training_calendar(request: QueryRequest, http_request: Request):
    """生成并返回训练日历（月历视图数据）"""
    _require_default_user(request.user_id)

    profile = load_user_profile()
    initial_state: IntegratedState = build_working_state(query=request.query, user_profile=profile)

    try:
        result = await integrated_app.ainvoke(initial_state)
        structured_training_plan = result.get("structured_training_plan")
        if not structured_training_plan:
            raise HTTPException(status_code=404, detail="未生成训练计划，请先使用 /query 接口生成训练计划。")

        calendar = generate_daily_schedule(structured_training_plan)
        if not calendar or not calendar.days:
            raise HTTPException(status_code=404, detail="训练日历生成失败，计划数据不完整。")

        calendar_payload = calendar.to_dict()
        daily_schedule_cards = list(calendar_payload.get("days") or [])
        training_plan_review = build_training_plan_review(
            structured_training_plan=structured_training_plan,
            daily_schedule_cards=daily_schedule_cards,
            training_load_summary=calendar.training_load_summary,
        )
        response = TrainingCalendarResponse(
            year=calendar.year,
            month=calendar.month,
            start_week_index=calendar.start_week_index,
            end_week_index=calendar.end_week_index,
            total_days=calendar.total_days,
            days=daily_schedule_cards,
            phases=calendar.phases,
            evidence_summary=calendar.evidence_summary,
            monthly_training_calendar=calendar_payload,
            daily_schedule_cards=daily_schedule_cards,
            training_load_summary=calendar.training_load_summary,
            training_plan_review=training_plan_review,
            evidence_chain=_build_response_evidence_chain(
                query=request.query,
                evidence_bundle=(
                    structured_training_plan.get("evidence_bundle")
                    if isinstance(structured_training_plan, dict)
                    else None
                ),
                answer_source_mode="structured_plan_rule",
            ),
        )
        return _project_training_calendar_response_for_role(response, _response_role(http_request))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_workflow_error_summary(e))


@app.get("/training-calendar/day-detail/{day_index}", response_model=DayDetailResponse)
async def get_day_detail(day_index: int):
    """返回训练日历中某一天的详情（从会话提取或历史缓存的日历数据）"""
    return DayDetailResponse(
        day={"day_index": day_index, "note": "请通过 /training-calendar 接口获取完整日历后在客户端侧查找。"},
        evidence_tier_labels=EVIDENCE_TIER_LABELS,
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
