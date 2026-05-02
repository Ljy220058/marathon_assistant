import os
import sys
import asyncio
from pathlib import Path

# 将当前文件所在目录添加到 sys.path
current_dir = Path(__file__).parent.resolve()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import json
import shutil
import chainlit as cl
from workflow_engine import integrated_app, load_user_profile, IntegratedState, set_kb_data, KB_CHUNKS
from utils_ui import UIHelper
from graph_engine import graph_engine
from core_state import check_ollama_status, DEFAULT_VECTOR_DIR, UPLOAD_DOCS_DIR, BASE_DIR
from build_vector_kb import load_vector_kb, retrieve
from datetime import datetime, date
from module_kb import KBModule
from module_research import ResearchModule
from module_multimodal import MultimodalModule

# 初始化多模态模块
mm_module = MultimodalModule()

# 设置项目根目录 (BASE_DIR 已在上面初始化为 current_dir)
BASE_DIR = current_dir

def init_knowledge_base():
    """初始化全局知识库"""
    cl.logger.info("正在加载本地全局知识库 (Hybrid: TF-IDF + BM25)...")
    try:
        chunks, vectorizer, matrix, bm25 = load_vector_kb(DEFAULT_VECTOR_DIR)
        set_kb_data(chunks, vectorizer, matrix, retrieve, bm25=bm25)
        cl.logger.info("全局知识库加载成功！")
    except Exception as e:
        error_msg = str(e)
        cl.logger.error(f"全局知识库加载失败: {error_msg}")
        
        # 针对 Windows 特有的 HNSW 索引加载失败进行自动清理建议
        if "hnsw" in error_msg.lower() or "compaction" in error_msg.lower():
            cl.logger.warning("检测到索引文件损坏，建议进入‘知识库管理’点击‘重新构建索引’。")
            # 尝试清理损坏的索引目录（如果没被占用）
            chroma_dir = DEFAULT_VECTOR_DIR / "chroma_db"
            if chroma_dir.exists():
                try:
                    shutil.rmtree(chroma_dir)
                    cl.logger.info("已自动清理损坏的索引目录，请重新构建。")
                except:
                    cl.logger.warning("无法自动清理索引目录，请手动删除 vector_kb/chroma_db 文件夹。")
        
        set_kb_data([], None, None, retrieve)

init_knowledge_base()

async def update_sidebar(profile_override=None):
    """根据当前模式更新侧边栏常驻画像"""
    chat_profile = cl.user_session.get("chat_profile")
    
    # 优先使用传入的 profile，其次从 session 中获取，最后从本地加载
    if profile_override:
        profile = profile_override
    else:
        state = cl.user_session.get("state")
        if state and "user_profile" in state:
            profile = state["user_profile"]
        else:
            profile = load_user_profile()
            
    sidebar_visible = cl.user_session.get("sidebar_visible", True)
    
    # 1. 确定侧边栏名称和内容
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
        
        sidebar_content = f"""### 🏃‍♂️ 运动员档案 (Coach)
        
**核心指标**
- **当前跑量**: `{profile.get('weekly_mileage', 0)} km/周`
- **乳酸阈 (LTHR)**: `{profile.get('lthr', 0)} bpm`
- **乳酸阈配速**: `{profile.get('t_pace', '-')} min/km`
- **目标赛事**: `{profile.get('goal', '未知')}`
- **赛事倒计时**: `{countdown_str}`

**区间映射 (Z1-Z5)**
| 区间 | 心率 | 配速 |
| :--- | :--- | :--- |
| **Z1** | {hz.get('Z1', '-').split(' ')[0]} | {pz.get('Z1', '-')} |
| **Z2** | {hz.get('Z2', '-').split(' ')[0]} | {pz.get('Z2', '-')} |
| **Z3** | {hz.get('Z3', '-').split(' ')[0]} | {pz.get('Z3', '-')} |
| **Z4** | {hz.get('Z4', '-').split(' ')[0]} | {pz.get('Z4', '-')} |
| **Z5** | {hz.get('Z5', '-').split(' ')[0]} | {pz.get('Z5', '-')} |

**个人 PB**
- **5k**: `{profile.get('pb_5k', '-')}` | **10k**: `{profile.get('pb_10k', '-')}`
- **半马**: `{profile.get('pb_half', '-')}` | **全马**: `{profile.get('pb_full', '-')}`

---
*数据实时同步自个人画像文件*
"""
    else:
        name = "Graph Intelligence"
        node_count = len(graph_engine.nodes)
        edge_count = len(graph_engine.edges)
        chunk_count = len(KB_CHUNKS)
        
        unique_files = set()
        for chunk in KB_CHUNKS:
            if "source_file" in chunk:
                unique_files.add(chunk["source_file"])
        
        # 统计视觉知识来源
        visual_sources = set()
        for node in graph_engine.nodes.values():
            for src in node.get("source_chunks", []):
                if src.startswith("img:"):
                    visual_sources.add(src)
        
        # 安全计算知识密度，防止除以零
        density = edge_count / node_count if node_count > 0 else 0
        
        sidebar_content = f"""### 🧠 知识图谱统计 (Research)

**图谱规模**
- **核心实体 (Nodes)**: `{node_count}`
- **逻辑关联 (Edges)**: `{edge_count}`
- **知识密度**: `{density:.2f} 关系/节点`

**索引数据**
- **已索引文档**: `{len(unique_files)}` 篇
- **视觉知识源**: `{len(visual_sources)}` 张图片
- **知识分片 (Chunks)**: `{chunk_count}`
- **图谱状态**: `{"已就绪" if node_count > 0 else "待构建"}`

---
*点击下方 [构建 AI 知识图谱] 可更新统计数据*
"""

    # 2. 获取侧边栏消息句柄
    sidebar_msg = cl.user_session.get("sidebar_msg")
    
    # 3. 如果不显示侧边栏，则更新为占位符或提示
    if not sidebar_visible:
        if sidebar_msg:
            element = cl.Text(name=name, content="*档案已收起 (点击主界面按钮重新打开)*", display="side", for_id=sidebar_msg.id)
            await element.send(for_id=sidebar_msg.id)
        return

    # 4. 正常更新侧边栏内容
    if sidebar_msg:
        # 直接更新侧边栏元素，关联到已有的消息 ID
        element = cl.Text(name=name, content=sidebar_content, display="side", for_id=sidebar_msg.id)
        await element.send(for_id=sidebar_msg.id)
    else:
        # 先发送消息，获取其 ID，再发送侧边栏元素
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
    # 防止重复初始化
    if cl.user_session.get("initialized"):
        return
    
    # 0. 获取当前选择的 Profile
    chat_profile = cl.user_session.get("chat_profile")
    
    # 1. 加载用户画像
    profile = load_user_profile()
    
    # 2. 初始化状态
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
    cl.user_session.set("sidebar_visible", True) # 默认显示
    
    # 3. 发送欢迎消息和详细画像展示
    await show_profile_summary(profile, chat_profile)
    
    # 4. 初始化侧边栏
    await update_sidebar()
    
    # 标记已初始化
    cl.user_session.set("initialized", True)

