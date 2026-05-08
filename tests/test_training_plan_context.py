from marathon_qa_assistant.core.training_plan_context import (
    align_plan_duration_context,
    derive_plan_duration_weeks,
    parse_requested_weeks,
)


def test_parse_requested_weeks_supports_chinese_and_digits():
    assert parse_requested_weeks("请帮我制定四周训练计划") == 4
    assert parse_requested_weeks("我想要20周马拉松计划") == 20
    assert parse_requested_weeks("先给我第一周训练计划") == 1


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


def test_align_plan_duration_context_falls_back_to_race_countdown():
    context = align_plan_duration_context(
        "请为我生成训练计划",
        {
            "target_race_date": "1个月",
            "plan_duration_weeks": 12,
        },
    )

    assert context["requested_weeks"] is None
    assert context["resolved_plan_weeks"] == 4
    assert context["resolved_from"] == "target_race_date"
