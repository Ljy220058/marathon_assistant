import urllib.parse
import datetime
import shutil
from pathlib import Path
import gradio as gr

from core_state import BASE_DIR, DEFAULT_VECTOR_DIR, UPLOAD_DOCS_DIR, USER_VECTOR_DIR, global_state
from workflow_engine import set_kb_data, clear_kb_data
from build_vector_kb import load_vector_kb, retrieve, collect_chunks, build_hybrid_indices, save_outputs
from graph_engine import graph_engine

class KBModule:
    def __init__(self):
        # 暴露需要跨模块交互的组件
        self.kb_status = None
        self.file_inventory_display = None
        self.kb_dir = None
        self.kb_load_btn = None
        self.kb_build_btn = None
        self.kb_upload = None
        self.kb_chunk_size = None
        self.kb_chunk_overlap = None
        self.graph_build_btn = None
        self.kb_meta = None
        self.delete_file_btn = None
        self.delete_file_input = None
        self.refresh_kb_btn = None
        self.copy_btn = None

    def get_file_inventory_md(self):
        """获取知识库中的文件清单 (Markdown 格式)"""
        inventory = []
        for d in [UPLOAD_DOCS_DIR, BASE_DIR / "domain_docs"]:
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

    def get_file_inventory(self):
        """获取知识库中的文件清单"""
        inventory = []
        for d in [UPLOAD_DOCS_DIR, BASE_DIR / "domain_docs"]:
            if not d.exists(): continue
            for f in d.iterdir():
                if f.is_file() and f.suffix.lower() in [".pdf", ".txt", ".md", ".docx"]:
                    stats = f.stat()
                    try:
                        encoded_name = urllib.parse.quote(f.name, safe='')
                        rel_path = f"/pdf_docs/{d.name}/{encoded_name}"
                    except:
                        rel_path = f.as_posix()
                    inventory.append({
                        "name": f.name,
                        "path": rel_path,
                        "abs_path": f.resolve().as_posix(),
                        "size": f"{stats.st_size / 1024:.1f} KB",
                        "modified": datetime.datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        "type": f.suffix[1:].upper(),
                        "dir": d.name
                    })
        
        if not inventory:
            return "<div style='color: var(--text-secondary); padding: 40px; text-align: center; background: var(--bg-container); border-radius: var(--radius-lg); border: 1px dashed var(--bg-border);'>No files in repository. Upload some docs to start!</div>"
        
        html = """<div style="border: 1px solid var(--bg-border); border-radius: var(--radius-lg); overflow: hidden; background: var(--bg-container);">
<div style="padding: 12px 16px; border-bottom: 1px solid var(--bg-border); background: var(--bg-交互); display: flex; align-items: center; gap: 8px;">
<svg height="16" viewBox="0 0 16 16" width="16" style="fill: var(--primary-color);"><path d="M1.75 1A1.75 1.75 0 0 0 0 2.75v10.5C0 14.216.784 15 1.75 15h12.5A1.75 1.75 0 0 0 16 13.25v-8.5A1.75 1.75 0 0 0 14.25 3h-5.71l-.745-1.117A1.75 1.75 0 0 0 6.31 1H1.75Z"></path></svg>
<span style="font-weight: 600; font-size: 14px; color: var(--text-title);">Repository Inventory</span>
</div>
<table style="width: 100%; border-collapse: collapse; font-size: 13px; color: var(--text-body) !important;">
<thead>
<tr style="border-bottom: 1px solid var(--bg-border); text-align: left; background-color: var(--bg-交互) !important;">
<th style="padding: 12px 16px; font-weight: 600; color: var(--text-title) !important;">Name</th>
<th style="padding: 12px 16px; font-weight: 600; color: var(--text-title) !important;">Type</th>
<th style="padding: 12px 16px; font-weight: 600; color: var(--text-title) !important;">Size</th>
<th style="padding: 12px 16px; font-weight: 600; text-align: right; color: var(--text-title) !important;">Action</th>
</tr>
</thead>
<tbody>"""
        for item in inventory:
            html += f"""<tr class="table-row" style="border-bottom: 1px solid var(--bg-border); transition: all 0.2s; color: var(--text-body) !important;">
<td style="padding: 12px 16px;">
<div style="display: flex; align-items: center; gap: 8px;">
<svg height="16" viewBox="0 0 16 16" width="16" style="fill: var(--primary-color); flex-shrink: 0;"><path d="M2 1.75C2 .784 2.784 0 3.75 0h6.586c.464 0 .909.184 1.237.513l3.414 3.414c.329.328.513.773.513 1.237v9.586A1.75 1.75 0 0 1 13.75 16h-10A1.75 1.75 0 0 1 2 14.25Zm1.75-.25a.25.25 0 0 0-.25.25v12.5c0 .138.112.25.25.25h10a.25.25 0 0 0 .25-.25V4.664a.25.25 0 0 0-.073-.177l-3.414-3.414a.25.25 0 0 0-.177-.073ZM8.325 6.443a.75.75 0 0 1 1.05 1.05l-3.5 3.5a.75.75 0 0 1-1.05 0l-1.75-1.75a.75.75 0 0 1 1.05-1.05l1.225 1.225 2.975-2.975Z"></path></svg>
<span class="pdf-link" data-src="{item['path']}" data-page="1" style="color: var(--text-title) !important; cursor: pointer; font-weight: 500; text-decoration: none;">{item['name']}</span>
</div>
</td>
<td style="padding: 12px 16px;">
<span class="repo-badge" style="background-color: rgba(22, 93, 255, 0.1) !important; color: var(--primary-color) !important; border-color: rgba(22, 93, 255, 0.2) !important; font-size: 11px;">{item['type']}</span>
</td>
<td style="padding: 12px 16px; color: var(--text-secondary) !important;">{item['size']}</td>
<td style="padding: 12px 16px; text-align: right;">
<div style="display: flex; gap: 8px; justify-content: flex-end;">
<button onclick="navigator.clipboard.writeText('{item['abs_path']}');" title="Copy absolute path" style="background: none; border: none; cursor: pointer; color: var(--text-secondary); padding: 4px; transition: all 0.2s;">
<svg height="16" viewBox="0 0 16 16" width="16" style="fill: currentColor;"><path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Z"></path><path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z"></path></svg>
</button>
</div>
</td>
</tr>"""
        html += "</tbody></table></div>"
        return html

    def delete_file(self, file_path_str: str):
        """删除知识库中的文件"""
        try:
            p = Path(file_path_str)
            if p.exists() and p.is_file():
                p.unlink()
                return f"Successfully deleted {p.name}", self.get_file_inventory()
            return f"File not found: {file_path_str}", self.get_file_inventory()
        except Exception as e:
            return f"Error deleting file: {str(e)}", self.get_file_inventory()

    def load_kb(self, vector_dir: str):
        try:
            path = Path(vector_dir).expanduser().resolve()
            chunks, vectorizer, matrix, bm25 = load_vector_kb(path)
            set_kb_data(chunks, vectorizer, matrix, retrieve, bm25=bm25)
            global_state.chunks = chunks
            global_state.kb_chunks_len = len(chunks)
            
            # 兼容 Chroma 的元数据提取
            try:
                db_stats = f"Chroma DB loaded"
            except:
                db_stats = "N/A"
                
            return "已加载知识库 (ChromaDB Vector Store)", {"vector_dir": str(path), "chunks": len(chunks), "status": db_stats}
        except Exception as e:
            set_kb_data([], None, None, retrieve)
            global_state.chunks = []
            global_state.kb_chunks_len = 0
            return f"加载失败：{e}", {}

    def build_kb(self, files, chunk_size: int, chunk_overlap: int):
        # 0. 预清理：释放所有可能的文件句柄 (关键：防止 ChromaDB 锁死)
        clear_kb_data()
        global_state.chunks = []
        global_state.kb_chunks_len = 0
        
        file_list = []
        if files is None:
            file_list = []
        elif isinstance(files, list):
            file_list = files
        else:
            file_list = [files]
        if not file_list:
            return "未选择文件", {}

        UPLOAD_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        
        # 1. 识别并复制源文件到 UPLOAD_DOCS_DIR (如果还没在里面的话)
        temp_paths = []
        saved = 0
        for f in file_list:
            # 兼容 pathlib.Path 对象和 Gradio/Chainlit 文件对象
            if isinstance(f, Path):
                src_path = f
            else:
                # 优先尝试 path 属性 (Chainlit)，然后是 name 属性 (Gradio)
                # Chainlit 的 cl.File 对象中 .path 是完整路径，.name 只是文件名
                # Gradio 的文件对象中 .name 通常是完整路径
                src = getattr(f, "path", None) or getattr(f, "name", None)
                if not src: continue
                src_path = Path(src)
            
            if not src_path.exists():
                continue
            
            target_path = UPLOAD_DOCS_DIR / src_path.name
            # 如果源路径不在 UPLOAD_DOCS_DIR 内部，则复制过去
            if src_path.resolve().parent != UPLOAD_DOCS_DIR.resolve():
                shutil.copy2(src_path, target_path)
            
            temp_paths.append(target_path.resolve())
            saved += 1
            
        if saved == 0:
            return "未能读取上传文件路径", {}

        # 2. 清理 UPLOAD_DOCS_DIR 中不在新列表里的旧文件
        for old in UPLOAD_DOCS_DIR.iterdir():
            if old.is_file() and old.resolve() not in temp_paths:
                old.unlink()

        try:
            # 使用 temp_paths 而不是硬编码 UPLOAD_DOCS_DIR，以支持跨目录文件
            chunks, file_stats = collect_chunks(temp_paths, chunk_size=int(chunk_size), chunk_overlap=int(chunk_overlap))
            if not chunks:
                return "未生成任何 chunk", {"files": file_stats}
            
            # build_hybrid_indices 现在只是占位符，真正的向量构建在 save_outputs 中
            vectorizer, matrix, bm25 = build_hybrid_indices(chunks)
            artifacts = save_outputs(USER_VECTOR_DIR, chunks, vectorizer, matrix, bm25)
            
            # 重新加载最新的向量库
            kb_chunks, kb_vec, kb_matrix, kb_bm25 = load_vector_kb(USER_VECTOR_DIR)
            set_kb_data(kb_chunks, kb_vec, kb_matrix, retrieve, bm25=kb_bm25)
            
            global_state.chunks = kb_chunks
            global_state.kb_chunks_len = len(kb_chunks)
            
            # 重置图谱状态，提示用户重新构建
            graph_engine.nodes = {}
            graph_engine.edges = []
            graph_engine.processed_chunks = {} # 清空已处理分片记录，避免“增量构图必空图”
            if graph_engine.GRAPH_DATA_PATH.exists():
                graph_engine.GRAPH_DATA_PATH.unlink()
                
            return "已构建并加载 Chroma 向量库。检测到文档变更，请点击下方按钮重新构建知识图谱。", {
                "docs_dir": str(UPLOAD_DOCS_DIR),
                "vector_dir": str(USER_VECTOR_DIR),
                "files": file_stats,
                "chunks": len(chunks),
                "status": "Chroma DB generated and loaded",
                "artifacts": artifacts,
            }
        except Exception as e:
            return f"❌ 构建失败：{e} (原知识库保持不变)", {}

    def build_ui(self):
        with gr.Tab("📚 Knowledge Base", id="tab_kb"):
            self.delete_file_input = gr.Textbox(visible=False, elem_id="delete-file-input")
            self.delete_file_btn = gr.Button("Delete", visible=False, elem_id="delete-file-btn")
            
            with gr.Row():
                with gr.Column(scale=2):
                    with gr.Group(elem_classes="github-container"):
                        self.file_inventory_display = gr.HTML(value=self.get_file_inventory())
                        self.refresh_kb_btn = gr.Button("↻ Refresh Inventory", variant="secondary", size="sm", elem_classes="primary-btn")

                with gr.Column(scale=1):
                    with gr.Group(elem_classes="github-container"):
                        gr.HTML("<div class='github-header'>⚙️ Repository Settings</div>")
                        with gr.Row():
                            self.kb_dir = gr.Textbox(
                                value=str(DEFAULT_VECTOR_DIR), 
                                label="Local Vector Path", 
                                interactive=False, 
                                elem_classes="code-style-input",
                                scale=8
                            )
                            self.copy_btn = gr.Button("📋", scale=1, variant="secondary")
                        self.kb_load_btn = gr.Button("🔌 Mount Knowledge Base", variant="secondary")
                    
                    with gr.Group(elem_classes="github-container"):
                        gr.HTML("<div class='github-header'>📤 File Import</div>")
                        self.kb_upload = gr.File(
                            label="Commit New Documents",
                            file_count="multiple",
                            file_types=[".pdf", ".txt", ".md", ".docx"],
                            elem_classes="upload-container"
                        )
                        with gr.Row():
                            self.kb_chunk_size = gr.Slider(minimum=200, maximum=1500, step=50, value=500, label="Chunk Size")
                            self.kb_chunk_overlap = gr.Slider(minimum=0, maximum=400, step=10, value=50, label="Overlap")
                        self.kb_build_btn = gr.Button("🔨 Build & Re-index", variant="primary", elem_classes="primary-btn")
                        
                        gr.HTML("<div style='margin-top: 20px;' class='github-header'>🕸️ Real-Graph RAG (Advanced)</div>")
                        self.graph_build_btn = gr.Button("🔍 Build Knowledge Graph (AI-powered)", variant="secondary", elem_classes="primary-btn")
                        
                        self.kb_status = gr.Textbox(label="Operation Status", interactive=False)
                        self.kb_meta = gr.JSON(label="Metadata")

        # 绑定模块内部事件
        self.delete_file_btn.click(self.delete_file, inputs=[self.delete_file_input], outputs=[self.kb_status, self.file_inventory_display])
        self.refresh_kb_btn.click(self.get_file_inventory, outputs=[self.file_inventory_display])
        self.copy_btn.click(None, inputs=[self.kb_dir], js="(path) => { navigator.clipboard.writeText(path).then(() => { window.showToast('Path copied!', 'success'); }); }")
        self.kb_load_btn.click(self.load_kb, inputs=[self.kb_dir], outputs=[self.kb_status, self.kb_meta]).then(self.get_file_inventory, outputs=[self.file_inventory_display])
        self.kb_build_btn.click(self.build_kb, inputs=[self.kb_upload, self.kb_chunk_size, self.kb_chunk_overlap], outputs=[self.kb_status, self.kb_meta]).then(self.get_file_inventory, outputs=[self.file_inventory_display])
