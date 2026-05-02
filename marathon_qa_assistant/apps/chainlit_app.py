import os
import sys
import asyncio
import json
import shutil
from pathlib import Path
from datetime import datetime, date

import chainlit as cl

# 将项目根目录添加到 sys.path 以支持包导入
current_file = Path(__file__).absolute()
# 假设结构为 marathon_qa_assistant/apps/chainlit_app.py
# 根目录应该是 parents[2]
_TMP_BASE = current_file.parents[2]
if str(_TMP_BASE) not in sys.path:
    sys.path.insert(0, str(_TMP_BASE))

from marathon_qa_assistant.core.workflow import (
    integrated_app, 
    load_user_profile, 
    save_user_profile,
    IntegratedState, 
    set_kb_data, 
    KB_CHUNKS
)
from marathon_qa_assistant.ui.legacy_ui import UIHelper
from marathon_qa_assistant.core.app_state import (
    check_ollama_status,
    DEFAULT_VECTOR_DIR,
    UPLOAD_DOCS_DIR,
    USER_VECTOR_DIR,
    BASE_DIR,
    get_preferred_vector_dir,
    global_state
)

# 尝试导入可选模块，如果失败则使用 fallback 或禁用功能
try:
    from marathon_qa_assistant.services.knowledge_graph import graph_engine
except ImportError:
    graph_engine = None

try:
    from marathon_qa_assistant.services.multimodal import multimodal_service as mm_module
except ImportError:
    mm_module = None

from marathon_qa_assistant.services.vector_store import (
    load_vector_kb, 
    probe_vector_kb_health,
    retrieve,
    collect_chunks,
    build_hybrid_indices,
    save_outputs,
    infer_source_path
)
from marathon_qa_assistant.nodes.profile_and_retrieval import _parse_profile_form, FIELD_LABELS, FIELD_HINTS
from marathon_qa_assistant.apps.chainlit.ui_config import build_zone_mapping_table

_KB_READY = False
_KB_VECTOR_DIR = None


def _kb_candidate_dirs() -> list[Path]:
    preferred_vector_dir = get_preferred_vector_dir()
    if preferred_vector_dir == USER_VECTOR_DIR:
        return [USER_VECTOR_DIR, DEFAULT_VECTOR_DIR]
    return [DEFAULT_VECTOR_DIR]

class KBHelper:
    @staticmethod
    def get_file_inventory_md():
        """获取知识库中的文件清单 (Markdown 格式)"""
        inventory = []
        domain_docs = BASE_DIR / "domain_docs"
        for d in [UPLOAD_DOCS_DIR, domain_docs]:
            if not d.exists(): continue
            for f in d.iterdir():
                if f.is_file() and f.suffix.lower() in [".pdf", ".txt", ".md", ".docx"]:
                    stats = f.stat()
                    inventory.append({
                        "name": f.name,
                        "size": f"{stats.st_size / 1024:.1f} KB",
                        "type": f.suffix[1:].upper(),
                        "dir": d.name
                    })
        
        if not inventory:
            return "_No files in repository. Upload some docs to start!_"
        
        md = "### 📂 Repository Inventory\n\n"
        md += "| Name | Type | Size | Source |\n"
        md += "| :--- | :--- | :--- | :--- |\n"
        for item in inventory:
            md += f"| `{item['name']}` | {item['type']} | {item['size']} | {item['dir']} |\n"
        
        return md


def _build_toggle_action(sidebar_visible: bool) -> cl.Action:
    toggle_label = "隐藏侧边栏" if sidebar_visible else "打开侧边栏"
    toggle_icon = "visibility_off" if sidebar_visible else "visibility"
    return cl.Action(
        name="toggle_sidebar",
        payload={"value": "toggle"},
        label=toggle_label,
        icon=toggle_icon,
    )


def _build_welcome_actions(profile_name: str, sidebar_visible: bool) -> list[cl.Action]:
    toggle_action = _build_toggle_action(sidebar_visible)
    if profile_name == "Coach Mode":
        return [
            cl.Action(name="fill_profile", payload={"value": "profile"}, label="📋 填写训练画像", icon="edit_note"),
            cl.Action(name="adaptive_plan", payload={"value": "adaptive"}, label="自适应调整", icon="bolt"),
            cl.Action(name="refresh_profile", payload={"value": "refresh"}, label="刷新画像", icon="refresh"),
            toggle_action,
            cl.Action(name="manage_kb", payload={"value": "kb"}, label="知识库管理", icon="settings"),
        ]
    return [
        cl.Action(name="search_graph", payload={"value": "search"}, label="搜索图谱", icon="search"),
        cl.Action(name="cross_research", payload={"value": "research"}, label="交叉研究", icon="hub"),
        toggle_action,
        cl.Action(name="manage_kb", payload={"value": "kb"}, label="知识库管理", icon="settings"),
    ]


