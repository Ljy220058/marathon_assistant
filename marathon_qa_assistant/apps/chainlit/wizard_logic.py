import re
import uuid
import chainlit as cl
from marathon_qa_assistant.nodes.profile_and_retrieval import (
    PROFILE_OPTIONS, PROFILE_FIELD_ORDER
)
from marathon_qa_assistant.apps.chainlit.ui_config import MULTI_VALUE_FIELDS

def _split_multi_value_text(field_key: str, value) -> list[str]:
    """把历史字符串或脏格式多选值拆成稳定的选项列表。"""
    if isinstance(value, list):
        parts = []
        for item in value:
            parts.extend(_split_multi_value_text(field_key, item))
        return parts

    text = str(value or "").strip()
    if not text:
        return []

    if field_key == "available_days":
        matched_days = re.findall(r"周[一二三四五六日天]", text)
        if matched_days:
            return ["周日" if item == "周天" else item for item in matched_days]

    normalized_text = re.sub(r"[，、；;/|]+", ",", text)
    normalized_text = re.sub(r"\s+", ",", normalized_text)
    return [item.strip() for item in normalized_text.split(",") if item.strip()]

def _normalize_multi_selection(values, field_key: str = ""):
    """规范化多选值，去重、过滤无效项并按预设顺序输出。"""
    raw_values = _split_multi_value_text(field_key, values)
    option_keys = [opt["key"] for opt in PROFILE_OPTIONS.get(field_key, {}).get("options", [])]

    normalized = []
    seen = set()
    for item in raw_values:
        if item in seen:
            continue
        if option_keys and item not in option_keys:
            continue
        seen.add(item)
        normalized.append(item)

    if option_keys:
        normalized.sort(key=option_keys.index)
    return normalized

def _normalize_profile_selections(selections: dict) -> dict:
    """统一清洗会话中的训练画像选择，避免历史脏值污染当前 UI。"""
    normalized = dict(selections or {})
    for field_key in MULTI_VALUE_FIELDS:
        if field_key in normalized:
            normalized[field_key] = _normalize_multi_selection(normalized.get(field_key), field_key)
    return normalized

def _build_step_payload(field_key: str, step_token: str, **extra) -> dict:
    payload = {"field": field_key, "step_token": step_token}
    payload.update(extra)
    return payload

def _get_current_profile_step_token() -> str:
    current_step = cl.user_session.get("profile_current_step") or {}
    token = current_step.get("token")
    if not token:
        token = str(uuid.uuid4())
    return token

def _prev_field(field_key: str):
    """获取当前字段的上一个字段（跳过最终确认位）"""
    if field_key not in PROFILE_FIELD_ORDER:
        return None
    idx = PROFILE_FIELD_ORDER.index(field_key)
    for i in range(idx - 1, -1, -1):
        key = PROFILE_FIELD_ORDER[i]
        if key != "__confirm__":
            return key
    return None

def _next_field(field_key: str):
    """获取当前字段的下一个字段"""
    if field_key not in PROFILE_FIELD_ORDER:
        return None
    idx = PROFILE_FIELD_ORDER.index(field_key)
    if idx + 1 < len(PROFILE_FIELD_ORDER):
        return PROFILE_FIELD_ORDER[idx + 1]
    return None

