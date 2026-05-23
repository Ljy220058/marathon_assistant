from pathlib import Path

from marathon_qa_assistant.core import kb_bootstrap


def test_default_kb_candidate_dirs_prefers_v2_runtime_before_legacy_default():
    dirs = kb_bootstrap.default_kb_candidate_dirs()

    assert kb_bootstrap.V2_VECTOR_DIR in dirs
    assert dirs.index(kb_bootstrap.V2_VECTOR_DIR) < dirs.index(kb_bootstrap.RUNTIME_USER_VECTOR_DIR)
    assert dirs.index(kb_bootstrap.V2_VECTOR_DIR) < dirs.index(kb_bootstrap.DEFAULT_VECTOR_DIR)


def test_bootstrap_knowledge_base_loads_v2_before_default(monkeypatch):
    v2_dir = Path("C:/fake/vector_kb/v2")
    default_dir = Path("C:/fake/vector_kb/default")
    loaded = []
    set_calls = []

    monkeypatch.setattr(kb_bootstrap, "USER_VECTOR_DIR", Path("C:/missing/user"))
    monkeypatch.setattr(kb_bootstrap, "RUNTIME_USER_VECTOR_DIR", Path("C:/missing/runtime-user"))
    monkeypatch.setattr(kb_bootstrap, "LEGACY_USER_VECTOR_DIR", Path("C:/missing/legacy-user"))
    monkeypatch.setattr(kb_bootstrap, "V2_VECTOR_DIR", v2_dir)
    monkeypatch.setattr(kb_bootstrap, "DEFAULT_VECTOR_DIR", default_dir)
    monkeypatch.setattr(kb_bootstrap, "LEGACY_DEFAULT_VECTOR_DIR", Path("C:/missing/legacy-default"))

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
        if path == default_dir:
            return {
                "ok": True,
                "source": "default",
                "vector_dir": str(path),
                "reason": "",
                "chunks_count": 1160,
                "faiss_ready": True,
                "index_schema_version": "legacy",
                "metadata_completeness": 0.0,
                "runtime_core_prescription_enabled": False,
            }
        return {"ok": False, "source": "missing", "vector_dir": str(path), "reason": "missing"}

    def fake_load(path):
        loaded.append(path)
        return ([{"chunk_id": "v2"}], "vec", object(), "bm25")

    def fake_set(chunks, vectorizer, matrix, retrieve_fn, bm25=None):
        set_calls.append({"chunks": list(chunks), "vectorizer": vectorizer, "matrix": matrix, "bm25": bm25})

    monkeypatch.setattr(kb_bootstrap, "probe_vector_kb_health", fake_probe)
    monkeypatch.setattr(kb_bootstrap, "load_vector_kb", fake_load)
    monkeypatch.setattr(kb_bootstrap, "set_kb_data", fake_set)

    report = kb_bootstrap.bootstrap_knowledge_base()

    assert loaded == [v2_dir]
    assert report["source"] == "v2"
    assert report["vector_dir"] == str(v2_dir)
    assert report["index_schema_version"] == "chunk_schema_v2"
    assert report["chunks_count"] == 1
    assert set_calls[0]["chunks"] == [{"chunk_id": "v2"}]


def test_bootstrap_knowledge_base_loads_v2_before_runtime_user_legacy(monkeypatch):
    v2_dir = Path("C:/fake/vector_kb/v2")
    runtime_user_dir = Path("C:/fake/runtime/vector_kb_user")
    loaded = []

    monkeypatch.setattr(kb_bootstrap, "USER_VECTOR_DIR", Path("C:/missing/user"))
    monkeypatch.setattr(kb_bootstrap, "V2_VECTOR_DIR", v2_dir)
    monkeypatch.setattr(kb_bootstrap, "RUNTIME_USER_VECTOR_DIR", runtime_user_dir)
    monkeypatch.setattr(kb_bootstrap, "LEGACY_USER_VECTOR_DIR", Path("C:/missing/legacy-user"))
    monkeypatch.setattr(kb_bootstrap, "DEFAULT_VECTOR_DIR", Path("C:/missing/default"))
    monkeypatch.setattr(kb_bootstrap, "LEGACY_DEFAULT_VECTOR_DIR", Path("C:/missing/legacy-default"))

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
        if path == runtime_user_dir:
            return {
                "ok": True,
                "source": "runtime_user",
                "vector_dir": str(path),
                "chunks_count": 744,
                "faiss_ready": True,
                "index_schema_version": "legacy",
                "metadata_completeness": 0.0,
                "runtime_core_prescription_enabled": False,
            }
        return {"ok": False, "source": "missing", "vector_dir": str(path), "reason": "missing"}

    monkeypatch.setattr(kb_bootstrap, "probe_vector_kb_health", fake_probe)
    monkeypatch.setattr(kb_bootstrap, "load_vector_kb", lambda path: (loaded.append(path) or ([{"chunk_id": "v2"}], "vec", object(), "bm25")))
    monkeypatch.setattr(kb_bootstrap, "set_kb_data", lambda *args, **kwargs: None)

    report = kb_bootstrap.bootstrap_knowledge_base()

    assert loaded == [v2_dir]
    assert report["source"] == "v2"


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
