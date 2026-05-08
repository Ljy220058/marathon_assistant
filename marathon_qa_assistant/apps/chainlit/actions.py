import json
import os
import shutil
import time
import chainlit as cl
from marathon_qa_assistant.core.app_state import (
    BASE_DIR, UPLOAD_DOCS_DIR, USER_VECTOR_DIR, global_state
)
from marathon_qa_assistant.core.kb_provider import KB_CHUNKS
from marathon_qa_assistant.core.workflow import (
    load_user_profile, save_user_profile
)
from marathon_qa_assistant.services.analytics import get_or_create_session_id, track_event
from marathon_qa_assistant.services.vector_store import (
    collect_chunks, build_hybrid_indices, save_outputs, infer_source_path
)
from marathon_qa_assistant.services.input_validator import (
    validate_file, 
    DOCUMENT_EXTENSIONS as VALIDATOR_DOC_EXTS, 
    IMAGE_EXTENSIONS as VALIDATOR_IMAGE_EXTS
)
from marathon_qa_assistant.nodes.profile_and_retrieval import (
    PROFILE_OPTIONS, PROFILE_FIELD_ORDER, FIELD_LABELS, FIELD_HINTS,
    profile_selections_to_save
)
from marathon_qa_assistant.nodes.common import llm as common_llm

from marathon_qa_assistant.apps.chainlit.ui_config import MULTI_VALUE_FIELDS
from marathon_qa_assistant.apps.chainlit.setup import (
    KBHelper, init_knowledge_base, update_sidebar, graph_engine
)
from marathon_qa_assistant.apps.chainlit.plan_ui import (
    build_training_feedback_bundle,
    build_training_feedback_card,
    extract_first_week_execution_context,
    render_first_week_execution_md,
    render_training_feedback_input_md,
    render_training_feedback_card_md,
)
from marathon_qa_assistant.apps.chainlit.coach_state import sync_coach_ui_snapshot
from marathon_qa_assistant.apps.chainlit.wizard_logic import (
    _send_profile_step, _normalize_profile_selections, _normalize_multi_selection,
    _is_active_profile_step_action, _get_profile_step_message_id, _render_profile_step,
    _next_field, _prev_field, _update_profile_step_message
)

# 尝试导入可选模块
try:
    from marathon_qa_assistant.services.multimodal import multimodal_service as mm_module
except ImportError:
    mm_module = None


def _sync_ui_state() -> dict:
    state = cl.user_session.get("state") or {}
    return sync_coach_ui_snapshot(cl.user_session.get, cl.user_session.set, state)


def _track_chainlit_event(event_name: str, properties: dict | None = None) -> None:
    try:
        session_id = get_or_create_session_id(cl.user_session.get, cl.user_session.set)
        state = cl.user_session.get("state") or {}
        profile = state.get("user_profile") if isinstance(state, dict) else {}
        user_id = "default_user"
        if isinstance(profile, dict):
            user_id = str(profile.get("user_id") or "default_user")
        track_event(
            event_name,
            user_id=user_id,
            session_id=session_id,
            properties=properties or {},
        )
    except Exception as exc:
        cl.logger.warning(f"analytics event skipped: {event_name}: {exc}")


@cl.action_callback("fill_profile")
async def on_fill_profile(action: cl.Action):
    try:
        await _start_profile_wizard(
            start_field="experience_level",
            intro_message="📋 **正在进入训练画像填写向导...**",
            wizard_mode="full",
        )
    except Exception as e:
        cl.logger.error(f"Error in on_fill_profile: {e}", exc_info=True)
        await cl.Message(content=f"❌ **无法启动画像向导**: {str(e)}").send()

@cl.action_callback("quick_profile")
async def on_quick_profile(action: cl.Action):
    try:
        await _start_profile_wizard(
            start_field="goal",
            intro_message="⚡ **极速画像：只需 3 步即可生成你的专属训练计划！**\n\n填完 goal / 周跑量 / 可用训练日 这 3 个核心字段后，系统会先生成基础计划，之后你随时可以补充高级画像来提升精度。",
            wizard_mode="quick",
        )
    except Exception as e:
        cl.logger.error(f"Error in on_quick_profile: {e}", exc_info=True)
        await cl.Message(content=f"❌ **无法启动极速画像**: {str(e)}").send()

@cl.action_callback("fill_field")
async def on_fill_field(action: cl.Action):
    field_key = action.payload.get("key", "")
    label = action.payload.get("label", field_key)
    hint = action.payload.get("hint", "")
    fill_mode = action.payload.get("mode", "required")
    cl.user_session.set("filling_field_key", field_key)
    cl.user_session.set("filling_field_label", label)
    cl.user_session.set("filling_field_mode", fill_mode)
    _sync_ui_state()
    await update_sidebar()
    mode_label = "高级画像" if fill_mode == "enhancement" else "基础画像"
    next_hint = "填写后会保留当前计划，你可继续补充或手动重生成。" if fill_mode == "enhancement" else "填写后若仍缺字段，会继续提示；补齐后会自动生成基础计划。"
    await cl.Message(content=f"### 📝 正在填写{mode_label}字段\n\n**当前字段**：{label}\n\n_{hint}_\n\n👉 **下一步**：请直接在下方输入框回复该字段的值。{next_hint}").send()

@cl.action_callback("cancel_fill")
async def on_cancel_fill(action: cl.Action):
    await action.remove()
    fill_mode = cl.user_session.get("filling_field_mode", "required")
    if fill_mode != "required":
        cl.user_session.set("pending_enhancement_fields", [])
        cl.user_session.set("filling_field_key", None)
        cl.user_session.set("filling_field_mode", None)
        _sync_ui_state()
        await update_sidebar()
        await cl.Message(content="👌 已保留当前基础计划，你可以稍后再补充高级画像。").send()
        return
    cl.user_session.set("pending_missing_fields", [])
    cl.user_session.set("filling_field_key", None)
    cl.user_session.set("filling_field_mode", None)
    _sync_ui_state()
    await update_sidebar()
    await cl.Message(content="✅ 已跳过画像填写，使用当前已有数据生成训练计划...").send()
    from marathon_qa_assistant.apps.chainlit.logic import process_message
    plan_query = cl.user_session.get("pending_plan_query", "请为我生成第一周训练计划")
    await process_message(
        cl.Message(content=f"【训练计划请求】用户画像可用。原始请求：{plan_query}"),
        plan_click_entry="cancel_fill",
    )


