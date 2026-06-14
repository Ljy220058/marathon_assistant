import asyncio
import pytest

from marathon_qa_assistant.core.evidence_bundle import build_evidence_bundle
from marathon_qa_assistant.core.working_state import build_working_state
from marathon_qa_assistant.nodes.common import format_evidence_lines, format_state_evidence_lines
from marathon_qa_assistant.nodes.expert_nodes import critic_auditor_node, rule_checker_node
from marathon_qa_assistant.nodes.output_nodes import _build_structured_report
from marathon_qa_assistant.nodes.plan_nodes import executor_node, planner_node
from marathon_qa_assistant.nodes.security import security_gate_node


def test_build_working_state_starts_clean_request_state():
    state = build_working_state(
        query="make a half marathon plan",
        user_profile={"goal": "half marathon"},
        history=[{"role": "assistant", "content": "old answer"}],
        kb_health={"ready": True, "source": "test", "chunks_count": 3, "faiss_ready": True},
    )

    assert state["mode"] == "team"
    assert state["workflow_kind"] == ""
    assert state["is_approved"] is False
    assert state["draft_ready"] is False
    assert state["draft_plan"] == ""
    assert state["final_report"] == ""
    assert state["evidence_bundle"]["query"] == "make a half marathon plan"
    assert state["evidence_bundle"]["health"]["kb_ready"] is True
    assert state["rule_check_result"] == {}
    assert state["supervisor_decision"] == ""


def test_evidence_bundle_adds_protocol_rule_for_hmp_plan():
    bundle = build_evidence_bundle(
        query="half marathon plan",
        structured_training_plan={
            "half_marathon_protocol": {"active": True},
            "half_marathon_protocol_validation": {"issues": []},
        },
        health={"ready": True},
    )

    items = bundle["evidence_items"]
    assert items
    assert items[0]["citation_label"] == "[1]"
    assert any(item["tier"] == "protocol_rule" for item in items)


def test_executor_node_does_not_self_approve_without_subtasks():
    state = build_working_state(query="make a plan")
    state["subtasks"] = []

    output = asyncio.run(executor_node(state, None))

    assert "is_approved" not in output
    assert output["structured_training_plan"] is None


def test_planner_node_writes_evidence_trace():
    state = build_working_state(query="make a plan")
    state["evidence_bundle"] = build_evidence_bundle(
        query="make a plan",
        rag_sources=[
            {
                "source_file": "training_protocol.pdf",
                "source_path": "docs/training_protocol.pdf",
                "text": "training load and periodization guidance",
                "page": 2,
                "chunk_id": "tp-1",
                "retrieval_mode": "sharded:training_protocol+rrf",
            }
        ],
        health={"ready": True},
    )

    output = asyncio.run(planner_node(state, None))

    assert output["subtasks"]
    assert output["expert_evidence_trace"]["planner"]["status"] == "verified"
    assert output["expert_evidence_trace"]["planner"]["evidence_refs"]
    assert output["expert_evidence_trace"]["planner"]["evidence_refs"][0]["evidence_domain"] == "training_protocol"


def test_executor_node_writes_evidence_trace(monkeypatch):
    async def fake_ai_invoke(prompt, config, token_usage):
        del prompt, config
        return "## 训练计划草案\n- done", token_usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    monkeypatch.setattr("marathon_qa_assistant.nodes.plan_nodes.ai_invoke", fake_ai_invoke)

    state = build_working_state(query="make a plan")
    state["subtasks"] = [{"id": "task-1", "title": "generate"}]
    state["ranked_evidence"] = [
        {
            "source_file": "training_protocol.pdf",
            "source_path": "docs/training_protocol.pdf",
            "page": 2,
            "chunk_id": "tp-1",
            "citation_label": "[1]",
            "evidence_domain": "training_protocol",
            "text": "training load and periodization guidance",
            "score": 0.9,
            "retrieval_mode": "sharded:training_protocol+rrf",
        }
    ]

    output = asyncio.run(executor_node(state, None))

    assert output["structured_training_plan"] is not None
    assert output["expert_evidence_trace"]["executor"]["status"] == "verified"
    assert output["expert_evidence_trace"]["executor"]["evidence_refs"]
    assert output["expert_evidence_trace"]["executor"]["evidence_refs"][0]["evidence_domain"] == "training_protocol"


