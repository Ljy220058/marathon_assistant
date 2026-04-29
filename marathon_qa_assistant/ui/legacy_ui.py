from datetime import date
from pathlib import Path
from marathon_qa_assistant.core.app_state import BASE_DIR

GITHUB_STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap');

/* 核心设计系统 - 深色模式标准 */
:root {
    --primary-color: #165DFF;
    --primary-hover: #0E42D2;
    --primary-active: #0932B3;
    
    --bg-main: #121212;
    --bg-container: #1E1E1E;
    --bg-interactive: #2D2D2D;
    --bg-border: #3D3D3D;
    
    --text-title: #FFFFFF;
    --text-body: #CCCCCC;
    --text-secondary: #888888;
    
    --success: #00B42A;
    --warning: #FF7D00;
    --error: #F53F3F;
    --info: #86909C;
    
    --radius-sm: 8px;
    --radius-lg: 12px;
    --radius-full: 24px;
}

/* 核心布局扩展 */
.side-panel-container { gap: 20px; }
.github-container {
    background: var(--bg-container);
    border: 1px solid var(--bg-border);
    border-radius: var(--radius-sm);
    padding: 12px;
    margin-bottom: 16px;
}
.github-header {
    font-size: 12px;
    font-weight: 600;
    color: var(--primary-color);
    text-transform: uppercase;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.github-header::before {
    content: "●";
    font-size: 8px;
}

/* 聊天容器样式 */
.chatbot-container {
    background: var(--bg-container) !important;
    border: 1px solid var(--bg-border) !important;
    border-radius: var(--radius-lg) !important;
}

/* 推理终端样式 */
.reasoning-terminal {
    background: #0d1117;
    color: #e6edf3;
    font-family: 'Fira Code', 'Cascadia Code', monospace;
    font-size: 12px;
    padding: 12px;
    border-radius: 6px;
    border: 1px solid #30363d;
    max-height: 300px;
    overflow-y: auto;
    line-height: 1.5;
}

/* 错误与警告 */
.github-flash-error {
    color: #f85149;
    background: rgba(248, 81, 73, 0.1);
    padding: 8px 12px;
    border-radius: 6px;
    border: 1px solid rgba(248, 81, 73, 0.4);
    font-size: 13px;
    margin: 8px 0;
}
"""

# Gradio JS 锁屏逻辑已移除，项目已全面迁移至 Chainlit

GITHUB_STYLE += """
/* PDF.js Viewer 样式扩展 */
.pdf-viewer-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: #525659;
}

.pdf-toolbar {
    background: #323639;
    padding: 8px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    color: white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    z-index: 10;
}

.pdf-toolbar button {
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.2);
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 4px;
}

.pdf-toolbar button:hover {
    background: rgba(255,255,255,0.2);
}

.pdf-toolbar .page-info {
    font-size: 13px;
    font-family: monospace;
}

.pdf-canvas-wrapper {
    flex-grow: 1;
    overflow: auto;
    padding: 20px;
    display: flex;
    justify-content: center;
    background: #525659;
}

#pdf-render-canvas {
    box-shadow: 0 0 20px rgba(0,0,0,0.5);
    background: white;
    max-width: 100%;
}

.pdf-loading-overlay {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 20;
}

.pdf-loading-overlay.active {
    display: flex;
}

/* 实验室报告风格 (Structured Report v2.0) */
.lab-report {
    background-color: var(--bg-container);
    border: 1px solid var(--bg-border);
    border-radius: var(--radius-lg);
    padding: 24px;
    margin: 16px 0;
    color: var(--text-body);
    font-size: 14px;
    line-height: 1.6;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}

.report-header {
    border-bottom: 2px solid var(--primary-color);
    padding-bottom: 16px;
    margin-bottom: 20px;
}

.report-title {
    font-size: 22px;
    font-weight: 700;
    color: var(--text-title);
    margin-bottom: 8px;
    letter-spacing: -0.02em;
}

.report-meta {
    font-size: 12px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.report-section {
    margin-bottom: 24px;
}

.section-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--primary-color);
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.section-title::before {
    content: "";
    width: 4px;
    height: 16px;
    background: var(--primary-color);
    border-radius: 2px;
}

.findings-table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    border: 1px solid var(--bg-border);
    border-radius: var(--radius-sm);
    overflow: hidden;
}

.findings-table th {
    background: var(--bg-interactive);
    color: var(--text-title);
    text-align: left;
    padding: 10px 14px;
    font-weight: 600;
    border-bottom: 1px solid var(--bg-border);
}

.findings-table td {
    padding: 10px 14px;
    border-bottom: 1px solid var(--bg-border);
    color: var(--text-body);
}

