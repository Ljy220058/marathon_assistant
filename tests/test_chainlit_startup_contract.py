import importlib
import sys
from pathlib import Path


root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))


def _reload_chainlit_app():
    sys.modules.pop("marathon_qa_assistant.apps.chainlit_app", None)
    return importlib.import_module("marathon_qa_assistant.apps.chainlit_app")


def _reset_kb_state(module):
    module._KB_READY = False
    module._KB_VECTOR_DIR = None
    module.global_state.chunks = []
    module.global_state.kb_chunks_len = 0
    module.global_state.kb_source = "unknown"
    module.global_state.kb_health_reason = ""


def test_chainlit_app_import_does_not_load_kb(monkeypatch):
    import marathon_qa_assistant.services.vector_store as vector_store

    original = vector_store.load_vector_kb
    calls = []

    def fake_load_vector_kb(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("chainlit_app import should not load knowledge base")

    monkeypatch.setattr(vector_store, "load_vector_kb", fake_load_vector_kb)

    module = _reload_chainlit_app()

    assert calls == []

    monkeypatch.setattr(vector_store, "load_vector_kb", original)
    importlib.reload(module)


def test_ensure_knowledge_base_ready_is_lazy_and_idempotent(monkeypatch):
    module = _reload_chainlit_app()

    load_calls = []
    set_calls = []

    def fake_load_vector_kb(path):
        load_calls.append(str(path))
        return ([{"chunk_id": "c1", "source_file": "demo.pdf"}], "vec", object(), "bm25")

    def fake_set_kb_data(chunks, vectorizer, matrix, retrieve_fn, bm25=None):
        set_calls.append(
            {
                "chunks": list(chunks),
                "vectorizer": vectorizer,
                "matrix": matrix,
                "bm25": bm25,
                "retrieve_fn": retrieve_fn,
            }
        )

    monkeypatch.setattr(module, "load_vector_kb", fake_load_vector_kb)
    monkeypatch.setattr(module, "set_kb_data", fake_set_kb_data)
    monkeypatch.setattr(module, "probe_vector_kb_health", lambda path: {
        "ok": True,
        "vector_dir": str(path),
        "source": "default",
        "reason": "",
        "chunks_count": 1,
        "faiss_ready": True,
    })
    monkeypatch.setattr(module, "_kb_candidate_dirs", lambda: [Path("C:/fake/vector_kb")])

    _reset_kb_state(module)

    assert module.ensure_knowledge_base_ready() is True
    assert module.ensure_knowledge_base_ready() is False
    assert len(load_calls) == 1
    assert len(set_calls) == 1
    assert module.global_state.kb_chunks_len == 1


def test_init_knowledge_base_falls_back_to_default_when_user_kb_unhealthy(monkeypatch):
    module = _reload_chainlit_app()

    user_dir = Path("C:/fake/vector_kb_user")
    default_dir = Path("C:/fake/vector_kb")
    load_calls = []
    set_calls = []

    def fake_probe_vector_kb_health(path):
        if path == user_dir:
            return {
                "ok": False,
                "vector_dir": str(path),
                "source": "user",
                "reason": "FAISS 索引不可用",
                "chunks_count": 12,
                "faiss_ready": False,
            }
        return {
            "ok": True,
            "vector_dir": str(path),
            "source": "default",
            "reason": "",
            "chunks_count": 5,
            "faiss_ready": True,
        }

    def fake_load_vector_kb(path):
        load_calls.append(path)
        return ([{"chunk_id": "c1", "source_file": "default.pdf"}], "vec", object(), "bm25")

    def fake_set_kb_data(chunks, vectorizer, matrix, retrieve_fn, bm25=None):
        set_calls.append(
            {
                "chunks": list(chunks),
                "vectorizer": vectorizer,
                "matrix": matrix,
                "bm25": bm25,
                "retrieve_fn": retrieve_fn,
            }
        )

    monkeypatch.setattr(module, "_kb_candidate_dirs", lambda: [user_dir, default_dir])
    monkeypatch.setattr(module, "probe_vector_kb_health", fake_probe_vector_kb_health)
    monkeypatch.setattr(module, "load_vector_kb", fake_load_vector_kb)
    monkeypatch.setattr(module, "set_kb_data", fake_set_kb_data)

    _reset_kb_state(module)

    assert module.init_knowledge_base() is True
    assert load_calls == [default_dir]
    assert len(set_calls) == 1
    assert module.global_state.kb_chunks_len == 1
    assert module.global_state.kb_source == "default"
    assert module.global_state.kb_health_reason == ""
    assert module._KB_VECTOR_DIR == default_dir


def test_init_knowledge_base_uses_empty_mode_when_all_candidates_unhealthy(monkeypatch):
    module = _reload_chainlit_app()

    user_dir = Path("C:/fake/vector_kb_user")
    default_dir = Path("C:/fake/vector_kb")
    load_calls = []
    set_calls = []

    def fake_probe_vector_kb_health(path):
        return {
            "ok": False,
            "vector_dir": str(path),
            "source": "user" if path == user_dir else "default",
            "reason": "缺少产物: faiss_index",
            "chunks_count": 0,
            "faiss_ready": False,
        }

    def fake_load_vector_kb(path):
        load_calls.append(path)
        raise AssertionError("unhealthy knowledge base should not be loaded")

    def fake_set_kb_data(chunks, vectorizer, matrix, retrieve_fn, bm25=None):
        set_calls.append(
            {
                "chunks": list(chunks),
                "vectorizer": vectorizer,
                "matrix": matrix,
                "bm25": bm25,
                "retrieve_fn": retrieve_fn,
            }
        )

    monkeypatch.setattr(module, "_kb_candidate_dirs", lambda: [user_dir, default_dir])
    monkeypatch.setattr(module, "probe_vector_kb_health", fake_probe_vector_kb_health)
    monkeypatch.setattr(module, "load_vector_kb", fake_load_vector_kb)
    monkeypatch.setattr(module, "set_kb_data", fake_set_kb_data)

    _reset_kb_state(module)

    assert module.init_knowledge_base() is False
    assert load_calls == []
    assert len(set_calls) == 1
    assert set_calls[0]["chunks"] == []
    assert set_calls[0]["matrix"] is None
    assert module.global_state.kb_chunks_len == 0
    assert module.global_state.kb_source == "empty"
    assert "user:缺少产物" in module.global_state.kb_health_reason
    assert "default:缺少产物" in module.global_state.kb_health_reason
