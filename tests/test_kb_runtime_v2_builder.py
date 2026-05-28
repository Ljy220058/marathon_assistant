import json
from pathlib import Path

import pytest

from marathon_qa_assistant.services.kb.runtime_v2 import build_v2_runtime_index, load_v2_preview_chunks


def _write_preview(path: Path, chunks: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def _v2_chunk(chunk_id: str = "chunk-v2-1", text: str = "approved") -> dict:
    return {
        "chunk_id": chunk_id,
        "source_file": "approved.md",
        "page": 1,
        "text": text,
        "source_registry_id": "src_v2",
        "source_url": "https://example.com/v2",
        "local_path": "knowledge_base/raw_sources/approved.md",
        "section": "intro",
        "language": "en",
        "evidence_domain": "protocol",
        "knowledge_layer": "document_index",
        "domain_pack": "training_protocols",
        "allowed_use": "core_prescription",
        "prescription_permission": "can_write_core",
        "quality_tier": "approved",
    }


def _fake_save_factory(save_calls: list):
    def fake_save(out_dir, chunks, vectorizer, matrix, bm25):
        save_calls.append((out_dir, list(chunks), vectorizer, matrix, bm25))
        faiss_dir = out_dir / "faiss_db"
        faiss_dir.mkdir(parents=True)
        (faiss_dir / "index.faiss").write_bytes(b"fake")
        (faiss_dir / "index.pkl").write_bytes(b"fake")
        (out_dir / "chunks.jsonl").write_text("{}", encoding="utf-8")
        return {"chunks_file": str(out_dir / "chunks.jsonl"), "faiss_dir": str(faiss_dir)}

    return fake_save


def test_load_v2_preview_chunks_reads_jsonl(tmp_path):
    preview = tmp_path / "chunk_schema_v2_preview.jsonl"
    _write_preview(
        preview,
        [
            {
                "chunk_id": "chunk-v2-1",
                "source_file": "approved.md",
                "page": 1,
                "text": "approved",
                "source_registry_id": "src_v2",
                "source_url": "https://example.com/v2",
                "local_path": "knowledge_base/raw_sources/approved.md",
                "section": "intro",
                "language": "en",
                "evidence_domain": "protocol",
                "knowledge_layer": "document_index",
                "domain_pack": "training_protocols",
                "allowed_use": "core_prescription",
                "prescription_permission": "can_write_core",
                "quality_tier": "approved",
            }
        ],
    )

    chunks = load_v2_preview_chunks(preview)

    assert chunks[0]["chunk_id"] == "chunk-v2-1"
    assert chunks[0]["prescription_permission"] == "can_write_core"


def test_build_v2_runtime_index_writes_manifest_and_delegates_save(tmp_path):
    preview = tmp_path / "chunk_schema_v2_preview.jsonl"
    output_dir = tmp_path / "vector_kb" / "v2"
    manifest = tmp_path / "runtime_index_v2_manifest.json"
    _write_preview(preview, [_v2_chunk()])

    save_calls = []
    fake_save = _fake_save_factory(save_calls)

    report = build_v2_runtime_index(
        preview_path=preview,
        output_dir=output_dir,
        manifest_path=manifest,
        save_func=fake_save,
    )

    assert report["ok"] is True
    assert report["current_runtime_vector_dir"] == str(output_dir)
    assert report["runtime_vector_dir"] == str(output_dir)
    assert report["runtime_chunk_count"] == 1
    assert save_calls[0][0] == output_dir
    assert save_calls[0][1][0]["chunk_id"] == "chunk-v2-1"
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_data["status"] == "runtime_preview_ready"
    assert manifest_data["current_runtime_vector_dir"] == str(output_dir)
    assert manifest_data["runtime_index_schema_version"] == "chunk_schema_v2"
    assert manifest_data["can_replace_runtime"] is False


def test_build_v2_runtime_index_uses_release_report_for_source_gate_counts(tmp_path):
    preview = tmp_path / "chunk_schema_v2_preview.jsonl"
    output_dir = tmp_path / "vector_kb" / "v2"
    manifest = tmp_path / "runtime_index_v2_manifest.json"
    release_report = tmp_path / "kb_release_report.json"
    _write_preview(preview, [_v2_chunk()])
    release_report.write_text(
        json.dumps(
            {
                "approved_records": 35,
                "ready_records": 35,
                "commercial_release_ready": False,
                "replacement_blockers": ["domain_pack_coverage_not_ready"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_v2_runtime_index(
        preview_path=preview,
        output_dir=output_dir,
        manifest_path=manifest,
        release_report_path=release_report,
        save_func=_fake_save_factory([]),
    )

    assert report["approved_records"] == 35
    assert report["ready_records"] == 35
    assert report["source_review_ready"] is True
    assert report["can_replace_runtime"] is False
    assert report["replacement_blockers"] == ["domain_pack_coverage_not_ready"]
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_data["approved_records"] == 35
    assert manifest_data["ready_records"] == 35


def test_build_v2_runtime_index_carries_release_diagnostics_but_keeps_replacement_blocked(tmp_path):
    preview = tmp_path / "chunk_schema_v2_preview.jsonl"
    output_dir = tmp_path / "vector_kb" / "v2"
    manifest = tmp_path / "runtime_index_v2_manifest.json"
    release_report = tmp_path / "kb_release_report.json"
    _write_preview(preview, [_v2_chunk()])
    release_report.write_text(
        json.dumps(
            {
                "approved_records": 35,
                "ready_records": 35,
                "commercial_release_ready": False,
                "first_batch_release_ready": True,
                "first_batch_ready_domain_packs": ["training_protocols", "action_library"],
                "readiness_blockers": ["all_domain_packs_still_have_gaps"],
                "domain_gap_summary": {
                    "total_domain_packs": 11,
                    "covered_domain_packs": 2,
                    "domain_packs_with_source_deficits": 9,
                },
                "actionable_domain_gaps": [
                    {
                        "domain_pack": "user_profile_cases",
                        "needed_source_count": 100,
                        "next_action": "collect_privacy_reviewed_user_profile_cases",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_v2_runtime_index(
        preview_path=preview,
        output_dir=output_dir,
        manifest_path=manifest,
        release_report_path=release_report,
        save_func=_fake_save_factory([]),
    )

    assert report["source_review_ready"] is True
    assert report["first_batch_release_ready"] is True
    assert report["can_replace_runtime"] is False
    assert report["replacement_blockers"] == ["all_domain_packs_still_have_gaps"]
    assert report["domain_gap_summary"]["domain_packs_with_source_deficits"] == 9
    assert report["top_actionable_domain_gaps"][0]["domain_pack"] == "user_profile_cases"
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_data["can_replace_runtime"] is False
    assert manifest_data["first_batch_release_ready"] is True


def test_build_v2_runtime_index_filters_blank_text_chunks_before_save(tmp_path):
    preview = tmp_path / "chunk_schema_v2_preview.jsonl"
    output_dir = tmp_path / "vector_kb" / "v2"
    manifest = tmp_path / "runtime_index_v2_manifest.json"
    good_chunk = _v2_chunk(chunk_id="chunk-v2-good", text="approved runtime text")
    blank_chunk = _v2_chunk(chunk_id="chunk-v2-blank", text="   ")
    _write_preview(preview, [good_chunk, blank_chunk])
    save_calls = []

    report = build_v2_runtime_index(
        preview_path=preview,
        output_dir=output_dir,
        manifest_path=manifest,
        save_func=_fake_save_factory(save_calls),
    )

    assert report["ok"] is True
    assert report["preview_chunk_count"] == 2
    assert report["runtime_chunk_count"] == 1
    assert report["skipped_empty_text_chunk_count"] == 1
    assert report["skipped_empty_text_chunk_ids"] == ["chunk-v2-blank"]
    assert save_calls[0][1] == [good_chunk]


def test_build_v2_runtime_index_rejects_preview_with_no_runtime_buildable_text(tmp_path):
    preview = tmp_path / "chunk_schema_v2_preview.jsonl"
    output_dir = tmp_path / "vector_kb" / "v2"
    blank_chunk = _v2_chunk(chunk_id="chunk-v2-blank", text="   ")
    _write_preview(preview, [blank_chunk])

    def fake_save(out_dir, chunks, vectorizer, matrix, bm25):
        raise AssertionError("save_outputs must not run without runtime-buildable text")

    with pytest.raises(ValueError, match="no runtime-buildable v2 chunks") as exc_info:
        build_v2_runtime_index(
            preview_path=preview,
            output_dir=output_dir,
            manifest_path=None,
            save_func=fake_save,
        )

    assert "chunk-v2-blank" in str(exc_info.value)
