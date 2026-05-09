import sys
import types
from pathlib import Path


root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

if "chainlit" not in sys.modules:
    fake_chainlit = types.ModuleType("chainlit")

    class _FakeLogger:
        def info(self, *args, **kwargs): pass
        def warning(self, *args, **kwargs): pass
        def error(self, *args, **kwargs): pass
        def debug(self, *args, **kwargs): pass

    class _FakeUserSession:
        def __init__(self):
            self._data = {}
        def get(self, key, default=None):
            return self._data.get(key, default)
        def set(self, key, value):
            self._data[key] = value

    class _FakeElement:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.__dict__.update(kwargs)
            if "id" not in self.__dict__:
                self.id = "fake-id"
        async def send(self, *args, **kwargs):
            return self
        async def update(self, *args, **kwargs):
            return self

    def _identity_decorator(*args, **kwargs):
        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return args[0]
        def wrapper(func):
            return func
        return wrapper

    async def _make_async_call(func, *args, **kwargs):
        return func(*args, **kwargs)

    def _make_async(func):
        async def wrapped(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapped

    fake_chainlit.logger = _FakeLogger()
    fake_chainlit.user_session = _FakeUserSession()
    fake_chainlit.Message = _FakeElement
    fake_chainlit.Action = _FakeElement
    fake_chainlit.Image = _FakeElement
    fake_chainlit.File = _FakeElement
    fake_chainlit.CustomElement = _FakeElement
    fake_chainlit.Text = _FakeElement
    fake_chainlit.ChatProfile = _FakeElement
    fake_chainlit.set_chat_profiles = _identity_decorator
    fake_chainlit.on_chat_start = _identity_decorator
    fake_chainlit.on_message = _identity_decorator
    fake_chainlit.action_callback = _identity_decorator
    fake_chainlit.make_async = _make_async
    sys.modules["chainlit"] = fake_chainlit


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

    class _FakeChatOllama:
        def __init__(self, *args, **kwargs):
            pass

        async def ainvoke(self, *args, **kwargs):
            return type("FakeResponse", (), {"content": "{}"})()

    fake_langchain_ollama.OllamaEmbeddings = _FakeOllamaEmbeddings
    fake_langchain_ollama.ChatOllama = _FakeChatOllama
    sys.modules["langchain_ollama"] = fake_langchain_ollama


if "langchain_core.documents" not in sys.modules:
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
