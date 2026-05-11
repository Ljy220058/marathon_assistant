from typing import Any, Dict, List, Optional, Tuple

try:
    from langchain_core.runnables import RunnableConfig
except ImportError:
    RunnableConfig = Any

from marathon_qa_assistant.core.state_models import (
    IntegratedState,
    build_adaptive_adjustment_contract,
    derive_adaptive_reasons,
    normalize_workout_feedback,
)
from marathon_qa_assistant.core.evidence_bundle import find_invalid_citations
from marathon_qa_assistant.nodes.common import (
    ai_invoke,
    ensure_usage,
    format_evidence_lines,
    format_state_evidence_lines,
    get_security_prompt_suffix,
)


def _profile_summary(profile: Dict[str, Any]) -> str:
    return (
        f"经验水平: {profile.get('experience_level', '未知')}\n"
        f"目标: {profile.get('goal', '未知')}\n"
        f"周跑量: {profile.get('weekly_mileage', 0)} km\n"
        f"LTHR: {profile.get('lthr', 0)}\n"
        f"T-Pace: {profile.get('t_pace', '') or '未设置'}"
    )


def _format_wiki_context(wiki_context: str) -> str:
    text = str(wiki_context or "").strip()
    if not text:
        return "暂无外部概念补充"
    return text


async def _run_expert_llm(
    role_name: str,
    task_instruction: str,
    state: IntegratedState,
    config: RunnableConfig,
    fallback_title: str,
) -> Tuple[str, Dict[str, int]]:
    profile = state.get("user_profile", {})
    prompt = f"""你是马拉松多智能体系统中的 {role_name}。

任务要求：
{task_instruction}

用户问题：
{state.get("query", "")}

用户画像：
{_profile_summary(profile)}

知识图谱上下文：
{state.get("graph_context", "") or "暂无直接图谱路径"}

本地知识库证据：
{format_state_evidence_lines(state, limit=5)}

Wiki 概念补充上下文：
{_format_wiki_context(state.get("wiki_context", ""))}

引用规则（严格遵守，违反即为不合格）：
1. 凡使用上述本地知识库证据中的事实信息，必须在对应句末标注 [1]、[2] 等数字来源编号，只允许纯数字编号格式。
2. 正确示例：...由于过度训练 [1]。...VO₂max 提升与间歇跑有关 [1][2]。
3. 严禁使用以下格式：[来源: xxx.pdf]、[来源: 某论文]、[ref: xxx]、[citation needed] 或任何非纯数字的引用格式。这些格式前端无法生成可点击的预览按钮。
4. Wiki 只用于解释概念背景，不作为训练处方依据，也不要给 Wiki 内容编造 [n] 引用。

请输出简洁、可执行、可审核的中文 Markdown，严格遵守引用规则，避免编造资料来源。
{get_security_prompt_suffix()}"""

    try:
        return await ai_invoke(prompt, config, state.get("token_usage"))
    except Exception:
        fallback = (
            f"## {fallback_title}\n"
            f"- 问题：{state.get('query', '')}\n"
            f"- 画像摘要：{profile.get('goal', '未知目标')} / {profile.get('weekly_mileage', 0)} km\n"
            f"- 证据摘要：\n{format_state_evidence_lines(state, limit=5)}"
        )
        return fallback, ensure_usage(state.get("token_usage"))


async def coach_node(state: IntegratedState, config: RunnableConfig) -> dict:
    intent = state.get("intent_type", "qa")
    if intent == "plan":
        task_instruction = (
            "用户请求生成训练计划。请从用户需求中提取所有训练类型、配速、时间、场地约束，"
            "生成一份包含具体日程的周训练计划。每节课必须包含热身方案、主课细节（组数×距离+配速+组间休息）、冷身方案。"
            "输出为 Markdown 表格格式，一周七天全覆盖。不要反问用户。"
        )
    else:
        task_instruction = "给出简洁的训练建议或问答回复。"
    content, usage = await _run_expert_llm(
        role_name="Coach",
        task_instruction=task_instruction,
        state=state,
        config=config,
        fallback_title="教练建议",
    )
    return {
        "draft_plan": content,
        "rag_sources": state.get("rag_sources", []),
        "token_usage": usage,
        "reasoning_log": ["[coach] 已生成训练建议草稿"],
    }


async def adaptive_coach_node(state: IntegratedState, config: RunnableConfig) -> dict:
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
    content, usage = await _run_expert_llm(
        role_name="Adaptive Coach",
        task_instruction=(
            "基于训练反馈，对当前计划做自适应调整建议。"
            "\n请优先围绕以下四类原因作答：轻微疲劳、明显疲劳、疼痛风险、漏训。"
            "\n输出中至少覆盖：明日调整、本周微调、替代训练、风险提示、为什么这么调。"
            f"\n标准化反馈卡：{workout_feedback}"
            f"\n已识别原因：{reasons}"
            f"\n调整输出骨架：{adaptive_adjustment}"
        ),
        state=state,
        config=config,
        fallback_title="自适应调整建议",
    )
    return {
        "draft_plan": content,
        "adaptive_feedback": adaptive_feedback,
        "adaptive_adjustment": adaptive_adjustment,
        "rag_sources": state.get("rag_sources", []),
        "token_usage": usage,
        "reasoning_log": ["[adaptive_coach] 已生成自适应调整建议"],
    }


