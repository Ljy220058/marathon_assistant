from marathon_qa_assistant.services.kb.rag_vs_base_eval import summarize_eval_rows


def test_summarize_eval_rows_counts_safety_failures():
    rows = [
        {
            "question_id": "q1",
            "mode": "rag",
            "citation_faithfulness": 1,
            "medical_safety": 1,
            "core_permission_compliance": 1,
        },
        {
            "question_id": "q2",
            "mode": "rag",
            "citation_faithfulness": 0,
            "medical_safety": 1,
            "core_permission_compliance": 0,
        },
    ]

    summary = summarize_eval_rows(rows)

    assert summary["total_rows"] == 2
    assert summary["fake_citation_failures"] == 1
    assert summary["core_permission_failures"] == 1
    assert summary["medical_safety_failures"] == 0
