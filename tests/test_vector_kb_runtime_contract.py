import json
from pathlib import Path

from marathon_qa_assistant.services import vector_store


def _write_vector_dir(path: Path, chunks: list[dict]) -> None:
    faiss_dir = path / "faiss_db"
    faiss_dir.mkdir(parents=True)
    (faiss_dir / "index.faiss").write_bytes(b"fake")
    (faiss_dir / "index.pkl").write_bytes(b"fake")
    with (path / "chunks.jsonl").open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def _v2_chunk() -> dict:
    return {
        "chunk_id": "chunk-v2-1",
        "source_registry_id": "src_protocol_approved",
        "source_file": "approved-protocol.md",
        "source_url": "https://example.com/approved-protocol",
        "local_path": "data/knowledge/approved-protocol.md",
        "page": 1,
        "section": "intro",
        "text": "Approved protocol text.",
        "language": "en",
        "evidence_domain": "protocol",
        "knowledge_layer": "document_index",
        "domain_pack": "training_protocols",
        "allowed_use": "core_prescription",
        "prescription_permission": "can_write_core",
        "quality_tier": "approved",
    }


def test_probe_vector_kb_health_marks_legacy_index_without_core_permission(monkeypatch, tmp_path):
    _write_vector_dir(tmp_path, [{"chunk_id": "legacy-1", "source_file": "legacy.pdf", "page": 1, "text": "legacy"}])
    monkeypatch.setattr(vector_store, "get_embeddings", lambda: object())
    monkeypatch.setattr(vector_store, "_load_faiss_store", lambda faiss_dir, embeddings: object())

    report = vector_store.probe_vector_kb_health(tmp_path)

    assert report["ok"] is True
    assert report["index_schema_version"] == "legacy"
    assert report["metadata_completeness"] == 0.0
    assert report["runtime_core_prescription_enabled"] is False


def test_probe_vector_kb_health_marks_v2_index_core_permission_ready(monkeypatch, tmp_path):
    _write_vector_dir(tmp_path, [_v2_chunk()])
    monkeypatch.setattr(vector_store, "get_embeddings", lambda: object())
    monkeypatch.setattr(vector_store, "_load_faiss_store", lambda faiss_dir, embeddings: object())

    report = vector_store.probe_vector_kb_health(tmp_path)

    assert report["ok"] is True
    assert report["index_schema_version"] == "chunk_schema_v2"
    assert report["metadata_completeness"] == 1.0
    assert report["runtime_core_prescription_enabled"] is True