async def show_profile_summary(profile, profile_name="Coach Mode"):
    hz = profile.get("hr_zones", {})
    pz = profile.get("pace_zones", {})
    pb_str = f"""
| 800m | 1500m | 5k | 10k | 半马 | 全马 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| {profile.get('pb_800m', '-')} | {profile.get('pb_1500m', '-')} | {profile.get('pb_5k', '-')} | {profile.get('pb_10k', '-')} | {profile.get('pb_half', '-')} | {profile.get('pb_full', '-')} |
"""
    zones_str = f"""
| 区间 | 心率范围 (Coros) | 配速范围 (T-Pace 映射) |
| :--- | :--- | :--- |
| **Z1 (轻松)** | {hz.get('Z1', '-')} | {pz.get('Z1', '-')} |
| **Z2 (有氧)** | {hz.get('Z2', '-')} | {pz.get('Z2', '-')} |
| **Z3 (马拉松)** | {hz.get('Z3', '-')} | {pz.get('Z3', '-')} |
| **Z4 (乳酸阈)** | {hz.get('Z4', '-')} | {pz.get('Z4', '-')} |
| **Z5 (间歇)** | {hz.get('Z5', '-')} | {pz.get('Z5', '-')} |
"""
    
    # 确定显示状态标签
    sidebar_visible = cl.user_session.get("sidebar_visible", True)
    toggle_label = "隐藏侧边栏" if sidebar_visible else "打开侧边栏"
    toggle_icon = "visibility_off" if sidebar_visible else "visibility"

    if profile_name == "Coach Mode":
        welcome_title = "🏃‍♂️ **你好！我是您的 AI 跑步教练 (Coach Mode)**"
        welcome_intro = "我将根据您的生理数据和训练反馈，为您提供专业的自适应计划指导。"
        actions = [
            cl.Action(name="adaptive_plan", payload={"value": "adaptive"}, label="自适应调整", icon="bolt"),
            cl.Action(name="refresh_profile", payload={"value": "refresh"}, label="刷新画像", icon="refresh"),
            cl.Action(name="toggle_sidebar", payload={"value": "toggle"}, label=toggle_label, icon=toggle_icon),
            cl.Action(name="manage_kb", payload={"value": "kb"}, label="知识库管理", icon="settings")
        ]
    else:
        welcome_title = "🧠 **你好！我是您的 科学研究助手 (Research Mode)**"
        welcome_intro = "我将利用 GraphRAG 技术，帮您从海量文献中挖掘跑步科学的深度联系。"
        actions = [
            cl.Action(name="search_graph", payload={"value": "search"}, label="搜索图谱", icon="search"),
            cl.Action(name="cross_research", payload={"value": "research"}, label="交叉研究", icon="hub"),
            cl.Action(name="multimodal_lab", payload={"value": "lab"}, label="多模态实验室", icon="image"),
            cl.Action(name="toggle_sidebar", payload={"value": "toggle"}, label=toggle_label, icon=toggle_icon),
            cl.Action(name="manage_kb", payload={"value": "kb"}, label="知识库管理", icon="settings")
        ]

    # 4. 构造欢迎消息中的专家团队头像元素 (Chainlit 2.x 标准做法：将元素绑定到消息中展示)
    expert_elements = [
        cl.Image(name="Coach", url="https://api.dicebear.com/7.x/avataaars/svg?seed=Coach&backgroundColor=b6e3f4", display="inline"),
        cl.Image(name="Nutritionist", url="https://api.dicebear.com/7.x/avataaars/svg?seed=Nutritionist&backgroundColor=ffdfbf", display="inline"),
        cl.Image(name="Therapist", url="https://api.dicebear.com/7.x/avataaars/svg?seed=Therapist&backgroundColor=c0aede", display="inline"),
        cl.Image(name="Auditor", url="https://api.dicebear.com/7.x/avataaars/svg?seed=Auditor&backgroundColor=ffd5dc", display="inline"),
        cl.Image(name="Logic Engine", url="https://api.dicebear.com/7.x/bottts/svg?seed=Logic&colors[]=blue", display="inline")
    ]

    welcome_msg = f"""{welcome_title}

{welcome_intro}

**您的当前画像：**
- **基本信息**: {profile.get('experience_level', '未知')} | {profile.get('goal', '未知')}
- **核心数据**: 周跑量 {profile.get('weekly_mileage', 0)}km | LTHR {profile.get('lthr', 0)}bpm | T-Pace {profile.get('t_pace', '-')}
- **目标赛事**: {profile.get('target_race_date', '未设置')} ({profile.get('plan_duration_weeks', 0)}周计划)

**最佳成绩 (PB):**
{pb_str}

**心率区间配速:**
{zones_str}

---
您可以直接提问，或通过下方功能菜单探索：
"""
    await cl.Message(content=welcome_msg, actions=actions, elements=expert_elements).send()

