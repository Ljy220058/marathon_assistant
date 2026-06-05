from marathon_qa_assistant.services.plan_query_classifier import (
    has_plan_generation_profile,
    is_plan_query,
)


def test_is_plan_query_matches_training_plan_language():
    assert is_plan_query("请生成 8 周半马训练计划，目标配速 5:30/km") is True
    assert is_plan_query("帮我安排 marathon training plan for 12 weeks") is True


def test_is_plan_query_excludes_nutrition_and_fueling_questions():
    assert is_plan_query("半马比赛前一天怎么补给和补水？") is False
    assert is_plan_query("nutrition and hydration plan for race day") is False


def test_has_plan_generation_profile_requires_any_meaningful_plan_field():
    assert has_plan_generation_profile({}) is False
    assert has_plan_generation_profile({"goal": "半马 sub140"}) is True
    assert has_plan_generation_profile({"available_days": ["周二", "周四"]}) is True