def _build_profile_selections(profile: dict) -> dict:
    selections = {}
    for k, v in profile.items():
        if k in FIELD_LABELS:
            if k in MULTI_VALUE_FIELDS:
                selections[k] = _normalize_multi_selection(v, k)
            else:
                selections[k] = v

    if not selections.get("pb_records"):
        pbs = []
        if profile.get("pb_5k"):
            pbs.append(f"5K {profile['pb_5k']}")
        if profile.get("pb_10k"):
            pbs.append(f"10K {profile['pb_10k']}")
        if profile.get("pb_half"):
            pbs.append(f"半马 {profile['pb_half']}")
        if profile.get("pb_full"):
            pbs.append(f"全马 {profile['pb_full']}")
        if pbs:
            selections["pb_records"] = ", ".join(pbs)

    return _normalize_profile_selections(selections)


async def _start_profile_wizard(start_field: str, intro_message: str, wizard_mode: str):
    await cl.Message(content=intro_message).send()
    profile = await cl.make_async(load_user_profile)()
    selections = _build_profile_selections(profile)
    _track_chainlit_event(
        "profile_wizard_started",
        {
            "entry": start_field,
            "wizard_mode": wizard_mode,
            "has_existing_profile": bool(selections),
            "pre_filled_field_count": len([v for v in selections.values() if v]),
        },
    )
    cl.user_session.set("profile_step_message_id", None)
    cl.user_session.set("profile_step_field_key", None)
    cl.user_session.set("profile_current_step", None)
    cl.user_session.set("profile_step_actions", [])
    cl.user_session.set("profile_wizard_mode", wizard_mode)
    _sync_ui_state()

    cl.user_session.set("profile_selections", selections)
    await _send_profile_step(start_field, selections)
    _sync_ui_state()
    await update_sidebar(profile)


@cl.action_callback("fill_advanced_profile")
async def on_fill_advanced_profile(action: cl.Action):
    try:
        start_field = action.payload.get("start_field") or "experience_level"
        await _start_profile_wizard(
            start_field=start_field,
            intro_message="🎯 **正在进入高级画像补全向导...**\n\n补完这些字段后，可以提升计划强度、配速和周期对齐精度。",
            wizard_mode="enhancement",
        )
    except Exception as e:
        cl.logger.error(f"Error in on_fill_advanced_profile: {e}", exc_info=True)
        await cl.Message(content=f"❌ **无法启动高级画像补全向导**: {str(e)}").send()


@cl.action_callback("regen_plan_from_profile")
async def on_regen_plan_from_profile(action: cl.Action):
    await action.remove()
    from marathon_qa_assistant.apps.chainlit.logic import process_message

    plan_query = cl.user_session.get("pending_plan_query", "请基于我最新的训练画像重新生成训练计划")
    await cl.Message(content="🔄 **正在基于最新训练画像重新生成计划...**").send()
    await process_message(
        cl.Message(content=f"【训练计划请求】请基于我最新的训练画像重新生成计划。原始请求：{plan_query}"),
        plan_click_entry="regen_plan_from_profile",
    )


@cl.action_callback("start_first_week")
async def on_start_first_week(action: cl.Action):
    await action.remove()
    state = cl.user_session.get("state") or {}
    context = extract_first_week_execution_context(state)
    if not context:
        await cl.Message(content="⚠️ 当前会话里还没有可用的首周计划内容，请先生成训练计划。").send()
        return

    cl.user_session.set("first_week_execution_context", context)
    actions = [
        cl.Action(name="submit_training_feedback", payload={"completed": True}, label="📝 完成后提交反馈"),
        cl.Action(name="submit_training_feedback", payload={"completed": False}, label="📝 未完成也提交反馈"),
    ]
    await cl.Message(content=render_first_week_execution_md(context), actions=actions).send()
    _track_chainlit_event(
        "weekly_review_viewed",
        {
            "entry": "start_first_week",
            "week_index": action.payload.get("week_index", 1),
            "has_key_workouts": bool(context.get("key_workouts")),
            "workout_count": len(context.get("key_workouts") or []),
        },
    )


@cl.action_callback("submit_training_feedback")
async def on_submit_training_feedback(action: cl.Action):
    await action.remove()
    context = cl.user_session.get("first_week_execution_context") or extract_first_week_execution_context(cl.user_session.get("state") or {})
    if not context:
        await cl.Message(content="⚠️ 当前会话里还没有可用于反馈的首周训练内容，请先生成并进入首周执行。").send()
        return

    completed = bool(action.payload.get("completed", True))
    cl.user_session.set("pending_operation", {"type": "training_feedback", "completed": completed})
    _sync_ui_state()
    await update_sidebar()
    await cl.Message(content=render_training_feedback_input_md(context, completed=completed)).send()


@cl.action_callback("complete_training_feedback")
async def on_complete_training_feedback(action: cl.Action):
    await action.remove()
    context = cl.user_session.get("first_week_execution_context") or extract_first_week_execution_context(cl.user_session.get("state") or {})
    if not context:
        await cl.Message(content="⚠️ 当前会话里还没有可用于反馈的首周训练内容，请先生成并进入首周执行。").send()
        return

    bundle = build_training_feedback_bundle(
        context,
        raw_text="",
        default_completed=bool(action.payload.get("completed", True)),
    )
    _track_chainlit_event(
        "workout_feedback_submitted",
        {
            "entry": "quick_action",
            "source_type": "action",
            "completed": bool(action.payload.get("completed", True)),
            "completion_status": bundle["workout_feedback"].get("completion_status"),
        },
    )
    state = cl.user_session.get("state") or {}
    state["adaptive_feedback"] = bundle["adaptive_feedback"]
    state["adaptive_adjustment"] = bundle["adaptive_adjustment"]
    cl.user_session.set("state", state)
    cl.user_session.set("latest_training_feedback_card", bundle["card"])
    cl.user_session.set("latest_workout_feedback", bundle["workout_feedback"])
    _sync_ui_state()
    await update_sidebar()
    await cl.Message(content=render_training_feedback_card_md(bundle["card"])).send()


@cl.action_callback("retry_plan_generation")
async def on_retry_plan_generation(action: cl.Action):
    await action.remove()
    from marathon_qa_assistant.apps.chainlit.logic import process_message

    query = (
        action.payload.get("query")
        or cl.user_session.get("pending_plan_query")
        or cl.user_session.get("last_plan_query")
        or "请基于当前训练画像重新生成训练计划"
    )
    cl.user_session.set("pending_plan_query", query)
    await cl.Message(content="🔄 **正在重试计划生成...**").send()
    await process_message(cl.Message(content=str(query)), plan_click_entry="retry_plan_generation")

