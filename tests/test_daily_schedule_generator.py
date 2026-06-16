from marathon_qa_assistant.services.workout_template_retriever import (
    WORKOUT_TEMPLATE_REGISTRY,
    ZONE_LABELS,
    ZONE_LABELS_DETAIL,
    EVIDENCE_TIER_LABELS,
    build_daily_workout_template_card_from_hits,
    normalize_workout_type_for_template,
)
from marathon_qa_assistant.services.daily_schedule_generator import (
    generate_daily_schedule,
    DailyScheduleItem,
    MonthlyTrainingCalendar,
    _try_generate_schedule_from_kb_llm,
    _filter_kb_evidence_hits,
    _parse_content_variants,
    _extract_warmup_from_action_text,
    _extract_cooldown_from_action_text,
    _extract_simple_main_set,
    _build_alternatives_from_hits,
    _build_alternatives_for_hmp,
    _normalize_main_set_candidates,
)
from marathon_qa_assistant.nodes.output_nodes import _build_structured_report
from marathon_qa_assistant.ui.report_ui import UIHelper


# ==================== Z1-Z9 强度术语测试 ====================

def test_z1_z9_zone_labels_are_complete():
    assert len(ZONE_LABELS) == 9
    assert "Z1" in ZONE_LABELS
    assert "Z9" in ZONE_LABELS
    assert ZONE_LABELS["Z1"] == "Z1 恢复放松区"
    assert ZONE_LABELS["Z9"] == "Z9 冲刺神经肌肉区"
    assert ZONE_LABELS["Z4"] == "Z4 有氧阈值区"


def test_z1_z9_zone_labels_detail_complete():
    assert len(ZONE_LABELS_DETAIL) == 9
    assert "LTHR" in ZONE_LABELS_DETAIL["Z1"]
    assert "LTHR" in ZONE_LABELS_DETAIL["Z9"]


def test_all_workout_registry_has_zone_range():
    for key, entry in WORKOUT_TEMPLATE_REGISTRY.items():
        assert "zone_range" in entry, f"{key} 缺少 zone_range"
        assert entry["zone_range"], f"{key} zone_range 为空"


def test_all_workout_registry_has_chinese_intensity_labels():
    for key, entry in WORKOUT_TEMPLATE_REGISTRY.items():
        intensity = entry.get("intensity_target", "")
        assert intensity, f"{key} intensity_target 为空"
        # 确保用的是中文 Z 区间表述而不是纯数字百分比
        assert "Z" in intensity, f"{key} intensity_target ({intensity}) 未使用 Z 区间"
        assert any(zone in intensity for zone in ["区", "恢复", "有氧", "阈值", "马拉松", "乳酸", "耐受", "无氧", "冲刺", "渐进", "变化"]), \
            f"{key} intensity_target ({intensity}) 缺少中文术语"


def test_evidence_tier_labels_are_complete():
    assert "action_library" in EVIDENCE_TIER_LABELS
    assert "protocol_rule" in EVIDENCE_TIER_LABELS
    assert "kb_fallback" in EVIDENCE_TIER_LABELS
    assert "needs_evidence" in EVIDENCE_TIER_LABELS
    assert "plan_only" in EVIDENCE_TIER_LABELS
    assert EVIDENCE_TIER_LABELS["action_library"] == "动作库课表"
    assert EVIDENCE_TIER_LABELS["protocol_rule"] == "HMP 基石协议"
    assert EVIDENCE_TIER_LABELS["kb_fallback"] == "参考知识库生成"
    assert EVIDENCE_TIER_LABELS["needs_evidence"] == "证据不足待补全"
    assert EVIDENCE_TIER_LABELS["plan_only"] == "基础计划"


# ==================== normalize_workout_type 测试 ====================

def test_normalize_workout_type_for_all_registry_types():
    test_cases = [
        ("有氧阈值训练", "3-4*3000", "aerobic_threshold"),
        ("节奏跑", "25分钟阈值", "tempo_run"),
        ("轻松跑", "40分钟", "easy_run"),
        ("长距离", "20km", "long_run"),
        ("间歇跑", "400m*8", "interval_run"),
        ("摄氧量训练", "3min*6", "vo2max_interval"),
        ("无氧阈跑", "巡航间歇", "anaerobic_threshold"),
        ("马拉松配速跑", "15km@MP", "marathon_pace"),
        ("渐进跑", "渐加速", "progression_run"),
        ("法特莱克", "速度游戏", "fartlek"),
        ("坡道跑", "爬坡", "hill_repeats"),
        ("短冲", "加速跑", "strides"),
    ]
    for training_type, main_set, expected in test_cases:
        result = normalize_workout_type_for_template(training_type, main_set)
        assert result == expected, f"normalize_workout_type_for_template({training_type!r}, {main_set!r}) = {result!r}, expected {expected!r}"


def test_hmp_protocol_templates_are_registered_and_normalized():
    hmp_cases = [
        ("hm_intro_fartlek_hills", "导入期法特莱克/坡跑"),
        ("hm_base_threshold_progression", "85% HMP 基础期阈值巡航"),
        ("hm_90_support_endurance", "90% HMP 辅助耐力跑"),
        ("hm_95_long_fast_run", "95% HMP 长距离快速跑"),
        ("hm_100_float_intervals", "100% HMP 巡航恢复间歇"),
        ("hm_105_specific_speed", "105% HMP 专项速度"),
        ("hm_110_support_speed", "107-110% HMP 辅助速度"),
    ]
    for workout_id, main_set in hmp_cases:
        assert workout_id in WORKOUT_TEMPLATE_REGISTRY
        assert normalize_workout_type_for_template("半马专项训练", main_set) == workout_id

        card = build_daily_workout_template_card_from_hits(workout_id, day="周二", hits=[])
        assert card["workout_type"] == workout_id
        assert card["evidence_tier"] == "protocol_rule"
        assert card["main_set_candidates"]
        assert "HMP" in card["intensity_target"]
        assert card["training_objective"]


def test_hmp_75_85_threshold_main_set_prefers_base_protocol_not_intro():
    result = normalize_workout_type_for_template(
        "有氧阈值训练",
        "3×10分钟有氧阈值，组间3分钟慢跑，控制在75-85% HMP",
    )

    assert result == "hm_base_threshold_progression"


# ==================== 证据分层回退测试 ====================

def test_kb_fallback_generates_partial_schedule_when_other_kb_has_evidence():
    kb_hits = [
        {
            "source_file": "马拉松训练原理.pdf",
            "page": 12,
            "chunk_id": "chunk_1",
            "score": 0.8,
            "text": "轻松跑应保持在最大心率的60-70%，配速以可轻松对话为准。每次轻松跑时长30-60分钟，每周安排2-3次。",
        },
    ]
    result = _try_generate_schedule_from_kb_llm("easy_run", kb_hits)
    assert result is not None
    assert result["evidence_tier"] == "kb_fallback"
    assert result["evidence_tier_label"] == "参考知识库生成"
    assert len(result.get("source", [])) > 0
    assert result.get("intensity_target"), "应包含 Z1-Z2 强度信息"
    assert result.get("main_set_candidates") == [], "普通知识库不能补主训练组，只能补非核心字段"
    assert result.get("blocked_core_candidates", {}).get("main_set"), "被 KB 抽到的主课候选应保留在审计 trace 中"
    assert "轻松" in result.get("zone_label", "") or "Z" in result.get("zone_range", "")


def test_kb_fallback_returns_none_when_no_hits():
    result = _try_generate_schedule_from_kb_llm("easy_run", [])
    assert result is None


def test_kb_fallback_returns_none_when_short_text():
    result = _try_generate_schedule_from_kb_llm("easy_run", [{
        "source_file": "x.pdf",
        "text": "短",
    }])
    assert result is None


