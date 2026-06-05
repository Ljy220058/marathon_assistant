from pathlib import Path

from marathon_qa_assistant.core import kb_bootstrap
from marathon_qa_assistant.core import app_state


def test_default_kb_candidate_dirs_only_contains_v2_runtime():
    assert kb_bootstrap.default_kb_candidate_dirs() == [app_state.V2_VECTOR_DIR]


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

    monkeypatch.setenv("GRAPHRAG_API_KEY", "ci_test_token")
    warm_calls = []

    monkeypatch.setattr(kb_bootstrap, "probe_vector_kb_health", fake_probe)
    monkeypatch.setattr(kb_bootstrap, "load_vector_kb", fake_load)
    monkeypatch.setattr(kb_bootstrap, "set_kb_data", fake_set)
    monkeypatch.setattr(kb_bootstrap.label_matcher, "warm_up", lambda labels: warm_calls.append(list(labels)))

    report = kb_bootstrap.bootstrap_knowledge_base()

    assert loaded == [v2_dir]
    assert report["source"] == "v2"
    assert report["vector_dir"] == str(v2_dir)
    assert report["index_schema_version"] == "chunk_schema_v2"
    assert report["chunks_count"] == 1
    assert set_calls[0]["chunks"] == [{"chunk_id": "v2"}]
    assert warm_calls
    assert "轻松跑" in warm_calls[0]
    assert "高强度间歇" in warm_calls[0]


def test_bootstrap_knowledge_base_ignores_runtime_user_and_legacy_candidates(monkeypatch):
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
    assert all(item.get("source") != "runtime_user" for item in report["health_reports"])


def test_bootstrap_knowledge_base_rejects_non_v2_candidates_and_enters_empty_mode(monkeypatch):
    user_dir = Path("C:/fake/vector_kb_user")
    default_dir = Path("C:/fake/vector_kb")
    set_calls = []

    def fake_probe(path):
        raise AssertionError(f"non-v2 path should not be probed: {path}")

    def fake_set(chunks, vectorizer, matrix, retrieve_fn, bm25=None):
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
            "reason": "缺少产物",
            "chunks_count": 0,
            "faiss_ready": False,
        }

    def fake_set(chunks, vectorizer, matrix, retrieve_fn, bm25=None):
        set_calls.append({"chunks": list(chunks), "vectorizer": vectorizer, "matrix": matrix, "bm25": bm25})

    monkeypatch.setattr(kb_bootstrap, "probe_vector_kb_health", fake_probe)
    monkeypatch.setattr(kb_bootstrap, "load_vector_kb", lambda path: (_ for _ in ()).throw(AssertionError("should not load unhealthy KB")))
    monkeypatch.setattr(kb_bootstrap, "set_kb_data", fake_set)

    report = kb_bootstrap.bootstrap_knowledge_base([v2_dir])

    assert report["ok"] is False
    assert report["mode"] == "empty"
    assert report["source"] == "empty"
    assert report["reason"] == "v2:缺少产物"
    assert set_calls[0]["chunks"] == []
    assert set_calls[0]["matrix"] is None
