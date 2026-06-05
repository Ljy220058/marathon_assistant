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


def test_query_config_defaults_to_deepseek_without_request_body_secret(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    monkeypatch.delenv("DS_MODEL", raising=False)
    request = QueryRequest(query="easy run guidance", timeout_sec=12)

    config = api_app._build_llm_config(request)

    assert config == {
        "configurable": {
            "llm_provider": "ds",
            "llm_model": "deepseek-v4-pro",
            "llm_timeout_sec": 12,
        }
    }


    from cryptography.fernet import Fernet
    from marathon_qa_assistant.services import google_calendar_provider as provider

    key = Fernet.generate_key().decode()
    monkeypatch.setenv("MARATHON_SYNC_KEY", key)

    saved = {}

    class FakeCredentials:
        token = "access-token"
        refresh_token = "refresh-token"
        expiry = None
        client_id = "client-id"
        client_secret = "plain-client-secret"
        token_uri = "https://oauth2.googleapis.com/token"

    class FakeDB:
        def save_sync_token(self, user_id, provider_name, data):
            saved.update(data)

    calendar = provider.GoogleCalendarProvider(credentials_path=__import__("pathlib").Path("client.json"))
    calendar._credentials = FakeCredentials()
    monkeypatch.setattr(provider.GoogleCalendarProvider, "_db", property(lambda self: FakeDB()))

    calendar._persist_credentials()

    assert saved["oauth_client_secret"] != "plain-client-secret"
    assert provider._decrypt_token(saved["oauth_client_secret"]) == "plain-client-secret"
