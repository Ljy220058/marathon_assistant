from typing import Any

try:
    from langchain_core.runnables import RunnableConfig
except ImportError:
    RunnableConfig = Any

from marathon_qa_assistant.core.state_models import IntegratedState
from marathon_qa_assistant.nodes.common import ensure_usage, input_guard


async def security_gate_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    query = state.get("query", "")
    is_safe, reason = input_guard.check(query, input_type="query")
    if not is_safe:
        return {
            "mode": "intercepted",
            "is_approved": True,
            "final_report": (
                "## 安全拦截\n"
                f"当前请求被系统安全护栏拦截，原因：{reason}\n\n"
                "请去掉越权、注入或敏感探测相关内容后重试。"
            ),
            "risk_alert": f"<div class='github-flash-error'><strong>安全拦截：</strong>{reason}</div>",
            "reasoning_log": [f"[security] 已拦截输入: {reason}"],
            "token_usage": ensure_usage(state.get("token_usage")),
        }

    for item in state.get("history", [])[-6:]:
        content = str(item.get("content", ""))
        history_safe, history_reason = input_guard.check(content, input_type="history")
        if not history_safe:
            return {
                "mode": "intercepted",
                "is_approved": True,
                "final_report": (
                    "## 会话已重置\n"
                    f"最近对话中检测到不安全内容：{history_reason}\n\n"
                    "请重新发起一个安全、明确的问题。"
                ),
                "risk_alert": f"<div class='github-flash-error'><strong>历史风险：</strong>{history_reason}</div>",
                "reasoning_log": [f"[security] 已拦截历史上下文: {history_reason}"],
                "token_usage": ensure_usage(state.get("token_usage")),
            }

    return {"reasoning_log": ["[security] 输入与近期历史通过检查"]}
