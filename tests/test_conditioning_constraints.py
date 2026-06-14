import asyncio
import sys
from pathlib import Path
import pytest


root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from marathon_qa_assistant.core.strength_conditioning_constraints import build_training_capacity_envelope
from marathon_qa_assistant.core.state_models import build_adaptive_adjustment_contract
from marathon_qa_assistant.core.half_marathon_validator import _validate_workout_duration_bounds
from marathon_qa_assistant.core.training_plan_skeleton import build_structured_training_plan_skeleton
from marathon_qa_assistant.nodes.conditioning import conditioning_constraints_node
from marathon_qa_assistant.nodes.expert_nodes import (
    adaptive_coach_node,
    coach_node,
    critic_auditor_node,
    nutritionist_node,
    psychologist_node,
    rule_checker_node,
    therapist_node,
)
from marathon_qa_assistant.nodes.plan_nodes import executor_node
from marathon_qa_assistant.nodes.security import safety_out_node


def _expert_trace_base_state(query: str = "marathon training question"):
    return {
        "query": query,
        "intent_type": "qa",
        "draft_plan": "",
        "final_report": "",
        "user_profile": {"goal": "marathon 3:30", "weekly_mileage": 50, "experience_level": "intermediate"},
        "adaptive_feedback": {},
        "evidence_bundle": {"evidence_items": []},
        "rag_sources": [],
        "ranked_evidence": [],
        "graph_context": "",
        "wiki_context": "",
        "token_usage": {},
        "expert_evidence_trace": {},
    }


async def _fake_expert_ai_invoke(prompt, config, token_usage):
    del prompt, config
    return "role feedback [1]", token_usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def _expert_trace_hit(chunk_id: str, domain: str, text: str):
    return {
        "source_file": f"{domain}.pdf",
        "source_path": f"data/domain_docs/{domain}.pdf",
        "page": 1,
        "chunk_id": chunk_id,
        "citation_label": "[1]",
        "evidence_domain": domain,
        "domain_terms": [domain],
        "text": text,
        "score": 0.91,
    }


def test_training_capacity_envelope_is_capacity_not_medical_diagnosis():
    envelope = build_training_capacity_envelope(
        profile={"weekly_mileage": 50, "available_days": ["周二", "周四", "周六", "周日"]},
        query="请生成 16 周全马训练计划",
    )

    assert envelope["source_role"] == "s_and_c"
    assert envelope["load_ceiling"]["weekly_load_cap_km"] == 55.0
    assert envelope["downstream_targets"]["therapist"] == ["requires_therapist_review"]
    assert "medical" in envelope["boundary"]


def test_training_capacity_envelope_routes_pain_signal_to_therapist():
    envelope = build_training_capacity_envelope(
        profile={"weekly_mileage": 50},
        query="膝盖疼，但我还想继续训练",
    )

    flags = envelope["capacity_risk_flags"]
    assert any(flag["code"] == "requires_therapist_review" for flag in flags)
    assert envelope["load_ceiling"]["weekly_load_cap_km"] < 50


def test_training_capacity_envelope_ignores_negated_injury_status():
    envelope = build_training_capacity_envelope(
        profile={"weekly_mileage": 50, "injury": "none"},
        query="Build a 16 week marathon training plan, no current injury.",
    )

    flags = envelope["capacity_risk_flags"]
    assert not any(flag["code"] == "requires_therapist_review" for flag in flags)
    assert envelope["load_ceiling"]["weekly_load_cap_km"] >= 50


def test_adaptive_adjustment_detects_missed_workout_from_raw_text():
    adjustment = build_adaptive_adjustment_contract(raw_text="上周漏练两次，需要重新安排")

    assert adjustment["adaptation_type"] == "MISSED"
    assert "missed_workout" in adjustment["reason_codes"]


def test_conditioning_constraints_node_writes_state_contract():
    state = {
        "query": "请生成 12 周半马训练计划",
        "workflow_kind": "plan",
        "intent_type": "plan",
        "user_profile": {"weekly_mileage": 40, "available_days": ["周二", "周四", "周日"]},
        "ranked_evidence": [
            {
                "citation_label": "[1]",
                "source_file": "strength_conditioning_guide.pdf",
                "source_path": "docs/domain/strength_conditioning_guide.pdf",
                "page": 3,
                "chunk_id": "sc-001",
                "text": "Weekly load ceiling and recovery windows should constrain normal training capacity.",
            }
        ],
        "token_usage": {},
    }

    output = asyncio.run(conditioning_constraints_node(state, None))

    assert output["s_and_c_done"] is True
    assert output["training_capacity_envelope"]["schema_version"] == "training_capacity_envelope.v1"
    assert output["s_and_c_constraints"] == output["training_capacity_envelope"]
    assert output["expert_evidence_trace"]["conditioning_constraints"]["role"] == "conditioning_constraints"
    assert output["expert_evidence_trace"]["conditioning_constraints"]["evidence_refs"] == ["[1]"]
    assert output["execution_trace"][0]["node"] == "conditioning_constraints"


