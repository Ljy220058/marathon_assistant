import json
from pathlib import Path

from tools.kb.build_expert_preview_chunks import build_expert_preview_chunks
from tools.kb.register_expert_source_batch import register_expert_source_batch


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _candidate_source(**overrides) -> dict:
    payload = {
        "source_registry_id": "src_test_heat_guideline",
        "title": "Heat Safety for Runners",
        "source_type": "official_guideline",
        "authors_or_owner": "Example Sports Medicine Owner",
        "year": "2026",
        "source_url": "https://example.com/heat-safety",
        "source_file": "expert_heat_safety.url",
        "license_status": "link_only_reviewed",
        "download_status": "metadata_only",
        "evidence_domain": "environment_race_context",
        "knowledge_layer": "source_registry",
        "domain_pack": "environment_race_context",
        "allowed_use": "explanation",
        "prescription_permission": "explanation_only",
        "quality_tier": "candidate",
        "freshness_status": "current",
        "needs_review": True,
        "review_status": "candidate",
        "metadata": {"summary": "Heat illness prevention and safe training adjustments."},
    }
    payload.update(overrides)
    return payload


def test_register_expert_source_batch_keeps_candidates_out_of_runtime(tmp_path):
    existing = tmp_path / "source_registry_v2.jsonl"
    batch = tmp_path / "expert_sources.jsonl"
    registry_out = tmp_path / "source_registry_v2_expert.jsonl"
    queue_out = tmp_path / "source_review_queue_expert.jsonl"
    summary_out = tmp_path / "source_review_summary_expert.json"
    _write_jsonl(existing, [_candidate_source(source_registry_id="src_existing_protocol", title="Existing Protocol")])
    _write_jsonl(batch, [_candidate_source()])

    report = register_expert_source_batch(
        registry_path=existing,
        batch_file=batch,
        registry_out=registry_out,
        queue_out=queue_out,
        summary_out=summary_out,
    )

    merged = [json.loads(line) for line in registry_out.read_text(encoding="utf-8").splitlines() if line.strip()]
    queue = [json.loads(line) for line in queue_out.read_text(encoding="utf-8").splitlines() if line.strip()]
    summary = json.loads(summary_out.read_text(encoding="utf-8"))
    candidate = next(item for item in queue if item["source_registry_id"] == "src_test_heat_guideline")

    assert report["existing_records"] == 1
    assert report["batch_records"] == 1
    assert report["merged_records"] == 2
    assert len(merged) == 2
    assert candidate["review_status"] == "candidate"
    assert candidate["can_enter_runtime_index"] is False
    assert "needs_review" in candidate["blocking_reasons"]
    assert "not_approved" in candidate["blocking_reasons"]
    assert summary["can_enter_runtime_index"] == 0


def test_register_expert_source_batch_rejects_core_permission_outside_protocol_or_action_library(tmp_path):
    existing = tmp_path / "source_registry_v2.jsonl"
    batch = tmp_path / "expert_sources.jsonl"
    _write_jsonl(existing, [])
    _write_jsonl(
        batch,
        [
            _candidate_source(
                evidence_domain="medical_safety",
                domain_pack="medical_risk",
                allowed_use="core_prescription",
                prescription_permission="can_write_core",
                needs_review=False,
                review_status="approved",
            )
        ],
    )

    try:
        register_expert_source_batch(
            registry_path=existing,
            batch_file=batch,
            registry_out=tmp_path / "registry_out.jsonl",
            queue_out=tmp_path / "queue_out.jsonl",
            summary_out=tmp_path / "summary_out.json",
        )
    except ValueError as exc:
        assert "core_permission_domain_violation" in str(exc)
    else:
        raise AssertionError("medical source must not write core prescription")


