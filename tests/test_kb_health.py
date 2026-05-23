from pathlib import Path

from marathon_qa_assistant.services.kb.health import (
    check_chunk_schema_v2_health,
    check_evidence_bindings_health,
    summarize_legacy_chunk_index,
)


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


def test_chunk_schema_v2_health_requires_metadata_and_blocks_absolute_path_leak():
    result = check_chunk_schema_v2_health(
        [
            {
                "chunk_id": "c1",
                "source_registry_id": "src_1",
                "source_file": "source.md",
                "source_url": "https://example.com/source",
                "local_path": "data/knowledge/source.md",
                "page": 1,
                "section": "intro",
                "text": "safe text",
                "language": "en",
                "evidence_domain": "sports_science_reference",
                "knowledge_layer": "document_index",
                "domain_pack": "training_load",
                "allowed_use": "explanation",
                "prescription_permission": "explanation_only",
                "quality_tier": "reviewed",
            },
            {
                "chunk_id": "c2",
                "source_file": "bad.md",
                "source_path": "C:/private/bad.md",
                "page": 0,
                "text": "missing metadata",
                "evidence_domain": "llm_general_knowledge",
                "prescription_permission": "can_write_core",
            },
        ]
    )

    assert result["status"] == "needs_review"
    assert result["metadata_complete_count"] == 1
    assert result["core_permission_violation_count"] == 1
    assert result["absolute_path_leak_count"] == 1


def test_legacy_default_chunk_index_is_reported_as_legacy_not_v2():
    result = summarize_legacy_chunk_index(Path("data/vector_kb/default/chunks.jsonl"))

    assert result["total"] >= 1000
    assert result["source_file_count"] >= 1
    assert result["is_legacy_index"] is True
    assert "source_registry_id" not in result["keys"]
