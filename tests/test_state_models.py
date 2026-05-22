from marathon_qa_assistant.core.state_models import (
    build_adaptive_adjustment_contract,
    build_execution_status_summary,
    build_feedback_risk_gate,
    build_workflow_trace,
    derive_adaptive_reasons,
    normalize_workout_feedback,
)


def test_normal_feedback_keeps_no_adjustment_contract_stable():
    feedback = normalize_workout_feedback(
        {
            "completion_status": "completed",
            "subjective_fatigue": "low",
            "pain_status": "none",
            "sleep_quality": "good",
        }
    )
    adjustment = build_adaptive_adjustment_contract(feedback)

    assert adjustment["adjustment_required"] is False
    assert adjustment["reason_codes"] == []
    assert "按原计划执行" in adjustment["next_day_adjustment"]


def test_adaptive_reasons_cover_completion_fatigue_pain_and_missed_workout():
    cases = [
        ({"completion_status": "partial", "subjective_fatigue": "mild", "pain_status": "none"}, "mild_fatigue"),
        ({"completion_status": "completed", "subjective_fatigue": "high", "pain_status": "none"}, "high_fatigue"),
        ({"completion_status": "completed", "subjective_fatigue": "low", "pain_status": "risk"}, "pain_risk"),
        ({"completion_status": "missed", "subjective_fatigue": "low", "pain_status": "none"}, "missed_workout"),
    ]

    for payload, expected_code in cases:
        reasons = derive_adaptive_reasons(payload)
        adjustment = build_adaptive_adjustment_contract(payload)

        assert expected_code in [reason["code"] for reason in reasons]
        assert expected_code in adjustment["reason_codes"]
        assert adjustment["adjustment_required"] is True


def test_medical_feedback_blocks_training_adjustment_generation():
    risk_gate = build_feedback_risk_gate(
        {
            "completion_status": "partial",
            "subjective_fatigue": "high",
            "pain_status": "risk",
            "sleep_quality": "poor",
        },
        raw_text="Chest pain, dizzy, possible heat illness.",
    )

    assert risk_gate["status"] == "blocked"
    assert risk_gate["product_status"] == "medical_referral"
    assert risk_gate["adjustment_action"] == "deescalate_or_refuse"
    assert {"chest_pain", "dizziness_or_syncope", "heat_illness"} <= set(risk_gate["triggers"])


def test_chinese_medical_feedback_blocks_training_adjustment_generation():
    risk_gate = build_feedback_risk_gate(
        {
            "completion_status": "partial",
            "subjective_fatigue": "high",
            "pain_status": "risk",
            "sleep_quality": "poor",
        },
        raw_text="训练中胸痛、头晕，疑似热病。",
    )

    assert risk_gate["status"] == "blocked"
    assert risk_gate["product_status"] == "medical_referral"
    assert {"chest_pain", "dizziness_or_syncope", "heat_illness"} <= set(risk_gate["triggers"])


def test_workflow_trace_summarizes_protocol_evidence_and_repairs():
    trace = build_workflow_trace(
        query="make a half marathon plan",
        workflow_kind="plan",
        intent_type="plan",
        status="complete",
        evidence_bundle={
            "query": "make a half marathon plan",
            "health": {"kb_ready": True, "chunks_count": 12, "faiss_ready": True},
            "evidence_items": [
                {
                    "evidence_id": "protocol_half_marathon_hmp",
                    "citation_label": "[1]",
                    "tier": "protocol_rule",
                    "source_path": "docs/half_marathon_hmp_protocol.md",
                }
            ],
        },
        structured_training_plan={
            "half_marathon_protocol": {
                "active": True,
                "selected_archetype": {"archetype_id": "short_build_after_marathon"},
                "capacity_budget": {"quality_session_cap": 1},
            },
            "half_marathon_protocol_validation": {
                "passed": True,
                "issues": [],
                "repair_applied": True,
                "repair_log": [{"constraint_id": "capacity_budget_exceeded"}],
            },
        },
        run_id="trace-test",
    )

    assert trace["trace_version"] == "workflow_trace.v1"
    assert trace["run_id"] == "trace-test"
    assert trace["evidence_state"]["status"] == "ok"
    assert trace["evidence_state"]["tier_counts"]["protocol_rule"] == 1
    assert trace["evidence_state"]["citation_labels"] == ["[1]"]
    assert trace["protocol_state"]["status"] == "passed"
    assert trace["protocol_state"]["selected_archetype"] == "short_build_after_marathon"
    assert "docs/product/half_marathon_hmp_protocol.md" in trace["protocol_state"]["source_docs"]
    assert trace["repair_state"]["repair_applied"] is True
    assert trace["repair_state"]["repair_attempts"] == 1
    assert trace["repair_state"]["repair_log"][0]["constraint_id"] == "capacity_budget_exceeded"