def test_build_expert_preview_chunks_preserves_permission_boundary(tmp_path):
    base_preview = tmp_path / "chunk_schema_v2_preview.jsonl"
    registry = tmp_path / "source_registry_v2_expert.jsonl"
    preview_out = tmp_path / "chunk_schema_v2_expert_preview.jsonl"
    _write_jsonl(
        base_preview,
        [
            {
                "chunk_id": "base_chunk_1",
                "source_registry_id": "src_base",
                "source_file": "base.md",
                "source_url": "https://example.com/base",
                "local_path": "data/knowledge/base.md",
                "page": 1,
                "section": "base",
                "text": "Base preview text",
                "language": "en",
                "evidence_domain": "sports_science_reference",
                "knowledge_layer": "document_index",
                "domain_pack": "training_protocols",
                "allowed_use": "explanation",
                "prescription_permission": "explanation_only",
                "quality_tier": "approved",
            }
        ],
    )
    _write_jsonl(registry, [_candidate_source()])

    report = build_expert_preview_chunks(
        registry_path=registry,
        base_preview_path=base_preview,
        preview_out=preview_out,
    )

    chunks = [json.loads(line) for line in preview_out.read_text(encoding="utf-8").splitlines() if line.strip()]
    base_chunk = next(item for item in chunks if item["source_registry_id"] == "src_base")
    expert_chunk = next(item for item in chunks if item["source_registry_id"] == "src_test_heat_guideline")

    assert report["base_chunk_count"] == 1
    assert report["expert_chunk_count"] == 1
    assert report["total_chunk_count"] == 2
    assert base_chunk["domain_terms"] == ["training_protocol"]
    assert expert_chunk["domain_terms"] == ["training_protocol"]
    assert expert_chunk["knowledge_layer"] == "document_index"
    assert expert_chunk["allowed_use"] == "explanation"
    assert expert_chunk["prescription_permission"] == "explanation_only"
    assert expert_chunk["needs_review"] is True
    assert "Heat Safety for Runners" in expert_chunk["text"]


def test_build_expert_preview_chunks_refreshes_existing_generated_source(tmp_path):
    base_preview = tmp_path / "chunk_schema_v2_preview.jsonl"
    registry = tmp_path / "source_registry_v2_expert.jsonl"
    preview_out = tmp_path / "chunk_schema_v2_expert_preview.jsonl"
    _write_jsonl(
        base_preview,
        [
            {
                "chunk_id": "chunkv2_src_test_heat_guideline_0001",
                "source_registry_id": "src_test_heat_guideline",
                "source_file": "expert_heat_safety.url",
                "source_url": "https://example.com/heat-safety",
                "local_path": "data/knowledge/expert_heat_safety.url",
                "page": 1,
                "section": "expert_source_registry",
                "text": "Old generated source summary",
                "language": "en",
                "evidence_domain": "environment_race_context",
                "knowledge_layer": "document_index",
                "domain_pack": "environment_race_context",
                "allowed_use": "explanation",
                "prescription_permission": "explanation_only",
                "quality_tier": "candidate",
                "needs_review": True,
                "review_status": "candidate",
            }
        ],
    )
    _write_jsonl(registry, [_candidate_source(metadata={"summary": "Updated bilingual heat safety summary."})])

    report = build_expert_preview_chunks(
        registry_path=registry,
        base_preview_path=base_preview,
        preview_out=preview_out,
    )

    chunks = [json.loads(line) for line in preview_out.read_text(encoding="utf-8").splitlines() if line.strip()]
    expert_chunk = next(item for item in chunks if item["source_registry_id"] == "src_test_heat_guideline")

    assert report["expert_chunk_count"] == 0
    assert report["refreshed_expert_chunk_count"] == 1
    assert expert_chunk["chunk_id"] == "chunkv2_src_test_heat_guideline_0001"
    assert "Updated bilingual heat safety summary" in expert_chunk["text"]