def test_training_plan_skeleton_consumes_capacity_envelope():
    envelope = build_training_capacity_envelope(
        profile={"weekly_mileage": 50, "available_days": ["周二", "周四", "周六", "周日"]},
        query="请生成 8 周半马训练计划",
    )

    plan = build_structured_training_plan_skeleton(
        query="请生成 8 周半马训练计划",
        profile={"goal": "半马1:40", "weekly_mileage": 50, "available_days": ["周二", "周四", "周六", "周日"]},
        requested_weeks=8,
        training_capacity_envelope=envelope,
    )

    assert plan["training_capacity_envelope"] == envelope
    cap = envelope["load_ceiling"]["weekly_load_cap_km"]
    weekly_targets = [
        week["repeat_guard_signature"]["weekly_volume_km"]
        for week in plan["week_plans"]
    ]
    assert weekly_targets
    assert max(weekly_targets) <= cap


def test_marathon_macrocycle_capacity_envelope_keeps_session_durations_auditable():
    envelope = build_training_capacity_envelope(
        profile={"weekly_mileage": 50, "available_days": ["周二", "周四", "周六", "周日"]},
        query="请生成 16 周全马训练计划",
    )

    plan = build_structured_training_plan_skeleton(
        query="请生成 16 周全马训练计划，目标全马3小时30分，每周二周四周六周日训练。",
        profile={
            "goal": "全马3:30",
            "weekly_mileage": 50,
            "available_days": ["周二", "周四", "周六", "周日"],
            "experience_level": "中级",
            "max_session_minutes": 150,
        },
        requested_weeks=16,
        training_capacity_envelope=envelope,
    )

    cap = envelope["load_ceiling"]["weekly_load_cap_km"]
    long_cap = envelope["load_ceiling"]["max_long_run_km"]
    assert max(week["repeat_guard_signature"]["weekly_volume_km"] for week in plan["week_plans"]) <= cap
    assert max(
        week["repeat_guard_signature"]["long_run_distance_km"] or 0
        for week in plan["week_plans"]
    ) <= long_cap
    assert _validate_workout_duration_bounds(plan["week_plans"]) == []


def test_executor_marks_multi_week_plan_for_nutrition_review(monkeypatch):
    async def fake_ai_invoke(prompt, config, token_usage):
        del prompt, config
        return "计划草案", token_usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    monkeypatch.setattr("marathon_qa_assistant.nodes.plan_nodes.ai_invoke", fake_ai_invoke)

    state = {
        "query": "请生成 16 周全马训练计划，目标全马3小时30分，每周二周四周六周日训练。",
        "workflow_kind": "plan",
        "intent_type": "plan",
        "subtasks": [{"id": "task-1", "title": "生成计划"}],
        "user_profile": {
            "goal": "全马3:30",
            "weekly_mileage": 50,
            "available_days": ["周二", "周四", "周六", "周日"],
            "experience_level": "中级",
            "max_session_minutes": 150,
        },
        "training_capacity_envelope": build_training_capacity_envelope(
            profile={"weekly_mileage": 50, "available_days": ["周二", "周四", "周六", "周日"]},
            query="请生成 16 周全马训练计划",
        ),
        "ranked_evidence": [],
        "rag_sources": [],
        "evidence_bundle": {"health": {}},
        "token_usage": {},
    }

    output = asyncio.run(executor_node(state, None))

    assert output["structured_training_plan"]["plan_meta"]["actual_weeks"] == 16
    assert output["needs_nutrition_review"] is True