@cl.action_callback("toggle_sidebar")
async def on_toggle_sidebar(action: cl.Action):
    current = cl.user_session.get("sidebar_visible", True)
    cl.user_session.set("sidebar_visible", not current)
    await update_sidebar()
    await action.remove()

@cl.action_callback("ask_q")
async def on_ask_q(action: cl.Action):
    await action.remove()
    query = action.payload.get("v")
    if query:
        from marathon_qa_assistant.apps.chainlit.logic import process_message
        await process_message(cl.Message(content=query))

@cl.action_callback("extract_pdf_visuals")
async def on_extract_pdf_visuals(action: cl.Action):
    await action.remove()
    pdf_path = action.payload.get("path")
    pdf_name = action.payload.get("name")
    msg_status = cl.Message(content=f"🧾 **正在解析 PDF `{pdf_name}` 并提取图片文字...**")
    await msg_status.send()
    async def ocr_log_callback(info: str):
        msg_status.content = f"🧾 **PDF OCR 处理中**:\n> {info.split(', 图片路径:')[0]}"
        await msg_status.update()
    try:
        insights = await mm_module.extract_and_analyze_pdf(pdf_path, log_callback=ocr_log_callback)
        if not insights:
            msg_status.content = f"⚠️ **未在 PDF `{pdf_name}` 中检测到明显的图片或图表。**"
            await msg_status.update()
            return
        report_md = f"### 📑 PDF 图片文字提取报告: `{pdf_name}`\n\n"
        full_description = ""
        for item in insights:
            report_md += f"**第 {item['page']} 页图片**:\n> {item['description']}\n\n"
            full_description += f"\n\n[PDF Page {item['page']}] {item['description']}"
        msg_status.content = f"✅ **PDF `{pdf_name}` 图片文字提取完成！**"
        await msg_status.update()
        await cl.Message(content=report_md).send()
        cl.user_session.set("last_multimodal_desc", full_description)
        cl.user_session.set("last_multimodal_source", f"pdf:{pdf_name}")
        actions = [cl.Action(name="inject_multimodal", payload={"value": "inject"}, label="注入知识图谱", icon="share")]
        await cl.Message(content="是否将提取到的图片文字注入到您的本地知识图谱中？", actions=actions).send()
    except Exception as e:
        await cl.Message(content=f"❌ **提取失败**: {str(e)}").send()

@cl.action_callback("manage_kb")
async def on_manage_kb(action: cl.Action):
    status_msg = cl.Message(content="🛠️ **正在加载知识库清单...**")
    await status_msg.send()
    try:
        await action.remove()
        inventory_md = await cl.make_async(KBHelper.get_file_inventory_md)()
        status_msg.content = "🛠️ **知识库管理**\n\n您可以查看当前文件，或通过下方功能菜单操作。"
        await status_msg.update()
        await cl.Message(content=inventory_md).send()
        actions = [
            cl.Action(name="upload_file", payload={"value": "upload"}, label="上传新文件", icon="upload"),
            cl.Action(name="paste_text", payload={"value": "paste"}, label="粘贴文本", icon="edit_note"),
            cl.Action(name="preview_pdf_list", payload={"value": "preview"}, label="预览文件", icon="description"),
            cl.Action(name="build_graph_ai", payload={"mode": "incremental"}, label="增量构建图谱", icon="share"),
            cl.Action(name="build_graph_ai", payload={"mode": "full"}, label="重构全量图谱", icon="refresh"),
            cl.Action(name="reindex_kb", payload={"value": "reindex"}, label="重新构建索引", icon="build")
        ]
        await cl.Message(content="请选择操作：", actions=actions).send()
    except Exception as e:
        cl.logger.error(f"ERROR in on_manage_kb: {e}")
        await cl.Message(content=f"❌ **知识库管理出错**: {str(e)}").send()

@cl.action_callback("upload_file")
async def on_upload_file(action: cl.Action):
    await action.remove()
    files = await cl.AskFileMessage(
        content="请上传文件（支持 PDF, TXT, MD, DOCX, 图片 PNG/JPG/WEBP/BMP）：",
        accept=["application/pdf", "text/plain", "text/markdown",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword",
                "image/png", "image/jpeg", "image/webp", "image/bmp", "image/tiff"],
        max_files=20
    ).send()
    if files:
        UPLOAD_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        saved_files = []
        rejected_files = []
        for file in files:
            validation = validate_file(file.path)
            if not validation.get("valid"):
                rejected_files.append(f"{file.name} ({'; '.join(validation.get('errors', []))})")
                continue
            target_path = UPLOAD_DOCS_DIR / file.name
            shutil.copy(file.path, target_path)
            saved_files.append(file.name)
        response_parts = []
        if saved_files:
            response_parts.append(f"✅ **已成功上传 {len(saved_files)} 个文件：**\n- " + "\n- ".join(saved_files))
        if rejected_files:
            response_parts.append(f"⚠️ **{len(rejected_files)} 个文件被拒绝：**\n- " + "\n- ".join(rejected_files))
        await cl.Message(content="\n\n".join(response_parts)).send()
        if saved_files:
            actions = [
                cl.Action(name="reindex_kb", payload={"value": "reindex"}, label="立即构建索引", icon="build"),
                cl.Action(name="build_graph_ai", payload={"mode": "full"}, label="全量重构图谱（推荐）", icon="refresh")
            ]
            await cl.Message(content="现在要构建索引或更新图谱吗？", actions=actions).send()

@cl.action_callback("paste_text")
async def on_paste_text(action: cl.Action):
    await action.remove()
    cl.user_session.set("pending_operation", {"type": "paste_text"})
    await cl.Message(content="📋 **请直接在下方输入框中粘贴文本内容**：\n\n> 粘贴后直接发送即可，无需点击其他按钮。").send()