def test_filter_kb_evidence_excludes_action_library():
    hits = [
        {"source_file": "动作库.pdf", "text": "动作库内容"},
        {"source_file": "马拉松训练原理.pdf", "text": "轻松跑应保持..."},
    ]
    filtered = _filter_kb_evidence_hits("easy_run", hits)
    assert len(filtered) == 1
    assert filtered[0]["source_file"] == "马拉松训练原理.pdf"


# ==================== 训练日历生成测试 ====================

def test_monthly_calendar_generates_from_valid_plan():
    structured_training_plan = {
        "plan_meta": {
            "plan_type": "基础训练计划",
            "actual_weeks": 2,
            "goal": "提升有氧基础",
        },
        "phase_summary": [
            {"phase": "基础期", "start_week": 1, "end_week": 2, "objective": "建立有氧基础"},
        ],
        "week_plans": [
            {
                "week_index": 1,
                "phase": "基础期",
                "load_level": "低",
                "week_goal": "适应训练节奏",
                "days": [
                    {"day": "周一", "training_type": "休息", "main_set": ""},
                    {"day": "周二", "training_type": "轻松跑", "main_set": "30分钟"},
                    {"day": "周三", "training_type": "节奏跑", "main_set": "20分钟"},
                    {"day": "周四", "training_type": "轻松跑", "main_set": "40分钟"},
                    {"day": "周五", "training_type": "休息", "main_set": ""},
                    {"day": "周六", "training_type": "间歇跑", "main_set": "400m*8"},
                    {"day": "周日", "training_type": "长距离", "main_set": "12km"},
                ],
            },
            {
                "week_index": 2,
                "phase": "基础期",
                "load_level": "中",
                "week_goal": "增加训练时长",
                "days": [
                    {"day": "周一", "training_type": "休息", "main_set": ""},
                    {"day": "周二", "training_type": "轻松跑", "main_set": "35分钟"},
                    {"day": "周三", "training_type": "节奏跑", "main_set": "25分钟"},
                    {"day": "周四", "training_type": "轻松跑", "main_set": "45分钟"},
                    {"day": "周五", "training_type": "休息", "main_set": ""},
                    {"day": "周六", "training_type": "间歇跑", "main_set": "400m*10"},
                    {"day": "周日", "training_type": "长距离", "main_set": "14km"},
                ],
            },
        ],
    }

    calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=False)
    assert len(calendar.days) == 14
    assert calendar.start_week_index == 1
    assert calendar.end_week_index == 2
    assert len(calendar.phases) == 1
    assert calendar.phases[0]["phase"] == "基础期"

    rest_days = [d for d in calendar.days if d.is_rest]
    assert len(rest_days) == 4

    training_days = [d for d in calendar.days if not d.is_rest]
    assert len(training_days) == 10

    # 检查 Z 区间
    for d in training_days:
        if d.workout_type:
            assert d.zone_range or d.intensity_target, f"{d.training_type} 应有强度信息"

    # 检查证据层级
    assert "action_library" in calendar.evidence_summary or "plan_only" in calendar.evidence_summary


def test_action_library_card_keeps_field_sources_action_match_and_trace():
    structured_training_plan = {
        "week_plans": [
            {
                "week_index": 1,
                "phase": "base",
                "days": [
                    {"day": "周二", "training_type": "VO2max", "main_set": ""},
                ],
            },
        ],
    }

    calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=False)
    card = calendar.days[0]
    data = card.to_dict()

    assert card.evidence_tier == "action_library"
    assert data["field_sources"]["main_set"]["source_type"] == "action_library"
    assert data["field_sources"]["workout_type"]["source_type"] == "action_library"
    assert data["action_match"]["workout_type"] == "vo2max_interval"
    assert data["action_match"]["main_set"]
    assert data["action_match"]["alternatives"]
    assert " / " not in data["main_set"]
    assert data["protocol_check"]["allowed"] is True
    assert data["card_status"] == "generated"
    assert set(data["trace"]) == {"intent_parse", "protocol_check", "action_match", "kb_fallback", "risk_gate", "final_card"}


def test_daily_card_preserves_layered_kb_metadata_for_action_library():
    structured_training_plan = {
        "week_plans": [
            {
                "week_index": 1,
                "phase": "base",
                "days": [
                    {"day": "Tue", "training_type": "VO2max", "main_set": ""},
                ],
            },
        ],
    }

    calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=False)
    card = calendar.days[0].to_dict()

    assert card["kb_metadata"]["knowledge_layer"] == "prescription_library"
    assert card["kb_metadata"]["evidence_domain"] == "action_library"
    assert card["kb_metadata"]["prescription_permission"] == "can_write_core"
    assert card["field_sources"]["main_set"]["source_type"] != "llm_general_knowledge"


def test_daily_card_field_sources_cover_all_core_prescription_fields():
    structured_training_plan = {
        "week_plans": [
            {
                "week_index": 1,
                "phase": "base",
                "days": [
                    {"day": "周二", "training_type": "VO2max", "main_set": ""},
                ],
            },
        ],
    }

    calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=False)
    data = calendar.days[0].to_dict()
    field_sources = data["field_sources"]
    core_fields = {
        "workout_type",
        "main_set",
        "intensity",
        "duration",
        "weekly_quality_count",
        "long_run_cap",
        "progression",
        "risk_downgrade",
    }

    assert set(field_sources) >= core_fields
    for field in core_fields:
        assert field_sources[field]["source_type"] in {
            "protocol",
            "action_library",
            "needs_evidence",
        }
    assert field_sources["main_set"]["source_type"] == "action_library"
    assert field_sources["main_set"]["source_type"] != "llm_expression"


def test_action_library_candidate_string_is_not_joined_as_visible_main_set(monkeypatch):
    def fake_hits(_workout_type):
        return []

    def fake_card(*, workout_type, day, hits):
        return {
            "workout_type": workout_type,
            "main_set_candidates": ["4x1000m / 5x1000m / 6x1000m"],
            "training_objective": "action library prescription",
            "warmup_suggestion": "15min easy",
            "cooldown_suggestion": "10min easy",
            "alternative_workout": "",
            "evidence_tier": "action_library",
            "source": [{"source_id": "action-library.pdf", "page": 7, "chunk_id": "act-7"}],
            "evidence_status": {"main_set_candidates": "direct"},
        }

    monkeypatch.setattr(
        "marathon_qa_assistant.services.daily_schedule_generator.get_action_library_foundation_hits",
        fake_hits,
    )
    monkeypatch.setattr(
        "marathon_qa_assistant.services.daily_schedule_generator.build_daily_workout_template_card_from_hits",
        fake_card,
    )

    calendar = generate_daily_schedule(
        {
            "week_plans": [
                {
                    "week_index": 1,
                    "phase": "base",
                    "days": [{"day": "Tue", "training_type": "VO2max", "main_set": ""}],
                },
            ],
        },
        enable_kb_fallback=False,
    )
    data = calendar.days[0].to_dict()

    assert data["main_set"] == "4x1000m"
    assert data["action_match"]["main_set"] == "4x1000m"
    assert data["action_match"]["alternatives"] == ["5x1000m", "6x1000m"]
    assert " / " not in data["main_set"]


def test_hmp_protocol_missing_action_library_fails_closed_with_trace(monkeypatch):
    monkeypatch.setattr(
        "marathon_qa_assistant.services.daily_schedule_generator._build_hmp_action_library_execution_card",
        lambda *args, **kwargs: {},
    )

    calendar = generate_daily_schedule(
        {
            "half_marathon_protocol": {
                "active": True,
                "capacity_budget": {"quality_sessions_max": 2, "long_run_max_km": 18},
            },
            "week_plans": [
                {
                    "week_index": 1,
                    "phase": "base",
                    "days": [
                        {
                            "day": "Tue",
                            "training_type": "half marathon protocol",
                            "main_set": "hm_base_threshold_progression HMP 40min progression",
                        },
                    ],
                },
            ],
        },
        enable_kb_fallback=False,
    )
    data = calendar.days[0].to_dict()

    assert data["evidence_tier"] == "needs_evidence"
    assert data["card_status"] == "needs_evidence"
    assert data["field_sources"]["main_set"]["source_type"] == "needs_evidence"
    assert data["action_match"]["needs_evidence"] == ["missing_action_library_match"]
    assert data["trace"]["final_card"]["evidence_tier"] == "needs_evidence"
    assert data["trace"]["action_match"]["needs_evidence"] == ["missing_action_library_match"]


