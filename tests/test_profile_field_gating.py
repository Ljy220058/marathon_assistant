import sys
from pathlib import Path


BASE_DIR = Path(__file__).absolute().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from marathon_qa_assistant.nodes.profile_and_retrieval import (  # noqa: E402
    PROFILE_FIELD_ORDER,
    _detect_missing_enhancement_fields,
    _detect_missing_fields,
)


def _build_plan_state(query: str = "请给我生成半马训练计划") -> dict:
    return {
        "intent_type": "plan",
        "query": query,
    }


def test_minimum_required_fields_only_block_goal_weekly_days():
    state = _build_plan_state()
    profile = {
        "goal": "半马 sub90",
        "weekly_mileage": 50,
        "available_days": "周二,周四,周日",
    }

    assert _detect_missing_fields(state, profile) == []


def test_enhancement_fields_no_longer_hard_block_first_generation():
    state = _build_plan_state()
    profile = {
        "goal": "全马 sub330",
        "weekly_mileage": 60,
        "available_days": "周一,周三,周六,周日",
        "vo2max": "",
        "lthr": "",
        "t_pace": "",
    }

    assert _detect_missing_fields(state, profile) == []
    enhancement_missing = _detect_missing_enhancement_fields(state, profile)
    assert "vo2max" in enhancement_missing
    assert "lthr" in enhancement_missing
    assert "t_pace" in enhancement_missing


def test_profile_field_order_includes_pace_preference():
    assert "pace_preference" in PROFILE_FIELD_ORDER
