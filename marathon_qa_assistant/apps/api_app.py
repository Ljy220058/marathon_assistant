import json
import os
import sys
import asyncio
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
from marathon_qa_assistant.core.training_plan_skeleton import build_structured_training_plan_skeleton
from marathon_qa_assistant.core.state_models import (
    build_adaptive_adjustment_contract,
    build_feedback_protocol_recheck,
    build_feedback_risk_gate,
    derive_adaptive_reasons,
    normalize_workout_feedback,
)
from marathon_qa_assistant.core.kb_bootstrap import (
    bootstrap_knowledge_base,
    ensure_knowledge_base_ready,
    get_knowledge_base_health_snapshot,
)
from marathon_qa_assistant.services.daily_schedule_generator import generate_daily_schedule
from marathon_qa_assistant.services.database import get_db
from marathon_qa_assistant.services.workout_template_retriever import (
    WORKOUT_TEMPLATE_REGISTRY,
    ZONE_LABELS,
    ZONE_LABELS_DETAIL,
    EVIDENCE_TIER_LABELS,
)

DEFAULT_API_USER_ID = "default_user"

app = FastAPI(title="Marathon QA Assistant API", version="1.0.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # Browsers reject "*" + credentials, so keep the API permissive but stateless.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    mode: str = "team"  # team (coach) or research
    user_id: str = DEFAULT_API_USER_ID
    stream: bool = False
    llm_provider: str = "ollama"
    llm_model: str = ""
    ds_api_key: str = ""
    response_mode: str = "full"  # full | skeleton | skeleton_first
    timeout_sec: int = Field(default=45, ge=5, le=180)

class QueryResponse(BaseModel):
    report: str
    structured_training_plan: Optional[Dict[str, Any]] = None
    structured_report: Optional[Dict[str, Any]] = None
    training_explanation_panel: Optional[Dict[str, Any]] = None
    monthly_training_calendar: Optional[Dict[str, Any]] = None
    daily_schedule_cards: Optional[List[Dict[str, Any]]] = None
    token_usage: Dict[str, int]
    audit_scores: Dict[str, Any]
    guided_questions: List[str]
    training_plan_id: Optional[str] = None
    generation_status: str = "complete"
    llm_provider: str = "ollama"
    llm_model: str = ""
    message: str = ""
    generation_timings: Dict[str, float] = Field(default_factory=dict)
    half_marathon_protocol_validation: Optional[Dict[str, Any]] = None

class ProfileRequest(BaseModel):
    user_id: str = DEFAULT_API_USER_ID
    profile: Dict[str, Any]

class ProfileFieldRequest(BaseModel):
    value: Any

class NluExtractRequest(BaseModel):
    text: str = ""

class SavePlanRequest(BaseModel):
    user_id: str = DEFAULT_API_USER_ID
    source_query: str = ""
    structured_training_plan: Dict[str, Any]
    calendar_settings: Dict[str, Any] = Field(default_factory=dict)

class FeedbackRequest(BaseModel):
    user_id: str = DEFAULT_API_USER_ID
    raw_text: str = ""
    feedback: Dict[str, Any] = Field(default_factory=dict)

class EventScheduleRequest(BaseModel):
    scheduled_date: str
    start_time: str
    duration_min: int = Field(default=60, ge=0, le=600)

class TrainingCalendarResponse(BaseModel):
    year: int
    month: int
    start_week_index: int
    end_week_index: int
    total_days: int
    days: List[Dict[str, Any]]
    phases: List[Dict[str, Any]]
    evidence_summary: Dict[str, int]

class ZoneReference(BaseModel):
    zones: Dict[str, str]  # Z1-Z9 -> label mapping
    zones_detail: Dict[str, str]  # Z1-Z9 -> detail label mapping

class DayDetailResponse(BaseModel):
    day: Dict[str, Any]
    evidence_tier_labels: Dict[str, str]

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
    fatigue_map = {"轻微": "mild", "明显": "high", "高疲劳": "high"}
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
    "race prep",
    "race preparation",
    "sub ",
    "pb",
)


def _is_plan_query(query: str) -> bool:
    text = str(query or "").lower()
    return any(keyword.lower() in text for keyword in PLAN_QUERY_KEYWORDS)


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


