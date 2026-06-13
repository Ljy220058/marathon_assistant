"""Plans router — training plan CRUD, calendar, and day detail endpoints."""

import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request

from marathon_qa_assistant.apps.async_db import run_db
from marathon_qa_assistant.apps.schemas import (
    DayDetailResponse,
    EventScheduleRequest,
    PlanDetailResponse,
    QueryRequest,
    RollbackPlanRequest,
    SavePlanRequest,
    TrainingCalendarResponse,
)
from marathon_qa_assistant.apps.response_builders import (
    _build_llm_config,
    _build_response_evidence_chain,
    _public_rag_health,
    _safe_workflow_error_summary,
)
from marathon_qa_assistant.apps.response_projection import (
    _project_plan_detail_response_for_role,
    _project_training_calendar_response_for_role,
)
from marathon_qa_assistant.apps.routers._shared import (
    _auth_enabled,
    _build_adjustment_history,
    _event_with_latest_feedback,
    _load_structured_plan,
    _request_api_token,
    _require_default_user,
    _resolve_user_id,
    DEFAULT_API_USER_ID,
)
from marathon_qa_assistant.apps.security.response_role import _response_role
from marathon_qa_assistant.core.state_models import build_execution_status_summary
from marathon_qa_assistant.core.profile_store import load_user_profile
from marathon_qa_assistant.core.working_state import build_working_state
from marathon_qa_assistant.core.workflow import integrated_app, IntegratedState
from marathon_qa_assistant.services.daily_schedule_generator import generate_daily_schedule
from marathon_qa_assistant.services.database import get_db
from marathon_qa_assistant.services.training_plan_review import build_training_plan_review
from marathon_qa_assistant.services.workout_template_retriever import EVIDENCE_TIER_LABELS


router = APIRouter()


@router.get("/plans")
async def list_plans(http_request: Request, user_id: str = DEFAULT_API_USER_ID):
    """列出本地已保存训练计划。空列表表示暂无历史，不应返回 404。"""
    uid = _resolve_user_id(http_request) if _auth_enabled() else user_id
    return {"plans": await run_db(get_db().list_training_plans, user_id=uid)}


@router.post("/plans")
async def save_plan(request: SavePlanRequest, http_request: Request):
    """保存前端当前结构化训练计划，并同步生成本地日历事件。"""
    uid = _resolve_user_id(http_request)
    if not request.structured_training_plan:
        raise HTTPException(status_code=400, detail="structured_training_plan 不能为空。")
    calendar_settings = request.calendar_settings or {}
    plan_id = await run_db(
        get_db().save_training_plan,
        request.structured_training_plan,
        source_query=request.source_query,
        user_id=uid,
        calendar_days=request.calendar_days,
        training_start_date=str(calendar_settings.get("training_start_date") or ""),
        default_start_time=str(calendar_settings.get("default_start_time") or "07:00"),
        lineage_id=request.lineage_id,
        parent_plan_id=request.parent_plan_id,
        trigger=request.trigger,
        trigger_detail=request.trigger_detail,
    )
    return {"plan_id": plan_id, "saved": True}


@router.get("/plans/{plan_id}", response_model=PlanDetailResponse)
async def get_plan(plan_id: str, http_request: Request, user_id: str = DEFAULT_API_USER_ID):
    """返回单个已保存训练计划及其日历事件。"""
    uid = _resolve_user_id(http_request) if _auth_enabled() else (_resolve_user_id(http_request) if _request_api_token(http_request) else user_id)
    _require_default_user(uid)
    plan = await run_db(get_db().get_plan, plan_id)
    if not plan or plan.get("user_id") != uid:
        raise HTTPException(status_code=404, detail="训练计划不存在。")
    structured_plan = _load_structured_plan(plan)
    raw_events = await run_db(get_db().list_events, plan_id)
    events = [_event_with_latest_feedback(event) for event in raw_events]
    calendar_day_contract = events
    training_plan_review_result = (
        build_training_plan_review(
            structured_training_plan=structured_plan,
            daily_schedule_cards=calendar_day_contract,
            rag_health=_public_rag_health(),
        )
        if isinstance(structured_plan, dict)
        else {}
    )
    response_payload = {
        "plan": plan,
        "structured_training_plan": structured_plan,
        "workflow_trace": {},
        "events": events,
        "versions": await run_db(get_db().list_plan_versions, plan_id),
        "execution_status_summary": build_execution_status_summary(
            events,
            plan={**plan, **(structured_plan.get("plan_meta") or {})},
        ),
        "adjustment_history": _build_adjustment_history(plan_id, events),
        "training_plan_review": training_plan_review_result,
        "evidence_chain": _build_response_evidence_chain(
            query=str(plan.get("source_query") or ""),
            evidence_bundle=(structured_plan.get("evidence_bundle") if isinstance(structured_plan, dict) else None),
            answer_source_mode="structured_plan_rule" if isinstance(structured_plan, dict) else "",
        ),
    }
    return _project_plan_detail_response_for_role(response_payload, _response_role(http_request))


