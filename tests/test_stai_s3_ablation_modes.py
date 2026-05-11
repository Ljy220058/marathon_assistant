from scripts.run_stai_s3_full_workflow import build_no_gate_evidence_gate, skip_repair


def test_no_gate_allows_all_visible_context_chunks():
    contexts = [
        {"chunk_id": "E1", "text": "first evidence"},
        {"chunk_id": "E2", "text": "second evidence"},
    ]

    gate = build_no_gate_evidence_gate(contexts)

    assert gate["gate_status"] == "answerable"
    assert gate["required_chunks"] == ["E1", "E2"]
    assert gate["ablation_mode"] == "no_gate"
    assert gate["missing_evidence"] == []


def test_no_gate_without_contexts_still_refuses_as_unanswerable():
    gate = build_no_gate_evidence_gate([])

    assert gate["gate_status"] == "unanswerable"
    assert gate["required_chunks"] == []
    assert gate["missing_evidence"]


def test_no_repair_keeps_draft_answer_when_audit_requires_repair():
    repair = skip_repair(
        sample={"safety_required": False},
        evidence_gate={"gate_status": "answerable", "required_chunks": ["E1"]},
        risk_gate={"risk_level": "low"},
        draft_answer="这是原始草稿，没有合格引用。",
        audit={"audit_status": "repair_required"},
        invalid_citations=["missing_chunk_id_citation"],
        contexts=[{"chunk_id": "E1", "text": "evidence"}],
    )

    assert repair["final_status"] == "answered"
    assert repair["repair_action"] == "skipped_repair_required"
    assert repair["final_answer"] == "这是原始草稿，没有合格引用。"
    assert repair["unrepaired_invalid_citations"] == ["missing_chunk_id_citation"]


def test_no_repair_preserves_gate_refusal_path():
    repair = skip_repair(
        sample={"safety_required": False},
        evidence_gate={"gate_status": "unanswerable", "required_chunks": []},
        risk_gate={"risk_level": "low"},
        draft_answer="Insufficient retrieved evidence to answer this question.",
        audit={"audit_status": "refuse_required"},
        invalid_citations=[],
        contexts=[],
    )

    assert repair["final_status"] == "refused"
    assert repair["repair_action"] == "gate_refusal_no_repair_ablation"
