import asyncio
import sys
from pathlib import Path


BASE_DIR = Path(__file__).absolute().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from marathon_qa_assistant.nodes import profile_and_retrieval as profile_module  # noqa: E402
from marathon_qa_assistant.nodes.profile_and_retrieval import (  # noqa: E402
    EXTRACT_PROFILE_SYSTEM,
    FIELD_HINTS,
    FIELD_LABELS,
    PROFILE_FIELD_ORDER,
    _detect_missing_enhancement_fields,
    _detect_missing_fields,
    profile_selections_to_save,
)
from marathon_qa_assistant.nodes.profile_update import (  # noqa: E402
    PROFILE_UPDATE_SYSTEM,
    _FIELD_LABEL_MAP,
)


def _build_plan_state(query: str = "build a half marathon training plan") -> dict:
    return {
        "intent_type": "plan",
        "query": query,
    }


def test_minimum_required_fields_only_block_goal_weekly_days():
    state = _build_plan_state()
    profile = {
        "goal": "half marathon sub90",
        "weekly_mileage": 50,
        "available_days": "Tue,Thu,Sun",
    }

    assert _detect_missing_fields(state, profile) == []


def test_enhancement_fields_no_longer_hard_block_first_generation():
    state = _build_plan_state()
    profile = {
        "goal": "marathon sub330",
        "weekly_mileage": 60,
        "available_days": "Mon,Wed,Sat,Sun",
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


def test_profile_workflow_exposes_runner_calibration_contract_fields():
    for field in [
        "current_half_time",
        "target_half_time",
        "last_month_mileage",
        "recent_four_week_mileage",
        "target_pace",
        "injury",
        "recovery_state",
        "injury_or_fatigue",
    ]:
        assert field in EXTRACT_PROFILE_SYSTEM
        assert field in FIELD_LABELS
        assert field in FIELD_HINTS
        assert field in PROFILE_FIELD_ORDER


def test_profile_selection_save_preserves_runner_calibration_fields():
    saved = profile_selections_to_save(
        {
            "current_half_time": "1:25:00",
            "target_half_time": "1:20:00",
            "last_month_mileage": "260 km",
            "recent_four_week_mileage": "59.8 km",
            "target_pace": "3:48/km",
            "injury": "none",
            "recovery_state": "normal",
            "injury_or_fatigue": "none",
        }
    )

    assert saved["current_half_time"] == "1:25:00"
    assert saved["target_half_time"] == "1:20:00"
    assert saved["last_month_mileage"] == "260 km"
    assert saved["recent_four_week_mileage"] == "59.8 km"
    assert saved["target_pace"] == "3:48/km"
    assert saved["injury"] == "none"
    assert saved["recovery_state"] == "normal"
    assert saved["injury_or_fatigue"] == "none"


def test_profile_update_prompt_accepts_runner_calibration_fields():
    for field in [
        "current_half_time",
        "target_half_time",
        "last_month_mileage",
        "recent_four_week_mileage",
        "target_pace",
        "injury",
        "recovery_state",
        "injury_or_fatigue",
    ]:
        assert field in PROFILE_UPDATE_SYSTEM
        assert field in _FIELD_LABEL_MAP


def test_no_evidence_static_fallback_uses_llm_general_knowledge_not_refusal():
    content = profile_module._static_fallback([], [])

    assert "llm_general_knowledge" in content
    assert "模型通用知识" in content
    for forbidden in ["## 信息不足", "## 证据不足", "请补充更具体的目标", "上传相关 PDF"]:
        assert forbidden not in content


def test_no_evidence_missing_info_handler_asks_llm_for_general_answer(monkeypatch):
    async def fake_ai_invoke(prompt, config, current_usage):
        assert "llm_general_knowledge" in prompt
        assert "不要要求用户补充上下文" in prompt
        assert "不要伪造引用" in prompt
        return (
            "Use an easy run, rest, and subjective fatigue as conservative defaults.",
            {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
        )

    monkeypatch.setattr(profile_module, "ai_invoke", fake_ai_invoke)

    result = asyncio.run(
        profile_module.missing_info_handler_node(
            {
                "intent_type": "qa",
                "query": "I feel tired after today's run. What should I do tomorrow?",
                "missing_fields": [],
                "rag_sources": [],
                "entities": [],
                "category": "coach",
                "token_usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
            {"configurable": {"llm_provider": "openai", "llm_model": "gpt-5.5"}},
        )
    )

    assert result["final_report"].startswith("## 模型通用知识回答")
    assert "llm_general_knowledge" in result["final_report"]
    for forbidden in ["## 信息不足", "## 证据不足", "请补充更具体的目标"]:
        assert forbidden not in result["final_report"]
    assert result["missing_info_status"] == ""
    assert result["token_usage"]["total_tokens"] == 18