@cl.action_callback("reindex_kb")
async def on_reindex_kb(action: cl.Action):
    await action.remove()
    domain_docs = BASE_DIR / "domain_docs"
    file_map = {}
    dirs_to_scan = [UPLOAD_DOCS_DIR, domain_docs]
    all_supported = VALIDATOR_DOC_EXTS | VALIDATOR_IMAGE_EXTS
    for d in dirs_to_scan:
        if d.exists():
            for f in d.glob("*"):
                if f.is_file() and f.suffix.lower() in all_supported:
                    if f.name not in file_map or d == UPLOAD_DOCS_DIR:
                        file_map[f.name] = f
    valid_files = list(file_map.values())
    if not valid_files:
        await cl.Message(content="⚠️ **未找到任何有效文档**，请先上传文件。").send()
        return
    msg = cl.Message(content=f"🔨 **正在重新构建索引 ({len(valid_files)} 个文件)...**")
    await msg.send()
    try:
        def build_kb_sync(files):
            chunks, stats = collect_chunks(files, 500, 50)
            if not chunks: return "No chunks", {}
            v, m, b = build_hybrid_indices(chunks)
            artifacts = save_outputs(USER_VECTOR_DIR, chunks, v, m, b)
            return "Success", {"artifacts": artifacts, "total_chunks": len(chunks), "files": stats}
        status, meta = await cl.make_async(build_kb_sync)(valid_files)
        if meta:
            await cl.Message(content=f"✅ **索引构建成功！**\n- 总分片数: `{meta['total_chunks']}`\n- 产物目录: `{meta['artifacts'].get('faiss_dir')}`").send()
            init_knowledge_base()
            actions = [cl.Action(name="build_graph_ai", payload={"mode": "full"}, label="全量重构图谱（推荐）", icon="refresh")]
            await cl.Message(content="📚 **索引已更新**。建议立即进行**全量重构图谱**：", actions=actions).send()
        else:
            await cl.Message(content=f"❌ **构建失败**: {status}").send()
    except Exception as e:
        await cl.Message(content=f"❌ **构建异常**: {str(e)}").send()

@cl.action_callback("build_graph_ai")
async def on_build_graph(action: cl.Action):
    await action.remove()
    mode = action.payload.get("mode", "incremental")
    is_incremental = (mode == "incremental")
    msg_status = cl.Message(content=f"🛠️ **正在{'增量更新' if is_incremental else '全量重构'}知识图谱...**")
    await msg_status.send()
    start_time = time.monotonic()
    async def progress_callback(current, total, filename):
        elapsed = int(time.monotonic() - start_time)
        percent = int(current / total * 100)
        bar_len = 20
        filled_len = int(bar_len * current / total)
        bar = "█" * filled_len + "░" * (bar_len - filled_len)
        msg_status.content = (
            f"🛠️ **知识图谱构建中 ({'增量' if is_incremental else '全量'})**\n\n"
            f"`{bar}` **{percent}%**\n\n"
            f"- **已处理**: `{current} / {total}` 分片\n"
            f"- **当前文件**: `{filename}`\n"
            f"- **累计耗时**: `{elapsed}s`\n"
            f"- **状态**: 正在调用 LLM 提取三元组..."
        )
        await msg_status.update()
    try:
        if not global_state.chunks:
            await cl.Message(content="⚠️ **缺少文本分片**，请先执行‘重新构建索引’。").send()
            return
        n_nodes, n_edges = await graph_engine.build_graph(global_state.chunks, progress_callback=progress_callback, incremental=is_incremental)
        total_elapsed = int(time.monotonic() - start_time)
        density = n_edges / n_nodes if n_nodes > 0 else 0
        details = f"### ✅ 知识图谱更新完毕 ({'增量' if is_incremental else '全量'})\n\n"
        details += f"- **核心实体**: `{n_nodes}`\n- **逻辑关联**: `{n_edges}`\n- **知识密度**: `{density:.2f}`\n- **总计耗时**: `{total_elapsed}s`\n"
        msg_status.content = details
        await msg_status.update()
        await update_sidebar()
    except Exception as e:
        cl.logger.error(f"图谱构建失败: {e}", exc_info=True)
        await cl.Message(content=f"❌ **图谱构建失败**: {str(e)}").send()

@cl.action_callback("preview_pdf_list")
async def on_preview_pdf_list(action: cl.Action):
    await action.remove()
    domain_docs = BASE_DIR / "domain_docs"
    files = []
    for d in [UPLOAD_DOCS_DIR, domain_docs]:
        if d.exists():
            for f in d.glob("*.pdf"):
                files.append(f)
    if not files:
        await cl.Message(content="⚠️ **未找到可预览的 PDF 文件**").send()
        return
    actions = [cl.Action(name="view_pdf", payload={"path": str(f.absolute()), "name": f.name}, label=f"📄 {f.name[:20]}...") for f in files[:10]]
    await cl.Message(content="请选择要预览的 PDF 文件：", actions=actions).send()

@cl.action_callback("view_pdf")
async def on_view_pdf(action: cl.Action):
    payload = action.payload
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception as e:
            cl.logger.error(f"解析 view_pdf payload 失败: {e}")
            await cl.Message(content="❌ **预览失败**: 引用按钮载荷解析失败。").send()
            return

    if not isinstance(payload, dict):
        await cl.Message(content="❌ **预览失败**: 不支持的引用按钮载荷类型。").send()
        return

    path = payload.get("path")
    name = payload.get("name")
    page = payload.get("page", 1)
    snippet = payload.get("snippet", "")
    
    # 方案二：防御性路径补全。如果路径不存在或是纯文件名，尝试推断绝对路径。
    if not path or not os.path.exists(path):
        inferred = infer_source_path(name or os.path.basename(path or ""))
        if inferred:
            path = inferred
    
    if path and os.path.exists(path):
        _track_chainlit_event(
            "evidence_opened",
            {
                "entry": "view_pdf",
                "source_type": "action",
                "source_name": name or os.path.basename(path),
                "page": page,
                "has_snippet": bool(snippet),
                "snippet_length": len(str(snippet or "")),
                "file_type": "pdf" if path.lower().endswith(".pdf") else "text",
            },
        )
        is_pdf = path.lower().endswith(".pdf")
        if is_pdf:
            display_name = f"{name} (P.{page})"
            msg_parts = [f"📑 **正在预览 PDF: {display_name}**"]
            if snippet:
                msg_parts.extend(["", "> **📌 引用原文：**", "> ", f"> {snippet}"])
            msg_content = "\n".join(msg_parts)
            pdf_element = cl.Pdf(name=display_name, path=path, display="side", page=page)
            msg = cl.Message(content=msg_content)
            await msg.send()
            pdf_element.for_id = msg.id
            await pdf_element.send(for_id=msg.id)
        else:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    file_content = f.read()
                msg_parts = [f"📄 **正在预览文件内容: {name}**"]
                if snippet:
                    msg_parts.extend(["", "> **📌 引用原文：**", "> ", f"> {snippet}"])
                msg_content = "\n".join(msg_parts)
                text_element = cl.Text(name=name, content=file_content, display="side")
                msg = cl.Message(content=msg_content)
                await msg.send()
                text_element.for_id = msg.id
                await text_element.send(for_id=msg.id)
            except Exception as e:
                await cl.Message(content=f"❌ **预览失败**: 无法读取文件内容 `{name}` ({str(e)})").send()
    else:
        await cl.Message(content=f"❌ **预览失败**: 文件不存在或路径无效 `{path}`").send()