def test_workflow_trace_marks_missing_evidence_and_medical_fail_closed():
    risk_gate = build_feedback_risk_gate(
        {
            "completion_status": "partial",
            "subjective_fatigue": "high",
            "pain_status": "risk",
            "sleep_quality": "poor",
        },
        raw_text="Chest pain and dizzy during the run.",
    )
    trace = build_workflow_trace(
        query="feedback",
        workflow_kind="adaptive",
        intent_type="feedback",
        status="medical_referral",
        evidence_bundle={"health": {"kb_ready": False}, "evidence_items": []},
        risk_gate=risk_gate,
        protocol_recheck={"allowed": False, "violations": risk_gate["triggers"]},
        adaptive_feedback={"reason_codes": ["pain_risk"], "source": "astro_feedback_form"},
        feedback_id="feedback-1",
        feedback_persisted=True,
        run_id="feedback-trace",
    )

    assert trace["evidence_state"]["status"] == "missing_or_partial"
    assert "no_evidence_items" in trace["evidence_state"]["missing_evidence"]
    assert trace["risk_state"]["product_status"] == "medical_referral"
    assert trace["risk_state"]["fail_closed"] is True
    assert trace["feedback_state"]["has_feedback"] is True
    assert trace["feedback_state"]["persisted"] is True
    assert trace["feedback_state"]["feedback_id"] == "feedback-1"


def test_execution_status_summary_counts_feedback_and_prioritizes_risk():
    summary = build_execution_status_summary(
        [
            {
                "id": "event-1",
                "week_no": 1,
                "day_no": 1,
                "scheduled_date": "2026-06-01",
                "workout_type": "easy",
                "latest_feedback": {
                    "completion_status": "completed",
                    "reason_codes": [],
                    "risk_gate": {"status": "passed", "triggers": [], "product_status": "generated"},
                },
            },
            {
                "id": "event-2",
                "week_no": 1,
                "day_no": 2,
                "scheduled_date": "2026-06-02",
                "workout_type": "quality",
                "latest_feedback": {
                    "completion_status": "partial",
                    "reason_codes": ["high_fatigue"],
                    "risk_gate": {
                        "status": "needs_protocol_recheck",
                        "triggers": ["high_fatigue"],
                        "product_status": "partial_generated",
                    },
                },
            },
            {
                "id": "event-3",
                "week_no": 1,
                "day_no": 3,
                "scheduled_date": "2026-06-03",
                "workout_type": "quality",
                "latest_feedback": {
                    "completion_status": "missed",
                    "reason_codes": ["pain_risk"],
                    "risk_gate": {
                        "status": "needs_protocol_recheck",
                        "triggers": ["pain_risk"],
                        "product_status": "risk_refused",
                    },
                },
            },
            {
                "id": "event-4",
                "week_no": 1,
                "day_no": 4,
                "scheduled_date": "2026-06-04",
                "workout_type": "easy",
            },
            {
                "id": "event-5",
                "week_no": 1,
                "day_no": 5,
                "scheduled_date": "2026-06-05",
                "workout_type": "easy",
                "latest_feedback": {
                    "completion_status": "partial",
                    "reason_codes": ["chest_pain"],
                    "risk_gate": {
                        "status": "blocked",
                        "triggers": ["chest_pain"],
                        "product_status": "medical_referral",
                    },
                },
            },
            {
                "id": "event-rest",
                "week_no": 1,
                "day_no": 6,
                "scheduled_date": "2026-06-06",
                "workout_type": "rest",
                "is_rest": True,
            },
        ],
        plan={"actual_weeks": 4},
        today="2026-06-05",
    )

    assert summary["week_start"] == "2026-06-01"
    assert summary["week_end"] == "2026-06-07"
    assert summary["planned_count"] == 5
    assert summary["completed_count"] == 1
    assert summary["partial_count"] == 2
    assert summary["skipped_count"] == 1
    assert summary["missed_feedback_count"] == 1
    assert summary["completion_rate"] == 40
    assert summary["risk_level"] == "medical_referral"
    assert summary["generation_status"] == "medical_referral"
    assert "chest_pain" in summary["risk_reasons"]
    assert summary["risk_rule_source"] == "deterministic_feedback_rules"
    assert "llm_general_knowledge" not in str(summary["risk_reasons"])
    assert "停止训练" in summary["next_training_recommendation"]
    assert "专业医疗评估" in summary["next_training_recommendation"]
    assert "Stop training" not in summary["next_training_recommendation"]
    assert summary["current_week"] == 1
    assert summary["total_weeks"] == 4
    assert summary["cycle_completion_rate"] == 25
    assert summary["completed_weeks"][0]["week_no"] == 1
    assert summary["phase_progress"][0]["phase"] == "base"
