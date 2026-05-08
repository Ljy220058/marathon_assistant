import os
import asyncio
import time
import shutil
import chainlit as cl
from marathon_qa_assistant.core.workflow import (
    integrated_app, 
    load_user_profile, 
    save_user_profile,
)
from marathon_qa_assistant.services.analytics import (
    build_plan_click_properties,
    get_or_create_session_id,
    track_event,
)
from marathon_qa_assistant.services.database import get_db
from marathon_qa_assistant.ui.legacy_ui import UIHelper
from marathon_qa_assistant.core.app_state import (
    check_ollama_status,
    UPLOAD_DOCS_DIR,
)
from marathon_qa_assistant.services.input_validator import (
    validate_file,
    validate_pasted_text,
    save_pasted_text
)
from marathon_qa_assistant.nodes.profile_and_retrieval import FIELD_LABELS, FIELD_HINTS

from marathon_qa_assistant.apps.chainlit.ui_config import FEEDBACK_INDICATORS
from marathon_qa_assistant.apps.chainlit.setup import (
    update_sidebar, graph_engine
)
from marathon_qa_assistant.apps.chainlit.plan_ui import (
    build_training_feedback_bundle,
    build_adaptive_adjustment_card,
    build_training_explanation_card,
    extract_adaptive_adjustment_context,
    extract_entry_status_context,
    extract_first_week_execution_context,
    extract_phase_overview_context,
    extract_training_explanation_context,
    render_adaptive_adjustment_card_md,
    render_plan_retry_md,
    render_training_feedback_card_md,
    extract_current_week_context,
    build_entry_status_bar_props,
    build_week_training_card_props,
    build_explanation_drawer_props,
    build_calendar_props_with_explanations,
    render_minimal_plan_summary_md,
)
from marathon_qa_assistant.apps.chainlit.coach_state import sync_coach_ui_snapshot
from marathon_qa_assistant.apps.chainlit.wizard_logic import (
    _send_profile_step, _next_field
)

# 尝试导入可选模块
try:
    from marathon_qa_assistant.services.multimodal import multimodal_service as mm_module
except ImportError:
    mm_module = None


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


def _persist_training_plan_if_ready(final_state: dict, source_query: str) -> str:
    structured_plan = final_state.get("structured_training_plan")
    if not isinstance(structured_plan, dict) or not structured_plan.get("week_plans"):
        return ""
    existing_plan_id = str(final_state.get("training_plan_id") or "").strip()
    if existing_plan_id:
        return existing_plan_id
    plan_id = get_db().save_training_plan(structured_plan, source_query=source_query)
    final_state["training_plan_id"] = plan_id
    return plan_id


async def _send_saved_plan_browse_action(plan_id: str):
    if not plan_id:
        return
    await cl.Message(
        content="📅 **训练计划已保存到本地日历表。** 你可以随时查看已保存的训练计划。",
        actions=[
            cl.Action(name="browse_saved_plans", payload={}, label="📂 查看已保存计划"),
        ],
    ).send()