def _build_expert_elements() -> list[cl.Image]:
    avatar_path = str(Path(__file__).parents[2] / "assets" / "images" / "avatar.png")
    return [cl.Image(name="Assistant", path=avatar_path, display="inline")]

def init_knowledge_base(force_reload: bool = False):
    """初始化全局知识库。仅在真正进入运行态后调用，避免 import-time 副作用。"""
    global _KB_READY, _KB_VECTOR_DIR
    candidate_dirs = _kb_candidate_dirs()
    preferred_vector_dir = candidate_dirs[0]
    if _KB_READY and not force_reload and _KB_VECTOR_DIR == preferred_vector_dir:
        return False

    cl.logger.info("正在加载本地全局知识库 (Hybrid: TF-IDF + BM25)...")
    failures = []
    for candidate_dir in candidate_dirs:
        probe = probe_vector_kb_health(candidate_dir)
        if not probe["ok"]:
            reason = probe["reason"]
            failures.append(f"{probe['source']}:{reason}")
            cl.logger.warning(f"跳过不健康知识库 ({candidate_dir}): {reason}")
            continue

        try:
            chunks, vectorizer, matrix, bm25 = load_vector_kb(candidate_dir)
        except Exception as exc:
            failures.append(f"{probe['source']}:加载失败:{exc}")
            cl.logger.warning(f"知识库加载失败，继续尝试下一候选目录 ({candidate_dir}): {exc}")
            continue

        if not matrix:
            reason = "探测通过但加载结果为空"
            failures.append(f"{probe['source']}:{reason}")
            cl.logger.warning(f"知识库加载结果为空，继续尝试下一候选目录 ({candidate_dir})")
            continue

        set_kb_data(chunks, vectorizer, matrix, retrieve, bm25=bm25)
        global_state.chunks = chunks
        global_state.kb_chunks_len = len(chunks)
        global_state.kb_source = probe["source"]
        global_state.kb_health_reason = ""
        _KB_READY = True
        _KB_VECTOR_DIR = candidate_dir
        cl.logger.info(
            f"全局知识库加载成功！来源: {probe['source']} | 当前目录: {candidate_dir} | chunks: {len(chunks)}"
        )
        return True

    failure_reason = " | ".join(failures) if failures else "未找到可用知识库产物"
    cl.logger.warning(f"全局知识库以空库模式启动: {failure_reason}")
    set_kb_data([], None, None, retrieve)
    global_state.chunks = []
    global_state.kb_chunks_len = 0
    global_state.kb_source = "empty"
    global_state.kb_health_reason = failure_reason
    _KB_READY = False
    _KB_VECTOR_DIR = None
    return False

def ensure_knowledge_base_ready(force_reload: bool = False):
    """在 Chainlit 会话真正启动后再加载知识库。"""
    return init_knowledge_base(force_reload=force_reload)

async def update_sidebar(profile_override=None):
    """更新侧边栏运动员档案或知识图谱统计"""
    chat_profile = cl.user_session.get("chat_profile")
    sidebar_visible = cl.user_session.get("sidebar_visible", True)
    
    if profile_override:
        profile = profile_override
    else:
        state = cl.user_session.get("state")
        profile = state.get("user_profile") if state else load_user_profile()

    if chat_profile == "Coach Mode":
        name = "Athlete Stats"
        target_date_str = profile.get("target_race_date", "")
        countdown_str = "未设置"
        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
                days = (target_date - date.today()).days
                countdown_str = f"{days} 天" if days >= 0 else "已赛完"
            except:
                countdown_str = "格式错误"

        hz = profile.get("hr_zones", {})
        pz = profile.get("pace_zones", {})
        
        zone_mapping_table = build_zone_mapping_table(hz, pz)

        sidebar_content = f"""### 🏃‍♂️ 运动员档案 (Coach)
        
**核心指标**
- **当前跑量**: `{profile.get('weekly_mileage', 0)} km/周`
- **乳酸阈 (LTHR)**: `{profile.get('lthr', 0)} bpm`
- **乳酸阈配速**: `{profile.get('t_pace', '-')} min/km`
- **目标赛事**: `{profile.get('goal', '未知')}`
- **赛事倒计时**: `{countdown_str}`

**区间映射 (Z1-Z9)**
{zone_mapping_table}

---
*数据实时同步自个人画像文件*
"""
    else:
        name = "Graph Intelligence"
        node_count = len(graph_engine.nodes) if graph_engine else 0
        edge_count = len(graph_engine.edges) if graph_engine else 0
        chunk_count = len(KB_CHUNKS)
        
        unique_files = set(c.get("source_file") for c in KB_CHUNKS if "source_file" in c)
        density = edge_count / node_count if node_count > 0 else 0
        
        sidebar_content = f"""### 🧠 知识图谱统计 (Research)

**图谱规模**
- **核心实体 (Nodes)**: `{node_count}`
- **逻辑关联 (Edges)**: `{edge_count}`
- **知识密度**: `{density:.2f} 关系/节点`

**索引数据**
- **已索引文档**: `{len(unique_files)}` 篇
- **知识分片 (Chunks)**: `{chunk_count}`
- **图谱状态**: `{"已就绪" if node_count > 0 else "待构建"}`

---
*点击下方 [构建 AI 知识图谱] 可更新统计数据*
"""

    sidebar_msg = cl.user_session.get("sidebar_msg")
    if not sidebar_visible:
        if sidebar_msg:
            # 清空侧边栏内容，避免“已收起”占位文案让用户误以为没有收起。
            element = cl.Text(name=name, content="", display="side", for_id=sidebar_msg.id)
            await element.send(for_id=sidebar_msg.id)
        return

    if sidebar_msg:
        element = cl.Text(name=name, content=sidebar_content, display="side", for_id=sidebar_msg.id)
        await element.send(for_id=sidebar_msg.id)
    else:
        msg = cl.Message(content=f"📊 **{chat_profile or 'System'} 画像已就绪**", author="System")
        await msg.send()
        element = cl.Text(name=name, content=sidebar_content, display="side", for_id=msg.id)
        await element.send(for_id=msg.id)
        cl.user_session.set("sidebar_msg", msg)

