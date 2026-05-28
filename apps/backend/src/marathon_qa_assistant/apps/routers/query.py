"""Query router — `/query` endpoint for training plan generation."""

import asyncio
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from marathon_qa_assistant.apps.schemas import QueryRequest, QueryResponse
from marathon_qa_assistant.apps.response_builders import (
    _build_llm_config,
    _build_skeleton_plan_response,
    _query_response_from_state,
    _safe_workflow_error_summary,
)
from marathon_qa_assistant.apps.routers._shared import (
    _has_plan_generation_profile,
    _is_plan_query,
    _project_query_response_for_role,
    _resolve_user_id,
    _response_role,
)
from marathon_qa_assistant.core.workflow import integrated_app, IntegratedState
from marathon_qa_assistant.core.profile_store import load_user_profile
from marathon_qa_assistant.core.working_state import build_working_state
from marathon_qa_assistant.core.training_plan_context import merge_plan_profile_overrides
from marathon_qa_assistant.core.kb_bootstrap import ensure_knowledge_base_ready


router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest, http_request: Request):
    """查询接口。Astro 计划生成默认可走 skeleton-first，避免前端长时间空等。"""
    user_id = _resolve_user_id(http_request)

    profile = merge_plan_profile_overrides(request.query, load_user_profile(user_id))
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
                user_id=user_id,
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
                user_id=user_id,
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
                    user_id=user_id,
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
                    user_id=user_id,
                ),
                _response_role(http_request),
            )
        raise HTTPException(status_code=500, detail=_safe_workflow_error_summary(e))