@cl.action_callback("refresh_profile")
async def on_refresh_profile(action: cl.Action):
    try:
        await action.remove()
    except Exception:
        pass
    profile = await cl.make_async(load_user_profile)()
    state = cl.user_session.get("state") or {}
    state["user_profile"] = profile
    cl.user_session.set("state", state)
    from marathon_qa_assistant.apps.chainlit_app import show_profile_summary
    profile_name = cl.user_session.get("chat_profile") or "Coach Mode"
    _sync_ui_state()
    await show_profile_summary(profile, profile_name)
    await update_sidebar()

@cl.action_callback("adaptive_plan")
async def on_adaptive_plan(action: cl.Action):
    try:
        await action.remove()
    except Exception:
        pass
    cl.user_session.set("pending_operation", {"type": "adaptive_plan"})
    _sync_ui_state()
    await update_sidebar()
    await cl.Message(content="📝 **请输入您的近期反馈**（例如：疲劳度、训练强度感受等）：\n\n> 在下方输入框回复后发送即可。").send()

@cl.action_callback("search_graph")
async def on_search_graph(action: cl.Action):
    try:
        await action.remove()
    except Exception:
        pass
    cl.user_session.set("pending_operation", {"type": "search_graph"})
    _sync_ui_state()
    await update_sidebar()
    await cl.Message(content="🔍 **请输入您想在图谱中搜索的实体名称**（如：VO2Max, HIIT）：\n\n> 在下方输入框回复后发送即可。").send()

@cl.action_callback("cross_research")
async def on_cross_research(action: cl.Action):
    try:
        await action.remove()
    except Exception:
        pass
    cl.user_session.set("pending_operation", {"type": "cross_research"})
    _sync_ui_state()
    await update_sidebar()
    await cl.Message(content="🔬 **请输入要进行交叉研究的多个实体**（用逗号分隔，如：心率, 疲劳度）：\n\n> 在下方输入框回复后发送即可。").send()

@cl.action_callback("pick_option")
async def on_pick_option(action: cl.Action):
    try:
        field = action.payload.get("field", "")
        value = action.payload.get("value", "")
        if not _is_active_profile_step_action(action, field): return
        selections = cl.user_session.get("profile_selections", {})
        if not isinstance(selections, dict): selections = {}
        if value != "__skip__": selections[field] = value
        cl.user_session.set("profile_selections", selections)
        next_f = _next_field(field)
        if next_f: await _send_profile_step(next_f, selections)
        else: await _send_profile_step("__confirm__", selections)
    except Exception as e:
        cl.logger.error(f"Error in on_pick_option: {e}", exc_info=True)
        await cl.Message(content=f"❌ **交互异常**: {str(e)}").send()

@cl.action_callback("toggle_option")
async def on_toggle_option(action: cl.Action):
    try:
        field = action.payload.get("field", "")
        value = action.payload.get("value", "")
        if not _is_active_profile_step_action(action, field): return
        selections = cl.user_session.get("profile_selections", {})
        if not isinstance(selections, dict): selections = {}
        current = _normalize_multi_selection(selections.get(field, []), field)
        if value in current: current.remove(value)
        else: current.append(value)
        selections[field] = _normalize_multi_selection(current, field)
        cl.user_session.set("profile_selections", selections)
        content, actions = _render_profile_step(field, selections)
        msg_id = _get_profile_step_message_id(action, field)
        if not await _update_profile_step_message(msg_id, content, actions=actions):
            await _send_profile_step(field, selections)
    except Exception as e:
        cl.logger.error(f"Error in on_toggle_option: {e}", exc_info=True)
        await cl.Message(content=f"❌ **多选切换异常**: {str(e)}").send()

@cl.action_callback("clear_multi")
async def on_clear_multi(action: cl.Action):
    try:
        field = action.payload.get("field", "")
        if not _is_active_profile_step_action(action, field): return
        selections = cl.user_session.get("profile_selections", {})
        if not isinstance(selections, dict): selections = {}
        selections[field] = []
        cl.user_session.set("profile_selections", selections)
        content, actions = _render_profile_step(field, selections)
        msg_id = _get_profile_step_message_id(action, field)
        if not await _update_profile_step_message(msg_id, content, actions=actions):
            await _send_profile_step(field, selections)
    except Exception as e:
        cl.logger.error(f"Error in on_clear_multi: {e}", exc_info=True)
        await cl.Message(content=f"❌ **清空异常**: {str(e)}").send()

@cl.action_callback("clear_single")
async def on_clear_single(action: cl.Action):
    try:
        field = action.payload.get("field", "")
        if not _is_active_profile_step_action(action, field): return
        selections = cl.user_session.get("profile_selections", {})
        if not isinstance(selections, dict): selections = {}
        selections.pop(field, None)
        cl.user_session.set("profile_selections", selections)
        content, actions = _render_profile_step(field, selections)
        msg_id = _get_profile_step_message_id(action, field)
        if not await _update_profile_step_message(msg_id, content, actions=actions):
            await _send_profile_step(field, selections)
    except Exception as e:
        cl.logger.error(f"Error in on_clear_single: {e}", exc_info=True)
        await cl.Message(content=f"❌ **取消选择异常**: {str(e)}").send()

@cl.action_callback("confirm_multi")
async def on_confirm_multi(action: cl.Action):
    try:
        field = action.payload.get("field", "")
        if not _is_active_profile_step_action(action, field): return
        selections = _normalize_profile_selections(cl.user_session.get("profile_selections", {}))
        cl.user_session.set("profile_selections", selections)
        next_f = _next_field(field)
        if next_f: await _send_profile_step(next_f, selections)
        else: await _send_profile_step("__confirm__", selections)
    except Exception as e:
        cl.logger.error(f"Error in on_confirm_multi: {e}", exc_info=True)
        await cl.Message(content=f"❌ **确认异常**: {str(e)}").send()

@cl.action_callback("profile_custom")
async def on_profile_custom(action: cl.Action):
    field = action.payload.get("field", "")
    cfg = PROFILE_OPTIONS.get(field, {})
    label = cfg.get("label", field)
    if not _is_active_profile_step_action(action, field): return
    msg_id = _get_profile_step_message_id(action, field)
    if msg_id:
        await cl.Message(id=msg_id, content=f"✏️ 正在自定义填写 **{label}**，请在弹出的输入框中回复。", actions=[]).update()
    else:
        await action.remove()
    cl.user_session.set("profile_custom_field_key", field)
    cl.user_session.set("profile_custom_field_label", label)
    await cl.Message(content=f"请输入 **{label}**：\n\n> 请直接在下方输入框中回复，无需点击其他按钮。").send()