def test_executor_preserves_structured_plan_when_llm_text_times_out(monkeypatch):
    async def slow_ai_invoke(prompt, config, token_usage):
        del prompt, config, token_usage
        await asyncio.sleep(1)
        return "不应返回", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    monkeypatch.setattr("marathon_qa_assistant.nodes.plan_nodes.ai_invoke", slow_ai_invoke)
    monkeypatch.setattr("marathon_qa_assistant.nodes.plan_nodes._executor_llm_timeout_sec", lambda _config: 0.01)

    state = {
        "query": "请生成 16 周全马训练计划，目标全马3小时30分，每周二周四周六周日训练。",
        "workflow_kind": "plan",
        "intent_type": "plan",
        "subtasks": [{"id": "task-1", "title": "生成计划"}],
        "user_profile": {
            "goal": "全马3:30",
            "weekly_mileage": 50,
            "available_days": ["周二", "周四", "周六", "周日"],
            "experience_level": "中级",
            "max_session_minutes": 150,
        },
        "training_capacity_envelope": build_training_capacity_envelope(
            profile={"weekly_mileage": 50, "available_days": ["周二", "周四", "周六", "周日"]},
            query="请生成 16 周全马训练计划",
        ),
        "ranked_evidence": [],
        "rag_sources": [],
        "evidence_bundle": {"health": {}},
        "token_usage": {},
    }

    output = asyncio.run(executor_node(state, {"configurable": {"executor_llm_timeout_sec": 0.01}}))

    assert output["structured_training_plan"]["plan_meta"]["actual_weeks"] == 16
    assert output["draft_ready"] is True
    assert output["used_fallback"] is True
    assert "TimeoutError" in output["fallback_reason"]
    assert output["needs_nutrition_review"] is True


def test_expert_nodes_emit_role_evidence_trace(monkeypatch):
    async def fake_ai_invoke(prompt, config, token_usage):
        del prompt, config
        return "expert feedback", token_usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    async def fake_get_context(*args, **kwargs):
        del args, kwargs
        return []

    def fake_fallback_role_shard_hits(*, role_key, query, domain_keywords, top_k):
        del query, domain_keywords, top_k
        if role_key != "psychologist":
            return []
        return [
            {
                "source_file": "sport_psychology.url",
                "source_path": "https://example.com/sport-psychology",
                "page": 1,
                "chunk_id": "sport_psychology-1",
                "evidence_domain": "sport_psychology",
                "domain_terms": ["sport_psychology"],
                "text": "sport psychology self-talk imagery goal setting confidence",
                "score": 0.8,
            }
        ]

    monkeypatch.setattr("marathon_qa_assistant.nodes.expert_nodes.ai_invoke", fake_ai_invoke)
    monkeypatch.setattr("marathon_qa_assistant.nodes.expert_nodes.get_context", fake_get_context)
    monkeypatch.setattr("marathon_qa_assistant.nodes.expert_nodes._fallback_role_shard_hits", fake_fallback_role_shard_hits)

    state = {
        "query": "nutrition and mental prep",
        "draft_plan": "16 week marathon plan with long run",
        "final_report": "",
        "user_profile": {"goal": "marathon 3:30", "weekly_mileage": 50},
        "adaptive_feedback": {},
        "evidence_bundle": {
            "evidence_items": [
                {
                    "source_file": "nutrition.pdf",
                    "source_path": "data/domain_docs/nutrition.pdf",
                    "page": 1,
                    "chunk_id": "nutrition-1",
                    "citation_label": "[1]",
                    "evidence_domain": "nutrition",
                    "text": "marathon carbohydrate hydration sodium protein",
                    "score": 0.9,
                }
            ]
        },
        "rag_sources": [],
        "ranked_evidence": [],
        "graph_context": "",
        "wiki_context": "",
        "token_usage": {},
        "expert_evidence_trace": {},
    }

    nutrition_output = asyncio.run(nutritionist_node(state, None))
    state.update(nutrition_output)
    psychology_output = asyncio.run(psychologist_node(state, None))

    nutrition_trace = nutrition_output["expert_evidence_trace"]["nutritionist"]
    psychology_trace = psychology_output["expert_evidence_trace"]["psychologist"]
    assert nutrition_trace["status"] == "verified"
    assert nutrition_trace["evidence_refs"][0]["chunk_id"] == "nutrition-1"
    assert psychology_trace["status"] == "verified"
    assert psychology_trace["evidence_refs"][0]["chunk_id"] == "sport_psychology-1"


