import asyncio
import sys
from pathlib import Path


root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from marathon_qa_assistant.nodes.router import router_node
from marathon_qa_assistant.nodes.routing import (
    after_auditor_route,
    after_planner_route,
    after_profile_update_route,
    after_router_route,
    after_therapist_route,
    entity_route_decision,
    gate_decision,
)


def test_router_node_routes_research_query_to_research_mode():
    state = {"query": "请基于文献研究对比乳酸阈训练和VO2max训练机制"}

    result = asyncio.run(router_node(state, None))

    assert result["mode"] == "research"
    assert result["intent_type"] == "qa"
    assert result["category"] == "research"


def test_router_node_routes_weekly_plan_query_to_subagent_mode():
    state = {"query": "请帮我安排下周马拉松训练计划"}

    result = asyncio.run(router_node(state, None))

    assert result["mode"] == "subagent"
    assert result["intent_type"] == "plan"
    assert result["category"] == "coach"


def test_router_node_routes_profile_update_query_to_profile_update_intent():
    state = {"query": "我的乳酸阈心率改为 172，帮我更新训练画像"}

    result = asyncio.run(router_node(state, None))

    assert result["mode"] == "team"
    assert result["intent_type"] == "profile_update"
    assert result["category"] == "coach"


def test_router_node_marks_nutrition_queries_with_nutritionist_category():
    state = {"query": "比赛前一晚如何安排碳水补给和 hydration？"}

    result = asyncio.run(router_node(state, None))

    assert result["mode"] == "team"
    assert result["intent_type"] == "qa"
    assert result["category"] == "nutritionist"


def test_gate_decision_respects_intercepted_mode():
    state = {"mode": "intercepted"}

    assert gate_decision(state) == "formatter"


def test_entity_route_decision_sends_missing_fields_to_handler():
    state = {"missing_fields": ["goal_race"], "gate_hits": [], "query": "", "intent_type": "qa", "mode": "team"}

    assert entity_route_decision(state) == "missing_info_handler"


def test_entity_route_decision_sends_plan_without_evidence_to_handler():
    state = {
        "missing_fields": [],
        "gate_hits": [],
        "query": "给我出个训练方案",
        "intent_type": "plan",
        "mode": "team",
    }

    assert entity_route_decision(state) == "missing_info_handler"


def test_entity_route_decision_sends_subagent_plan_with_evidence_to_planner():
    state = {
        "missing_fields": [],
        "gate_hits": [{"text": "周一轻松跑 8km，周三 6x800m 间歇，周末 LSD 24km"}],
        "query": "请给我一周训练计划",
        "intent_type": "plan",
        "mode": "subagent",
    }

    assert entity_route_decision(state) == "planner"


def test_after_router_route_sends_profile_updates_to_profile_update_node():
    state = {"intent_type": "profile_update"}

    assert after_router_route(state) == "profile_update"


def test_after_profile_update_route_finishes_updated_profile_requests():
    state = {"profile_update__is_update": True}

    assert after_profile_update_route(state) == "formatter"


def test_after_planner_route_requires_subtasks_before_executor():
    state = {"subtasks": []}

    assert after_planner_route(state) == "missing_info_handler"


def test_after_therapist_route_prioritizes_auditor_for_qa():
    state = {"intent_type": "qa", "is_approved": False, "mode": "team"}

    assert after_therapist_route(state) == "auditor"


def test_after_auditor_route_returns_to_executor_for_subagent_retry():
    state = {"is_approved": False, "iteration_count": 1, "mode": "subagent"}

    assert after_auditor_route(state) == "executor"


def test_after_auditor_route_stops_after_max_iterations():
    state = {"is_approved": False, "iteration_count": 3, "mode": "team"}

    assert after_auditor_route(state) == "missing_info_handler"
