import json
import pickle
from pathlib import Path

import faiss

from marathon_qa_assistant.apps import response_builders
from marathon_qa_assistant.services import knowledge_graph
from marathon_qa_assistant.services import vector_store


def test_save_outputs_rejects_chunks_without_non_empty_text(monkeypatch, tmp_path):
    calls = []

    def fake_from_documents(docs, embeddings):
        calls.append((docs, embeddings))
        raise AssertionError("FAISS.from_documents must not run without valid documents")

    monkeypatch.setattr(vector_store, "get_embeddings", lambda: object())
    monkeypatch.setattr(vector_store.FAISS, "from_documents", fake_from_documents)

    chunks = [
        {
            "chunk_id": "blank-1",
            "source_file": "blank.md",
            "page": 1,
            "text": "   ",
        }
    ]

    try:
        vector_store.save_outputs(tmp_path, chunks, None, None, None)
    except ValueError as exc:
        assert "no non-empty documents" in str(exc)
        assert "blank-1" in str(exc)
    else:
        raise AssertionError("Expected ValueError for chunks without non-empty text")

    assert calls == []


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


def test_probe_vector_kb_health_labels_v2_runtime_source(monkeypatch, tmp_path):
    from marathon_qa_assistant.core import app_state

    v2_dir = tmp_path / "v2"
    _write_vector_dir(v2_dir, [_v2_chunk()])
    monkeypatch.setattr(vector_store, "V2_VECTOR_DIR", v2_dir)
    monkeypatch.setattr(app_state, "V2_VECTOR_DIR", v2_dir)
    monkeypatch.setattr(vector_store, "get_embeddings", lambda: object())
    monkeypatch.setattr(vector_store, "_load_faiss_store", lambda faiss_dir, embeddings: object())

    report = vector_store.probe_vector_kb_health(v2_dir)

    assert report["source"] == "v2"
    assert report["index_schema_version"] == "chunk_schema_v2"


def test_kb_source_label_resolves_repo_v2_directory():
    # Use vector_store's own V2_VECTOR_DIR (imported at module load) to avoid
    # mismatch when test_monorepo_paths reloads app_state with temp paths.
    assert vector_store._kb_source_label(vector_store.V2_VECTOR_DIR) == "v2"


def test_graph_engine_runtime_path_defaults_to_v2_directory():
    from marathon_qa_assistant.core import app_state

    assert knowledge_graph.GRAPH_DATA_PATH == app_state.V2_VECTOR_DIR / "knowledge_graph.json"


def test_graph_runtime_health_disables_graph_fusion_when_graph_source_mismatches_vector_runtime(tmp_path):
    vector_dir = tmp_path / "v2"
    graph_dir = tmp_path / "default"
    fake_engine = knowledge_graph.GraphEngine.__new__(knowledge_graph.GraphEngine)
    fake_engine.GRAPH_DATA_PATH = graph_dir / "knowledge_graph.json"
    fake_engine.nodes = {"node-1": {"label": "tempo"}}

    health = knowledge_graph.graph_runtime_health(
        {
            "source": "v2",
            "vector_dir": str(vector_dir),
            "ready": True,
            "faiss_ready": True,
            "index_schema_version": "chunk_schema_v2",
            "runtime_core_prescription_enabled": True,
        },
        graph_engine_instance=fake_engine,
    )

    assert health["graph_source"] == str(graph_dir.resolve())
    assert health["vector_source"] == "v2"
    assert health["graph_vector_source_aligned"] is False
    assert health["graph_fusion_enabled"] is False
    assert "graph_source_mismatch" in health["reason"]


def test_public_rag_health_exposes_graph_alignment_and_disables_graph_fusion_when_mismatched(monkeypatch):
    monkeypatch.setattr(
        response_builders,
        "graph_runtime_health",
        lambda _health=None: {
            "graph_path": "C:/graph/default/knowledge_graph.json",
            "graph_source": "default",
            "vector_source": "v2",
            "graph_ready": True,
            "graph_vector_source_aligned": False,
            "graph_fusion_enabled": False,
            "reason": "graph_source_mismatch:default!=v2",
        },
    )

    payload = response_builders._public_rag_health(
        {
            "source": "v2",
            "vector_dir": "C:/vector/v2",
            "index_schema_version": "chunk_schema_v2",
            "runtime_core_prescription_enabled": True,
            "chunks_count": 12,
            "faiss_ready": True,
            "ready": True,
        }
    )

    assert payload["graph_source"] == "default"
    assert payload["graph_vector_source_aligned"] is False
    assert payload["graph_fusion_enabled"] is False