def _normalize_provider(provider: str) -> str:
    normalized = str(provider or "ollama").strip().lower()
    return "ds" if normalized in {"ds", "deepseek"} else "ollama"


def _selected_model(request: QueryRequest) -> str:
    provider = _normalize_provider(request.llm_provider)
    if request.llm_model:
        return request.llm_model.strip()
    if provider == "ds":
        return os.getenv("DEEPSEEK_MODEL", os.getenv("DS_MODEL", "deepseek-v4-pro"))
    return os.getenv("OLLAMA_MODEL", "qwen2.5:latest")


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
            "trace",
        }
        for key in passthrough_keys:
            if key in content and content[key] not in (None, ""):
                enriched[key] = content[key]
    return enriched


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
    report = _compose_skeleton_report(structured_plan, message)
    audit_scores = {
        "consistency": 90,
        "safety": 90,
        "roi": 70,
        "summary": "规则骨架已生成，等待可选 LLM 解释补充。",
        "score_sources": {"path": "astro_skeleton_first"},
    }
    save_started = time.perf_counter()
    training_plan_id = _save_plan_if_ready(structured_plan, request, daily_schedule_cards)
    save_elapsed = time.perf_counter() - save_started
    total_elapsed = time.perf_counter() - started
    response = QueryResponse(
        report=report,
        structured_training_plan=structured_plan,
        structured_report=None,
        training_explanation_panel=None,
        monthly_training_calendar=monthly_training_calendar.to_dict() if monthly_training_calendar else None,
        daily_schedule_cards=daily_schedule_cards,
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
    )
    return response


def _query_response_from_state(
    result: Dict[str, Any],
    request: QueryRequest,
    *,
    generation_status: str,
    message: str = "",
    training_plan_id: Optional[str] = None,
) -> QueryResponse:
    structured_report = result.get("structured_report")
    training_explanation_panel = None
    monthly_training_calendar = None
    daily_schedule_cards = None
    if isinstance(structured_report, dict):
        training_explanation_panel = structured_report.get("training_explanation_panel")
        monthly_training_calendar = structured_report.get("monthly_training_calendar")
        daily_schedule_cards = structured_report.get("daily_schedule_cards")

    structured_plan = result.get("structured_training_plan")
    return QueryResponse(
        report=result.get("final_report", ""),
        structured_training_plan=structured_plan,
        structured_report=structured_report,
        training_explanation_panel=training_explanation_panel,
        monthly_training_calendar=monthly_training_calendar,
        daily_schedule_cards=daily_schedule_cards,
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
    )

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "provider": os.getenv("LLM_PROVIDER", "ollama"),
        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:latest"),
        "rag": get_knowledge_base_health_snapshot(),
    }


@app.on_event("startup")
async def startup_load_knowledge_base():
    app.state.rag_bootstrap = bootstrap_knowledge_base()


