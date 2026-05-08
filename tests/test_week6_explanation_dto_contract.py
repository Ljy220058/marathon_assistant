import sys
from pathlib import Path


root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from marathon_qa_assistant.apps.chainlit.plan_ui import (
    build_training_explanation_card,
    extract_training_explanation_context,
    render_training_explanation_card_md,
)
from marathon_qa_assistant.nodes.output_nodes import _build_structured_report
from marathon_qa_assistant.ui.legacy_ui import UIHelper


def test_training_explanation_panel_marks_fallback_source_and_stable_fields():
    report = _build_structured_report(
        {
            "query": "帮我解释这周阈值跑安排",
            "category": "coach",
            "mode": "team",
            "audit_scores": {"consistency": 88, "safety": 92, "roi": 75},
            "structured_training_plan": {
                "plan_meta": {
                    "requested_weeks": 4,
                    "actual_weeks": 4,
                    "goal": "半马 90 分",
                    "experience_level": "进阶",
                    "target_race_date": "4周后",
                    "plan_type": "multi_week",
                    "render_version": "v1",
                },
                "week_plans": [
                    {
                        "week_index": 1,
                        "phase": "基础期",
                        "week_goal": "建立节奏与长距离基础",
                        "load_level": "medium",
                        "load_progression_note": "本周总量稳定，聚焦节奏跑与长距离。",
                        "execution_reminder": "注意周日长距离后补给。",
                        "key_workouts": ["周二 节奏跑：20分钟阈值跑"],
                        "days": [
                            {
                                "day": "周二",
                                "training_type": "节奏跑",
                                "warmup": "慢跑15分钟",
                                "main_set": "20分钟阈值跑",
                                "cooldown": "慢跑10分钟",
                                "venue": "田径场",
                                "notes": "保持稳定呼吸。",
                            }
                        ],
                    }
                ],
            },
        },
        "已生成本周解释。",
    )

    panel = report["training_explanation_panel"]
    week = panel["weeks"][0]
    item = week["items"][0]

    assert panel["panel_version"] == "v2"
    assert panel["coverage_status"] == "full"
    assert week["week_goal"] == "建立节奏与长距离基础"
    assert week["execution_reminder"] == "注意周日长距离后补给。"
    assert week["item_count"] == 1
    assert item["item_id"] == "week1_item1"
    assert item["explanation_source"] == "fallback_heuristic"
    assert item["target_labels"] == ["乳酸阈", "专项节奏"]
    assert item["warnings"] == []
    assert item["adjustments"] == []
    assert item["constraints"] == []
    assert item["decision_trace"] == []


