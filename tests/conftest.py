import sys
import types
from pathlib import Path


root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))


if "langchain_community.vectorstores" not in sys.modules:
    fake_langchain_community = types.ModuleType("langchain_community")
    fake_vectorstores = types.ModuleType("langchain_community.vectorstores")

    class _FakeFAISS:
        pass

    fake_vectorstores.FAISS = _FakeFAISS
    sys.modules["langchain_community"] = fake_langchain_community
    sys.modules["langchain_community.vectorstores"] = fake_vectorstores


if "langchain_ollama" not in sys.modules:
    fake_langchain_ollama = types.ModuleType("langchain_ollama")

    class _FakeOllamaEmbeddings:
        def __init__(self, *args, **kwargs):
            pass

    fake_langchain_ollama.OllamaEmbeddings = _FakeOllamaEmbeddings
    sys.modules["langchain_ollama"] = fake_langchain_ollama


if "langchain_core.documents" not in sys.modules:
    fake_langchain_core = types.ModuleType("langchain_core")
    fake_documents = types.ModuleType("langchain_core.documents")

    class _FakeDocument:
        def __init__(self, page_content="", metadata=None):
            self.page_content = page_content
            self.metadata = metadata or {}

    fake_documents.Document = _FakeDocument
    sys.modules["langchain_core"] = fake_langchain_core
    sys.modules["langchain_core.documents"] = fake_documents
