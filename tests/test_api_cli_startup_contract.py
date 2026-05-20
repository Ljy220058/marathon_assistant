import runpy
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient

from marathon_qa_assistant.apps import api_app


root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

API_SCRIPT = root / "apps" / "backend" / "src" / "marathon_qa_assistant" / "apps" / "api_app.py"

client = TestClient(api_app.app)


def test_health_endpoint_uses_default_model_when_env_missing(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["model"] == "qwen2.5:latest"
    assert set(payload["rag"]).issuperset({"ready", "source", "chunks_count", "faiss_ready"})


def test_api_app_main_starts_uvicorn_with_expected_contract(monkeypatch):
    calls = []

    fake_workflow = types.ModuleType("marathon_qa_assistant.core.workflow")

    class _FakeIntegratedApp:
        async def ainvoke(self, initial_state):
            return {}

    fake_workflow.integrated_app = _FakeIntegratedApp()
    fake_workflow.IntegratedState = dict
    fake_workflow.load_user_profile = lambda: {}

    fake_uvicorn = types.ModuleType("uvicorn")

    def fake_run(app, host=None, port=None):
        calls.append({"app": app, "host": host, "port": port})

    fake_uvicorn.run = fake_run

    monkeypatch.setitem(sys.modules, "marathon_qa_assistant.core.workflow", fake_workflow)
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)

    namespace = runpy.run_path(str(API_SCRIPT), run_name="__main__")

    assert len(calls) == 1
    assert calls[0]["app"] is namespace["app"]
    assert calls[0]["host"] == "0.0.0.0"
    assert calls[0]["port"] == 8000
