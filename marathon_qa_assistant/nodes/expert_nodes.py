from typing import Any, Dict, List, Optional, Tuple

try:
    from langchain_core.runnables import RunnableConfig
except ImportError:
    RunnableConfig = Any

from marathon_qa_assistant.core.state_models import IntegratedState
from marathon_qa_assistant.nodes.common import (
    ai_invoke,
    ensure_usage,
    format_evidence_lines,
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


async def _run_expert_llm(
    role_name: str,
    task_instruction: str,
    state: IntegratedState,
    config: RunnableConfig,
    fallback_title: str,
) -> Tuple[str, Dict[str, int]]:
    rag_sources = state.get("rag_sources", [])
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
{format_evidence_lines(rag_sources, limit=3)}

引用规则：
凡使用上述证据中的事实信息，必须在对应句末标注 [1]、[2] 等来源编号（例如：...由于过度训练 [1]）。

请输出简洁、可执行、可审核的中文 Markdown，严格遵守引用规则，避免编造资料来源。
{get_security_prompt_suffix()}"""

    try:
        return await ai_invoke(prompt, config, state.get("token_usage"))
    except Exception:
        fallback = (
            f"## {fallback_title}\n"
            f"- 问题：{state.get('query', '')}\n"
            f"- 画像摘要：{profile.get('goal', '未知目标')} / {profile.get('weekly_mileage', 0)} km\n"
            f"- 证据摘要：\n{format_evidence_lines(rag_sources, limit=3)}"
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
    adaptive_feedback = state.get("adaptive_feedback", {})
    content, usage = await _run_expert_llm(
        role_name="Adaptive Coach",
        task_instruction=(
            "基于疲劳、缺课和异常心率反馈，对当前计划做降载或替代建议。"
            f"\n自适应反馈：{adaptive_feedback}"
        ),
        state=state,
        config=config,
        fallback_title="自适应调整建议",
    )
    return {
        "draft_plan": content,
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
        "token_usage": usage,
        "reasoning_log": ["[nutritionist] 已补充营养支持建议"],
    }


async def therapist_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    draft = state.get("draft_plan", "") or state.get("final_report", "")
    review_feedback: List[str] = []
    is_approved = True

    risky_keywords = ["每日高强度", "无休息", "强忍疼痛", "all-out", "极限冲刺"]
    for keyword in risky_keywords:
        if keyword in draft:
            is_approved = False
            review_feedback.append(f"检测到潜在高风险表述：{keyword}")

    if state.get("intent_type") == "qa":
        review_feedback.append("QA 模式仅做安全检查，不做处方回写。")
        is_approved = True

    feedback_text = "；".join(review_feedback) if review_feedback else "未发现明显风险表达。"
    risk_alert = ""
    if not is_approved:
        risk_alert = f"<div class='github-flash-warn'><strong>治疗师审查：</strong>{feedback_text}</div>"

    return {
        "is_approved": is_approved,
        "review_feedback": feedback_text,
        "risk_alert": risk_alert,
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": [f"[therapist] 审查结果: {'通过' if is_approved else '需回退'}"],
    }


async def auditor_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    current_iteration = int(state.get("iteration_count", 0) or 0)
    approved = bool(state.get("is_approved", False))
    rag_sources = state.get("rag_sources", [])
    has_evidence = bool(rag_sources)

    consistency = 85 if approved else 60
    safety = 90 if approved else 55
    roi = min(100, 40 + len(rag_sources) * 10)

    if state.get("intent_type") == "plan" and not has_evidence:
        approved = False
        safety = 40

    summary = "通过终审，可进入格式化输出。" if approved else "存在安全或证据缺口，需要补充或回退。"

    return {
        "is_approved": approved,
        "iteration_count": current_iteration + (0 if approved else 1),
        "audit_scores": {
            "consistency": consistency,
            "safety": safety,
            "roi": roi,
            "summary": summary,
        },
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": [f"[auditor] consistency={consistency}, safety={safety}, roi={roi}"],
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