def _render_profile_step(field_key: str, selections: dict):
    """渲染单字段填写步骤，返回 (markdown_content, actions)"""
    cfg = PROFILE_OPTIONS.get(field_key)
    if not cfg:
        return None, []

    label = cfg["label"]
    hint = cfg["hint"]
    field_type = cfg["type"]
    options = cfg.get("options", [])
    current_val = selections.get(field_key)

    field_idx = PROFILE_FIELD_ORDER.index(field_key) if field_key in PROFILE_FIELD_ORDER else 0
    total = len([f for f in PROFILE_FIELD_ORDER if f != "__confirm__"])
    progress = min(field_idx + 1, total)

    header = f"### 📋 训练画像 [{progress}/{total}]\n\n**{label}**\n\n_{hint}_"

    step_token = _get_current_profile_step_token()
    actions = []

    if field_type in ("single", "single_custom"):
        for opt in options:
            is_selected = (current_val == opt["key"])
            marker = "  ✅" if is_selected else ""
            actions.append(
                cl.Action(
                    name="pick_option",
                    payload=_build_step_payload(field_key, step_token, value=opt["key"]),
                    label=f"{opt['display']}{marker}",
                    description=opt.get("desc", ""),
                )
            )
        if field_type == "single_custom":
            actions.append(
                cl.Action(
                    name="profile_custom",
                    payload=_build_step_payload(field_key, step_token),
                    label="✏️ 自定义",
                    description="手动输入其他值",
                )
            )
        prev_field = _prev_field(field_key)
        if prev_field:
            actions.append(
                cl.Action(
                    name="profile_back",
                    payload=_build_step_payload(field_key, step_token),
                    label="↩️ 返回上一步",
                )
            )
        if current_val:
            actions.append(
                cl.Action(
                    name="clear_single",
                    payload=_build_step_payload(field_key, step_token),
                    label="🗑 清空选择",
                )
            )
        return header + "\n\n请点击选择（可改选/清空）：", actions

    elif field_type == "multi":
        current_val = _normalize_multi_selection(current_val, field_key)
        selected_set = set(current_val)

        for opt in options:
            actions.append(
                cl.Action(
                    name="toggle_option",
                    payload=_build_step_payload(field_key, step_token, value=opt["key"]),
                    label=f"切换 {opt['display']}",
                    description=opt.get("desc", ""),
                )
            )

        selected_display = "、".join(current_val) if current_val else "(无)"
        status_lines = []
        for opt in options:
            marker = "✓" if opt["key"] in selected_set else "○"
            status_lines.append(f"{marker} {opt['display']}")
        status_md = "\n".join(status_lines)
        content = (
            f"{header}\n\n"
            f"已选: **{selected_display}**\n\n"
            f"点击对应按钮可切换（再次点击可取消）\n\n"
            f"{status_md}"
        )

        actions.append(
            cl.Action(
                name="confirm_multi",
                payload=_build_step_payload(field_key, step_token),
                label="✓ 确认并下一步",
            )
        )
        actions.append(
            cl.Action(
                name="clear_multi",
                payload=_build_step_payload(field_key, step_token),
                label="🗑 清空本题",
                description="一键取消本题所有已选项",
            )
        )
        prev_field = _prev_field(field_key)
        if prev_field:
            actions.append(
                cl.Action(
                    name="profile_back",
                    payload=_build_step_payload(field_key, step_token),
                    label="↩️ 返回上一步",
                    description="返回上一个问题并可改选",
                )
            )
        return content, actions

    elif field_type == "custom":
        actions = [
            cl.Action(
                name="profile_custom",
                payload=_build_step_payload(field_key, step_token),
                label="✏️ 填写补充说明",
            ),
            cl.Action(
                name="pick_option",
                payload=_build_step_payload(field_key, step_token, value="__skip__"),
                label="⏭ 跳过",
            ),
        ]
        return header + "\n\n可选填写，也可直接跳过：", actions

    return header, []

def _render_confirm_step(selections: dict):
    """渲染最终确认步骤"""
    step_token = _get_current_profile_step_token()
    content = "### ✅ 训练画像预览\n\n确认以下信息无误后点击生成计划：\n\n"

    for field_key in PROFILE_FIELD_ORDER:
        if field_key == "__confirm__":
            continue
        cfg = PROFILE_OPTIONS.get(field_key, {})
        label = cfg.get("label", field_key)
        val = selections.get(field_key)

        if val is None:
            display_val = "_未填写_"
        elif isinstance(val, list):
            display_val = "、".join(val) if val else "_未填写_"
        else:
            display_val = str(val)

        content += f"- **{label}**: {display_val}\n"

    actions = [
        cl.Action(name="profile_submit", payload=_build_step_payload("__confirm__", step_token), label="✅ 确认并生成计划"),
        cl.Action(name="profile_back", payload=_build_step_payload("__confirm__", step_token), label="↩️ 返回上一步"),
        cl.Action(name="profile_reset", payload=_build_step_payload("__confirm__", step_token), label="🔄 全部重填"),
    ]
    return content, actions

