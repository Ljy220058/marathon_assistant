from marathon_qa_assistant.core import app_state
from marathon_qa_assistant.core.kb_bootstrap import default_kb_candidate_dirs


def test_runtime_vector_kb_loader_only_targets_v2_even_if_legacy_dirs_exist():
    assert default_kb_candidate_dirs() == [app_state.V2_VECTOR_DIR]
    assert app_state.get_preferred_vector_dir() == app_state.V2_VECTOR_DIR
    assert app_state.DEFAULT_VECTOR_DIR not in default_kb_candidate_dirs()
    assert app_state.USER_VECTOR_DIR not in default_kb_candidate_dirs()
    assert app_state.LEGACY_DEFAULT_VECTOR_DIR not in default_kb_candidate_dirs()


def test_legacy_vector_kb_archive_contains_readme_and_is_outside_runtime_path():
    archive_dir = app_state.BASE_DIR / "archive" / "legacy_vector_kb_20260530"

    assert archive_dir.exists()
    assert archive_dir.joinpath("README.md").exists()
    assert app_state.DATA_DIR not in archive_dir.parents
