import os
import sys
import chainlit as cl
from pathlib import Path
from datetime import datetime, date

from marathon_qa_assistant.core.app_state import (
    BASE_DIR,
    UPLOAD_DOCS_DIR,
    global_state
)
from marathon_qa_assistant.core.kb_bootstrap import bootstrap_knowledge_base, get_knowledge_base_health_snapshot
from marathon_qa_assistant.core.kb_provider import KB_CHUNKS, get_kb_runtime_state
from marathon_qa_assistant.services.input_validator import (
    IMAGE_EXTENSIONS as VALIDATOR_IMAGE_EXTS,
    DOCUMENT_EXTENSIONS as VALIDATOR_DOC_EXTS,
)
from marathon_qa_assistant.core.workflow import load_user_profile
from marathon_qa_assistant.apps.chainlit.ui_config import ZONE_LABELS
from marathon_qa_assistant.apps.chainlit.coach_state import (
    render_coach_ui_status_md,
    sync_coach_ui_snapshot,
)
from marathon_qa_assistant.nodes.common import llm as common_llm
from marathon_qa_assistant.nodes.profile_and_retrieval import FIELD_LABELS, FIELD_HINTS

def _build_left_action_groups(sidebar_visible: bool):
    toggle_label = "隐藏侧边栏" if sidebar_visible else "打开侧边栏"
    toggle_icon = "visibility_off" if sidebar_visible else "visibility"
    return [
        {
            "title": "训练计划",
            "items": [
                {"name": "quick_profile", "label": "极速画像", "description": "3 步后生成基础计划", "icon": "⚡", "payload": {"value": "quick_profile"}},
                {"name": "fill_profile", "label": "完整画像", "description": "补齐更多信息，生成更精准计划", "icon": "📋", "payload": {"value": "profile"}},
                {"name": "adaptive_plan", "label": "自适应调整", "description": "根据近期反馈调整当前计划", "icon": "⚡", "payload": {"value": "adaptive"}},
            ],
        },
        {
            "title": "知识库",
            "items": [
                {"name": "search_graph", "label": "搜索知识图谱", "description": "检索训练知识实体", "icon": "🔍", "payload": {"value": "search"}},
                {"name": "cross_research", "label": "交叉研究实体", "description": "比较多个运动科学实体", "icon": "🔗", "payload": {"value": "research"}},
                {"name": "manage_kb", "label": "管理知识库", "description": "上传、查看和重建资料库", "icon": "⚙️", "payload": {"value": "kb"}},
            ],
        },
        {
            "title": "界面",
            "items": [
                {"name": "refresh_profile", "label": "刷新画像", "description": "同步最新侧边栏画像", "icon": "🔄", "payload": {"value": "refresh"}},
                {"name": "toggle_sidebar", "label": toggle_label, "description": "切换侧边栏显示状态", "icon": "👁️", "icon_name": toggle_icon, "payload": {"value": "toggle"}},
            ],
        },
    ]


async def show_profile_summary(profile, profile_name="Coach Mode"):
    sidebar_visible = cl.user_session.get("sidebar_visible", True)

    is_coach = (profile_name == "Coach Mode")
    welcome_title = "🏃‍♂️ **你好！我是您的 AI 跑步教练 (Coach Mode)**" if is_coach else "🔬 **你好！我是您的 科学研究助手 (Research Mode)**"

    actions = []

    _avatar_path = str(Path(__file__).parents[3] / "assets" / "images" / "avatar.png")
    expert_elements = [
        cl.Image(name="Assistant", path=_avatar_path, display="inline"),
    ]

    session_state = cl.user_session.get("state") or {}
    snapshot = sync_coach_ui_snapshot(cl.user_session.get, cl.user_session.set, session_state)
    status_line = ""
    if is_coach:
        status_line = (
            f"\n\n🧭 **当前状态**：{snapshot['page_label']} / {snapshot['message_label']}"
            f"\n\n👉 **下一步**：{snapshot['next_step_hint']}"
        )

    welcome_msg = f"""{welcome_title}

📊 **右侧面板**会实时显示核心画像、证据库与下一步建议。{status_line}"""
    action_element = cl.CustomElement(
        name="LeftActionRail",
        props={
            "title": "AI 跑步教练操作台" if is_coach else "科研助手操作台",
            "subtitle": "常用功能已移动到左侧分组卡片栏。",
            "status": f"当前状态：{snapshot['page_label']} / {snapshot['message_label']}\n下一步：{snapshot['next_step_hint']}" if is_coach else "请选择左侧入口开始使用。",
            "groups": _build_left_action_groups(sidebar_visible),
        },
    )
    await cl.Message(content=welcome_msg, actions=actions, elements=[*expert_elements, action_element]).send()