@router.post("/plans/{plan_id}/rollback")
async def rollback_plan(
    plan_id: str,
    request: RollbackPlanRequest,
    http_request: Request,
    user_id: str = DEFAULT_API_USER_ID,
):
    """回退到同一版本链中的指定历史版本，并创建一条新的 rollback 计划记录。"""
    uid = _resolve_user_id(http_request) if _auth_enabled() else (_resolve_user_id(http_request) if _request_api_token(http_request) else user_id)
    _require_default_user(uid)
    plan = await run_db(get_db().get_plan, plan_id)
    if not plan or plan.get("user_id") != uid:
        raise HTTPException(status_code=404, detail="训练计划不存在。")
    try:
        rollback_plan_id = await run_db(
            get_db().rollback_training_plan,
            plan_id,
            request.to_version,
            user_id=uid,
            trigger_detail=request.trigger_detail,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"plan_id": rollback_plan_id, "rolled_back": True, "to_version": request.to_version}


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: str, http_request: Request, user_id: str = DEFAULT_API_USER_ID):
    """删除已保存的训练计划及其日历事件。"""
    uid = _resolve_user_id(http_request) if _auth_enabled() else user_id
    plan = await run_db(get_db().get_plan, plan_id)
    if not plan or plan.get("user_id") != uid:
        raise HTTPException(status_code=404, detail="训练计划不存在。")
    if not await run_db(get_db().delete_training_plan, plan_id):
        raise HTTPException(status_code=404, detail="训练计划不存在。")
    return {"deleted": True, "plan_id": plan_id}


@router.patch("/plans/{plan_id}/events/{event_id}")
async def update_plan_event_schedule(
    plan_id: str,
    event_id: str,
    request: EventScheduleRequest,
    http_request: Request,
    user_id: str = DEFAULT_API_USER_ID,
):
    """更新已保存训练日历事件的日期、开始时间和时长。"""
    uid = _resolve_user_id(http_request) if _auth_enabled() else (_resolve_user_id(http_request) if _request_api_token(http_request) else user_id)
    _require_default_user(uid)
    plan = await run_db(get_db().get_plan, plan_id)
    if not plan or plan.get("user_id") != uid:
        raise HTTPException(status_code=404, detail="训练计划不存在。")
    events = await run_db(get_db().list_events, plan_id)
    if not any(event.get("id") == event_id for event in events):
        raise HTTPException(status_code=404, detail="训练日历事件不存在。")
    updated = await run_db(
        get_db().update_event_schedule,
        event_id,
        scheduled_date=request.scheduled_date,
        start_time=request.start_time,
        duration_min=request.duration_min,
    )
    return {"updated": updated}


@router.post("/training-calendar", response_model=TrainingCalendarResponse)
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
        training_plan_review_result = build_training_plan_review(
            structured_training_plan=structured_training_plan,
            daily_schedule_cards=daily_schedule_cards,
            training_load_summary=calendar.training_load_summary,
            rag_health=_public_rag_health(),
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
            training_plan_review=training_plan_review_result,
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


@router.get("/training-calendar/day-detail/{day_index}", response_model=DayDetailResponse)
async def get_day_detail(day_index: int):
    """返回训练日历中某一天的详情（从会话提取或历史缓存的日历数据）"""
    return DayDetailResponse(
        day={"day_index": day_index, "note": "请通过 /training-calendar 接口获取完整日历后在客户端侧查找。"},
        evidence_tier_labels=EVIDENCE_TIER_LABELS,
    )