def test_nutritionist_retrieves_role_specific_evidence_when_missing(monkeypatch):
    async def fake_ai_invoke(prompt, config, token_usage):
        del prompt, config
        assert "nutrition.pdf" in prompt
        return "nutrition feedback [1]", token_usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    async def fake_get_context(*args, **kwargs):
        del args, kwargs
        return [
            {
                "source_file": "nutrition.pdf",
                "source_path": "data/domain_docs/nutrition.pdf",
                "page": 3,
                "chunk_id": "nutrition-role-1",
                "evidence_domain": "nutrition",
                "domain_terms": ["nutrition", "hydration"],
                "text": "Marathon runners need carbohydrate, fluid, sodium, and protein planning.",
                "score": 0.91,
                "retrieval_mode": "role_shard_jsonl:nutrition",
                "score_breakdown": {"shard": "nutrition"},
            }
        ]

    monkeypatch.setattr("marathon_qa_assistant.nodes.expert_nodes.ai_invoke", fake_ai_invoke)
    monkeypatch.setattr("marathon_qa_assistant.nodes.expert_nodes.get_context", fake_get_context)

    state = {
        "query": "16 week marathon plan",
        "draft_plan": "16 week marathon plan with long run",
        "final_report": "",
        "user_profile": {"goal": "marathon 3:30", "weekly_mileage": 50},
        "adaptive_feedback": {},
        "evidence_bundle": {"evidence_items": []},
        "rag_sources": [],
        "ranked_evidence": [],
        "graph_context": "",
        "wiki_context": "",
        "token_usage": {},
        "expert_evidence_trace": {},
    }

    output = asyncio.run(nutritionist_node(state, None))

    trace = output["expert_evidence_trace"]["nutritionist"]
    assert trace["status"] == "verified"
    assert trace["evidence_refs"][0]["chunk_id"] == "nutrition-role-1"
    assert output["evidence_bundle"]["evidence_items"]
    assert output["role_evidence_queries"]["nutritionist"]


def test_nutritionist_trace_prefers_nutrition_metadata_over_training_text(monkeypatch):
    async def fake_ai_invoke(prompt, config, token_usage):
        del prompt, config
        return "nutrition feedback [2]", token_usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    monkeypatch.setattr("marathon_qa_assistant.nodes.expert_nodes.ai_invoke", fake_ai_invoke)

    state = {
        "query": "16 week marathon plan",
        "draft_plan": "16 week marathon plan with long run",
        "final_report": "",
        "user_profile": {"goal": "marathon 3:30", "weekly_mileage": 50},
        "adaptive_feedback": {},
        "evidence_bundle": {
            "evidence_items": [
                {
                    "source_file": "training_protocol.pdf",
                    "source_path": "data/domain_docs/training_protocol.pdf",
                    "page": 1,
                    "chunk_id": "training-contains-nutrition-words",
                    "citation_label": "[1]",
                    "evidence_domain": "training_protocol",
                    "text": "This training plan mentions carbohydrate, hydration, fluid, and protein in passing.",
                    "score": 0.99,
                },
                {
                    "source_file": "nutrition.pdf",
                    "source_path": "data/domain_docs/nutrition.pdf",
                    "page": 3,
                    "chunk_id": "nutrition-domain-1",
                    "citation_label": "[2]",
                    "evidence_domain": "nutrition",
                    "text": "Marathon nutrition guidance covers carbohydrate, fluid, sodium, and protein planning.",
                    "score": 0.8,
                },
            ]
        },
        "rag_sources": [],
        "ranked_evidence": [],
        "graph_context": "",
        "wiki_context": "",
        "token_usage": {},
        "expert_evidence_trace": {},
    }

    output = asyncio.run(nutritionist_node(state, None))

    trace = output["expert_evidence_trace"]["nutritionist"]
    assert trace["status"] == "verified"
    assert trace["evidence_refs"][0]["chunk_id"] == "nutrition-domain-1"
    assert trace["evidence_refs"][0]["evidence_domain"] == "nutrition"


