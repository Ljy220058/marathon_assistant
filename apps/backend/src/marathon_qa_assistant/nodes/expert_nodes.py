from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import logging
import re
import time

logger = logging.getLogger(__name__)

try:
    from langchain_core.runnables import RunnableConfig
except ImportError:  # pragma: no cover - test environments may not install langchain
    RunnableConfig = Any

from marathon_qa_assistant.core.app_state import V2_VECTOR_DIR
from marathon_qa_assistant.core.evidence_bundle import build_evidence_bundle, find_invalid_citations
from marathon_qa_assistant.core.profile_context import build_prompt_profile_summary
from marathon_qa_assistant.core.state_models import (
    IntegratedState,
    build_adaptive_adjustment_contract,
    derive_adaptive_reasons,
    normalize_workout_feedback,
)
from marathon_qa_assistant.core.prompt_kit import (
    QA_REPORT_CONTRACT_INSTRUCTION,
    QA_REPORT_REQUIRED_SECTIONS,
    build_expert_prompt,
)
from marathon_qa_assistant.nodes.common import (
    ai_invoke,
    build_rag_sources,
    ensure_usage,
    format_state_evidence_lines,
    get_context,
)


def _profile_summary(profile: Dict[str, Any]) -> str:
    return build_prompt_profile_summary(profile)


def _format_wiki_context(wiki_context: str) -> str:
    text = str(wiki_context or "").strip()
    return text or "暂无外部概念补充"


def _source_domain_blob(item: Dict[str, Any]) -> str:
    values = [
        item.get("domain_pack", ""),
        item.get("evidence_domain", ""),
        item.get("knowledge_layer", ""),
        item.get("expert_domain", ""),
        item.get("source_file", ""),
        item.get("source_path", ""),
        item.get("source", ""),
        item.get("document", ""),
        " ".join(str(term or "") for term in (item.get("domain_terms") or [])),
        str(item.get("text") or item.get("snippet") or item.get("text_span") or "")[:500],
    ]
    return " ".join(str(value or "") for value in values).lower()


def _source_metadata_blob(item: Dict[str, Any]) -> str:
    values = [
        item.get("domain_pack", ""),
        item.get("evidence_domain", ""),
        item.get("knowledge_layer", ""),
        item.get("expert_domain", ""),
        item.get("source_file", ""),
        item.get("source_path", ""),
        item.get("source", ""),
        item.get("document", ""),
        " ".join(str(term or "") for term in (item.get("domain_terms") or [])),
    ]
    return " ".join(str(value or "") for value in values).lower()


def _source_text_blob(item: Dict[str, Any]) -> str:
    return str(item.get("text") or item.get("snippet") or item.get("text_span") or "")[:500].lower()


def _role_keyword_match(blob: str, domain_keywords: Tuple[str, ...]) -> bool:
    return any(str(keyword or "").lower() in blob for keyword in domain_keywords)


def _role_shard_name(role_key: str) -> str:
    return {
        "coach": "training_protocol",
        "adaptive_coach": "training_protocol",
        "nutritionist": "nutrition",
        "psychologist": "sport_psychology",
        "therapist": "injury_safety",
    }.get(role_key, "")


def _role_strong_source_match(role_key: str, item: Dict[str, Any]) -> bool:
    shard = _role_shard_name(role_key)
    score_breakdown = item.get("score_breakdown") if isinstance(item.get("score_breakdown"), dict) else {}
    values = [
        item.get("domain_pack", ""),
        item.get("evidence_domain", ""),
        item.get("knowledge_layer", ""),
        item.get("expert_domain", ""),
        item.get("retrieval_mode", ""),
        item.get("source_file", ""),
        item.get("source_path", ""),
        item.get("source", ""),
        item.get("document", ""),
        score_breakdown.get("shard", ""),
    ]
    blob = " ".join(str(value or "") for value in values).lower()
    if shard and shard.lower() in blob:
        return True
    role_terms = {
        "nutritionist": ("nutrition", "nutrient", "hydration", "fueling"),
        "psychologist": ("sport_psychology", "psychology", "mental"),
        "therapist": ("injury_safety", "medical_safety", "rehab", "injury"),
        "coach": ("training_protocol", "periodization", "training"),
        "adaptive_coach": ("training_protocol", "adaptive", "fatigue", "recovery"),
    }.get(role_key, ())
    return any(term in blob for term in role_terms)


def _domain_from_retrieval_mode(retrieval_mode: str) -> str:
    text = str(retrieval_mode or "")
    for prefix in ("sharded:", "bm25:", "role_shard_jsonl:"):
        if prefix not in text:
            continue
        tail = text.split(prefix, 1)[1]
        domain = re.split(r"[+:]", tail, maxsplit=1)[0].strip()
        if domain:
            return domain
    return ""


def _role_trace_item(item: Dict[str, Any]) -> Dict[str, Any]:
    score_breakdown = item.get("score_breakdown") if isinstance(item.get("score_breakdown"), dict) else {}
    retrieval_mode = str(item.get("retrieval_mode") or "")
    return {
        "source_file": item.get("source_file") or item.get("source") or item.get("document") or "",
        "source_path": item.get("source_path") or item.get("path") or "",
        "page": item.get("page"),
        "chunk_id": item.get("chunk_id") or "",
        "citation_label": item.get("citation_label") or "",
        "evidence_domain": item.get("evidence_domain") or item.get("domain_pack") or _domain_from_retrieval_mode(retrieval_mode),
        "retrieval_mode": retrieval_mode,
        "retrieval_status": item.get("retrieval_status") or "",
        "shard": score_breakdown.get("shard") or "",
        "why_retrieved": item.get("why_retrieved") or "",
        "score": item.get("score"),
    }


def _evidence_identity(item: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        str(item.get("chunk_id") or item.get("evidence_id") or ""),
        str(item.get("source_path") or item.get("source_file") or item.get("source") or ""),
        str(item.get("page") or item.get("locator_hint") or ""),
    )