def test_training_explanation_panel_preserves_decision_graph_metadata():
    report = _build_structured_report(
        {
            "query": "请解释这周关键训练为什么这么排",
            "category": "coach",
            "mode": "team",
            "audit_scores": {"consistency": 90, "safety": 95, "roi": 80},
            "rag_sources": [{"id": 1}, {"id": 2}],
            "structured_training_plan": {
                "plan_meta": {
                    "requested_weeks": 2,
                    "actual_weeks": 2,
                    "goal": "半马 PB",
                    "experience_level": "进阶",
                    "target_race_date": "2周后",
                    "plan_type": "multi_week",
                    "render_version": "v1",
                },
                "week_plans": [
                    {
                        "week_index": 1,
                        "phase": "专项期",
                        "week_goal": "围绕半马专项节奏做最后两次关键刺激",
                        "load_level": "medium-high",
                        "load_progression_note": "本周以专项刺激为主。",
                        "execution_reminder": "若周二主课后疲劳过高，周四先降强度。",
                        "key_workouts": ["周二 节奏跑：3 x 10分钟阈值跑"],
                        "days": [
                            {
                                "day": "周二",
                                "training_type": "节奏跑",
                                "warmup": "慢跑15分钟",
                                "main_set": "3 x 10分钟阈值跑",
                                "cooldown": "慢跑10分钟",
                                "venue": "田径场",
                                "notes": "两组之间慢跑 3 分钟。",
                                "draft": {
                                    "status": "adjusted",
                                    "template_id": "tempo_threshold",
                                    "physiology_targets": ["乳酸阈", "专项节奏"],
                                    "adaptation_targets": ["稳态耐力"],
                                    "warnings": ["上一堂质量课距离不足 48h，已下调刺激密度。"],
                                    "adjustments": ["duration_min 按 conservative 档位取值为 30"],
                                    "constraints": [
                                        {
                                            "rule": "quality_gap_48h",
                                            "status": "adjusted",
                                            "message": "距离上一堂质量课不足 48h，已自动下调主课刺激。",
                                        }
                                    ],
                                    "decision_trace": [
                                        {
                                            "requested": "节奏跑",
                                            "status": "blocked",
                                            "warnings": ["上一堂质量课距离不足 48h"],
                                        },
                                        {
                                            "requested": "节奏跑-保守版",
                                            "status": "adjusted",
                                            "warnings": [],
                                        },
                                    ],
                                },
                            }
                        ],
                    }
                ],
            },
        },
        "已生成解释报告。",
    )

    panel = report["training_explanation_panel"]
    week = panel["weeks"][0]
    item = week["items"][0]

    assert panel["panel_version"] == "v2"
    assert panel["coverage_status"] == "full"
    assert week["phase"] == "专项期"
    assert week["week_goal"] == "围绕半马专项节奏做最后两次关键刺激"
    assert week["execution_reminder"] == "若周二主课后疲劳过高，周四先降强度。"
    assert week["item_count"] == 1
    assert item["item_id"] == "week1_item1"
    assert item["template_id"] == "tempo_threshold"
    assert item["status"] == "adjusted"
    assert item["explanation_source"] == "decision_graph"
    assert item["target_labels"] == ["乳酸阈", "专项节奏", "稳态耐力"]
    assert item["warnings"] == ["上一堂质量课距离不足 48h，已下调刺激密度。"]
    assert item["adjustments"] == ["duration_min 按 conservative 档位取值为 30"]
    assert item["evidence_ids"] == [1, 2]
    assert item["constraints"] == [
        {
            "rule": "quality_gap_48h",
            "status": "adjusted",
            "message": "距离上一堂质量课不足 48h，已自动下调主课刺激。",
        }
    ]
    assert item["decision_trace"] == [
        {
            "requested": "节奏跑",
            "status": "blocked",
            "warnings": ["上一堂质量课距离不足 48h"],
        },
        {
            "requested": "节奏跑-保守版",
            "status": "adjusted",
            "warnings": [],
        },
    ]

    shared_md = UIHelper.render_structured_report(report, "已生成解释报告。", include_sources=False)
    assert "<summary>展开决策细节</summary>" in shared_md
    assert "- 约束检查：" in shared_md
    assert "quality_gap_48h / adjusted / 距离上一堂质量课不足 48h，已自动下调主课刺激。" in shared_md
    assert "- 决策轨迹：" in shared_md
    assert "节奏跑 / blocked / 上一堂质量课距离不足 48h" in shared_md
    assert "- 关联证据：`[1]` `[2]`" in shared_md
    assert "- 预览提示：可在下方“查看证据”中点击同编号按钮打开原文。" in shared_md

    context = extract_training_explanation_context({"structured_report": report})
    card = build_training_explanation_card(context)
    card_md = render_training_explanation_card_md(card)
    assert card["items"][0]["constraints"] == item["constraints"]
    assert card["items"][0]["decision_trace"] == item["decision_trace"]
    assert "<summary>打开解释抽屉：决策细节与证据</summary>" in card_md
    assert "- 约束告警：" in card_md
    assert "- 自动调整：" in card_md
    assert "- 约束检查：" in card_md
    assert "- 决策轨迹：" in card_md
    assert "- 关联证据：`[1]` `[2]`" in card_md
    assert "- 预览提示：可在下方“查看证据”中点击同编号按钮打开原文。" in card_md