def test_security_gate_does_not_write_approval_flag(monkeypatch):
    class BlockAll:
        def check(self, text, input_type="query"):
            return False, "blocked for test"

    from marathon_qa_assistant.nodes import security

    monkeypatch.setattr(security, "input_guard", BlockAll())
    state = build_working_state(query="unsafe")

    output = asyncio.run(security_gate_node(state, None))

    assert output["mode"] == "intercepted"
    assert "is_approved" not in output


def test_critic_auditor_rejects_invalid_citation():
    state = build_working_state(query="qa")
    state["workflow_kind"] = "qa"
    state["draft_plan"] = "This claim cites a missing source [99]."
    state["evidence_bundle"] = build_evidence_bundle(
        query="qa",
        rag_sources=[
            {
                "source_file": "kb.md",
                "source_path": "docs/kb.md",
                "text": "trusted evidence",
                "page": 1,
                "chunk_id": "c1",
            }
        ],
        health={"ready": True},
    )

    output = asyncio.run(critic_auditor_node(state, None))

    assert output["is_approved"] is False
    assert "[99]" in output["audit_scores"]["score_sources"]["invalid_citations"]
    assert output["iteration_count"] == 1


def test_critic_auditor_returns_workflow_error_when_retry_budget_exhausted():
    state = build_working_state(query="qa")
    state["workflow_kind"] = "plan"
    state["draft_plan"] = "This claim cites a missing source [99]."
    state["iteration_count"] = 2
    state["evidence_bundle"] = build_evidence_bundle(
        query="qa",
        rag_sources=[
            {
                "source_file": "kb.md",
                "source_path": "docs/kb.md",
                "text": "trusted evidence",
                "page": 1,
                "chunk_id": "c1",
            }
        ],
        health={"ready": True},
    )

    output = asyncio.run(critic_auditor_node(state, None))

    assert output["workflow_error"]["error_code"] == "AUDIT_RETRY_EXHAUSTED"
    assert output["audit_verdict"] == "fail"


def test_rule_checker_rejects_invalid_citation_before_llm_critic():
    state = build_working_state(query="qa")
    state["workflow_kind"] = "qa"
    state["draft_plan"] = "This claim cites a missing source [99]."
    state["evidence_bundle"] = build_evidence_bundle(
        query="qa",
        rag_sources=[
            {
                "source_file": "kb.md",
                "source_path": "docs/kb.md",
                "text": "trusted evidence",
                "page": 1,
                "chunk_id": "c1",
            }
        ],
        health={"ready": True},
    )

    output = asyncio.run(rule_checker_node(state, None))

    assert output["rule_check_result"]["passed"] is False
    assert "硬规则检查未通过" in output["review_feedback"]


def test_rule_checker_ignores_profile_training_type_preferences_without_explicit_contract():
    state = build_working_state(query="qa", user_profile={"training_types": ["间歇跑", "节奏跑", "长距离"]})
    state["workflow_kind"] = "plan"
    state["draft_plan"] = "This plan already has quality work and long run coverage [1]."
    state["structured_training_plan"] = {
        "week_plans": [
            {
                "week_index": 1,
                "days": [
                    {"day": "Mon", "training_type": "interval"},
                    {"day": "Wed", "training_type": "tempo"},
                    {"day": "Sun", "training_type": "long run"},
                ],
            }
        ]
    }
    state["evidence_bundle"] = build_evidence_bundle(
        query="qa",
        rag_sources=[
            {
                "source_file": "kb.md",
                "source_path": "docs/kb.md",
                "text": "trusted evidence",
                "page": 2,
                "chunk_id": "c2",
            }
        ],
        health={"ready": True},
    )

    output = asyncio.run(rule_checker_node(state, None))

    assert output["rule_check_result"]["passed"] is True
    assert not any("训练类型" in item for item in output["rule_check_result"]["violations"])


