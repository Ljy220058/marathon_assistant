"""Feedback router — `/feedback` and feedback action endpoints."""

import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request

from marathon_qa_assistant.apps.async_db import run_db
from marathon_qa_assistant.apps.response_projection import _project_feedback_response_for_role
from marathon_qa_assistant.apps.schemas import (
    FeedbackActionRequest,
    FeedbackActionResponse,
    FeedbackRequest,
    FeedbackResponse,
)
from marathon_qa_assistant.apps.routers._shared import (
    _affected_events_after_feedback,
    _build_adjustment_history,
    _build_feedback_plan_diff,
    _build_feedback_replan,
    _event_with_content_trace,
    _feedback_summary_to_adaptive_adjustment,
    _find_applied_feedback_replan,
    _medical_referral_adjustment,
    _normalize_frontend_feedback,
    _parse_schedule_constraints,
    _plan_diff_from_affected_events,
    _resolve_user_id,
)
from marathon_qa_assistant.apps.security.response_role import _response_role
from marathon_qa_assistant.core.state_models import (
    build_adaptive_adjustment_contract,
    build_feedback_protocol_recheck,
    build_feedback_risk_gate,
    build_workflow_trace,
    derive_adaptive_reasons,
    normalize_workout_feedback,
)
from marathon_qa_assistant.core.observability import (
    record_feedback_risk,
    record_generation_status,
)
from marathon_qa_assistant.services.database import get_db


router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest, http_request: Request):
    """根据训练反馈返回自适应调整建议，供 Astro 反馈面板使用。"""
    uid = _resolve_user_id(http_request)
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
    affected_events: List[Dict[str, Any]] = []
    feedback_replan: Dict[str, Any] = {}
    if bool(request.plan_id) != bool(request.event_id):
        raise HTTPException(status_code=400, detail="保存训练反馈需要同时提供 plan_id 和 event_id。")
    if request.plan_id and request.event_id:
        if not await run_db(get_db().get_event, request.plan_id, request.event_id, uid):
            raise HTTPException(status_code=404, detail="训练日历事件不存在，反馈未保存。")
        feedback_id = await run_db(
            get_db().save_training_event_feedback,
            plan_id=request.plan_id,
            event_id=request.event_id,
            user_id=uid,
            workout_feedback=workout_feedback,
            reason_codes=reason_codes,
            adaptive_adjustment=adaptive_adjustment,
            risk_gate=risk_gate,
            protocol_recheck=protocol_recheck,
            raw_text=request.raw_text,
        )
        if feedback_id:
            try:
                from marathon_qa_assistant.services.memory_pipeline import write_feedback_memories
                await run_db(
                    write_feedback_memories, uid, workout_feedback,
                    raw_text=request.raw_text or "", reason_codes=reason_codes,
                )
            except Exception:
                pass
            affected_events = await run_db(
                get_db().apply_feedback_effect_to_future_events,
                plan_id=request.plan_id,
                event_id=request.event_id,
                user_id=uid,
                feedback_id=feedback_id,
                reason_codes=reason_codes,
                adaptive_adjustment=adaptive_adjustment,
                risk_gate=risk_gate,
            )
            blocked = str(risk_gate.get("product_status") or "") == "medical_referral" or protocol_recheck.get("allowed") is False
            feedback_replan = _build_feedback_replan(
                plan_id=request.plan_id,
                event_id=request.event_id,
                feedback_id=feedback_id,
                events=await run_db(get_db().list_events, request.plan_id),
                workout_feedback=workout_feedback,
                risk_gate=risk_gate,
                protocol_recheck=protocol_recheck,
                adaptive_adjustment=adaptive_adjustment,
                schedule_constraints=_parse_schedule_constraints(
                    request.raw_text,
                    request.feedback or {},
                    request.schedule_constraints,
                ),
            )
            if feedback_replan.get("patches"):
                await run_db(
                    get_db().save_feedback_replan,
                    plan_id=request.plan_id,
                    feedback_id=feedback_id,
                    user_id=uid,
                    feedback_replan=feedback_replan,
                    apply_patch=False,
                    exception_type="feedback_replan_suggested",
                )
            plan_diff = _plan_diff_from_affected_events(
                plan_diff,
                affected_events,
                blocked=blocked,
                needs_adjustment=bool(adaptive_adjustment.get("adjustment_required") or reason_codes or blocked),
            )
            if feedback_replan.get("status") == "blocked_medical" and not affected_events:
                plan_diff["affected_days"] = max(int(plan_diff.get("affected_days") or 0), 1)
                plan_diff["cancelled"] = max(int(plan_diff.get("cancelled") or 0), 1)
                plan_diff["status"] = "medical_referral"
    # Fix #4: 当用户标记"未完成"时，生成调整建议（不自动应用）
    adjustment_proposals = []
    if workout_feedback.get("completion_status") == "missed":
        try:
            from marathon_qa_assistant.core.session_adjuster import propose_adjustments
            missed_day = {
                "training_type": str(workout_feedback.get("training_type") or ""),
                "zone_range": str(workout_feedback.get("zone_range") or ""),
                "day": str(workout_feedback.get("day") or ""),
                "stimulus_type": str(workout_feedback.get("stimulus_type") or ""),
            }
            # C1: 从 DB 查询当前周完整训练上下文，用于智能重排建议
            current_week_context = []
            if request.plan_id:
                try:
                    all_events = await run_db(get_db().list_events, request.plan_id)
                    # 找到被跳过训练的所在周
                    missed_event = next(
                        (e for e in all_events if str(e.get("id") or e.get("event_id")) == str(request.event_id)),
                        None,
                    )
                    if missed_event:
                        missed_week = missed_event.get("week_number") or missed_event.get("week")
                        if missed_week is not None:
                            current_week_context = [
                                e for e in all_events
                                if (e.get("week_number") or e.get("week")) == missed_week
                            ]
                except Exception:
                    pass  # DB 查询降级: 保持空列表，调整器仍可给出基础建议
            adjustment_proposals = [
                {"action": p.action, "target_day": p.target_day, "new_type": p.new_type,
                 "reason": p.reason, "source": p.source_citation,
                 "requires_confirmation": p.requires_confirmation}
                for p in propose_adjustments(missed_day, current_week_context, {})
            ]
        except Exception:
            pass  # 调整器不可用时静默降级

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
        "affected_events": affected_events,
        "feedback_id": feedback_id,
        "feedback_replan": feedback_replan,
        "adjustment_proposals": adjustment_proposals,
        "workflow_trace": workflow_trace,
    }
    return _project_feedback_response_for_role(response_payload, _response_role(http_request))