@cl.action_callback("extract_pdf_visuals")
async def on_extract_pdf_visuals(action: cl.Action):
    await action.remove()
    pdf_path = action.payload.get("path")
    pdf_name = action.payload.get("name")
    
    msg_status = cl.Message(content=f"🧠 **正在解析 PDF `{pdf_name}` 并提取图表知识...**")
    await msg_status.send()
    
    try:
        # 增加进度反馈：由于提取可能很慢，这里先告知用户正在进行
        cl.logger.info(f"开始提取 PDF 视觉知识: {pdf_name}, 路径: {pdf_path}")
        
        # 提取逻辑
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
            
        # 更新状态消息为完成
        msg_status.content = f"✅ **PDF `{pdf_name}` 视觉知识提取完成！**"
        await msg_status.update()
        
        await cl.Message(content=report_md).send()
        
        # 保存到 session 供注入
        cl.user_session.set("last_multimodal_desc", full_description)
        cl.user_session.set("last_multimodal_source", f"pdf:{pdf_name}")
        
        actions = [
            cl.Action(name="inject_multimodal", payload={"value": "inject"}, label="注入知识图谱", icon="share")
        ]
        await cl.Message(content="是否将上述从 PDF 中提取的视觉知识注入到您的本地知识图谱中？", actions=actions).send()
        
    except Exception as e:
        await cl.Message(content=f"❌ **提取失败**: {str(e)}").send()

@cl.action_callback("toggle_sidebar")
async def on_toggle_sidebar(action: cl.Action):
    # 切换显示状态
    current_status = cl.user_session.get("sidebar_visible", True)
    new_status = not current_status
    cl.user_session.set("sidebar_visible", new_status)
    
    # 更新侧边栏内容
    await update_sidebar()
    
    # 更新按钮标签 (通过发送一条新消息提示或刷新欢迎消息)
    # 由于欢迎消息已经发送，最简单的办法是发送一条状态反馈
    status_text = "✅ 侧边栏档案已显示" if new_status else "🙈 侧边栏档案已收起"
    await cl.Message(content=status_text).send()
    
    # 移除当前动作按钮，并建议用户刷新页面或等待下次触发
    await action.remove()

