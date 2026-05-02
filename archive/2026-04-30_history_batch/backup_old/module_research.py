import re
import gradio as gr
from core_state import global_state, DEFAULT_HIGHLIGHTS
from graph_engine import graph_engine
from workflow_engine import IntegratedState, integrated_app, load_user_profile
from utils_ui import UIHelper

class ResearchModule:
    def __init__(self):
        self.mermaid_explorer = None
        self.search_results_info = None
        self.entity_selector = None
        self.graph_search_input = None
        self.graph_search_hops = None
        self.graph_search_btn = None
        self.refresh_explorer_btn = None
        self.last_trace_btn = None
        self.research_query_input = None
        self.analyze_entities_btn = None
        self.entity_source_display = None

    async def build_graph_ui(self, incremental: bool = True):
        """UI 回调：构建知识图谱"""
        if not global_state.chunks:
            return "请先构建向量知识库以获取文本分片", ""
        
        try:
            n_nodes, n_edges = await graph_engine.build_graph(global_state.chunks, incremental=incremental)
            mermaid_code = graph_engine.generate_mermaid(highlight_phrases=DEFAULT_HIGHLIGHTS)
            return f"✅ 图谱构建成功！目前共有 {n_nodes} 个实体，{n_edges} 条关系。", f"```mermaid\n{mermaid_code}\n```"
        except Exception as e:
            return f"❌ 构建失败：{str(e)}", ""

    def search_graph_ui(self, search_query: str, max_hops: int = 2):
        """UI 回调：搜索图谱并展示子图"""
        if not search_query:
            mermaid_code = graph_engine.generate_mermaid(limit=50, highlight_phrases=DEFAULT_HIGHLIGHTS)
            return f"```mermaid\n{mermaid_code}\n```", "<div style='color: var(--text-secondary); padding: 10px;'>请输入实体名称进行搜索</div>", gr.update(choices=[], value=[])
        
        result = graph_engine.search_graph([search_query], max_hops=int(max_hops))
        if not result["nodes"]:
            return "flowchart TD\n  Empty[未找到相关实体]", f"未找到与 '{search_query}' 相关的实体", []
        
        mermaid_code = graph_engine.generate_mermaid(nodes=result["nodes"], edges=result["edges"], highlight_phrases=DEFAULT_HIGHLIGHTS)
        
        details_html = f"<div style='margin-top: 10px;'><strong>找到 {len(result['nodes'])} 个相关节点：</strong><ul style='list-style-type: none; padding-left: 0;'>"
        entity_list = []
        for nid, ninfo in result["nodes"].items():
            label = ninfo.get("label")
            if not label or re.match(r'^[0-9a-f]{12}$', str(label).lower().strip()):
                continue
                
            chunks_count = len(ninfo.get("source_chunks", []))
            details_html += f"<li style='margin-bottom: 8px; padding: 8px; background: var(--bg-交互); border-radius: 4px;'>📍 <b>{label}</b> (来源: {chunks_count} 个分片)</li>"
            entity_list.append(label)
        details_html += "</ul></div>"
        
        return f"```mermaid\n{mermaid_code}\n```", details_html, gr.update(choices=entity_list, value=[entity_list[0]] if entity_list else [])

    def get_entity_source_chunks(self, entity_labels):
        """获取实体(单/多)的来源分片内容"""
        if not entity_labels:
            return "请选择实体以查看其来源内容"
            
        labels = entity_labels if isinstance(entity_labels, list) else [entity_labels]
        
        all_chunk_ids = set()
        found_labels = []
        for label in labels:
            for nid, ninfo in graph_engine.nodes.items():
                if ninfo.get("label") == label:
                    all_chunk_ids.update(ninfo.get("source_chunks", []))
                    found_labels.append(label)
                    break
                    
        if not all_chunk_ids:
            return f"实体 '{', '.join(labels)}' 没有关联的来源分片"
            
        source_chunk_ids = list(all_chunk_ids)
        
        matched_chunks = [c for c in global_state.chunks if c["chunk_id"] in source_chunk_ids]
        
        if not matched_chunks:
            return f"无法加载选中实体的分片内容 (分片可能已被重置)"
        
        html = f"<div style='max-height: 400px; overflow-y: auto; padding: 10px;'>"
        html += f"<div style='font-size:12px; color:var(--text-secondary); margin-bottom:10px;'>展示 <b>{', '.join(found_labels)}</b> 的关联片段 ({len(matched_chunks)} 个)：</div>"
        for i, c in enumerate(matched_chunks):
            html += f"""
            <div style="margin-bottom: 16px; border-bottom: 1px solid var(--bg-border); padding-bottom: 12px;">
                <div style="color: var(--primary-color); font-weight: 600; font-size: 12px; margin-bottom: 4px;">SOURCE {i+1} | {c.get('source_file', 'Unknown')} (P.{c.get('page', 1)})</div>
                <div style="font-size: 13px; color: var(--text-body); line-height: 1.5;">{c['text']}</div>
            </div>
            """
        html += "</div>"
        return html

    async def handle_research_analysis(self, selected_entities, query_focus):
        if not selected_entities:
            yield "<div class='github-flash-error'>请先在下拉框中选择至少一个实体进行分析。</div>"
            return
            
        yield f"<div class='reasoning-terminal'>正在启动 Cross-Document Analysis 引擎...<br/>分析实体: {', '.join(selected_entities)}</div>"
        
        state: IntegratedState = {
            "query": query_focus or f"深度对比分析以下实体之间的关系及其在文献中的共识与分歧：{', '.join(selected_entities)}",
            "mode": "research",
            "category": "research",
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
            "mermaid_graph": "",
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "audit_scores": {"consistency": 0, "safety": 0, "roi": 0, "summary": ""},
            "roi_history": [],
            "risk_alert": "",
            "entities": [],
            "guided_questions": [],
            "user_profile": load_user_profile(),
            "selected_entities": selected_entities if isinstance(selected_entities, list) else [selected_entities]
        }
        
        current_log = []
        final_html = ""
        log_counter = 0 # 日志计数器
        
        try:
            async for event in integrated_app.astream(state):
                for node_name, output in event.items():
                    if "reasoning_log" in output:
                        current_log.extend(output["reasoning_log"])
                        log_counter += 1
                        # 减少日志 yield 频率，每 3 条日志更新一次或在生成报告前更新
                        if log_counter % 3 == 0:
                            log_html = "<br/>".join([f"<span style='color:var(--info)'>$</span> {l}" for l in current_log])
                            yield f"<div class='reasoning-terminal'>{log_html}</div>"
                        
                    if "structured_report" in output and output["structured_report"]:
                        final_html = UIHelper.render_structured_report(output["structured_report"], output.get("final_report", ""))
                    elif "final_report" in output:
                        final_html = f"<div class='lab-report' style='white-space:pre-wrap;'>{output['final_report']}</div>"
                        
            if final_html:
                yield final_html
            else:
                yield "<div class='github-flash-warn'>分析完成，但未生成结构化报告。</div>"
                
        except Exception as e:
            yield f"<div class='github-flash-error'>交叉分析发生错误: {str(e)}</div>"

    def build_ui(self):
        with gr.Tab("🕸️ Graph Explorer", id="tab_graph"):
            with gr.Row():
                with gr.Column(scale=7):
                    with gr.Group(elem_classes="github-container"):
                        gr.HTML("<div class='github-header'>🔍 Entity Search & Sub-graph Visualization</div>")
                        with gr.Row():
                            self.graph_search_input = gr.Textbox(
                                placeholder="输入实体名称进行搜索 (如: Marathon)...", 
                                show_label=False,
                                scale=8
                            )
                            self.graph_search_btn = gr.Button("Search", variant="primary", scale=2)
                        self.graph_search_hops = gr.Slider(
                            minimum=1,
                            maximum=4,
                            step=1,
                            value=2,
                            label="Traversal Hops"
                        )
                        
                        self.mermaid_explorer = gr.Markdown(
                            value=f"```mermaid\n{graph_engine.generate_mermaid()}\n```",
                            elem_classes="mermaid-container",
                            height=600
                        )
                        with gr.Row():
                            self.refresh_explorer_btn = gr.Button("↻ Reset to Full Graph", variant="secondary", size="sm")
                            self.last_trace_btn = gr.Button("📍 Show Last Reasoning Trace", variant="secondary", size="sm")
                
                with gr.Column(scale=3):
                    with gr.Group(elem_classes="github-container"):
                        gr.HTML("<div class='github-header'>💡 Entity Intelligence</div>")
                        self.search_results_info = gr.HTML(value="<div style='color: var(--text-secondary); padding: 10px;'>搜索实体以解锁关联逻辑</div>")
                        self.entity_selector = gr.Dropdown(label="Select Entities for Analysis", choices=[], multiselect=True, interactive=True)
                        
                        self.research_query_input = gr.Textbox(label="Research Focus (Optional)", placeholder="例如：分析它们在马拉松表现中的协同作用...", lines=2)
                        self.analyze_entities_btn = gr.Button("🧠 Cross-Document Analysis (Multi-Agent)", variant="primary")
                        
                    with gr.Group(elem_classes="github-container"):
                        gr.HTML("<div class='github-header'>📖 Source Context / Report</div>")
                        self.entity_source_display = gr.HTML(
                            value="<div style='color: var(--text-secondary); padding: 20px; text-align: center;'>选择节点以追溯原始文档分片，或点击上方按钮生成交叉分析报告</div>",
                            elem_classes="reasoning-terminal"
                        )

        # 内部事件绑定
        self.refresh_explorer_btn.click(
            lambda: (f"```mermaid\n{graph_engine.generate_mermaid(highlight_phrases=DEFAULT_HIGHLIGHTS)}\n```", "<div style='color: var(--text-secondary); padding: 10px;'>已重置为全量图谱</div>", gr.update(choices=[], value=[]), ""),
            outputs=[self.mermaid_explorer, self.search_results_info, self.entity_selector, self.graph_search_input]
        )
        self.graph_search_btn.click(self.search_graph_ui, inputs=[self.graph_search_input, self.graph_search_hops], outputs=[self.mermaid_explorer, self.search_results_info, self.entity_selector])
        self.graph_search_input.submit(self.search_graph_ui, inputs=[self.graph_search_input, self.graph_search_hops], outputs=[self.mermaid_explorer, self.search_results_info, self.entity_selector])
        self.entity_selector.change(self.get_entity_source_chunks, inputs=[self.entity_selector], outputs=[self.entity_source_display])
        self.analyze_entities_btn.click(
            self.handle_research_analysis,
            inputs=[self.entity_selector, self.research_query_input],
            outputs=[self.entity_source_display]
        )
