from marathon_qa_assistant.nodes.output_nodes import _build_structured_report


def _day(day, training_type="半马专项", main_set="16km @90% HMP 稳定跑"):
    return {
        "day": day,
        "training_type": training_type,
        "warmup": "慢跑 15 分钟",
        "main_set": main_set,
        "cooldown": "慢跑 10 分钟",
        "venue": "公路",
        "notes": "按体感控制。",
        "warmup_km": 2.0,
        "main_km": 16.0,
        "cooldown_km": 1.5,
    }


def _hmp_structured_plan(validation=None):
    return {
        "plan_meta": {
            "requested_weeks": 1,
            "actual_weeks": 1,
            "goal": "半马 PB",
            "experience_level": "进阶",
            "plan_type": "multi_week",
            "render_version": "v1",
        },
        "phase_summary": [
            {
                "phase": "专项能力构建阶段",
                "start_week": 1,
                "end_week": 1,
                "objective": "构建 90-95% HMP 支撑能力。",
            }
        ],
        "week_plans": [
            {
                "week_index": 1,
                "phase": "专项能力构建阶段",
                "week_goal": "HMP协议：专项能力构建阶段；候选课表：半马辅助耐力跑",
                "load_level": "medium",
                "load_progression_note": "本周稳步进入半马专项支撑。",
                "execution_reminder": "疲劳明显时下调。",
                "key_workouts": ["周四 半马专项：16km @90% HMP 稳定跑"],
                "action_suggestions": ["保留 48 小时恢复。"],
                "repeat_guard_signature": {"weekly_volume_km": 58},
                "days": [
                    _day("周一", "休息", "休息"),
                    _day("周四"),
                    _day("周日", "长距离", "90 分钟轻松长跑"),
                ],
            }
        ],
        "half_marathon_protocol": {
            "active": True,
            "recent_marathon": True,
            "input_weekly_mileage_km": 50,
            "profile_gaps": [
                {
                    "field": "current_10k_time",
                    "label": "当前10K成绩",
                    "reason": "105% HMP 中长间歇更适合用当前 5K/10K 能力校准。",
                    "severity": "warning",
                }
            ],
            "pace_calibration": {
                "status": "ambitious_target",
                "speed_calibration_available": True,
                "target_hmp_pace": "4:16/km",
                "current_hmp_pace": "4:28/km",
                "gap_seconds_per_km": 12.0,
                "current_zone_table": [
                    {
                        "zone_id": "support_endurance_90",
                        "label": "90% HMP 支撑耐力",
                        "percent": "90%",
                        "pace": "4:58/km",
                        "purpose": "半马专项耐力前置支撑",
                    },
                    {
                        "zone_id": "race_specific_100",
                        "label": "100% HMP 比赛专项",
                        "percent": "100%",
                        "pace": "4:28/km",
                        "purpose": "目标配速巡航能力",
                    },
                ],
                "notes": ["目标 HMP 快于当前能力估计，专项课应优先使用当前能力配速并保守推进。"],
            },
            "capacity_budget": {
                "quality_sessions_max": 1,
                "hmp_95_max_km": 10,
                "hmp_100_total_max_km": 4,
                "hmp_105_total_max_km": 4,
                "hmp_110_total_max_km": 2,
                "notes": ["周跑量低于 65km，HMP 关键课容量按低跑量保守缩放。"],
            },
            "selected_archetype": {
                "archetype_id": "short_build_after_marathon",
                "label": "C 型：备战期短且刚比完全马",
                "score": 6,
                "reasons": ["近期刚比完全马", "备战期不超过 8 周"],
            },
            "archetype_candidates": [],
            "phase_sequence": ["introductory", "race_supportive", "race_specific"],
            "preferred_workouts": [
                {
                    "id": "hm_95_long_fast_run",
                    "label": "半马专项耐力长距离快速跑",
                    "primary_zone": "specific_endurance_95",
                    "objective": "建立半马后程抗疲劳能力。",
                    "caution": "刚比完完全马时不应直接安排上限课表。",
                },
                {
                    "id": "hm_100_float_intervals",
                    "label": "半马核心专项巡航恢复间歇",
                    "primary_zone": "race_specific_100",
                    "objective": "提升目标配速代谢效率。",
                    "caution": "需要充分恢复。",
                },
            ],
        },
        "half_marathon_protocol_validation": validation
        or {
            "active": True,
            "passed": True,
            "errors": [],
            "warnings": [],
            "issues": [],
            "checked_constraints": ["marathon_recovery_intro", "quality_recovery_gap"],
        },
    }


