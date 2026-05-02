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
from marathon_qa_assistant.apps.chainlit.wizard_logic import (
    _send_profile_step, _next_field
)

# 尝试导入可选模块
try:
    from marathon_qa_assistant.services.multimodal import multimodal_service as mm_module
except ImportError:
    mm_module = None

async def process_message(message: cl.Message):
    """处理用户消息的核心逻辑"""
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
        value = message.content.strip()
        profile = await cl.make_async(load_user_profile)()
        if filling_key in ("weekly_mileage", "vo2max", "max_session_minutes"):
            try: profile[filling_key] = int(value) if value.strip().isdigit() else value
            except: profile[filling_key] = value
        else: profile[filling_key] = value
        await cl.make_async(save_user_profile)(profile)
        state["user_profile"] = profile
        await update_sidebar(profile)
        cl.user_session.set("filling_field_key", None)
        pending = cl.user_session.get("pending_missing_fields", [])
        pending = [k for k in pending if k != filling_key]
        cl.user_session.set("pending_missing_fields", pending)
        if pending:
            actions = [cl.Action(name="fill_field", payload={"key": k, "label": FIELD_LABELS.get(k, k), "hint": FIELD_HINTS.get(k, "")}, label=f"📝 填写 {FIELD_LABELS.get(k, k)}") for k in pending]
            actions.append(cl.Action(name="cancel_fill", payload={}, label="跳过，直接生成", icon="skip_next"))
            await cl.Message(content=f"✅ **{filling_label}** 已保存！剩余 **{len(pending)}** 项：", actions=actions).send()
        else:
            await cl.Message(content="✅ **所有训练画像信息已收集完毕！正在生成你的周训练计划...**").send()
            plan_query = cl.user_session.get("pending_plan_query", "请为我生成第一周训练计划")
            await process_message(cl.Message(content=f"【训练计划请求】用户画像已完善。原始请求：{plan_query}"))
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
            return
        elif op_type == "adaptive_plan":
            cl.user_session.set("pending_operation", None)
            await process_message(cl.Message(content=f"【自适应调整】用户反馈：{message.content.strip()}。请根据此反馈调整我的训练计划。"))
            return
        elif op_type == "cross_research":
            entities = [e.strip() for e in message.content.strip().split(",") if e.strip()]
            cl.user_session.set("pending_operation", None)
            await process_message(cl.Message(content=f"【交叉研究】请深入分析以下实体之间的科学关联：{', '.join(entities)}。"))
            return
        elif op_type == "search_graph":
            entity = message.content.strip()
            cl.user_session.set("pending_operation", None)
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
    state["reasoning_log"] = []
    
    msg = cl.Message(content="")
    await msg.send()
    
    active_node = None
    final_state = state.copy()
    printed_logs = set()

    try:
        async for event in integrated_app.astream_events(state, version="v2"):
            kind = event["event"]
            name = event.get("name", "")
            if kind == "on_chain_start":
                active_node = name
                if name in ["coach", "auditor", "formatter", "router", "planner"]:
                    await cl.Message(content=f"⚙️ 正在执行 `{name}` 节点...").send()
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
        intent_type = final_state.get("intent_type", "")
        missing_fields = final_state.get("missing_fields", [])
        final_report = final_state.get("final_report", "")
        
        if intent_type == "plan" and final_report == "__FILL_FIELDS__" and missing_fields:
            profile = await cl.make_async(load_user_profile)()
            still_missing = [k for k in missing_fields if not profile.get(k)]
            if still_missing:
                cl.user_session.set("pending_missing_fields", still_missing)
                cl.user_session.set("pending_plan_query", message.content)
                actions = [cl.Action(name="fill_field", payload={"key": k, "label": FIELD_LABELS.get(k, k), "hint": FIELD_HINTS.get(k, "")}, label=f"📝 填写 {FIELD_LABELS.get(k, k)}") for k in still_missing]
                actions.append(cl.Action(name="cancel_fill", payload={}, label="跳过，直接生成", icon="skip_next"))
                await cl.Message(content=f"## 📋 请补充训练画像\n\n还需要以下 **{len(still_missing)}** 项信息，请逐一点击填写：", actions=actions).send()
                msg.content = ""
                await msg.update()
                return
        
        report_html = UIHelper.render_structured_report(final_state.get("structured_report"), final_state.get("final_report"), include_sources=True)
        wiki_panel_md = UIHelper.render_chainlit_wiki_context_md(final_state.get("structured_report"))
        preview_bundle = UIHelper.build_evidence_preview_bundle(final_state.get("structured_report"), final_state.get("final_report"))
        msg.content = report_html
        await msg.update()

        if wiki_panel_md:
            await cl.Message(content=wiki_panel_md).send()

        if preview_bundle.get("panel_md") and preview_bundle.get("actions"):
            preview_actions = [cl.Action(name=spec["name"], payload=spec["payload"], label=spec["label"], icon="visibility") for spec in preview_bundle["actions"]]
            await cl.Message(content=preview_bundle["panel_md"], actions=preview_actions).send()
            
        usage = final_state.get("token_usage", {})
        await cl.Message(content=UIHelper.generate_token_md({"Total": usage.get("total_tokens", 0)}, roi_score=final_state.get("audit_scores", {}).get("roi", 0))).send()
        
        if final_state.get("guided_questions"):
            actions = [cl.Action(name="ask_q", payload={"v": q}, label=q) for q in final_state["guided_questions"]]
            await cl.Message(content="💡 **您可以接着问：**", actions=actions).send()

        if final_state.get("mode") != "adaptive":
            if any(kw in message.content.strip() for kw in FEEDBACK_INDICATORS):
                await cl.Message(content="💪 **需要我根据以上建议帮你调整训练计划吗？**", actions=[cl.Action(name="adaptive_plan", payload={}, label="🔁 基于此建议调整我的训练计划")]).send()

    except Exception as e: await cl.Message(content=f"❌ **运行出错**: {str(e)}").send()
