from marathon_qa_assistant.apps.chainlit.plan_ui import (
    build_calendar_props_with_explanations,
    build_entry_status_bar_props,
    build_training_explanation_card,
    build_explanation_drawer_props,
    build_week_training_card_props,
    extract_entry_status_context,
    extract_training_explanation_context,
    extract_current_week_context,
)


def _sample_state():
    state = {
        "structured_report": {
            "structured_training_plan": {
                "plan_meta": {
                    "requested_weeks": 2,
                    "actual_weeks": 2,
                    "goal": "半马完赛",
                    "plan_type": "base",
                    "start_date": "2026-05-04",
                },
                "week_plans": [
                    {
                        "week_index": 1,
                        "phase": "基础期",
                        "load_level": "中",
                        "week_goal": "建立稳定跑量",
                        "training_day_count": 2,
                        "days": [
                            {
                                "day": "周一",
                                "training_type": "休息",
                                "main_set": "休息",
                                "warmup_km": 0,
                                "main_km": 0,
                                "cooldown_km": 0,
                            },
                            {
                                "day": "周二",
                                "training_type": "轻松跑",
                                "warmup": "热身 10 分钟",
                                "main_set": "轻松跑 30 分钟",
                                "cooldown": "放松 5 分钟",
                                "warmup_km": 1.0,
                                "main_km": 5.0,
                                "cooldown_km": 0.5,
                                "venue": "操场",
                                "notes": "保持轻松",
                            },
                        ],
                        "key_workouts": ["轻松跑"],
                        "action_suggestions": ["控制配速"],
                        "execution_reminder": "循序渐进。",
                    },
                    {
                        "week_index": 2,
                        "phase": "基础期",
                        "load_level": "中",
                        "week_goal": "继续累积",
                    },
                ],
                "training_explanation_panel": {
                    "coverage_ratio": 0.75,
                    "summary": "大部分安排可追溯。",
                    "weeks": [
                        {
                            "week_index": 1,
                            "phase": "基础期",
                            "load_level": "中",
                            "items": [
                                {
                                    "day": "周二",
                                    "title": "轻松跑",
                                    "why_scheduled": "用于打底。",
                                    "primary_target": "建立有氧基础。",
                                    "risk_alert": "注意前半程别冲。",
                                    "alternative_workout": "改为 30 分钟快走。",
                                    "decision_summary": "按基础期节奏安排。",
                                    "template_id": "easy_run",
                                    "status": "matched",
                                    "explanation_source": "action_library",
                                    "target_labels": ["有氧", "恢复"],
                                    "evidence_ids": [1, 2],
                                }
                            ],
                        }
                    ],
                },
                "monthly_training_calendar": {
                    "start_week_index": 1,
                    "end_week_index": 2,
                    "phases": [{"phase": "基础期", "start_week": 1, "end_week": 2}],
                    "days": [
                        {
                            "week_index": 1,
                            "day_label": "周一",
                            "training_type": "休息",
                            "is_rest": True,
                            "evidence_tier": "plan_only",
                        },
                        {
                            "week_index": 1,
                            "day_label": "周二",
                            "training_type": "轻松跑",
                            "is_rest": False,
                            "zone_range": "Z2",
                            "evidence_tier": "action_library",
                        },
                    ],
                    "evidence_summary": {},
                },
            },
            "training_plan_overview": {
                "current_phase": "基础期",
            },
            "training_plan_weeks": [
                {
                    "week_index": 1,
                    "phase": "基础期",
                    "load_level": "中",
                    "week_goal": "建立稳定跑量",
                    "training_day_count": 2,
                    "days": [
                        {"day": "周一", "training_type": "休息", "main_set": "休息"},
                        {"day": "周二", "training_type": "轻松跑", "main_set": "轻松跑 30 分钟", "warmup_km": 1.0, "main_km": 5.0, "cooldown_km": 0.5},
                    ],
                    "key_workouts": ["轻松跑"],
                    "action_suggestions": ["控制配速"],
                    "execution_reminder": "循序渐进。",
                }
            ],
            "daily_schedule_cards": [
                {
                    "week_index": 1,
                    "day_index": 2,
                    "zone_range": "Z2",
                    "zone_label": "Z2",
                    "intensity_target": "轻松",
                    "evidence_tier": "action_library",
                    "evidence_tier_label": "动作库课表",
                }
            ],
        }
    }
    structured_plan = state["structured_report"]["structured_training_plan"]
    state["structured_report"]["training_explanation_panel"] = structured_plan["training_explanation_panel"]
    state["structured_report"]["monthly_training_calendar"] = structured_plan["monthly_training_calendar"]
    return state


def test_entry_status_week_and_explanation_props_align_with_current_week():
    state = _sample_state()

    entry_context = extract_entry_status_context(state)
    week_context = extract_current_week_context(state)
    explanation_context = extract_training_explanation_context(state)
    calendar_props = build_calendar_props_with_explanations(state)

    entry_props = build_entry_status_bar_props(entry_context)
    week_props = build_week_training_card_props(week_context)
    explanation_props = build_explanation_drawer_props(build_training_explanation_card(explanation_context))

    assert entry_props["week_index"] == 1
    assert entry_props["training_type"] == "轻松跑"
    assert week_props["week_index"] == 1
    assert week_props["days"][1]["training_type"] == "轻松跑"
    assert explanation_props["coverage_ratio"] == 75
    assert explanation_props["evidence_ids"] == [1, 2]
    assert calendar_props["days"][1]["explanation"]["primary_target"] == "建立有氧基础。"