@cl.action_callback("multimodal_lab")
async def on_multimodal_lab(action: cl.Action):
    await action.remove()
    
    # 1. 引导用户上传图片
    files = await cl.AskFileMessage(
        content="🖼️ 请上传需要分析的跑步科学图表、训练照片或数据截图 (支持 JPG, PNG, WEBP)：",
        accept=["image/jpeg", "image/png", "image/webp"],
        max_files=1
    ).send()
    
    if not files: return
    image_file = files[0]
    
    # 2. 引导用户输入 Prompt
    res_prompt = await cl.AskUserMessage(content="💭 您想让模型分析什么？（例如：'详细描述图表内容' 或 '提取其中的训练指标'，直接发送使用默认 Prompt）：").send()
    prompt = res_prompt['output'] if res_prompt and res_prompt['output'].strip() else "请详细描述这张图片中的跑步科学知识，包括任何图表数据、技术动作或生理指标。如果是对比图，请指出差异。"
    
    # 3. 调用 VLM 对比
    msg_status = cl.Message(content=f"🚀 **正在启动本地多模态模型 (LLaVA & Llama 3.2-Vision)...**")
    await msg_status.send()
    
    try:
        results = await mm_module.compare_vlms(image_file.path, prompt)
        
        # 4. 展示对比结果
        comparison_md = f"### 🖼️ 多模态对比分析: `{image_file.name}`\n\n"
        comparison_md += f"**用户指令**: `{prompt}`\n\n"
        
        for model, content in results.items():
            icon = "🦙" if "llama" in model.lower() else "🌋"
            comparison_md += f"#### {icon} {model}\n{content}\n\n---\n"
            
        await cl.Message(content=comparison_md).send()
        
        # 5. 提供注入图谱的选项
        cl.user_session.set("last_multimodal_desc", "\n\n".join(results.values()))
        cl.user_session.set("last_multimodal_source", f"img:{image_file.name}")
        
        actions = [
            cl.Action(name="inject_multimodal", payload={"value": "inject"}, label="注入知识图谱", icon="share"),
            cl.Action(name="multimodal_lab", payload={"value": "retry"}, label="分析另一张", icon="refresh")
        ]
        await cl.Message(content="是否将上述视觉知识提取并注入到您的本地知识图谱中？", actions=actions).send()
        
    except Exception as e:
        await cl.Message(content=f"❌ **分析失败**: {str(e)}").send()

@cl.action_callback("inject_multimodal")
async def on_inject_multimodal(action: cl.Action):
    await action.remove()
    
    description = cl.user_session.get("last_multimodal_desc")
    source_id = cl.user_session.get("last_multimodal_source")
    
    if not description or not source_id:
        await cl.Message(content="⚠️ **未找到待注入的描述内容**").send()
        return
        
    msg_status = cl.Message(content="🧠 **正在从描述中提取三元组并注入图谱...**")
    await msg_status.send()
    
    try:
        count = await graph_engine.add_multimodal_description(description, source_id)
        if count > 0:
            await cl.Message(content=f"✅ **注入成功！** 从视觉描述中提取了 `{count}` 条新知识关联。").send()
            # 更新侧边栏
            await update_sidebar()
        else:
            await cl.Message(content="⚠️ **注入完成，但未提取到有效的三元组。** 可能是描述内容不够结构化。").send()
    except Exception as e:
        await cl.Message(content=f"❌ **注入失败**: {str(e)}").send()

@cl.action_callback("search_graph")
async def on_search_graph(action: cl.Action):
    await action.remove()
    res = await cl.AskUserMessage(content="请输入要搜索的实体名称（如：Marathon, Recovery）：").send()
    if res:
        query = res['output']
        result = graph_engine.search_graph([query], max_hops=2)
        if not result["nodes"]:
            await cl.Message(content=f"❌ 未找到与 '{query}' 相关的实体").send()
            return
        
        details = f"### 📍 搜索结果: `{query}`\n\n"
        details += f"**找到 {len(result['nodes'])} 个相关知识节点：**\n"
        for nid, ninfo in result["nodes"].items():
            details += f"- 📍 **{ninfo.get('label')}** ({len(ninfo.get('source_chunks', []))} 个文档关联)\n"
            
        if result["edges"]:
            details += "\n**知识关联路径：**\n"
            for edge in result["edges"]:
                s_label = result["nodes"].get(edge["source"], {}).get("label", edge["source"])
                t_label = result["nodes"].get(edge["target"], {}).get("label", edge["target"])
                details += f"- {s_label} ➔ *{edge['relation']}* ➔ {t_label}\n"

        msg = cl.Message(content=details)
        await msg.send()
        
        # 仍然提供 Mermaid 作为可选的“可视化视图”，但放在 cl.Text 中默认折叠或作为附件
        mermaid_code = graph_engine.generate_mermaid(nodes=result["nodes"], edges=result["edges"])
        await cl.Text(name="Visual Graph (Mermaid)", content=f"```mermaid\n{mermaid_code}\n```", display="inline", for_id=msg.id).send(for_id=msg.id)

