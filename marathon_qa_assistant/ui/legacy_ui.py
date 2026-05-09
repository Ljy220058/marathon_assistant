from datetime import date
from pathlib import Path
from marathon_qa_assistant.core.app_state import BASE_DIR
from marathon_qa_assistant.core.zone_constants import sanitize_all_pace as _strip_pace
import re

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


def _normalize_source_filename(raw: str) -> str:
    import urllib.parse

    decoded = urllib.parse.unquote(raw or "")
    normalized = decoded.replace("+", " ").replace("_", " ")
    normalized = " ".join(normalized.split())
    return normalized.strip().lower()


def _match_source_to_evidence_ids(text: str, evidence_base: list) -> list:
    import re

    if not evidence_base:
        return []

    source_patterns = re.findall(r"\[来源:\s*([^\]]+)\]", text or "")
    if not source_patterns:
        return []

    seen_ids = set()
    matched_ids = []
    for source_text in source_patterns:
        normalized_query = _normalize_source_filename(source_text)
        if not normalized_query:
            continue
        for item in evidence_base:
            if not isinstance(item, dict):
                continue
            normalized_source = _normalize_source_filename(str(item.get("source", "") or ""))
            if not normalized_source:
                continue
            if normalized_query in normalized_source or normalized_source in normalized_query:
                ev_id = int(item.get("id") or 0)
                if ev_id > 0 and ev_id not in seen_ids:
                    seen_ids.add(ev_id)
                    matched_ids.append(ev_id)
                break

    return matched_ids


def _get_citation_link(idx, item):
    """生成报告内展示用的引用标记。"""
    return f"[{idx}]"


def _format_evidence_badges(evidence_ids):
    normalized_ids = [int(ev_id) for ev_id in (evidence_ids or []) if str(ev_id).isdigit()]
    return " ".join(f"`[{ev_id}]`" for ev_id in normalized_ids)


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


def _safe_md_text(value, fallback="—"):
    text = str(value or "").strip()
    return text if text else fallback


def _normalize_week_sections_from_plan(structured_plan):
    if not isinstance(structured_plan, dict):
        return []

    normalized = []
    for fallback_index, week in enumerate(structured_plan.get("week_plans", []) or [], start=1):
        if not isinstance(week, dict):
            continue

        days = []
        for day in week.get("days", []) or []:
            if not isinstance(day, dict):
                continue
            days.append(
                {
                    "day": _safe_md_text(day.get("day")),
                    "training_type": _safe_md_text(day.get("training_type")),
                    "warmup": _safe_md_text(day.get("warmup")),
                    "main_set": _safe_md_text(day.get("main_set")),
                    "cooldown": _safe_md_text(day.get("cooldown")),
                    "venue": _safe_md_text(day.get("venue")),
                    "notes": _safe_md_text(day.get("notes"), fallback=""),
                }
            )

        repeat_guard = week.get("repeat_guard_signature", {}) or {}
        normalized.append(
            {
                "week_index": int(week.get("week_index") or fallback_index),
                "phase": _safe_md_text(week.get("phase")),
                "week_goal": _safe_md_text(week.get("week_goal")),
                "load_level": _safe_md_text(week.get("load_level")),
                "load_progression_note": _safe_md_text(week.get("load_progression_note")),
                "execution_reminder": _safe_md_text(week.get("execution_reminder")),
                "key_workouts": [
                    _strip_pace(_safe_md_text(item)) for item in (week.get("key_workouts") or []) if str(item or "").strip()
                ],
                "action_suggestions": [
                    _strip_pace(_safe_md_text(item)) for item in (week.get("action_suggestions") or []) if str(item or "").strip()
                ],
                "days": days,
                "training_day_count": sum(1 for day in days if day["training_type"] != "休息"),
                "repeat_guard": {
                    "quality_session_count": int(repeat_guard.get("quality_session_count") or 0),
                    "hard_day_count": int(repeat_guard.get("hard_day_count") or 0),
                    "rest_day_count": int(repeat_guard.get("rest_day_count") or 0),
                    "long_run_minutes": int(repeat_guard.get("long_run_minutes") or 0),
                    "long_run_distance_km": repeat_guard.get("long_run_distance_km"),
                    "weekly_volume_km": repeat_guard.get("weekly_volume_km"),
                },
            }
        )
    return normalized


def _render_adaptive_adjustment_md(structured_data):
    if not isinstance(structured_data, dict):
        return ""

    adaptive_adjustment = structured_data.get("adaptive_adjustment") or {}
    if not isinstance(adaptive_adjustment, dict) or not adaptive_adjustment:
        return ""

    reason_labels = []
    for reason in adaptive_adjustment.get("reasons", []) or []:
        if not isinstance(reason, dict):
            continue
        label = str(reason.get("label") or "").strip()
        if label and label not in reason_labels:
            reason_labels.append(label)
    if not reason_labels:
        for code in adaptive_adjustment.get("reason_codes", []) or []:
            normalized = str(code or "").strip()
            if normalized and normalized not in reason_labels:
                reason_labels.append(normalized)

    adjustment_required = bool(adaptive_adjustment.get("adjustment_required"))
    trigger_text = "已触发" if adjustment_required else "无需调整"
    reasons_text = "、".join(reason_labels) if reason_labels else "未触发"
    next_day_adjustment = _safe_md_text(adaptive_adjustment.get("next_day_adjustment"))
    weekly_adjustment = _safe_md_text(adaptive_adjustment.get("weekly_adjustment"))
    alternative_workout = _safe_md_text(adaptive_adjustment.get("alternative_workout"))
    rationale = _safe_md_text(adaptive_adjustment.get("rationale"))
    risk_alert = str(adaptive_adjustment.get("risk_alert") or "").strip()

    lines = [
        "#### 🔁 自适应调整卡",
        "",
        f"- 状态：{trigger_text}",
        f"- 触发原因：{reasons_text}",
        "",
        "**明日调整**",
        f"- {next_day_adjustment}",
        "",
        "**本周微调**",
        f"- {weekly_adjustment}",
        "",
        "**替代训练**",
        f"- {alternative_workout}",
    ]

    if risk_alert:
        lines.extend(["", "**风险提示**", f"- {_safe_md_text(risk_alert)}"])

    lines.extend(["", "**为什么这么调**", f"- {rationale}", ""])
    return "\n".join(lines).strip()