def _merge_evidence_lists(*groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen = set()
    for group in groups:
        for item in group or []:
            if not isinstance(item, dict):
                continue
            key = _evidence_identity(item)
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _role_evidence_query(state: IntegratedState, role_key: str, query_terms: Tuple[str, ...]) -> str:
    profile = state.get("user_profile") if isinstance(state.get("user_profile"), dict) else {}
    parts = [
        str(state.get("query") or ""),
        str(profile.get("goal") or ""),
        str(profile.get("experience_level") or ""),
        str(profile.get("weekly_mileage") or ""),
        str(state.get("draft_plan") or "")[:1200],
        " ".join(query_terms),
    ]
    role_hints = {
        "nutritionist": "marathon fueling hydration carbohydrate protein sodium recovery",
        "psychologist": "sport psychology mental skills self-talk imagery confidence anxiety goal setting marathon",
        "coach": "marathon training periodization workout prescription intensity distribution long run threshold interval",
        "adaptive_coach": "adaptive training adjustment fatigue missed workout recovery training load deload return to training",
        "therapist": "running injury rehabilitation pain red flags medical safety return to run contraindication",
    }
    parts.append(role_hints.get(role_key, ""))
    return " ".join(part for part in parts if part).strip()


def _fallback_role_shard_hits(
    *,
    role_key: str,
    query: str,
    domain_keywords: Tuple[str, ...],
    top_k: int,
) -> List[Dict[str, Any]]:
    shard_name = _role_shard_name(role_key)
    if not shard_name:
        return []
    chunks_path = V2_VECTOR_DIR.parent / "v2_sharded" / shard_name / "chunks.jsonl"
    if not chunks_path.exists():
        return []

    query_blob = f"{query} {' '.join(domain_keywords)}".lower()
    tokens = [token for token in re.findall(r"[a-z0-9][a-z0-9_\-+.]*", query_blob) if len(token) >= 3]
    tokens = list(dict.fromkeys(tokens))
    scored: List[Tuple[float, Dict[str, Any]]] = []
    try:
        with Path(chunks_path).open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                if not isinstance(chunk, dict):
                    continue
                blob = _source_domain_blob(chunk)
                if domain_keywords and not any(keyword.lower() in blob for keyword in domain_keywords):
                    continue
                overlap = sum(1 for token in tokens if token in blob)
                score = overlap / max(1, len(tokens))
                if score <= 0 and shard_name not in str(chunk.get("domain_terms") or "").lower():
                    continue
                hit = dict(chunk)
                hit["score"] = round(max(score, 0.01), 6)
                hit.setdefault("evidence_domain", shard_name)
                hit["retrieval_mode"] = f"role_shard_jsonl:{shard_name}"
                hit["retrieval_status"] = "role_shard_fallback"
                hit["why_retrieved"] = (
                    f"Role-specific fallback searched {shard_name} shard after runtime RAG returned no role evidence."
                )
                scored.append((float(hit["score"]), hit))
    except Exception as exc:  # pragma: no cover - fallback must never break the workflow
        logger.warning("role shard fallback failed for %s: %s", role_key, exc)
        return []

    scored.sort(key=lambda item: item[0], reverse=True)
    return [hit for _, hit in scored[:top_k]]


def _expert_evidence_trace_for_role(
    *,
    state: IntegratedState,
    role_key: str,
    domain_keywords: Tuple[str, ...],
    allow_fallback: bool = True,
    allow_text_match: bool = True,
) -> Dict[str, Any]:
    role_traces = state.get("expert_evidence_trace") if isinstance(state.get("expert_evidence_trace"), dict) else {}
    cached_trace = role_traces.get(role_key) if isinstance(role_traces, dict) else None
    if isinstance(cached_trace, dict) and cached_trace.get("status") == "verified":
        return cached_trace

    evidence_bundle = state.get("evidence_bundle") if isinstance(state.get("evidence_bundle"), dict) else {}
    candidates: List[Dict[str, Any]] = []
    candidates.extend([item for item in (evidence_bundle.get("evidence_items") or []) if isinstance(item, dict)])
    candidates.extend([item for item in (state.get("rag_sources") or []) if isinstance(item, dict)])
    candidates.extend([item for item in (state.get("ranked_evidence") or []) if isinstance(item, dict)])

    strong_matches: List[Dict[str, Any]] = []
    metadata_matches: List[Dict[str, Any]] = []
    text_matches: List[Dict[str, Any]] = []
    seen = set()
    for item in candidates:
        strong_match = _role_strong_source_match(role_key, item)
        metadata_match = _role_keyword_match(_source_metadata_blob(item), domain_keywords)
        text_match = allow_text_match and _role_keyword_match(_source_text_blob(item), domain_keywords)
        if not strong_match and not metadata_match and not text_match:
            continue
        key = _evidence_identity(item)
        if key in seen:
            continue
        seen.add(key)
        if strong_match:
            strong_matches.append(_role_trace_item(item))
        elif metadata_match:
            metadata_matches.append(_role_trace_item(item))
        elif text_match:
            text_matches.append(_role_trace_item(item))

    matched = strong_matches[:5] or metadata_matches[:5]
    if not matched and allow_fallback:
        query = _role_evidence_query(state, role_key, domain_keywords)
        matched = [_role_trace_item(item) for item in _fallback_role_shard_hits(
            role_key=role_key,
            query=query,
            domain_keywords=domain_keywords,
            top_k=5,
        )]
    if not matched and allow_text_match:
        matched = text_matches[:5]

    return {
        "role": role_key,
        "status": "verified" if matched else "needs_evidence",
        "evidence_refs": matched,
        "note": "" if matched else "No role-specific KB evidence was visible to this expert node.",
    }


def _merge_expert_evidence_trace(
    state: IntegratedState,
    role_key: str,
    trace: Dict[str, Any],
) -> Dict[str, Any]:
    existing = state.get("expert_evidence_trace") if isinstance(state.get("expert_evidence_trace"), dict) else {}
    merged = dict(existing)
    merged[role_key] = trace
    return merged


async def _augment_state_with_role_evidence(
    state: IntegratedState,
    *,
    role_key: str,
    domain_keywords: Tuple[str, ...],
    query_terms: Tuple[str, ...],
    top_k: int = 5,
) -> IntegratedState:
    current_trace = _expert_evidence_trace_for_role(
        state=state,
        role_key=role_key,
        domain_keywords=domain_keywords,
        allow_fallback=False,
        allow_text_match=False,
    )
    if current_trace.get("status") == "verified":
        return state

    query = _role_evidence_query(state, role_key, query_terms)
    if not query:
        return state

    hits = await get_context(query, top_k=top_k, rerank=False)
    role_hits = [
        hit for hit in hits or []
        if isinstance(hit, dict)
        and (_role_strong_source_match(role_key, hit) or _role_keyword_match(_source_metadata_blob(hit), domain_keywords))
    ]
    if not role_hits:
        role_hits = _fallback_role_shard_hits(
            role_key=role_key,
            query=query,
            domain_keywords=domain_keywords,
            top_k=top_k,
        )
    if not role_hits:
        role_hits = [
            hit for hit in hits or []
            if isinstance(hit, dict) and _role_keyword_match(_source_text_blob(hit), domain_keywords)
        ]
    if not role_hits:
        return state

    role_sources = build_rag_sources(role_hits)
    merged_rag_sources = _merge_evidence_lists(state.get("rag_sources") or [], role_sources)
    existing_bundle = state.get("evidence_bundle") if isinstance(state.get("evidence_bundle"), dict) else {}
    augmented_bundle = build_evidence_bundle(
        query=str(state.get("query") or ""),
        ranked_evidence=state.get("ranked_evidence") or [],
        rag_sources=merged_rag_sources,
        structured_training_plan=state.get("structured_training_plan") if isinstance(state.get("structured_training_plan"), dict) else None,
        health=existing_bundle.get("health") if isinstance(existing_bundle, dict) else None,
    )

    augmented_state = dict(state)
    augmented_state["rag_sources"] = merged_rag_sources
    augmented_state["evidence_bundle"] = augmented_bundle
    augmented_state["role_evidence_queries"] = {
        **(state.get("role_evidence_queries") if isinstance(state.get("role_evidence_queries"), dict) else {}),
        role_key: query,
    }
    return augmented_state


async def _run_expert_llm(
    role_name: str,
    task_instruction: str,
    state: IntegratedState,
    config: RunnableConfig,
    fallback_title: str,
) -> Tuple[str, Dict[str, int]]:
    profile = state.get("user_profile", {}) if isinstance(state.get("user_profile"), dict) else {}
    qa_contract = QA_REPORT_CONTRACT_INSTRUCTION if str(state.get("intent_type") or "").lower() == "qa" else ""
    # 专家提示词统一由 prompt_kit.build_expert_prompt 组装：引用规则、安全后缀、
    # QA 契约等共享约束集中管理，避免在各节点内联重复、各自漂移。
    prompt = build_expert_prompt(
        role_name=role_name,
        task_instruction=task_instruction,
        query=state.get("query", ""),
        profile_summary=_profile_summary(profile),
        graph_context=state.get("graph_context", ""),
        evidence_lines=format_state_evidence_lines(state, limit=None),
        wiki_context=_format_wiki_context(state.get("wiki_context", "")),
        qa_contract=qa_contract,
    )

    try:
        return await ai_invoke(prompt, config, state.get("token_usage"))
    except Exception:
        fallback = (
            f"## {fallback_title}\n"
            f"- 问题：{state.get('query', '')}\n"
            f"- 画像摘要：{_profile_summary(profile)}\n"
            f"- 本地知识库可见证据：\n{format_state_evidence_lines(state, limit=None)}"
        )
        return fallback, ensure_usage(state.get("token_usage"))


async def coach_node(state: IntegratedState, config: RunnableConfig) -> dict:
    state = await _augment_state_with_role_evidence(
        state,
        role_key="coach",
        domain_keywords=(
            "training",
            "training_theory",
            "training_protocol",
            "workout",
            "workout_prescription",
            "periodization",
            "race_strategy",
            "threshold",
            "interval",
            "long run",
        ),
        query_terms=("marathon training", "periodization", "workout prescription", "long run", "threshold", "interval"),
    )
    intent = str(state.get("intent_type") or "qa").lower()
    instruction = (
        "根据用户目标和现有证据生成训练计划建议，优先说明负荷、恢复和专项约束。"
        if intent == "plan"
        else "直接回答训练问题，给出可执行建议，不要反问。"
    )
    content, usage = await _run_expert_llm("Coach", instruction, state, config, "教练建议")
    trace = _expert_evidence_trace_for_role(
        state=state,
        role_key="coach",
        domain_keywords=(
            "training",
            "training_theory",
            "training_protocol",
            "workout",
            "workout_prescription",
            "periodization",
            "race_strategy",
            "threshold",
            "interval",
            "long run",
        ),
    )
    return {
        "draft_plan": content,
        "rag_sources": state.get("rag_sources", []),
        "evidence_bundle": state.get("evidence_bundle"),
        "role_evidence_queries": state.get("role_evidence_queries", {}),
        "expert_evidence_trace": _merge_expert_evidence_trace(state, "coach", trace),
        "token_usage": usage,
        "reasoning_log": ["[coach] generated training guidance"],
    }


async def adaptive_coach_node(state: IntegratedState, config: RunnableConfig) -> dict:
    state = await _augment_state_with_role_evidence(
        state,
        role_key="adaptive_coach",
        domain_keywords=("training", "training_protocol", "capacity", "load", "fatigue", "recovery", "deload", "injury", "rehab", "return to run"),
        query_terms=("adaptive training adjustment", "fatigue", "missed workout", "training load", "recovery", "deload"),
    )
    raw_feedback_text = str(state.get("query", "") or "").strip()
    existing_feedback = state.get("adaptive_feedback", {}) or {}
    workout_feedback = normalize_workout_feedback(
        existing_feedback.get("workout_feedback") if isinstance(existing_feedback, dict) else {},
        raw_text=raw_feedback_text,
    )
    reasons = derive_adaptive_reasons(workout_feedback, raw_text=raw_feedback_text)
    adaptive_feedback = {
        "workout_feedback": workout_feedback,
        "reason_codes": [reason["code"] for reason in reasons],
        "reasons": reasons,
        "raw_text": raw_feedback_text,
        "source": "query_text",
    }
    adaptive_adjustment = build_adaptive_adjustment_contract(workout_feedback, raw_text=raw_feedback_text)
    adaptation_type = str(adaptive_adjustment.get("adaptation_type") or "UNKNOWN").upper()
    adaptation_context = {
        "adaptation_type": adaptation_type,
        "reason_codes": adaptive_feedback["reason_codes"],
        "reasons": reasons,
        "source": "adaptive_coach",
    }
    instruction = (
        "根据用户反馈给出自适应训练调整建议，优先处理疲劳、缺课、恢复和负荷边界；不做医疗诊断。"
        f"\n\n自适应反馈数据：{adaptive_feedback}"
    )
    content, usage = await _run_expert_llm("Adaptive Coach", instruction, state, config, "自适应调整建议")
    trace = _expert_evidence_trace_for_role(
        state=state,
        role_key="adaptive_coach",
        domain_keywords=("training", "training_protocol", "capacity", "load", "fatigue", "recovery", "deload", "injury", "rehab", "return to run"),
    )
    return {
        "draft_plan": content,
        "adaptive_feedback": adaptive_feedback,
        "adaptive_adjustment": adaptive_adjustment,
        "adaptation_type": adaptation_type,
        "adaptation_context": adaptation_context,
        "rag_sources": state.get("rag_sources", []),
        "evidence_bundle": state.get("evidence_bundle"),
        "role_evidence_queries": state.get("role_evidence_queries", {}),
        "expert_evidence_trace": _merge_expert_evidence_trace(state, "adaptive_coach", trace),
        "token_usage": usage,
        "reasoning_log": ["[adaptive_coach] generated adaptive adjustment guidance"],
    }


async def nutritionist_node(state: IntegratedState, config: RunnableConfig) -> dict:
    state = await _augment_state_with_role_evidence(
        state,
        role_key="nutritionist",
        domain_keywords=("nutrition", "hydration", "carbohydrate", "protein", "fluid", "sodium", "fueling"),
        query_terms=("nutrition", "hydration", "carbohydrate", "protein", "fluid", "sodium", "race fueling"),
    )
    draft = str(state.get("draft_plan") or state.get("final_report") or "").strip()
    instruction = "围绕当前训练计划给出营养、补水和恢复建议；只覆盖计划中已经出现或用户明确询问的训练类型。"
    content, usage = await _run_expert_llm("Nutritionist", instruction, state, config, "营养支持建议")
    merged = (draft + "\n\n" + content).strip() if draft else content
    trace = _expert_evidence_trace_for_role(
        state=state,
        role_key="nutritionist",
        domain_keywords=("nutrition", "hydration", "carbohydrate", "protein", "fluid", "sodium", "fueling"),
    )
    return {
        "draft_plan": merged,
        "rag_sources": state.get("rag_sources", []),
        "evidence_bundle": state.get("evidence_bundle"),
        "role_evidence_queries": state.get("role_evidence_queries", {}),
        "nutritionist_done": True,
        "expert_evidence_trace": _merge_expert_evidence_trace(state, "nutritionist", trace),
        "token_usage": usage,
        "reasoning_log": ["[nutritionist] added nutrition guidance"],
    }


def _psychology_scenarios(state: IntegratedState) -> List[str]:
    draft = str(state.get("draft_plan") or state.get("final_report") or "")
    profile = state.get("user_profile") if isinstance(state.get("user_profile"), dict) else {}
    feedback = state.get("adaptive_feedback") if isinstance(state.get("adaptive_feedback"), dict) else {}
    scenarios: List[str] = []
    if profile.get("goal"):
        scenarios.append("race_goal")
    if any(keyword.lower() in draft.lower() for keyword in ("long run", "marathon", "半马", "全马", "长距离")):
        scenarios.append("long_run")
    if any(keyword.lower() in draft.lower() for keyword in ("interval", "tempo", "阈值", "间歇", "VO2max")):
        scenarios.append("high_intensity")
    if profile.get("injury_history"):
        scenarios.append("injury_history")
    for reason in feedback.get("reasons") or []:
        if isinstance(reason, dict) and reason.get("code") in {"missed_workout", "high_fatigue", "pain_risk", "mild_fatigue"}:
            scenarios.append(str(reason["code"]))
    return list(dict.fromkeys(scenarios))


async def psychologist_node(state: IntegratedState, config: RunnableConfig) -> dict:
    state = await _augment_state_with_role_evidence(
        state,
        role_key="psychologist",
        domain_keywords=("sport_psychology", "psychology", "psychological", "mental", "confidence", "anxiety", "self-talk", "visualization", "imagery", "goal setting"),
        query_terms=("sport psychology", "mental skills", "self-talk", "imagery", "confidence", "anxiety", "goal setting"),
    )
    draft = str(state.get("draft_plan") or state.get("final_report") or "").strip()
    scenarios = _psychology_scenarios(state)
    trace = _expert_evidence_trace_for_role(
        state=state,
        role_key="psychologist",
        domain_keywords=("sport_psychology", "psychology", "psychological", "mental", "confidence", "anxiety", "self-talk", "visualization", "imagery", "goal setting"),
    )
    if not scenarios:
        return {
            "draft_plan": draft,
            "rag_sources": state.get("rag_sources", []),
            "evidence_bundle": state.get("evidence_bundle"),
            "role_evidence_queries": state.get("role_evidence_queries", {}),
            "psychologist_done": True,
            "needs_psychology_review": False,
            "expert_evidence_trace": _merge_expert_evidence_trace(state, "psychologist", trace),
            "token_usage": ensure_usage(state.get("token_usage")),
            "reasoning_log": ["[psychologist] skipped; no clear psychology context"],
        }

    instruction = "围绕赛前心理准备、长距离训练和高强度训练的心理支持给出建议；不得修改训练处方、营养或医疗决策。"
    content, usage = await _run_expert_llm("Sport Psychologist", instruction, state, config, "心理准备参考")
    merged = (draft + "\n\n" + content).strip() if draft else content
    return {
        "draft_plan": merged,
        "rag_sources": state.get("rag_sources", []),
        "evidence_bundle": state.get("evidence_bundle"),
        "role_evidence_queries": state.get("role_evidence_queries", {}),
        "psychologist_done": True,
        "needs_psychology_review": True,
        "expert_evidence_trace": _merge_expert_evidence_trace(state, "psychologist", trace),
        "token_usage": usage,
        "reasoning_log": ["[psychologist] added psychology guidance"],
    }


async def therapist_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    state = await _augment_state_with_role_evidence(
        state,
        role_key="therapist",
        domain_keywords=("rehab", "rehabilitation", "injury", "pain", "medical", "medical_safety", "safety", "contraindication", "return to run", "tendon", "knee"),
        query_terms=("running injury", "pain", "rehabilitation", "medical safety", "return to run", "red flags"),
    )
    draft = str(state.get("draft_plan") or state.get("final_report") or "")
    query = str(state.get("query") or "")
    medical = state.get("medical_constraints") if isinstance(state.get("medical_constraints"), dict) else {}
    risk_text = f"{query}\n{draft}\n{medical}".lower()
    risk_terms = ("强忍疼痛", "忍痛", "无法承重", "胸痛", "头晕", "晕厥", "骨折", "应力性骨折", "rupture", "fracture")
    limited_by_medical = str(medical.get("can_run") or "").strip().lower() in {"limited", "no"}
    passed = not limited_by_medical and not any(term.lower() in risk_text for term in risk_terms)
    feedback_text = "未发现明显医疗红旗。" if passed else "检测到医疗或伤病红旗，训练计划必须暂停或降级并转人工/医疗评估。"
    risk_alert = "" if passed else f"<div class='github-flash-warn'><strong>治疗师审查：</strong>{feedback_text}</div>"
    medical_constraints = {
        "source_role": "therapist",
        "can_run": "yes" if passed else "limited",
        "can_strength_train": "yes" if passed else "limited",
        "summary": feedback_text,
        "risk_alert": risk_alert,
    }
    trace = _expert_evidence_trace_for_role(
        state=state,
        role_key="therapist",
        domain_keywords=("rehab", "rehabilitation", "injury", "pain", "medical", "medical_safety", "safety", "contraindication", "return to run", "tendon", "knee"),
    )
    return {
        "therapist_passed": passed,
        "medical_constraints": medical_constraints,
        "review_feedback": feedback_text,
        "risk_alert": risk_alert,
        "rag_sources": state.get("rag_sources", []),
        "evidence_bundle": state.get("evidence_bundle"),
        "role_evidence_queries": state.get("role_evidence_queries", {}),
        "expert_evidence_trace": _merge_expert_evidence_trace(state, "therapist", trace),
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": [f"[therapist] safety review {'passed' if passed else 'blocked'}"],
    }


_FEEDBACK_TRIPLE_MAP: Dict[str, Tuple[str, str, str]] = {
    "引用编号不存在": ("llm_generation", "hallucinated_claim", "citation_break"),
    "source_path": ("rag_retrieval", "citation_integrity", "untraceable_evidence"),
    "强忍疼痛": ("user_input", "contraindication_missed", "injury_risk"),
    "治疗师节点未执行": ("user_input", "contraindication_missed", "injury_risk"),
    "S&C": ("llm_generation", "training_capacity_violation", "overtraining_syndrome"),
    "容量": ("llm_generation", "training_capacity_violation", "overtraining_syndrome"),
    "合同": ("llm_generation", "contract_violation", "user_misalignment"),
}

_FIX_MAP: Dict[str, str] = {
    "hallucinated_claim": "删除或替换为有本地证据支持的表述，并重新检查引用编号。",
    "citation_integrity": "为每个处方级建议补充可定位来源，或降级为未绑定证据的一般说明。",
    "contraindication_missed": "暂停相关训练，转 therapist 或人工医疗审查后再继续。",
    "training_capacity_violation": "按 S&C 容量边界降低周跑量、长距离或质量课密度后重新生成。",
    "contract_violation": "按用户明确约束修正计划，包括可用日、时长、周数和训练类型。",
    "user_misalignment": "对照用户画像和反馈逐项修正。",
}


def _classify_feedback(feedback_text: str) -> Tuple[str, str, str, str]:
    risk_source = "llm_generation"
    failure_mode = "citation_integrity"
    real_world_harm = "untraceable_evidence"
    for keyword, triple in _FEEDBACK_TRIPLE_MAP.items():
        if keyword in feedback_text:
            risk_source, failure_mode, real_world_harm = triple
            break
    return risk_source, failure_mode, real_world_harm, _FIX_MAP.get(failure_mode, "重新审查该部分内容。")


def _build_ternary_diagnosis(feedback: List[str], approved: bool) -> Dict[str, Any]:
    if approved:
        return {"diagnoses": [], "summary": "审计通过，无剩余安全风险。"}
    diagnoses = []
    for item in feedback:
        risk_source, failure_mode, real_world_harm, targeted_fix = _classify_feedback(item)
        diagnoses.append(
            {
                "feedback": item,
                "risk_source": risk_source,
                "failure_mode": failure_mode,
                "real_world_harm": real_world_harm,
                "targeted_fix": targeted_fix,
            }
        )
    return {
        "diagnoses": diagnoses,
        "summary": f"审计未通过：{len(diagnoses)} 个问题。",
        "primary_risk_source": diagnoses[0]["risk_source"] if diagnoses else "unknown",
        "primary_failure_mode": diagnoses[0]["failure_mode"] if diagnoses else "unknown",
    }


def _auditor_trace_step(state: Dict[str, Any], approved: bool, feedback: List[str], iteration: int) -> Dict[str, Any]:
    from datetime import datetime, timezone

    return {
        "node": "critic_auditor",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_snapshot": {
            "workflow_kind": state.get("workflow_kind") or state.get("intent_type"),
            "iteration": iteration,
            "has_evidence": bool(state.get("ranked_evidence") or (state.get("evidence_bundle") or {}).get("evidence_items")),
            "has_draft": bool(state.get("draft_plan") or state.get("final_report")),
        },
        "output_snapshot": {
            "approved": approved,
            "issue_count": len(feedback),
            "issues": feedback[:3],
        },
        "decision": "approved" if approved else "retry_or_fail",
    }


