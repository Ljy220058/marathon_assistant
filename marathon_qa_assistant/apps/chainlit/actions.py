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

@cl.action_callback("fill_profile")
async def on_fill_profile(action: cl.Action):
    try:
        await cl.Message(content="📋 **正在进入训练画像填写向导...**").send()
        cl.user_session.set("profile_step_message_id", None)
        cl.user_session.set("profile_step_field_key", None)
        cl.user_session.set("profile_current_step", None)
        cl.user_session.set("profile_step_actions", [])
        
        profile = await cl.make_async(load_user_profile)()
        selections = {}
        for k, v in profile.items():
            if k in FIELD_LABELS:
                if k in MULTI_VALUE_FIELDS:
                    selections[k] = _normalize_multi_selection(v, k)
                else:
                    selections[k] = v
        
        if not selections.get("pb_records"):
            pbs = []
            if profile.get("pb_5k"): pbs.append(f"5K {profile['pb_5k']}")
            if profile.get("pb_10k"): pbs.append(f"10K {profile['pb_10k']}")
            if profile.get("pb_half"): pbs.append(f"半马 {profile['pb_half']}")
            if profile.get("pb_full"): pbs.append(f"全马 {profile['pb_full']}")
            if pbs:
                selections["pb_records"] = ", ".join(pbs)
        
        selections = _normalize_profile_selections(selections)
        cl.user_session.set("profile_selections", selections)
        await _send_profile_step("experience_level", selections)
    except Exception as e:
        cl.logger.error(f"Error in on_fill_profile: {e}", exc_info=True)
        await cl.Message(content=f"❌ **无法启动画像向导**: {str(e)}").send()

@cl.action_callback("fill_field")
async def on_fill_field(action: cl.Action):
    field_key = action.payload.get("key", "")
    label = action.payload.get("label", field_key)
    hint = action.payload.get("hint", "")
    cl.user_session.set("filling_field_key", field_key)
    cl.user_session.set("filling_field_label", label)
    await cl.Message(content=f"请输入 **{label}**：\n_{hint}_\n\n> 请直接在下方输入框中回复，无需点击其他按钮。").send()

@cl.action_callback("cancel_fill")
async def on_cancel_fill(action: cl.Action):
    await action.remove()
    cl.user_session.set("pending_missing_fields", [])
    cl.user_session.set("filling_field_key", None)
    await cl.Message(content="✅ 已跳过画像填写，使用当前已有数据生成训练计划...").send()
    from marathon_qa_assistant.apps.chainlit.logic import process_message
    plan_query = cl.user_session.get("pending_plan_query", "请为我生成第一周训练计划")
    await process_message(cl.Message(content=f"【训练计划请求】用户画像可用。原始请求：{plan_query}"))

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
    await action.remove()
    profile = await cl.make_async(load_user_profile)()
    state = cl.user_session.get("state")
    state["user_profile"] = profile
    cl.user_session.set("state", state)
    from marathon_qa_assistant.apps.chainlit_app import show_profile_summary
    await show_profile_summary(profile)
    await update_sidebar()

@cl.action_callback("adaptive_plan")
async def on_adaptive_plan(action: cl.Action):
    await action.remove()
    cl.user_session.set("pending_operation", {"type": "adaptive_plan"})
    await cl.Message(content="📝 **请输入您的近期反馈**（例如：疲劳度、训练强度感受等）：\n\n> 在下方输入框回复后发送即可。").send()

@cl.action_callback("search_graph")
async def on_search_graph(action: cl.Action):
    await action.remove()
    cl.user_session.set("pending_operation", {"type": "search_graph"})
    await cl.Message(content="🔍 **请输入您想在图谱中搜索的实体名称**（如：VO2Max, HIIT）：\n\n> 在下方输入框回复后发送即可。").send()

@cl.action_callback("cross_research")
async def on_cross_research(action: cl.Action):
    await action.remove()
    cl.user_session.set("pending_operation", {"type": "cross_research"})
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
        if k in ("weekly_mileage", "vo2max", "max_session_minutes"):
            try: profile[k] = int(v) if isinstance(v, str) and v.strip().isdigit() else v
            except (ValueError, TypeError): profile[k] = v
        else: profile[k] = v
    await cl.make_async(save_user_profile)(profile)
    state = cl.user_session.get("state")
    if state:
        state["user_profile"] = profile
        cl.user_session.set("state", state)
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
    await cl.Message(content="正在生成你的专属周训练计划...").send()
    from marathon_qa_assistant.apps.chainlit.logic import process_message
    await process_message(cl.Message(content="请为我生成第一周训练计划"))

@cl.action_callback("profile_reset")
async def on_profile_reset(action: cl.Action):
    if not _is_active_profile_step_action(action, "__confirm__"): return
    await action.remove()
    cl.user_session.set("profile_selections", {})
    cl.user_session.set("profile_current_step", None)
    await _send_profile_step("experience_level", {})