def _render_half_marathon_protocol_panel_md(structured_data):
    if not isinstance(structured_data, dict):
        return ""

    panel = structured_data.get("half_marathon_protocol_panel") or {}
    if not isinstance(panel, dict) or not panel.get("active"):
        return ""

    selected = panel.get("selected_archetype") or {}
    validation = panel.get("validation_summary") or {}
    status_label = {
        "passed": "通过",
        "warning": "有提醒",
        "error": "有错误",
    }.get(str(panel.get("status") or ""), _safe_md_text(panel.get("status"), "未知"))

    lines = [
        "#### 🧬 半马 HMP 协议面板",
        "",
        f"- 协议状态：{status_label}",
        f"- 选中画像：{_safe_md_text(selected.get('label'))}（`{_safe_md_text(selected.get('archetype_id'), 'unknown')}`，评分 {int(selected.get('score') or 0)}）",
        f"- 画像依据：{'；'.join(str(item) for item in (selected.get('reasons') or []) if str(item).strip()) or '未记录'}",
        f"- 输入周跑量：{_safe_md_text(panel.get('input_weekly_mileage_km'), '未提供')} km",
        f"- 近期全马：{'是' if panel.get('recent_marathon') else '否'}",
        f"- 验证摘要：错误 {int(validation.get('error_count') or 0)} 条 / 提醒 {int(validation.get('warning_count') or 0)} 条 / 已检查 {len(validation.get('checked_constraints') or [])} 条约束",
        "",
    ]

    pace_calibration = panel.get("pace_calibration") or {}
    if isinstance(pace_calibration, dict) and pace_calibration:
        lines.extend(
            [
                "**HMP 配速校准**",
                "",
                f"- 校准状态：{_safe_md_text(pace_calibration.get('status'))}",
                f"- 目标 HMP：{_safe_md_text(pace_calibration.get('target_hmp_pace'), '未估算')}",
                f"- 当前能力 HMP：{_safe_md_text(pace_calibration.get('current_hmp_pace'), '未估算')}",
                f"- 差值：{_safe_md_text(pace_calibration.get('gap_seconds_per_km'), '未知')} 秒/公里",
                f"- 速度课校准：{'可用' if pace_calibration.get('speed_calibration_available') else '缺少当前5K/10K，按保守策略'}",
                "",
            ]
        )
        zone_rows = [item for item in (pace_calibration.get("current_zone_table") or pace_calibration.get("target_zone_table") or []) if isinstance(item, dict)]
        if zone_rows:
            lines.extend(["| HMP区间 | 百分比 | 配速 | 用途 |", "| :--- | :---: | :--- | :--- |"])
            for item in zone_rows:
                if item.get("zone_id") not in {"support_endurance_90", "specific_endurance_95", "race_specific_100", "specific_speed_105", "support_speed_107_110"}:
                    continue
                lines.append(
                    "| "
                    f"{_safe_md_text(item.get('label')).replace('|', '&#124;')} | "
                    f"{_safe_md_text(item.get('percent')).replace('|', '&#124;')} | "
                    f"{_safe_md_text(item.get('pace')).replace('|', '&#124;')} | "
                    f"{_safe_md_text(item.get('purpose')).replace('|', '&#124;')} |"
                )
            lines.append("")
        notes = [str(item or "").strip() for item in (pace_calibration.get("notes") or []) if str(item or "").strip()]
        if notes:
            lines.extend(["**校准提示**", ""])
            for item in notes[:4]:
                lines.append(f"- {item}")
            lines.append("")

    capacity_budget = panel.get("capacity_budget") or {}
    if isinstance(capacity_budget, dict) and capacity_budget:
        lines.extend(
            [
                "**HMP 容量预算**",
                "",
                f"- 质量课上限：{_safe_md_text(capacity_budget.get('quality_sessions_max'), '未知')} 堂/周",
                f"- 95% HMP 上限：{_safe_md_text(capacity_budget.get('hmp_95_max_km'), '未知')} km",
                f"- 100% HMP 上限：{_safe_md_text(capacity_budget.get('hmp_100_total_max_km'), '未知')} km",
                f"- 105% HMP 上限：{_safe_md_text(capacity_budget.get('hmp_105_total_max_km'), '未知')} km",
                f"- 110% HMP 上限：{_safe_md_text(capacity_budget.get('hmp_110_total_max_km'), '未知')} km",
                "",
            ]
        )
        notes = [str(item or "").strip() for item in (capacity_budget.get("notes") or []) if str(item or "").strip()]
        if notes:
            for item in notes[:4]:
                lines.append(f"- {item}")
            lines.append("")

    profile_gaps = [item for item in (panel.get("profile_gaps") or []) if isinstance(item, dict)]
    if profile_gaps:
        lines.extend(["**画像缺口**", ""])
        for item in profile_gaps[:8]:
            lines.append(
                f"- {_safe_md_text(item.get('label') or item.get('field'))}：{_safe_md_text(item.get('reason'))}"
            )
        lines.append("")

    phases = [item for item in (panel.get("phase_sequence") or []) if isinstance(item, dict)]
    if phases:
        lines.extend(["**阶段目标**", ""])
        for item in phases:
            lines.append(
                f"- `{_safe_md_text(item.get('id'), '')}`：{_safe_md_text(item.get('label'))}；{_safe_md_text(item.get('objective'), '')}"
            )
        lines.append("")

    workouts = [item for item in (panel.get("preferred_workouts") or []) if isinstance(item, dict)]
    if workouts:
        lines.extend(["**关键课表候选**", "", "| 课表 | 区间 | 目标 | 风险提示 |", "| :--- | :--- | :--- | :--- |"])
        for item in workouts:
            label = _safe_md_text(item.get("label") or item.get("id")).replace("|", "&#124;")
            zone = _safe_md_text(item.get("primary_zone"), "").replace("|", "&#124;")
            objective = _safe_md_text(item.get("objective"), "").replace("|", "&#124;")
            caution = _safe_md_text(item.get("caution"), "").replace("|", "&#124;")
            lines.append(f"| {label} | `{zone}` | {objective} | {caution} |")
        lines.append("")

    glossary_terms = [item for item in (panel.get("glossary_terms") or []) if isinstance(item, dict)]
    if glossary_terms:
        lines.extend(["**HMP 术语解释**", ""])
        for item in glossary_terms[:8]:
            label = _safe_md_text(item.get("label") or item.get("id"))
            definition = _safe_md_text(item.get("definition"), "")
            implication = _safe_md_text(item.get("training_implication"), "")
            text = f"- {label}：{definition}"
            if implication:
                text += f" 执行含义：{implication}"
            lines.append(text)
        lines.append("")

    issues = [item for item in (panel.get("issues") or []) if isinstance(item, dict)]
    if issues:
        lines.extend(["**验证问题与建议**", ""])
        for item in issues[:8]:
            location = ""
            if item.get("week_index"):
                location = f"第 {item.get('week_index')} 周"
                if str(item.get("day") or "").strip():
                    location += f" {item.get('day')}"
            prefix = f"[{_safe_md_text(item.get('severity'), 'warning')}] {_safe_md_text(item.get('label') or item.get('constraint_id'))}"
            lines.append(f"- {prefix}：{_safe_md_text(location, '').strip()} {_safe_md_text(item.get('message'))}".strip())
            recommendation = _safe_md_text(item.get("recommendation"), "")
            if recommendation:
                lines.append(f"  建议：{recommendation}")
            evidence_basis = item.get("evidence_basis") if isinstance(item.get("evidence_basis"), dict) else {}
            evidence_summary = _safe_md_text(evidence_basis.get("summary"), "")
            if evidence_summary:
                lines.append(f"  依据：{evidence_summary}")
        lines.append("")
    else:
        lines.extend(["**验证问题与建议**", "", "- 当前 HMP 专项验证未发现错误或提醒。", ""])

    repair_log = [item for item in (panel.get("repair_log") or []) if isinstance(item, dict)]
    repair_suggestions = [item for item in (panel.get("repair_suggestions") or []) if isinstance(item, dict)]
    if repair_log:
        lines.extend(["**自动修复记录**", ""])
        for item in repair_log[:8]:
            location = ""
            if item.get("week_index"):
                location = f"第 {item.get('week_index')} 周"
                if str(item.get("day") or "").strip():
                    location += f" {item.get('day')}"
            lines.append(
                f"- {_safe_md_text(item.get('constraint_id'))}：{_safe_md_text(location, '').strip()} "
                f"{_safe_md_text(item.get('action'))}".strip()
            )
        lines.append("")
    elif repair_suggestions:
        lines.extend(["**修复建议**", ""])
        for item in repair_suggestions[:8]:
            lines.append(f"- {_safe_md_text(item.get('constraint_id'))}：{_safe_md_text(item.get('action'))}")
        lines.append("")

    source_docs = [str(item or "").strip() for item in (panel.get("source_docs") or []) if str(item or "").strip()]
    if source_docs:
        lines.extend(["**基石资料**", ""])
        for item in source_docs:
            lines.append(f"- `{item}`")
        lines.append("")

    return "\n".join(lines).strip()


