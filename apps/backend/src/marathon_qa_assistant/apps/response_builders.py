"""Response builder helpers for the Marathon QA Assistant API.

These functions assemble QueryResponse, TrainingCalendarResponse, and related
payloads from workflow results, structured plans, and feedback state.  They are
extracted from api_app.py so that the API layer stays focused on HTTP routing.
"""

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from marathon_qa_assistant.core.profile_context import profile_context_metadata
from marathon_qa_assistant.core.settings import get_settings
from marathon_qa_assistant.core.state_models import build_feedback_risk_gate
from marathon_qa_assistant.core.workflow import IntegratedState
from marathon_qa_assistant.core.working_state import build_working_state
from marathon_qa_assistant.core.evidence_bundle import build_evidence_bundle
from marathon_qa_assistant.core.state_models import build_workflow_trace
from marathon_qa_assistant.core.observability import (
    record_generation_status,
    record_plan_persist_status,
)
from marathon_qa_assistant.core.kb_bootstrap import get_knowledge_base_health_snapshot
from marathon_qa_assistant.core.app_state import DATA_DIR
from marathon_qa_assistant.services.daily_schedule_generator import generate_daily_schedule
from marathon_qa_assistant.services.database import get_db
from marathon_qa_assistant.services.kb.evidence_chain import build_evidence_chain_payload
from marathon_qa_assistant.services.knowledge_graph import graph_runtime_health
from marathon_qa_assistant.services.training_plan_review import build_training_plan_review

from marathon_qa_assistant.apps.schemas import QueryRequest, QueryResponse
from marathon_qa_assistant.nodes.expert_nodes import QA_REPORT_REQUIRED_SECTIONS


# -------- shared utility helpers ---------------------------------------------

DEFAULT_API_USER_ID = "default_user"


def _normalize_provider(provider: str) -> str:
    normalized = str(provider or "ds").strip().lower()
    if normalized in {"ds", "deepseek"}:
        return "ds"
    if normalized in {"openai", "gpt"}:
        return "openai"
    return "ollama"


def _selected_model(request: QueryRequest) -> str:
    settings = get_settings()
    provider = _normalize_provider(request.llm_provider)
    if request.llm_model:
        return request.llm_model.strip()
    if provider == "ds":
        return settings.deepseek_model
    if provider == "openai":
        return settings.openai_model
    return settings.ollama_model


def _save_plan_if_ready(
    structured_plan: Optional[Dict[str, Any]],
    request: QueryRequest,
    calendar_days: Optional[List[Dict[str, Any]]] = None,
    user_id: str = DEFAULT_API_USER_ID,
) -> Tuple[Optional[str], str]:
    if not isinstance(structured_plan, dict) or not structured_plan.get("week_plans"):
        return None, "skipped"
    try:
        return (
            get_db().save_training_plan(
                structured_plan,
                source_query=request.query,
                user_id=user_id,
                calendar_days=calendar_days,
            ),
            "saved",
        )
    except Exception:
        return None, "failed"


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
            "llm_timeout_sec": request.timeout_sec,
        }
    }


