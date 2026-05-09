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
)
from marathon_qa_assistant.nodes.output_nodes import _build_structured_report
from marathon_qa_assistant.ui.legacy_ui import UIHelper


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
    assert "kb_fallback" in EVIDENCE_TIER_LABELS
    assert "plan_only" in EVIDENCE_TIER_LABELS
    assert EVIDENCE_TIER_LABELS["action_library"] == "动作库课表"
    assert EVIDENCE_TIER_LABELS["kb_fallback"] == "参考知识库生成"
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
        assert card["evidence_tier"] == "plan_only"
        assert card["main_set_candidates"]
        assert "HMP" in card["intensity_target"]
        assert card["training_objective"]


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

    calendar = generate_daily_schedule(structured_training_plan)
    assert calendar.total_days == 14
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
    assert custom_day.evidence_tier == "plan_only"
    assert custom_day.evidence_tier_label == "基础计划"


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
    assert quality_day.main_set == "18km 渐进跑"
    assert "95% HMP" in quality_day.intensity_target
    assert "半马后程抗疲劳" in quality_day.training_objective


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

    calendar = generate_daily_schedule(structured_training_plan)

    assert all(day.workout_type != "hm_95_long_fast_run" for day in calendar.days)


# ==================== 结构化报告包含新字段测试 ====================

def test_structured_report_includes_monthly_calendar():
    report = _build_structured_report(
        {
            "query": "给我生成训练计划",
            "category": "coach",
            "mode": "team",
            "rag_sources": [],
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