def test_training_explanation_panel_evidence_ids_feed_sources_preview_without_inline_citations():
    report = {
        "title": "马拉松专业分析报告",
        "summary": "这是一个不带正文引用的解释摘要。",
        "evidence_base": [
            {
                "id": 1,
                "source": "evidence_a.pdf",
                "path": r"C:\kb\evidence_a.pdf",
                "page": 3,
                "text": "证据 A 摘要",
            },
            {
                "id": 2,
                "source": "evidence_b.pdf",
                "path": r"C:\kb\evidence_b.pdf",
                "page": 5,
                "text": "证据 B 摘要",
            },
        ],
        "training_explanation_panel": {
            "coverage_ratio": 1.0,
            "explained_key_workouts": 1,
            "total_key_workouts": 1,
            "audit_summary": "解释完整。",
            "summary": "本周关键训练已完成解释。",
            "weeks": [
                {
                    "week_index": 1,
                    "phase": "专项期",
                    "load_level": "medium-high",
                    "items": [
                        {
                            "title": "周二 节奏跑",
                            "why_scheduled": "围绕专项目标安排。",
                            "primary_target": "专项节奏",
                            "risk_alert": "疲劳高时降强度。",
                            "alternative_workout": "改为轻松跑 40 分钟。",
                            "decision_summary": "按保守版执行。",
                            "evidence_ids": [1, 2],
                        }
                    ],
                }
            ],
        },
    }

    shared_md = UIHelper.render_structured_report(report, "原始报告", include_sources=True)
    assert "#### 参考来源" in shared_md
    assert "[1] evidence_a.pdf P.3" in shared_md
    assert "[2] evidence_b.pdf P.5" in shared_md

    preview_bundle = UIHelper.build_evidence_preview_bundle(report, "原始报告", max_items=5)
    assert "<summary>查看证据（同号按钮）</summary>" in preview_bundle["panel_md"]
    assert "点击与上方证据编号同号的按钮，可直接预览对应原文：" in preview_bundle["panel_md"]
    assert "- [1] evidence_a.pdf P.3" in preview_bundle["panel_md"]
    assert "- [2] evidence_b.pdf P.5" in preview_bundle["panel_md"]
    assert [action["id"] for action in preview_bundle["actions"]] == ["view_pdf_1", "view_pdf_2"]


def test_training_explanation_panel_multi_week_empty_state_and_card_note():
    report = {
        "training_explanation_panel": {
            "coverage_ratio": 0.5,
            "explained_key_workouts": 1,
            "total_key_workouts": 2,
            "audit_summary": "部分周次已解释。",
            "summary": "本轮生成了多周解释。",
            "weeks": [
                {
                    "week_index": 1,
                    "phase": "基础期",
                    "load_level": "medium",
                    "items": [],
                },
                {
                    "week_index": 2,
                    "phase": "专项期",
                    "load_level": "medium-high",
                    "items": [
                        {
                            "title": "周四 间歇跑",
                            "why_scheduled": "为了补专项刺激。",
                            "primary_target": "速度耐力",
                            "risk_alert": "恢复不足先降量。",
                            "alternative_workout": "改为轻松跑 45 分钟。",
                            "decision_summary": "优先保证质量。",
                            "evidence_ids": [],
                        }
                    ],
                },
            ],
        }
    }

    shared_md = UIHelper.render_structured_report(report, "原始报告", include_sources=False)
    assert "> 本周暂无关键训练解释项。" in shared_md
    assert "> 如为多周计划，其他周解释请继续向下查看。" in shared_md

    context = extract_training_explanation_context({"structured_report": report}, week_index=2)
    card = build_training_explanation_card(context)
    card_md = render_training_explanation_card_md(card)
    assert card["total_weeks"] == 2
    assert card["available_week_indexes"] == [1, 2]
    assert "**多周说明**：当前仅展示第 2 周关键解释；完整解释覆盖 第 1 周 / 第 2 周，其余周请以上方共享报告为准。" in card_md
    assert "- 关联证据：当前未提取到编号，请以下方“参考来源 / 查看证据（同号按钮）”区块为准。" in card_md


def test_evidence_preview_bundle_reports_missing_paths_instead_of_silent_drop():
    report = {
        "summary": "解释摘要 [1]",
        "evidence_base": [
            {
                "id": 1,
                "source": "missing_path.pdf",
                "path": "",
                "page": 2,
                "text": "只有来源，没有路径。",
            }
        ],
        "training_explanation_panel": {
            "summary": "关键训练解释。",
            "weeks": [],
        },
    }

    preview_bundle = UIHelper.build_evidence_preview_bundle(report, "原始报告", max_items=5)
    assert "<summary>查看证据（同号按钮）</summary>" in preview_bundle["panel_md"]
    assert "当前已识别到证据来源，但原文路径缺失，暂时无法生成同号预览按钮。" in preview_bundle["panel_md"]
    assert "受影响来源：[1] missing_path.pdf" in preview_bundle["panel_md"]
    assert preview_bundle["actions"] == []
