import os
import sys
import chainlit as cl
from pathlib import Path
from datetime import datetime, date

from marathon_qa_assistant.core.app_state import (
    BASE_DIR,
    UPLOAD_DOCS_DIR,
    get_preferred_vector_dir,
    global_state
)
from marathon_qa_assistant.core.kb_provider import KB_CHUNKS, set_kb_data
from marathon_qa_assistant.services.vector_store import load_vector_kb, retrieve
from marathon_qa_assistant.services.input_validator import (
    IMAGE_EXTENSIONS as VALIDATOR_IMAGE_EXTS,
    DOCUMENT_EXTENSIONS as VALIDATOR_DOC_EXTS,
)
from marathon_qa_assistant.core.workflow import load_user_profile
from marathon_qa_assistant.apps.chainlit.ui_config import ZONE_LABELS
from marathon_qa_assistant.nodes.common import llm as common_llm
from marathon_qa_assistant.nodes.profile_and_retrieval import FIELD_LABELS, FIELD_HINTS

async def show_profile_summary(profile, profile_name="Coach Mode"):
    sidebar_visible = cl.user_session.get("sidebar_visible", True)
    toggle_label = "隐藏侧边栏" if sidebar_visible else "打开侧边栏"
    toggle_icon = "visibility_off" if sidebar_visible else "visibility"

    is_coach = (profile_name == "Coach Mode")
    welcome_title = "🏃‍♂️ **你好！我是您的 AI 跑步教练 (Coach Mode)**" if is_coach else "🔬 **你好！我是您的 科学研究助手 (Research Mode)**"

    actions = [
        cl.Action(name="fill_profile", payload={"value": "profile"}, label="📋 填写训练画像", icon="edit_note"),
        cl.Action(name="adaptive_plan", payload={"value": "adaptive"}, label="⚡ 自适应调整", icon="bolt"),
        cl.Action(name="refresh_profile", payload={"value": "refresh"}, label="🔄 刷新画像", icon="refresh"),
        cl.Action(name="search_graph", payload={"value": "search"}, label="🔍 搜索图谱", icon="search"),
        cl.Action(name="cross_research", payload={"value": "research"}, label="🔗 交叉研究", icon="hub"),
        cl.Action(name="manage_kb", payload={"value": "kb"}, label="⚙️ 知识库管理", icon="settings"),
        cl.Action(name="toggle_sidebar", payload={"value": "toggle"}, label=toggle_label, icon=toggle_icon),
    ]

    _avatar_path = str(Path(__file__).parents[3] / "assets" / "images" / "avatar.png")
    expert_elements = [
        cl.Image(name="Assistant", path=_avatar_path, display="inline"),
    ]

    welcome_msg = f"""{welcome_title}

📊 **右侧面板**查看训练画像与知识图谱，通过**下方功能栏**开始探索："""
    await cl.Message(content=welcome_msg, actions=actions, elements=expert_elements).send()

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
    try:
        active_vector_dir = get_preferred_vector_dir()
        chunks, vectorizer, matrix, bm25 = load_vector_kb(active_vector_dir)
        set_kb_data(chunks, vectorizer, matrix, retrieve, bm25=bm25)
        global_state.chunks = chunks
        global_state.kb_chunks_len = len(chunks)
        
        if matrix:
            cl.logger.info(f"全局知识库加载成功！当前目录: {active_vector_dir}")
        else:
            cl.logger.warning(f"全局知识库以空库模式启动（未找到 FAISS 索引）。当前目录: {active_vector_dir}")
    except Exception as e:
        error_msg = str(e)
        cl.logger.error(f"全局知识库加载失败: {error_msg}")
        set_kb_data([], None, None, retrieve)

def _build_profile_section(profile: dict) -> str:
    """构建运动员档案段（PB + 心率/配速区间）"""
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

    hz = profile.get("hr_zones", {})
    pz = profile.get("pace_zones", {})

    zones_rows = []
    for i in range(1, 10):
        key = f"Z{i}"
        label = ZONE_LABELS.get(key, key)
        hr_val = hz.get(key, "—")
        pace_val = pz.get(key, "—")
        zones_rows.append(f"| **{key} ({label})** | {hr_val} | {pace_val} |")
    zones_table = "\n".join(zones_rows)

    pb_str = f"""| 5k | 10k | 半马 | 全马 |
| :--- | :--- | :--- | :--- |
| {profile.get('pb_5k', '-')} | {profile.get('pb_10k', '-')} | {profile.get('pb_half', '-')} | {profile.get('pb_full', '-')} |"""

    return f"""### 🏃‍♂️ 运动员档案

**核心指标**
- **当前跑量**: `{profile.get('weekly_mileage', 0)} km/周`
- **乳酸阈 (LTHR)**: `{profile.get('lthr', 0)} bpm`
- **乳酸阈配速**: `{profile.get('t_pace', '-')} min/km`
- **目标赛事**: `{profile.get('goal', '未知')}`
- **赛事倒计时**: `{countdown_str}`

**最佳成绩 (PB)**
{pb_str}

**心率区间与配速（Z1-Z9）**
| 区间 | 心率范围 (LTHR) | 配速范围 (T-Pace) |
| :--- | :--- | :--- |
{zones_table}"""


def _build_graph_section() -> str:
    """构建知识图谱统计段"""
    node_count = len(graph_engine.nodes) if graph_engine else 0
    edge_count = len(graph_engine.edges) if graph_engine else 0
    chunk_count = len(KB_CHUNKS)

    unique_files = set(c.get("source_file") for c in KB_CHUNKS if "source_file" in c)
    density = edge_count / node_count if node_count > 0 else 0

    return f"""### 🧠 知识图谱

**图谱规模**
- **核心实体**: `{node_count}`
- **逻辑关联**: `{edge_count}`
- **知识密度**: `{density:.2f} 关系/节点`

**索引数据**
- **已索引文档**: `{len(unique_files)}` 篇
- **知识分片**: `{chunk_count}`
- **图谱状态**: `{"已就绪" if node_count > 0 else "待构建"}`"""


async def update_sidebar(profile_override=None):
    """更新侧边栏 — 双段式：运动员档案 + 知识图谱统计"""
    sidebar_visible = cl.user_session.get("sidebar_visible", True)

    if profile_override:
        profile = profile_override
    else:
        state = cl.user_session.get("state")
        profile = state.get("user_profile") if state else await cl.make_async(load_user_profile)()

    profile_section = _build_profile_section(profile)
    graph_section = _build_graph_section()
    sidebar_content = f"""{profile_section}

---

{graph_section}

---
*数据实时同步自个人画像与知识库*"""

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