def test_load_faiss_store_rejects_untrusted_external_dir(monkeypatch, tmp_path):
    faiss_dir = tmp_path / "external" / "faiss_db"
    faiss_dir.mkdir(parents=True)
    (faiss_dir / "index.faiss").write_bytes(b"fake")
    (faiss_dir / "index.pkl").write_bytes(b"fake")
    calls = []

    def fake_load_local(*args, **kwargs):
        calls.append((args, kwargs))
        return object()

    monkeypatch.setattr(vector_store.FAISS, "load_local", fake_load_local)

    assert vector_store._load_faiss_store(faiss_dir, object()) is None
    assert calls == []


def test_load_faiss_store_allows_configured_vector_dir(monkeypatch, tmp_path):
    vector_dir = tmp_path / "v2"
    _write_vector_dir(vector_dir, [])
    monkeypatch.setattr(vector_store, "V2_VECTOR_DIR", vector_dir)
    calls = []

    def fake_load_local(path, embeddings, allow_dangerous_deserialization=False):
        calls.append((path, allow_dangerous_deserialization))
        return "faiss-store"

    monkeypatch.setattr(vector_store.FAISS, "load_local", fake_load_local)

    assert vector_store._load_faiss_store(vector_dir / "faiss_db", object()) == "faiss-store"
    assert calls
    assert calls[0][1] is True


def test_load_faiss_store_falls_back_to_memory_deserialization_for_trusted_dir(monkeypatch, tmp_path):
    vector_dir = tmp_path / "v2"
    _write_vector_dir(vector_dir, [])
    monkeypatch.setattr(vector_store, "V2_VECTOR_DIR", vector_dir)
    (vector_dir / "faiss_db" / "index.faiss").write_bytes(b"index-bytes")
    with (vector_dir / "faiss_db" / "index.pkl").open("wb") as handle:
        pickle.dump(("docstore", {0: "doc-0"}), handle)

    def fake_load_local(path, embeddings, allow_dangerous_deserialization=False):
        raise RuntimeError("simulated Windows unicode path failure")

    def fake_deserialize_index(index_bytes):
        return f"index:{bytes(index_bytes).decode()}"

    class FakeFaissStore:
        def __init__(self, embedding_function, index, docstore, index_to_docstore_id):
            self.embedding_function = embedding_function
            self.index = index
            self.docstore = docstore
            self.index_to_docstore_id = index_to_docstore_id

    monkeypatch.setattr(vector_store.FAISS, "load_local", fake_load_local)
    monkeypatch.setattr(vector_store.FAISS, "__init__", FakeFaissStore.__init__)
    monkeypatch.setattr(faiss, "deserialize_index", fake_deserialize_index)

    store = vector_store._load_faiss_store(vector_dir / "faiss_db", type("Emb", (), {"embed_query": lambda self, text: []})())

    assert store.index == "index:index-bytes"
    assert store.docstore == "docstore"
    assert store.index_to_docstore_id == {0: "doc-0"}


def test_load_vector_kb_does_not_deserialize_untrusted_external_dir(monkeypatch, tmp_path):
    vector_dir = tmp_path / "external"
    _write_vector_dir(vector_dir, [{"chunk_id": "legacy-1", "source_file": "legacy.pdf", "page": 1, "text": "legacy"}])
    calls = []

    def fake_load_local(*args, **kwargs):
        calls.append((args, kwargs))
        return "should-not-load"

    monkeypatch.setattr(vector_store, "get_embeddings", lambda: object())
    monkeypatch.setattr(vector_store.FAISS, "load_local", fake_load_local)

    chunks, vectorizer, matrix, bm25 = vector_store.load_vector_kb(vector_dir)

    assert chunks
    assert vectorizer == "faiss_vectorizer"
    assert matrix is None
    assert bm25["doc_count"] == 1
    assert calls == []
