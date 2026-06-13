from pathlib import Path

from marathon_qa_assistant.core import app_state, kb_bootstrap


def test_default_kb_candidate_dirs_only_contains_v2_runtime():
    assert kb_bootstrap.default_kb_candidate_dirs() == [app_state.V2_VECTOR_DIR]


def test_bootstrap_knowledge_base_loads_sharded_v2_by_default(monkeypatch, tmp_path):
    vector_root = tmp_path / "vector_kb"
    v2_dir = vector_root / "v2"
    sharded_dir = vector_root / "v2_sharded"
    v2_dir.mkdir(parents=True)
    sharded_dir.mkdir()
    loaded = []
    sharded_loaded = []
    set_calls = []

    monkeypatch.setattr(kb_bootstrap.app_state, "V2_VECTOR_DIR", v2_dir)

    def fake_probe(path):
        if path == v2_dir:
            return {
                "ok": True,
                "source": "v2",
                "vector_dir": str(path),
                "reason": "",
                "chunks_count": 750,
                "faiss_ready": True,
                "index_schema_version": "chunk_schema_v2",
                "metadata_completeness": 1.0,
                "runtime_core_prescription_enabled": True,
            }
        return {"ok": False, "source": "missing", "vector_dir": str(path), "reason": "missing"}

    def fake_load(path):
        loaded.append(path)
        return ([{"chunk_id": "v2"}], "vec", object(), "bm25")

    def fake_load_sharded(path):
        sharded_loaded.append(path)
        return (
            {"training_protocol": object(), "nutrition": object()},
            {"training_protocol": [{"chunk_id": "tp-1"}], "nutrition": [{"chunk_id": "n-1"}]},
            [{"chunk_id": "tp-1"}, {"chunk_id": "n-1"}],
            {"training_protocol": "bm25-training", "nutrition": "bm25-nutrition"},
            "bm25-global",
        )

    def fake_set(chunks, vectorizer, matrix, retrieve_fn, bm25=None, shard_chunks=None):
        set_calls.append(
            {
                "chunks": list(chunks),
                "vectorizer": vectorizer,
                "matrix": matrix,
                "bm25": bm25,
                "shard_chunks": shard_chunks,
            }
        )

    monkeypatch.delenv("MARATHON_SHARDED_RETRIEVAL_ENABLED", raising=False)
    monkeypatch.setattr(kb_bootstrap, "probe_vector_kb_health", fake_probe)
    monkeypatch.setattr(kb_bootstrap, "load_vector_kb", fake_load)
    monkeypatch.setattr(kb_bootstrap, "load_sharded_kb", fake_load_sharded)
    monkeypatch.setattr(kb_bootstrap, "set_kb_data", fake_set)
    monkeypatch.setattr(kb_bootstrap.label_matcher, "warm_up", lambda labels: None)

    report = kb_bootstrap.bootstrap_knowledge_base()

    assert loaded == []
    assert sharded_loaded == [sharded_dir]
    assert report["source"] == "v2_sharded"
    assert report["mode"] == "loaded_sharded"
    assert report["vector_dir"] == str(sharded_dir)
    assert report["index_schema_version"] == "chunk_schema_v2"
    assert report["chunks_count"] == 2
    assert report["faiss_ready"] is True
    assert report["bm25_ready"] is True
    assert set_calls[0]["chunks"] == [{"chunk_id": "tp-1"}, {"chunk_id": "n-1"}]
    assert set_calls[0]["vectorizer"] == "faiss_sharded_vectorizer"
    assert set_calls[0]["shard_chunks"] == {
        "training_protocol": [{"chunk_id": "tp-1"}],
        "nutrition": [{"chunk_id": "n-1"}],
    }


def test_bootstrap_knowledge_base_can_disable_sharded_retrieval(monkeypatch, tmp_path):
    vector_root = tmp_path / "vector_kb"
    v2_dir = vector_root / "v2"
    sharded_dir = vector_root / "v2_sharded"
    v2_dir.mkdir(parents=True)
    sharded_dir.mkdir()
    loaded = []
    sharded_loaded = []
    set_calls = []

    monkeypatch.setattr(kb_bootstrap.app_state, "V2_VECTOR_DIR", v2_dir)

    def fake_probe(path):
        return {
            "ok": path == v2_dir,
            "source": "v2",
            "vector_dir": str(path),
            "reason": "",
            "chunks_count": 750,
            "faiss_ready": True,
            "index_schema_version": "chunk_schema_v2",
            "metadata_completeness": 1.0,
            "runtime_core_prescription_enabled": True,
        }

    def fake_load(path):
        loaded.append(path)
        return ([{"chunk_id": "v2"}], "vec", object(), "bm25")

    def fake_load_sharded(path):
        sharded_loaded.append(path)
        return ({}, {}, [], {}, None)

    def fake_set(chunks, vectorizer, matrix, retrieve_fn, bm25=None, shard_chunks=None):
        set_calls.append({"chunks": list(chunks), "vectorizer": vectorizer, "shard_chunks": shard_chunks})

    monkeypatch.setenv("MARATHON_SHARDED_RETRIEVAL_ENABLED", "0")
    monkeypatch.setattr(kb_bootstrap, "probe_vector_kb_health", fake_probe)
    monkeypatch.setattr(kb_bootstrap, "load_vector_kb", fake_load)
    monkeypatch.setattr(kb_bootstrap, "load_sharded_kb", fake_load_sharded)
    monkeypatch.setattr(kb_bootstrap, "set_kb_data", fake_set)
    monkeypatch.setattr(kb_bootstrap.label_matcher, "warm_up", lambda labels: None)

    report = kb_bootstrap.bootstrap_knowledge_base()

    assert loaded == [v2_dir]
    assert sharded_loaded == []
    assert report["source"] == "v2"
    assert report["mode"] == "loaded"
    assert report["vector_dir"] == str(v2_dir)
    assert set_calls[0]["chunks"] == [{"chunk_id": "v2"}]
    assert set_calls[0]["shard_chunks"] is None