@cl.action_callback("profile_back")
async def on_profile_back(action: cl.Action):
    try:
        field = action.payload.get("field", "")
        if not _is_active_profile_step_action(action, field): return
        selections = _normalize_profile_selections(cl.user_session.get("profile_selections", {}))
        if field == "__confirm__": target = _prev_field("__confirm__") or _prev_field(PROFILE_FIELD_ORDER[-1])
        else: target = _prev_field(field)
        if not target:
            await cl.Message(content="ℹ️ 已经是第一步，无法继续返回。").send()
            return
        await _send_profile_step(target, selections)
    except Exception as e:
        cl.logger.error(f"Error in on_profile_back: {e}", exc_info=True)
        await cl.Message(content=f"❌ **返回上一步失败**: {str(e)}").send()

@cl.action_callback("profile_submit")
async def on_profile_submit(action: cl.Action):
    if not _is_active_profile_step_action(action, "__confirm__"): return
    await action.remove()
    cl.user_session.set("profile_current_step", None)
    selections = _normalize_profile_selections(cl.user_session.get("profile_selections", {}))
    cl.user_session.set("profile_selections", selections)
    profile_data = profile_selections_to_save(selections)
    profile = await cl.make_async(load_user_profile)()
    for k, v in profile_data.items():
        if k in ("weekly_mileage", "vo2max", "max_session_minutes", "lthr"):
            try: profile[k] = int(v) if isinstance(v, str) and v.strip().isdigit() else v
            except (ValueError, TypeError): profile[k] = v
        else: profile[k] = v
    await cl.make_async(save_user_profile)(profile)
    state = cl.user_session.get("state")
    if state:
        state["user_profile"] = profile
        cl.user_session.set("state", state)
    cl.user_session.set("pending_missing_fields", [])
    cl.user_session.set("pending_enhancement_fields", [])
    cl.user_session.set("filling_field_key", None)
    cl.user_session.set("filling_field_mode", None)
    cl.user_session.set("last_error", None)
    _sync_ui_state()
    await update_sidebar(profile)
    summary = "### ✅ 训练画像已保存！\n\n"
    for field_key in PROFILE_FIELD_ORDER:
        if field_key == "__confirm__": continue
        cfg = PROFILE_OPTIONS.get(field_key, {})
        label = cfg.get("label", field_key)
        val = selections.get(field_key)
        display_val = "、".join(val) if isinstance(val, list) else (str(val) if val else "未填写")
        summary += f"- **{label}**: {display_val}\n"
    await cl.Message(content=summary).send()
    wizard_mode = cl.user_session.get("profile_wizard_mode", "full")
    _track_chainlit_event(
        "profile_submitted",
        {
            "wizard_mode": wizard_mode,
            "filled_fields": len([v for v in selections.values() if v]),
            "total_fields_available": len(PROFILE_FIELD_ORDER) - 1,
            "will_generate_plan": wizard_mode != "enhancement",
        },
    )
    if wizard_mode == "enhancement":
        plan_query = cl.user_session.get("pending_plan_query", "请基于我最新的训练画像重新生成训练计划")
        actions = [
            cl.Action(name="regen_plan_from_profile", payload={}, label="🔄 基于最新画像重生成计划"),
        ]
        await cl.Message(
            content="✅ **高级画像已补全！** 当前计划浏览不会被打断；如果你愿意，可以基于最新画像重新生成更精准的计划。",
            actions=actions,
        ).send()
    else:
        if wizard_mode == "quick":
            plan_prompt = "请基于我的训练画像生成训练计划，优先给出首周详细课表"
        else:
            plan_prompt = "请为我生成第一周训练计划"
        await cl.Message(content="正在生成你的专属训练计划...").send()
        from marathon_qa_assistant.apps.chainlit.logic import process_message
        await process_message(cl.Message(content=plan_prompt), plan_click_entry="profile_submit")

@cl.action_callback("profile_reset")
async def on_profile_reset(action: cl.Action):
    if not _is_active_profile_step_action(action, "__confirm__"): return
    await action.remove()
    cl.user_session.set("profile_selections", {})
    cl.user_session.set("profile_current_step", None)
    _sync_ui_state()
    await _send_profile_step("experience_level", {})
    _sync_ui_state()
    await update_sidebar()


# ---- 阶段生成回调 ----

def _build_phase_detail_prompt(phase_name: str, start_week: int, end_week: int, week_plans: list, profile: dict, evidence_lines: str) -> str:
    weeks_desc_lines = []
    for week in week_plans:
        if not isinstance(week, dict):
            continue
        wi = week.get("week_index", "?")
        phase = str(week.get("phase") or phase_name).strip()
        goal = str(week.get("week_goal") or "").strip()
        load = str(week.get("load_level") or "").strip()
        prog = str(week.get("load_progression_note") or "").strip()
        reminder = str(week.get("execution_reminder") or "").strip()
        weeks_desc_lines.append(f"第{wi}周 ({phase}, {load}): {goal}")
        if prog:
            weeks_desc_lines.append(f"  负荷递进: {prog}")
        days = week.get("days") or []
        for day in days:
            if not isinstance(day, dict):
                continue
            d = str(day.get("day") or "")
            tt = str(day.get("training_type") or "休息")
            if tt == "休息":
                weeks_desc_lines.append(f"  {d}: 休息")
                continue
            warmup = str(day.get("warmup") or "").strip()
            main_set = str(day.get("main_set") or "").strip()
            cooldown = str(day.get("cooldown") or "").strip()
            venue = str(day.get("venue") or "").strip()
            weeks_desc_lines.append(f"  {d}: {tt} | 热身: {warmup} | 主课: {main_set} | 冷身: {cooldown}" + (f" | 场地: {venue}" if venue else ""))
        if reminder:
            weeks_desc_lines.append(f"  提醒: {reminder}")
        weeks_desc_lines.append("")

    weeks_text = "\n".join(weeks_desc_lines)

    prompt = f"""你是马拉松训练计划教练。请基于以下训练骨架，为「{phase_name}」阶段（第{start_week}-{end_week}周）生成详细的日常训练安排。

══════════════════════════
【训练阶段上下文】
- 阶段名称：{phase_name}
- 周范围：第{start_week}-{end_week}周，共 {end_week - start_week + 1} 周

══════════════════════════
【训练骨架】
{weeks_text}

══════════════════════════
【运动员画像】
- 目标：{profile.get('goal', '未设置')}
- 当前周跑量：{profile.get('weekly_mileage', 0)} km
- T-Pace（乳酸阈配速）：{profile.get('t_pace', '') or '未设置'}
- 经验水平：{profile.get('experience_level', '未知')}
- 可用训练日：{profile.get('available_days', '未指定')}
- 单次最长训练：{profile.get('max_session_minutes', '未指定')} 分钟
- VO₂max：{profile.get('vo2max', '未设置')}

══════════════════════════
【知识库证据】
{evidence_lines}

══════════════════════════
【硬性输出约束】

1. 每周 7 天全覆盖（周一至周日），一天不能少
2. 骨架中指定的训练类型必须逐一覆盖，不可遗漏

★ 主课格式强制要求：
  A. 间歇/重复类：必须写成「N×距离，配速X:XX/km，组间慢跑Ym/站立Zm」
  B. 节奏跑：必须写成「T分钟，配速X:XX/km」
  C. 有氧阈：必须写成「T分钟，配速X:XX/km」
  D. 长距离：必须写成「T分钟，配速X:XX-X:XX/km」
  E. 轻松跑：必须写成「T分钟，配速X:XX/km 或更慢」
  F. 配速必须带单位 /km

★ 热身格式：写具体时长+动作类型
★ 冷身格式：写具体时长+动作类型
★ 表格列：日期 | 训练类型 | 热身 | 主课 | 冷身 | 场地 | 备注
★ 表格之后附 ≤100 字的执行提醒

4. 不要反问用户，不要追加需要补充的信息
5. 配速标注统一使用「分:秒/km」格式（如 3:07/km）"""
    return prompt


