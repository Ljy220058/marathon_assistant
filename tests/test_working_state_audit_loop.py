import asyncio

from marathon_qa_assistant.core.evidence_bundle import build_evidence_bundle
from marathon_qa_assistant.core.working_state import build_working_state
from marathon_qa_assistant.nodes.expert_nodes import critic_auditor_node
from marathon_qa_assistant.nodes.output_nodes import _build_structured_report
from marathon_qa_assistant.nodes.plan_nodes import executor_node
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
