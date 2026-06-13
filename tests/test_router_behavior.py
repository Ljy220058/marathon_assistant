import asyncio
import sys
from pathlib import Path

import pytest

root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from marathon_qa_assistant.core.working_state import build_working_state
from marathon_qa_assistant.core.workflow_graph import FallbackIntegratedApp, _check_node_visit_limits
from marathon_qa_assistant.nodes.router import router_node
from marathon_qa_assistant.nodes.routing import (
    after_adaptive_coach_route,
    after_conditioning_route,
    after_context_fanout_route,
    after_critic_auditor_route,
    after_executor_route,
    after_planner_route,
    after_rule_checker_route,
    after_router_route,
    after_supervisor_route,
    evaluate_plan_evidence,
    gate_decision,
    supervisor_node,
)


def test_router_node_routes_research_query_to_research_mode():
    state = {"query": "请基于研究文献比较乳酸阈训练和 VO2max 训练机制"}
    result = asyncio.run(router_node(state, None))
    assert result["mode"] == "research"
    assert result["workflow_kind"] == "research"
    assert result["intent_type"] == "qa"
    assert result["category"] == "research"


def test_router_node_routes_weekly_plan_query_to_subagent_mode():
    state = {"query": "请帮我安排下周马拉松训练计划"}
    result = asyncio.run(router_node(state, None))
    assert result["mode"] == "subagent"
    assert result["workflow_kind"] == "plan"
    assert result["intent_type"] == "plan"
    assert result["category"] == "coach"


def test_router_node_routes_mixed_pain_and_next_week_plan_to_adaptive_priority():
    state = {"query": "我膝盖疼，下周训练怎么练？"}
    result = asyncio.run(router_node(state, None))
    assert result["workflow_kind"] == "adaptive"
    assert result["intent_type"] == "plan"
    assert result["mode"] == "adaptive"
    assert result["category"] == "therapist"
    assert result["intent_labels"] == ["adaptive_adjustment", "training_plan"]
    assert result["intent_priority"] == "adaptive_adjustment"


def test_router_node_keeps_pure_pain_question_as_therapist_qa():
    state = {"query": "膝盖疼是什么原因？"}
    result = asyncio.run(router_node(state, None))
    assert result["workflow_kind"] == "qa"
    assert result["intent_type"] == "qa"
    assert result["mode"] == "team"
    assert result["category"] == "therapist"
    assert result["intent_labels"] == ["general_qa"]
    assert result["intent_priority"] == "general_qa"


def test_router_node_treats_profile_signal_query_as_regular_qa():
    state = {"query": "我的乳酸阈心率改为 172，帮我更新训练画像"}
    result = asyncio.run(router_node(state, None))
    assert result["mode"] == "team"
    assert result["workflow_kind"] == "qa"
    assert result["intent_type"] == "qa"
    assert result["category"] == "coach"
    assert "profile_signal" in result["intent_labels"]


def test_router_node_marks_nutrition_queries_with_nutritionist_category():
    state = {"query": "比赛前一晚如何安排碳水补给和 hydration？"}
    result = asyncio.run(router_node(state, None))
    assert result["mode"] == "team"
    assert result["workflow_kind"] == "qa"
    assert result["intent_type"] == "qa"
    assert result["category"] == "nutritionist"
    assert result["intent_labels"] == ["nutrition_query"]
    assert result["intent_priority"] == "nutrition_query"


def test_gate_decision_respects_intercepted_mode():
    assert gate_decision({"mode": "intercepted"}) == "blocked"


def test_working_state_initializes_node_visit_count():
    state = build_working_state(query="请给我训练计划")
    assert state["node_visit_count"] == {}


def test_node_visit_circuit_breaker_counts_and_fails_loud():
    state = {"node_visit_count": {"therapist": 2}}
    with pytest.raises(RuntimeError) as excinfo:
        _check_node_visit_limits(state, "therapist")
    assert "Circuit breaker" in str(excinfo.value)
    assert "therapist" in str(excinfo.value)


def test_node_visit_circuit_breaker_returns_updated_counts():
    state = {"node_visit_count": {"planner": 1}}
    visits = _check_node_visit_limits(state, "planner")
    assert visits["planner"] == 2


def test_fallback_workflow_routes_evidence_retriever_to_conditioning():
    app = FallbackIntegratedApp({})
    assert app._next_node("evidence_retriever", {}) == "conditioning_constraints"


def test_fallback_workflow_routes_conditioning_to_supervisor_by_default():
    app = FallbackIntegratedApp({})
    assert app._next_node("conditioning_constraints", {}) == "supervisor"