@cl.action_callback("generate_phase_training")
async def on_generate_phase_training(action: cl.Action):
    await action.remove()
    phase_name = str(action.payload.get("phase") or "")
    start_week = int(action.payload.get("start_week") or 0)
    end_week = int(action.payload.get("end_week") or 0)

    if not phase_name or start_week <= 0 or end_week < start_week:
        await cl.Message(content="⚠️ 阶段参数不完整，请返回重新选择。").send()
        return

    state = cl.user_session.get("full_plan_final_state") or cl.user_session.get("state") or {}
    structured_plan = state.get("structured_training_plan") or {}
    if not isinstance(structured_plan, dict):
        structured_plan = {}

    all_weeks = structured_plan.get("week_plans") or []
    if not isinstance(all_weeks, list):
        all_weeks = []

    phase_weeks = [w for w in all_weeks if isinstance(w, dict) and start_week <= int(w.get("week_index") or 0) <= end_week]
    if not phase_weeks:
        await cl.Message(content=f"⚠️ 未找到 {phase_name}（第{start_week}-{end_week}周）的训练骨架数据。").send()
        return

    profile = state.get("user_profile") or {}
    if not isinstance(profile, dict):
        profile = {}
    rag_sources = state.get("rag_sources") or []

    try:
        from marathon_qa_assistant.nodes.common import ai_invoke, ensure_usage, format_evidence_lines
    except ImportError:
        await cl.Message(content="❌ 无法加载 LLM 调用模块，请稍后重试。").send()
        return

    evidence_lines = format_evidence_lines(rag_sources, limit=3)
    prompt = _build_phase_detail_prompt(phase_name, start_week, end_week, phase_weeks, profile, evidence_lines)

    status_msg = cl.Message(content=f"⏳ 正在调用模型生成 **{phase_name}**（第{start_week}-{end_week}周）详细课表，请稍候…")
    await status_msg.send()

    try:
        content, _usage = await ai_invoke(prompt, None, None)
    except Exception as exc:
        await cl.Message(content=f"❌ LLM 调用失败: {str(exc)}").send()
        return

    if not str(content or "").strip():
        await cl.Message(content="⚠️ 模型返回为空，请尝试重新生成或切换到完整计划查看。").send()
        return

    phase_actions = [
        cl.Action(
            name="show_full_plan",
            payload={},
            label="📄 查看完整计划",
        ),
    ]

    await cl.Message(
        content=f"## 📋 {phase_name} 详细课表\n\n{content}",
        actions=phase_actions,
    ).send()


@cl.action_callback("show_full_plan")
async def on_show_full_plan(action: cl.Action):
    await action.remove()
    final_state = cl.user_session.get("full_plan_final_state")

    if not final_state:
        await cl.Message(content="⚠️ 当前会话里没有缓存的完整计划数据，请重新生成训练计划。").send()
        return

    from marathon_qa_assistant.apps.chainlit.plan_ui import build_calendar_props_with_explanations

    calendar_props = build_calendar_props_with_explanations(final_state)
    if not calendar_props:
        await cl.Message(content="⚠️ 暂时无法渲染训练日历，请稍后重试。").send()
        return

    calendar_element = cl.CustomElement(name="MonthlyTrainingCalendar", props=calendar_props)
    year = calendar_props.get("year", "")
    month = calendar_props.get("month", "")
    start_w = calendar_props.get("start_week_index", 1)
    end_w = calendar_props.get("end_week_index", 1)
    await cl.Message(
        content=f"## 📅 {year}年{month}月 第{start_w}-{end_w}周训练日历",
        elements=[calendar_element],
    ).send()


# ---- Google Calendar 同步回调 ----


@cl.action_callback("authorize_google_calendar")
async def on_authorize_google_calendar(action: cl.Action):
    await action.remove()

    from pathlib import Path

    from marathon_qa_assistant.core.app_state import GOOGLE_CREDENTIALS_PATH
    from marathon_qa_assistant.services.google_calendar_provider import GoogleCalendarProvider

    status_msg = cl.Message(content="⏳ 正在打开浏览器进行 Google 账号授权…")
    await status_msg.send()

    creds_path = Path(os.environ.get("GOOGLE_CREDENTIALS_PATH", str(GOOGLE_CREDENTIALS_PATH)))

    if not creds_path.exists():
        status_msg.content = (
            "❌ 未找到 Google 凭据文件。\n\n"
            "请先完成以下步骤：\n"
            "1. 前往 [Google Cloud Console](https://console.cloud.google.com) 创建 OAuth 2.0 桌面客户端 ID\n"
            "2. 下载凭据 JSON 文件并重命名为 `google_credentials.json`\n"
            f"3. 将其放到 `{GOOGLE_CREDENTIALS_PATH.parent}` 目录下\n"
            "4. 确保已设置环境变量 `MARATHON_SYNC_KEY`（加密密钥）"
        )
        await status_msg.update()
        return

    provider = GoogleCalendarProvider(creds_path)

    try:
        email = provider.authorize_interactive()
        status_msg.content = (
            f"✅ Google 日历授权成功！已绑定账号：**{email}**\n\n"
            "现在可以点击 **同步训练计划到日历** 将已生成的计划推送到 Google Calendar。"
        )
        await status_msg.update()
        _track_chainlit_event(
            "google_calendar_authorized",
            {"email": email},
        )
    except Exception as exc:
        status_msg.content = f"❌ 授权失败：{str(exc)}\n\n请重试。如果问题持续，请检查 Google Cloud Console 中的 OAuth 配置。"
        await status_msg.update()


