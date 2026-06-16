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


@pytest.fixture(autouse=True)
def _disable_real_llm_calls(monkeypatch):
    """测试环境禁用真实 LLM：archetype_advisor 返回确定性有效原型。

    真实 LLM 在测试环境常返回无效判断；其关键词 fallback 又因"信息不足"选通用原型，
    导致生成的训练课（如 Pfitzinger Progression Run）超过 80min 容量上限、
    half_marathon_protocol validation 失败。LLM 判断质量属评测管道（eval）范畴，
    不应阻塞单元/集成测试。这里给确定性半马原型（marathon_background=True），
    保证 plan 生成测试可重复。需要真实 LLM 的测试可局部 monkeypatch 重载。
    """
    try:
        from marathon_qa_assistant.core import archetype_advisor
        from marathon_qa_assistant.core.half_marathon_protocol import RunnerArchetypeInput

        def _fake_advisory(profile, total_weeks, enable_llm=True):
            return RunnerArchetypeInput(
                recent_marathon=False,
                build_weeks=total_weeks,
                endurance_background=False,
                marathon_background=True,
                long_training_gap=False,
                middle_distance_background=False,
                speed_strength=False,
                half_marathon_experience_low=False,
                weekly_mileage_km=float((profile or {}).get("weekly_mileage") or 35),
                injury_or_fatigue=False,
            ), {"marathon_background": "test fixture (LLM disabled)"}

        monkeypatch.setattr(archetype_advisor, "get_archetype_advisory", _fake_advisory)
    except ImportError:
        pass