@app.delete("/plans/{plan_id}")
async def delete_plan(plan_id: str, user_id: str = DEFAULT_API_USER_ID):
    """删除已保存的训练计划及其日历事件。"""
    _require_default_user(user_id)
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
async def get_llm_options():
    """返回前端模型选择控件所需的可用模型清单。"""
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:latest")
    deepseek_model = os.getenv("DEEPSEEK_MODEL", os.getenv("DS_MODEL", "deepseek-v4-pro"))
    default_provider = os.getenv("LLM_PROVIDER", "ollama")
    return {
        "default": {
            "provider": default_provider,
            "model": deepseek_model if default_provider == "ds" else ollama_model,
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
                "api_key_configured": bool(os.getenv("DEEPSEEK_API_KEY") or os.getenv("DS_API_KEY")),
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
        training_start_date=str(calendar_settings.get("training_start_date") or ""),
        default_start_time=str(calendar_settings.get("default_start_time") or "07:00"),
    )
    return {"plan_id": plan_id, "saved": True}


@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
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
    adaptive_adjustment["adjustment_action"] = risk_gate.get("adjustment_action", "none")
    adaptive_adjustment["workflow_status"] = risk_gate.get("product_status", "generated")
    reason_codes = [reason["code"] for reason in reasons]
    plan_diff = _build_feedback_plan_diff(
        risk_gate=risk_gate,
        protocol_recheck=protocol_recheck,
        adaptive_adjustment=adaptive_adjustment,
        reason_codes=reason_codes,
    )
    return {
        "workout_feedback": workout_feedback,
        "risk_gate": risk_gate,
        "protocol_recheck": protocol_recheck,
        "adaptive_feedback": {
            "workout_feedback": workout_feedback,
            "reason_codes": reason_codes,
            "reasons": reasons,
            "raw_text": request.raw_text,
            "source": "astro_feedback_form",
            "workflow": ["risk_gate", "protocol_recheck", "adjustment"],
        },
        "adaptive_adjustment": adaptive_adjustment,
        "plan_diff": plan_diff,
        "generation_status": risk_gate.get("product_status", "generated"),
    }


@app.get("/plans/{plan_id}")
async def get_plan(plan_id: str, user_id: str = DEFAULT_API_USER_ID):
    """返回单个已保存训练计划及其日历事件。"""
    _require_default_user(user_id)
    plan = get_db().get_plan(plan_id)
    if not plan or plan.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="训练计划不存在。")
    return {
        "plan": plan,
        "structured_training_plan": _load_structured_plan(plan),
        "events": [_event_with_content_trace(event) for event in get_db().list_events(plan_id)],
    }


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
async def execute_query(request: QueryRequest):
    """查询接口。Astro 计划生成默认可走 skeleton-first，避免前端长时间空等。"""
    _require_default_user(request.user_id)

    profile = load_user_profile()
    response_mode = str(request.response_mode or "full").strip().lower()
    plan_query = _is_plan_query(request.query)

    if plan_query and response_mode in {"skeleton", "skeleton_first"}:
        return await _build_skeleton_plan_response(
            request,
            profile,
            generation_status="skeleton_ready",
            message="已先返回确定性结构化计划骨架，避免模型长时间生成导致前端卡住。",
        )

    ensure_knowledge_base_ready()
    initial_state: IntegratedState = build_working_state(query=request.query, user_profile=profile)
    config = _build_llm_config(request)

    try:
        result = await asyncio.wait_for(
            integrated_app.ainvoke(initial_state, config=config),
            timeout=float(request.timeout_sec),
        )
        return _query_response_from_state(
            result,
            request,
            generation_status="complete",
            message="完整工作流已返回。",
        )
    except asyncio.TimeoutError:
        if plan_query:
            return await _build_skeleton_plan_response(
                request,
                profile,
                generation_status="llm_timeout_skeleton",
                message=f"完整 LLM 工作流超过 {request.timeout_sec} 秒，已回退到结构化规则骨架。",
            )
        raise HTTPException(status_code=504, detail=f"完整 LLM 工作流超过 {request.timeout_sec} 秒。")
    except Exception as e:
        if plan_query:
            return await _build_skeleton_plan_response(
                request,
                profile,
                generation_status="llm_error_skeleton",
                message=f"完整 LLM 工作流异常，已回退到结构化规则骨架：{str(e)}",
            )
        raise HTTPException(status_code=500, detail=str(e))


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
        "descriptions": {
            "action_library": "课表数据来自动作库直接证据，训练方案经过验证。",
            "protocol_rule": "课表由 HMP 基石协议确定性排课，动作库注册表提供执行细节和替代方案。",
            "kb_fallback": "动作库中未找到该训练类型的直接证据，已基于其他知识库内容生成参考课表。",
            "needs_evidence": "当前训练类型缺少可绑定动作库证据，暂不向用户展示模板化主课。",
            "plan_only": "当前训练类型在知识库中暂无充分证据支撑，基于训练计划骨架生成。",
        },
    }


@app.post("/training-calendar", response_model=TrainingCalendarResponse)
async def get_training_calendar(request: QueryRequest):
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

        return TrainingCalendarResponse(
            year=calendar.year,
            month=calendar.month,
            start_week_index=calendar.start_week_index,
            end_week_index=calendar.end_week_index,
            total_days=calendar.total_days,
            days=[d.to_dict() for d in calendar.days],
            phases=calendar.phases,
            evidence_summary=calendar.evidence_summary,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
