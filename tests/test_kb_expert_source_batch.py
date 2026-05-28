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
    expert_chunk = next(item for item in chunks if item["source_registry_id"] == "src_test_heat_guideline")

    assert report["base_chunk_count"] == 1
    assert report["expert_chunk_count"] == 1
    assert report["total_chunk_count"] == 2
    assert expert_chunk["knowledge_layer"] == "document_index"
    assert expert_chunk["allowed_use"] == "explanation"
    assert expert_chunk["prescription_permission"] == "explanation_only"
    assert expert_chunk["needs_review"] is True
    assert "Heat Safety for Runners" in expert_chunk["text"]
