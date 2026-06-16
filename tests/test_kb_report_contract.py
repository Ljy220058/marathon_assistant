import os

os.environ.setdefault("GRAPHRAG_API_KEY", "ci_test_token")

from marathon_qa_assistant.apps.response_builders import _query_response_from_state
from marathon_qa_assistant.apps.schemas import QueryRequest
from marathon_qa_assistant.nodes.expert_nodes import QA_REPORT_REQUIRED_SECTIONS


def _assert_required_sections_in_order(report: str) -> None:
    positions = []
    for section in QA_REPORT_REQUIRED_SECTIONS:
        marker = f"## {section}"
        assert marker in report
        positions.append(report.index(marker))
    assert positions == sorted(positions)


def test_query_response_enforces_visible_kb_evidence_section_for_qa_report():
    response = _query_response_from_state(
        {
            "final_report": "## 结论\n轻松跑应保持可交谈强度。",
            "intent_type": "qa",
            "workflow_kind": "team",
            "token_usage": {},
            "audit_scores": {},
            "guided_questions": [],
            "evidence_bundle": {
                "query": "轻松跑应该怎么跑？",
                "evidence_items": [
                    {
                        "evidence_id": "chunk-easy-run",
                        "citation_label": "[1]",
                        "source_file": "easy-run-guide.md",
                        "source_path": "data/knowledge/easy-run-guide.md",
                        "page": 3,
                        "chunk_id": "easy-run-001",
                        "text": "Easy running should remain conversational and low intensity.",
                        "score": 0.87,
                        "tier": "kb_fallback",
                        "prescription_permission": "can_write_core",
                        "display_mode": "verified_source",
                    }
                ],
                "health": {
                    "index_schema_version": "chunk_schema_v2",
                    "runtime_core_prescription_enabled": True,
                },
            },
        },
        QueryRequest(query="轻松跑应该怎么跑？"),
        generation_status="complete",
    )

    _assert_required_sections_in_order(response.report)
    assert "## 知识库可见证据" in response.report
    assert "[1] easy-run-guide.md p.3" in response.report
    assert "Easy running should remain conversational" in response.report


def test_query_response_marks_missing_visible_kb_evidence_for_qa_report():
    response = _query_response_from_state(
        {
            "final_report": "这是一个没有结构化章节的回答。",
            "intent_type": "qa",
            "workflow_kind": "team",
            "token_usage": {},
            "audit_scores": {},
            "guided_questions": [],
            "evidence_bundle": {
                "query": "如何训练跑姿？",
                "evidence_items": [],
                "health": {
                    "index_schema_version": "chunk_schema_v2",
                    "runtime_core_prescription_enabled": True,
                },
            },
        },
        QueryRequest(query="如何训练跑姿？"),
        generation_status="complete",
    )

    _assert_required_sections_in_order(response.report)
    assert "本轮未检索到可展示的本地知识库证据" in response.report


def test_query_response_neutralizes_source_local_citation_numbers_in_visible_evidence():
    response = _query_response_from_state(
        {
            "final_report": "## 结论\n已生成。\n",
            "intent_type": "qa",
            "workflow_kind": "team",
            "token_usage": {},
            "audit_scores": {},
            "guided_questions": [],
            "evidence_bundle": {
                "query": "qa",
                "evidence_items": [
                    {
                        "evidence_id": "chunk-1",
                        "citation_label": "[1]",
                        "source_file": "paper.pdf",
                        "source_path": "docs/paper.pdf",
                        "page": 7,
                        "chunk_id": "p7",
                        "text": "This evidence cites prior work [221] and [224].",
                        "score": 0.8,
                        "tier": "kb_fallback",
                        "prescription_permission": "can_write_core",
                        "display_mode": "verified_source",
                    }
                ],
                "health": {
                    "index_schema_version": "chunk_schema_v2",
                    "runtime_core_prescription_enabled": True,
                },
            },
        },
        QueryRequest(query="qa"),
        generation_status="complete",
    )

    assert "[1] paper.pdf p.7" in response.report
    assert "[221]" not in response.report
    assert "[224]" not in response.report
    assert "(221)" in response.report
    assert "(224)" in response.report