@router.post("/plans/{plan_id}/feedback/{feedback_id}/actions", response_model=FeedbackActionResponse)
async def apply_feedback_action(plan_id: str, feedback_id: str, request: FeedbackActionRequest, http_request: Request):
    """处理跑者对局部重规划的确认、重排、恢复复核和暂不采用动作。"""
    user_id = _resolve_user_id(http_request)
    plan = await run_db(get_db().get_plan, plan_id)
    if not plan or plan.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="训练计划不存在。")
    feedback_items = await run_db(get_db().list_plan_feedback, plan_id)
    feedback = next((item for item in feedback_items if str(item.get("id")) == str(feedback_id)), None)
    if not feedback:
        raise HTTPException(status_code=404, detail="训练反馈不存在。")

    events = await run_db(get_db().list_events, plan_id)
    existing_applied_replan = _find_applied_feedback_replan(events, feedback_id)
    risk_gate = feedback.get("risk_gate") or {}
    protocol_recheck = feedback.get("protocol_recheck") or {}
    adaptive_adjustment = _feedback_summary_to_adaptive_adjustment(feedback)
    schedule_constraints = _parse_schedule_constraints(
        str(feedback.get("raw_text") or ""),
        {"schedule_constraints": request.schedule_constraints},
        request.schedule_constraints,
    )
    action = str(request.action or "").strip().lower()
    if action not in {"accept", "replan", "recover", "update_availability", "dismiss"}:
        raise HTTPException(status_code=400, detail="不支持的反馈重规划动作。")

    replan = _build_feedback_replan(
        plan_id=plan_id,
        event_id=str(feedback.get("event_id") or ""),
        feedback_id=feedback_id,
        events=events,
        workout_feedback=feedback,
        risk_gate=risk_gate,
        protocol_recheck=protocol_recheck,
        adaptive_adjustment=adaptive_adjustment,
        schedule_constraints=schedule_constraints,
        status="suggested",
    )
    if existing_applied_replan and action in {"replan", "update_availability"}:
        from marathon_qa_assistant.apps.routers._shared import _replan_no_safe_slot
        replan["previous_replan_id"] = existing_applied_replan.get("replan_id", "")
        if replan.get("status") == "suggested" and len(replan.get("patches") or []) <= len(existing_applied_replan.get("patches") or []):
            replan = _replan_no_safe_slot(
                feedback_id=feedback_id,
                schedule_constraints=schedule_constraints,
                previous_replan_id=str(existing_applied_replan.get("replan_id") or ""),
            )
    affected_events: List[Dict[str, Any]] = []
    if action == "accept":
        if replan.get("status") not in {"blocked_medical", "needs_manual_choice"}:
            replan["status"] = "applied"
            replan["user_action"] = "accept"
            affected_events = await run_db(
                get_db().save_feedback_replan,
                plan_id=plan_id,
                feedback_id=feedback_id,
                user_id=user_id,
                feedback_replan=replan,
                apply_patch=True,
                exception_type="feedback_replan_applied",
            )
    elif action in {"replan", "update_availability"}:
        if replan.get("patches"):
            affected_events = await run_db(
                get_db().save_feedback_replan,
                plan_id=plan_id,
                feedback_id=feedback_id,
                user_id=user_id,
                feedback_replan=replan,
                apply_patch=False,
                exception_type="feedback_replan_suggested",
            )
    elif action == "recover":
        if replan.get("status") == "blocked_medical":
            replan["audit"]["blocked_reason"] = "需要专业医疗评估通过后，才能恢复跑步主课。"
    elif action == "dismiss":
        replan["status"] = "dismissed"
        replan["user_action"] = "dismiss"

    plan_diff_result = {
        "status": replan.get("status"),
        "affected_days": len(replan.get("patches") or []),
        "downgraded": len(replan.get("patches") or []) if replan.get("status") != "blocked_medical" else 0,
        "cancelled": 1 if replan.get("status") == "blocked_medical" else 0,
    }
    return {"feedback_replan": replan, "affected_events": affected_events, "plan_diff": plan_diff_result}
