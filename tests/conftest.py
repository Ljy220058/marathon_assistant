import os
import sys
import types
import importlib.util
from pathlib import Path

# 安全加固后不再有硬编码默认值 — 测试需显式注入
os.environ.setdefault("GRAPHRAG_API_KEY", "test-graphrag-key-for-ci")
os.environ.setdefault("OLLAMA_API_KEY", "test-ollama-key-for-ci")
os.environ.setdefault("API_KEY", "test-api-key-for-ci")

root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

backend_src = root / "apps" / "backend" / "src"
if backend_src.exists() and str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))


def _has_module(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False


if (
    "langchain_community.vectorstores" not in sys.modules
    and not _has_module("langchain_community.vectorstores")
):
    fake_langchain_community = types.ModuleType("langchain_community")
    fake_vectorstores = types.ModuleType("langchain_community.vectorstores")

    class _FakeFAISS:
        pass

    fake_vectorstores.FAISS = _FakeFAISS
    sys.modules["langchain_community"] = fake_langchain_community
    sys.modules["langchain_community.vectorstores"] = fake_vectorstores


if "langchain_ollama" not in sys.modules and not _has_module("langchain_ollama"):
    fake_langchain_ollama = types.ModuleType("langchain_ollama")

    class _FakeOllamaEmbeddings:
        def __init__(self, *args, **kwargs):
            pass

    class _FakeChatOllama:
        def __init__(self, *args, **kwargs):
            pass

        async def ainvoke(self, *args, **kwargs):
            return type("FakeResponse", (), {"content": "{}"})()

    fake_langchain_ollama.OllamaEmbeddings = _FakeOllamaEmbeddings
    fake_langchain_ollama.ChatOllama = _FakeChatOllama
    sys.modules["langchain_ollama"] = fake_langchain_ollama


if (
    "langchain_core.documents" not in sys.modules
    and not _has_module("langchain_core.documents")
):
    fake_langchain_core = types.ModuleType("langchain_core")
    fake_documents = types.ModuleType("langchain_core.documents")
    fake_messages = types.ModuleType("langchain_core.messages")

    class _FakeDocument:
        def __init__(self, page_content="", metadata=None):
            self.page_content = page_content
            self.metadata = metadata or {}

    class _FakeMessage:
        def __init__(self, content="", *args, **kwargs):
            self.content = content

    fake_documents.Document = _FakeDocument
    fake_messages.HumanMessage = _FakeMessage
    fake_messages.SystemMessage = _FakeMessage
    sys.modules["langchain_core"] = fake_langchain_core
    sys.modules["langchain_core.documents"] = fake_documents
    sys.modules["langchain_core.messages"] = fake_messages


# ── Test fixtures ────────────────────────────────────────────────────────────
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Return a synchronous TestClient bound to the FastAPI app."""
    from marathon_qa_assistant.apps.api_app import app

    return TestClient(app)
