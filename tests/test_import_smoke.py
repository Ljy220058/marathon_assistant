import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = ROOT / "apps" / "backend" / "src"


def _import_module(module_name: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_SRC)
    env.setdefault("GRAPHRAG_API_KEY", "test-graphrag-key-for-ci")
    env.setdefault("OLLAMA_API_KEY", "test-ollama-key-for-ci")
    env.setdefault("API_KEY", "test-api-key-for-ci")
    return subprocess.run(
        [
            sys.executable,
            "-c",
            (
                f"import importlib; "
                f"module = importlib.import_module('{module_name}'); "
                "assert module is not None"
            ),
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def test_api_app_imports_without_pytest_bootstrap():
    result = _import_module("marathon_qa_assistant.apps.api_app")

    assert result.returncode == 0, (
        "api_app import should not depend on pytest bootstrap patches.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def test_workflow_imports_without_pytest_bootstrap():
    result = _import_module("marathon_qa_assistant.core.workflow")

    assert result.returncode == 0, (
        "workflow import should not depend on pytest bootstrap patches.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
