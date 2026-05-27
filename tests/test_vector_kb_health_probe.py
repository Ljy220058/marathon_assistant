import json
from pathlib import Path

import marathon_qa_assistant.services.vector_store as vector_store


def probe_vector_kb_health(vector_dir: Path) -> dict:
    # conftest 里有历史 fallback；这里强制确认测到的是正式实现。
    if getattr(vector_store.probe_vector_kb_health, "__module__", "") == "tests.conftest":
        raise ImportError("probe_vector_kb_health is still provided by tests.conftest fallback")
    return vector_store.probe_vector_kb_health(vector_dir)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _write_faiss_markers(vector_dir: Path) -> None:
    faiss_dir = vector_dir / "faiss_db"
    faiss_dir.mkdir(parents=True, exist_ok=True)
    (faiss_dir / "index.faiss").write_bytes(b"fake")
    (faiss_dir / "index.pkl").write_bytes(b"fake")


def test_probe_vector_kb_health_reports_missing_chunks(tmp_path):
    result = probe_vector_kb_health(tmp_path / "missing")

    assert result["ok"] is False
    assert result["source"] == "missing"
    assert result["chunks_count"] == 0
    assert result["faiss_ready"] is False
    assert "chunks.jsonl" in result["reason"]


def test_probe_vector_kb_health_reports_legacy_schema(tmp_path):
    vector_dir = tmp_path / "default"
    _write_jsonl(vector_dir / "chunks.jsonl", [{"chunk_id": "c1", "source_file": "a.pdf", "page": 1, "text": "hello"}])
    _write_faiss_markers(vector_dir)

    result = probe_vector_kb_health(vector_dir)

    assert result["ok"] is True
    assert result["source"] == "default"
    assert result["chunks_count"] == 1
    assert result["faiss_ready"] is True
    assert result["index_schema_version"] == "legacy"
    assert result["metadata_completeness"] == 0.0
    assert result["runtime_core_prescription_enabled"] is False


def test_probe_vector_kb_health_reports_v2_schema(tmp_path):
    vector_dir = tmp_path / "v2"
    _write_jsonl(
        vector_dir / "chunks.jsonl",
        [
            {
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
        ],
    )
    _write_faiss_markers(vector_dir)

    result = probe_vector_kb_health(vector_dir)

    assert result["ok"] is True
    assert result["source"] == "v2"
    assert result["chunks_count"] == 1
    assert result["index_schema_version"] == "chunk_schema_v2"
    assert result["metadata_completeness"] == 1.0
    assert result["runtime_core_prescription_enabled"] is True


def test_probe_vector_kb_health_blocks_missing_faiss(tmp_path):
    vector_dir = tmp_path / "v2"
    _write_jsonl(vector_dir / "chunks.jsonl", [{"chunk_id": "c1", "source_file": "a.pdf", "page": 1, "text": "hello"}])

    result = probe_vector_kb_health(vector_dir)

    assert result["ok"] is False
    assert result["chunks_count"] == 1
    assert result["faiss_ready"] is False
    assert "index.faiss" in result["reason"]
