from pathlib import Path

from marathon_qa_assistant.core import app_state
from marathon_qa_assistant.core.kb_bootstrap import default_kb_candidate_dirs


def test_runtime_vector_kb_loader_only_targets_v2_even_if_legacy_dirs_exist():
    assert default_kb_candidate_dirs() == [app_state.V2_VECTOR_DIR]
    assert app_state.get_preferred_vector_dir() == app_state.V2_VECTOR_DIR
    assert app_state.USER_VECTOR_DIR not in default_kb_candidate_dirs()
    assert not hasattr(app_state, "DEFAULT_VECTOR_DIR")
    assert not hasattr(app_state, "LEGACY_DEFAULT_VECTOR_DIR")


def test_legacy_vector_kb_archive_contains_readme_and_is_outside_runtime_path():
    repo_root = Path(__file__).parents[1]
    archive_dir = repo_root / "back" / "legacy_kb_archive_20260613"

    assert archive_dir.exists()
    assert archive_dir.joinpath("README.md").exists()
    assert repo_root / "data" not in archive_dir.parents
    assert archive_dir.joinpath("data", "vector_kb", "default").exists()
    assert archive_dir.joinpath("data", "vector_kb", "v2_sharded_clean").exists()
