"""Path contract tests for the marathon assistant monorepo.

Verifies that PROJECT_ROOT, MARATHON_DATA_DIR, vector KB paths, upload
paths, research/artifact paths, and legacy fallbacks resolve correctly
under the current monorepo layout.

These tests validate the path-resolution logic in
``marathon_qa_assistant.core.app_state`` and the actual directory
structure on disk.
"""

from __future__ import annotations

import importlib
from pathlib import Path


def _reload_app_state(monkeypatch, project_root: Path, data_root: Path):
    monkeypatch.setenv("PROJECT_ROOT", str(project_root))
    monkeypatch.setenv("MARATHON_DATA_DIR", str(data_root))
    from marathon_qa_assistant.core import app_state

    return importlib.reload(app_state)


# ---------------------------------------------------------------------------
# PROJECT_ROOT and MARATHON_DATA_DIR
# ---------------------------------------------------------------------------

def test_monorepo_path_contract_uses_data_dir(monkeypatch, tmp_path):
    project_root = tmp_path / "repo"
    data_root = tmp_path / "repo-data"
    project_root.mkdir()

    app_state = _reload_app_state(monkeypatch, project_root, data_root)

    assert app_state.BASE_DIR == project_root.absolute()
    assert app_state.DATA_DIR == data_root.absolute()
    assert app_state.USER_VECTOR_DIR == data_root.absolute() / "vector_kb" / "user"
    assert app_state.UPLOAD_DOCS_DIR == data_root.absolute() / "uploads" / "seed"
    assert app_state.STAI_RUNS_DIR == project_root.absolute() / "artifacts" / "research_runs" / "stai2026"


def test_project_root_env_var(monkeypatch, tmp_path):
    """PROJECT_ROOT env var should override auto-detection reliably."""
    project_root = tmp_path / "real_repo"
    project_root.mkdir()
    (project_root / ".git").mkdir()
    (project_root / "apps").mkdir()

    monkeypatch.setenv("PROJECT_ROOT", str(project_root))
    monkeypatch.setenv("MARATHON_DATA_DIR", str(project_root / "data"))
    from marathon_qa_assistant.core import app_state as s

    reloaded = importlib.reload(s)
    assert reloaded.BASE_DIR == project_root


def test_data_dir_relative_default(monkeypatch, tmp_path):
    """Without MARATHON_DATA_DIR, DATA_DIR defaults to BASE_DIR/data."""
    project_root = tmp_path / "plain_repo"
    project_root.mkdir()
    (project_root / ".git").mkdir()
    (project_root / "apps").mkdir()

    monkeypatch.delenv("MARATHON_DATA_DIR", raising=False)
    monkeypatch.setenv("PROJECT_ROOT", str(project_root))
    from marathon_qa_assistant.core import app_state as s

    reloaded = importlib.reload(s)
    assert reloaded.DATA_DIR == project_root / "data"


# ---------------------------------------------------------------------------
# Vector KB paths
# ---------------------------------------------------------------------------

def test_vector_dir_always_prefers_v2_runtime(monkeypatch, tmp_path):
    project_root = tmp_path / "repo"
    data_root = project_root / "data"
    project_root.mkdir()

    legacy_default = project_root / "vector_kb"
    (legacy_default / "faiss_db").mkdir(parents=True)
    (legacy_default / "chunks.jsonl").write_text("{}", encoding="utf-8")
    (legacy_default / "faiss_db" / "index.faiss").write_text("index", encoding="utf-8")

    app_state = _reload_app_state(monkeypatch, project_root, data_root)

    assert app_state.get_preferred_vector_dir() == data_root / "vector_kb" / "v2"

    new_user = data_root / "vector_kb" / "user"
    (new_user / "faiss_db").mkdir(parents=True)
    (new_user / "chunks.jsonl").write_text("{}", encoding="utf-8")
    (new_user / "faiss_db" / "index.faiss").write_text("index", encoding="utf-8")

    assert app_state.get_preferred_vector_dir() == data_root / "vector_kb" / "v2"


def test_v2_vector_dir_path(monkeypatch, tmp_path):
    project_root = tmp_path / "repo_v2"
    data_root = project_root / "data"
    project_root.mkdir()

    app_state = _reload_app_state(monkeypatch, project_root, data_root)
    assert app_state.V2_VECTOR_DIR == data_root / "vector_kb" / "v2"


# ---------------------------------------------------------------------------
# Research and artifacts paths
# ---------------------------------------------------------------------------

def test_stai_paths(monkeypatch, tmp_path):
    project_root = tmp_path / "research_repo"
    data_root = project_root / "data"
    project_root.mkdir()

    app_state = _reload_app_state(monkeypatch, project_root, data_root)

    assert app_state.RESEARCH_DIR == project_root / "research"
    assert app_state.ARTIFACTS_DIR == project_root / "artifacts"
    assert app_state.STAI_DIR == project_root / "research" / "stai2026"
    assert app_state.STAI_MANUSCRIPT_DIR == project_root / "research" / "stai2026" / "manuscript"
    assert app_state.STAI_BENCHMARK_DIR == project_root / "research" / "stai2026" / "benchmark"
    assert app_state.STAI_ANALYSIS_DIR == project_root / "research" / "stai2026" / "analysis"
    assert (
        app_state.STAI_RUNS_DIR
        == project_root / "artifacts" / "research_runs" / "stai2026"
    )


# ---------------------------------------------------------------------------
# Runtime data paths
# ---------------------------------------------------------------------------

def test_runtime_data_dir(monkeypatch, tmp_path):
    project_root = tmp_path / "rt_repo"
    project_root.mkdir()
    runtime = tmp_path / "runtime_area"
    runtime.mkdir()

    monkeypatch.setenv("PROJECT_ROOT", str(project_root))
    monkeypatch.setenv("MARATHON_RUNTIME_DATA_DIR", str(runtime))
    from marathon_qa_assistant.core import app_state as s

    reloaded = importlib.reload(s)
    assert reloaded.RUNTIME_DATA_DIR == runtime
    assert reloaded.RUNTIME_UPLOAD_DOCS_DIR == runtime / "uploaded_docs"
    assert reloaded.RUNTIME_USER_VECTOR_DIR == runtime / "vector_kb_user"


# ---------------------------------------------------------------------------
# Archived legacy paths
# ---------------------------------------------------------------------------

def test_vector_kb_legacy_fallback_constants_removed(monkeypatch, tmp_path):
    """Legacy vector KB paths should not remain as runtime constants."""
    project_root = tmp_path / "legacy_repo"
    project_root.mkdir()
    data_root = project_root / "data"

    app_state = _reload_app_state(monkeypatch, project_root, data_root)

    assert not hasattr(app_state, "DEFAULT_VECTOR_DIR")
    assert not hasattr(app_state, "LEGACY_DEFAULT_VECTOR_DIR")
    assert not hasattr(app_state, "LEGACY_USER_VECTOR_DIR")
    assert app_state.LEGACY_UPLOAD_DOCS_DIR == project_root / "uploaded_docs"
    assert app_state.LEGACY_STAI_DIR == project_root / "docs" / "paper_project"


def test_user_profile_path(monkeypatch, tmp_path):
    project_root = tmp_path / "profile_repo"
    data_root = project_root / "data"
    project_root.mkdir()

    app_state = _reload_app_state(monkeypatch, project_root, data_root)
    assert app_state.USER_PROFILE_PATH == app_state.RUNTIME_DATA_DIR / "profiles" / "default_user.json"
