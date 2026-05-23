import json
from pathlib import Path

from marathon_qa_assistant.services.kb.runtime_v2 import build_v2_runtime_index, load_v2_preview_chunks


def _write_preview(path: Path, chunks: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")


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

    save_calls = []

    def fake_save(out_dir, chunks, vectorizer, matrix, bm25):
        save_calls.append((out_dir, list(chunks), vectorizer, matrix, bm25))
        faiss_dir = out_dir / "faiss_db"
        faiss_dir.mkdir(parents=True)
        (faiss_dir / "index.faiss").write_bytes(b"fake")
        (faiss_dir / "index.pkl").write_bytes(b"fake")
        (out_dir / "chunks.jsonl").write_text("{}", encoding="utf-8")
        return {"chunks_file": str(out_dir / "chunks.jsonl"), "faiss_dir": str(faiss_dir)}

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