@cl.action_callback("cross_research")
async def on_cross_research(action: cl.Action):
    await action.remove()
    res_entities = await cl.AskUserMessage(content="请输入要分析的多个实体名称，用逗号分隔（如：Endurance, T-Pace, VO2Max）：").send()
    if not res_entities: return
    
    entities = [e.strip() for e in res_entities['output'].split(",") if e.strip()]
    
    res_focus = await cl.AskUserMessage(content="请输入研究侧重点（可选，直接发送跳过）：").send()
    focus = res_focus['output'] if res_focus else f"深度对比分析这些实体：{', '.join(entities)}"
    
    state = cl.user_session.get("state")
    state["query"] = focus
    state["mode"] = "research"
    state["selected_entities"] = entities
    cl.user_session.set("state", state)
    
    await main(cl.Message(content=focus))

@cl.action_callback("manage_kb")
async def on_manage_kb(action: cl.Action):
    # 立即发送响应，让用户知道系统已接收点击
    status_msg = cl.Message(content="🛠️ **正在加载知识库清单...**")
    await status_msg.send()
    
    try:
        await action.remove()
        kb = KBModule()
        inventory_md = kb.get_file_inventory_md()
        
        # 更新状态消息
        status_msg.content = "🛠️ **知识库管理**\n\n您可以查看当前文件，或通过下方功能菜单操作。"
        await status_msg.update()
        
        # 展示文件清单
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

    # 如果文件太多，限制展示
    display_files = files[:10]
    actions = [
        cl.Action(name="view_pdf", payload={"path": str(f.resolve()), "name": f.name}, label=f"📄 {f.name[:20]}...") 
        for f in display_files
    ]
    
    await cl.Message(content="请选择要预览的 PDF 文件：", actions=actions).send()

@cl.action_callback("view_pdf")
async def on_view_pdf(action: cl.Action):
    # 对于查看 PDF，我们不一定需要 remove action，因为用户可能想点多次
    path = action.payload.get("path")
    name = action.payload.get("name")
    page = action.payload.get("page", 1)
    
    if path and os.path.exists(path):
        pdf_element = cl.Pdf(name=name, path=path, display="side", page=page)
        msg = cl.Message(content=f"📑 **正在预览: {name}** (第 {page} 页)")
        await msg.send()
        pdf_element.for_id = msg.id
        await pdf_element.send(for_id=msg.id)
    else:
        await cl.Message(content=f"❌ **无法找到文件**: {path}").send()

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
            cl.Action(name="build_graph_ai", payload={"mode": "full"}, label="全量重构图谱（推荐）", icon="refresh"),
            cl.Action(name="build_graph_ai", payload={"mode": "incremental"}, label="增量更新图谱", icon="share")
        ]
        await cl.Message(content="现在要构建索引或更新图谱吗？", actions=actions).send()

@cl.action_callback("build_graph_ai")
async def on_build_graph(action: cl.Action):
    await action.remove()
    mode = action.payload.get("mode", "incremental")
    is_incremental = (mode == "incremental")
    
    # 显示构建状态
    msg_status = cl.Message(content=f"🛠️ **正在{'增量更新' if is_incremental else '全量重构'}知识图谱...**")
    await msg_status.send()
    
    research = ResearchModule()
    status, mermaid = await research.build_graph_ui(incremental=is_incremental)
    
    # 更新状态消息
    msg_status.content = status
    await msg_status.update()
    
    if mermaid:
        # 生成简要统计
        node_count = len(graph_engine.nodes)
        edge_count = len(graph_engine.edges)
        
        details = f"### 📊 知识图谱已更新 ({'增量' if is_incremental else '全量'})\n\n"
        details += f"- **核心实体 (Nodes)**: `{node_count}`\n"
        details += f"- **逻辑关联 (Edges)**: `{edge_count}`\n"
        density = edge_count / node_count if node_count > 0 else 0
        details += f"- **知识密度**: `{density:.2f} 关系/节点`\n\n"
        details += "> 💡 您可以通过 [搜索图谱] 按钮或直接提问来探索这些关联。"

        msg = cl.Message(content=details)
        await msg.send()
        
        # 将复杂的 Mermaid 图作为附件展示
        await cl.Text(name="Graph Visualization (Mermaid)", content=f"```mermaid\n{mermaid}\n```", display="inline", for_id=msg.id).send(for_id=msg.id)
    
    # 更新侧边栏统计
    await update_sidebar()

