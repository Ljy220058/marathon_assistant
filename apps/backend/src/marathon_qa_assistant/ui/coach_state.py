from typing import Any, Callable, Dict, Mapping


SESSION_DEFAULT_FACTORIES: Dict[str, Callable[[], Any]] = {
    "sidebar_visible": lambda: True,
    "sidebar_msg": lambda: None,
    "welcome_msg_id": lambda: None,
    "filling_field_key": lambda: None,
    "filling_field_label": lambda: None,
    "filling_field_mode": lambda: None,
    "pending_missing_fields": list,
    "pending_enhancement_fields": list,
    "pending_plan_query": lambda: None,
    "pending_operation": lambda: None,
    "profile_custom_field_key": lambda: None,
    "profile_custom_field_label": lambda: None,
    "profile_selections": dict,
    "profile_wizard_mode": lambda: "full",
    "profile_step_message_id": lambda: None,
    "profile_step_field_key": lambda: None,
    "profile_step_actions": list,
    "profile_current_step": lambda: None,
    "workflow_running": lambda: False,
    "last_error": lambda: None,
    "coach_page_state": lambda: "idle_ready",
    "coach_message_state": lambda: "welcome_ready",
    "coach_ui_snapshot": dict,
}


COACH_PAGE_STATE_LABELS = {
    "idle_ready": "空闲待命",
    "workflow_running": "计划生成中",
    "awaiting_required_profile": "待补基础画像",
    "filling_required_field": "填写基础字段中",
    "filling_enhancement_field": "填写高级字段中",
    "profile_wizard_full": "完整画像向导中",
    "profile_wizard_enhancement": "高级画像向导中",
    "awaiting_adaptive_feedback": "等待自适应反馈输入",
    "awaiting_graph_search": "等待图谱搜索输入",
    "awaiting_cross_research": "等待交叉研究输入",
    "awaiting_pasted_text": "等待粘贴知识文本",
    "plan_ready": "计划已生成",
    "plan_ready_with_enhancement": "基础计划已生成，可补高级画像",
    "answer_ready": "问答结果已生成",
    "error_fallback": "错误兜底",
    "non_coach_mode": "非 Coach 主链路",
}


COACH_MESSAGE_STATE_LABELS = {
    "welcome_ready": "欢迎与功能入口已展示",
    "streaming_status": "进度消息流式输出中",
    "required_profile_prompt": "基础画像补填提示已发出",
    "field_input_prompt": "字段输入提示已发出",
    "wizard_prompt": "画像向导步骤已发出",
    "operation_prompt": "待输入操作提示已发出",
    "report_rendered": "结果报告已渲染",
    "enhancement_prompt": "高级画像补全提示已发出",
    "error_message": "错误消息已发出",
}


COACH_STATE_GUIDANCE = {
    "idle_ready": "可以直接输入训练计划需求，或点击「⚡ 极速画像 (3 步)」先补齐最小画像。",
    "workflow_running": "系统正在生成内容，请等待当前进度消息完成。",
    "awaiting_required_profile": "请点击下方任一基础字段按钮补充信息；补齐后系统会自动继续生成基础计划。",
    "filling_required_field": "请在下方输入框直接回复当前基础字段，不需要再点击其他按钮。",
    "filling_enhancement_field": "请在下方输入框直接回复当前高级字段；也可以保留当前计划稍后再补。",
    "profile_wizard_full": "请按画像向导逐步选择，最后点击「确认并生成计划」。",
    "profile_wizard_enhancement": "请按高级画像向导补充信息，完成后可点击「基于最新画像重生成计划」。",
    "plan_ready": "当前计划已生成；如果刚补完画像，可点击「基于最新画像重生成计划」刷新结果。",
    "plan_ready_with_enhancement": "当前基础计划已可查看；可点击高级画像字段或「补全高级画像」提升计划精度。",
    "answer_ready": "当前回答已生成，可以继续追问或切换功能入口。",
    "error_fallback": "请查看最近错误信息，调整输入后重新发送请求。",
}


def apply_session_defaults(session_set: Callable[[str, Any], None]) -> None:
    for key, factory in SESSION_DEFAULT_FACTORIES.items():
        session_set(key, factory())