async def _build_fast_qa_response(
    request: QueryRequest,
    profile: Dict[str, Any],
    *,
    user_id: str = DEFAULT_API_USER_ID,
) -> Optional[QueryResponse]:
    started = time.perf_counter()
    state: IntegratedState = build_working_state(query=request.query, mode=request.mode, user_profile=profile)
    config = _build_llm_config(request)

    from marathon_qa_assistant.nodes.common import output_guard_obj
    from marathon_qa_assistant.nodes.expert_nodes import (
        coach_node,
        nutritionist_node,
        research_analyst_node,
    )
    from marathon_qa_assistant.nodes.profile_and_retrieval import entity_extraction_node
    from marathon_qa_assistant.nodes.router import router_node

    state.update(await router_node(state, config))
    workflow_kind = str(state.get("workflow_kind") or "qa")
    category = str(state.get("category") or "coach")
    if workflow_kind not in {"qa", "research"} or category not in {"coach", "nutritionist", "research"}:
        return None

    state.update(await entity_extraction_node(state, config))
    if category == "nutritionist":
        expert_output = await nutritionist_node(state, config)
    elif category == "research":
        expert_output = await research_analyst_node(state, config)
    else:
        expert_output = await coach_node(state, config)
    state.update(expert_output)

    raw_report = str(state.get("draft_plan") or state.get("final_report") or "")
    _, cleaned_output, _ = output_guard_obj.check(raw_report)
    state["final_report"] = cleaned_output
    state["workflow_trace"] = build_workflow_trace(
        query=request.query,
        workflow_kind=workflow_kind,
        intent_type=str(state.get("intent_type") or "qa"),
        status="complete",
        evidence_bundle=state.get("evidence_bundle") if isinstance(state.get("evidence_bundle"), dict) else None,
        adaptive_feedback=state.get("adaptive_feedback") if isinstance(state.get("adaptive_feedback"), dict) else None,
        adaptive_adjustment=state.get("adaptive_adjustment") if isinstance(state.get("adaptive_adjustment"), dict) else None,
    )
    state["workflow_trace"].setdefault("performance", {})
    if isinstance(state["workflow_trace"]["performance"], dict):
        state["workflow_trace"]["performance"].update(
            {
                "path": "qa_fast",
                "total_sec": round(time.perf_counter() - started, 3),
            }
        )
    response = _query_response_from_state(
        state,
        request,
        generation_status="complete",
        message="快速问答路径已返回。",
        user_id=user_id,
    )
    response.generation_timings = {
        **dict(response.generation_timings or {}),
        "qa_fast_sec": round(time.perf_counter() - started, 3),
        "total_sec": round(time.perf_counter() - started, 3),
    }
    return response


# -------- report / skeleton helpers ------------------------------------------

