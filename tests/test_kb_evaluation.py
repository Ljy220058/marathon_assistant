import json
from pathlib import Path

from marathon_qa_assistant.services.kb.evaluation import evaluate_evidence_answer


def test_evaluation_marks_missing_context_and_core_evidence():
    result = evaluate_evidence_answer(
        question="How should I adjust training after pain?",
        answer="Continue high intensity intervals.",
        evidence_bindings=[],
        core_fields={"main_set": "Continue high intensity intervals."},
    )

    assert result["retrieval_hit"] is False
    assert result["source_coverage"] == 0.0
    assert result["needs_review"] is True
    assert result["core_prescription_supported"] is False
    assert result["failure_modes"] == ["retrieval_miss", "core_prescription_missing_evidence"]


def test_evaluation_accepts_action_library_core_field():
    result = evaluate_evidence_answer(
        question="How should I schedule an easy run today?",
        answer="Run 40 minutes easy.",
        evidence_bindings=[
            {
                "evidence_domain": "action_library",
                "prescription_permission": "can_write_core",
                "snippet": "Easy runs are scheduled for 30-60 minutes.",
            }
        ],
        core_fields={"main_set": "Run 40 minutes easy."},
    )

    assert result["retrieval_hit"] is True
    assert result["core_prescription_supported"] is True
    assert result["needs_review"] is False
    assert result["failure_modes"] == []


def test_evaluation_distinguishes_unsupported_answer_from_retrieval_miss():
    result = evaluate_evidence_answer(
        question="What recovery work is supported?",
        answer="Do maximal hill sprints.",
        evidence_bindings=[
            {
                "evidence_domain": "sports_science_reference",
                "prescription_permission": "explanation_only",
                "snippet": "Recovery work should reduce load after pain.",
            }
        ],
        core_fields={},
    )

    assert result["retrieval_hit"] is True
    assert result["faithfulness_proxy"] == 0.0
    assert result["needs_review"] is True
    assert result["failure_modes"] == ["answer_unsupported"]


def test_kb_golden_questions_cover_required_domains():
    questions = json.loads(Path("tests/fixtures/kb_golden_questions.json").read_text(encoding="utf-8"))
    domains = {item["domain"] for item in questions}

    assert len(questions) >= 10
    assert {
        "training_load",
        "plan_structure",
        "periodization",
        "injury_recovery",
        "rehabilitation",
        "strength_conditioning",
        "mobility_recovery",
        "injury_prevention",
        "evidence_control",
        "rag_vs_base_model",
    }.issubset(domains)
