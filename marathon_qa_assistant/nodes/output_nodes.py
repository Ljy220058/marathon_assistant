from typing import Any, Dict, List

try:
    from langchain_core.runnables import RunnableConfig
except ImportError:
    RunnableConfig = Any

from marathon_qa_assistant.core.state_models import IntegratedState
from marathon_qa_assistant.nodes.common import ensure_usage, output_guard_obj


def _build_structured_report(state: IntegratedState, final_report: str) -> Dict[str, Any]:
    rag_sources = state.get("rag_sources", [])
    execution_steps = []
    for idx, task in enumerate(state.get("subtasks", [])[:5], start=1):
        execution_steps.append(
            {
                "task_id": task.get("task_id", f"TASK-{idx}"),
                "objective": task.get("objective", ""),
                "findings": {
                    "focus": task.get("focus", ""),
                    "result": "已纳入本轮综合输出",
                },
                "conclusion": "本子任务已被整合到最终建议中。",
            }
        )

    if not execution_steps:
        execution_steps.append(
            {
                "task_id": "TASK-1",
                "objective": "直接回复用户问题",
                "findings": {"summary": final_report[:400]},
                "conclusion": "当前轮次以直接问答形式完成。",
            }
        )

    evidence_base = []
    for i, src in enumerate(rag_sources[:5], start=1):
        evidence_base.append(
            {
                "id": i,
                "document": src.get("source", "unknown"),
                "source": src.get("source", "unknown"),
                "path": src.get("source_path", "") or src.get("source_file", ""),
                "source_path": src.get("source_path", ""),
                "pages": [int(src.get("page", 1) or 1)],
                "text": src.get("text", ""),
            }
        )

    summary = final_report if final_report and final_report.strip() else "（本轮未产生实质性回复内容）"
    audit_scores = state.get("audit_scores", {})
    wiki_context = str(state.get("wiki_context", "") or "").strip()
    findings = [
        {"key": "用户问题", "value": state.get("query", "") or "—"},
        {"key": "意图分类", "value": state.get("category", "coach")},
        {"key": "识别实体", "value": ", ".join(state.get("entities", [])) or "—"},
        {"key": "图谱关联", "value": state.get("graph_context", "")[:200] or "暂无直接关联"},
        {"key": "一致性评分", "value": str(audit_scores.get("consistency", "—"))},
        {"key": "安全性评分", "value": str(audit_scores.get("safety", "—"))},
        {"key": "知识回报率 (ROI)", "value": f"{audit_scores.get('roi', 0)}%"},
    ]
    if wiki_context:
        findings.append({"key": "Wiki补充", "value": wiki_context[:200]})
    recommendations = [
        state.get("review_feedback", "") or "当前轮次未触发额外审查反馈",
    ]
    risk_alert = state.get("risk_alert", "")
    if risk_alert:
        recommendations.append(f"⚠️ 风险提示: {risk_alert}")

    return {
        "title": "马拉松专业分析报告",
        "summary": summary,
        "findings": findings,
        "recommendations": recommendations,
        "report_metadata": {
            "version": "2.1",
            "mode": state.get("mode", "team"),
            "title": "Marathon QA Assistant Report",
        },
        "analysis_framework": {
            "query": state.get("query", ""),
            "key_entities": state.get("entities", []),
            "graph_context": state.get("graph_context", ""),
            "wiki_context": wiki_context,
        },
        "execution_steps": execution_steps,
        "audit_block": {
            "scores": audit_scores,
            "review_feedback": state.get("review_feedback", ""),
            "risk_alert": risk_alert,
        },
        "evidence_base": evidence_base,
    }


async def formatter_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    raw_content = state.get("final_report") or state.get("draft_plan") or "当前没有可格式化的输出。"
    is_safe, cleaned_output, reason = output_guard_obj.check(raw_content)
    structured_report = _build_structured_report(state, cleaned_output)

    logs = ["[formatter] 已生成结构化报告"]
    if not is_safe:
        logs.append(f"[formatter] 输出安全清洗: {reason}")

    return {
        "final_report": cleaned_output,
        "structured_report": structured_report,
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": logs,
    }


def _safe_truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "…"


async def guided_questions_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    intent = state.get("intent_type", "qa")
    draft_plan = state.get("draft_plan", "")
    final_report = state.get("final_report", "")
    missing_fields = state.get("missing_fields", [])

    if intent == "plan" and final_report == "__FILL_FIELDS__":
        return {
            "guided_questions": [],
            "token_usage": ensure_usage(state.get("token_usage")),
            "reasoning_log": ["[guided_questions] 计划待补信息，跳过追问"],
        }

    if intent == "plan" and not missing_fields and (draft_plan or final_report):
        return {
            "guided_questions": [],
            "token_usage": ensure_usage(state.get("token_usage")),
            "reasoning_log": ["[guided_questions] 计划已生成，跳过追问"],
        }

    query = state.get("query", "")
    category = state.get("category", "coach")
    entities = state.get("entities", [])
    mode = state.get("mode", "team")
    audit_scores = state.get("audit_scores", {})
    roi = audit_scores.get("roi", 0)

    entity_hint = entities[0] if entities else "当前主题"
    query_hint = _safe_truncate(query, 12)
    iteration = state.get("iteration_count", 0)

    template_pool = [
        f"如果继续围绕「{entity_hint}」，你想看更细的分解吗？",
        f"你希望我把这次{category}建议改写成更偏执行清单的版本吗？",
        f"要不要结合你的下一个比赛目标，继续追问「{query_hint}」的后续安排？",
        f"你对「{entity_hint}」相关的运动生理机制感兴趣吗？",
        f"当前 ROI 评分为 {roi}%，要不要补充更多个人数据来提升回答精度？",
        f"需要我把「{entity_hint}」的训练建议拆成周计划吗？",
    ]

    if mode == "research":
        template_pool.append("要不要对当前结论做一次交叉验证分析？")
    if iteration >= 2:
        template_pool.append("是否需要我切换为更简洁的模式来回答？")

    seen = set()
    picked = []
    offset = (iteration * 2 + len(query_hint)) % len(template_pool)
    for i in range(len(template_pool)):
        idx = (offset + i * 3) % len(template_pool)
        q = template_pool[idx]
        if q not in seen:
            seen.add(q)
            picked.append(q)
        if len(picked) >= 3:
            break

    return {
        "guided_questions": picked,
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": ["[guided_questions] 已生成 3 个追问建议"],
    }
