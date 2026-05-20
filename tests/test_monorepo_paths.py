import importlib
from pathlib import Path


def _reload_app_state(monkeypatch, project_root: Path, data_root: Path):
    monkeypatch.setenv("PROJECT_ROOT", str(project_root))
    monkeypatch.setenv("MARATHON_DATA_DIR", str(data_root))
    from marathon_qa_assistant.core import app_state

    return importlib.reload(app_state)


def test_monorepo_path_contract_uses_data_dir(monkeypatch, tmp_path):
    project_root = tmp_path / "repo"
    data_root = tmp_path / "repo-data"
    project_root.mkdir()

    app_state = _reload_app_state(monkeypatch, project_root, data_root)

    assert app_state.BASE_DIR == project_root.absolute()
    assert app_state.DATA_DIR == data_root.absolute()
    assert app_state.DEFAULT_VECTOR_DIR == data_root.absolute() / "vector_kb" / "default"
    assert app_state.USER_VECTOR_DIR == data_root.absolute() / "vector_kb" / "user"
    assert app_state.UPLOAD_DOCS_DIR == data_root.absolute() / "uploads" / "seed"
    assert app_state.STAI_RUNS_DIR == project_root.absolute() / "artifacts" / "research_runs" / "stai2026"


def test_vector_dir_prefers_new_user_then_legacy_default(monkeypatch, tmp_path):
    project_root = tmp_path / "repo"
    data_root = project_root / "data"
    project_root.mkdir()

    legacy_default = project_root / "vector_kb"
    (legacy_default / "faiss_db").mkdir(parents=True)
    (legacy_default / "chunks.jsonl").write_text("{}", encoding="utf-8")
    (legacy_default / "faiss_db" / "index.faiss").write_text("index", encoding="utf-8")

    app_state = _reload_app_state(monkeypatch, project_root, data_root)

    assert app_state.get_preferred_vector_dir() == legacy_default

    new_user = data_root / "vector_kb" / "user"
    (new_user / "faiss_db").mkdir(parents=True)
    (new_user / "chunks.jsonl").write_text("{}", encoding="utf-8")
    (new_user / "faiss_db" / "index.faiss").write_text("index", encoding="utf-8")

    assert app_state.get_preferred_vector_dir() == new_user