def test_nutritionist_role_retrieval_prefers_domain_fallback_over_text_only_hits(monkeypatch):
    async def fake_ai_invoke(prompt, config, token_usage):
        del config
        assert "nutrition.pdf" in prompt
        assert "training_protocol.pdf" not in prompt
        return "nutrition feedback [1]", token_usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    async def fake_get_context(*args, **kwargs):
        del args, kwargs
        return [
            {
                "source_file": "training_protocol.pdf",
                "source_path": "data/domain_docs/training_protocol.pdf",
                "page": 1,
                "chunk_id": "training-text-only",
                "evidence_domain": "training_protocol",
                "text": "This training evidence mentions carbohydrate, hydration, fluid, and protein.",
                "score": 0.99,
            }
        ]

    def fake_fallback_role_shard_hits(*, role_key, query, domain_keywords, top_k):
        del query, domain_keywords, top_k
        if role_key != "nutritionist":
            return []
        return [
            {
                "source_file": "nutrition.pdf",
                "source_path": "data/domain_docs/nutrition.pdf",
                "page": 3,
                "chunk_id": "nutrition-role-1",
                "evidence_domain": "nutrition",
                "domain_terms": ["nutrition", "hydration"],
                "text": "Marathon runners need carbohydrate, fluid, sodium, and protein planning.",
                "score": 0.91,
            }
        ]

    monkeypatch.setattr("marathon_qa_assistant.nodes.expert_nodes.ai_invoke", fake_ai_invoke)
    monkeypatch.setattr("marathon_qa_assistant.nodes.expert_nodes.get_context", fake_get_context)
    monkeypatch.setattr("marathon_qa_assistant.nodes.expert_nodes._fallback_role_shard_hits", fake_fallback_role_shard_hits)

    state = {
        "query": "16 week marathon plan",
        "draft_plan": "16 week marathon plan with long run",
        "final_report": "",
        "user_profile": {"goal": "marathon 3:30", "weekly_mileage": 50},
        "adaptive_feedback": {},
        "evidence_bundle": {"evidence_items": []},
        "rag_sources": [],
        "ranked_evidence": [],
        "graph_context": "",
        "wiki_context": "",
        "token_usage": {},
        "expert_evidence_trace": {},
    }

    output = asyncio.run(nutritionist_node(state, None))

    trace = output["expert_evidence_trace"]["nutritionist"]
    assert trace["status"] == "verified"
    assert trace["evidence_refs"]
    assert output["role_evidence_queries"]["nutritionist"]


def test_coach_adds_role_evidence_trace_when_initial_evidence_is_missing(monkeypatch):
    async def fake_get_context(*args, **kwargs):
        del args, kwargs
        return [_expert_trace_hit("coach-role-1", "training_protocol", "marathon training periodization workout threshold interval")]

    monkeypatch.setattr("marathon_qa_assistant.nodes.expert_nodes.ai_invoke", _fake_expert_ai_invoke)
    monkeypatch.setattr("marathon_qa_assistant.nodes.expert_nodes.get_context", fake_get_context)

    output = asyncio.run(coach_node(_expert_trace_base_state("tempo run vs interval run"), None))

    trace = output["expert_evidence_trace"]["coach"]
    assert trace["status"] == "verified"
    assert trace["evidence_refs"][0]["chunk_id"] == "coach-role-1"
    assert output["role_evidence_queries"]["coach"]


def test_adaptive_coach_adds_role_evidence_trace_when_initial_evidence_is_missing(monkeypatch):
    async def fake_get_context(*args, **kwargs):
        del args, kwargs
        return [_expert_trace_hit("adaptive-role-1", "training_protocol", "fatigue recovery deload training load missed workout")]

    monkeypatch.setattr("marathon_qa_assistant.nodes.expert_nodes.ai_invoke", _fake_expert_ai_invoke)
    monkeypatch.setattr("marathon_qa_assistant.nodes.expert_nodes.get_context", fake_get_context)

    state = _expert_trace_base_state("I missed two workouts and feel fatigued")
    state["intent_type"] = "plan"
    output = asyncio.run(adaptive_coach_node(state, None))

    trace = output["expert_evidence_trace"]["adaptive_coach"]
    assert trace["status"] == "verified"
    assert trace["evidence_refs"][0]["chunk_id"] == "adaptive-role-1"
    assert output["role_evidence_queries"]["adaptive_coach"]
    assert output["adaptation_type"] == "FATIGUE"
    assert output["adaptation_context"]["adaptation_type"] == "FATIGUE"


def test_therapist_adds_role_evidence_trace_when_initial_evidence_is_missing(monkeypatch):
    async def fake_get_context(*args, **kwargs):
        del args, kwargs
        return [_expert_trace_hit("therapist-role-1", "injury_safety", "running injury pain rehabilitation medical safety return to run")]

    monkeypatch.setattr("marathon_qa_assistant.nodes.expert_nodes.get_context", fake_get_context)

    output = asyncio.run(therapist_node(_expert_trace_base_state("knee pain after long run"), None))

    trace = output["expert_evidence_trace"]["therapist"]
    assert trace["status"] == "verified"
    assert trace["evidence_refs"][0]["chunk_id"] == "therapist-role-1"
    assert output["role_evidence_queries"]["therapist"]