async def process_message(message: cl.Message, *, plan_click_entry: str | None = None):
    """处理用户消息的核心逻辑"""
    def sync_ui_state(session_state_override=None):
        current_state = session_state_override
        if current_state is None:
            current_state = cl.user_session.get("state") or {}
        return sync_coach_ui_snapshot(cl.user_session.get, cl.user_session.set, current_state)

    cl.user_session.set("last_user_query", message.content)

    # 1. 处理上传的文件与图片
    image_descriptions = []
    image_suffixes = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif')
    if message.elements:
        UPLOAD_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        saved_files = []
        
        async def process_image(element, file_path=None):
            actual_path = file_path or element.path
            if not element.name.lower().endswith(image_suffixes):
                return None
                
            msg_ocr = cl.Message(content=f"🖼️ **检测到图片 `{element.name}`，正在执行 OCR 文本提取...**")
            await msg_ocr.send()
            progress = {"phase": "初始化中", "last_info": "正在准备 OCR 任务..."}
            start_time = time.monotonic()
            stop_heartbeat = asyncio.Event()

            def build_ocr_status() -> str:
                elapsed = int(time.monotonic() - start_time)
                return (f"🖼️ **图片 `{element.name}` OCR 处理中**\n- 阶段: `{progress['phase']}`\n- 已等待: `{elapsed}s`\n- 状态: {progress['last_info']}")

            async def heartbeat():
                while not stop_heartbeat.is_set():
                    msg_ocr.content = build_ocr_status()
                    await msg_ocr.update()
                    try: await asyncio.wait_for(stop_heartbeat.wait(), timeout=3)
                    except asyncio.TimeoutError:
                        progress["phase"] = "OCR 识别中"
                        progress["last_info"] = "正在进行本地 OCR 提字，请耐心等待..."
            
            async def ocr_log_callback(info: str):
                clean_info = info.split(", 图片路径:")[0] if ", 图片路径:" in info else info
                if "正在执行本地 OCR" in clean_info: progress["phase"] = "OCR 识别中"
                elif "识别成功" in clean_info: progress["phase"] = "结果整理中"
                else: progress["phase"] = "任务执行中"
                progress["last_info"] = clean_info
                msg_ocr.content = build_ocr_status()
                await msg_ocr.update()

            heartbeat_task = asyncio.create_task(heartbeat())
            try:
                desc = await mm_module.smart_analyze_image(actual_path, log_callback=ocr_log_callback)
                stop_heartbeat.set()
                await heartbeat_task
                total_elapsed = int(time.monotonic() - start_time)
                if "错误" in desc:
                    msg_ocr.content = f"⚠️ 图片 `{element.name}` OCR 失败（耗时 `{total_elapsed}s`）: {desc}"
                    await msg_ocr.update()
                    return None
                else:
                    msg_ocr.content = f"✅ **图片文本提取完成** (⚡ OCR, 耗时 `{total_elapsed}s`): {desc[:100]}..."
                    await msg_ocr.update()
                    return f"【图片内容: {element.name}】\n{desc}"
            except Exception as e:
                stop_heartbeat.set()
                await heartbeat_task
                msg_ocr.content = f"⚠️ 图片 `{element.name}` OCR 异常。"
                await msg_ocr.update()
                return None

        tasks = []
        for element in message.elements:
            if isinstance(element, (cl.File, cl.Image)):
                target_path = UPLOAD_DOCS_DIR / element.name
                if element.path and os.path.exists(element.path):
                    validation = validate_file(element.path)
                    if not validation.get("valid"):
                        await cl.Message(content=f"⚠️ **文件 `{element.name}` 校验未通过**: {'; '.join(validation.get('errors', []))}").send()
                        continue
                    try:
                        shutil.copy(element.path, target_path)
                        saved_files.append(element.name)
                    except Exception as e:
                        cl.logger.error(f"复制文件失败: {e}")
                
                if element.name.lower().endswith(image_suffixes) and target_path.exists():
                    tasks.append(process_image(element, str(target_path)))
        
        if tasks:
            results = await asyncio.gather(*tasks)
            image_descriptions = [r for r in results if r]
        
        if saved_files:
            other_files = [f for f in saved_files if not f.lower().endswith(image_suffixes)]
            if other_files:
                await cl.Message(content=f"✅ **检测到上传文件并保存到知识库：**\n- " + "\n- ".join(other_files)).send()
            
            pdf_files = [f for f in saved_files if f.lower().endswith('.pdf')]
            if pdf_files:
                actions = [
                    cl.Action(name="extract_pdf_visuals", payload={"path": str((UPLOAD_DOCS_DIR / pdf_files[0]).absolute()), "name": pdf_files[0]}, label="🧾 提取 PDF 图片文字", icon="auto_awesome"),
                    cl.Action(name="reindex_kb", payload={"value": "reindex"}, label="构建索引", icon="build")
                ]
                await cl.Message(content="检测到 PDF，是否提取其中图片/扫描页的文字？", actions=actions).send()

    if not message.content.strip() and image_descriptions:
        await cl.Message(content="\n\n---\n\n".join(image_descriptions)).send()
        return

    if not message.content.strip() and message.elements:
        return

    if not await check_ollama_status():
        await cl.Message(content="❌ **Ollama 服务未在线**，请确保本地 11434 端口服务已启动。").send()
        return

    state = cl.user_session.get("state")
    if state.get("final_report"):
        state["history"].append({"role": "assistant", "content": state["final_report"]})

    # 处理画像自定义字段填写
    profile_custom_key = cl.user_session.get("profile_custom_field_key")
    if profile_custom_key:
        profile_custom_label = cl.user_session.get("profile_custom_field_label", profile_custom_key)
        value = message.content.strip()
        selections = cl.user_session.get("profile_selections", {})
        cl.user_session.set("profile_custom_field_key", None)
        if value:
            selections[profile_custom_key] = value
            cl.user_session.set("profile_selections", selections)
            await cl.Message(content=f"✅ 已填写 **{profile_custom_label}**: {value}").send()
            next_f = _next_field(profile_custom_key)
            await _send_profile_step(next_f or "__confirm__", selections)
        else:
            await cl.Message(content=f"⚠️ **{profile_custom_label}** 未填写，已停留在当前步骤，请重新选择或输入。").send()
            await _send_profile_step(profile_custom_key, selections)
        return

    # 处理缺失信息填写
    filling_key = cl.user_session.get("filling_field_key")
    if filling_key:
        filling_label = cl.user_session.get("filling_field_label", filling_key)
        filling_mode = cl.user_session.get("filling_field_mode", "required")
        value = message.content.strip()
        profile = await cl.make_async(load_user_profile)()
        if filling_key in ("weekly_mileage", "vo2max", "max_session_minutes", "lthr"):
            try: profile[filling_key] = int(value) if value.strip().isdigit() else value
            except: profile[filling_key] = value
        else: profile[filling_key] = value
        await cl.make_async(save_user_profile)(profile)
        state["user_profile"] = profile
        cl.user_session.set("state", state)
        await update_sidebar(profile)
        cl.user_session.set("filling_field_key", None)
        cl.user_session.set("filling_field_mode", None)
        pending_key = "pending_enhancement_fields" if filling_mode == "enhancement" else "pending_missing_fields"
        pending = cl.user_session.get(pending_key, [])
        pending = [k for k in pending if k != filling_key]
        cl.user_session.set(pending_key, pending)
        if pending:
            actions = [
                cl.Action(
                    name="fill_field",
                    payload={"key": k, "label": FIELD_LABELS.get(k, k), "hint": FIELD_HINTS.get(k, ""), "mode": filling_mode},
                    label=f"📝 填写 {FIELD_LABELS.get(k, k)}"
                )
                for k in pending
            ]
            if filling_mode == "enhancement":
                actions.append(cl.Action(name="fill_advanced_profile", payload={"start_field": pending[0]}, label="📋 补全高级画像"))
                actions.append(cl.Action(name="regen_plan_from_profile", payload={}, label="🔄 立即重生成计划"))
                await cl.Message(content=f"✅ **{filling_label}** 已保存！\n\n还剩 **{len(pending)}** 项高级画像可继续补充。当前基础计划会保留在消息历史中；你可以继续点字段补充，也可以直接点「立即重生成计划」。", actions=actions).send()
            else:
                actions.append(cl.Action(name="fill_profile", payload={"value": "profile"}, label="📋 打开完整画像向导"))
                await cl.Message(content=f"✅ **{filling_label}** 已保存！\n\n还剩 **{len(pending)}** 项基础信息。请继续点击字段补充；基础字段补齐后系统会自动生成基础训练计划。", actions=actions).send()
        else:
            if filling_mode == "enhancement":
                actions = [cl.Action(name="regen_plan_from_profile", payload={}, label="🔄 基于最新画像重生成计划")]
                await cl.Message(content="✅ **本轮高级画像补充已完成！** 你可以继续浏览当前计划，或基于最新画像重新生成更精准的版本。", actions=actions).send()
            else:
                await cl.Message(content="✅ **基础画像已齐备！正在生成你的基础训练计划...**\n\n后续你仍可补充 LTHR、T-Pace、VO₂max 等高级画像来提升精度。").send()
                plan_query = cl.user_session.get("pending_plan_query", "请为我生成第一周训练计划")
                sync_ui_state(state)
                await update_sidebar(profile)
                await process_message(
                    cl.Message(content=f"【训练计划请求】用户画像已完善。原始请求：{plan_query}"),
                    plan_click_entry=None,
                )
                return
        sync_ui_state(state)
        await update_sidebar(profile)
        return
    
    # 处理挂起的异步操作
    pending_op = cl.user_session.get("pending_operation")
    if pending_op:
        op_type = pending_op.get("type", "")
        if op_type == "paste_text":
            text = message.content.strip()
            validation = validate_pasted_text(text)
            if not validation.get("valid"):
                await cl.Message(content=f"⚠️ **文本无效**: {'; '.join(validation.get('errors', []))}").send()
            else:
                file_path = save_pasted_text(text, UPLOAD_DOCS_DIR)
                if file_path:
                    await cl.Message(content=f"✅ **已保存文本到知识库**: `{file_path.name}`").send()
                    actions = [cl.Action(name="reindex_kb", payload={"value": "reindex"}, label="立即构建索引", icon="build"), cl.Action(name="build_graph_ai", payload={"mode": "full"}, label="全量重构图谱（推荐）", icon="refresh")]
                    await cl.Message(content="现在要构建索引或更新图谱吗？", actions=actions).send()
                else: await cl.Message(content="⚠️ **保存失败，请重试。**").send()
            cl.user_session.set("pending_operation", None)
            sync_ui_state(state)
            await update_sidebar()
            return
        elif op_type == "adaptive_plan":
            cl.user_session.set("pending_operation", None)
            sync_ui_state(state)
            await update_sidebar()
            await process_message(
                cl.Message(content=f"【自适应调整】用户反馈：{message.content.strip()}。请根据此反馈调整我的训练计划。"),
                plan_click_entry=None,
            )
            return
        elif op_type == "training_feedback":
            context = cl.user_session.get("first_week_execution_context") or extract_first_week_execution_context(state or {})
            cl.user_session.set("pending_operation", None)
            if not context:
                sync_ui_state(state)
                await update_sidebar()
                await cl.Message(content="⚠️ 当前会话里还没有可用于反馈的首周训练内容，请先生成并进入首周执行。").send()
                return

            bundle = build_training_feedback_bundle(
                context,
                raw_text=message.content.strip(),
                default_completed=bool(pending_op.get("completed", True)),
            )
            _track_chainlit_event(
                "workout_feedback_submitted",
                {
                    "entry": "free_text",
                    "source_type": "text",
                    "completed": bool(pending_op.get("completed", True)),
                    "completion_status": bundle["workout_feedback"].get("completion_status"),
                    "feedback_length": len(message.content.strip()),
                    "has_keywords": bool(bundle["workout_feedback"].get("notes")),
                },
            )
            state["adaptive_feedback"] = bundle["adaptive_feedback"]
            state["adaptive_adjustment"] = bundle["adaptive_adjustment"]
            cl.user_session.set("state", state)
            cl.user_session.set("latest_training_feedback_card", bundle["card"])
            cl.user_session.set("latest_workout_feedback", bundle["workout_feedback"])
            sync_ui_state(state)
            await update_sidebar()
            await cl.Message(content="✅ **训练反馈已提交。** 系统已写入当前会话状态，可直接供后续自适应调整链路消费。").send()
            await cl.Message(content=render_training_feedback_card_md(bundle["card"])).send()
            return
        elif op_type == "cross_research":
            entities = [e.strip() for e in message.content.strip().split(",") if e.strip()]
            cl.user_session.set("pending_operation", None)
            sync_ui_state(state)
            await update_sidebar()
            await process_message(
                cl.Message(content=f"【交叉研究】请深入分析以下实体之间的科学关联：{', '.join(entities)}。"),
                plan_click_entry=None,
            )
            return
        elif op_type == "search_graph":
            entity = message.content.strip()
            cl.user_session.set("pending_operation", None)
            sync_ui_state(state)
            await update_sidebar()
            status_msg = cl.Message(content=f"🔍 **正在图谱中搜索 `{entity}` 并生成知识卡片...**")
            await status_msg.send()
            try:
                result = graph_engine.search_graph([entity])
                if not result["nodes"]:
                    await cl.Message(content=f"### 🔍 `{entity}` 未找到\n\n知识图谱中暂无与 **{entity}** 相关的实体。").send()
                    return
                from marathon_qa_assistant.apps.chainlit.setup import _generate_knowledge_card
                card_md = await _generate_knowledge_card(entity, result)
                await cl.Message(content=card_md).send()
                actions = [cl.Action(name="cross_research", payload={"value": "research"}, label="🔬 交叉研究此实体"), cl.Action(name="search_graph", payload={"value": "search"}, label="🔍 搜索其他实体")]
                await cl.Message(content="接下来想做什么？", actions=actions).send()
            except Exception as e: await cl.Message(content=f"❌ **图谱搜索失败**: {str(e)}").send()
            return

    # 执行主工作流
    state["query"] = message.content
    if image_descriptions: state["query"] = "\n\n".join(image_descriptions) + f"\n\n**用户问题**: {message.content}"
    state["history"].append({"role": "user", "content": message.content})
    state["final_report"] = ""
    state["missing_info_status"] = ""
    state["reasoning_log"] = []
    plan_click_properties = build_plan_click_properties(
        entry=plan_click_entry,
        message_text=message.content,
        has_image_context=bool(image_descriptions),
    )
    if plan_click_properties:
        _track_chainlit_event(
            "plan_generate_clicked",
            plan_click_properties,
        )
    cl.user_session.set("workflow_running", True)
    cl.user_session.set("last_error", None)
    sync_ui_state(state)
    await update_sidebar()
    
    msg = cl.Message(content="")
    await msg.send()
    
    active_node = None
    final_state = state.copy()
    printed_logs = set()

    node_names_seen: set = set()
    try:
        async for event in integrated_app.astream_events(state, version="v2"):
            kind = event["event"]
            name = event.get("name", "")
            if kind == "on_chain_start":
                active_node = name
                if name in ["coach", "auditor", "formatter", "router", "planner", "executor"]:
                    node_names_seen.add(name)
            elif kind == "on_chat_model_stream":
                if active_node in ["coach", "research_analyst", "formatter", "missing_info_handler"]:
                    content = event["data"]["chunk"].content
                    if content and "__FILL_FIELDS__" not in content: await msg.stream_token(content)
            elif kind == "on_chain_end":
                output = event["data"].get("output", {})
                if isinstance(output, dict):
                    final_state.update(output)
                    if "reasoning_log" in output:
                        for log in output["reasoning_log"]:
                            if log not in printed_logs:
                                printed_logs.add(log)
                                await cl.Message(content=f"📝 `{log}`").send()

        cl.user_session.set("state", final_state)
        cl.user_session.set("workflow_running", False)
        cl.user_session.set("last_error", None)
        intent_type = final_state.get("intent_type", "")
        missing_fields = final_state.get("missing_fields", [])
        final_report = final_state.get("final_report", "")
        missing_info_status = final_state.get("missing_info_status", "")
        if intent_type == "plan":
            cl.user_session.set("last_plan_query", message.content)
            _track_chainlit_event(
                "plan_generated",
                {
                    "missing_info_status": missing_info_status,
                    "has_final_report": bool(str(final_report or "").strip()),
                    "final_report_length": len(str(final_report or "")),
                    "has_structured_training_plan": bool(final_state.get("structured_training_plan")),
                    "plan_type": (
                        (final_state.get("structured_training_plan") or {}).get("plan_meta", {}).get("plan_type")
                        if isinstance(final_state.get("structured_training_plan"), dict)
                        else None
                    ),
                    "actual_weeks": (
                        (final_state.get("structured_training_plan") or {}).get("plan_meta", {}).get("actual_weeks")
                        if isinstance(final_state.get("structured_training_plan"), dict)
                        else None
                    ),
                    "rag_source_count": len(final_state.get("rag_sources") or []),
                    "has_training_explanation_panel": bool(
                        isinstance(final_state.get("structured_report"), dict)
                        and final_state.get("structured_report", {}).get("training_explanation_panel")
                    ),
                },
            )
        
        if intent_type == "plan" and missing_info_status == "awaiting_profile" and missing_fields:
            profile = await cl.make_async(load_user_profile)()
            still_missing = [k for k in missing_fields if not profile.get(k)]
            if still_missing:
                cl.user_session.set("pending_missing_fields", still_missing)
                cl.user_session.set("pending_plan_query", message.content)
                actions = [
                    cl.Action(
                        name="fill_field",
                        payload={"key": k, "label": FIELD_LABELS.get(k, k), "hint": FIELD_HINTS.get(k, ""), "mode": "required"},
                        label=f"📝 填写 {FIELD_LABELS.get(k, k)}"
                    )
                    for k in still_missing
                ]
                actions.append(cl.Action(name="fill_profile", payload={"value": "profile"}, label="📋 打开完整画像向导"))
                await cl.Message(
                    content=(
                        "## 📋 请补充基础训练画像\n\n"
                        "当前还缺少下面这些**最小必要字段**。请点击任一字段按钮补充；"
                        "补齐后系统会自动继续生成基础训练计划，不需要重新输入原始需求。\n\n"
                        "LTHR、T-Pace、VO₂max 等高级字段可以在基础计划生成后再补，不会阻塞首次生成。"
                    ),
                    actions=actions
                ).send()
                sync_ui_state(final_state)
                await update_sidebar()
                msg.content = ""
                await msg.update()
                return
        
        report_html = UIHelper.render_structured_report(final_state.get("structured_report"), final_state.get("final_report"), include_sources=True)
        adaptive_context = extract_adaptive_adjustment_context(final_state)
        first_week_context = extract_first_week_execution_context(final_state) if intent_type == "plan" else {}
        has_renderable_plan = bool(first_week_context or str(final_report or "").strip())
        phase_overview_context = extract_phase_overview_context(final_state) if intent_type == "plan" else {}
        persisted_plan_id = ""
        if intent_type == "plan" and missing_info_status != "awaiting_profile":
            persisted_plan_id = _persist_training_plan_if_ready(final_state, message.content)
        if intent_type == "plan" and phase_overview_context:
            cl.user_session.set("full_plan_final_state", final_state.copy())
            cl.user_session.set("full_plan_report_html", report_html)
        if intent_type == "plan" and not has_renderable_plan:
            retry_query = cl.user_session.get("pending_plan_query") or message.content
            await cl.Message(
                content=render_plan_retry_md(retry_query),
                actions=[
                    cl.Action(name="retry_plan_generation", payload={"query": retry_query}, label="🔄 重试计划生成"),
                    cl.Action(name="fill_profile", payload={"value": "profile"}, label="📋 检查训练画像"),
                ],
            ).send()
            sync_ui_state(final_state)
            await update_sidebar()
            msg.content = ""
            await msg.update()
            return
        wiki_panel_md = UIHelper.render_chainlit_wiki_context_md(final_state.get("structured_report"))
        preview_bundle = UIHelper.build_evidence_preview_bundle(final_state.get("structured_report"), final_state.get("final_report"))
        if intent_type == "plan":
            msg.content = render_minimal_plan_summary_md(final_state)
        else:
            msg.content = report_html
        await msg.update()

        if intent_type == "plan":
            overview_elements = []
            entry_status_props = build_entry_status_bar_props(extract_entry_status_context(final_state))
            if entry_status_props:
                overview_elements.append(cl.CustomElement(name="EntryStatusBar", props=entry_status_props))

            week_card_props = build_week_training_card_props(extract_current_week_context(final_state))
            if week_card_props:
                overview_elements.append(cl.CustomElement(name="WeekTrainingCard", props=week_card_props))

            explanation_context = extract_training_explanation_context(final_state)
            explanation_card = build_training_explanation_card(explanation_context)
            explanation_props = build_explanation_drawer_props(explanation_card)
            if explanation_props and explanation_card.get("items"):
                overview_elements.append(cl.CustomElement(name="ExplanationDrawer", props=explanation_props))

            if overview_elements:
                await cl.Message(
                    content="",
                    elements=overview_elements,
                ).send()

            calendar_props = build_calendar_props_with_explanations(final_state)
            if calendar_props:
                calendar_element = cl.CustomElement(name="MonthlyTrainingCalendar", props=calendar_props)
                await cl.Message(
                    content="",
                    elements=[calendar_element],
                ).send()

        if adaptive_context:
            adaptive_card = build_adaptive_adjustment_card(adaptive_context)
            cl.user_session.set("latest_adaptive_adjustment_card", adaptive_card)
            _track_chainlit_event(
                "adaptive_plan_generated",
                {
                    "entry": "adaptive_context",
                    "has_adjustment_summary": bool(adaptive_card.get("summary")),
                    "has_recommendations": bool(adaptive_card.get("recommendations")),
                    "recommendation_count": len(adaptive_card.get("recommendations") or []),
                    "has_training_feedback": bool(final_state.get("adaptive_feedback")),
                },
            )
            adaptive_actions = [
                cl.Action(name="adaptive_plan", payload={}, label="📝 继续补充训练反馈")
            ]
            await cl.Message(
                content=render_adaptive_adjustment_card_md(adaptive_card),
                actions=adaptive_actions,
            ).send()

        if intent_type == "plan" and first_week_context:
            plan_actions = [cl.Action(name="start_first_week", payload={"week_index": 1}, label="🚀 开始第1周训练")]
            if persisted_plan_id:
                plan_actions.append(
                    cl.Action(name="view_saved_plan", payload={"plan_id": persisted_plan_id}, label="📅 查看训练日历"),
                )
            await cl.Message(
                content="",
                actions=plan_actions,
            ).send()

        enhancement_missing = final_state.get("enhancement_missing_fields", [])
        if intent_type == "plan" and enhancement_missing and missing_info_status != "awaiting_profile":
            cl.user_session.set("pending_enhancement_fields", enhancement_missing)
            cl.user_session.set("pending_plan_query", message.content)
            from marathon_qa_assistant.nodes.profile_and_retrieval import ENHANCEMENT_FIELD_LABELS
            labels = [ENHANCEMENT_FIELD_LABELS.get(k, k) for k in enhancement_missing]
            actions = []
            for k in enhancement_missing[:5]:
                actions.append(cl.Action(
                    name="fill_field",
                    payload={"key": k, "label": FIELD_LABELS.get(k, k), "hint": FIELD_HINTS.get(k, ""), "mode": "enhancement"},
                    label=f"📝 填写 {FIELD_LABELS.get(k, k)}"
                ))
            actions.append(cl.Action(name="fill_advanced_profile", payload={"start_field": enhancement_missing[0]}, label="📋 补全高级画像"))
            if actions:
                await cl.Message(
                    content=(
                        "💡 **当前已先为你生成基础计划。**\n\n"
                        "你可以先阅读和演示当前计划；如果继续补充以下高级画像，系统可以进一步提升配速、强度和周期对齐精度。\n\n"
                        + "\n".join(f"- {l}" for l in labels[:5])
                        + "\n\n👉 **下一步**：点击单个字段快速补充，或点击「补全高级画像」进入连续向导。"
                    ),
                    actions=actions
                ).send()

        if wiki_panel_md:
            await cl.Message(content=wiki_panel_md).send()

        if preview_bundle.get("panel_md"):
            preview_actions = [
                cl.Action(name=spec["name"], payload=spec["payload"], label=spec["label"], icon="visibility")
                for spec in preview_bundle.get("actions", [])
            ]
            await cl.Message(content=preview_bundle["panel_md"], actions=preview_actions or None).send()
            
        if final_state.get("guided_questions"):
            actions = [cl.Action(name="ask_q", payload={"v": q}, label=q) for q in final_state["guided_questions"]]
            await cl.Message(content="💡 **您可以接着问：**", actions=actions).send()

        if final_state.get("mode") != "adaptive":
            if any(kw in message.content.strip() for kw in FEEDBACK_INDICATORS):
                await cl.Message(content="💪 **需要我根据以上建议帮你调整训练计划吗？**", actions=[cl.Action(name="adaptive_plan", payload={}, label="🔁 基于此建议调整我的训练计划")]).send()

        sync_ui_state(final_state)
        await update_sidebar()

    except Exception as e:
        cl.user_session.set("workflow_running", False)
        cl.user_session.set("last_error", str(e))
        sync_ui_state(final_state)
        await update_sidebar()
        retry_query = cl.user_session.get("pending_plan_query") or message.content
        if cl.user_session.get("chat_profile") == "Coach Mode":
            await cl.Message(
                content=render_plan_retry_md(retry_query, str(e)),
                actions=[
                    cl.Action(name="retry_plan_generation", payload={"query": retry_query}, label="🔄 重试计划生成"),
                    cl.Action(name="fill_profile", payload={"value": "profile"}, label="📋 检查训练画像"),
                ],
            ).send()
            return
        await cl.Message(content=f"❌ **运行出错**: {str(e)}").send()