def test_rule_checker_does_not_require_source_path_for_graph_hint_or_decision_gate():
    state = build_working_state(query="plan")
    state["workflow_kind"] = "plan"
    state["draft_plan"] = "This draft cites [1]."
    state["structured_training_plan"] = {
        "week_plans": [
            {
                "week_index": 1,
                "days": [
                    {"day": "Mon", "training_type": "easy run"},
                ],
                "repeat_guard_signature": {
                    "weekly_volume_km": 12,
                    "long_run_distance_km": 0,
                    "quality_session_count": 0,
                },
            }
        ]
    }
    state["evidence_bundle"] = build_evidence_bundle(
        query="plan",
        ranked_evidence=[
            {
                "evidence_id": "gate_1",
                "citation_label": "[1]",
                "kind": "graph",
                "display_mode": "needs_evidence",
                "source_file": "sport_psychology_curated_chunks",
                "source_path": "",
                "page": None,
                "chunk_id": "sport_psychology_subgraph_v1",
                "text": "The psychologist role must not modify mileage, intensity, workout type, nutrition, or injury decisions.",
                "evidence_domain": "sports_science_reference",
                "retrieval_mode": "decision_gate",
                "evidence_source_type": "decision_gate",
                "prescription_permission": "blocked_needs_evidence",
                "decision_gate": True,
                "allowed_use": "risk_gate",
            }
        ],
        health={"ready": True},
    )

    output = asyncio.run(rule_checker_node(state, None))

    assert output["rule_check_result"]["passed"] is True
    assert output["rule_check_result"]["violations"] == []


def test_critic_auditor_rejects_hmp_validation_errors():
    state = build_working_state(query="half marathon plan")
    state["workflow_kind"] = "plan"
    state["draft_plan"] = "Draft plan [1]."
    state["structured_training_plan"] = {
        "half_marathon_protocol": {"active": True},
        "half_marathon_protocol_validation": {"errors": [{"code": "too_hard"}]},
    }
    state["evidence_bundle"] = build_evidence_bundle(
        query="half marathon plan",
        structured_training_plan=state["structured_training_plan"],
        health={"ready": True},
    )

    output = asyncio.run(critic_auditor_node(state, None))

    assert output["is_approved"] is False
    assert output["audit_scores"]["score_sources"]["hmp_error_count"] == 1


def test_structured_report_uses_unified_evidence_bundle():
    state = build_working_state(query="qa")
    state["evidence_bundle"] = build_evidence_bundle(
        query="qa",
        rag_sources=[
            {
                "source_file": "kb.md",
                "source_path": "docs/kb.md",
                "text": "trusted evidence",
                "page": 2,
                "chunk_id": "c2",
            }
        ],
        health={"ready": True},
    )

    report = _build_structured_report(state, "answer [1]")

    assert report["evidence_bundle"]["evidence_items"][0]["citation_label"] == "[1]"
    assert report["evidence_base"][0]["citation_label"] == "[1]"
    assert report["evidence_base"][0]["source_path"] == "docs/kb.md"


def test_format_evidence_lines_neutralizes_embedded_source_citations():
    output = format_evidence_lines(
        [
            {
                "source": "paper.pdf",
                "page": 12,
                "snippet": "This paper cites prior work [221] and later work [7].",
            }
        ],
        limit=1,
    )

    assert "[1] paper.pdf P.12" in output
    assert "[221]" not in output
    assert "[7]" not in output
    assert "(221)" in output
    assert "(7)" in output


def test_format_state_evidence_lines_neutralizes_bundle_source_citations():
    bundle = build_evidence_bundle(
        query="plan",
        rag_sources=[
            {
                "source_file": "marathon-review.pdf",
                "source_path": "docs/marathon-review.pdf",
                "page": 5,
                "chunk_id": "c1",
                "text": "Marathon training evidence cites source-local references [235] and [224].",
            }
        ],
        health={"ready": True},
    )

    output = format_state_evidence_lines({"evidence_bundle": bundle}, limit=1)

    assert "[1]" in output
    assert "[235]" not in output
    assert "[224]" not in output
    assert "(235)" in output
    assert "(224)" in output