@cl.set_chat_profiles
async def set_chat_profiles():
    return [
        cl.ChatProfile(
            name="Coach Mode",
            markdown_description="**教练模式**：专注于自适应训练计划、跑步表现分析与伤病预防指导。",
            icon="https://api.dicebear.com/7.x/avataaars/svg?seed=Coach&backgroundColor=b6e3f4",
        ),
        cl.ChatProfile(
            name="Research Mode",
            markdown_description="**研究模式**：专注于知识图谱探索、多篇文献交叉研究与领域知识挖掘。",
            icon="https://api.dicebear.com/7.x/avataaars/svg?seed=Research&backgroundColor=c0aede",
        ),
    ]

@cl.on_chat_start
async def start():
    if cl.user_session.get("initialized"):
        return

    ensure_knowledge_base_ready()
    
    chat_profile = cl.user_session.get("chat_profile")
    profile = load_user_profile()
    initial_mode = "team" if chat_profile == "Coach Mode" else "research"
    
    state: IntegratedState = {
        "query": "",
        "mode": initial_mode,
        "intent_type": "qa",
        "category": "",
        "subtasks": [],
        "draft_plan": "",
        "review_feedback": "",
        "is_approved": False,
        "iteration_count": 0,
        "final_report": "",
        "structured_report": None,
        "reasoning_log": [],
        "rag_sources": [],
        "graph_context": "",
        "wiki_context": "",
        "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "audit_scores": {"consistency": 0, "safety": 0, "roi": 0, "summary": ""},
        "roi_history": [],
        "risk_alert": "",
        "entities": [],
        "mermaid_graph": "",
        "guided_questions": [],
        "user_profile": profile,
        "adaptive_feedback": {},
        "history": []
    }
    
    cl.user_session.set("state", state)
    cl.user_session.set("sidebar_visible", True)
    cl.user_session.set("filling_field_key", None)
    await show_profile_summary(profile, chat_profile)
    await update_sidebar()
    cl.user_session.set("initialized", True)