def test_critic_auditor_rejects_capacity_envelope_violation():
    envelope = build_training_capacity_envelope(
        profile={"weekly_mileage": 30},
        query="请生成训练计划",
    )
    cap = envelope["load_ceiling"]["weekly_load_cap_km"]
    structured_plan = {
        "training_capacity_envelope": envelope,
        "week_plans": [
            {
                "week_index": 1,
                "days": [],
                "repeat_guard_signature": {
                    "weekly_volume_km": cap + 5,
                    "long_run_distance_km": 8,
                    "quality_session_count": 1,
                },
            }
        ],
    }
    state = {
        "workflow_kind": "plan",
        "intent_type": "plan",
        "draft_plan": "测试计划",
        "structured_training_plan": structured_plan,
        "training_capacity_envelope": envelope,
        "evidence_bundle": {"evidence_items": []},
        "iteration_count": 0,
        "token_usage": {},
    }

    output = asyncio.run(rule_checker_node(state, None))

    assert output["rule_check_result"]["passed"] is False
    assert "硬规则检查未通过" in output["review_feedback"]


def test_critic_auditor_counts_only_training_days_for_available_day_contract():
    week_days = [
        {"day": "周一", "training_type": "休息", "main_set": "休息"},
        {"day": "周二", "training_type": "轻松跑", "main_set": "40分钟轻松跑"},
        {"day": "周三", "training_type": "休息", "main_set": "休息"},
        {"day": "周四", "training_type": "节奏跑", "main_set": "25分钟节奏跑"},
        {"day": "周五", "training_type": "休息", "main_set": "休息"},
        {"day": "周六", "training_type": "轻松跑", "main_set": "35分钟轻松跑"},
        {"day": "周日", "training_type": "长距离", "main_set": "12km轻松长距离，配速6:00/km"},
    ]
    structured_plan = {
        "week_plans": [
            {
                "week_index": 1,
                "days": week_days,
                "repeat_guard_signature": {
                    "weekly_volume_km": 40,
                    "long_run_distance_km": 12,
                    "quality_session_count": 1,
                },
            }
        ],
    }
    state = {
        "workflow_kind": "plan",
        "intent_type": "plan",
        "draft_plan": "结构化计划",
        "structured_training_plan": structured_plan,
        "user_profile": {
            "available_days": ["周二", "周四", "周六", "周日"],
            "max_session_minutes": 150,
        },
        "evidence_bundle": {"evidence_items": []},
        "iteration_count": 0,
        "token_usage": {},
    }

    output = asyncio.run(critic_auditor_node(state, None))

    assert output["is_approved"] is True


def test_critic_auditor_does_not_require_therapist_for_missed_adaptive_plan():
    structured_plan = {
        "week_plans": [
            {
                "week_index": 1,
                "days": [
                    {"day": "周二", "training_type": "轻松跑", "main_set": "40分钟轻松跑"},
                    {"day": "周四", "training_type": "节奏跑", "main_set": "20分钟节奏跑"},
                ],
                "repeat_guard_signature": {
                    "weekly_volume_km": 20,
                    "long_run_distance_km": 0,
                    "quality_session_count": 1,
                },
            }
        ],
    }
    state = {
        "workflow_kind": "adaptive",
        "intent_type": "plan",
        "adaptation_type": "MISSED",
        "draft_plan": "漏训后重新规划",
        "structured_training_plan": structured_plan,
        "evidence_bundle": {"evidence_items": []},
        "iteration_count": 0,
        "token_usage": {},
    }

    output = asyncio.run(critic_auditor_node(state, None))

    assert "治疗师节点未执行" not in output["review_feedback"]


def test_safety_out_sanitizes_sensitive_draft_output():
    state = {
        "draft_plan": "内部 token: sk-marathon-2026-secret-key 不应输出",
        "final_report": "",
        "reasoning_log": [],
        "ranked_evidence": [],
        "evidence_bundle": {"evidence_items": []},
        "token_usage": {},
    }

    output = asyncio.run(safety_out_node(state, None))

    assert "sk-marathon-2026-secret-key" not in output["draft_plan"]
    assert "[已脱敏]" in output["draft_plan"]
    assert "输出安全清洗" in "".join(output["reasoning_log"])
    assert "risk_alert" in output