@cl.action_callback("reindex_kb")
async def on_reindex_kb(action: cl.Action):
    await action.remove()
    kb = KBModule()
    
    # 汇总所有可用文档目录并去重
    domain_docs = BASE_DIR / "domain_docs"
    
    file_map = {} # 使用文件名作为 key 进行去重
    dirs_to_scan = [UPLOAD_DOCS_DIR, domain_docs]
    
    for d in dirs_to_scan:
        if d.exists():
            for f in d.glob("*"):
                if f.is_file() and f.suffix.lower() in [".pdf", ".txt", ".md", ".docx"]:
                    # 优先保留 UPLOAD_DOCS_DIR 中的文件（通常是用户最新上传的）
                    if f.name not in file_map or d == UPLOAD_DOCS_DIR:
                        file_map[f.name] = f
    
    valid_files = list(file_map.values())
    
    if not valid_files:
        await cl.Message(content="⚠️ **未找到任何有效文档** (检查了 uploaded_docs 和 domain_docs)，请先上传文件。").send()
        return
    
    msg = cl.Message(content=f"🔨 **正在重新构建索引 ({len(valid_files)} 个文件)...**")
    await msg.send()
    
    # 采用 make_async 运行同步阻塞函数，防止阻塞事件循环
    status, meta = await cl.make_async(kb.build_kb)(valid_files, 500, 50)
    # 不再直接输出状态字符串，而是根据 meta 生成 Markdown 报告
    if meta:
        report_md = UIHelper.render_build_summary_md(meta)
        await cl.Message(content=report_md).send()
        
        # P0: 索引重建后，引导用户全量重构图谱
        actions = [
            cl.Action(name="build_graph_ai", payload={"mode": "full"}, label="全量重构图谱（推荐）", icon="refresh"),
            cl.Action(name="build_graph_ai", payload={"mode": "incremental"}, label="增量更新图谱", icon="share")
        ]
        await cl.Message(content="📚 **索引已更新**。建议立即进行**全量重构图谱**以保证知识关联的准确性：", actions=actions).send()
    else:
        # 如果没有 meta，说明可能彻底失败了，显示原始 status
        await cl.Message(content=f"❌ **构建过程中出现问题**\n{status}").send()
    
    # 更新侧边栏统计
    await update_sidebar()

@cl.action_callback("refresh_profile")
async def on_refresh(action: cl.Action):
    await action.remove()
    profile = load_user_profile()
    state = cl.user_session.get("state")
    state["user_profile"] = profile
    cl.user_session.set("state", state)
    await show_profile_summary(profile)
    # 更新侧边栏
    await update_sidebar()

@cl.action_callback("adaptive_plan")
async def on_adaptive(action: cl.Action):
    await action.remove()
    # 引导用户输入自适应反馈
    res = await cl.AskUserMessage(content="请输入您的近期反馈（例如：疲劳度1-10，是否漏掉训练，心率是否异常等）").send()
    if res:
        feedback_text = res['output']
        # 构造自适应调整的 Prompt
        query = f"【自适应调整请求】用户反馈：{feedback_text}。请根据此反馈调整我的训练计划。"
        await main(cl.Message(content=query))