def _render_training_explanation_panel_md(structured_data):
    if not isinstance(structured_data, dict):
        return ""

    panel = structured_data.get("training_explanation_panel") or {}
    if not isinstance(panel, dict):
        return ""

    lines = [
        "#### 🔍 关键训练解释面板",
        "",
        f"- 解释覆盖率：{int(float(panel.get('coverage_ratio', 0)) * 100)}%",
        f"- 覆盖数量：{int(panel.get('explained_key_workouts', 0) or 0)} / {int(panel.get('total_key_workouts', 0) or 0)}",
        f"- 审计摘要：{_safe_md_text(panel.get('audit_summary'))}",
        "",
    ]

    summary = _safe_md_text(panel.get("summary"), "")
    if summary:
        lines.extend([summary, ""])

    weeks = [item for item in (panel.get("weeks") or []) if isinstance(item, dict)]
    if not weeks:
        lines.append("> 当前暂无可展示的关键训练解释。")
        return "\n".join(lines).strip()

    for week in weeks:
        week_index = int(week.get("week_index") or 0)
        lines.append(
            f"##### 第{week_index}周 · {_safe_md_text(week.get('phase'))} · {_safe_md_text(week.get('load_level'))}"
        )
        lines.append("")
        week_items = [item for item in (week.get("items") or []) if isinstance(item, dict)]
        if not week_items:
            lines.extend(
                [
                    "> 本周暂无关键训练解释项。",
                    "> 如为多周计划，其他周解释请继续向下查看。",
                    "",
                ]
            )
            continue
        for item in week_items:
            lines.append(f"**{_strip_pace(_safe_md_text(item.get('title')))}**")
            lines.append(f"- 为什么安排：{_safe_md_text(item.get('why_scheduled'))}")
            lines.append(f"- 主要训练目标：{_safe_md_text(item.get('primary_target'))}")
            lines.append(f"- 风险提醒：{_safe_md_text(item.get('risk_alert'))}")
            lines.append(f"- 状态不佳时替代：{_safe_md_text(item.get('alternative_workout'))}")
            lines.append(f"- 决策摘要：{_safe_md_text(item.get('decision_summary'))}")
            template_id = _safe_md_text(item.get("template_id"), "")
            detail_lines = []
            target_labels = [str(label or "").strip() for label in (item.get("target_labels") or []) if str(label or "").strip()]
            warnings = [str(warning or "").strip() for warning in (item.get("warnings") or []) if str(warning or "").strip()]
            adjustments = [str(adjustment or "").strip() for adjustment in (item.get("adjustments") or []) if str(adjustment or "").strip()]
            constraints = [constraint for constraint in (item.get("constraints") or []) if isinstance(constraint, dict)]
            decision_trace = [trace for trace in (item.get("decision_trace") or []) if isinstance(trace, dict)]
            explanation_source = _safe_md_text(item.get("explanation_source"), "")
            status = _safe_md_text(item.get("status"), "")
            if target_labels:
                detail_lines.append(f"- 目标标签：{'、'.join(target_labels[:5])}")
            if explanation_source:
                detail_lines.append(f"- 解释来源：{explanation_source}")
            if status:
                detail_lines.append(f"- 决策状态：{status}")
            if warnings:
                detail_lines.extend(["- 约束告警：", *[f"  - {_safe_md_text(warning)}" for warning in warnings[:3]]])
            if adjustments:
                detail_lines.extend(["- 自动调整：", *[f"  - {_safe_md_text(adjustment)}" for adjustment in adjustments[:3]]])
            if constraints:
                detail_lines.append("- 约束检查：")
                for constraint in constraints[:3]:
                    rule = _safe_md_text(constraint.get("rule"), "")
                    constraint_status = _safe_md_text(constraint.get("status"), "")
                    message = _safe_md_text(constraint.get("message"), "")
                    detail_lines.append(f"  - {' / '.join(part for part in [rule, constraint_status, message] if part)}")
            if decision_trace:
                detail_lines.append("- 决策轨迹：")
                for trace in decision_trace[:4]:
                    requested = _safe_md_text(trace.get("requested"), "")
                    trace_status = _safe_md_text(trace.get("status"), "")
                    trace_warnings = "；".join(str(warning or "").strip() for warning in (trace.get("warnings") or []) if str(warning or "").strip())
                    detail_lines.append(f"  - {' / '.join(part for part in [requested, trace_status, trace_warnings] if part)}")
            if template_id:
                detail_lines.append(f"- 模板标识：{template_id}")
            evidence_ids = [int(ev_id) for ev_id in (item.get("evidence_ids") or []) if str(ev_id).isdigit()]
            if evidence_ids:
                detail_lines.append(f"- 关联证据：{_format_evidence_badges(evidence_ids)}")
                detail_lines.append("- 预览提示：可在下方“查看证据”中点击同编号按钮打开原文。")
            else:
                detail_lines.append("- 关联证据：当前未提取到编号，请以下方“参考来源 / 查看证据（同号按钮）”区块为准。")
            if detail_lines:
                lines.extend(["<details>", "<summary>展开决策细节</summary>", "", *detail_lines, "", "</details>"])
            lines.append("")

    return "\n".join(lines).strip()


