from marathon_qa_assistant.core.training_plan_context import (
    align_plan_duration_context,
    coerce_float_from_unit_text,
    coerce_int_from_unit_text,
    derive_plan_duration_weeks,
    parse_requested_weeks,
)


def test_parse_requested_weeks_supports_chinese_and_digits():
    assert parse_requested_weeks("请帮我制定四周训练计划") == 4
    assert parse_requested_weeks("我想要20周马拉松计划") == 20
    assert parse_requested_weeks("先给我第一周训练计划") == 1
    assert parse_requested_weeks("计划周期：12") == 12


def test_derive_plan_duration_weeks_from_target_race_date_labels():
    assert derive_plan_duration_weeks("1个月") == 4
    assert derive_plan_duration_weeks("2个月后") == 8
    assert derive_plan_duration_weeks("半年") == 24


def test_align_plan_duration_context_prefers_explicit_query_weeks():
    context = align_plan_duration_context(
        "请给我做20周全马训练计划",
        {
            "target_race_date": "3个月",
            "plan_duration_weeks": 12,
        },
    )

    assert context["requested_weeks"] == 20
    assert context["target_race_weeks"] == 12
    assert context["resolved_plan_weeks"] == 20
    assert context["resolved_from"] == "query"
    assert context["aligned_profile"]["plan_duration_weeks"] == 20


def test_align_plan_duration_context_prefers_saved_profile_weeks_over_race_countdown():
    context = align_plan_duration_context(
        "请为我生成训练计划",
        {
            "target_race_date": "1个月",
            "plan_duration_weeks": 12,
        },
    )

    assert context["requested_weeks"] is None
    assert context["target_race_weeks"] == 4
    assert context["resolved_plan_weeks"] == 12
    assert context["resolved_from"] == "profile"


def test_align_plan_duration_context_uses_race_countdown_when_profile_weeks_missing():
    context = align_plan_duration_context(
        "请为我生成训练计划",
        {
            "target_race_date": "1个月",
        },
    )

    assert context["requested_weeks"] is None
    assert context["stored_plan_weeks"] is None
    assert context["resolved_plan_weeks"] == 4
    assert context["resolved_from"] == "target_race_date"


def test_numeric_profile_fields_accept_common_units():
    assert coerce_float_from_unit_text("105 km") == 105.0
    assert coerce_float_from_unit_text("100公里") == 100.0
    assert coerce_float_from_unit_text(" 82.5 千米 ") == 82.5
    assert coerce_float_from_unit_text("未填写", default=40.0) == 40.0

    assert coerce_int_from_unit_text("120 min") == 120
    assert coerce_int_from_unit_text("90分钟") == 90
    assert coerce_int_from_unit_text("12 周") == 12