def _rule_checker_trace_step(state: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    from datetime import datetime, timezone

    violations = list(result.get("violations") or [])
    return {
        "node": "rule_checker",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_snapshot": {
            "workflow_kind": state.get("workflow_kind") or state.get("intent_type"),
            "has_structured_plan": isinstance(state.get("structured_training_plan"), dict),
            "evidence_count": result.get("evidence_count", 0),
        },
        "output_snapshot": {
            "passed": bool(result.get("passed")),
            "violation_count": len(violations),
            "violations": violations[:3],
        },
        "decision": "passed" if result.get("passed") else "hard_violation",
    }


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_available_days(value: Any) -> List[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    if not text:
        return []
    return [part.strip() for part in re.split(r"[,，、/|;；\s]+", text) if part.strip()]


def _normalize_training_types(value: Any) -> List[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    if not text:
        return []
    return [part.strip() for part in re.split(r"[,，、/|;；]+", text) if part.strip()]


def _estimate_day_duration_min(day: Dict[str, Any]) -> Optional[int]:
    candidates = [
        day.get("duration_minutes"),
        day.get("duration_min"),
        day.get("session_minutes"),
        day.get("duration"),
        day.get("main_set"),
        day.get("notes"),
        day.get("description"),
    ]
    for raw in candidates:
        if isinstance(raw, (int, float)):
            return int(raw)
        text = str(raw or "")
        if not text:
            continue
        hour_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|hour|hours|小时)", text, flags=re.IGNORECASE)
        if hour_match:
            return int(float(hour_match.group(1)) * 60)
        minute_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:min|mins|minute|minutes|分钟|分)", text, flags=re.IGNORECASE)
        if minute_match:
            return int(float(minute_match.group(1)))
    return None