async def show_profile_summary(profile, profile_name="Coach Mode"):
    hz = profile.get("hr_zones", {})
    pz = profile.get("pace_zones", {})
    pb_str = f"""
| 5k | 10k | 半马 | 全马 |
| :--- | :--- | :--- | :--- |
| {profile.get('pb_5k', '-')} | {profile.get('pb_10k', '-')} | {profile.get('pb_half', '-')} | {profile.get('pb_full', '-')} |
"""
    zones_str = f"""
| 区间 | 心率范围 (Coros) | 配速范围 (T-Pace) |
| :--- | :--- | :--- |
| **Z1 (轻松)** | {hz.get('Z1', '-')} | {pz.get('Z1', '-')} |
| **Z2 (有氧)** | {hz.get('Z2', '-')} | {pz.get('Z2', '-')} |
| **Z3 (马拉松)** | {hz.get('Z3', '-')} | {pz.get('Z3', '-')} |
| **Z4 (乳酸阈)** | {hz.get('Z4', '-')} | {pz.get('Z4', '-')} |
| **Z5 (间歇)** | {hz.get('Z5', '-')} | {pz.get('Z5', '-')} |
"""
    
    sidebar_visible = cl.user_session.get("sidebar_visible", True)

    if profile_name == "Coach Mode":
        welcome_title = "🏃‍♂️ **你好！我是您的 AI 跑步教练 (Coach Mode)**"
        welcome_intro = "我将根据您的生理数据和训练反馈，为您提供专业的自适应计划指导。"
    else:
        welcome_title = "🔬 **你好！我是您的 科学研究助手 (Research Mode)**"
        welcome_intro = "我将利用 GraphRAG 技术，帮您从海量文献中挖掘跑步科学的深度联系。"
    actions = _build_welcome_actions(profile_name, sidebar_visible)
    expert_elements = _build_expert_elements()

    welcome_msg = f"""{welcome_title}

{welcome_intro}

**您的当前画像：**
- **基本信息**: {profile.get('experience_level', '未知')} | {profile.get('goal', '未知')}
- **核心数据**: 周跑量 {profile.get('weekly_mileage', 0)}km | LTHR {profile.get('lthr', 0)}bpm | T-Pace {profile.get('t_pace', '-')}

**最佳成绩 (PB):**
{pb_str}

**心率区间与配速:**
{zones_str}

---
您可以直接提问，或通过下方功能菜单探索。"""
    welcome_msg_id = cl.user_session.get("welcome_msg_id")
    if welcome_msg_id:
        await cl.Message(id=welcome_msg_id, content=welcome_msg, actions=actions, elements=expert_elements).update()
    else:
        msg = cl.Message(content=welcome_msg, actions=actions, elements=expert_elements)
        await msg.send()
        cl.user_session.set("welcome_msg_id", msg.id)


async def handle_toggle_sidebar():
    current = cl.user_session.get("sidebar_visible", True)
    cl.user_session.set("sidebar_visible", not current)

    state = cl.user_session.get("state") or {}
    profile = state.get("user_profile") or load_user_profile()
    chat_profile = cl.user_session.get("chat_profile") or "Coach Mode"

    await show_profile_summary(profile, chat_profile)
    await update_sidebar(profile)