def _render_weekly_structure_md(structured_data):
    if not isinstance(structured_data, dict):
        return ""

    constraints = structured_data.get("weekly_structure_constraints") or {}
    validation = structured_data.get("weekly_structure_validation") or {}
    if not isinstance(constraints, dict) or not constraints.get("required_workouts"):
        return ""

    requirements = [item for item in (constraints.get("required_workouts") or []) if isinstance(item, dict)]
    if not requirements:
        return ""

    lines = ["#### 🧩 个性化周结构要求", "", "| 训练单元 | 要求数量 | 日期要求 | 原文片段 |", "| :--- | :---: | :--- | :--- |"]
    for item in requirements:
        lines.append(
            "| "
            f"{_safe_md_text(item.get('display_name') or item.get('workout_type'))} | "
            f"{int(item.get('count') or 1)} | "
            f"{_safe_md_text(item.get('day'), '未指定')} | "
            f"{_safe_md_text(item.get('source_text'), '—')} |"
        )
    lines.append("")

    if isinstance(validation, dict) and validation:
        status_map = {
            "satisfied": "已满足",
            "partially_satisfied": "部分满足",
            "unsatisfied": "未满足",
        }
        lines.extend(["#### ✅ 周结构满足情况", "", f"- 状态：{status_map.get(validation.get('status'), _safe_md_text(validation.get('status'), '未知'))}"])
        matched = [item for item in (validation.get("matched_requirements") or []) if isinstance(item, dict)]
        if matched:
            lines.append("- 已满足：")
            for item in matched:
                days = "、".join(str(day or "").strip() for day in (item.get("matched_days") or []) if str(day or "").strip()) or "未定位日期"
                lines.append(
                    f"  - {_safe_md_text(item.get('display_name') or item.get('workout_type'))}："
                    f"要求 {int(item.get('required_count') or 0)} 节，已安排 {int(item.get('actual_count') or 0)} 节（{days}）"
                )
        violations = [item for item in (validation.get("violations") or []) if isinstance(item, dict)]
        if violations:
            lines.append("- 未满足/冲突：")
            for item in violations:
                lines.append(
                    f"  - {_safe_md_text(item.get('display_name') or item.get('workout_type'))}："
                    f"{_safe_md_text(item.get('reason'), '未达到用户要求')}"
                )
        warnings = [str(item or "").strip() for item in (validation.get("warnings") or []) if str(item or "").strip()]
        if warnings:
            lines.append("- 提醒：")
            for warning in warnings:
                lines.append(f"  - {_safe_md_text(warning)}")
        lines.append("")

    return "\n".join(lines).strip()