def _is_rest_day(day: Dict[str, Any]) -> bool:
    text = f"{day.get('training_type', '')} {day.get('main_set', '')}".lower()
    return any(term in text for term in ("rest", "休息", "off"))


def _requires_locatable_source_path(item: Dict[str, Any]) -> bool:
    tier = str(item.get("tier") or item.get("evidence_tier") or "").strip()
    if tier not in {"kb_fallback", "action_library"}:
        return False
    trace = item.get("trace") if isinstance(item.get("trace"), dict) else {}
    display_mode = str(item.get("display_mode") or trace.get("display_mode") or "").strip()
    prescription_permission = str(item.get("prescription_permission") or trace.get("prescription_permission") or "").strip()
    evidence_source_type = str(item.get("evidence_source_type") or trace.get("evidence_source_type") or "").strip()
    retrieval_mode = str(item.get("retrieval_mode") or trace.get("retrieval_mode") or "").strip()
    if bool(trace.get("graph_hit")) or str(item.get("kind") or "").strip() == "graph":
        return False
    if display_mode in {"graph_hint", "legacy_explanation", "model_general_knowledge", "needs_evidence", "rejected_source"}:
        return False
    if prescription_permission == "blocked_needs_evidence":
        return False
    if bool(item.get("decision_gate") or trace.get("decision_gate")):
        return False
    if evidence_source_type == "decision_gate" or retrieval_mode == "decision_gate":
        return False
    return True