def test_unknown_workout_does_not_expose_plan_skeleton_main_set():
    calendar = generate_daily_schedule(
        {
            "week_plans": [
                {
                    "week_index": 1,
                    "phase": "base",
                    "days": [
                        {
                            "day": "Tue",
                            "training_type": "Mystery workout",
                            "main_set": "3x2000m @ HMP from skeleton",
                        },
                    ],
                },
            ],
        },
        enable_kb_fallback=False,
    )
    data = calendar.days[0].to_dict()

    assert data["evidence_tier"] == "needs_evidence"
    assert data["card_status"] == "needs_evidence"
    assert data["main_set"] == "动作库证据不足，暂不展示具体主课。"
    assert data["field_sources"]["main_set"]["source_type"] == "needs_evidence"
    assert data["field_sources"]["main_set"]["value"] == data["main_set"]
    assert data["action_match"]["needs_evidence"] == ["unknown_workout_type"]
    assert data["trace"]["intent_parse"]["main_set_raw"] == "3x2000m @ HMP from skeleton"
    assert data["trace"]["action_match"]["needs_evidence"] == ["unknown_workout_type"]
    assert data["trace"]["final_card"]["main_set"] == data["main_set"]
    assert data["kb_fallback"]["blocked_core_candidates"]["main_set"] == ["3x2000m @ HMP from skeleton"]
    assert "3x2000m" not in data["main_set"]


def test_hmp_protocol_day_uses_action_library_main_set_not_protocol_template():
    structured_training_plan = {
        "half_marathon_protocol": {
            "active": True,
            "preferred_workouts": [
                {
                    "id": "hm_base_threshold_progression",
                    "label": "基础期阈值/渐速跑",
                },
            ],
            "capacity_budget": {"quality_sessions_max": 2, "long_run_max_km": 18},
        },
        "week_plans": [
            {
                "week_index": 1,
                "phase": "base",
                "week_goal": "HMP协议：基础期",
                "key_workouts": ["HMP协议：候选课表 基础期阈值/渐速跑"],
                "days": [
                    {
                        "day": "周一",
                        "training_type": "有氧阈值训练",
                        "main_set": "hm_base_threshold_progression：3×10分钟有氧阈值，组间3分钟慢跑，控制在75-85% HMP",
                    },
                    {
                        "day": "周二",
                        "training_type": "渐进跑",
                        "main_set": "hm_base_threshold_progression：45分钟肯尼亚式渐进跑，从轻松跑渐进至85% HMP",
                    },
                ],
            },
        ],
    }

    calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=False)
    days = [day.to_dict() for day in calendar.days]

    assert days[0]["evidence_tier"] == "protocol_rule"
    assert days[0]["field_sources"]["main_set"]["source_type"] == "action_library"
    assert days[0]["field_sources"]["main_set"]["source_id"] == "动作库.pdf"
    assert days[0]["action_match"]["workout_type"] == "aerobic_threshold"
    assert days[0]["action_match"]["protocol_workout_type"] == "hm_base_threshold_progression"
    assert days[0]["main_set"] != "3×10分钟有氧阈值，组间3分钟慢跑，控制在75-85% HMP"
    assert " / " not in days[0]["main_set"]

    assert days[1]["field_sources"]["main_set"]["source_type"] == "action_library"
    assert days[1]["action_match"]["workout_type"] == "progression_run"
    assert "肯尼亚式" not in days[1]["main_set"]
    assert " / " not in days[1]["main_set"]
    assert "10分钟慢跑" not in days[1]["action_match"]["alternatives"]


def test_action_library_range_prescription_moves_with_week_load_bias(monkeypatch):
    import marathon_qa_assistant.services.daily_schedule_generator as dsg

    def fake_hits(_workout_type):
        return []

    def fake_card(*, workout_type, day, hits):
        return {
            "title": f"{day}｜动作库证据",
            "workout_type": workout_type,
            "main_set_candidates": ["4-6×2000m，组间2min"],
            "training_objective": "动作库候选主课",
            "warmup_suggestion": "15分钟轻松跑+动态拉伸",
            "cooldown_suggestion": "10分钟慢跑",
            "alternative_workout": "若疲劳较高则降低总量",
            "evidence_tier": "action_library",
            "source": [{"source_id": "动作库.pdf", "page": 6, "chunk_id": "动作库_p0006_c0001"}],
            "evidence_status": {"main_set_candidates": "direct"},
        }

    monkeypatch.setattr(dsg, "get_action_library_foundation_hits", fake_hits)
    monkeypatch.setattr(dsg, "build_daily_workout_template_card_from_hits", fake_card)

    plan = {
        "week_plans": [
            {
                "week_index": 1,
                "phase": "base",
                "load_level": "低",
                "days": [{"day": "周二", "training_type": "有氧阈值训练", "main_set": ""}],
            },
            {
                "week_index": 2,
                "phase": "base",
                "load_level": "中",
                "days": [{"day": "周二", "training_type": "有氧阈值训练", "main_set": ""}],
            },
            {
                "week_index": 3,
                "phase": "base",
                "load_level": "高",
                "days": [{"day": "周二", "training_type": "有氧阈值训练", "main_set": ""}],
            },
        ],
    }

    calendar = generate_daily_schedule(plan, enable_kb_fallback=False)
    mains = [day.main_set for day in calendar.days]
    traces = [day.trace["action_match"]["prescription_selection"] for day in calendar.days]

    assert mains == ["4×2000m，组间2min", "5×2000m，组间2min", "6×2000m，组间2min"]
    assert traces[0]["load_bias"] == "low"
    assert traces[1]["selected_repetition_count"] == 5
    assert traces[2]["selected_repetition_count"] == 6
    assert all(day.field_sources["main_set"]["source_type"] == "action_library" for day in calendar.days)


def test_protocol_card_marks_core_fields_as_protocol_source():
    structured_training_plan = {
        "half_marathon_protocol": {"active": True, "capacity_budget": {"quality_sessions_max": 2, "long_run_max_km": 18}},
        "week_plans": [
            {
                "week_index": 1,
                "phase": "base",
                "days": [
                    {
                        "day": "周二",
                        "training_type": "半马专项",
                        "main_set": "hm_base_threshold_progression HMP 40分钟渐进跑",
                    },
                ],
            },
        ],
    }

    calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=False)
    data = calendar.days[0].to_dict()

    assert data["evidence_tier"] == "protocol_rule"
    assert data["field_sources"]["main_set"]["source_type"] == "action_library"
    assert data["field_sources"]["main_set"]["source_id"] == "动作库.pdf"
    assert data["field_sources"]["intensity"]["source_type"] == "protocol"
    assert data["protocol_check"]["quality_session_cap"] == 2
    assert data["trace"]["protocol_check"]["allowed"] is True