@cl.on_message
async def main(message: cl.Message):
    # 1. 处理上传的文件
    image_descriptions = []
    if message.elements:
        UPLOAD_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        saved_files = []
        
        # 1.1 定义异步处理单张图片的函数
        async def process_image(element, file_path=None):
            # 如果没传 file_path，就用 element.path (虽然在 1.2 中我们已经改成了传 target_path)
            actual_path = file_path or element.path
            
            if not element.name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                return None
                
            msg_vlm = cl.Message(content=f"🎨 **检测到图片 `{element.name}`，正在理解内容...**\n> 💡 提示: 初次加载 11B 多模态模型可能需要 1-2 分钟，请耐心等待。")
            await msg_vlm.send()
            
            try:
                # 使用传入的 file_path (即已持久化保存的路径) 保证安全性
                desc = await mm_module.call_vlm("llama3.2-vision:11b", "请简要描述这张图片的内容，以便我将其作为对话上下文。", actual_path)
                
                if "错误" in desc:
                    cl.logger.warning(f"VLM 理解失败: {desc}")
                    msg_vlm.content = f"⚠️ 图片 `{element.name}` 理解遇到问题: {desc}"
                    await msg_vlm.update()
                    return None
                else:
                    msg_vlm.content = f"✅ **图片理解完成**：{desc[:100]}..."
                    await msg_vlm.update()
                    return f"【图片内容: {element.name}】\n{desc}"
            except Exception as e:
                cl.logger.error(f"VLM error: {e}")
                msg_vlm.content = f"⚠️ 图片 `{element.name}` 理解过程中发生异常，将作为普通文件处理。"
                await msg_vlm.update()
                return None

        # 1.2 并行处理所有图片
        tasks = []
        for element in message.elements:
            if isinstance(element, (cl.File, cl.Image)):
                # 统一保存到上传目录
                UPLOAD_DOCS_DIR.mkdir(parents=True, exist_ok=True)
                target_path = UPLOAD_DOCS_DIR / element.name
                
                # 安全复制文件，防止 Chainlit 临时文件提前被系统回收
                try:
                    if element.path and os.path.exists(element.path):
                        shutil.copy(element.path, target_path)
                        saved_files.append(element.name)
                        cl.logger.info(f"成功保存文件: {element.name} -> {target_path}")
                    else:
                        # 记录警告而不是直接报错，因为某些 element 可能确实没有物理路径
                        cl.logger.warning(f"无法保存文件: {element.name}，原始路径不存在或已失效: {element.path}")
                except Exception as e:
                    cl.logger.error(f"复制文件 {element.name} 失败: {e}")
                    # 如果复制失败，我们依然尝试继续处理其他文件
                
                # 添加到并行处理任务 (仅当本地文件存在时，使用 target_path 保证安全性)
                if element.name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and target_path.exists():
                    tasks.append(process_image(element, str(target_path)))
        
        if tasks:
            results = await asyncio.gather(*tasks)
            image_descriptions = [r for r in results if r]
        
        if saved_files: # 修改：只要有保存的文件就处理，不再排斥图片描述
            # 发送文件保存成功的反馈 (仅当包含非图片文件时，或者显式需要处理文件时)
            other_files = [f for f in saved_files if not f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
            if other_files:
                await cl.Message(content=f"✅ **检测到上传文件并保存到知识库：**\n- " + "\n- ".join(other_files)).send()
            
            # 如果包含 PDF，提供视觉提取选项
            pdf_files = [f for f in saved_files if f.lower().endswith('.pdf')]
            actions = [
                cl.Action(name="reindex_kb", payload={"value": "reindex"}, label="立即构建索引", icon="build"),
                cl.Action(name="build_graph_ai", payload={"mode": "incremental"}, label="增量更新图谱", icon="share")
            ]
            
            if pdf_files:
                actions.insert(0, cl.Action(
                    name="extract_pdf_visuals", 
                    payload={"path": str((UPLOAD_DOCS_DIR / pdf_files[0]).resolve()), "name": pdf_files[0]}, 
                    label="🧠 提取 PDF 视觉知识", 
                    icon="auto_awesome"
                ))
                
            await cl.Message(content="是否需要进行索引或提取 PDF 视觉知识？", actions=actions).send()

    # 2. 检查 Ollama 状态
    if not await check_ollama_status():
        await cl.Message(content="❌ **Ollama 服务未在线**，请确保本地 11434 端口服务已启动。").send()
        return

    # 2.1 特殊逻辑：如果用户只上传了文件且没有输入文字，则停止后续工作流，让用户使用上面的按钮
    if not message.content.strip() and message.elements:
        return

    state = cl.user_session.get("state")
    
    # 3. 构造增强后的查询 (包含图片描述)
    full_query = message.content
    if image_descriptions:
        full_query = "\n\n".join(image_descriptions) + f"\n\n**用户问题**: {message.content}"
    
    # 4. 状态清理与上下文维护
    # 将上一轮的最终结果存入历史（如果存在）
    if state.get("final_report"):
        state["history"].append({"role": "assistant", "content": state["final_report"]})
    
    # 清理本轮输出字段，防止状态污染
    state["query"] = full_query
    state["history"].append({"role": "user", "content": message.content})
    state["final_report"] = ""
    state["draft_plan"] = ""
    state["reasoning_log"] = []
    state["rag_sources"] = []
    state["structured_report"] = None
    state["iteration_count"] = 0
    state["is_approved"] = False
    
    # 3. 执行工作流并处理流式事件
    # 创建主消息用于流式输出
    msg = cl.Message(content="")
    await msg.send()
    
    active_node = None
    active_step = None
    final_state = state.copy()
    
    try:
        async for event in integrated_app.astream_events(state, version="v2"):
            kind = event["event"]
            name = event.get("name", "")
            
            # 1. 捕获节点开始 (推理日志)
            if kind == "on_chain_start" and name in ["coach", "nutritionist", "therapist", "auditor", "formatter", "profiler", "router", "entity_extraction", "wiki_search", "planner", "executor", "guided_questions_generator", "research_analyst", "adaptive_coach"]:
                active_node = name
                if active_step:
                    await active_step.remove()
                active_step = cl.Step(name=f"⚙️ {name.capitalize()}", type="run")
                await active_step.send()
                active_step.output = f"正在执行 {name} 节点..."
                await active_step.update()

            # 2. 捕获流式输出 - 仅当是最终报告生成节点时才流式展示给用户
            elif kind == "on_chat_model_stream":
                # 只有特定的展示型节点才流式展示给用户
                if active_node in ["coach", "research_analyst", "adaptive_coach", "formatter", "executor", "missing_info_handler"]:
                    chunk = event["data"]["chunk"]
                    content = chunk.content
                    if content:
                        # 增加一个简单的 JSON 防御：如果内容以 { 开头且看起来像 JSON，则不流式展示
                        # (这通常发生在模型忽略了 Markdown 指令时)
                        if content.strip().startswith("{") and active_node != "formatter":
                            # 如果是在 formatter 节点，可能是正常的（虽然我们希望它输出 Markdown）
                            # 但在 coach/executor 等节点，这通常是泄露
                            pass 
                        else:
                            await msg.stream_token(content)

            # 3. 捕获节点结束 (状态同步)
            elif kind == "on_chain_end":
                if name in ["coach", "nutritionist", "therapist", "auditor", "formatter", "profiler", "router", "entity_extraction", "wiki_search", "planner", "executor", "guided_questions_generator", "research_analyst", "adaptive_coach"]:
                    output = event["data"].get("output", {})
                    if not isinstance(output, dict):
                        continue
                    
                    # 增量更新 final_state
                    final_state.update(output)
                    
                    # 推理日志实时展示
                    if "reasoning_log" in output and output["reasoning_log"]:
                        for log in output["reasoning_log"]:
                            await cl.Message(content=f"📝 `{log}`", author="System Log").send()
                    
                    # 4. 推理链路展示 (不再使用 Mermaid，改用结构化 Markdown)
                    if "entities" in output and output["entities"]:
                        entities = output["entities"]
                        graph_ctx = output.get("graph_context", "")
                        
                        flow_md = UIHelper.render_reasoning_flow_md(entities, graph_ctx)
                        # 确保 Logic Engine 头像能够正确显示
                        expert_elements = [
                            cl.Image(name="Logic Engine", url="https://api.dicebear.com/7.x/bottts/svg?seed=Logic&colors[]=blue", display="inline")
                        ]
                        msg_flow = cl.Message(content=flow_md, author="Logic Engine", elements=expert_elements)
                        await msg_flow.send()
                    
                    # 实时同步 RAG 来源
                    if "rag_sources" in output and output["rag_sources"]:
                        sources = output["rag_sources"]
                        for i, src in enumerate(sources):
                            source_name = src.get('source', '未知')
                            page = src.get('page', 1)
                            score = src.get('score', 0.0)
                            snippet = src.get('snippet', '')
                            
                            content = f"来源: {source_name}\n页面: {page}\n得分: {score:.2f}\n\n{snippet}"
                            
                            # 尝试定位物理文件路径以支持预览
                            domain_docs = BASE_DIR / "domain_docs"
                            file_path = None
                            for d in [UPLOAD_DOCS_DIR, domain_docs]:
                                target = d / source_name
                                if target.exists():
                                    file_path = str(target.resolve())
                                    break
                            
                            actions = []
                            if file_path and source_name.lower().endswith('.pdf'):
                                actions.append(cl.Action(
                                    name="view_pdf", 
                                    payload={"path": file_path, "name": source_name, "page": page, "value": f"{source_name}_p{page}"}, 
                                    label=f"📄 预览第 {page} 页"
                                ))
                            
                            msg = cl.Message(content=f"📚 **相关证据 {i+1}**", actions=actions)
                            await msg.send()
                            await cl.Text(name=f"Source {i+1} Snippet", content=content, display="inline", for_id=msg.id).send(for_id=msg.id)
                    
                    # 如果有风险警报
                    if "risk_alert" in output and output["risk_alert"]:
                        await cl.Message(content=f"⚠️ **审计提示**\n{output['risk_alert']}").send()
                
                # 捕获整个图的结束，获取完整状态
                elif name == "LangGraph": # 或者根据具体版本可能是 "__root__" 或空
                     output = event["data"].get("output")
                     if output:
                         final_state = output

        # 4. 最终报告展示
        cl.user_session.set("state", final_state)
        
        # 使用 UIHelper 渲染更美观的报告 (Task: UI Beautification)
        final_report_html = UIHelper.render_structured_report(
            final_state.get("structured_report"), 
            final_state.get("final_report")
        )
        
        # 将最终格式化后的报告更新到主消息中
        if final_report_html:
            # 如果之前有流式内容，直接更新。如果没有，则发送新消息（兜底）
            if msg:
                msg.content = final_report_html
                await msg.update()
            else:
                await cl.Message(content=final_report_html).send()
        
        # 发送 Token 统计和 ROI
        usage = final_state.get("token_usage", {})
        roi_score = final_state.get("audit_scores", {}).get("roi", 0)
        token_md = UIHelper.generate_token_md(
            {"Prompt": usage.get("prompt_tokens", 0), 
             "Completion": usage.get("completion_tokens", 0), 
             "Total": usage.get("total_tokens", 0)},
            roi_score=roi_score
        )
        await cl.Message(content=token_md).send()
        
        # 发送引导式提问
        if final_state.get("guided_questions"):
            questions = final_state["guided_questions"]
            actions = [cl.Action(name="ask_question", payload={"value": q}, label=q, icon="help_outline") for q in questions]
            await cl.Message(content="💡 **您可以接着问：**", actions=actions).send()

        # 实时同步侧边栏画像 (确保计算出的区间能立即显示)
        await update_sidebar()

    except Exception as e:
        await cl.Message(content=f"❌ **发生错误**: {str(e)}").send()

@cl.action_callback("ask_question")
async def on_action(action: cl.Action):
    await action.remove()
    query = action.payload.get("value")
    if query:
        await main(cl.Message(content=query))