def build_coach_ui_snapshot(
    session_get: Callable[[str, Any], Any],
    workflow_state: Mapping[str, Any] | None,
) -> dict:
    workflow_state = workflow_state or {}
    page_state = _resolve_page_state(session_get, workflow_state)
    message_state = _resolve_message_state(session_get, workflow_state)
    pending_operation = session_get("pending_operation") or {}
    enhancement_missing = session_get("pending_enhancement_fields") or []
    required_missing = session_get("pending_missing_fields") or []

    return {
        "chat_profile": session_get("chat_profile", "Coach Mode"),
        "page_state": page_state,
        "page_label": COACH_PAGE_STATE_LABELS.get(page_state, page_state),
        "message_state": message_state,
        "message_label": COACH_MESSAGE_STATE_LABELS.get(message_state, message_state),
        "workflow_running": bool(session_get("workflow_running", False)),
        "sidebar_visible": bool(session_get("sidebar_visible", True)),
        "wizard_mode": session_get("profile_wizard_mode", "full"),
        "pending_operation_type": pending_operation.get("type", ""),
        "required_missing_count": len(required_missing),
        "enhancement_missing_count": len(enhancement_missing),
        "missing_info_status": workflow_state.get("missing_info_status", ""),
        "intent_type": workflow_state.get("intent_type", ""),
        "has_final_report": bool(str(workflow_state.get("final_report", "") or "").strip()),
        "last_error": session_get("last_error"),
        "next_step_hint": COACH_STATE_GUIDANCE.get(page_state, "请根据当前消息提示继续操作。"),
    }


def sync_coach_ui_snapshot(
    session_get: Callable[[str, Any], Any],
    session_set: Callable[[str, Any], None],
    workflow_state: Mapping[str, Any] | None,
) -> dict:
    snapshot = build_coach_ui_snapshot(session_get, workflow_state)
    session_set("coach_page_state", snapshot["page_state"])
    session_set("coach_message_state", snapshot["message_state"])
    session_set("coach_ui_snapshot", snapshot)
    return snapshot


def render_coach_ui_status_md(snapshot: Mapping[str, Any]) -> str:
    if snapshot.get("chat_profile") != "Coach Mode":
        return ""

    lines = [
        "### 下一步",
        f"- {snapshot.get('next_step_hint', '请根据当前消息提示继续操作。')}",
    ]
    enhancement_count = snapshot.get("enhancement_missing_count", 0)
    if enhancement_count:
        lines.append(f"- 待补高级字段：`{enhancement_count}`")
    return "\n".join(lines)


def _resolve_page_state(
    session_get: Callable[[str, Any], Any],
    workflow_state: Mapping[str, Any],
) -> str:
    chat_profile = session_get("chat_profile", "Coach Mode")
    mode = workflow_state.get("mode", "")
    if chat_profile != "Coach Mode" and mode != "team":
        return "non_coach_mode"

    if session_get("last_error"):
        return "error_fallback"

    if session_get("workflow_running", False):
        return "workflow_running"

    if session_get("profile_current_step"):
        wizard_mode = session_get("profile_wizard_mode", "full")
        if wizard_mode == "enhancement":
            return "profile_wizard_enhancement"
        return "profile_wizard_full"

    filling_key = session_get("filling_field_key")
    if filling_key:
        filling_mode = session_get("filling_field_mode", "required")
        if filling_mode == "enhancement":
            return "filling_enhancement_field"
        return "filling_required_field"

    pending_operation = session_get("pending_operation") or {}
    operation_type = pending_operation.get("type", "")
    if operation_type == "adaptive_plan":
        return "awaiting_adaptive_feedback"
    if operation_type == "search_graph":
        return "awaiting_graph_search"
    if operation_type == "cross_research":
        return "awaiting_cross_research"
    if operation_type == "paste_text":
        return "awaiting_pasted_text"

    missing_info_status = workflow_state.get("missing_info_status", "")
    if missing_info_status == "awaiting_profile":
        return "awaiting_required_profile"

    final_report = str(workflow_state.get("final_report", "") or "").strip()
    intent_type = workflow_state.get("intent_type", "")
    enhancement_missing = session_get("pending_enhancement_fields") or []
    if final_report and intent_type == "plan" and enhancement_missing:
        return "plan_ready_with_enhancement"
    if final_report and intent_type == "plan":
        return "plan_ready"
    if final_report:
        return "answer_ready"
    return "idle_ready"


def _resolve_message_state(
    session_get: Callable[[str, Any], Any],
    workflow_state: Mapping[str, Any],
) -> str:
    if session_get("last_error"):
        return "error_message"

    if session_get("workflow_running", False):
        return "streaming_status"

    if session_get("profile_current_step"):
        return "wizard_prompt"

    if session_get("filling_field_key") or session_get("profile_custom_field_key"):
        return "field_input_prompt"

    if session_get("pending_operation"):
        return "operation_prompt"

    missing_info_status = workflow_state.get("missing_info_status", "")
    if missing_info_status == "awaiting_profile":
        return "required_profile_prompt"

    final_report = str(workflow_state.get("final_report", "") or "").strip()
    enhancement_missing = session_get("pending_enhancement_fields") or []
    if final_report and workflow_state.get("intent_type") == "plan" and enhancement_missing:
        return "enhancement_prompt"
    if final_report:
        return "report_rendered"
    return "welcome_ready"
