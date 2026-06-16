import re
import sys
from pathlib import Path

import tomllib


root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_backend_pyproject_declares_runtime_dependencies_and_optional_groups():
    pyproject = tomllib.loads(_read(root / "apps" / "backend" / "pyproject.toml"))
    project = pyproject["project"]

    dependencies = project.get("dependencies") or []
    optional = project.get("optional-dependencies") or {}

    assert any(dep.startswith("fastapi") for dep in dependencies)
    assert any(dep.startswith("langgraph") for dep in dependencies)
    assert "ocr" in optional
    assert "eval" in optional
    assert "dev" in optional


def test_backend_requirements_files_point_to_split_entrypoints():
    runtime_requirements = _read(root / "apps" / "backend" / "requirements-runtime.txt")
    dev_requirements = _read(root / "apps" / "backend" / "requirements-dev.txt")
    compatibility_requirements = _read(root / "apps" / "backend" / "requirements.txt")

    assert "-c constraints.txt" in runtime_requirements
    assert runtime_requirements.strip().endswith(".")
    assert "-c constraints.txt" in dev_requirements
    assert ".[dev,eval,ocr]" in dev_requirements
    assert "-r requirements-dev.txt" in compatibility_requirements


def test_coverage_threshold_is_defined_once_and_ci_does_not_override_it():
    pytest_ini = _read(root / "pytest.ini")
    ci_yaml = _read(root / ".github" / "workflows" / "ci.yml")

    assert "--cov-fail-under=70" in pytest_ini
    assert "--cov-fail-under=" not in ci_yaml


def test_backend_ci_installs_split_dev_requirements():
    ci_yaml = _read(root / ".github" / "workflows" / "ci.yml")

    assert "pip install -r requirements-dev.txt" in ci_yaml
    assert "requirements-runtime.txt" in ci_yaml
    assert "constraints.txt" in ci_yaml


def test_backend_docker_uses_runtime_requirements():
    dockerfile = _read(root / "apps" / "backend" / "Dockerfile")

    assert "COPY pyproject.toml constraints.txt requirements-runtime.txt ./" in dockerfile
    assert "pip install --no-cache-dir --target=/build/deps -r requirements-runtime.txt" in dockerfile
