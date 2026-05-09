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

    bootstrap_calls = []

    def fake_bootstrap(candidate_dirs=None):
        bootstrap_calls.append(list(candidate_dirs or []))
        return {
            "ok": True,
            "vector_dir": "C:/fake/vector_kb",
            "source": "default",
            "reason": "",
            "chunks_count": 1,
        }

    monkeypatch.setattr(module, "bootstrap_knowledge_base", fake_bootstrap)
    monkeypatch.setattr(module, "get_knowledge_base_health_snapshot", lambda: {
        "ok": True,
        "source": "default",
        "reason": "",
        "chunks_count": 1,
    })
    monkeypatch.setattr(module, "get_kb_runtime_state", lambda: {"chunks": [{"chunk_id": "c1", "source_file": "demo.pdf"}]})
    monkeypatch.setattr(module, "_kb_candidate_dirs", lambda: [Path("C:/fake/vector_kb")])

    _reset_kb_state(module)

    assert module.ensure_knowledge_base_ready() is True
    assert module.ensure_knowledge_base_ready() is False
    assert len(bootstrap_calls) == 1
    assert module.global_state.kb_chunks_len == 1


def test_init_knowledge_base_falls_back_to_default_when_user_kb_unhealthy(monkeypatch):
    module = _reload_chainlit_app()

    user_dir = Path("C:/fake/vector_kb_user")
    default_dir = Path("C:/fake/vector_kb")

    bootstrap_calls = []

    def fake_bootstrap(candidate_dirs=None):
        bootstrap_calls.append(list(candidate_dirs or []))
        return {
            "ok": True,
            "vector_dir": str(default_dir),
            "source": "default",
            "reason": "",
            "chunks_count": 1,
        }

    monkeypatch.setattr(module, "_kb_candidate_dirs", lambda: [user_dir, default_dir])
    monkeypatch.setattr(module, "bootstrap_knowledge_base", fake_bootstrap)
    monkeypatch.setattr(module, "get_knowledge_base_health_snapshot", lambda: {
        "ok": True,
        "source": "default",
        "reason": "",
        "chunks_count": 1,
    })
    monkeypatch.setattr(module, "get_kb_runtime_state", lambda: {"chunks": [{"chunk_id": "c1", "source_file": "default.pdf"}]})

    _reset_kb_state(module)

    assert module.init_knowledge_base() is True
    assert bootstrap_calls == [[user_dir, default_dir]]
    assert module.global_state.kb_chunks_len == 1
    assert module.global_state.kb_source == "default"
    assert module.global_state.kb_health_reason == ""
    assert module._KB_VECTOR_DIR == default_dir


def test_init_knowledge_base_uses_empty_mode_when_all_candidates_unhealthy(monkeypatch):
    module = _reload_chainlit_app()

    user_dir = Path("C:/fake/vector_kb_user")
    default_dir = Path("C:/fake/vector_kb")

    monkeypatch.setattr(module, "_kb_candidate_dirs", lambda: [user_dir, default_dir])
    monkeypatch.setattr(module, "bootstrap_knowledge_base", lambda candidate_dirs=None: {
        "ok": False,
        "vector_dir": "",
        "source": "empty",
        "reason": "user:缺少产物: faiss_index; default:缺少产物: faiss_index",
        "chunks_count": 0,
    })
    monkeypatch.setattr(module, "get_knowledge_base_health_snapshot", lambda: {
        "ok": False,
        "source": "empty",
        "reason": "user:缺少产物: faiss_index; default:缺少产物: faiss_index",
        "chunks_count": 0,
    })
    monkeypatch.setattr(module, "get_kb_runtime_state", lambda: {"chunks": []})

    _reset_kb_state(module)

    assert module.init_knowledge_base() is False
    assert module.global_state.kb_chunks_len == 0
    assert module.global_state.kb_source == "empty"
    assert "user:缺少产物" in module.global_state.kb_health_reason
    assert "default:缺少产物" in module.global_state.kb_health_reason