async def _generate_knowledge_card(entity: str, result: dict) -> str:
    """用 LLM 基于图谱数据生成实体知识卡片 (带文献溯源)"""
    nodes = result.get("nodes", {})
    edges = result.get("edges", [])

    total_nodes = len(nodes)
    total_edges = len(edges)

    chunk_to_file = {}
    try:
        for c in KB_CHUNKS:
            cid = c.get("chunk_id")
            fname = c.get("source_file")
            if cid and fname:
                chunk_to_file[cid] = fname
    except Exception:
        pass

    src_files = set()
    for nid, nd in nodes.items():
        for sc in nd.get("source_chunks", []):
            fname = chunk_to_file.get(sc)
            if fname:
                src_files.add(fname)

    display_edges = edges[:25]

    edge_lines = []
    for edge in display_edges:
        s_label = nodes.get(edge["source"], {}).get("label", edge["source"])
        t_label = nodes.get(edge["target"], {}).get("label", edge["target"])
        relation = edge.get("relation", "关联")
        edge_lines.append(f"- {s_label} --({relation})--> {t_label}")

    entity_labels = list(set(
        nodes[nid]["label"] for nid in nodes
        if nodes[nid].get("label")
    ))
    top_labels = entity_labels[:30]

    source_list = "\n".join(f"- `{f}`" for f in sorted(src_files)[:20]) if src_files else "(无法解析来源文件)"

    prompt = f"""你是运动科学知识图谱分析师。以下是知识图谱中与「{entity}」相关的实体和关系：

**搜索实体**: {entity}
**图谱规模**: {total_nodes} 个关联实体, {total_edges} 条关联边

**知识来源文件**:
{source_list}

**实体列表** (部分):
{chr(10).join(f'- {l}' for l in top_labels)}

**关系链路** (Top {len(display_edges)}):
{chr(10).join(edge_lines)}

请基于以上图谱数据生成一份结构化的**实体知识卡片**（用 Markdown），严格按以下格式输出。
**重要：每条关键发现在末尾必须标注来源文件名，格式为 `[来源: 文件名]`**。

### 🧠 {entity} · 知识卡片

**📌 核心概述**
(2-3句话概述：这个实体在跑步/运动科学中的角色和意义)

**🔗 关键关联发现**
(从关系链路中提取最重要的3-5条发现，每条一句话。每条末尾加 `[来源: xxx.pdf]`，从知识来源文件列表中选取最相关的文件引用)

**📂 涉及主题**
(归纳图谱中与此实体相关的研究主题方向，3-5个关键词)

**📚 引用文献**
- (列出 3-5 篇最相关的来源文件名)

**📊 图谱统计**
- 关联实体: {total_nodes} 个
- 关联边: {total_edges} 条
- 来源文件: {len(src_files)} 篇

> 💡 此卡片由 AI 基于本地知识图谱自动生成，每条发现均已标注知识来源。"""

    if common_llm is None:
        edge_summary = "\n".join(edge_lines[:10])
        source_display = "\n".join(f"- `{f}`" for f in sorted(src_files)[:10]) if src_files else "_(无)_"
        return f"""### 🧠 {entity} · 知识卡片 (仅图谱数据)

> ⚠️ LLM 不可用，仅展示原始图谱数据。

**📌 核心概述**
知识图谱中找到 **{total_nodes}** 个关联实体、**{total_edges}** 条关联边。

**🔗 主要关联 (Top 10)**
{edge_summary}

**📚 知识来源**
{source_display}

**📊 图谱统计**
- 关联实体: {total_nodes} 个
- 关联边: {total_edges} 条
- 来源文件: {len(src_files)} 篇"""

    try:
        from langchain_core.messages import HumanMessage
        response = await common_llm.ainvoke([HumanMessage(content=prompt)])
        content = str(getattr(response, "content", "") or "").strip()
        if content:
            return content
    except Exception:
        pass

    return f"### 🧠 {entity}\n\n知识图谱中找到 {total_nodes} 个关联实体、{total_edges} 条关联边，但 LLM 总结生成失败。\n\n请稍后重试或检查 Ollama 服务状态。"