@cl.action_callback("sync_to_google_calendar")
async def on_sync_to_google_calendar(action: cl.Action):
    await action.remove()

    from pathlib import Path

    from marathon_qa_assistant.core.app_state import GOOGLE_CREDENTIALS_PATH
    from marathon_qa_assistant.services.google_calendar_provider import (
        GoogleCalendarProvider,
        build_google_calendar_event,
    )
    from marathon_qa_assistant.services.database import get_db

    status_msg = cl.Message(content="⏳ 正在同步训练计划到 Google 日历…")
    await status_msg.send()

    creds_path = Path(os.environ.get("GOOGLE_CREDENTIALS_PATH", str(GOOGLE_CREDENTIALS_PATH)))

    if not creds_path.exists():
        await cl.Message(
            content="⚠️ 未找到 Google 凭据文件，请先点击 **授权 Google 日历** 完成设置。",
            actions=[
                cl.Action(
                    name="authorize_google_calendar",
                    payload={},
                    label="🔐 授权 Google 日历",
                )
            ],
        ).send()
        return

    provider = GoogleCalendarProvider(creds_path)

    if not provider.is_authorized():
        await cl.Message(
            content="⚠️ 尚未授权 Google 日历，请先点击下方按钮完成授权。",
            actions=[
                cl.Action(
                    name="authorize_google_calendar",
                    payload={},
                    label="🔐 授权 Google 日历",
                )
            ],
        ).send()
        return

    plan_id = action.payload.get("plan_id", "")
    db = get_db()
    events = db.get_unsynced_events(plan_id) if plan_id else []

    if not events:
        status_msg.content = "ℹ️ 没有需要同步的训练事件。请先生成训练计划。"
        await status_msg.update()
        return

    calendar_id = "primary"
    success_count = 0
    error_count = 0
    error_details: list = []

    for event_row in events:
        google_event = build_google_calendar_event(event_row)
        ics_uid = event_row.get("ics_uid", "")

        try:
            external_id = provider.push_event(calendar_id, google_event)
            db.update_event_sync_status(
                event_row["id"],
                external_event_id=external_id,
                sync_status="synced",
                provider="google",
            )
            success_count += 1
        except Exception as exc:
            error_count += 1
            detail = str(exc)[:120]
            error_details.append(f"- {event_row.get('title', '?')}: {detail}")
            db.update_event_sync_status(
                event_row["id"],
                sync_status="error",
                provider="google",
            )

    summary = f"## 📅 同步完成\n\n✅ 成功：**{success_count}** 个事件\n"
    if error_count:
        summary += f"❌ 失败：**{error_count}** 个事件\n"
        if error_details:
            summary += "\n### 错误详情\n" + "\n".join(error_details[:10])

    status_msg.content = summary
    await status_msg.update()

    _track_chainlit_event(
        "google_calendar_synced",
        {
            "success_count": success_count,
            "error_count": error_count,
            "plan_id": plan_id,
        },
    )


@cl.action_callback("revoke_google_calendar")
async def on_revoke_google_calendar(action: cl.Action):
    await action.remove()

    from pathlib import Path

    from marathon_qa_assistant.core.app_state import GOOGLE_CREDENTIALS_PATH
    from marathon_qa_assistant.services.google_calendar_provider import GoogleCalendarProvider

    creds_path = Path(os.environ.get("GOOGLE_CREDENTIALS_PATH", str(GOOGLE_CREDENTIALS_PATH)))
    provider = GoogleCalendarProvider(creds_path)
    provider.revoke()

    await cl.Message(content="✅ 已断开 Google 日历连接。授权令牌已清除。").send()


@cl.action_callback("browse_saved_plans")
async def on_browse_saved_plans(action: cl.Action):
    await action.remove()

    from marathon_qa_assistant.services.database import get_db
    from marathon_qa_assistant.apps.chainlit.plan_ui import build_calendar_props_from_db

    db = get_db()
    plans = db.list_training_plans()

    if not plans:
        await cl.Message(content="📭 暂未找到已保存的训练计划。请先生成一份训练计划。").send()
        return

    seen = set()
    deduped = []
    for plan in plans:
        weeks = plan.get("actual_weeks") or plan.get("requested_weeks") or "?"
        goal = plan.get("goal") or "训练计划"
        created = str(plan.get("created_at") or "")[:10]
        key = (goal, str(weeks), created)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(plan)

    plan_actions = []
    for plan in deduped:
        weeks = plan.get("actual_weeks") or plan.get("requested_weeks") or "?"
        goal = plan.get("goal") or "训练计划"
        created = str(plan.get("created_at") or "")[:10]
        label = f"📋 {goal}（{weeks}周）{created}"
        plan_actions.append(
            cl.Action(
                name="view_saved_plan",
                payload={"plan_id": plan["id"]},
                label=label,
            )
        )

    await cl.Message(
        content="## 📂 已保存的训练计划\n\n点击下方计划查看日历视图：",
        actions=plan_actions,
    ).send()


@cl.action_callback("view_saved_plan")
async def on_view_saved_plan(action: cl.Action):
    await action.remove()

    plan_id = action.payload.get("plan_id", "")
    if not plan_id:
        await cl.Message(content="❌ 无效的计划 ID。").send()
        return

    from marathon_qa_assistant.apps.chainlit.plan_ui import (
        build_calendar_props_from_db,
        build_calendar_props_with_explanations,
    )

    props = {}
    session_state = cl.user_session.get("state") or {}
    session_plan_id = str(session_state.get("training_plan_id") or "").strip()
    if session_plan_id and session_plan_id == plan_id:
        props = build_calendar_props_with_explanations(session_state)

    if not props:
        props = build_calendar_props_from_db(plan_id)

    if not props:
        await cl.Message(content="❌ 无法加载该计划，可能已被删除。").send()
        return

    calendar_element = cl.CustomElement(name="MonthlyTrainingCalendar", props=props)
    year = props.get("year", "")
    month = props.get("month", "")
    start_w = props.get("start_week_index", 1)
    end_w = props.get("end_week_index", 1)
    await cl.Message(
        content=f"## 📅 {year}年{month}月 第{start_w}-{end_w}周训练日历",
        elements=[calendar_element],
    ).send()