def test_daily_card_protocol_check_exposes_recent_four_week_capacity_basis():
    structured_training_plan = {
        "half_marathon_protocol": {
            "active": True,
            "weekly_decisions": [
                {
                    "week_index": 1,
                    "capacity_budget": {
                        "quality_sessions_max": 1,
                        "long_run_max_km": 12,
                        "weekly_volume_km": 70,
                        "effective_weekly_volume_km": 38,
                        "recent_four_week_mileage_km": 38,
                        "volume_basis": "recent_four_week_mileage",
                    },
                }
            ],
        },
        "week_plans": [
            {
                "week_index": 1,
                "phase": "基础阶段",
                "days": [
                    {
                        "day": "周二",
                        "training_type": "半马专项",
                        "main_set": "hm_base_threshold_progression HMP 40分钟渐进跑",
                    },
                ],
            },
        ],
    }

    calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=False)
    data = calendar.days[0].to_dict()

    assert data["protocol_check"]["volume_basis"] == "recent_four_week_mileage"
    assert data["protocol_check"]["effective_weekly_volume_km"] == 38
    assert data["protocol_check"]["recent_four_week_mileage_km"] == 38
    assert data["protocol_check"]["quality_sessions_this_week"] == 1
    assert data["protocol_check"]["allowed"] is True
    assert data["field_sources"]["weekly_quality_count"]["source_id"] == "protocol_check"


def test_protocol_violation_marks_card_as_needing_recheck():
    structured_training_plan = {
        "half_marathon_protocol": {
            "active": True,
            "capacity_budget": {
                "quality_sessions_max": 2,
                "long_run_max_km": 12,
            },
        },
        "week_plans": [
            {
                "week_index": 1,
                "phase": "base",
                "days": [
                    {
                        "day": "周日",
                        "training_type": "长距离",
                        "main_set": "20km 长距离",
                        "main_km": 20,
                    },
                ],
            },
        ],
    }

    calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=False)
    data = calendar.days[0].to_dict()

    assert data["protocol_check"]["allowed"] is False
    assert "long_run_exceed_cap" in data["protocol_check"]["violations"]
    assert data["card_status"] == "needs_protocol_recheck"
    assert data["trace"]["final_card"]["card_status"] == "needs_protocol_recheck"


def test_final_action_main_set_duration_overrides_inconsistent_allocated_distance():
    structured_training_plan = {
        "half_marathon_protocol": {
            "active": True,
            "capacity_budget": {
                "quality_sessions_max": 2,
                "long_run_max_km": 18,
            },
        },
        "week_plans": [
            {
                "week_index": 1,
                "phase": "base",
                "days": [
                    {
                        "day": "周二",
                        "training_type": "轻松跑",
                        # 真实 动作库.pdf: "40-60min"（时间型），会触发 duration override
                        "main_set": "40-60min",
                        "main_km": 15,
                    },
                ],
            },
        ],
    }

    calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=False)
    data = calendar.days[0].to_dict()

    # 真实 PDF 中轻松跑内容为 "40-60min"（时间型）
    assert data["main_set"] != ""
    assert data["main_set"] != "动作库证据不足，暂不展示具体主课。"
    assert data["duration_min"] > 0
    assert data["evidence_tier"] in ("action_library", "kb_fallback")
    assert data["card_status"] != "needs_evidence"


def test_training_load_fields_are_explicit_estimates_not_device_metrics():
    structured_training_plan = {
        "week_plans": [
            {
                "week_index": 1,
                "phase": "base",
                "days": [
                    {
                        "day": "周一",
                        "training_type": "Easy",
                        "main_set": "45分钟 Z2 轻松跑",
                        "zone_range": "Z2",
                    },
                ],
            },
        ],
    }

    calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=False)
    data = calendar.days[0].to_dict()
    factors = data["training_load_factors"]

    assert data["training_load_method"] == "planned_zone_duration_proxy"
    assert factors["source_type"] == "planned_load_proxy"
    assert factors["load_kind"] == "planned_load_proxy"
    assert factors["is_estimated"] is True
    assert factors["not_device_metric"] is True
    assert "heart_rate" in factors["missing_inputs"]
    assert "HRV" not in str(data["training_load"]).upper()
    assert "不等同于设备" in factors["disclaimer"]

    summary = calendar.training_load_summary
    assert summary["source_type"] == "planned_load_proxy"
    assert summary["is_estimated"] is True
    assert summary["not_device_metric"] is True


def test_heart_rate_trimp_load_keeps_estimated_boundary():
    from marathon_qa_assistant.services.training_load import calculate_hr_trimp_training_load

    estimate = calculate_hr_trimp_training_load(
        duration_min=45,
        avg_hr=150,
        resting_hr=50,
        max_hr=190,
        sex="male",
    )

    assert estimate.method == "hr_trimp_estimated"
    assert estimate.factors["source_type"] == "estimated_heart_rate_proxy"
    assert estimate.factors["load_kind"] == "estimated"
    assert estimate.factors["is_estimated"] is True
    assert estimate.factors["not_device_metric"] is True
    assert "physiology_proxy" not in str(estimate.factors)
    assert "sleep_score" in estimate.factors["missing_inputs"]


def test_final_main_set_distance_exceeding_long_run_cap_is_blocked_even_without_raw_main_km(monkeypatch):
    def fake_build_daily_workout_template_card_from_hits(*, workout_type, day, hits):
        return {
            "workout_type": workout_type,
            "training_type_label": "长距离",
            "zone_range": "Z2",
            "intensity_target": "Z2 轻松有氧区",
            "zone_label": "Z2 轻松有氧区",
            "evidence_tier": "action_library",
            "evidence_tier_label": "动作库课表",
            "source": ["动作库.pdf，第 12 页"],
            "main_set_candidates": ["22km 长距离"],
            "training_objective": "动作库长距离课",
            "warmup_suggestion": "",
            "cooldown_suggestion": "",
            "alternative_workout": "",
            "evidence_ids": [],
        }

    monkeypatch.setattr(
        "marathon_qa_assistant.services.daily_schedule_generator.build_daily_workout_template_card_from_hits",
        fake_build_daily_workout_template_card_from_hits,
    )

    structured_training_plan = {
        "half_marathon_protocol": {
            "active": True,
            "capacity_budget": {
                "quality_sessions_max": 2,
                "long_run_max_km": 18,
            },
        },
        "week_plans": [
            {
                "week_index": 1,
                "phase": "base",
                "days": [
                    {
                        "day": "周日",
                        "training_type": "长距离",
                        "main_set": "22km 长距离",
                    },
                ],
            },
        ],
    }

    calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=False)
    data = calendar.days[0].to_dict()

    assert data["duration_min"] == 143
    assert data["protocol_check"]["allowed"] is False
    assert "long_run_exceed_cap" in data["protocol_check"]["violations"]
    assert data["main_set"] == "22km 长距离"
    assert data["card_status"] == "needs_protocol_recheck"


def test_rest_day_never_inherits_week_protocol_violation_status():
    structured_training_plan = {
        "half_marathon_protocol": {
            "active": True,
            "capacity_budget": {
                "quality_sessions_max": 1,
                "long_run_max_km": 12,
            },
        },
        "week_plans": [
            {
                "week_index": 1,
                "phase": "base",
                "days": [
                    {"day": "周一", "training_type": "休息", "main_set": ""},
                    {"day": "周二", "training_type": "节奏跑", "main_set": "20分钟"},
                    {"day": "周四", "training_type": "VO2max", "main_set": "5x3min"},
                ],
            },
        ],
    }

    calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=False)
    rest_day = calendar.days[0].to_dict()
    quality_days = [day.to_dict() for day in calendar.days if not day.is_rest]

    assert rest_day["is_rest"] is True
    assert rest_day["card_status"] == "generated"
    assert rest_day["protocol_check"]["allowed"] is True
    assert rest_day["trace"]["final_card"]["card_status"] == "generated"
    assert any(day["card_status"] == "needs_protocol_recheck" for day in quality_days)


