from pathlib import Path

from marathon_qa_assistant.core import app_state
from marathon_qa_assistant.core.kb_bootstrap import bootstrap_knowledge_base, default_kb_candidate_dirs


def test_preferred_vector_dir_is_always_v2_even_when_legacy_has_artifacts(monkeypatch):
    calls = []

    def fake_has_artifacts(path: Path) -> bool:
        calls.append(path)
        return path in {
            app_state.USER_VECTOR_DIR,
            app_state.RUNTIME_USER_VECTOR_DIR,
            app_state.LEGACY_USER_VECTOR_DIR,
            app_state.DEFAULT_VECTOR_DIR,
            app_state.LEGACY_DEFAULT_VECTOR_DIR,
        }

    monkeypatch.setattr(app_state, "has_vector_kb_artifacts", fake_has_artifacts)

    assert app_state.get_preferred_vector_dir() == app_state.V2_VECTOR_DIR
    assert calls == []


def test_default_kb_candidate_dirs_only_contains_v2_runtime_path():
    assert default_kb_candidate_dirs() == [app_state.V2_VECTOR_DIR]


def test_bootstrap_reports_degraded_when_v2_unavailable_without_legacy_fallback(monkeypatch, tmp_path):
    v2_dir = tmp_path / "data" / "vector_kb" / "v2"
    legacy_dir = tmp_path / "vector_kb"

    def fake_probe(path: Path):
        if path == v2_dir:
            return {
                "ok": False,
                "ready": False,
                "source": str(path),
                "reason": "missing chunks.jsonl or faiss index",
                "index_schema_version": "missing",
                "metadata_completeness": 0.0,
                "runtime_core_prescription_enabled": False,
            }
        return {
            "ok": True,
            "ready": True,
            "source": str(path),
            "reason": "legacy should not be checked",
            "index_schema_version": "legacy_chunk_schema",
            "metadata_completeness": 0.2,
            "runtime_core_prescription_enabled": True,
        }

    loaded_paths = []

    def fake_load(path: Path):
        loaded_paths.append(path)
        return ([{"chunk_id": "legacy"}], object(), object(), None)

    monkeypatch.setattr("marathon_qa_assistant.core.kb_bootstrap.probe_vector_kb_health", fake_probe)
    monkeypatch.setattr("marathon_qa_assistant.core.kb_bootstrap.load_vector_kb", fake_load)
    monkeypatch.setattr("marathon_qa_assistant.core.kb_bootstrap.set_kb_data", lambda *args, **kwargs: None)

    report = bootstrap_knowledge_base([v2_dir, legacy_dir])

    assert report["ok"] is False
    assert report["ready"] is False
    assert report["mode"] == "empty"
    assert "missing chunks.jsonl or faiss index" in report["reason"]
    assert loaded_paths == []
    assert all("legacy" not in item.get("index_schema_version", "") for item in report["health_reports"])