@cl.on_message
async def main(message: cl.Message):
    # 1. 处理上传的文件与图片
    image_descriptions = []
    if message.elements:
        UPLOAD_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        saved_files = []
        
        async def process_image(element, file_path=None):
            actual_path = file_path or element.path
            if not element.name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                return None
                
            msg_vlm = cl.Message(content=f"🎨 **检测到图片 `{element.name}`，正在理解内容...**")
            await msg_vlm.send()
            
            try:
                desc = await mm_module.call_vlm("llama3.2-vision:11b", "请简要描述这张图片的内容，以便我将其作为对话上下文。", actual_path)
                if "错误" in desc:
                    msg_vlm.content = f"⚠️ 图片 `{element.name}` 理解遇到问题: {desc}"
                    await msg_vlm.update()
                    return None
                else:
                    msg_vlm.content = f"✅ **图片理解完成**：{desc[:100]}..."
                    await msg_vlm.update()
                    return f"【图片内容: {element.name}】\n{desc}"
            except Exception as e:
                msg_vlm.content = f"⚠️ 图片 `{element.name}` 理解异常。"
                await msg_vlm.update()
                return None

        tasks = []
        for element in message.elements:
            if isinstance(element, (cl.File, cl.Image)):
                target_path = UPLOAD_DOCS_DIR / element.name
                try:
                    if element.path and os.path.exists(element.path):
                        shutil.copy(element.path, target_path)
                        saved_files.append(element.name)
                except Exception as e:
                    cl.logger.error(f"复制文件失败: {e}")
                
                if element.name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and target_path.exists():
                    tasks.append(process_image(element, str(target_path)))
        
        if tasks:
            results = await asyncio.gather(*tasks)
            image_descriptions = [r for r in results if r]
        
        if saved_files:
            other_files = [f for f in saved_files if not f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
            if other_files:
                await cl.Message(content=f"✅ **检测到上传文件并保存到知识库：**\n- " + "\n- ".join(other_files)).send()
            
            pdf_files = [f for f in saved_files if f.lower().endswith('.pdf')]
            if pdf_files:
                actions = [
                    cl.Action(name="extract_pdf_visuals", payload={"path": str((UPLOAD_DOCS_DIR / pdf_files[0]).absolute()), "name": pdf_files[0]}, label="🧠 提取 PDF 视觉知识", icon="auto_awesome"),
                    cl.Action(name="reindex_kb", payload={"value": "reindex"}, label="构建索引", icon="build")
                ]
                await cl.Message(content="检测到 PDF，是否提取视觉知识？", actions=actions).send()

    if not message.content.strip() and message.elements:
        return

    if not await check_ollama_status():
        await cl.Message(content="❌ **Ollama 服务未在线**，请确保本地 11434 端口服务已启动。").send()
        return

    state = cl.user_session.get("state")
    if state.get("final_report"):
        state["history"].append({"role": "assistant", "content": state["final_report"]})

    parsed_form = _parse_profile_form(message.content)
    if parsed_form:
        profile = load_user_profile()
        for k, v in parsed_form.items():
            if k == "weekly_mileage":
                try:
                    profile[k] = int(v) if isinstance(v, str) and v.isdigit() else v
                except (ValueError, TypeError):
                    profile[k] = v
            elif k == "vo2max":
                try:
                    profile[k] = int(v) if isinstance(v, str) and v.isdigit() else v
                except (ValueError, TypeError):
                    profile[k] = v
            elif k == "max_session_minutes":
                try:
                    profile[k] = int(v) if isinstance(v, str) and v.isdigit() else v
                except (ValueError, TypeError):
                    profile[k] = v
            else:
                profile[k] = v
        save_user_profile(profile)
        state["user_profile"] = profile
        await cl.Message(content="✅ 训练画像已保存！正在生成你的周训练计划...").send()
    
    filling_key = cl.user_session.get("filling_field_key")
    if filling_key:
        filling_label = cl.user_session.get("filling_field_label", filling_key)
        value = message.content.strip()
        
        profile = load_user_profile()
        if filling_key in ("weekly_mileage", "vo2max", "max_session_minutes"):
            try:
                profile[filling_key] = int(value) if isinstance(value, str) and value.strip().isdigit() else value
            except (ValueError, TypeError):
                profile[filling_key] = value
        else:
            profile[filling_key] = value
        
        save_user_profile(profile)
        if state:
            state["user_profile"] = profile
            cl.user_session.set("state", state)
        
        cl.user_session.set("filling_field_key", None)
        cl.user_session.set("filling_field_label", None)
        
        pending = cl.user_session.get("pending_missing_fields", [])
        pending = [k for k in pending if k != filling_key]
        cl.user_session.set("pending_missing_fields", pending)
        
        if pending:
            actions = [
                cl.Action(
                    name="fill_field",
                    payload={"key": k, "label": FIELD_LABELS.get(k, k), "hint": FIELD_HINTS.get(k, "")},
                    label=f"📝 填写 {FIELD_LABELS.get(k, k)}",
                )
                for k in pending
            ]
            actions.append(
                cl.Action(name="cancel_fill", payload={}, label="跳过，直接生成", icon="skip_next")
            )
            await cl.Message(
                content=f"✅ **{filling_label}** 已保存！剩余 **{len(pending)}** 项：",
                actions=actions
            ).send()
        else:
            await cl.Message(content="✅ **所有训练画像信息已收集完毕！正在生成你的周训练计划...**").send()
            plan_query = cl.user_session.get("pending_plan_query", "请为我生成第一周训练计划")
            await main(cl.Message(content=f"【训练计划请求】用户画像已完善。原始请求：{plan_query}"))
        return
    
    state["query"] = message.content
    if image_descriptions:
        state["query"] = "\n\n".join(image_descriptions) + f"\n\n**用户问题**: {message.content}"
    
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
                    if content and "__FILL_FIELDS__" not in content:
                        await msg.stream_token(content)

            elif kind == "on_chain_end":
                output = event["data"].get("output", {})
                if isinstance(output, dict):
                    final_state.update(output)
                    if "reasoning_log" in output and output["reasoning_log"]:
                        for log in output["reasoning_log"]:
                            if log not in printed_logs:
                                printed_logs.add(log)
                                await cl.Message(content=f"📝 `{log}`").send()

        cl.user_session.set("state", final_state)
        
        intent_type = final_state.get("intent_type", "")
        missing_fields = final_state.get("missing_fields", [])
        final_report = final_state.get("final_report", "")
        
        if intent_type == "plan" and final_report == "__FILL_FIELDS__" and missing_fields:
            profile = load_user_profile()
            still_missing = [k for k in missing_fields if not profile.get(k)]
            if still_missing:
                cl.user_session.set("pending_missing_fields", still_missing)
                cl.user_session.set("pending_plan_query", message.content)
                actions = [
                    cl.Action(
                        name="fill_field",
                        payload={"key": k, "label": FIELD_LABELS.get(k, k), "hint": FIELD_HINTS.get(k, "")},
                        label=f"📝 填写 {FIELD_LABELS.get(k, k)}",
                    )
                    for k in still_missing
                ]
                actions.append(
                    cl.Action(name="cancel_fill", payload={}, label="跳过，直接生成", icon="skip_next")
                )
                status_text = f"## 📋 请补充训练画像\n\n还需要以下 **{len(still_missing)}** 项信息，请逐一点击填写："
                await cl.Message(content=status_text, actions=actions).send()
                msg.content = ""
                await msg.update()
                return
        
        # 渲染最终报告 (显式开启 include_sources 以显示参考来源区块)
        report_html = UIHelper.render_structured_report(
            final_state.get("structured_report"), 
            final_state.get("final_report"),
            include_sources=True
        )
        wiki_panel_md = UIHelper.render_chainlit_wiki_context_md(
            final_state.get("structured_report")
        )
        msg.content = report_html
        
        # 关联 PDF 预览 Action 载荷，使正文中的 action:view_pdf 链接生效
        # 必须将 actions 添加到消息对象中，Chainlit 才会允许点击跳转
        preview_bundle = UIHelper.build_evidence_preview_bundle(
            final_state.get("structured_report"), 
            final_state.get("final_report")
        )
        if preview_bundle.get("actions"):
            msg.actions = [
                cl.Action(
                    name=a["name"], 
                    payload=a["payload"], 
                    label=a["label"]
                ) 
                for a in preview_bundle["actions"]
            ]
        
        await msg.update()

        if wiki_panel_md:
            await cl.Message(content=wiki_panel_md).send()
        
        # 发送统计信息
        usage = final_state.get("token_usage", {})
        token_md = UIHelper.generate_token_md(
            {"Total": usage.get("total_tokens", 0)},
            roi_score=final_state.get("audit_scores", {}).get("roi", 0)
        )
        await cl.Message(content=token_md).send()
        
        # 引导问题
        if final_state.get("guided_questions"):
            actions = [cl.Action(name="ask_q", payload={"v": q}, label=q) for q in final_state["guided_questions"]]
            await cl.Message(content="💡 **您可以接着问：**", actions=actions).send()

    except Exception as e:
        await cl.Message(content=f"❌ **运行出错**: {str(e)}").send()

@cl.action_callback("fill_profile")
async def on_fill_profile(action: cl.Action):
    await action.remove()
    from marathon_qa_assistant.nodes.profile_and_retrieval import TRAINING_PROFILE_FORM
    await cl.Message(content=TRAINING_PROFILE_FORM).send()

@cl.action_callback("fill_field")
async def on_fill_field(action: cl.Action):
    field_key = action.payload.get("key", "")
    label = action.payload.get("label", field_key)
    hint = action.payload.get("hint", "")
    
    cl.user_session.set("filling_field_key", field_key)
    cl.user_session.set("filling_field_label", label)
    
    await cl.Message(
        content=f"请输入 **{label}**：\n_{hint}_\n\n> 请直接在下方输入框中回复，无需点击其他按钮。"
    ).send()

@cl.action_callback("cancel_fill")
async def on_cancel_fill(action: cl.Action):
    await action.remove()
    cl.user_session.set("pending_missing_fields", [])
    cl.user_session.set("filling_field_key", None)
    await cl.Message(content="✅ 已跳过画像填写，使用当前已有数据生成训练计划...").send()
    plan_query = cl.user_session.get("pending_plan_query", "请为我生成第一周训练计划")
    await main(cl.Message(content=f"【训练计划请求】用户画像可用。原始请求：{plan_query}"))

@cl.action_callback("toggle_sidebar")
async def on_toggle_sidebar(action: cl.Action):
    await handle_toggle_sidebar()

@cl.action_callback("ask_q")
async def on_ask_q(action: cl.Action):
    await action.remove()
    query = action.payload.get("v")
    if query:
        await main(cl.Message(content=query))

@cl.action_callback("extract_pdf_visuals")
async def on_extract_pdf_visuals(action: cl.Action):
    await action.remove()
    pdf_path = action.payload.get("path")
    pdf_name = action.payload.get("name")
    
    msg_status = cl.Message(content=f"🧠 **正在解析 PDF `{pdf_name}` 并提取图表知识...**")
    await msg_status.send()
    
    try:
        insights = await mm_module.extract_and_analyze_pdf(pdf_path)
        if not insights:
            msg_status.content = f"⚠️ **未在 PDF `{pdf_name}` 中检测到明显的图片或图表。**"
            await msg_status.update()
            return
            
        report_md = f"### 📑 PDF 视觉知识提取报告: `{pdf_name}`\n\n"
        full_description = ""
        for item in insights:
            report_md += f"**第 {item['page']} 页图片**:\n> {item['description']}\n\n"
            full_description += f"\n\n[PDF Page {item['page']}] {item['description']}"
            
        msg_status.content = f"✅ **PDF `{pdf_name}` 视觉知识提取完成！**"
        await msg_status.update()
        await cl.Message(content=report_md).send()
        
        cl.user_session.set("last_multimodal_desc", full_description)
        cl.user_session.set("last_multimodal_source", f"pdf:{pdf_name}")
        
        actions = [cl.Action(name="inject_multimodal", payload={"value": "inject"}, label="注入知识图谱", icon="share")]
        await cl.Message(content="是否将视觉知识注入到您的本地知识图谱中？", actions=actions).send()
    except Exception as e:
        await cl.Message(content=f"❌ **提取失败**: {str(e)}").send()

@cl.action_callback("multimodal_lab")
async def on_multimodal_lab(action: cl.Action):
    await action.remove()
    files = await cl.AskFileMessage(
        content="🖼️ 请上传跑步科学图表或数据截图 (JPG, PNG, WEBP)：",
        accept=["image/jpeg", "image/png", "image/webp"],
        max_files=1
    ).send()
    
    if not files: return
    image_file = files[0]
    
    res_prompt = await cl.AskUserMessage(content="💭 您想分析什么？（直接发送使用默认 Prompt）：").send()
    prompt = res_prompt['output'] if res_prompt and res_prompt['output'].strip() else "请详细描述这张图片中的跑步科学知识。"
    
    msg_status = cl.Message(content=f"🚀 **正在启动本地多模态模型 (LLaVA & Llama 3.2-Vision)...**")
    await msg_status.send()
    
    try:
        results = await mm_module.compare_vlms(image_file.path, prompt)
        comparison_md = f"### 🖼️ 多模态对比分析: `{image_file.name}`\n\n**用户指令**: `{prompt}`\n\n"
        for model, content in results.items():
            icon = "🦙" if "llama" in model.lower() else "🌋"
            comparison_md += f"#### {icon} {model}\n{content}\n\n---\n"
            
        await cl.Message(content=comparison_md).send()
        cl.user_session.set("last_multimodal_desc", "\n\n".join(results.values()))
        cl.user_session.set("last_multimodal_source", f"img:{image_file.name}")
        
        actions = [cl.Action(name="inject_multimodal", payload={"value": "inject"}, label="注入知识图谱", icon="share")]
        await cl.Message(content="是否注入知识图谱？", actions=actions).send()
    except Exception as e:
        await cl.Message(content=f"❌ **分析失败**: {str(e)}").send()

@cl.action_callback("inject_multimodal")
async def on_inject_multimodal(action: cl.Action):
    await action.remove()
    description = cl.user_session.get("last_multimodal_desc")
    source_id = cl.user_session.get("last_multimodal_source")
    
    if not description or not source_id:
        await cl.Message(content="⚠️ **未找到待注入内容**").send()
        return
        
    msg_status = cl.Message(content="🧠 **正在注入图谱...**")
    await msg_status.send()
    
    try:
        count = await graph_engine.add_multimodal_description(description, source_id)
        if count > 0:
            await cl.Message(content=f"✅ **注入成功！** 提取了 `{count}` 条知识。").send()
            await update_sidebar()
        else:
            await cl.Message(content="⚠️ **未提取到有效三元组。**").send()
    except Exception as e:
        await cl.Message(content=f"❌ **注入失败**: {str(e)}").send()

@cl.action_callback("manage_kb")
async def on_manage_kb(action: cl.Action):
    status_msg = cl.Message(content="🛠️ **正在加载知识库清单...**")
    await status_msg.send()
    try:
        await action.remove()
        inventory_md = KBHelper.get_file_inventory_md()
        status_msg.content = "🛠️ **知识库管理**\n\n您可以查看当前文件，或通过下方功能菜单操作。"
        await status_msg.update()
        await cl.Message(content=inventory_md).send()
        actions = [
            cl.Action(name="upload_file", payload={"value": "upload"}, label="上传新文件", icon="upload"),
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
        content="请上传 PDF, TXT 或 MD 文件：",
        accept=["application/pdf", "text/plain", "text/markdown"],
        max_files=10
    ).send()
    if files:
        UPLOAD_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        saved_files = []
        for file in files:
            target_path = UPLOAD_DOCS_DIR / file.name
            shutil.copy(file.path, target_path)
            saved_files.append(file.name)
        await cl.Message(content=f"✅ **已成功上传 {len(saved_files)} 个文件：**\n- " + "\n- ".join(saved_files)).send()
        actions = [
            cl.Action(name="reindex_kb", payload={"value": "reindex"}, label="立即构建索引", icon="build"),
            cl.Action(name="build_graph_ai", payload={"mode": "full"}, label="全量重构图谱（推荐）", icon="refresh")
        ]
        await cl.Message(content="现在要构建索引或更新图谱吗？", actions=actions).send()

@cl.action_callback("reindex_kb")
async def on_reindex_kb(action: cl.Action):
    await action.remove()
    domain_docs = BASE_DIR / "domain_docs"
    file_map = {}
    dirs_to_scan = [UPLOAD_DOCS_DIR, domain_docs]
    for d in dirs_to_scan:
        if d.exists():
            for f in d.glob("*"):
                if f.is_file() and f.suffix.lower() in [".pdf", ".txt", ".md", ".docx"]:
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
            ensure_knowledge_base_ready(force_reload=True)
            actions = [
                cl.Action(name="build_graph_ai", payload={"mode": "full"}, label="全量重构图谱（推荐）", icon="refresh")
            ]
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
    try:
        if not global_state.chunks:
            await cl.Message(content="⚠️ **缺少文本分片**，请先执行‘重新构建索引’。").send()
            return
        n_nodes, n_edges = await graph_engine.build_graph(global_state.chunks, incremental=is_incremental)
        density = n_edges / n_nodes if n_nodes > 0 else 0
        details = f"### 📊 知识图谱已更新 ({'增量' if is_incremental else '全量'})\n\n"
        details += f"- **核心实体**: `{n_nodes}`\n- **逻辑关联**: `{n_edges}`\n- **知识密度**: `{density:.2f}`\n"
        await cl.Message(content=details).send()
        await update_sidebar()
    except Exception as e:
        await cl.Message(content=f"❌ **构建失败**: {str(e)}").send()

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
    # payload 可能是字符串化的 JSON (来自 Markdown 链接) 或 字典 (来自 Action 按钮)
    payload = action.payload
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception as e:
            cl.logger.error(f"解析 view_pdf payload 失败: {e}")
            await cl.Message(content="❌ **无法打开引用**：载荷解析失败。").send()
            return

    if not isinstance(payload, dict):
        await cl.Message(content="❌ **无法打开引用**：载荷类型不受支持。").send()
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
        display_name = f"{name} (P.{page})"
        msg_parts = [f"📑 **正在预览: {display_name}**"]
        if snippet:
            msg_parts.extend(["", "> **📌 引用原文：**", "> ", f"> {snippet}"])
        msg = cl.Message(content="\n".join(msg_parts))
        await msg.send()
        pdf_element = cl.Pdf(name=display_name, path=path, display="side", page=page)
        pdf_element.for_id = msg.id
        await pdf_element.send(for_id=msg.id)
    else:
        await cl.Message(content=f"❌ **无法找到文件**: {name or '未知'}\n路径: `{path}`").send()

@cl.action_callback("refresh_profile")
async def on_refresh_profile(action: cl.Action):
    await action.remove()
    profile = load_user_profile()
    state = cl.user_session.get("state")
    state["user_profile"] = profile
    cl.user_session.set("state", state)
    await show_profile_summary(profile)
    await update_sidebar()

@cl.action_callback("adaptive_plan")
async def on_adaptive_plan(action: cl.Action):
    await action.remove()
    res = await cl.AskUserMessage(content="请输入您的近期反馈（例如：疲劳度、训练强度感受等）：").send()
    if res:
        query = f"【自适应调整】用户反馈：{res['output']}。请根据此反馈调整我的训练计划。"
        await main(cl.Message(content=query))

@cl.action_callback("search_graph")
async def on_search_graph(action: cl.Action):
    await action.remove()
    res = await cl.AskUserMessage(content="🔍 请输入您想在图谱中搜索的实体名称（如：VO2Max, HIIT）：").send()
    if res:
        entity = res['output']
        result = graph_engine.search_graph([entity])
        mermaid = graph_engine.generate_mermaid(nodes=result["nodes"], edges=result["edges"])
        msg = cl.Message(content=f"### 🔍 图谱搜索结果: `{entity}`\n- 找到 `{len(result['nodes'])}` 个相关节点\n- 找到 `{len(result['edges'])}` 条关联边")
        await msg.send()
        await cl.Text(name="Mermaid Graph", content=f"```mermaid\n{mermaid}\n```", display="inline", for_id=msg.id).send(for_id=msg.id)

@cl.action_callback("cross_research")
async def on_cross_research(action: cl.Action):
    await action.remove()
    res = await cl.AskUserMessage(content="🔬 请输入要进行交叉研究的多个实体（用逗号分隔，如：心率, 疲劳度）：").send()
    if res:
        entities = [e.strip() for e in res['output'].split(",") if e.strip()]
        query = f"【交叉研究】请深入分析以下实体之间的科学关联：{', '.join(entities)}。"
        await main(cl.Message(content=query))
