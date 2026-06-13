from pathlib import Path
import json

from marathon_qa_assistant.core.app_state import DATA_DIR
from marathon_qa_assistant.core.evidence_bundle import build_evidence_bundle
from marathon_qa_assistant.services.kb.health import (
    check_chunk_schema_v2_health,
    check_evidence_bindings_health,
    summarize_runtime_index_schema,
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


def test_legacy_chunk_index_is_reported_as_legacy_not_v2():
    result = summarize_legacy_chunk_index(
        [
            {
                "chunk_id": "legacy-1",
                "source_file": "legacy.pdf",
                "page": 1,
                "text": "legacy text",
            }
        ]
    )

    assert result["total"] > 0
    assert result["source_file_count"] >= 1
    assert result["is_legacy_index"] is True
    assert "source_registry_id" not in result["keys"]


def test_runtime_index_schema_summary_distinguishes_legacy_v2_and_mixed_chunks():
    legacy = [{"chunk_id": "legacy-1", "source_file": "legacy.pdf", "page": 1, "text": "legacy"}]
    v2 = {
        "chunk_id": "v2-1",
        "source_registry_id": "src_1",
        "source_file": "source.md",
        "source_url": "https://example.com/source",
        "local_path": "data/knowledge/source.md",
        "page": 1,
        "section": "intro",
        "text": "safe text",
        "language": "en",
        "evidence_domain": "protocol",
        "knowledge_layer": "document_index",
        "domain_pack": "training_protocols",
        "allowed_use": "core_prescription",
        "prescription_permission": "can_write_core",
        "quality_tier": "approved",
    }

    legacy_summary = summarize_runtime_index_schema(legacy)
    v2_summary = summarize_runtime_index_schema([v2])
    mixed_summary = summarize_runtime_index_schema([legacy[0], v2])

    assert legacy_summary["index_schema_version"] == "legacy"
    assert legacy_summary["runtime_core_prescription_enabled"] is False
    assert v2_summary["index_schema_version"] == "chunk_schema_v2"
    assert v2_summary["metadata_completeness"] == 1.0
    assert v2_summary["runtime_core_prescription_enabled"] is True
    assert mixed_summary["index_schema_version"] == "mixed"
    assert mixed_summary["runtime_core_prescription_enabled"] is False


def test_evidence_bundle_normalize_health_preserves_runtime_gate_fields():
    bundle = build_evidence_bundle(
        query="health",
        health={
            "ready": True,
            "source": "v2",
            "chunks_count": 10,
            "faiss_ready": True,
            "index_schema_version": "chunk_schema_v2",
            "metadata_completeness": 0.98,
            "runtime_core_prescription_enabled": False,
            "commercial_core_prescription_enabled": False,
        },
    )

    health = bundle["health"]
    assert health["index_schema_version"] == "chunk_schema_v2"
    assert health["metadata_completeness"] == 0.98
    assert health["runtime_core_prescription_enabled"] is False
    assert health["commercial_core_prescription_enabled"] is False



def test_runtime_v2_manifest_declares_query_preview_runtime_boundary():
    manifest_path = DATA_DIR / "knowledge" / "governance" / "runtime_index_v2_manifest.json"
    chunks_path = DATA_DIR / "vector_kb" / "v2" / "chunks.jsonl"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunks = [
        json.loads(line)
        for line in chunks_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    runtime_chunk_count = len(chunks)
    schema_summary = summarize_runtime_index_schema(chunks)

    assert manifest["status"] == "runtime_preview_ready"
    assert manifest["metadata_completeness"] == schema_summary["metadata_completeness"]
    assert manifest["runtime_index_schema_version"] == schema_summary["index_schema_version"]
    assert manifest["runtime_use_enabled"] is True
    assert manifest["runtime_chunk_count"] == runtime_chunk_count
    assert manifest["runtime_chunk_count"] >= 750
    assert manifest["can_replace_runtime"] is False
    assert manifest["replacement_blockers"]


def test_runtime_v2_index_meta_matches_chunks_and_faiss_index():
    meta_path = DATA_DIR / "vector_kb" / "v2" / "index_meta.json"
    chunks_path = DATA_DIR / "vector_kb" / "v2" / "chunks.jsonl"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    runtime_chunk_count = sum(1 for line in chunks_path.read_text(encoding="utf-8").splitlines() if line.strip())

    assert meta["chunks_count"] == runtime_chunk_count
    assert meta["total_chunks"] == runtime_chunk_count
    assert meta["runtime_chunk_count"] == runtime_chunk_count

    try:
        import faiss
    except Exception:
        faiss = None
    if faiss is not None:
        index = faiss.read_index("data/vector_kb/v2/faiss_db/index.faiss")
        assert meta["faiss_vector_count"] == index.ntotal
        assert meta["embedding_dim"] == index.d