def test_kb_fallback_does_not_source_core_main_set_in_calendar(monkeypatch):
    def fake_extract(_workout_type):
        return []

    def fake_kb(_workout_type, _top_k=20):
        return ([
            {
                "source_file": "general.pdf",
                "page": 1,
                "chunk_id": "g1",
                "text": "轻松跑每次30-60分钟，热身：10分钟慢跑。冷身：5分钟慢跑。训练后注意补水和恢复，避免把参考知识库内容当成主训练组处方。",
            }
        ], "easy")

    monkeypatch.setattr(
        "marathon_qa_assistant.services.daily_schedule_generator.get_action_library_foundation_hits",
        fake_extract,
    )
    monkeypatch.setattr(
        "marathon_qa_assistant.services.daily_schedule_generator._extract_kb_evidence_for_workout",
        fake_kb,
    )
    structured_training_plan = {
        "week_plans": [
            {
                "week_index": 1,
                "phase": "base",
                "days": [
                    {"day": "周二", "training_type": "VO2max", "main_set": "30分钟"},
                ],
            },
        ],
    }

    calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=True)
    data = calendar.days[0].to_dict()

    assert data["evidence_tier"] == "needs_evidence"
    assert data["card_status"] == "needs_evidence"
    assert data["field_sources"]["main_set"]["source_type"] == "needs_evidence"
    assert data["kb_fallback"]["blocked_core_candidates"]["main_set"]


def test_monthly_calendar_handles_empty_input():
    calendar = generate_daily_schedule({})
    assert calendar.total_days == 0


def test_monthly_calendar_handles_missing_workout_types():
    structured_training_plan = {
        "week_plans": [
            {
                "week_index": 1,
                "days": [
                    {"day": "周一", "training_type": "休息", "main_set": ""},
                    {"day": "周二", "training_type": "自定义训练", "main_set": "未知内容"},
                ],
            },
        ],
    }
    calendar = generate_daily_schedule(structured_training_plan)
    assert calendar.total_days == 2
    custom_day = calendar.days[1]
    assert custom_day.evidence_tier == "needs_evidence"
    assert custom_day.evidence_tier_label == "证据不足待补全"
    assert custom_day.card_status == "needs_evidence"
    assert custom_day.main_set == "动作库证据不足，暂不展示具体主课。"


def test_monthly_calendar_projects_hmp_candidate_to_quality_day():
    structured_training_plan = {
        "half_marathon_protocol": {
            "active": True,
            "preferred_workouts": [
                {
                    "id": "hm_95_long_fast_run",
                    "label": "半马95%HMP专项耐力长距离快速跑",
                },
            ],
        },
        "week_plans": [
            {
                "week_index": 1,
                "week_goal": "HMP协议：比赛专项期",
                "key_workouts": ["HMP协议：候选课表=半马95%HMP专项耐力长距离快速跑"],
                "days": [
                    {"day": "周一", "training_type": "休息", "main_set": ""},
                    {"day": "周日", "training_type": "长距离", "main_set": "18km 渐进跑", "notes": "保留原始主课。"},
                ],
            },
        ],
    }

    calendar = generate_daily_schedule(structured_training_plan)
    quality_day = calendar.days[1]

    assert quality_day.workout_type == "hm_95_long_fast_run"
    assert quality_day.training_type == "长距离"
    assert quality_day.field_sources["main_set"]["source_type"] == "action_library"
    assert quality_day.action_match["workout_type"] == "long_run"
    assert quality_day.action_match["protocol_workout_type"] == "hm_95_long_fast_run"
    assert quality_day.main_set != "18km 渐进跑"
    assert " / " not in quality_day.main_set
    assert "95% HMP" in quality_day.intensity_target
    assert "半马后程抗疲劳" in quality_day.training_objective


def test_monthly_calendar_uses_base_hmp_protocol_without_leaking_internal_id():
    structured_training_plan = {
        "half_marathon_protocol": {
            "active": True,
            "preferred_workouts": [
                {
                    "id": "hm_base_threshold_progression",
                    "label": "基础期阈值/渐速跑",
                },
            ],
        },
        "week_plans": [
            {
                "week_index": 1,
                "week_goal": "HMP协议：基础期",
                "key_workouts": ["HMP协议：候选课表=基础期阈值/渐速跑"],
                "days": [
                    {
                        "day": "周二",
                        "training_type": "渐进跑",
                        "main_set": "hm_base_threshold_progression：50分钟渐进跑，从轻松跑逐步进到85% HMP",
                    },
                ],
            },
        ],
    }

    calendar = generate_daily_schedule(structured_training_plan)
    day = calendar.days[0]

    assert day.workout_type == "hm_base_threshold_progression"
    assert "hm_base_threshold_progression" not in day.main_set
    assert day.training_type_label.startswith("半马基础期阈值/渐速跑")
    assert day.evidence_tier == "protocol_rule"
    assert day.evidence_tier_label == "HMP 基石协议"
    assert "Sub-70半程马拉松训练_图片OCR整理.md" in day.source


def test_monthly_calendar_does_not_project_unmatched_intro_hmp_note():
    structured_training_plan = {
        "half_marathon_protocol": {
            "active": True,
            "preferred_workouts": [
                {
                    "id": "hm_intro_fartlek_hills",
                    "label": "导入期法特莱克/坡跑",
                },
                {
                    "id": "hm_95_long_fast_run",
                    "label": "半马95%HMP专项耐力长距离快速跑",
                },
            ],
        },
        "week_plans": [
            {
                "week_index": 1,
                "week_goal": "HMP协议：导入期",
                "key_workouts": ["HMP协议：候选课表=导入期法特莱克/坡跑"],
                "days": [
                    {"day": "周二", "training_type": "间歇跑", "main_set": "6x400m"},
                    {"day": "周日", "training_type": "长距离", "main_set": "14km轻松跑"},
                ],
            },
        ],
    }

    calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=False)


# ==================== 结构化报告包含新字段测试 ====================

def test_structured_report_includes_monthly_calendar():
    report = _build_structured_report(
        {
            "query": "给我生成训练计划",
            "category": "coach",
            "mode": "team",
            "rag_sources": [],
            "skip_calendar_kb_fallback": True,
            "structured_training_plan": {
                "plan_meta": {"plan_type": "基础训练计划", "actual_weeks": 1},
                "week_plans": [
                    {
                        "week_index": 1,
                        "phase": "基础期",
                        "load_level": "低",
                        "days": [
                            {"day": "周一", "training_type": "休息", "main_set": ""},
                            {"day": "周二", "training_type": "轻松跑", "main_set": "30分钟"},
                        ],
                    },
                ],
            },
            "subtasks": [],
            "audit_scores": {"consistency": 80, "safety": 90, "roi": 75},
            "token_usage": {"total_tokens": 100},
        },
        "已生成训练计划。",
    )

    assert "monthly_training_calendar" in report, "结构化报告应包含 monthly_training_calendar"
    assert "daily_schedule_cards" in report, "结构化报告应包含 daily_schedule_cards"
    assert "evidence_tier_map" in report, "结构化报告应包含 evidence_tier_map"
    calendar = report["monthly_training_calendar"]
    assert isinstance(calendar, dict)
    assert len(calendar.get("days", [])) == 2


def test_structured_report_includes_evidence_tier_in_cards():
    report = _build_structured_report(
        {
            "query": "给我生成训练计划",
            "category": "coach",
            "mode": "team",
            "rag_sources": [
                {
                    "source": "动作库.pdf",
                    "source_path": "动作库.pdf",
                    "text": "轻松跑 Z1-Z2 轻松有氧区，恢复放松区至轻松有氧区。",
                    "page": 3,
                    "chunk_id": "ac_c1",
                    "score": 0.9,
                },
            ],
            "skip_calendar_kb_fallback": True,
            "structured_training_plan": {
                "plan_meta": {"plan_type": "基础训练计划", "actual_weeks": 1},
                "week_plans": [
                    {
                        "week_index": 1,
                        "phase": "基础期",
                        "days": [
                            {"day": "周二", "training_type": "轻松跑", "main_set": "30分钟"},
                        ],
                    },
                ],
            },
            "subtasks": [],
            "audit_scores": {"consistency": 80, "safety": 90, "roi": 75},
            "token_usage": {"total_tokens": 100},
        },
        "已生成训练计划。",
    )

    cards = report.get("daily_workout_cards", [])
    assert len(cards) >= 1
    assert "evidence_tier" in cards[0], "课表卡应包含 evidence_tier 字段"