def test_bootstrap_knowledge_base_ignores_runtime_user_and_legacy_candidates(monkeypatch):
    v2_dir = Path("C:/fake/vector_kb/v2")
    loaded = []

    monkeypatch.setenv("MARATHON_SHARDED_RETRIEVAL_ENABLED", "0")
    monkeypatch.setattr(kb_bootstrap.app_state, "V2_VECTOR_DIR", v2_dir)

    def fake_probe(path):
        if path == v2_dir:
            return {
                "ok": True,
                "source": "v2",
                "vector_dir": str(path),
                "chunks_count": 750,
                "faiss_ready": True,
                "index_schema_version": "chunk_schema_v2",
                "metadata_completeness": 1.0,
                "runtime_core_prescription_enabled": True,
            }
        return {"ok": False, "source": "missing", "vector_dir": str(path), "reason": "missing"}

    monkeypatch.setattr(kb_bootstrap, "probe_vector_kb_health", fake_probe)
    monkeypatch.setattr(kb_bootstrap, "load_vector_kb", lambda path: (loaded.append(path) or ([{"chunk_id": "v2"}], "vec", object(), "bm25")))
    monkeypatch.setattr(kb_bootstrap, "set_kb_data", lambda *args, **kwargs: None)

    report = kb_bootstrap.bootstrap_knowledge_base()

    assert loaded == [v2_dir]
    assert report["source"] == "v2"
    assert all(item.get("source") != "runtime_user" for item in report["health_reports"])


def test_bootstrap_knowledge_base_rejects_non_v2_candidates_and_enters_empty_mode(monkeypatch):
    user_dir = Path("C:/fake/vector_kb_user")
    default_dir = Path("C:/fake/vector_kb")
    set_calls = []

    def fake_probe(path):
        raise AssertionError(f"non-v2 path should not be probed: {path}")

    def fake_set(chunks, vectorizer, matrix, retrieve_fn, bm25=None, shard_chunks=None):
        set_calls.append({"chunks": list(chunks), "vectorizer": vectorizer, "matrix": matrix, "bm25": bm25})

    monkeypatch.setattr(kb_bootstrap, "probe_vector_kb_health", fake_probe)
    monkeypatch.setattr(
        kb_bootstrap,
        "load_vector_kb",
        lambda path: (_ for _ in ()).throw(AssertionError(f"non-v2 path should not load: {path}")),
    )
    monkeypatch.setattr(kb_bootstrap, "set_kb_data", fake_set)

    report = kb_bootstrap.bootstrap_knowledge_base([user_dir, default_dir])

    assert report["ok"] is False
    assert report["mode"] == "empty"
    assert report["source"] == "empty"
    assert report["reason"] == ""
    assert report["health_reports"] == []
    assert set_calls[0]["chunks"] == []
    assert set_calls[0]["matrix"] is None


def test_bootstrap_knowledge_base_enters_empty_mode_when_v2_candidate_fails(monkeypatch):
    v2_dir = Path("C:/fake/vector_kb/v2")
    set_calls = []

    def fake_probe(path):
        return {
            "ok": False,
            "source": "v2",
            "vector_dir": str(path),
            "reason": "missing artifacts",
            "chunks_count": 0,
            "faiss_ready": False,
        }

    def fake_set(chunks, vectorizer, matrix, retrieve_fn, bm25=None, shard_chunks=None):
        set_calls.append({"chunks": list(chunks), "vectorizer": vectorizer, "matrix": matrix, "bm25": bm25})

    monkeypatch.setattr(kb_bootstrap, "probe_vector_kb_health", fake_probe)
    monkeypatch.setattr(kb_bootstrap, "load_vector_kb", lambda path: (_ for _ in ()).throw(AssertionError("should not load unhealthy KB")))
    monkeypatch.setattr(kb_bootstrap, "set_kb_data", fake_set)

    report = kb_bootstrap.bootstrap_knowledge_base([v2_dir])

    assert report["ok"] is False
    assert report["mode"] == "empty"
    assert report["source"] == "empty"
    assert report["reason"] == "v2:missing artifacts"
    assert set_calls[0]["chunks"] == []
    assert set_calls[0]["matrix"] is None