.findings-table tr:last-child td {
    border-bottom: none;
}

.audit-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 16px;
    margin-top: 12px;
}

.audit-item {
    background: var(--bg-interactive);
    padding: 12px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--bg-border);
}

.audit-label {
    font-size: 11px;
    color: var(--text-secondary);
    margin-bottom: 4px;
}

.audit-value {
    font-size: 18px;
    font-weight: 700;
    color: var(--primary-color);
}
"""

import markdown


def _extract_citation_ids(text: str):
    import re

    seen = set()
    ordered_ids = []
    # 匹配 [1] 或 [1, 2] 这种形式
    for match in re.findall(r"\[(\d+(?:\s*,\s*\d+)*)\]", text or ""):
        # 拆分逗号分隔的 ID
        ids = [s.strip() for s in match.split(',')]
        for i_str in ids:
            if i_str.isdigit():
                idx = int(i_str)
                if idx not in seen:
                    seen.add(idx)
                    ordered_ids.append(idx)
    return ordered_ids


def _get_citation_link(idx, item):
    """生成报告内展示用的引用标记。"""
    return f"[{idx}]"


def _get_evidence_item_details(item, fallback_id=None):
    evidence_id = item.get("id", fallback_id)
    source = item.get("source") or item.get("document") or item.get("source_file") or "unknown"
    path = item.get("path", "") or item.get("source_path", "")
    pages = item.get("pages") or []
    page = pages[0] if pages else (item.get("page") or 1)
    text = str(item.get("text", "") or "").strip()
    return {
        "id": evidence_id,
        "source": source,
        "path": path,
        "page": page,
        "text": text,
    }


def _resolve_cited_evidence_items(evidence_base, cited_ids):
    if not evidence_base:
        return []

    evidence_map = {
        int(item.get("id", 0)): item
        for item in evidence_base
        if isinstance(item, dict) and item.get("id")
    }
    valid_ids = [idx for idx in cited_ids if idx in evidence_map]
    items = [_get_evidence_item_details(evidence_map[idx], fallback_id=idx) for idx in valid_ids]

    if items:
        return items

    # 当正文没有稳定引用时，退回到证据基底中的前几条，保证 Chainlit 仍可预览。
    fallback_items = []
    for idx, item in enumerate(evidence_base, start=1):
        if not isinstance(item, dict):
            continue
        details = _get_evidence_item_details(item, fallback_id=idx)
        if details["path"]:
            fallback_items.append(details)
    return fallback_items


def _render_evidence_base_md(evidence_base, cited_ids):
    evidence_items = _resolve_cited_evidence_items(evidence_base, cited_ids)
    if not evidence_items:
        return ""

    lines = ["#### 参考来源", "", "> 请点击消息下方同编号的预览按钮在当前界面打开原文。", ""]
    for item in evidence_items:
        idx = item["id"]
        source = item["source"]
        path = item["path"]
        page = item["page"]
        page_suffix = f" P.{page}"
        text = item["text"]
        
        # 统一使用跳转预览链接
        view_link = _get_citation_link(idx, item)
        
        lines.append(f"{view_link} {source}{page_suffix}")
        if text:
            # 清理文本中的多余换行，避免破坏 Markdown 列表结构
            clean_text = " ".join(text.split())
            if len(clean_text) > 300:
                clean_text = clean_text[:300] + "..."
            lines.append(f"> {clean_text}")
        lines.append("")

    return "\n" + "\n".join(lines).strip() + "\n"


def _render_audit_sources_md(audit_block, evidence_base):
    if not isinstance(audit_block, dict):
        return ""
    
    import re as _re

    score_sources = audit_block.get("score_sources", {}) or {}
    if not score_sources:
        return ""

    label_map = {
        "consistency": "一致性",
        "safety": "安全性",
        "roi": "知识回报率 (ROI)",
    }
    lines = ["", "#### 评分依据", "", "| 指标 | 判定依据 |", "| :--- | :--- |"]
    for key in ("consistency", "safety", "roi"):
        # 确保每个 entry 内部没有换行符，或者将其替换为 <br>，且转义表格分界符 |
        entries = [str(item).strip().replace('\n', '<br>').replace('|', '&#124;') for item in score_sources.get(key, []) if str(item).strip()]
        if entries:
            # 使用标准 <br> 标签，并确保表格行内没有未处理的换行
            lines.append(f"| **{label_map[key]}** | {'<br>'.join(entries)} |")

    evidence_labels = [str(label).strip() for label in score_sources.get("evidence_labels", []) if str(label).strip()]
    if evidence_labels and evidence_base:
        evidence_map = {}
        for item in evidence_base:
            citation = str(item.get("citation", "") or "").strip()
            if citation:
                evidence_map[citation] = item

        lines.extend(["", "**关联证据**", ""])
        for label in evidence_labels[:3]:
            item = evidence_map.get(label)
            if not item:
                # 尝试通过提取数字 ID 来匹配
                match = _re.search(r"(\d+)", label)
                if match:
                    numeric_id = int(match.group(1))
                    for ev_item in evidence_base:
                        if int(ev_item.get("id", 0)) == numeric_id:
                            item = ev_item
                            break

            if not item:
                continue

            source = item.get("source") or item.get("document") or item.get("source_file") or "unknown"
            path = item.get("path", "") or item.get("source_path", "")
            pages = item.get("pages") or []
            page = pages[0] if pages else (item.get("page") or 1)
            page_suffix = f" P.{page}"
            
            # 使用统一的跳转链接生成器
            label_id_match = _re.search(r"(\d+)", label)
            label_idx = int(label_id_match.group(1)) if label_id_match else item.get("id", 0)
            view_link = _get_citation_link(label_idx, item)
            
            text = str(item.get("text", "") or "").strip()
            clean_text = " ".join(text.split())
            if len(clean_text) > 90:
                clean_text = clean_text[:90].rstrip() + "..."
            lines.append(f"- {view_link} {source}{page_suffix}: {clean_text or '无片段摘要'}")

    return "\n".join(lines).strip()


class UIHelper:
    @staticmethod
    def render_structured_report(structured_data, raw_report, include_sources: bool = False):
        import re
        
        if not structured_data:
            raw = (raw_report or "当前没有可显示的报告内容。").strip()
            raw = re.sub(r'^```[a-zA-Z]*\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            return raw

        evidence_base = structured_data.get("evidence_base", [])

        summary = structured_data.get('summary', '')
        if not summary or summary.startswith("（本轮未产生"):
            summary = (raw_report or structured_data.get('summary', '无摘要'))

        summary = re.sub(r'^```[a-zA-Z]*\s*', '', summary.strip())
        summary = re.sub(r'\s*```$', '', summary)
        
        # 引用 [n] 保持纯文本，点击预览由 Chainlit 显式 Action 按钮提供

        md = f"### 🏃‍♂️ {structured_data.get('title', '马拉松专业分析报告')}\n\n"
        md += f"**Generated on**: {date.today().isoformat()} | Marathon QA Assistant\n\n"
        
        # 增加审计评分面板 (美化展示)
        audit_scores = structured_data.get("audit_block", {}).get("scores", {})
        if audit_scores:
            md += "#### 🛡️ 质量与安全审计\n\n"
            md += "| 一致性评分 | 安全性评分 | 知识回报率 (ROI) |\n"
            md += "| :---: | :---: | :---: |\n"
            
            c_score = audit_scores.get("consistency", 0)
            s_score = audit_scores.get("safety", 0)
            r_score = audit_scores.get("roi", 0)
            
            # 根据分数添加颜色指示 (Markdown 模拟)
            def _get_status_emoji(score):
                if score >= 85: return "🟢"
                if score >= 60: return "🟡"
                return "🔴"
            
            md += f"| {_get_status_emoji(c_score)} **{c_score}** | {_get_status_emoji(s_score)} **{s_score}** | {_get_status_emoji(r_score)} **{r_score}%** |\n\n"
            
            # 增加空行确保后续内容不被视为表格的一部分
            md += "\n\n"
            
            audit_sources_md = _render_audit_sources_md(
                structured_data.get("audit_block", {}),
                evidence_base,
            )
            if audit_sources_md:
                md += "\n" + audit_sources_md + "\n\n"
        
        md += "\n\n---\n\n"
        
        md += "#### 🎯 核心摘要\n\n"
        md += f"{summary}\n\n"

        # 收集所有正文中出现的引用 ID
        all_cited_text = summary
        
        if structured_data.get('findings'):
            md += "\n#### 📊 详细分析\n\n"
            md += "| 维度 | 内容 |\n"
            md += "| :--- | :--- |\n"
            for finding in structured_data['findings']:
                key = str(finding.get('key', '')).replace('\n', ' ').replace('|', '&#124;')
                val = str(finding.get('value', '')).replace('\n', '<br>').replace('|', '&#124;')
                all_cited_text += " " + val
                md += f"| **{key}** | {val} |\n"
            md += "\n"

        if structured_data.get('recommendations'):
            md += "\n#### 💡 行动建议\n\n"
            for rec in structured_data['recommendations']:
                if rec and rec.strip():
                    processed_rec = rec.strip()
                    all_cited_text += " " + processed_rec
                    md += f"- {processed_rec}\n"
            md += "\n"

        if include_sources:
            # 从汇总的文本中提取所有引用的 ID
            cited_ids = _extract_citation_ids(all_cited_text)
            sources_md = _render_evidence_base_md(evidence_base, cited_ids)
            if sources_md:
                md += "\n" + sources_md + "\n"

        return md

    @staticmethod
    def build_evidence_preview_bundle(structured_data, raw_report, max_items: int = 5):
        import re

        if not structured_data:
            return {"panel_md": "", "actions": []}

        evidence_base = structured_data.get("evidence_base", [])
        if not evidence_base:
            return {"panel_md": "", "actions": []}

        summary = structured_data.get("summary", "")
        if not summary or summary.startswith("（本轮未产生"):
            summary = raw_report or structured_data.get("summary", "")

        summary = re.sub(r'^```[a-zA-Z]*\s*', '', str(summary).strip())
        summary = re.sub(r'\s*```$', '', summary)
        all_cited_text = summary

        for finding in structured_data.get("findings", []):
            all_cited_text += " " + str(finding.get("value", ""))
        for rec in structured_data.get("recommendations", []):
            all_cited_text += " " + str(rec or "")

        cited_ids = _extract_citation_ids(all_cited_text)
        # 获取所有引用过的证据项，不设数量限制以确保正文所有 [n] 都能跳转
        all_evidence_items = _resolve_cited_evidence_items(evidence_base, cited_ids)
        all_evidence_items = [item for item in all_evidence_items if item.get("path")]
        
        if not all_evidence_items:
            return {"panel_md": "", "actions": []}

        lines = [
            "<details>",
            "<summary>查看证据</summary>",
            "",
            "点击下方按钮可直接预览对应原文：",
            "",
        ]
        
        actions = []
        for i, item in enumerate(all_evidence_items):
            idx = item["id"]
            source = item["source"]
            path = item["path"]
            page = item["page"]
            
            # 统一使用正斜杠路径
            safe_path = path.replace("\\", "/")
            
            # 清理片段中的换行符
            snippet = " ".join(str(item.get("text", "") or "").split())
            if len(snippet) > 120:
                snippet = snippet[:120].rstrip() + "..."
            
            # 只在面板中展示前 max_items 条摘要，防止 UI 过长
            if i < max_items:
                lines.append(f"- [{idx}] {source} P.{page}")
                if snippet:
                    lines.append(f"> {snippet}")
                lines.append("")
            
            short_source = source if len(source) <= 20 else source[:17] + "..."
            
            # PDF 预览只通过显式 Action 按钮触发，避免正文链接被前端渲染成新标签页跳转。
            payload_dict = {"path": safe_path, "name": source, "page": page, "snippet": snippet}
            
            actions.append(
                {
                    "id": f"view_pdf_{idx}",
                    "name": "view_pdf",
                    "payload": payload_dict,
                    "label": f"[{idx}] {short_source} P.{page}",
                }
            )
            
        if len(all_evidence_items) > max_items:
            lines.append(f"*(仅展示前 {max_items} 条证据，点击正文引用可查看全部)*")
            
        lines.append("</details>")

        return {
            "panel_md": "\n".join(lines).strip(),
            "actions": actions,
        }

    @staticmethod
    def render_reasoning_flow_md(entities, graph_ctx):
        md = "### 🧠 推理路径分析\n\n"
        if entities:
            md += "**识别到的核心实体**:\n"
            md += " → ".join([f"`{e}`" for e in entities]) + "\n\n"
        
        if graph_ctx:
            md += "**知识图谱关联分析**:\n"
            md += f"> {graph_ctx}\n\n"
        return md

    @staticmethod
    def generate_token_md(usage_dict, roi_score=0):
        total = usage_dict.get("Total", 0)
        md = f"📊 **运行统计** | Total Tokens: `{total}`"
        if roi_score > 0:
            md += f" | 知识回报率 (ROI): `{roi_score:.1f}`"
        return md

    @staticmethod
    def render_build_summary_md(meta):
        md = f"### ✅ 索引构建完成\n\n"
        md += f"- **总文件数**: `{meta.get('file_count', 0)}`\n"
        md += f"- **总切片数 (Chunks)**: `{meta.get('chunk_count', 0)}`\n"
        md += f"- **构建耗时**: `{meta.get('duration', 0):.2f}s`\n"
        md += f"- **存储路径**: `{meta.get('index_path', 'unknown')}`\n"
        return md

    @staticmethod
    def render_guided_questions(questions):
        if not questions:
            return ""
        md = "#### 💡 你可以接着问：\n\n"
        for q in questions:
            md += f"- {q}\n"
        return md