def test_build_expert_preview_chunks_can_split_pdf_candidate_by_paragraph(tmp_path):
    base_preview = tmp_path / "chunk_schema_v2_preview.jsonl"
    registry = tmp_path / "source_registry_v2_expert.jsonl"
    preview_out = tmp_path / "chunk_schema_v2_expert_preview.jsonl"
    pdf_path = tmp_path / "candidate.pdf"
    pdf_path.write_bytes(b"%PDF-1.7 fake test file")
    _write_jsonl(base_preview, [])
    _write_jsonl(
        registry,
        [
            _candidate_source(
                source_registry_id="src_test_pdf_candidate",
                title="Norway Method Candidate",
                source_file="candidate.pdf",
                source_path=str(pdf_path),
                local_path=str(pdf_path),
                evidence_domain="sports_science_reference",
                domain_pack="training_load",
                metadata={
                    "summary": "Threshold training candidate source.",
                    "runtime_chunking": "paragraph",
                },
            )
        ],
    )

    report = build_expert_preview_chunks(
        registry_path=registry,
        base_preview_path=base_preview,
        preview_out=preview_out,
        page_loader=lambda _path: [
            (
                2,
                "第一段讲阈值训练。\n第二段讲强度控制。\n\n第三段讲双阈值训练。",
            )
        ],
    )

    chunks = [json.loads(line) for line in preview_out.read_text(encoding="utf-8").splitlines() if line.strip()]
    paragraph_chunks = [item for item in chunks if item["section"] == "pdf_paragraph_candidate"]

    assert report["expert_chunk_count"] == 4
    assert len(chunks) == 4
    assert len(paragraph_chunks) == 3
    assert [item["page"] for item in paragraph_chunks] == [2, 2, 2]
    assert [item["paragraph_index"] for item in paragraph_chunks] == [1, 2, 3]
    assert all(item["source_registry_id"] == "src_test_pdf_candidate" for item in paragraph_chunks)
    assert all(item["domain_terms"] == ["training_protocol"] for item in paragraph_chunks)
    assert all(item["review_status"] == "candidate" for item in paragraph_chunks)
    assert all(item["prescription_permission"] == "explanation_only" for item in paragraph_chunks)
    assert all(item["exclude_from_training_generation"] is True for item in paragraph_chunks)
    assert "第一段讲阈值训练" in paragraph_chunks[0]["text"]


def test_build_expert_preview_chunks_avoids_duplicate_chunk_ids_for_pdf_candidates(tmp_path):
    base_preview = tmp_path / "chunk_schema_v2_preview.jsonl"
    registry = tmp_path / "source_registry_v2_expert.jsonl"
    preview_out = tmp_path / "chunk_schema_v2_expert_preview.jsonl"
    pdf_path = tmp_path / "candidate.pdf"
    pdf_path.write_bytes(b"%PDF-1.7 fake test file")
    _write_jsonl(
        base_preview,
        [
            {
                "chunk_id": "chunkv2_src_test_pdf_candidate_0003",
                "source_registry_id": "src_test_pdf_candidate",
                "source_file": "candidate.pdf",
                "source_url": "https://example.com/candidate.pdf",
                "local_path": str(pdf_path),
                "page": 1,
                "section": "expert_source_registry",
                "text": "Old generated summary",
                "language": "en",
                "evidence_domain": "sports_science_reference",
                "knowledge_layer": "document_index",
                "domain_pack": "training_load",
                "allowed_use": "explanation",
                "prescription_permission": "explanation_only",
                "quality_tier": "candidate",
                "needs_review": True,
                "review_status": "candidate",
            }
        ],
    )
    _write_jsonl(
        registry,
        [
            _candidate_source(
                source_registry_id="src_test_pdf_candidate",
                title="Norway Method Candidate",
                source_file="candidate.pdf",
                source_path=str(pdf_path),
                local_path=str(pdf_path),
                evidence_domain="sports_science_reference",
                domain_pack="training_load",
                metadata={
                    "summary": "Threshold training candidate source.",
                    "runtime_chunking": "paragraph",
                },
            )
        ],
    )

    build_expert_preview_chunks(
        registry_path=registry,
        base_preview_path=base_preview,
        preview_out=preview_out,
        page_loader=lambda _path: [
            (
                2,
                "First paragraph about threshold training.\n\nSecond paragraph about intensity control.\n\nThird paragraph about 45/15 sessions.",
            )
        ],
    )

    chunks = [json.loads(line) for line in preview_out.read_text(encoding="utf-8").splitlines() if line.strip()]
    chunk_ids = [item["chunk_id"] for item in chunks]
    paragraph_chunks = [item for item in chunks if item["section"] == "pdf_paragraph_candidate"]

    assert len(chunks) == 4
    assert len(chunk_ids) == len(set(chunk_ids))
    assert next(item for item in chunks if item["section"] == "expert_source_registry")["chunk_id"] == "chunkv2_src_test_pdf_candidate_0003"
    assert len(paragraph_chunks) == 3
    assert all(item["chunk_id"] != "chunkv2_src_test_pdf_candidate_0003" for item in paragraph_chunks)