def test_fallback_workflow_routes_adaptive_conditioning_to_planner_after_replan():
    app = FallbackIntegratedApp({})
    state = {"workflow_kind": "adaptive", "adaptation_type": "MISSED"}
    assert app._next_node("conditioning_constraints", state) == "planner"


def test_fallback_workflow_routes_router_to_context_fanout():
    app = FallbackIntegratedApp({})
    assert app._next_node("router", {}) == "context_fanout"


def test_after_router_route_always_enters_context_fanout():
    assert after_router_route({}) == "context_fanout"


def test_after_context_fanout_route_continues_to_evidence_retriever():
    assert after_context_fanout_route({}) == "evidence_retriever"


def test_after_conditioning_route_defaults_to_supervisor():
    assert after_conditioning_route({"workflow_kind": "plan"}) == "supervisor"


def test_after_conditioning_route_sends_adaptive_replan_straight_to_planner():
    state = {"workflow_kind": "adaptive", "adaptation_type": "MISSED", "s_and_c_done": True}
    assert after_conditioning_route(state) == "planner"


def test_supervisor_routes_initial_plan_to_planner():
    state = {
        "missing_fields": [],
        "intent_type": "plan",
        "workflow_kind": "plan",
        "mode": "subagent",
    }
    assert after_supervisor_route(state) == "planner"


def test_supervisor_routes_adaptive_initial_pass_to_adaptive_coach():
    state = {
        "missing_fields": [],
        "intent_type": "plan",
        "workflow_kind": "adaptive",
        "mode": "adaptive",
    }
    assert after_supervisor_route(state) == "adaptive_coach"


def test_supervisor_routes_adaptive_replan_back_to_adaptive_coach_before_constraints_refresh():
    state = {
        "missing_fields": [],
        "intent_type": "plan",
        "workflow_kind": "adaptive",
        "mode": "adaptive",
        "adaptation_type": "MISSED",
    }
    assert after_supervisor_route(state) == "adaptive_coach"


def test_supervisor_routes_missing_fields_to_missing_info_handler():
    state = {
        "missing_fields": ["weekly_mileage"],
        "intent_type": "plan",
        "workflow_kind": "plan",
        "mode": "subagent",
    }
    assert after_supervisor_route(state) == "missing_info_handler"


def test_supervisor_node_records_dispatch_decision():
    state = {
        "missing_fields": [],
        "intent_type": "plan",
        "workflow_kind": "plan",
        "mode": "subagent",
    }
    output = asyncio.run(supervisor_node(state, None))
    assert output["supervisor_decision"] == "planner"
    assert output["reasoning_log"][0].startswith("[supervisor]")
    assert output["execution_trace"][0]["node"] == "supervisor"


def test_after_planner_route_requires_subtasks_before_executor():
    with pytest.raises(RuntimeError):
        after_planner_route({"subtasks": []})


def test_after_executor_routes_to_nutritionist():
    assert after_executor_route({}) == "nutritionist"


def test_after_adaptive_coach_routes_missed_workout_directly_to_conditioning():
    state = {"workflow_kind": "adaptive", "adaptation_type": "MISSED"}
    assert after_adaptive_coach_route(state) == "conditioning_constraints"


def test_after_adaptive_coach_routes_injury_or_fatigue_to_therapist():
    assert after_adaptive_coach_route({"workflow_kind": "adaptive", "adaptation_type": "INJURY"}) == "therapist"
    assert after_adaptive_coach_route({"workflow_kind": "adaptive", "adaptive_adjustment": {"adaptation_type": "FATIGUE"}}) == "therapist"


def test_after_critic_auditor_route_returns_to_supervisor_for_retry():
    assert after_critic_auditor_route({"is_approved": False, "iteration_count": 1, "workflow_kind": "plan"}) == "supervisor"


def test_after_critic_auditor_route_fails_loud_after_max_iterations():
    assert after_critic_auditor_route({"is_approved": False, "iteration_count": 3, "workflow_kind": "plan"}) == "workflow_error"


def test_after_rule_checker_route_sends_hard_failures_to_workflow_error():
    assert after_rule_checker_route({"workflow_error": {"error_code": "HARD_RULE_VIOLATION"}}) == "workflow_error"


def test_evaluate_plan_evidence_for_non_plan_query_not_required():
    result = evaluate_plan_evidence([], "今天适合怎么练", "qa")
    assert result == {"required": False, "has_plan_evidence": True}


def test_evaluate_plan_evidence_detects_macrocycle_signals_from_query():
    result = evaluate_plan_evidence([], "给我一个12周半马训练计划，目标145", "plan")
    assert result["required"] is True
    assert result["has_plan_evidence"] is True
    assert result["is_training_plan_request"] is True