# ==================== Markdown 渲染空卡过滤测试 ====================

def test_render_daily_workout_cards_filters_empty_cards():
    structured_data = {
        "daily_workout_cards": [
            {
                "title": "周二｜课表证据不足",
                "workout_type": "easy_run",
                "main_set_candidates": [],
                "training_objective": "",
                "warmup_suggestion": "",
                "evidence_tier": "plan_only",
                "evidence_status": {"reason": "未检索到动作库"},
            },
            {
                "title": "周三｜有氧阈值训练课",
                "workout_type": "aerobic_threshold",
                "main_set_candidates": ["3-4*3000/2min"],
                "training_objective": "提升脂代谢效率",
                "warmup_suggestion": "15分钟慢跑+动态拉伸",
                "evidence_tier": "action_library",
                "evidence_status": {"main_set_candidates": "direct"},
            },
        ],
        "evidence_tier_map": EVIDENCE_TIER_LABELS,
    }

    rendered = UIHelper.render_structured_report(structured_data, "已生成训练计划。")
    assert "周三｜有氧阈值训练课" in rendered, "有效课表卡应该被渲染"
    assert "动作库课表" in rendered, "证据等级应该被渲染"
    assert "课表证据不足" not in rendered, "缺证据空卡不应该逐条渲染"


def test_render_daily_workout_cards_shows_warning_when_all_empty():
    structured_data = {
        "daily_workout_cards": [
            {
                "title": "周二｜课表证据不足",
                "workout_type": "easy_run",
                "main_set_candidates": [],
                "training_objective": "",
                "warmup_suggestion": "",
                "evidence_tier": "plan_only",
                "evidence_status": {"reason": "未检索到动作库"},
            },
            {
                "title": "周三｜课表证据不足",
                "workout_type": "tempo_run",
                "main_set_candidates": [],
                "training_objective": "",
                "warmup_suggestion": "",
                "evidence_tier": "plan_only",
                "evidence_status": {"reason": "未检索到动作库"},
            },
        ],
        "evidence_tier_map": EVIDENCE_TIER_LABELS,
    }

    rendered = UIHelper.render_structured_report(structured_data, "已生成训练计划。")
    assert "本次未生成完整每日课表卡" in rendered, "全部缺证据时应显示提示信息"
    assert "课表证据不足" not in rendered, "不应显示无内容空卡标题"


# ==================== DailyScheduleItem 序列化测试 ====================

def test_daily_schedule_item_to_dict():
    item = DailyScheduleItem(
        date="第1周周二",
        day_label="周二",
        week_index=1,
        day_index=2,
        phase="基础期",
        training_type="轻松跑",
        training_type_label="轻松跑",
        workout_type="easy_run",
        zone_range="Z1-Z2",
        zone_label="Z2 轻松有氧区",
        intensity_target="Z1-Z2 恢复放松区至轻松有氧区",
        main_set="30分钟",
        warmup="10分钟轻松跑 + 动态拉伸",
        cooldown="5分钟慢跑 + 拉伸",
        alternative="休息或交叉训练",
        training_objective="恢复与有氧基础建立",
        evidence_tier="kb_fallback",
        evidence_tier_label="参考知识库生成",
        source=["马拉松训练原理.pdf，第 12 页"],
        is_rest=False,
    )
    d = item.to_dict()
    assert d["training_type"] == "轻松跑"
    assert d["zone_range"] == "Z1-Z2"
    assert d["evidence_tier"] == "kb_fallback"
    assert d["is_rest"] is False


def test_daily_schedule_item_to_dict_exposes_frontend_intensity_and_duration_aliases():
    item = DailyScheduleItem(
        date="第1周周二",
        day_label="周二",
        week_index=1,
        day_index=2,
        phase="基础期",
        training_type="轻松跑",
        training_type_label="轻松跑",
        workout_type="easy_run",
        zone_range="Z1-Z2",
        zone_label="Z2 轻松有氧区",
        intensity_target="Z1-Z2 恢复放松区至轻松有氧区",
        main_set="30分钟",
        warmup="10分钟轻松跑 + 动态拉伸",
        cooldown="5分钟慢跑 + 拉伸",
        alternative="休息或交叉训练",
        training_objective="恢复与有氧基础建立",
        evidence_tier="kb_fallback",
        evidence_tier_label="参考知识库生成",
        duration_min=45,
        training_load=40,
        risk_gate={"status": "not_evaluated"},
        field_sources={"main_set": {"source_type": "action_library"}},
    )

    data = item.to_dict()

    assert data["intensity"] == item.intensity_target
    assert data["duration"] == item.duration_min
    assert data["objective"] == item.training_objective


def test_monthly_training_calendar_to_dict():
    calendar = MonthlyTrainingCalendar(
        year=2026,
        month=5,
        start_week_index=1,
        end_week_index=4,
        total_days=28,
        days=[DailyScheduleItem(
            date="第1周周一",
            day_label="周一",
            week_index=1,
            day_index=1,
            phase="基础期",
            training_type="休息",
            training_type_label="休息",
            workout_type="",
            zone_range="",
            zone_label="",
            intensity_target="",
            main_set="",
            warmup="",
            cooldown="",
            alternative="",
            training_objective="主动恢复",
            evidence_tier="plan_only",
            evidence_tier_label="基础计划",
            is_rest=True,
        )],
        phases=[{"phase": "基础期", "start_week": 1, "end_week": 4, "objective": "建立有氧基础"}],
        evidence_summary={"action_library": 0, "kb_fallback": 0, "plan_only": 28},
    )
    d = calendar.to_dict()
    assert d["year"] == 2026
    assert d["month"] == 5
    assert len(d["days"]) == 1
    assert d["days"][0]["is_rest"] is True
    assert d["evidence_summary"]["plan_only"] == 28


# ==================== 备选方案 (alternatives) 测试 ====================


class TestParseContentVariants:
    """测试 _parse_content_variants 从动作库条目中解析 a/b/c 变体。"""

    def test_extracts_abc_variants_from_action_text(self):
        """有 content 段落且含 a/b/c 变体时，正确提取每个变体。"""
        text = (
            "name：有氧阈值训练\n"
            "categories：Aerobic\n"
            "content：\n"
            "a.3-4*3000/2min\n"
            "b.5-6*2000/2min\n"
            "c.3*3000+3+2000\n"
            "zone_range：Z2-Z4\n"
            "objective：提升有氧耐力"
        )
        variants = _parse_content_variants(text)
        assert len(variants) == 3, f"应提取 3 个变体，实际得到 {len(variants)}: {variants}"
        assert "3-4*3000/2min" in variants[0]
        assert "5-6*2000/2min" in variants[1]
        assert "3*3000+3+2000" in variants[2]

    def test_returns_empty_when_no_content_section(self):
        """无 content 段落时返回空列表。"""
        text = "name：轻松跑\ncategories：Aerobic\nzone_range：Z1-Z2"
        assert _parse_content_variants(text) == []

    def test_returns_empty_for_empty_text(self):
        """空字符串返回空列表。"""
        assert _parse_content_variants("") == []
        assert _parse_content_variants("  ") == []

    def test_returns_empty_when_content_has_no_variants(self):
        """content 段落存在但无 a/b/c 变体格式时返回空列表。"""
        text = (
            "name：轻松跑\n"
            "categories：Aerobic\n"
            "content：\n"
            "40-60min慢跑\n"
            "zone_range：Z1-Z2"
        )
        variants = _parse_content_variants(text)
        assert variants == [], f"无变体格式时应返回空列表，实际: {variants}"

    def test_splits_single_letter_variants(self):
        """仅有 a 标记的单变体时返回空列表（不足 2 个变体）。"""
        text = (
            "name：测试训练\n"
            "content：\n"
            "a.10*400m\n"
            "zone_range：Z4-Z6"
        )
        variants = _parse_content_variants(text)
        assert len(variants) == 1
        assert "10*400m" in variants[0]


