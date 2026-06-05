import asyncio
import importlib

import pytest

from marathon_qa_assistant.nodes import common


def test_openai_defaults_use_configured_commercial_gateway(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    reloaded_common = importlib.reload(common)

    assert reloaded_common.OPENAI_MODEL == "gpt-5.5"
    assert reloaded_common.OPENAI_BASE_URL == "https://api.aisz.mom/v1"


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeAsyncClient:
    calls = []

    def __init__(self, timeout):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers, json):
        self.__class__.calls.append({"url": url, "headers": headers, "json": json, "timeout": self.timeout})
        return _FakeResponse(
            {
                "output_text": "结构化训练解释",
                "usage": {"input_tokens": 12, "output_tokens": 8, "total_tokens": 20},
            }
        )


class _RateLimitedResponse:
    def raise_for_status(self):
        request = common.httpx.Request("POST", "https://api.openai.test/v1/responses")
        response = common.httpx.Response(429, request=request)
        raise common.httpx.HTTPStatusError("rate limited", request=request, response=response)

    def json(self):
        return {}


class _RateLimitedAsyncClient:
    def __init__(self, timeout):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers, json):
        return _RateLimitedResponse()


def test_ai_invoke_defaults_to_deepseek_provider(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DS_API_KEY", raising=False)

    with pytest.raises(common.LLMProviderError, match="DeepSeek API Key") as error:
        asyncio.run(common.ai_invoke("生成训练解释", {"configurable": {}}, None))

    assert error.value.provider == "ds"
    assert error.value.error_code == "missing_key"


    _FakeAsyncClient.calls = []
    monkeypatch.setattr(common.httpx, "AsyncClient", _FakeAsyncClient)

    content, usage = asyncio.run(
        common.ai_invoke(
            "生成训练解释",
            {
                "configurable": {
                    "llm_provider": "openai",
                    "llm_model": "gpt-5.2",
                    "openai_api_key": "sk-test",
                    "openai_base_url": "https://api.openai.test/v1",
                }
            },
            {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        )
    )

    assert content == "结构化训练解释"
    assert usage == {"prompt_tokens": 13, "completion_tokens": 10, "total_tokens": 23}
    call = _FakeAsyncClient.calls[0]
    assert call["url"] == "https://api.openai.test/v1/responses"
    assert call["headers"]["Authorization"] == "Bearer sk-test"
    assert call["json"]["model"] == "gpt-5.2"
    assert call["json"]["input"] == "生成训练解释"


def test_ai_invoke_requires_openai_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(common.LLMProviderError, match="OpenAI API Key") as error:
        asyncio.run(
            common.ai_invoke(
                "生成训练解释",
                {"configurable": {"llm_provider": "gpt", "llm_model": "gpt-5.2"}},
                None,
            )
        )
    assert error.value.error_code == "missing_key"
    assert error.value.provider == "openai"


def test_ai_invoke_classifies_openai_rate_limit(monkeypatch):
    monkeypatch.setattr(common.httpx, "AsyncClient", _RateLimitedAsyncClient)

    with pytest.raises(common.LLMProviderError, match="rate_limited") as error:
        asyncio.run(
            common.ai_invoke(
                "生成训练解释",
                {
                    "configurable": {
                        "llm_provider": "openai",
                        "llm_model": "gpt-5.2",
                        "openai_api_key": "sk-test",
                        "openai_base_url": "https://api.openai.test/v1",
                    }
                },
                None,
            )
        )

    assert error.value.error_code == "rate_limited"
    assert error.value.status_code == 429