def test_structured_report_exposes_half_marathon_protocol_panel_and_context():
    report = _build_structured_report(
        {
            "query": "生成半马计划",
            "category": "coach",
            "mode": "team",
            "audit_scores": {"consistency": 90, "safety": 92, "roi": 80},
            "structured_training_plan": _hmp_structured_plan(),
        },
        "已生成半马计划。",
    )

    panel = report["half_marathon_protocol_panel"]

    assert panel["active"] is True
    assert panel["panel_version"] == "hmp_v1"
    assert panel["status"] == "passed"
    assert panel["selected_archetype"]["archetype_id"] == "short_build_after_marathon"
    assert [item["id"] for item in panel["phase_sequence"]] == ["introductory", "race_supportive", "race_specific"]
    assert panel["preferred_workouts"][0]["id"] == "hm_95_long_fast_run"
    assert panel["glossary_terms"][0]["id"] == "hmp"
    assert panel["pace_calibration"]["target_hmp_pace"] == "4:16/km"
    assert panel["capacity_budget"]["quality_sessions_max"] == 1
    assert panel["profile_gaps"][0]["field"] == "current_10k_time"
    assert report["training_explanation_panel"]["protocol_context"]["status"] == "passed"


def test_half_marathon_protocol_panel_keeps_validation_issues():
    validation = {
        "active": True,
        "passed": False,
        "errors": ["第 1 周 周二 过早出现 100% HMP 核心专项巡航恢复课。"],
        "warnings": [],
        "issues": [
            {
                "severity": "error",
                "constraint_id": "race_specific_timing",
                "label": "100% HMP 核心课需靠近比赛专项期",
                "message": "第 1 周 周二 过早出现 100% HMP 核心专项巡航恢复课。",
                "recommendation": "100% HMP 核心课应主要放在比赛专项阶段。",
                "week_index": 1,
                "day": "周二",
                "workout_type": "hm_100_float_intervals",
            }
        ],
        "checked_constraints": ["race_specific_timing"],
    }
    report = _build_structured_report(
        {
            "query": "生成半马计划",
            "category": "coach",
            "mode": "team",
            "audit_scores": {"consistency": 90, "safety": 92, "roi": 80},
            "structured_training_plan": _hmp_structured_plan(validation=validation),
        },
        "已生成半马计划。",
    )

    panel = report["half_marathon_protocol_panel"]

    assert panel["status"] == "error"
    assert panel["validation_summary"]["error_count"] == 1
    assert panel["validation_summary"]["warning_count"] == 0
    assert panel["issues"][0]["constraint_id"] == "race_specific_timing"
    assert panel["issues"][0]["recommendation"] == "100% HMP 核心课应主要放在比赛专项阶段。"
    assert panel["source_docs"]


def test_half_marathon_protocol_panel_keeps_repair_log():
    validation = {
        "active": True,
        "passed": True,
        "errors": [],
        "warnings": [],
        "issues": [],
        "repair_applied": True,
        "repair_log": [
            {
                "constraint_id": "race_specific_timing",
                "severity": "error",
                "week_index": 1,
                "day": "周二",
                "action": "过早100% HMP核心课已替换为90% HMP支撑跑。",
            }
        ],
        "repair_suggestions": [],
        "checked_constraints": ["race_specific_timing"],
    }
    report = _build_structured_report(
        {
            "query": "生成半马计划",
            "category": "coach",
            "mode": "team",
            "structured_training_plan": _hmp_structured_plan(validation=validation),
        },
        "已生成半马计划。",
    )

    panel = report["half_marathon_protocol_panel"]

    assert panel["repair_applied"] is True
    assert panel["repair_log"][0]["constraint_id"] == "race_specific_timing"
    assert "90% HMP" in panel["repair_log"][0]["action"]


def test_non_half_marathon_report_omits_hmp_panel():
    report = _build_structured_report(
        {
            "query": "生成全马计划",
            "category": "coach",
            "mode": "team",
            "structured_training_plan": {
                "plan_meta": {"requested_weeks": 1, "actual_weeks": 1, "goal": "全马完赛"},
                "week_plans": [],
            },
        },
        "已生成全马计划。",
    )

    assert report["half_marathon_protocol_panel"] == {}