# 尝试导入可选模块
try:
    from marathon_qa_assistant.services.knowledge_graph import graph_engine
except ImportError:
    graph_engine = None

class KBHelper:
    @staticmethod
    def get_file_inventory_md():
        """获取知识库中的文件清单 (Markdown 格式)"""
        inventory = []
        domain_docs = BASE_DIR / "domain_docs"
        all_supported = VALIDATOR_DOC_EXTS | VALIDATOR_IMAGE_EXTS
        for d in [UPLOAD_DOCS_DIR, domain_docs]:
            if not d.exists(): continue
            for f in d.iterdir():
                if f.is_file() and f.suffix.lower() in all_supported:
                    stats = f.stat()
                    inventory.append({
                        "name": f.name,
                        "size": f"{stats.st_size / 1024:.1f} KB",
                        "type": f.suffix[1:].upper(),
                        "dir": d.name
                    })
        
        if not inventory:
            return "_No files in repository. Upload some docs to start!_"
        
        md = "### 📂 知识库清单\n\n"
        md += "| 名称 | 类型 | 大小 | 来源 |\n"
        md += "| :--- | :--- | :--- | :--- |\n"
        for item in inventory:
            md += f"| `{item['name']}` | {item['type']} | {item['size']} | {item['dir']} |\n"
        
        return md

def init_knowledge_base():
    """初始化全局知识库"""
    cl.logger.info("正在加载本地全局知识库 (Hybrid: TF-IDF + BM25)...")
    report = bootstrap_knowledge_base()
    snapshot = get_knowledge_base_health_snapshot()
    global_state.chunks = list(get_kb_runtime_state().get("chunks") or [])
    global_state.kb_chunks_len = int(snapshot.get("chunks_count") or 0)
    global_state.kb_source = str(snapshot.get("source") or "unknown")
    global_state.kb_health_reason = str(snapshot.get("reason") or "")

    if report.get("ok"):
        cl.logger.info(f"全局知识库加载成功！当前目录: {report.get('vector_dir')}")
    else:
        cl.logger.warning(f"全局知识库以空库模式启动：{report.get('reason')}")

def _format_t_pace_for_sidebar(value) -> str:
    text = str(value or "").strip()
    if not text or text in ("-", "—", "未设置"):
        return "未设置"
    if ":" in text:
        return text if "/" in text else f"{text}/km"
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits == text and len(digits) in (3, 4):
        return f"{int(digits[:-2])}:{digits[-2:]}/km"
    return text


def _zone_label_short(key: str) -> str:
    label = ZONE_LABELS.get(key, key)
    if label.startswith(f"{key} "):
        label = label[len(key) + 1:]
    return label.split("(", 1)[0].strip() or key


