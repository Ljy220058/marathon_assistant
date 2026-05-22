from marathon_qa_assistant.services.kb.health import check_evidence_bindings_health


def test_health_check_flags_missing_sources_and_pages():
    result = check_evidence_bindings_health(
        [
            {"source_path": "", "source_file": "", "page": None, "evidence_domain": "protocol"},
            {
                "source_path": "docs/kb/action_library.pdf",
                "source_file": "action_library.pdf",
                "page": 3,
                "evidence_domain": "action_library",
                "prescription_permission": "can_write_core",
            },
        ]
    )

    assert result["total"] == 2
    assert result["missing_source_count"] == 1
    assert result["missing_page_count"] == 1
    assert result["status"] == "needs_review"


def test_health_check_flags_core_permission_violations():
    result = check_evidence_bindings_health(
        [
            {
                "source_path": "docs/kb/wiki.md",
                "source_file": "wiki.md",
                "page": None,
                "evidence_domain": "llm_general_knowledge",
                "prescription_permission": "can_write_core",
            }
        ]
    )

    assert result["core_permission_violation_count"] == 1
    assert result["status"] == "needs_review"


def test_health_check_reports_empty_kb():
    result = check_evidence_bindings_health([])

    assert result["status"] == "empty"
    assert result["total"] == 0