def _section_body(report: str, section: str) -> str:
    pattern = rf"^##\s+{re.escape(section)}\s*$([\s\S]*?)(?=^##\s+|\Z)"
    match = re.search(pattern, str(report or ""), flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def _visible_evidence_lines_from_chain(evidence_chain: Any) -> List[str]:
    if not isinstance(evidence_chain, dict):
        return []
    lines: List[str] = []
    for index, item in enumerate(evidence_chain.get("items") or [], start=1):
        if not isinstance(item, dict):
            continue
        display_mode = str(item.get("display_mode") or "").strip()
        if display_mode == "model_general_knowledge" and not str(item.get("citation_label") or "").strip():
            continue
        label = str(item.get("citation_label") or f"[{index}]").strip()
        source = str(item.get("source_label") or item.get("source_file") or item.get("source") or "来源待补充").strip()
        locator = str(item.get("locator_hint") or item.get("page_hint") or "").strip()
        page = item.get("page")
        if not locator and page not in (None, "", 0):
            locator = f"p.{page}"
        snippet = str(item.get("text_span") or item.get("user_facing_summary") or "").replace("\n", " ").strip()
        boundary = str(item.get("display_mode") or "visible_context").strip()
        locator_text = f" {locator}" if locator else ""
        snippet_text = f"：{snippet[:220]}" if snippet else ""
        lines.append(f"- {label} {source}{locator_text} [{boundary}]{snippet_text}")
    return lines


def ensure_kb_visible_evidence_report_sections(report: str, evidence_chain: Any) -> str:
    """QA 兜底契约：即使模型漏写章节，也要把可见证据显式补进报告。"""
    raw_report = str(report or "").strip()
    evidence_lines = _visible_evidence_lines_from_chain(evidence_chain)
    if not evidence_lines:
        evidence_lines = ["本轮未检索到可展示的本地知识库证据。"]
    fallback_bodies = {
        "结论": raw_report or "本轮暂未生成明确结论。",
        "训练建议": "请先依据上方结论执行低风险、可回退的训练调整；涉及核心处方时必须优先核对本轮证据。",
        "专项不受影响的边界": "保持专项目标不受影响的前提是：不把图谱线索、旧库解释性来源或模型常识当作核心训练处方证据。",
        "知识库可见证据": "\n".join(evidence_lines) if evidence_lines else "本轮未检索到可展示的本地知识库证据。",
        "证据不足或待核验之处": "若上方证据显示为 graph_hint、legacy_explanation、model_general_knowledge、needs_evidence 或 rejected_source，请视为待核验背景，不能直接作为核心训练处方依据。",
    }
    sections = []
    for section in QA_REPORT_REQUIRED_SECTIONS:
        body = _section_body(raw_report, section) or fallback_bodies[section]
        if section == "知识库可见证据":
            # 证据章节必须以运行时 evidence_chain 为准，避免模型漏列或编造来源。
            body = fallback_bodies[section]
        sections.append(f"## {section}\n{body.strip()}")
    return "\n\n".join(sections)


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


def _has_calendar_source_plan(structured_plan: Any) -> bool:
    return isinstance(structured_plan, dict) and bool(structured_plan.get("week_plans"))


# -------- RAG health helpers -------------------------------------------------

def _v2_runtime_manifest_overlay(payload: Dict[str, Any]) -> Dict[str, Any]:
    schema_version = str(payload.get("index_schema_version") or payload.get("source") or "")
    source = str(payload.get("source") or "")
    if source != "v2" and schema_version != "chunk_schema_v2":
        return {}
    manifest_path = DATA_DIR / "knowledge" / "governance" / "runtime_index_v2_manifest.json"
    if not manifest_path.exists():
        return {"runtime_status": "runtime_manifest_missing"}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {"runtime_status": "runtime_manifest_unreadable"}
    can_replace_runtime = bool(manifest.get("can_replace_runtime"))
    runtime_core_enabled = bool(payload.get("runtime_core_prescription_enabled"))
    approved_records = int(manifest.get("approved_records") or 0)
    ready_records = int(manifest.get("ready_records") or 0)
    return {
        "runtime_status": str(manifest.get("status") or ""),
        "runtime_use_enabled": bool(manifest.get("runtime_use_enabled")),
        "can_replace_runtime": can_replace_runtime,
        "approved_records": approved_records,
        "ready_records": ready_records,
        "replacement_blockers": list(manifest.get("replacement_blockers") or []),
        "source_review_ready": approved_records > 0 and ready_records > 0,
        "commercial_core_prescription_enabled": runtime_core_enabled and can_replace_runtime,
    }


def _public_rag_health(health: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = dict(health or get_knowledge_base_health_snapshot() or {})
    public = {
        "source": str(payload.get("source") or "unknown"),
        "vector_dir": str(payload.get("vector_dir") or ""),
        "index_schema_version": str(payload.get("index_schema_version") or payload.get("source") or "unknown"),
        "metadata_completeness": float(payload.get("metadata_completeness") or 0.0),
        "runtime_core_prescription_enabled": bool(payload.get("runtime_core_prescription_enabled")),
        "chunks_count": int(payload.get("chunks_count") or 0),
        "faiss_ready": bool(payload.get("faiss_ready")),
        "ready": bool(payload.get("ready") or payload.get("ok")),
    }
    public.update(graph_runtime_health(public))
    public.update(_v2_runtime_manifest_overlay(public))
    if "commercial_core_prescription_enabled" not in public:
        public["commercial_core_prescription_enabled"] = bool(public["runtime_core_prescription_enabled"])
    return public


# -------- calendar / evidence assembly ---------------------------------------

def _calendar_contract_from_plan(
    structured_plan: Dict[str, Any],
    rag_health: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
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
            rag_health=rag_health,
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


def _answer_source_mode_from_review(current_mode: str, training_plan_review: Dict[str, Any]) -> str:
    mode = str(current_mode or "")
    if mode != "structured_plan_rule":
        return mode
    dimensions = training_plan_review.get("dimensions") if isinstance(training_plan_review, dict) else {}
    evidence_control = dimensions.get("evidence_control") if isinstance(dimensions, dict) else {}
    if not isinstance(evidence_control, dict):
        return mode
    needs_evidence_count = int(evidence_control.get("needs_evidence_count") or 0)
    core_violations = list(evidence_control.get("core_source_violations") or [])
    if needs_evidence_count > 0 or core_violations:
        return "needs_evidence"
    return mode


def _build_response_evidence_chain(
    *,
    query: str,
    evidence_bundle: Any = None,
    answer_source_mode: str = "",
    answer_text: str = "",
    rag_health: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return build_evidence_chain_payload(
        query=query,
        evidence_bundle=evidence_bundle if isinstance(evidence_bundle, dict) else None,
        answer_source_mode=answer_source_mode,
        answer_text=answer_text,
        health=rag_health or get_knowledge_base_health_snapshot(),
    )


def _attach_citation_gate_to_trace_and_review(
    *,
    workflow_trace: Dict[str, Any],
    training_plan_review: Dict[str, Any],
    evidence_chain: Dict[str, Any],
) -> None:
    gate = evidence_chain.get("citation_gate") if isinstance(evidence_chain.get("citation_gate"), dict) else {}
    summary = {
        "answer_source_mode": str(evidence_chain.get("answer_source_mode") or ""),
        "citation_gate_status": str(gate.get("status") or "passed"),
        "fake_citation_count": int(gate.get("fake_citation_count") or 0),
        "fake_citation_violations": list(gate.get("violations") or []),
    }
    evidence_state = workflow_trace.setdefault("evidence_state", {})
    if isinstance(evidence_state, dict):
        evidence_state.update(summary)

    if not isinstance(training_plan_review, dict):
        return
    dimensions = training_plan_review.setdefault("dimensions", {})
    if not isinstance(dimensions, dict):
        return
    evidence_control = dimensions.setdefault("evidence_control", {})
    if not isinstance(evidence_control, dict):
        return
    evidence_control.update(summary)
    evidence_control["citation_gate"] = gate
    if summary["fake_citation_count"] > 0:
        evidence_control["status"] = "attention"
        training_plan_review["status"] = "needs_attention"


def _build_ui_policy(render_mode: str = "qa_card") -> Dict[str, Any]:
    return {
        "version": "ui_policy.v1",
        "render_mode": render_mode,
        "must_not_truncate": [
            "answer_card.title",
            "answer_card.one_line",
            "answer_card.must_show",
            "answer_card.do_not_do",
        ],
        "default_collapsed": ["full_report.markdown", "evidence_chain"],
        "max_preview_chars": 1200,
        "evidence_display": "drawer",
    }


def _has_medical_referral_signal(request: QueryRequest, result: Dict[str, Any], generation_status: str) -> bool:
    if generation_status == "medical_referral":
        return True
    risk_gate = result.get("risk_gate") if isinstance(result.get("risk_gate"), dict) else {}
    if str(risk_gate.get("product_status") or "") == "medical_referral":
        return True
    return build_feedback_risk_gate({}, raw_text=str(request.query or "")).get("product_status") == "medical_referral"


def _infer_answer_card_intent(result: Dict[str, Any], request: QueryRequest, structured_plan: Any, generation_status: str) -> str:
    category = str(result.get("category") or "").strip().lower()
    query = str(request.query or "").lower()
    if isinstance(structured_plan, dict) and structured_plan.get("week_plans"):
        return "training_plan"
    if generation_status == "medical_referral" or category == "therapist" or any(term in query for term in ("疼", "痛", "伤", "膝", "胸痛", "头晕", "无法承重")):
        return "injury_safety"
    if category == "nutritionist" or any(term in query for term in ("营养", "补给", "碳水", "能量胶", "喝水", "电解质")):
        return "nutrition"
    return "general_qa"


def _build_answer_card(
    *,
    request: QueryRequest,
    result: Dict[str, Any],
    report: str,
    structured_plan: Any = None,
    generation_status: str = "complete",
    answer_source_mode: str = "",
    evidence_chain: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    intent = _infer_answer_card_intent(result, request, structured_plan, generation_status)
    first_line = next((line.strip("# *") for line in str(report or "").splitlines() if line.strip()), "本次回答已生成。")
    if intent == "training_plan":
        title = "训练日历已生成" if isinstance(structured_plan, dict) and structured_plan.get("week_plans") else "训练计划建议"
        must_show = [{"type": "decision", "label": "计划状态", "text": "已生成可查看的训练日历，请优先按周重点和单日卡片执行。"}]
        render_mode = "plan_calendar"
        severity = "info"
    elif intent == "injury_safety":
        medical_referral = _has_medical_referral_signal(request, result, generation_status)
        title = "立即停止训练并寻求医疗评估" if medical_referral else "先按安全分流处理"
        must_show = [
            {"type": "decision", "label": "今天是否继续训练", "text": "出现红旗症状时不要继续训练；如疼痛出现在跑步中或影响跑姿，今天不要继续强度训练。"},
            {"type": "safety_gate", "label": "必须停止/就医", "items": ["胸痛、胸闷、头晕、晕厥或呼吸困难", "无法承重或走路跛行", "红肿热烫、明显肿胀", "关节交锁、打软腿或夜间痛", "疼痛持续超过 3 天不缓解"]},
            {"type": "alternative", "label": "可替代训练", "items": ["红旗症状未排除前不安排替代训练", "完全无痛且无红旗症状时才选择低强度骑行、游泳或核心训练", "任何替代训练诱发同部位疼痛时立即停止"]},
        ]
        render_mode = "safety_card"
        severity = "medical_referral" if medical_referral else "stop_training"
    elif intent == "nutrition":
        title = "补给建议摘要"
        must_show = [
            {"type": "action", "label": "先遵守的原则", "items": ["比赛日不要首次尝试新食物或新能量胶", "碳水、饮水和电解质按训练中验证过的方案执行"]},
            {"type": "nutrition_timing", "label": "时间窗口", "text": "优先关注赛前 2–4 小时、赛前 15–30 分钟、赛中每 30–40 分钟和赛后 30 分钟。"},
        ]
        render_mode = "nutrition_card"
        severity = "info"
    else:
        title = first_line[:40] or "回答摘要"
        must_show = [{"type": "decision", "label": "核心结论", "text": first_line[:160]}]
        render_mode = "qa_card"
        severity = "info"
    profile_metadata = profile_context_metadata(result.get("user_profile", {}) if isinstance(result, dict) else {})
    if severity == "medical_referral":
        first_line = "出现红旗症状：立即停止训练，并尽快寻求专业医疗评估。"
    return {
        "version": "answer_card.v2",
        "intent": intent,
        "severity": severity,
        "title": title,
        "one_line": first_line[:220],
        "must_show": must_show,
        "next_steps": [],
        "do_not_do": ["立即停止训练，不要继续完成间歇、节奏跑或长距离；请优先按安全卡片处理。"] if severity == "medical_referral" else ["不要只根据被截断的长报告做决策；请优先查看本卡片的必看信息。"] if intent in {"injury_safety", "nutrition"} else [],
        "personalization": profile_metadata,
        "confidence": {
            "level": "medium" if answer_source_mode else "low",
            "reason": "置信度由回答来源模式和证据链共同决定；完整证据请查看证据抽屉。",
        },
        "ui_render_mode": render_mode,
    }



def _build_skeleton_state(request: QueryRequest, profile: Dict[str, Any]) -> IntegratedState:
    from marathon_qa_assistant.core.training_plan_skeleton import build_structured_training_plan_skeleton

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


# -------- *the* two main response builders ------------------------------------

async def _build_skeleton_plan_response(
    request: QueryRequest,
    profile: Dict[str, Any],
    *,
    generation_status: str,
    message: str,
    user_id: str = DEFAULT_API_USER_ID,
) -> QueryResponse:
    started = time.perf_counter()
    state = await asyncio.to_thread(_build_skeleton_state, request, profile)
    build_elapsed = time.perf_counter() - started
    structured_plan = state["structured_training_plan"]
    calendar_started = time.perf_counter()
    monthly_training_calendar = await asyncio.to_thread(
        generate_daily_schedule,
        structured_plan,
        enable_kb_fallback=False,
    )
    calendar_elapsed = time.perf_counter() - calendar_started
    daily_schedule_cards = [
        item.to_dict() if hasattr(item, "to_dict") else item
        for item in (monthly_training_calendar.days if monthly_training_calendar else [])
    ]
    calendar_payload = monthly_training_calendar.to_dict() if monthly_training_calendar else None
    phases = list((calendar_payload or {}).get("phases") or [])
    training_load_summary = dict((calendar_payload or {}).get("training_load_summary") or {})
    rag_health = _public_rag_health()
    training_plan_review_result = build_training_plan_review(
        structured_training_plan=structured_plan,
        daily_schedule_cards=daily_schedule_cards,
        training_load_summary=training_load_summary,
        rag_health=rag_health,
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
    answer_source_mode = _answer_source_mode_from_review("structured_plan_rule", training_plan_review_result)
    evidence_chain = _build_response_evidence_chain(
        query=request.query,
        evidence_bundle=state.get("evidence_bundle"),
        answer_source_mode=answer_source_mode,
        answer_text=report,
        rag_health=rag_health,
    )
    _attach_citation_gate_to_trace_and_review(
        workflow_trace=workflow_trace,
        training_plan_review=training_plan_review_result,
        evidence_chain=evidence_chain,
    )
    answer_card = _build_answer_card(
        request=request,
        result=state,
        report=report,
        structured_plan=structured_plan,
        generation_status=generation_status,
        answer_source_mode=str(evidence_chain.get("answer_source_mode") or answer_source_mode),
        evidence_chain=evidence_chain,
    )
    ui_policy = _build_ui_policy(str(answer_card.get("ui_render_mode") or "plan_calendar"))
    save_started = time.perf_counter()
    training_plan_id, persist_status = _save_plan_if_ready(
        structured_plan,
        request,
        daily_schedule_cards,
        user_id=user_id,
    )
    save_elapsed = time.perf_counter() - save_started
    workflow_trace.setdefault("persistence", {})
    if isinstance(workflow_trace["persistence"], dict):
        workflow_trace["persistence"].update(
            {
                "plan_save_status": persist_status,
                "training_plan_id": training_plan_id or "",
                "save_plan_sec": round(save_elapsed, 3),
            }
        )
    record_plan_persist_status(persist_status)
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
        training_plan_review=training_plan_review_result,
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
        answer_card=answer_card,
        full_report={"markdown": report},
        ui_policy=ui_policy,
        answer_source_mode=str(evidence_chain.get("answer_source_mode") or answer_source_mode),
        rag_health=rag_health,
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
    user_id: str = DEFAULT_API_USER_ID,
) -> QueryResponse:
    raw_structured_report = result.get("structured_report")
    structured_report = dict(raw_structured_report) if isinstance(raw_structured_report, dict) else raw_structured_report
    structured_plan = result.get("structured_training_plan")
    training_explanation_panel = None
    monthly_training_calendar = None
    daily_schedule_cards = None
    phases: List[Dict[str, Any]] = []
    training_load_summary: Dict[str, Any] = {}
    training_plan_review_result: Dict[str, Any] = {}
    rag_health = _public_rag_health()
    if isinstance(structured_report, dict):
        training_explanation_panel = structured_report.get("training_explanation_panel")
        monthly_training_calendar = structured_report.get("monthly_training_calendar")
        daily_schedule_cards = structured_report.get("daily_schedule_cards")
        phases = list(structured_report.get("phases") or [])
        training_load_summary = dict(structured_report.get("training_load_summary") or {})
        training_plan_review_result = dict(structured_report.get("training_plan_review") or {})

    if (not monthly_training_calendar or not daily_schedule_cards) and _has_calendar_source_plan(structured_plan):
        contract = _calendar_contract_from_plan(structured_plan, rag_health=rag_health)
        monthly_training_calendar = monthly_training_calendar or contract["monthly_training_calendar"]
        daily_schedule_cards = daily_schedule_cards or contract["daily_schedule_cards"]
        phases = phases or contract["phases"]
        training_load_summary = training_load_summary or contract["training_load_summary"]
        training_plan_review_result = training_plan_review_result or contract["training_plan_review"]
        if isinstance(structured_report, dict):
            structured_report["monthly_training_calendar"] = monthly_training_calendar
            structured_report["daily_schedule_cards"] = daily_schedule_cards
            structured_report["phases"] = phases
            structured_report["training_load_summary"] = training_load_summary
            structured_report["training_plan_review"] = training_plan_review_result
    elif isinstance(monthly_training_calendar, dict):
        phases = phases or list(monthly_training_calendar.get("phases") or [])
        training_load_summary = training_load_summary or dict(monthly_training_calendar.get("training_load_summary") or {})
        training_plan_review_result = training_plan_review_result or dict(monthly_training_calendar.get("training_plan_review") or {})

    if not training_plan_review_result and _has_calendar_source_plan(structured_plan):
        training_plan_review_result = build_training_plan_review(
            structured_training_plan=structured_plan,
            daily_schedule_cards=daily_schedule_cards or [],
            training_load_summary=training_load_summary,
            rag_health=rag_health,
        )
        if isinstance(structured_report, dict):
            structured_report["training_plan_review"] = training_plan_review_result

    workflow_trace: Dict[str, Any] = {}
    if isinstance(result.get("workflow_trace"), dict):
        workflow_trace = result["workflow_trace"]
    elif isinstance(structured_report, dict) and isinstance(structured_report.get("workflow_trace"), dict):
        workflow_trace = structured_report["workflow_trace"]
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
    evidence_chain = result.get("evidence_chain") if isinstance(result.get("evidence_chain"), dict) else {}
    answer_source_mode = ""
    if not evidence_chain:
        answer_source_mode = _answer_source_mode_from_review(
            _answer_source_mode_from_result(result, structured_plan, generation_status),
            training_plan_review_result,
        )
        evidence_chain = _build_response_evidence_chain(
            query=request.query,
            evidence_bundle=result.get("evidence_bundle"),
            answer_source_mode=answer_source_mode,
            answer_text=str(result.get("final_report") or result.get("report") or ""),
            rag_health=rag_health,
        )
    else:
        answer_source_mode = _answer_source_mode_from_review(
            str(
                evidence_chain.get("answer_source_mode")
                or _answer_source_mode_from_result(result, structured_plan, generation_status)
            ),
            training_plan_review_result,
        )
        evidence_chain["answer_source_mode"] = answer_source_mode
    answer_source_mode = str(evidence_chain.get("answer_source_mode") or answer_source_mode)
    report = str(result.get("final_report") or result.get("report") or "")
    if str(result.get("intent_type") or "").strip() == "qa":
        report = ensure_kb_visible_evidence_report_sections(report, evidence_chain)
    _attach_citation_gate_to_trace_and_review(
        workflow_trace=workflow_trace,
        training_plan_review=training_plan_review_result,
        evidence_chain=evidence_chain,
    )
    resolved_training_plan_id = training_plan_id
    persist_status = "skipped"
    if resolved_training_plan_id:
        persist_status = "saved"
    else:
        resolved_training_plan_id, persist_status = _save_plan_if_ready(
            structured_plan,
            request,
            daily_schedule_cards,
            user_id=user_id,
        )
        record_plan_persist_status(persist_status)
    workflow_trace.setdefault("persistence", {})
    if isinstance(workflow_trace["persistence"], dict):
        workflow_trace["persistence"].update(
            {
                "plan_save_status": persist_status,
                "training_plan_id": resolved_training_plan_id or "",
            }
        )
    answer_card = _build_answer_card(
        request=request,
        result=result,
        report=report,
        structured_plan=structured_plan,
        generation_status=generation_status,
        answer_source_mode=answer_source_mode,
        evidence_chain=evidence_chain,
    )
    ui_policy = _build_ui_policy(str(answer_card.get("ui_render_mode") or "qa_card"))

    response = QueryResponse(
        report=report,
        structured_training_plan=structured_plan,
        structured_report=structured_report,
        training_explanation_panel=training_explanation_panel,
        monthly_training_calendar=monthly_training_calendar,
        daily_schedule_cards=daily_schedule_cards,
        phases=phases,
        training_load_summary=training_load_summary,
        training_plan_review=training_plan_review_result,
        token_usage=result.get("token_usage", {}),
        audit_scores=result.get("audit_scores", {}),
        guided_questions=result.get("guided_questions", []),
        training_plan_id=resolved_training_plan_id,
        generation_status=generation_status,
        llm_provider=_normalize_provider(request.llm_provider),
        llm_model=_selected_model(request),
        message=message,
        half_marathon_protocol_validation=structured_plan.get("half_marathon_protocol_validation")
        if isinstance(structured_plan, dict)
        else None,
        answer_card=answer_card,
        full_report={"markdown": report},
        ui_policy=ui_policy,
        answer_source_mode=answer_source_mode,
        rag_health=rag_health,
        workflow_trace=workflow_trace,
        evidence_chain=evidence_chain,
    )
    record_generation_status(generation_status)
    return response