def _build_simplified_zone_table(profile: dict) -> str:
    hz = profile.get("hr_zones", {}) or {}
    pz = profile.get("pace_zones", {}) or {}
    rows = []
    for i in range(1, 10):
        key = f"Z{i}"
        label = _zone_label_short(key)
        hr_val = hz.get(key, "—")
        pace_val = pz.get(key, "—")
        rows.append(f"| **{key}** | {label} | {hr_val} | {pace_val} |")
    return "\n".join(rows)


def _build_profile_section(profile: dict) -> str:
    """构建运动员档案段（用户摘要）"""
    target_date_str = str(profile.get("target_race_date", "") or "").strip()
    countdown_str = "未设置"
    if target_date_str and target_date_str.lower() not in ("none", "null", "未设置"):
        parsed_date = None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%d/%m/%Y"):
            try:
                parsed_date = datetime.strptime(target_date_str, fmt).date()
                break
            except ValueError:
                continue
        if parsed_date:
            days = (parsed_date - date.today()).days
            if days == 0:
                countdown_str = "📅 **就在今天！**"
            elif days > 0:
                countdown_str = f"{days} 天"
            else:
                countdown_str = f"已赛完 ({abs(days)} 天前)"
        else:
            countdown_str = target_date_str

    t_pace = _format_t_pace_for_sidebar(profile.get("t_pace"))
    zones_table = _build_simplified_zone_table(profile)

    return f"""### 🏃‍♂️ 核心画像

- **目标赛事**: `{profile.get('goal', '未知')}`
- **赛事倒计时**: `{countdown_str}`
- **当前跑量**: `{profile.get('weekly_mileage', 0)} km/周`
- **强度模型**: `LTHR 九区 Z1-Z9`
- **乳酸阈**: `{profile.get('lthr', 0)} bpm`
- **阈值配速**: `{t_pace}`
- **执行口径**: `Z1-Z9 为主，配速仅参考`

**强度速查**
| 区间 | 用途 | 心率 | 配速参考 |
| :--- | :--- | :--- | :--- |
{zones_table}"""


def _build_graph_section() -> str:
    """构建证据库摘要段"""
    node_count = len(graph_engine.nodes) if graph_engine else 0
    unique_files = set(c.get("source_file") for c in KB_CHUNKS if "source_file" in c)
    status = "已就绪" if node_count > 0 or unique_files else "待加载"
    return f"""### 📚 证据库

{len(unique_files)} 篇资料 · {status}"""


async def update_sidebar(profile_override=None):
    """更新侧边栏 — 中等轻量化训练画像摘要"""
    sidebar_visible = cl.user_session.get("sidebar_visible", True)
    session_state = cl.user_session.get("state") or {}

    if profile_override:
        profile = profile_override
    else:
        profile = session_state.get("user_profile") if session_state else await cl.make_async(load_user_profile)()

    profile_section = _build_profile_section(profile)
    graph_section = _build_graph_section()
    snapshot = sync_coach_ui_snapshot(cl.user_session.get, cl.user_session.set, session_state)
    status_section = render_coach_ui_status_md(snapshot)
    status_block = ""
    if status_section:
        status_block = f"""

---

{status_section}"""

    sidebar_content = f"""{profile_section}

---

{graph_section}
{status_block}"""

    sidebar_name = "马拉松助手 · 统一面板"

    sidebar_msg = cl.user_session.get("sidebar_msg")
    if not sidebar_visible:
        if sidebar_msg:
            element = cl.Text(name=sidebar_name, content="*面板已收起*", display="side", for_id=sidebar_msg.id)
            await element.send(for_id=sidebar_msg.id)
        return

    if sidebar_msg:
        element = cl.Text(name=sidebar_name, content=sidebar_content, display="side", for_id=sidebar_msg.id)
        await element.send(for_id=sidebar_msg.id)
    else:
        msg = cl.Message(content="📊 **马拉松助手 · 统一面板已就绪**", author="System")
        await msg.send()
        element = cl.Text(name=sidebar_name, content=sidebar_content, display="side", for_id=msg.id)
        await element.send(for_id=msg.id)
        cl.user_session.set("sidebar_msg", msg)