def _render_daily_workout_cards_md(structured_data):
    if not isinstance(structured_data, dict):
        return ""

    cards = [item for item in (structured_data.get("daily_workout_cards") or []) if isinstance(item, dict)]
    if not cards:
        return ""

    valid_cards = []
    missing_cards = []
    for card in cards:
        has_content = (
            card.get("main_set_candidates") or
            card.get("training_objective") or
            card.get("warmup_suggestion") or
            card.get("evidence_tier") == "action_library"
        )
        if has_content:
            valid_cards.append(card)
        else:
            missing_cards.append(card)

    lines = ["#### 📌 每日课表卡", ""]

    for card in valid_cards:
        title = _safe_md_text(card.get("title"), "课表卡")
        lines.append(f"##### {title}")
        lines.append("")
        sources = [str(item or "").strip() for item in (card.get("source") or []) if str(item or "").strip()]
        if sources:
            lines.append(f"**来源**：{'；'.join(sources[:3])}")
            lines.append("")
        training_type = _safe_md_text(card.get("training_type"), "")
        if training_type:
            lines.append(f"**训练类型**：{training_type}")
            lines.append("")
        candidates = [str(item or "").strip() for item in (card.get("main_set_candidates") or []) if str(item or "").strip()]
        if candidates:
            lines.append("**主训练候选**：")
            for index, candidate in enumerate(candidates, start=1):
                lines.append(f"{index}. {candidate}")
            lines.append("")
        intensity = _safe_md_text(card.get("intensity_target"), "")
        if intensity:
            lines.append("**强度目标**：")
            lines.append(intensity)
            lines.append("")
        zone_range = _safe_md_text(card.get("zone_range"), "")
        if zone_range and zone_range != intensity:
            lines.append("**强度区间**：")
            lines.append(zone_range)
            lines.append("")
        evidence_tier = _safe_md_text(card.get("evidence_tier"), "")
        if evidence_tier:
            tier_label_map = structured_data.get("evidence_tier_map", {})
            tier_label = tier_label_map.get(evidence_tier, evidence_tier)
            lines.append(f"**证据等级**：{tier_label}")
            lines.append("")
        objective = _safe_md_text(card.get("training_objective"), "")
        if objective:
            lines.append("**训练目标**：")
            lines.append(objective)
            lines.append("")
        warmup = _safe_md_text(card.get("warmup_suggestion"), "")
        if warmup:
            lines.append("**热身建议**：")
            lines.append(warmup)
            lines.append("")
        cooldown = _safe_md_text(card.get("cooldown_suggestion"), "")
        if cooldown:
            lines.append("**冷身建议**：")
            lines.append(cooldown)
            lines.append("")
        alternative = _safe_md_text(card.get("alternative_workout"), "")
        if alternative:
            lines.append("**备选训练**：")
            lines.append(alternative)
            lines.append("")
        evidence_status = card.get("evidence_status") or {}
        if isinstance(evidence_status, dict):
            status_text = []
            if evidence_status.get("main_set_candidates") == "direct":
                status_text.append("主训练有直接证据")
            if evidence_status.get("intensity_target") == "direct":
                status_text.append("强度目标有直接证据")
            if evidence_status.get("training_objective") == "direct":
                status_text.append("训练目标有直接证据")
            if evidence_status.get("warmup_suggestion") == "direct":
                status_text.append("热身建议有直接证据")
            missing = []
            if evidence_status.get("cooldown") == "missing":
                missing.append("冷身")
            if evidence_status.get("alternative_workout") == "missing":
                missing.append("替代训练")
            if missing:
                status_text.append(f"{'、'.join(missing)}还需要补充课表库")
            reason = _safe_md_text(evidence_status.get("reason"), "")
            if reason:
                status_text.append(reason)
            if status_text:
                lines.append("**证据状态**：")
                lines.append("；".join(status_text) + "。")
                lines.append("")

    if missing_cards and not valid_cards:
        lines.append("> ⚠️ 本次未生成完整每日课表卡：动作库证据不足，已保留基础训练计划。")
        lines.append("> 请在 Chainlit 页面中查看「训练日历」了解完整的月历课表视图（支持点击日期展开详情）。")
        lines.append("")

    return "\n".join(lines).strip()