def _review_training_capacity_envelope(structured_plan: Dict[str, Any], state: IntegratedState) -> List[str]:
    envelope = (
        structured_plan.get("training_capacity_envelope")
        or state.get("training_capacity_envelope")
        or state.get("s_and_c_constraints")
        or {}
    )
    if not isinstance(envelope, dict):
        return []
    load_ceiling = envelope.get("load_ceiling") if isinstance(envelope.get("load_ceiling"), dict) else {}
    weekly_cap = _safe_float(load_ceiling.get("weekly_load_cap_km"))
    long_run_cap = _safe_float(load_ceiling.get("max_long_run_km"))
    quality_max = _safe_float(load_ceiling.get("quality_sessions_max"))
    if weekly_cap is None and long_run_cap is None and quality_max is None:
        return []

    feedback: List[str] = []
    for week in structured_plan.get("week_plans", []) or []:
        if not isinstance(week, dict):
            continue
        signature = week.get("repeat_guard_signature") if isinstance(week.get("repeat_guard_signature"), dict) else {}
        week_index = week.get("week_index") or "?"
        weekly_volume = _safe_float(signature.get("weekly_volume_km"))
        long_run = _safe_float(signature.get("long_run_distance_km"))
        quality_count = _safe_float(signature.get("quality_session_count"))
        if weekly_cap is not None and weekly_volume is not None and weekly_volume > weekly_cap:
            feedback.append(f"[S&C] 第 {week_index} 周周跑量 {weekly_volume:g} km 超过容量上限 {weekly_cap:g} km")
        if long_run_cap is not None and long_run is not None and long_run > long_run_cap:
            feedback.append(f"[S&C] 第 {week_index} 周长距离 {long_run:g} km 超过容量上限 {long_run_cap:g} km")
        if quality_max is not None and quality_count is not None and quality_count > quality_max:
            feedback.append(f"[S&C] 第 {week_index} 周质量课 {quality_count:g} 次超过上限 {quality_max:g} 次")
    return feedback