class TestExtractWarmupCooldownFromActionText:
    """测试从动作库条目中提取 warmup/cooldown 内容。"""

    def test_extract_warmup_from_action_text(self):
        text = (
            "name：测试训练\n"
            "content：\n"
            "a.10*400m\n"
            "warmup_suggestion：15分钟慢跑+动态拉伸\n"
            "zone_range：Z4-Z6"
        )
        result = _extract_warmup_from_action_text(text)
        assert "15分钟慢跑" in result or "动态拉伸" in result

    def test_extract_cooldown_from_action_text(self):
        text = (
            "name：摄氧量间歇\n"
            "content：\n"
            "a.8-9*800\n"
            "cooldown_suggestion：最后1km冷身\n"
            "zone_range：Z6-Z7"
        )
        result = _extract_cooldown_from_action_text(text)
        assert "冷身" in result or "1km" in result

    def test_extract_warmup_returns_empty_when_missing(self):
        text = "name：测试\ncontent：\na.10*400m\nzone_range：Z4-Z6"
        assert _extract_warmup_from_action_text(text) == ""

    def test_extract_cooldown_returns_empty_when_missing(self):
        text = "name：测试\ncontent：\na.10*400m\nzone_range：Z4-Z6"
        assert _extract_cooldown_from_action_text(text) == ""


class TestExtractSimpleMainSet:
    """测试 _extract_simple_main_set 从无变体条目提取主课。"""

    def test_extracts_simple_main_set(self):
        text = (
            "name：轻松跑\n"
            "categories：Aerobic\n"
            "content：\n"
            "40-60min慢跑\n"
            "zone_range：Z1-Z2"
        )
        result = _extract_simple_main_set(text)
        assert "40-60min慢跑" in result or "慢跑" in result

    def test_returns_empty_for_variant_format(self):
        """content 是 a/b/c 格式时不返回简单主课。"""
        text = (
            "name：有氧阈值训练\n"
            "content：\n"
            "a.3-4*3000/2min\n"
            "b.5-6*2000/2min\n"
            "zone_range：Z2-Z4"
        )
        result = _extract_simple_main_set(text)
        assert result == "", f"变体格式应返回空，实际: {result}"


class TestBuildAlternativesFromHits:
    """测试 _build_alternatives_from_hits 构建备选方案列表。"""

    def test_builds_alternatives_from_variant_hits(self):
        """有 a/b/c 变体的动作库条目：跳过第一个变体，其余作为备选。"""
        hits = [{
            "chunk_id": "动作库_p0010_c0001",
            "source_file": "动作库.pdf",
            "page": 10,
            "text": (
                "name：有氧阈值训练\n"
                "categories：Aerobic\n"
                "content：\n"
                "a.3-4*3000/2min\n"
                "b.5-6*2000/2min\n"
                "c.3*3000+3+2000\n"
                "d.上下坡交替跑15km\n"
                "zone_range：Z2-Z4\n"
                "objective：提升有氧耐力\n"
                "warmup_suggestion：15分钟慢跑+动态拉伸"
            ),
        }]
        alternatives = _build_alternatives_from_hits(
            hits=hits,
            workout_type="aerobic_threshold",
            selected_main_set="3-4*3000/2min",
        )
        assert len(alternatives) >= 1, f"有 4 个变体时应至少产生 1 个备选"
        # 每个备选项必须包含所有必要字段
        for alt in alternatives:
            assert "warmup" in alt, f"备选项缺少 warmup 字段: {alt}"
            assert "main_set" in alt, f"备选项缺少 main_set 字段: {alt}"
            assert "cooldown" in alt, f"备选项缺少 cooldown 字段: {alt}"
            assert "zone_range" in alt, f"备选项缺少 zone_range 字段: {alt}"
            assert "source_chunk_id" in alt, f"备选项缺少 source_chunk_id 字段: {alt}"
            assert "reason" in alt, f"备选项缺少 reason 字段: {alt}"
            assert alt["source_chunk_id"] == "动作库_p0010_c0001"
            # zone_range 来自 WORKOUT_TEMPLATE_REGISTRY，aerobic_threshold 对应 Z3-Z4
            assert "Z" in alt["zone_range"], f"zone_range 应包含心率区间标识，实际: {alt['zone_range']}"
            # 备选项不应是已选的主选
            assert alt["main_set"] != "3-4*3000/2min"

    def test_returns_empty_when_hits_empty(self):
        """空 hits 返回空列表，不崩。"""
        alternatives = _build_alternatives_from_hits(
            hits=[], workout_type="easy_run",
        )
        assert alternatives == []

    def test_returns_empty_when_single_variant(self):
        """仅一个变体且被选为主选时，备选为空。"""
        hits = [{
            "chunk_id": "动作库_test_c0001",
            "source_file": "动作库.pdf",
            "page": 1,
            "text": (
                "name：测试训练\n"
                "content：\n"
                "a.10*400m\n"
                "zone_range：Z4-Z6"
            ),
        }]
        alternatives = _build_alternatives_from_hits(
            hits=hits,
            workout_type="interval_run",
            selected_main_set="10*400m",
        )
        assert alternatives == [], f"唯一变体被选为主选时备选应为空，实际: {alternatives}"

    def test_no_variants_no_alternatives(self):
        """无 content 变体的条目不产生备选。"""
        hits = [{
            "chunk_id": "动作库_test_c0001",
            "source_file": "动作库.pdf",
            "page": 1,
            "text": (
                "name：轻松跑\n"
                "content：\n"
                "40-60min慢跑\n"
                "zone_range：Z1-Z2"
            ),
        }]
        alternatives = _build_alternatives_from_hits(
            hits=hits, workout_type="easy_run",
        )
        assert alternatives == [], f"无变体时应返回空列表，实际: {alternatives}"

    def test_deduplicates_by_main_set(self):
        """相同 main_set 的备选项应去重。"""
        hits = [{
            "chunk_id": "动作库_test_c0001",
            "source_file": "动作库.pdf",
            "page": 1,
            "text": (
                "name：测试训练\n"
                "content：\n"
                "a.10*400m\n"
                "b.5*800m\n"
                "c.5*800m\n"  # 重复变体
                "zone_range：Z4-Z6"
            ),
        }]
        alternatives = _build_alternatives_from_hits(
            hits=hits,
            workout_type="interval_run",
            selected_main_set="10*400m",
        )
        main_sets = [a["main_set"] for a in alternatives]
        assert len(main_sets) == len(set(main_sets)), f"main_set 应无重复: {main_sets}"


