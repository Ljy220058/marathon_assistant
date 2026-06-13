import sys
from pathlib import Path


root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from marathon_qa_assistant.core.settings import build_settings


def test_settings_defaults_are_local_and_safe():
    settings = build_settings({})

    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.rate_limit_per_minute == 600
    assert settings.rate_limit_max_buckets == 4096
    assert settings.auth_enabled is False
    assert settings.runtime_config_errors("127.0.0.1") == []
    assert settings.allowed_cors_origins() == ["http://127.0.0.1:4321", "http://localhost:4321"]
    assert settings.llm_provider == "ds"
    assert settings.model_for_provider("ds") == "deepseek-v4-pro"
    assert settings.embedding_model == "bge-m3:latest"
    assert settings.retrieval_variants_enabled is True
    assert settings.semantic_chunking_enabled is False
    assert settings.bm25_fallback_enabled is True
    assert settings.domain_filter_enabled is True
    assert settings.sharded_retrieval_enabled is True
    assert settings.ragas_eval_enabled is False


def test_semantic_chunking_is_explicit_opt_in():
    settings = build_settings({"MARATHON_SEMANTIC_CHUNKING_ENABLED": "1"})

    assert settings.semantic_chunking_enabled is True


def test_sharded_retrieval_can_be_disabled():
    settings = build_settings({"MARATHON_SHARDED_RETRIEVAL_ENABLED": "0"})

    assert settings.sharded_retrieval_enabled is False


def test_settings_production_requires_token_and_fernet_key():
    settings = build_settings({"MARATHON_ENV": "production"})

    assert settings.is_production is True
    assert settings.auth_enabled is True
    assert settings.production_config_errors() == [
        "MARATHON_API_TOKEN is required when MARATHON_ENV=production.",
        "MARATHON_FERNET_KEY is required when MARATHON_ENV=production.",
    ]


def test_settings_runtime_config_blocks_public_host_without_token_but_allows_dev_override():
    settings = build_settings({})
    assert settings.runtime_config_errors("0.0.0.0") == [
        "MARATHON_API_TOKEN is required when binding a public host."
    ]

    dev_settings = build_settings({"MARATHON_DEV_ALLOW_PUBLIC_NO_AUTH": "1"})
    assert dev_settings.runtime_config_errors("0.0.0.0") == []


def test_settings_redacts_secrets_in_safe_view():
    settings = build_settings(
        {
            "MARATHON_API_TOKEN": "api-secret",
            "MARATHON_EXPERT_API_TOKEN": "expert-secret",
            "MARATHON_FERNET_KEY": "fernet-secret",
            "DEEPSEEK_API_KEY": "deepseek-secret",
            "OPENAI_API_KEY": "openai-secret",
            "MARATHON_HOST": "127.0.0.1",
        }
    )

    safe = settings.redacted()

    assert safe["api_token"] == "[redacted]"
    assert safe["expert_api_token"] == "[redacted]"
    assert safe["fernet_key"] == "[redacted]"
    assert safe["deepseek_api_key"] == "[redacted]"
    assert safe["openai_api_key"] == "[redacted]"
    assert safe["host"] == "127.0.0.1"
