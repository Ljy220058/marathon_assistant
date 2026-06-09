"""Profile field gating tests — minimum required fields for plan generation."""
import sys
from pathlib import Path

import pytest


BASE_DIR = Path(__file__).absolute().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from marathon_qa_assistant.nodes import profile_and_retrieval as profile_module  # noqa: E402
from marathon_qa_assistant.nodes.profile_and_retrieval import (  # noqa: E402
    _detect_missing_fields,
)


def _build_plan_state(query: str = "build a half marathon training plan") -> dict:
    return {
        "intent_type": "plan",
        "query": query,
    }


def test_minimum_required_fields_only_block_goal_weekly_days():
    """当前 profile 硬阻断字段为 goal, weekly_mileage, vo2max, lthr,
    t_pace/pace_preference, available_days。全部提供后应无缺失。"""
    state = _build_plan_state()
    profile = {
        "goal": "half marathon sub90",
        "weekly_mileage": 50,
        "vo2max": 55,
        "lthr": 170,
        "t_pace": "4:15/km",
        "available_days": "Tue,Thu,Sun",
    }

    assert _detect_missing_fields(state, profile) == []
