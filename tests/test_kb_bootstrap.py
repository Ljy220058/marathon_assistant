from pathlib import Path

from marathon_qa_assistant.core import kb_bootstrap


def test_bootstrap_knowledge_base_falls_back_from_user_to_default(monkeypatch):
    user_dir = Path("C:/fake/vector_kb_user")
    default_dir = Path("C:/fake/vector_kb")
    loaded = []
    set_calls = []

    def fake_probe(path):
        if path == user_dir:
            return {
                "ok": False,
                "source": "user",
                "vector_dir": str(path),
                "reason": "FAISS 索引不可用",
                "chunks_count": 2,
                "faiss_ready": False,
            }
        return {
            "ok": True,
            "source": "default",
            "vector_dir": str(path),
            "reason": "",
            "chunks_count": 3,
            "faiss_ready": True,
            "index_schema_version": "chunk_schema_v2",
            "metadata_completeness": 1.0,
            "runtime_core_prescription_enabled": True,
        }

    def fake_load(path):
        loaded.append(path)
        return ([{"chunk_id": "c1"}], "vec", object(), "bm25")

    def fake_set(chunks, vectorizer, matrix, retrieve_fn, bm25=None):
        set_calls.append({"chunks": list(chunks), "vectorizer": vectorizer, "matrix": matrix, "bm25": bm25})

    monkeypatch.setattr(kb_bootstrap, "probe_vector_kb_health", fake_probe)
    monkeypatch.setattr(kb_bootstrap, "load_vector_kb", fake_load)
    monkeypatch.setattr(kb_bootstrap, "set_kb_data", fake_set)

    report = kb_bootstrap.bootstrap_knowledge_base([user_dir, default_dir])

    assert report["ok"] is True
    assert report["source"] == "default"
    assert loaded == [default_dir]
    assert set_calls[0]["chunks"] == [{"chunk_id": "c1"}]
    assert report["health_reports"][0]["source"] == "user"
    assert report["index_schema_version"] == "chunk_schema_v2"
    assert report["runtime_core_prescription_enabled"] is True


def test_bootstrap_knowledge_base_enters_empty_mode_when_all_candidates_fail(monkeypatch):
    user_dir = Path("C:/fake/vector_kb_user")
    default_dir = Path("C:/fake/vector_kb")
    set_calls = []

    def fake_probe(path):
        return {
            "ok": False,
            "source": "user" if path == user_dir else "default",
            "vector_dir": str(path),
            "reason": "缺少产物",
            "chunks_count": 0,
            "faiss_ready": False,
        }

    def fake_set(chunks, vectorizer, matrix, retrieve_fn, bm25=None):
        set_calls.append({"chunks": list(chunks), "vectorizer": vectorizer, "matrix": matrix, "bm25": bm25})

    monkeypatch.setattr(kb_bootstrap, "probe_vector_kb_health", fake_probe)
    monkeypatch.setattr(kb_bootstrap, "load_vector_kb", lambda path: (_ for _ in ()).throw(AssertionError("should not load unhealthy KB")))
    monkeypatch.setattr(kb_bootstrap, "set_kb_data", fake_set)

    report = kb_bootstrap.bootstrap_knowledge_base([user_dir, default_dir])

    assert report["ok"] is False
    assert report["mode"] == "empty"
    assert report["source"] == "empty"
    assert "user:缺少产物" in report["reason"]
    assert "default:缺少产物" in report["reason"]
    assert set_calls[0]["chunks"] == []
    assert set_calls[0]["matrix"] is None
