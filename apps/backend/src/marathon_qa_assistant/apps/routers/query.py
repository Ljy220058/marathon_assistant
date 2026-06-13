"""Query router — `/query` endpoint for training plan generation."""

import asyncio
import time
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from marathon_qa_assistant.apps.schemas import QueryRequest, QueryResponse
from marathon_qa_assistant.apps.response_builders import (
    _build_llm_config,
    _build_fast_qa_response,
    _build_skeleton_plan_response,
    _query_response_from_state,
    _safe_workflow_error_summary,
)
from marathon_qa_assistant.apps.response_projection import _project_query_response_for_role
from marathon_qa_assistant.apps.routers._shared import _resolve_user_id
from marathon_qa_assistant.apps.security.response_role import _response_role
from marathon_qa_assistant.core.workflow import integrated_app, IntegratedState
from marathon_qa_assistant.core.profile_store import load_user_profile
from marathon_qa_assistant.core.working_state import build_working_state
from marathon_qa_assistant.core.training_plan_context import merge_plan_profile_overrides
from marathon_qa_assistant.services.plan_query_classifier import (
    is_plan_query,
)
router = APIRouter()

# Idempotency cache: (user_id, idempotency_key) → (timestamp, response_dict)
# TTL: 300s. Pruned on access to bound memory.
_IDEMPOTENCY_CACHE: Dict[Tuple[str, str], Tuple[float, Dict[str, Any]]] = {}
_IDEMPOTENCY_TTL_SEC = 300


def _prune_idempotency_cache(now: float) -> None:
    stale = [
        key for key, (ts, _) in _IDEMPOTENCY_CACHE.items()
        if now - ts > _IDEMPOTENCY_TTL_SEC
    ]
    for key in stale:
        _IDEMPOTENCY_CACHE.pop(key, None)


def _normalize_resume_pause(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    status = str(payload.get("status") or "").strip().lower()
    if status != "awaiting_user_input":
        return {}
    return payload


def _resolve_effective_query(request: QueryRequest) -> str:
    pause = _normalize_resume_pause(request.resume_from_workflow_pause)
    pending_query = str(pause.get("pending_query") or "").strip()
    if pending_query:
        return pending_query
    return str(request.query or "")


@router.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest, http_request: Request):
    """查询接口。默认走完整工作流，显式 skeleton / qa_fast 仅作兼容入口。"""
    user_id = _resolve_user_id(http_request)
    effective_query = _resolve_effective_query(request)
    resume_pause = _normalize_resume_pause(request.resume_from_workflow_pause)
    effective_request = request.model_copy(update={"query": effective_query})

    # Idempotency: 如果客户端提供了 Idempotency-Key，检查是否已处理过
    idempotency_key = http_request.headers.get("Idempotency-Key", "").strip()
    if idempotency_key:
        _prune_idempotency_cache(time.monotonic())
        cache_key = (user_id, idempotency_key)
        cached = _IDEMPOTENCY_CACHE.get(cache_key)
        if cached is not None:
            return JSONResponse(content=cached[1])

    # Idempotency: 成功后缓存响应，防止重复执行副作用操作
    async def _cache_response(response: Any) -> Any:
        if not idempotency_key:
            return response
        try:
            if hasattr(response, "model_dump"):
                payload = response.model_dump()
            elif hasattr(response, "body"):
                import json as _json
                payload = _json.loads(response.body)
            else:
                return response
            _IDEMPOTENCY_CACHE[(user_id, idempotency_key)] = (time.monotonic(), payload)
        except Exception:
            pass  # 缓存失败不影响主流程
        return response

    profile = load_user_profile(user_id)
    profile = merge_plan_profile_overrides(effective_query, profile)
    if resume_pause:
        supplement_query = str(request.query or "").strip()
        if supplement_query and supplement_query != effective_query:
            profile = merge_plan_profile_overrides(supplement_query, profile)
    response_mode = str(request.response_mode or "full").strip().lower()
    skeleton_requested = response_mode in {"skeleton", "skeleton_first"}
    fast_qa_requested = response_mode in {"qa_fast", "quick_qa"}
    plan_query = is_plan_query(effective_query)

    if plan_query and skeleton_requested:
        return _project_query_response_for_role(
            await _build_skeleton_plan_response(
                effective_request,
                profile,
                generation_status="skeleton_ready",
                message="已先返回确定性结构化计划骨架，避免模型长时间生成导致前端卡住。",
                user_id=user_id,
            ),
            _response_role(http_request),
        )

    if fast_qa_requested and not plan_query:
        fast_response = await _build_fast_qa_response(effective_request, profile, user_id=user_id)
        if fast_response is not None:
            return _project_query_response_for_role(fast_response, _response_role(http_request))

    # P1-1: 将 API mode 参数传入 build_working_state，避免被硬编码 "team" 覆盖
    initial_state: IntegratedState = build_working_state(query=effective_query, mode=request.mode, user_profile=profile)
    config = _build_llm_config(request)

    try:
        result = await asyncio.wait_for(
            integrated_app.ainvoke(initial_state, config=config),
            timeout=float(request.timeout_sec),
        )
        workflow_error = result.get("workflow_error") if isinstance(result.get("workflow_error"), dict) else {}
        if workflow_error:
            request_id = getattr(http_request.state, "request_id", "") or http_request.headers.get("X-Request-ID") or ""
            error_code = str(workflow_error.get("error_code") or "WORKFLOW_ERROR")
            status_code = 422 if error_code == "HARD_RULE_VIOLATION" else 500
            return JSONResponse(
                status_code=status_code,
                content={
                    "error_code": error_code,
                    "request_id": request_id,
                    "message": str(workflow_error.get("message") or _safe_workflow_error_summary(Exception(error_code))),
                    "workflow_error": workflow_error,
                },
            )
        workflow_pause = result.get("workflow_pause") if isinstance(result.get("workflow_pause"), dict) else {}
        generation_status = "workflow_pause" if workflow_pause.get("status") == "awaiting_user_input" else (
            "security_intercepted" if str(result.get("mode") or "").strip().lower() == "intercepted" else "complete"
        )
        message = "需要补齐信息，工作流已暂停。" if generation_status == "workflow_pause" else (
            "请求已被安全护栏拦截，工作流已终止。" if generation_status == "security_intercepted" else "完整工作流已返回。"
        )
        response = _project_query_response_for_role(
            _query_response_from_state(
                result,
                effective_request,
                generation_status=generation_status,
                message=message,
                user_id=user_id,
            ),
            _response_role(http_request),
        )
        return await _cache_response(response)
    except asyncio.TimeoutError:
        if plan_query:
            return _project_query_response_for_role(
                await _build_skeleton_plan_response(
                    effective_request,
                    profile,
                    generation_status="llm_timeout_skeleton",
                    message=f"完整 LLM 工作流超过 {request.timeout_sec} 秒，已回退到结构化规则骨架。",
                    user_id=user_id,
                ),
                _response_role(http_request),
            )
        # P1-2: 非计划查询超时时返回有意义错误，不再抛 504
        raise HTTPException(status_code=504, detail=f"完整 LLM 工作流超过 {request.timeout_sec} 秒。")
    except Exception as e:
        # P1-2: 统一异常处理 — 仅保留超时骨架回退，其他异常返回 5xx
        request_id = getattr(http_request.state, "request_id", "") or http_request.headers.get("X-Request-ID") or ""
        return JSONResponse(
            status_code=503,
            content={
                "error_code": "QUERY_EXECUTION_FAILED",
                "request_id": request_id,
                "message": _safe_workflow_error_summary(e),
            },
        )
