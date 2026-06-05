from marathon_qa_assistant.core.profile_context import build_prompt_profile_summary, filter_confirmed_profile


def test_filter_confirmed_profile_removes_unconfirmed_default_fields():
    raw_profile = {
        "goal": "半马 sub135",
        "weekly_mileage": 50,
        "experience_level": "新手",
        "weight_kg": 65,
        "t_pace": "3:15/km",
    }

    filtered = filter_confirmed_profile(raw_profile)

    assert filtered == {}


def test_filter_confirmed_profile_keeps_explicitly_confirmed_fields():
    raw_profile = {
        "goal": "半马 sub135",
        "weekly_mileage": 50,
        "experience_level": "进阶",
        "weight_kg": 62,
        "_confirmed_fields": ["goal", "weekly_mileage", "experience_level", "weight_kg"],
    }

    filtered = filter_confirmed_profile(raw_profile)

    assert filtered["goal"] == "半马 sub135"
    assert filtered["weekly_mileage"] == 50
    assert filtered["experience_level"] == "进阶"
    assert filtered["weight_kg"] == 62
    assert filtered["_profile_context"] == {
        "used_profile_fields": ["goal", "weekly_mileage", "experience_level", "weight_kg"],
        "missing_fields": [],
        "assumptions": [],
    }


def test_prompt_profile_summary_does_not_leak_unconfirmed_defaults():
    raw_profile = {
        "goal": "半马 sub135",
        "weekly_mileage": 50,
        "experience_level": "新手",
        "weight_kg": 65,
        "nutrition_profile": {"weight_kg": 65},
        "t_pace": "3:15/km",
    }

    summary = build_prompt_profile_summary(raw_profile)

    assert "半马 sub135" not in summary
    assert "新手" not in summary
    assert "65" not in summary
    assert "3:15/km" not in summary
    assert "本轮无已确认画像字段" in summary


def test_prompt_profile_summary_includes_confirmed_fields_only():
    raw_profile = {
        "goal": "半马 sub135",
        "weekly_mileage": 50,
        "experience_level": "新手",
        "weight_kg": 65,
        "_confirmed_fields": ["goal", "weekly_mileage"],
    }

    summary = build_prompt_profile_summary(raw_profile)

    assert "目标: 半马 sub135" in summary
    assert "周跑量: 50 km" in summary
    assert "新手" not in summary
    assert "65" not in summary