def test_build_expert_preview_chunks_splits_local_markdown_documents_by_default(tmp_path):
    base_preview = tmp_path / "chunk_schema_v2_preview.jsonl"
    registry = tmp_path / "source_registry_v2_expert.jsonl"
    preview_out = tmp_path / "chunk_schema_v2_expert_preview.jsonl"
    markdown_path = tmp_path / "action-library.md"
    markdown_path.write_text(
        "# Warmup Library\n\n"
        "Easy running warmup should prepare joints and breathing.\n\n"
        "- Main sets must keep intensity inside the approved training boundary.\n"
        "- Cooldown helps return the runner to easy effort.",
        encoding="utf-8",
    )
    _write_jsonl(
        base_preview,
        [
            {
                "chunk_id": "chunkv2_src_test_action_library_0007",
                "source_registry_id": "src_test_action_library",
                "source_file": "action-library.md",
                "source_url": "internal://action-library",
                "local_path": str(markdown_path),
                "page": 1,
                "section": "registry_preview",
                "text": "Old registry preview",
                "language": "en",
                "evidence_domain": "action_library",
                "knowledge_layer": "document_index",
                "domain_pack": "action_library",
                "allowed_use": "core_prescription",
                "prescription_permission": "can_write_core",
                "quality_tier": "approved",
                "needs_review": False,
                "review_status": "approved",
            }
        ],
    )
    _write_jsonl(
        registry,
        [
            _candidate_source(
                source_registry_id="src_test_action_library",
                title="Action Library",
                source_file="action-library.md",
                source_path=str(markdown_path),
                local_path=str(markdown_path),
                evidence_domain="action_library",
                domain_pack="action_library",
                allowed_use="core_prescription",
                prescription_permission="can_write_core",
                needs_review=False,
                review_status="approved",
                quality_tier="approved",
                metadata={"summary": "Approved action library source."},
            )
        ],
    )

    report = build_expert_preview_chunks(
        registry_path=registry,
        base_preview_path=base_preview,
        preview_out=preview_out,
    )

    chunks = [json.loads(line) for line in preview_out.read_text(encoding="utf-8").splitlines() if line.strip()]
    paragraph_chunks = [item for item in chunks if item["section"] == "document_paragraph"]

    assert report["paragraph_source_count"] == 1
    assert report["refreshed_expert_chunk_count"] == 1
    assert all(item["section"] != "registry_preview" for item in chunks)
    assert next(item for item in chunks if item["section"] == "expert_source_registry")["chunk_id"] == "chunkv2_src_test_action_library_0007"
    assert len(paragraph_chunks) == 4
    assert all(item["review_status"] == "approved" for item in paragraph_chunks)
    assert all(item["prescription_permission"] == "can_write_core" for item in paragraph_chunks)
    assert all(item["exclude_from_training_generation"] is False for item in paragraph_chunks)


def test_build_expert_preview_chunks_leaves_url_only_sources_as_summaries(tmp_path):
    base_preview = tmp_path / "chunk_schema_v2_preview.jsonl"
    registry = tmp_path / "source_registry_v2_expert.jsonl"
    preview_out = tmp_path / "chunk_schema_v2_expert_preview.jsonl"
    _write_jsonl(base_preview, [])
    _write_jsonl(registry, [_candidate_source()])

    report = build_expert_preview_chunks(
        registry_path=registry,
        base_preview_path=base_preview,
        preview_out=preview_out,
    )

    chunks = [json.loads(line) for line in preview_out.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert report["paragraph_source_count"] == 0
    assert len(chunks) == 1
    assert chunks[0]["section"] == "expert_source_registry"
