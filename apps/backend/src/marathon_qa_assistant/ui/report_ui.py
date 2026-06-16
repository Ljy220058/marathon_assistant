"""Structured report rendering helpers.

Astro is the current frontend. This module keeps a minimal compatibility layer
for structured-report rendering and evidence preview bundles.
"""

from datetime import date
from typing import Any


def _safe_text(value: Any, fallback: str = "—") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _format_wiki_context(wiki_context: str) -> str:
    text = str(wiki_context or "").strip()
    return text or "暂无外部概念补充"


def _render_daily_workout_cards(structured_data: dict[str, Any]) -> list[str]:
    cards = []
    tier_map = structured_data.get("evidence_tier_map") or {}
    for card in structured_data.get("daily_workout_cards") or []:
        title = _safe_text(card.get("title"))
        if "课表证据不足" in title:
            continue
        cards.append(f"- {title}")
        tier = _safe_text(card.get("evidence_tier_label"))
        if tier == "—":
            tier = _safe_text(tier_map.get(card.get("evidence_tier")))
        if tier != "—":
            cards.append(f"  - {tier}")
        source = _safe_text(card.get("source"))
        if source != "—":
            cards.append(f"  - {source}")
        status = card.get("evidence_status") or {}
        reason = status.get("reason")
        if reason:
            cards.append(f"  - {reason}")
        if status.get("main_set_candidates") == "direct":
            cards.append("  - 冷身、替代训练还需要补充课表库")
    if not cards:
        return ["本次未生成完整每日课表卡"]
    return cards


def _render_half_marathon_protocol_panel(structured_data: dict[str, Any]) -> list[str]:
    panel = structured_data.get("half_marathon_protocol_panel") or {}
    if not panel:
        return []
    lines = ["#### 🧩 半马协议"]
    if panel.get("status"):
        lines.append(f"状态：{panel['status']}")
    selected = panel.get("selected_archetype") or {}
    if selected.get("label"):
        lines.append(f"类型：{selected['label']}")
    if panel.get("pace_calibration"):
        pace = panel["pace_calibration"]
        if pace.get("target_hmp_pace"):
            lines.append(f"目标配速：{pace['target_hmp_pace']}")
    return lines


def _render_training_explanation_panel(structured_data: dict[str, Any]) -> list[str]:
    panel = structured_data.get("training_explanation_panel") or {}
    if not panel:
        return []
    lines = ["#### 🧠 训练解释"]
    for week in panel.get("weeks") or []:
        if week.get("week_goal"):
            lines.append(f"- {week['week_goal']}")
        for item in week.get("items") or []:
            if item.get("title"):
                lines.append(f"  - {item['title']}")
            if item.get("decision_trace"):
                lines.append("  - 决策轨迹")
            if item.get("evidence_ids"):
                ids = " ".join(f"`[{i}]`" for i in item["evidence_ids"])
                lines.append(f"  - 关联证据：{ids}")
    return lines


def _render_evidence_base(structured_data: dict[str, Any]) -> list[str]:
    evidence = structured_data.get("evidence_base") or []
    if not evidence:
        return []
    lines = ["#### 参考来源"]
    for item in evidence:
        source = item.get("source") or item.get("document")
        if not source:
            continue
        page = item.get("page")
        lines.append(f"- [{item.get('id')}] {source} P.{page}")
    return lines


class UIHelper:
    @staticmethod
    def render_structured_report(structured_data, raw_report, include_sources: bool = False):
        if not structured_data:
            return str(raw_report or "当前没有可显示的报告内容。").strip()

        title = _safe_text(structured_data.get("title"), "马拉松专业分析报告")
        summary = _safe_text(structured_data.get("summary"), _safe_text(raw_report))
        lines = [
            f"### 🏃‍♂️ {title}",
            "",
            f"**Generated on**: {date.today().isoformat()} | Marathon QA Assistant",
            "",
        ]

        if structured_data.get("training_explanation_panel"):
            lines.extend(_render_training_explanation_panel(structured_data))
        if structured_data.get("half_marathon_protocol_panel"):
            lines.extend(_render_half_marathon_protocol_panel(structured_data))
        if structured_data.get("monthly_training_calendar"):
            lines.append("#### 月度日历")
        if structured_data.get("daily_workout_cards") is not None:
            lines.append("#### 📌 每日课表卡")
            lines.extend(_render_daily_workout_cards(structured_data))
        if include_sources and structured_data.get("evidence_base"):
            lines.extend(_render_evidence_base(structured_data))

        lines.extend(["", "---", "", "#### 核心摘要", "", summary])
        return "\n".join(lines).strip()

    @staticmethod
    def render_wiki_context_md(structured_data):
        if not isinstance(structured_data, dict):
            return ""
        analysis_framework = structured_data.get("analysis_framework", {}) or {}
        wiki_context = str(analysis_framework.get("wiki_context", "") or "").strip()
        if not wiki_context:
            return ""
        return f"### Wiki补充\n\n{wiki_context}\n"

    @staticmethod
    def build_evidence_preview_bundle(structured_data, raw_report, max_items: int = 5):
        evidence_base = list((structured_data or {}).get("evidence_base") or [])
        items = evidence_base[:max_items]
        panel_md = (
            "\n".join(
                [
                    "<details>",
                    "<summary>查看证据（同号按钮）</summary>",
                    "",
                    *[
                        f"- [{item.get('id')}] {item.get('source')} P.{item.get('page')}"
                        for item in items
                        if item.get("source")
                    ],
                    "",
                    "</details>",
                ]
            ).strip()
            if items
            else ""
        )
        actions = [
            {
                "id": f"view_pdf_{item.get('id')}",
                "name": "view_pdf",
                "payload": {
                    "path": item.get("path", ""),
                    "name": item.get("source", ""),
                    "page": item.get("page", 1),
                    "snippet": item.get("text", ""),
                },
                "label": f"[{item.get('id')}] {item.get('source', '')} P.{item.get('page', '')}",
            }
            for item in items
            if item.get("source")
        ]
        return {"panel_md": panel_md, "actions": actions}