def _audit_requires_therapist(state: IntegratedState, workflow_kind: str) -> bool:
    # therapist 节点仅从 adaptive_coach 可达（workflow_graph.py: adaptive_coach → therapist）。
    # 在 team/qa/plan 模式下强制要求 therapist 会导致 auditor 永远失败，
    # 因此只在 adaptive 模式下执行此检查。
    if workflow_kind != "adaptive":
        return False
    adaptation_type = str(state.get("adaptation_type") or "").strip().upper()
    adjustment = state.get("adaptive_adjustment") if isinstance(state.get("adaptive_adjustment"), dict) else {}
    if not adaptation_type:
        adaptation_type = str(adjustment.get("adaptation_type") or "").strip().upper()
    return adaptation_type in {"INJURY", "PAIN"}


def _run_hard_rule_checks(state: IntegratedState) -> Dict[str, Any]:
    draft = state.get("draft_plan", "") or state.get("final_report", "")
    evidence_bundle = state.get("evidence_bundle") if isinstance(state.get("evidence_bundle"), dict) else {}
    evidence_items = [item for item in (evidence_bundle.get("evidence_items") or []) if isinstance(item, dict)]
    structured_plan = state.get("structured_training_plan") if isinstance(state.get("structured_training_plan"), dict) else {}
    workflow_kind = str(state.get("workflow_kind") or state.get("intent_type") or "qa")
    feedback: List[str] = []

    if evidence_items:
        invalid_citations = find_invalid_citations(str(draft or ""), evidence_bundle)
        if invalid_citations:
            feedback.append(f"引用编号不存在：{', '.join(invalid_citations)}")
    else:
        invalid_citations = []

    for item in evidence_items:
        if _requires_locatable_source_path(item) and not str(item.get("source_path") or "").strip():
            feedback.append(f"证据 {item.get('citation_label', '')} 缺少 source_path")
            break

    hmp_validation = structured_plan.get("half_marathon_protocol_validation") if structured_plan else {}
    hmp_errors = (hmp_validation.get("errors") or []) if isinstance(hmp_validation, dict) else []
    if hmp_errors:
        feedback.append(f"HMP 专项验证仍有 {len(hmp_errors)} 条错误，不能放行")

    if structured_plan:
        feedback.extend(_review_training_capacity_envelope(structured_plan, state))
        try:
            from marathon_qa_assistant.core.half_marathon_validator import _validate_workout_duration_bounds

            for issue in _validate_workout_duration_bounds(structured_plan.get("week_plans", []) or []):
                feedback.append(f"[{issue.constraint_id}] {issue.message} -> {issue.recommendation}")
        except Exception:
            pass

    for keyword in ("强忍疼痛", "忍痛继续"):
        if keyword in str(draft):
            feedback.append(f"检测到潜在高风险表述：{keyword}")

    has_rule_skeleton = bool(structured_plan)
    has_evidence = bool(evidence_items)
    if workflow_kind == "plan" and not (has_rule_skeleton or has_evidence):
        feedback.append("计划型请求缺少规则骨架或证据包支撑")

    requires_therapist = _audit_requires_therapist(state, workflow_kind)
    therapist_passed = state.get("therapist_passed")
    if requires_therapist:
        if therapist_passed is None:
            feedback.append("治疗师节点未执行 - 无法确认安全审查已完成")
        elif therapist_passed is False and state.get("review_feedback"):
            feedback.append(str(state.get("review_feedback")))

    profile = state.get("user_profile") if isinstance(state.get("user_profile"), dict) else {}
    available_days = _normalize_available_days(profile.get("available_days"))
    if structured_plan and available_days:
        expected_count = len(available_days)
        max_training_days = 0
        for week in structured_plan.get("week_plans", []) or []:
            days = [day for day in (week.get("days", []) or []) if isinstance(day, dict) and not _is_rest_day(day)]
            max_training_days = max(max_training_days, len(days))
        if max_training_days > expected_count:
            feedback.append(
                f"[合同] 计划安排了 {max_training_days} 天训练，但用户明确可用 {expected_count} 天({','.join(available_days)})"
            )

    max_minutes = _safe_float(profile.get("max_session_minutes"))
    if structured_plan and max_minutes is not None:
        for week in structured_plan.get("week_plans", []) or []:
            for day in week.get("days", []) or []:
                if not isinstance(day, dict) or _is_rest_day(day):
                    continue
                duration = _estimate_day_duration_min(day)
                if duration is not None and duration > max_minutes:
                    feedback.append(
                        f"[合同] 第 {week.get('week_index')} 周 {day.get('day')} 约 {duration} 分钟，超过用户设定的最长 {max_minutes:g} 分钟"
                    )
                    break

    explicit_fields = set(profile.get("_explicit_plan_profile_fields") or [])
    training_types = _normalize_training_types(profile.get("training_types"))
    if workflow_kind == "plan" and training_types and "training_types" in explicit_fields:
        missing_types = [item for item in training_types if item not in str(draft)]
        if missing_types:
            feedback.append(f"[合同] 用户要求训练类型 {training_types}，计划未体现：{missing_types}")

    return {
        "passed": not feedback,
        "violations": feedback,
        "invalid_citations": invalid_citations,
        "hmp_error_count": len(hmp_errors),
        "evidence_count": len(evidence_items),
        "has_rule_skeleton": bool(structured_plan),
        "requires_therapist": requires_therapist,
    }