def _collect_training_explanation_text(structured_data):
    if not isinstance(structured_data, dict):
        return ""

    panel = structured_data.get("training_explanation_panel") or {}
    if not isinstance(panel, dict):
        return ""

    parts = [_safe_md_text(panel.get("summary"), "")]
    for week in panel.get("weeks", []) or []:
        if not isinstance(week, dict):
            continue
        for item in week.get("items", []) or []:
            if not isinstance(item, dict):
                continue
            parts.extend(
                [
                    str(item.get("title", "") or ""),
                    str(item.get("why_scheduled", "") or ""),
                    str(item.get("primary_target", "") or ""),
                    str(item.get("risk_alert", "") or ""),
                    str(item.get("alternative_workout", "") or ""),
                    str(item.get("decision_summary", "") or ""),
                ]
            )
            evidence_ids = [
                int(ev_id)
                for ev_id in (item.get("evidence_ids") or [])
                if str(ev_id).isdigit()
            ]
            if evidence_ids:
                parts.append("".join(f"[{ev_id}]" for ev_id in evidence_ids))
    return " ".join(part for part in parts if str(part or "").strip()).strip()


def _render_structured_training_plan_md(structured_data):
    if not isinstance(structured_data, dict):
        return ""

    structured_plan = structured_data.get("structured_training_plan") or {}
    if not isinstance(structured_plan, dict):
        return ""

    plan_meta = structured_plan.get("plan_meta", {}) or {}
    phase_summary = structured_plan.get("phase_summary", []) or structured_data.get("phase_summary", []) or []
    week_sections = _normalize_week_sections_from_plan(structured_plan)
    if not week_sections:
        week_sections = structured_data.get("training_plan_weeks", []) or []
    if not week_sections:
        return ""
    first_week_actions = structured_plan.get("first_week_actions") or structured_data.get("training_plan_overview", {}).get("first_week_actions", []) or []

    lines = [
        "",
        "#### 🗓️ 结构化训练周期",
        "",
        f"- 周期类型：{_safe_md_text(plan_meta.get('plan_type'))}",
        f"- 请求周数：{plan_meta.get('requested_weeks', len(week_sections))}",
        f"- 实际周数：{plan_meta.get('actual_weeks', len(week_sections))}",
        f"- 训练目标：{_safe_md_text(plan_meta.get('goal'))}",
        f"- 经验等级：{_safe_md_text(plan_meta.get('experience_level'))}",
        f"- 目标比赛日期：{_safe_md_text(plan_meta.get('target_race_date'))}",
        "",
    ]

    if phase_summary:
        lines.extend(["#### 🧱 阶段拆分", ""])
        for phase in phase_summary:
            if not isinstance(phase, dict):
                continue
            lines.append(
                f"- {_safe_md_text(phase.get('phase'))}：第{phase.get('start_week', 0)}-{phase.get('end_week', 0)}周，目标：{_safe_md_text(phase.get('objective'))}"
            )
        lines.append("")

    if len(week_sections) >= 8:
        lines.extend(["#### 🧭 周卡片导航", ""])
        if phase_summary:
            for phase in phase_summary:
                if not isinstance(phase, dict):
                    continue
                start_week = int(phase.get("start_week") or 0)
                end_week = int(phase.get("end_week") or 0)
                week_count = max(0, end_week - start_week + 1)
                lines.append(
                    f"- {_safe_md_text(phase.get('phase'))}：第{start_week}-{end_week}周，共 {week_count} 周"
                )
        else:
            grouped_ranges = []
            current_phase = None
            range_start = 0
            range_end = 0
            for week in week_sections:
                phase_name = _safe_md_text(week.get("phase"))
                week_index = int(week.get("week_index") or 0)
                if current_phase != phase_name:
                    if current_phase is not None:
                        grouped_ranges.append((current_phase, range_start, range_end))
                    current_phase = phase_name
                    range_start = week_index
                range_end = week_index
            if current_phase is not None:
                grouped_ranges.append((current_phase, range_start, range_end))
            for phase_name, start_week, end_week in grouped_ranges:
                week_count = max(0, end_week - start_week + 1)
                lines.append(f"- {phase_name}：第{start_week}-{end_week}周，共 {week_count} 周")
        lines.append("")

    if first_week_actions:
        lines.extend(["#### 🚀 首周行动建议", ""])
        for action in first_week_actions:
            if str(action or "").strip():
                lines.append(f"- {_strip_pace(_safe_md_text(action))}")
        lines.append("")

    lines.extend(["#### 📅 当前周计划", ""])
    focus_week = next((week for week in week_sections if int(week.get("week_index") or 0) == 1), week_sections[0])
    week = focus_week
    week_index = int(week.get("week_index") or 0)
    repeat_guard = week.get("repeat_guard", {}) or {}
    long_run_minutes = int(repeat_guard.get("long_run_minutes") or 0)
    long_run_distance = repeat_guard.get("long_run_distance_km")
    weekly_volume = repeat_guard.get("weekly_volume_km")

    lines.append(
        f"##### 第{week_index}周 · {_safe_md_text(week.get('phase'))} · {_safe_md_text(week.get('load_level'))}"
    )
    lines.append(f"周目标：{_safe_md_text(week.get('week_goal'))}")
    lines.append(f"负荷说明：{_safe_md_text(week.get('load_progression_note'))}")
    lines.append(f"执行提醒：{_safe_md_text(week.get('execution_reminder'))}")

    digest_parts = [f"训练日 {int(week.get('training_day_count') or 0)} 天"]
    if int(repeat_guard.get("quality_session_count") or 0):
        digest_parts.append(f"质量课 {int(repeat_guard.get('quality_session_count') or 0)} 次")
    if long_run_distance is not None:
        digest_parts.append(f"长距离 {long_run_distance} km")
    elif long_run_minutes:
        digest_parts.append(f"长距离 {long_run_minutes} 分钟")
    if weekly_volume is not None:
        actual_km = sum(
            float((day.get("warmup_km") or 0) + (day.get("main_km") or 0) + (day.get("cooldown_km") or 0))
            for day in (week.get("days") or []) if isinstance(day, dict)
        )
        if actual_km > 0:
            digest_parts.append(f"周跑量 {actual_km:.1f}km (目标{weekly_volume}km)")
        else:
            digest_parts.append(f"周跑量约 {weekly_volume} km")
    if int(repeat_guard.get("rest_day_count") or 0):
        digest_parts.append(f"休息 {int(repeat_guard.get('rest_day_count') or 0)} 天")
    lines.append("训练摘要：" + " / ".join(digest_parts))
    lines.append("")

    key_workouts = [_strip_pace(item) for item in (week.get("key_workouts") or []) if str(item or "").strip()]
    if not key_workouts:
        key_workouts = []
        for day in week.get("days", []) or []:
            if not isinstance(day, dict):
                continue
            training_type = _safe_md_text(day.get("training_type"))
            main_set = _strip_pace(_safe_md_text(day.get("main_set")))
            if training_type != "休息" and len(key_workouts) < 3:
                key_workouts.append(f"{_safe_md_text(day.get('day'))} {training_type}：{main_set}")
    if key_workouts:
        lines.append("关键训练：" + "；".join(key_workouts))
    action_suggestions = [_strip_pace(item) for item in (week.get("action_suggestions") or []) if str(item or "").strip()]
    if action_suggestions:
        lines.append("行动建议：" + "；".join(action_suggestions))
    lines.append("")

    lines.append("**7 天缩略行**")
    for day in week.get("days", []) or []:
        if not isinstance(day, dict):
            continue
        day_label = _safe_md_text(day.get("day"))
        training_type = _safe_md_text(day.get("training_type"))
        main_set = _strip_pace(_safe_md_text(day.get("main_set"), ""))
        km_total = 0.0
        for key in ("warmup_km", "main_km", "cooldown_km"):
            try:
                km_total += float(day.get(key) or 0)
            except (TypeError, ValueError):
                pass
        km_text = f" · {km_total:.1f}km" if km_total > 0 else ""
        suffix = f" · {main_set}" if main_set and main_set != "—" else ""
        lines.append(f"- {day_label}：{training_type}{km_text}{suffix}")
    lines.append("")

    lines.append("<details>")
    lines.append(f"<summary>按需展开第{week_index}周每日详情</summary>")
    lines.append("")
    for day in week.get("days", []) or []:
        if not isinstance(day, dict):
            continue
        lines.append(f"**{_safe_md_text(day.get('day'))}｜{_safe_md_text(day.get('training_type'))}**  ")
        lines.append(f"热身：{_safe_md_text(day.get('warmup'))}  ")
        lines.append(f"主训练：{_strip_pace(_safe_md_text(day.get('main_set')))}  ")
        lines.append(f"放松：{_safe_md_text(day.get('cooldown'))}  ")
        wu_km = day.get("warmup_km", 0) or 0
        main_km = day.get("main_km", 0) or 0
        cd_km = day.get("cooldown_km", 0) or 0
        total_km = wu_km + main_km + cd_km
        if total_km > 0:
            km_parts = []
            if wu_km > 0:
                km_parts.append(f"热身{wu_km:.1f}km")
            if main_km > 0:
                km_parts.append(f"主课{main_km:.1f}km")
            if cd_km > 0:
                km_parts.append(f"冷身{cd_km:.1f}km")
            lines.append(f"跑量：{' + '.join(km_parts)} = **{total_km:.1f}km**  ")
        lines.append(f"场地：{_safe_md_text(day.get('venue'))}")
        notes = _safe_md_text(day.get("notes"), fallback="")
        if notes:
            lines.append(f"备注：{notes}")
        lines.append("")
    lines.append("</details>")
    lines.append("")

    if len(week_sections) > 1:
        lines.extend(["<details>", "<summary>查看其他周摘要</summary>", ""])
        for other_week in week_sections:
            if not isinstance(other_week, dict) or int(other_week.get("week_index") or 0) == week_index:
                continue
            other_index = int(other_week.get("week_index") or 0)
            other_digest = [f"训练日 {int(other_week.get('training_day_count') or 0)} 天"]
            other_repeat_guard = other_week.get("repeat_guard", {}) or {}
            if int(other_repeat_guard.get("quality_session_count") or 0):
                other_digest.append(f"质量课 {int(other_repeat_guard.get('quality_session_count') or 0)} 次")
            if other_repeat_guard.get("long_run_distance_km") is not None:
                other_digest.append(f"长距离 {other_repeat_guard.get('long_run_distance_km')} km")
            if other_repeat_guard.get("weekly_volume_km") is not None:
                other_digest.append(f"周跑量约 {other_repeat_guard.get('weekly_volume_km')} km")
            lines.append(
                f"- 第{other_index}周 · {_safe_md_text(other_week.get('phase'))} · {_safe_md_text(other_week.get('load_level'))}："
                f"{_safe_md_text(other_week.get('week_goal'))}（{' / '.join(other_digest)}）"
            )
        lines.extend(["", "</details>", ""])

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

        structured_plan_md = _render_structured_training_plan_md(structured_data)
        weekly_structure_md = _render_weekly_structure_md(structured_data)
        daily_workout_cards_md = _render_daily_workout_cards_md(structured_data)
        half_marathon_protocol_md = _render_half_marathon_protocol_panel_md(structured_data)

        summary = structured_data.get('summary', '')
        adaptive_adjustment_md = _render_adaptive_adjustment_md(structured_data)
        training_explanation_md = _render_training_explanation_panel_md(structured_data)
        if structured_plan_md:
            summary = structured_data.get("training_plan_overview", {}).get("goal", "") or structured_data.get('summary', '')
        if not summary or summary.startswith("（本轮未产生"):
            summary = (raw_report or structured_data.get('summary', '无摘要'))
        if structured_plan_md:
            meta = (structured_data.get("structured_training_plan") or {}).get("plan_meta", {}) or {}
            summary = (
                f"已生成 {meta.get('actual_weeks', 0)} 周结构化训练计划，"
                f"目标为 {_safe_md_text(meta.get('goal'))}，"
                "下方按周展示固定训练结构，优先避免多周 Markdown 截断与错位。"
            )

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

        if adaptive_adjustment_md:
            md += adaptive_adjustment_md + "\n\n"

        if half_marathon_protocol_md:
            md += half_marathon_protocol_md + "\n\n"

        if training_explanation_md:
            md += training_explanation_md + "\n\n"

        if weekly_structure_md:
            md += weekly_structure_md + "\n\n"

        if daily_workout_cards_md:
            md += daily_workout_cards_md + "\n\n"

        # 收集所有正文中出现的引用 ID
        all_cited_text = summary
        all_cited_text += " " + _collect_training_explanation_text(structured_data)
        
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

        if structured_plan_md:
            md += "\n" + structured_plan_md + "\n"

        if include_sources:
            # 从汇总的文本中提取所有引用的 ID
            cited_ids = _extract_citation_ids(all_cited_text)
            sources_md = _render_evidence_base_md(evidence_base, cited_ids)
            if sources_md:
                md += "\n" + sources_md + "\n"

        return md

    @staticmethod
    def render_chainlit_wiki_context_md(structured_data):
        if not isinstance(structured_data, dict):
            return ""

        analysis_framework = structured_data.get("analysis_framework", {}) or {}
        wiki_context = str(analysis_framework.get("wiki_context", "") or "").strip()
        if not wiki_context or wiki_context == "暂无外部概念补充":
            return ""

        return (
            "### 🌐 Wiki补充\n\n"
            "> 以下内容仅用于概念背景解释，不作为训练处方依据，也不对应本地知识库编号引用。\n\n"
            f"{wiki_context}\n"
        )

    @staticmethod
    def build_evidence_preview_bundle(structured_data, raw_report, max_items: int = 5):
        import re

        if not structured_data:
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
        all_cited_text += " " + _collect_training_explanation_text(structured_data)

        cited_ids = _extract_citation_ids(all_cited_text)
        evidence_base = structured_data.get("evidence_base", [])

        # 兼容 LLM 偶尔不遵守编号规则而输出 [来源: xxx.pdf] 的情况
        source_pattern_ids = _match_source_to_evidence_ids(all_cited_text, evidence_base)
        for src_id in source_pattern_ids:
            if src_id not in cited_ids:
                cited_ids.append(src_id)

        if not evidence_base:
            if cited_ids:
                return {
                    "panel_md": "\n".join(
                        [
                            "<details>",
                            "<summary>查看证据（同号按钮）</summary>",
                            "",
                            "当前已检测到证据编号，但本轮没有可用的证据基底，暂时无法生成同号预览按钮。",
                            "",
                            "</details>",
                        ]
                    ).strip(),
                    "actions": [],
                }
            return {"panel_md": "", "actions": []}

        # 获取所有引用过的证据项，不设数量限制以确保正文所有 [n] 都能跳转
        all_evidence_items = _resolve_cited_evidence_items(evidence_base, cited_ids)
        pathless_items = [item for item in all_evidence_items if not item.get("path")]
        all_evidence_items = [item for item in all_evidence_items if item.get("path")]

        if not all_evidence_items:
            if pathless_items:
                source_labels = "、".join(
                    f"[{item['id']}] {item['source']}"
                    for item in pathless_items[:3]
                )
                return {
                    "panel_md": "\n".join(
                        [
                            "<details>",
                            "<summary>查看证据（同号按钮）</summary>",
                            "",
                            "当前已识别到证据来源，但原文路径缺失，暂时无法生成同号预览按钮。",
                            f"受影响来源：{source_labels}" if source_labels else "",
                            "",
                            "</details>",
                        ]
                    ).strip(),
                    "actions": [],
                }
            return {"panel_md": "", "actions": []}

        lines = [
            "<details>",
            "<summary>查看证据（同号按钮）</summary>",
            "",
            "点击与上方证据编号同号的按钮，可直接预览对应原文：",
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