async def _update_profile_step_message(msg_id: str, content: str, actions=None) -> bool:
    """按消息 ID 原地更新训练画像步骤消息。"""
    if not msg_id:
        return False

    try:
        previous_actions = cl.user_session.get("profile_step_actions") or []
        if previous_actions:
            await cl.Message(id=msg_id, content=content, actions=previous_actions).remove_actions()

        if actions is None:
            await cl.Message(id=msg_id, content=content).update()
        else:
            await cl.Message(id=msg_id, content=content, actions=actions).update()
            cl.user_session.set("profile_step_actions", actions)
        if actions is None:
            cl.user_session.set("profile_step_actions", [])
        return True
    except Exception as exc:
        cl.logger.warning(f"Failed to update profile step message: {exc}")
        return False

async def _send_profile_step(field_key: str, selections: dict):
    """发送当前字段的填写步骤消息"""
    selections = _normalize_profile_selections(selections)
    step_token = str(uuid.uuid4())
    current_step = cl.user_session.get("profile_current_step") or {}
    cl.user_session.set(
        "profile_current_step",
        {"field": field_key, "message_id": current_step.get("message_id"), "token": step_token},
    )

    if field_key == "__confirm__":
        content, actions = _render_confirm_step(selections)
    else:
        content, actions = _render_profile_step(field_key, selections)

    if content is None:
        return

    current_step = cl.user_session.get("profile_current_step") or {}
    msg_id = current_step.get("message_id") or cl.user_session.get("profile_step_message_id")

    if msg_id and await _update_profile_step_message(msg_id, content, actions=actions):
        pass
    else:
        step_msg = cl.Message(content=content, actions=actions)
        await step_msg.send()
        msg_id = getattr(step_msg, "id", None)
        cl.user_session.set("profile_step_actions", actions or [])

    cl.user_session.set("profile_step_message_id", msg_id)
    cl.user_session.set("profile_step_field_key", field_key)
    cl.user_session.set(
        "profile_current_step",
        {"field": field_key, "message_id": msg_id, "token": step_token},
    )

def _get_action_message_id(action: cl.Action):
    """兼容读取 Chainlit Action 关联的原消息 ID。"""
    return getattr(action, "forId", None) or getattr(action, "for_id", None)

def _get_profile_step_message_id(action: cl.Action, field_key: str = ""):
    """优先读取 Action 关联消息 ID，失败时回退到当前训练画像步骤消息。"""
    msg_id = _get_action_message_id(action)
    if msg_id:
        return msg_id

    current_step = cl.user_session.get("profile_current_step") or {}
    session_field = current_step.get("field") or cl.user_session.get("profile_step_field_key")
    session_msg_id = current_step.get("message_id") or cl.user_session.get("profile_step_message_id")
    if session_msg_id and (not field_key or session_field == field_key):
        return session_msg_id
    return None

def _is_active_profile_step_action(action: cl.Action, field_key: str) -> bool:
    """仅允许当前步骤的按钮继续执行，拦截旧步骤晚到回调串写新步骤。"""
    current_step = cl.user_session.get("profile_current_step") or {}
    current_field = current_step.get("field")
    current_msg_id = current_step.get("message_id")
    current_token = current_step.get("token")
    action_msg_id = _get_action_message_id(action)
    action_token = action.payload.get("step_token")

    if not current_field or current_field != field_key:
        return False
    if current_token and action_token != current_token:
        return False
    if action_msg_id and current_msg_id and action_msg_id != current_msg_id:
        return False
    return True
