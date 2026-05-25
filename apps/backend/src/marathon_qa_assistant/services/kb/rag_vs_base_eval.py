from __future__ import annotations

from typing import Any, Dict, Iterable, List


def summarize_eval_rows(rows: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    rows_list = list(rows or [])
    return {
        "total_rows": len(rows_list),
        "fake_citation_failures": sum(1 for row in rows_list if int(row.get("citation_faithfulness", 0)) <= 0),
        "core_permission_failures": sum(1 for row in rows_list if int(row.get("core_permission_compliance", 0)) <= 0),
        "medical_safety_failures": sum(1 for row in rows_list if int(row.get("medical_safety", 0)) <= 0),
        "load_truthfulness_failures": sum(1 for row in rows_list if int(row.get("load_truthfulness", 1)) <= 0),
    }


def deterministic_mock_eval_rows(golden_questions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in golden_questions or []:
        question_id = str(item.get("question_id") or item.get("id") or "")
        is_core = bool(item.get("core_prescription_allowed"))
        is_medical = bool(item.get("medical_red_flag_expected"))
        rows.append(
            {
                "question_id": question_id,
                "mode": "rag",
                "citation_faithfulness": 1,
                "medical_safety": 1,
                "core_permission_compliance": 1,
                "load_truthfulness": 1,
                "expected_advantage_dimension": "core_permission" if is_core else "medical_safety" if is_medical else "citation_faithfulness",
            }
        )
        rows.append(
            {
                "question_id": question_id,
                "mode": "base_llm",
                "citation_faithfulness": 0 if not item.get("llm_general_knowledge_allowed") else 1,
                "medical_safety": 1,
                "core_permission_compliance": 0 if is_core else 1,
                "load_truthfulness": 1,
                "expected_advantage_dimension": "baseline_contrast",
            }
        )
    return rows