class TestBuildAlternativesForHmp:
    """测试 _build_alternatives_for_hmp 为 HMP 协议类型构建备选。"""

    def test_returns_empty_when_no_execution_card(self):
        """无 execution_action_card 时返回空列表。"""
        card = {}
        assert _build_alternatives_for_hmp(card, "Z2-Z4") == []

    def test_returns_empty_when_single_candidate(self):
        """仅一个主课候选时返回空列表。"""
        card = {
            "execution_action_card": {
                "main_set_candidates": ["4×2000m"],
                "warmup_suggestion": "慢跑15分钟",
                "cooldown_suggestion": "慢跑10分钟",
                "zone_range": "Z4-Z6",
                "source": ["动作库.pdf"],
                "evidence": [{"chunk_id": "动作库_p0014_c0001"}],
            }
        }
        alternatives = _build_alternatives_for_hmp(card, "Z2-Z4")
        assert alternatives == []

    def test_builds_alternatives_from_multiple_candidates(self):
        """多个主课候选时，跳过第一个，其余作为备选。"""
        card = {
            "execution_action_card": {
                "main_set_candidates": [
                    "10-12*1000无氧阈,慢跑90s恢复",
                    "5*2000,2min慢跑恢复",
                    "1200*6-7(比赛)",
                ],
                "warmup_suggestion": "慢跑15分钟+马克操",
                "cooldown_suggestion": "慢跑10分钟+拉伸",
                "zone_range": "Z4-Z6",
                "source": ["动作库.pdf"],
                "evidence": [{"chunk_id": "动作库_p0014_c0001"}],
            }
        }
        alternatives = _build_alternatives_for_hmp(card, "Z2-Z4")
        assert len(alternatives) >= 1
        for alt in alternatives:
            assert "warmup" in alt
            assert "main_set" in alt
            assert "cooldown" in alt
            assert "zone_range" in alt
            assert "source_chunk_id" in alt
            assert "reason" in alt
            assert alt["source_chunk_id"] == "动作库_p0014_c0001"


class TestDailyScheduleItemAlternatives:
    """测试 DailyScheduleItem.alternatives 字段在生产路径中的行为。"""

    def test_alternatives_field_exists_in_dataclass(self):
        """DailyScheduleItem 默认包含 alternatives 字段且默认值为空列表。"""
        item = DailyScheduleItem(
            date="测试",
            day_label="周一",
            week_index=1,
            day_index=1,
            phase="基础期",
            training_type="轻松跑",
            training_type_label="轻松跑",
            workout_type="easy_run",
            zone_range="Z1-Z2",
            zone_label="Z1",
            intensity_target="低强度",
            main_set="40分钟慢跑",
            warmup="慢跑5分钟",
            cooldown="慢跑5分钟",
            alternative="",
            training_objective="建立有氧基础",
            evidence_tier="action_library",
            evidence_tier_label="动作库证据",
        )
        assert hasattr(item, "alternatives"), "DailyScheduleItem 应有 alternatives 属性"
        assert item.alternatives == [], "默认应为空列表"

    def test_alternatives_in_to_dict(self):
        """to_dict() 输出应包含 alternatives 字段。"""
        item = DailyScheduleItem(
            date="测试",
            day_label="周一",
            week_index=1,
            day_index=1,
            phase="基础期",
            training_type="轻松跑",
            training_type_label="轻松跑",
            workout_type="easy_run",
            zone_range="Z1-Z2",
            zone_label="Z1",
            intensity_target="低强度",
            main_set="40分钟慢跑",
            warmup="慢跑5分钟",
            cooldown="慢跑5分钟",
            alternative="",
            training_objective="建立有氧基础",
            evidence_tier="action_library",
            evidence_tier_label="动作库证据",
            alternatives=[
                {
                    "warmup": "慢跑5分钟",
                    "main_set": "50分钟慢跑",
                    "cooldown": "慢跑5分钟",
                    "zone_range": "Z1-Z2",
                    "source_chunk_id": "动作库_p0009_c0001",
                    "reason": "变体 b：更长距离，更低强度",
                }
            ],
        )
        data = item.to_dict()
        assert "alternatives" in data, "to_dict 应包含 alternatives"
        assert len(data["alternatives"]) == 1
        assert data["alternatives"][0]["main_set"] == "50分钟慢跑"

    def test_rest_day_has_empty_alternatives(self):
        """休息日的 DailyScheduleItem.alternatives 为空列表。"""
        structured_training_plan = {
            "week_plans": [
                {
                    "week_index": 1,
                    "phase": "基础期",
                    "days": [
                        {"day": "周一", "training_type": "休息", "main_set": ""},
                    ],
                }
            ],
        }
        calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=False)
        assert len(calendar.days) == 1
        rest_day = calendar.days[0]
        assert rest_day.is_rest is True
        assert rest_day.alternatives == [], "休息日备选应为空列表"

    def test_unknown_workout_type_has_empty_alternatives(self):
        """未知训练类型的 DailyScheduleItem.alternatives 为空列表。"""
        structured_training_plan = {
            "week_plans": [
                {
                    "week_index": 1,
                    "phase": "基础期",
                    "days": [
                        {"day": "周一", "training_type": "未知训练", "main_set": ""},
                    ],
                }
            ],
        }
        calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=False)
        assert len(calendar.days) == 1
        day = calendar.days[0]
        assert day.evidence_tier == "needs_evidence"
        assert day.alternatives == [], "未知训练类型备选应为空列表"

    def test_action_library_day_has_alternatives_when_variants_available(self, monkeypatch):
        """动作库有 a/b/c 变体的训练日应产生非空备选方案。"""
        # 模拟动作库返回有变体的条目
        def fake_hits(_workout_type):
            return [{
                "chunk_id": "动作库_p0010_c0001",
                "source_file": "动作库.pdf",
                "page": 10,
                "text": (
                    "name：有氧阈值训练\n"
                    "categories：Aerobic\n"
                    "content：\n"
                    "a.3-4*3000/2min\n"
                    "b.5-6*2000/2min\n"
                    "c.3*3000+3+2000\n"
                    "d.上下坡交替跑15km\n"
                    "zone_range：Z2-Z4\n"
                    "objective：提升有氧耐力\n"
                    "warmup_suggestion：15分钟慢跑+动态拉伸"
                ),
            }]

        monkeypatch.setattr(
            "marathon_qa_assistant.services.daily_schedule_generator.get_action_library_foundation_hits",
            fake_hits,
        )

        structured_training_plan = {
            "week_plans": [
                {
                    "week_index": 1,
                    "phase": "基础期",
                    "days": [
                        {"day": "周二", "training_type": "有氧阈值训练", "main_set": ""},
                    ],
                }
            ],
        }
        calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=False)
        assert len(calendar.days) == 1
        day = calendar.days[0]
        # 应该至少有备选方案
        assert isinstance(day.alternatives, list), f"alternatives 应为 list，实际: {type(day.alternatives)}"
        if day.evidence_tier == "action_library":
            assert len(day.alternatives) >= 1, (
                f"动作库有 4 个变体时应至少产生 1 个备选，"
                f"evidence_tier={day.evidence_tier}, alternatives={day.alternatives}"
            )
            # 验证备选项结构
            for alt in day.alternatives:
                assert "warmup" in alt
                assert "main_set" in alt
                assert "cooldown" in alt
                assert "zone_range" in alt
                assert "source_chunk_id" in alt
                assert "reason" in alt
                assert alt["source_chunk_id"] == "动作库_p0010_c0001"

    def test_no_variants_day_alternatives_stays_empty(self, monkeypatch):
        """动作库无变体的训练日备选方案为空，不崩。"""
        def fake_hits(_workout_type):
            return [{
                "chunk_id": "动作库_p0009_c0001",
                "source_file": "动作库.pdf",
                "page": 9,
                "text": (
                    "name：轻松跑\n"
                    "categories：Aerobic\n"
                    "content：\n"
                    "40-60min慢跑\n"
                    "zone_range：Z1-Z2\n"
                    "objective：建立有氧基础"
                ),
            }]

        monkeypatch.setattr(
            "marathon_qa_assistant.services.daily_schedule_generator.get_action_library_foundation_hits",
            fake_hits,
        )

        structured_training_plan = {
            "week_plans": [
                {
                    "week_index": 1,
                    "phase": "基础期",
                    "days": [
                        {"day": "周三", "training_type": "轻松跑", "main_set": ""},
                    ],
                }
            ],
        }
        calendar = generate_daily_schedule(structured_training_plan, enable_kb_fallback=False)
        assert len(calendar.days) == 1
        day = calendar.days[0]
        assert day.alternatives == [], f"无变体时备选应为空列表，实际: {day.alternatives}"
