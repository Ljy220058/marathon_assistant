from marathon_qa_assistant.apps import api_app
from marathon_qa_assistant.apps.schemas import QueryRequest


def test_query_request_does_not_expose_provider_api_key_field():
    schema = api_app.app.openapi()["components"]["schemas"]["QueryRequest"]

    assert "ds_api_key" not in schema["properties"]


def test_query_config_ignores_legacy_request_body_provider_key():
    request = QueryRequest(
        query="easy run guidance",
        llm_provider="deepseek",
        llm_model="deepseek-test",
        ds_api_key="legacy-request-body-secret",
        timeout_sec=12,
    )

    config = api_app._build_llm_config(request)

    assert not hasattr(request, "ds_api_key")
    assert config == {
        "configurable": {
            "llm_provider": "ds",
            "llm_model": "deepseek-test",
            "llm_timeout_sec": 12,
        }
    }