async def rule_checker_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    started = time.perf_counter()

    # 自动修复 LLM 生成的训练时长违反文献约束的情况
    stp = state.get("structured_training_plan")
    if isinstance(stp, dict):
        week_plans = stp.get("week_plans") or []
        if week_plans:
            try:
                from marathon_qa_assistant.core.half_marathon_validator import repair_workout_durations
                repaired = repair_workout_durations(week_plans)
                if repaired:
                    logger.info("rule_checker: auto-repaired %d workout durations", repaired)
            except Exception as exc:
                logger.warning("rule_checker: duration repair failed: %s", exc)

    # 修复 evidence 中缺失 source_path 的情况。
    # curated/degraded 检索的 evidence（如 nutrition/training 知识包）没有 PDF 文件路径，
    # 但通常携带 source_label/source_url/source_registry_id；依次兜底填充，
    # 避免 rule_checker 因"证据 [N] 缺少 source_path"误判 QA 回答失败（导致 auditor 永远 fail → 500/504）。
    eb = state.get("evidence_bundle")
    if isinstance(eb, dict):
        for ev in eb.get("evidence_items") or []:
            if not isinstance(ev, dict):
                continue
            if not str(ev.get("source_path") or "").strip():
                # 依次尝试各 source 字段；'unknown' 视为空（curated/幽灵 evidence 常见）。
                # 用 next 显式跳过 unknown，避免 or 链被 'unknown' 短路后被 != "unknown" 排除。
                candidates = [
                    ev.get("source_file"), ev.get("source"),
                    ev.get("source_label"), ev.get("source_url"),
                    ev.get("source_registry_id"),
                ]
                fallback = next(
                    (str(c or "").strip() for c in candidates
                     if str(c or "").strip() and str(c or "").strip().lower() != "unknown"),
                    "",
                )
                if fallback:
                    ev["source_path"] = fallback
                elif ev.get("kind") in ("graph", "fusion"):
                    ev["source_path"] = "knowledge_graph"
                # 全空幽灵 evidence 不再兜底填占位 —— 由 build_evidence_bundle 聚合层过滤根除。
                # 若此处仍出现空 source_path，说明聚合层过滤有漏网，应修聚合层而非兜底掩盖。

    result = _run_hard_rule_checks(state)
    logger.info(
        "rule_checker: %.1fms, passed=%s, violations=%d, detail=%s",
        (time.perf_counter() - started) * 1000,
        result["passed"],
        len(result["violations"]),
        result["violations"][:3],
    )
    summary = "硬规则检查通过" if result["passed"] else "硬规则检查未通过：" + "；".join(result["violations"][:4])
    if not result["passed"]:
        return {
            "rule_check_result": result,
            "reasoning_log": [f"[rule_checker] passed={result['passed']}, violations={len(result['violations'])}"],
            "execution_trace": [_rule_checker_trace_step(state, result)],
            "token_usage": ensure_usage(state.get("token_usage")),
            "review_feedback": summary,
        }
    return {
        "rule_check_result": result,
        "reasoning_log": [f"[rule_checker] passed={result['passed']}, violations={len(result['violations'])}"],
        "execution_trace": [_rule_checker_trace_step(state, result)],
        "token_usage": ensure_usage(state.get("token_usage")),
        "review_feedback": summary if not result["passed"] else state.get("review_feedback", ""),
    }