async def nutritionist_node(state: IntegratedState, config: RunnableConfig) -> dict:
    content, usage = await _run_expert_llm(
        role_name="Nutritionist",
        task_instruction="为现有建议补充训练前中后补给、补水和恢复营养提醒。",
        state=state,
        config=config,
        fallback_title="营养支持建议",
    )
    merged = (state.get("draft_plan", "") + "\n\n" + content).strip()
    return {
        "draft_plan": merged,
        "nutritionist_done": True,
        "token_usage": usage,
        "reasoning_log": ["[nutritionist] 已补充营养支持建议"],
    }


async def therapist_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    draft = state.get("draft_plan", "") or state.get("final_report", "")
    review_feedback: List[str] = []
    passed = True

    risky_keywords = ["每日高强度", "无休息", "强忍疼痛", "all-out", "极限冲刺"]
    for keyword in risky_keywords:
        if keyword in draft:
            passed = False
            review_feedback.append(f"检测到潜在高风险表述：{keyword}")

    if state.get("intent_type") == "qa":
        review_feedback.append("QA 模式仅做安全检查，不做处方回写。")

    feedback_text = "；".join(review_feedback) if review_feedback else "未发现明显风险表达。"
    risk_alert = ""
    if not passed:
        risk_alert = f"<div class='github-flash-warn'><strong>治疗师审查：</strong>{feedback_text}</div>"

    return {
        "therapist_passed": passed,
        "review_feedback": feedback_text,
        "risk_alert": risk_alert,
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": [f"[therapist] 安全初筛: {'通过' if passed else '需审计处理'}"],
    }


async def critic_auditor_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    current_iteration = int(state.get("iteration_count", 0) or 0)
    draft = state.get("draft_plan", "") or state.get("final_report", "")
    evidence_bundle = state.get("evidence_bundle") if isinstance(state.get("evidence_bundle"), dict) else {}
    evidence_items = [item for item in (evidence_bundle.get("evidence_items") or []) if isinstance(item, dict)]
    structured_plan = state.get("structured_training_plan") if isinstance(state.get("structured_training_plan"), dict) else {}
    workflow_kind = state.get("workflow_kind") or state.get("intent_type") or "qa"
    feedback: List[str] = []

    invalid_citations = find_invalid_citations(draft, evidence_bundle)
    if invalid_citations:
        feedback.append(f"引用编号不存在：{', '.join(invalid_citations)}")

    for item in evidence_items:
        tier = str(item.get("tier") or "")
        if tier in {"kb_fallback", "action_library"} and not str(item.get("source_path") or "").strip():
            feedback.append(f"证据 {item.get('citation_label', '')} 缺少 source_path")
            break

    hmp_validation = {}
    if structured_plan:
        hmp_validation = structured_plan.get("half_marathon_protocol_validation") or {}
    hmp_errors = (hmp_validation.get("errors") or []) if isinstance(hmp_validation, dict) else []
    if hmp_errors:
        feedback.append(f"HMP 专项验证仍有 {len(hmp_errors)} 条错误，不能放行")

    risky_keywords = ["每日高强度", "无休息", "强忍疼痛", "all-out", "极限冲刺"]
    for keyword in risky_keywords:
        if keyword in draft:
            feedback.append(f"检测到潜在高风险表述：{keyword}")

    has_rule_skeleton = bool(structured_plan)
    has_evidence = bool(evidence_items)
    if workflow_kind == "plan" and not (has_rule_skeleton or has_evidence):
        feedback.append("计划型请求缺少规则骨架或证据包支撑")

    therapist_passed = state.get("therapist_passed", True)
    if therapist_passed is False and state.get("review_feedback"):
        feedback.append(str(state.get("review_feedback")))

    approved = not feedback
    consistency = 88 if approved else 60
    safety = 92 if approved else 45
    roi = min(100, 40 + len(evidence_items) * 10)
    if has_rule_skeleton:
        roi = max(roi, 70)

    summary = "通过独立审计，可进入格式化输出。" if approved else "独立审计未通过：" + "；".join(feedback[:4])

    return {
        "is_approved": approved,
        "iteration_count": current_iteration + (0 if approved else 1),
        "review_feedback": summary,
        "audit_scores": {
            "consistency": consistency,
            "safety": safety,
            "roi": roi,
            "summary": summary,
            "score_sources": {
                "evidence_count": len(evidence_items),
                "has_rule_skeleton": has_rule_skeleton,
                "invalid_citations": invalid_citations,
                "hmp_error_count": len(hmp_errors),
            },
        },
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": [f"[critic_auditor] approved={approved}, consistency={consistency}, safety={safety}, roi={roi}"],
    }


async def research_analyst_node(state: IntegratedState, config: RunnableConfig) -> dict:
    content, usage = await _run_expert_llm(
        role_name="Research Analyst",
        task_instruction="输出研究式分析，强调概念关系、证据比较和可复用结论。",
        state=state,
        config=config,
        fallback_title="研究分析",
    )
    return {
        "draft_plan": content,
        "rag_sources": state.get("rag_sources", []),
        "token_usage": usage,
        "reasoning_log": ["[research_analyst] 已生成研究分析草稿"],
    }