async def critic_auditor_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    started = time.perf_counter()
    current_iteration = int(state.get("iteration_count", 0) or 0)
    evidence_bundle = state.get("evidence_bundle") if isinstance(state.get("evidence_bundle"), dict) else {}
    evidence_items = [item for item in (evidence_bundle.get("evidence_items") or []) if isinstance(item, dict)]
    existing_rule_check = state.get("rule_check_result") if isinstance(state.get("rule_check_result"), dict) else {}
    rule_check = (
        existing_rule_check
        if {"passed", "violations"} <= set(existing_rule_check.keys())
        else _run_hard_rule_checks(state)
    )
    feedback = list(rule_check.get("violations") or [])
    invalid_citations = list(rule_check.get("invalid_citations") or [])
    hmp_error_count = int(rule_check.get("hmp_error_count") or 0)
    has_rule_skeleton = bool(rule_check.get("has_rule_skeleton"))
    approved = not feedback
    audit_verdict = "pass" if approved else ("retry" if current_iteration < 2 else "fail")
    evidence_quality = "high" if len(evidence_items) >= 3 else ("medium" if evidence_items else "low")
    summary = "通过独立审计，可进入格式化输出。" if approved else "独立审计未通过：" + "；".join(feedback[:4])
    retry_budget_exhausted = current_iteration >= 2 or int(state.get("hard_rule_retry_count", 0) or 0) >= 1 or int(state.get("rag_audit_retry_count", 0) or 0) >= 2

    logger.info(
        "critic_auditor: %.1fms, approved=%s, issues=%d, evidence=%d",
        (time.perf_counter() - started) * 1000,
        approved,
        len(feedback),
        len(evidence_items),
    )
    if not approved and (audit_verdict == "fail" or retry_budget_exhausted):
        workflow_error = {
            "status": "failed",
            "error_code": "AUDIT_RETRY_EXHAUSTED",
            "node": "critic_auditor",
            "message": "审计重试次数已耗尽，工作流终止。",
            "diagnosis": _build_ternary_diagnosis(feedback, approved),
            "iteration_count": current_iteration,
        }
        return {
            "is_approved": False,
            "iteration_count": current_iteration + 1,
            "review_feedback": summary,
            "audit_verdict": "fail",
            "evidence_quality": evidence_quality,
            "audit_scores": {
                "verdict": "fail",
                "evidence_quality": evidence_quality,
                "issue_count": len(feedback),
                "iterations": current_iteration,
                "summary": summary,
                "score_sources": {
                    "evidence_count": len(evidence_items),
                    "has_rule_skeleton": has_rule_skeleton,
                    "invalid_citations": invalid_citations,
                    "hmp_error_count": hmp_error_count,
                },
            },
            "workflow_error": workflow_error,
            "token_usage": ensure_usage(state.get("token_usage")),
            "reasoning_log": [
                f"[critic_auditor] verdict=fail, approved=False, evidence_quality={evidence_quality}, issues={len(feedback)}"
            ],
            "execution_trace": [_auditor_trace_step(state, approved, feedback, current_iteration)],
            "audit_diagnosis": _build_ternary_diagnosis(feedback, approved),
        }
    return {
        "is_approved": approved,
        "iteration_count": current_iteration + (0 if approved else 1),
        "review_feedback": summary,
        "audit_verdict": audit_verdict,
        "evidence_quality": evidence_quality,
        "audit_scores": {
            "verdict": audit_verdict,
            "evidence_quality": evidence_quality,
            "issue_count": len(feedback),
            "iterations": current_iteration,
            "summary": summary,
            "score_sources": {
                "evidence_count": len(evidence_items),
                "has_rule_skeleton": has_rule_skeleton,
                "invalid_citations": invalid_citations,
                "hmp_error_count": hmp_error_count,
            },
        },
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": [
            f"[critic_auditor] verdict={audit_verdict}, approved={approved}, evidence_quality={evidence_quality}, issues={len(feedback)}"
        ],
        "execution_trace": [_auditor_trace_step(state, approved, feedback, current_iteration)],
        "audit_diagnosis": _build_ternary_diagnosis(feedback, approved),
    }


__all__ = [
    "QA_REPORT_CONTRACT_INSTRUCTION",
    "QA_REPORT_REQUIRED_SECTIONS",
    "_fallback_role_shard_hits",
    "_format_wiki_context",
    "_run_expert_llm",
    "adaptive_coach_node",
    "coach_node",
    "critic_auditor_node",
    "nutritionist_node",
    "psychologist_node",
    "rule_checker_node",
    "therapist_node",
]
