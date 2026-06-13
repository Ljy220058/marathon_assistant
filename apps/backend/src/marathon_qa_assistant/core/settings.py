from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from marathon_qa_assistant.core.app_state import BASE_DIR


def _env_str(env: Mapping[str, Any], key: str, default: str = "") -> str:
    return str(env.get(key) or default).strip()


def _env_int(env: Mapping[str, Any], key: str, default: int, minimum: Optional[int] = None) -> int:
    raw = _env_str(env, key, str(default))
    try:
        value = int(raw)
    except ValueError:
        value = default
    if minimum is not None:
        value = max(minimum, value)
    return value


def _env_float(env: Mapping[str, Any], key: str, default: float) -> float:
    raw = _env_str(env, key, str(default))
    try:
        return float(raw)
    except ValueError:
        return float(default)


def _env_flag(env: Mapping[str, Any], key: str) -> bool:
    return _env_str(env, key) == "1"


@dataclass(frozen=True)
class Settings:
    marathon_env: str
    api_token: str
    expert_api_token: str
    fernet_key: str
    host: str
    port: int
    rate_limit_per_minute: int
    rate_limit_max_buckets: int
    trust_proxy_headers: bool
    dev_allow_public_no_auth: bool
    dev_allow_expert_response: bool
    dev_permissive_cors: bool
    allowed_origins_raw: str
    llm_provider: str
    llm_timeout_sec: float
    ollama_base_url: str
    ollama_model: str
    deepseek_base_url: str
    deepseek_model: str
    deepseek_api_key: str
    openai_base_url: str
    openai_model: str
    openai_api_key: str
    graphrag_api_key: str
    embedding_model: str
    retrieval_variants_enabled: bool
    semantic_chunking_enabled: bool
    bm25_fallback_enabled: bool
    domain_filter_enabled: bool
    sharded_retrieval_enabled: bool
    rerank_enabled: bool
    ragas_eval_enabled: bool
    log_client_ip: bool
    app_version: str
    sync_key: str

    @property
    def is_production(self) -> bool:
        return self.marathon_env in {"prod", "production"}

    @property
    def auth_enabled(self) -> bool:
        return self.is_production or bool(self.api_token)

    def is_public_host(self, host: Optional[str] = None) -> bool:
        normalized = str(host if host is not None else self.host).strip().lower().strip("[]")
        return normalized not in {"127.0.0.1", "localhost", "::1"}

    def production_config_errors(self) -> list[str]:
        if not self.is_production:
            return []
        errors: list[str] = []
        if not self.api_token:
            errors.append("MARATHON_API_TOKEN is required when MARATHON_ENV=production.")
        if not self.fernet_key:
            errors.append("MARATHON_FERNET_KEY is required when MARATHON_ENV=production.")
        return errors

    def runtime_config_errors(self, host: Optional[str] = None) -> list[str]:
        errors = list(self.production_config_errors())
        if self.is_public_host(host) and not self.api_token and not self.dev_allow_public_no_auth:
            errors.append("MARATHON_API_TOKEN is required when binding a public host.")
        return errors

    def allowed_cors_origins(self) -> list[str]:
        if self.dev_permissive_cors:
            return ["*"]
        if self.allowed_origins_raw:
            origins = [item.strip() for item in self.allowed_origins_raw.split(",") if item.strip()]
            if origins:
                return origins
        return ["http://127.0.0.1:4321", "http://localhost:4321"]

    def model_for_provider(self, provider: str) -> str:
        normalized = str(provider or self.llm_provider).strip().lower()
        if normalized in {"ds", "deepseek"}:
            return self.deepseek_model
        if normalized in {"openai", "gpt"}:
            return self.openai_model
        return self.ollama_model

    def redacted(self) -> Dict[str, Any]:
        safe = asdict(self)
        for key in ("api_token", "expert_api_token", "fernet_key", "deepseek_api_key", "openai_api_key"):
            if safe.get(key):
                safe[key] = "[redacted]"
        return safe


def build_settings(env: Optional[Mapping[str, Any]] = None) -> Settings:
    values = os.environ if env is None else env
    return Settings(
        marathon_env=_env_str(values, "MARATHON_ENV").lower(),
        api_token=_env_str(values, "MARATHON_API_TOKEN"),
        expert_api_token=_env_str(values, "MARATHON_EXPERT_API_TOKEN"),
        fernet_key=_env_str(values, "MARATHON_FERNET_KEY"),
        host=_env_str(values, "MARATHON_HOST", "127.0.0.1") or "127.0.0.1",
        port=_env_int(values, "MARATHON_PORT", 8000),
        rate_limit_per_minute=_env_int(values, "MARATHON_RATE_LIMIT_PER_MINUTE", 600, minimum=0),
        rate_limit_max_buckets=_env_int(values, "MARATHON_RATE_LIMIT_MAX_BUCKETS", 4096, minimum=128),
        trust_proxy_headers=_env_flag(values, "MARATHON_TRUST_PROXY_HEADERS"),
        dev_allow_public_no_auth=_env_flag(values, "MARATHON_DEV_ALLOW_PUBLIC_NO_AUTH"),
        dev_allow_expert_response=_env_flag(values, "MARATHON_DEV_ALLOW_EXPERT_RESPONSE"),
        dev_permissive_cors=_env_flag(values, "MARATHON_DEV_PERMISSIVE_CORS"),
        allowed_origins_raw=_env_str(values, "MARATHON_ALLOWED_ORIGINS"),
        llm_provider=_env_str(values, "LLM_PROVIDER", "ds").lower() or "ds",
        llm_timeout_sec=_env_float(values, "LLM_TIMEOUT_SEC", 60.0),
        ollama_base_url=_env_str(values, "OLLAMA_BASE_URL", "http://localhost:11434") or "http://localhost:11434",
        ollama_model=_env_str(values, "OLLAMA_MODEL", "qwen2.5:latest") or "qwen2.5:latest",
        deepseek_base_url=_env_str(values, "DEEPSEEK_BASE_URL", "https://api.deepseek.com") or "https://api.deepseek.com",
        deepseek_model=_env_str(values, "DEEPSEEK_MODEL", _env_str(values, "DS_MODEL", "deepseek-v4-pro")) or "deepseek-v4-pro",
        deepseek_api_key=_env_str(values, "DEEPSEEK_API_KEY") or _env_str(values, "DS_API_KEY"),
        openai_base_url=_env_str(values, "OPENAI_BASE_URL", "https://api.aisz.mom/v1") or "https://api.aisz.mom/v1",
        openai_model=_env_str(values, "OPENAI_MODEL", "gpt-5.5") or "gpt-5.5",
        openai_api_key=_env_str(values, "OPENAI_API_KEY"),
        graphrag_api_key=_env_str(values, "GRAPHRAG_API_KEY"),
        embedding_model=_env_str(values, "MARATHON_EMBEDDING_MODEL", "bge-m3:latest") or "bge-m3:latest",
        retrieval_variants_enabled=(_env_str(values, "MARATHON_RETRIEVAL_VARIANTS_ENABLED", "1") != "0"),
        semantic_chunking_enabled=_env_flag(values, "MARATHON_SEMANTIC_CHUNKING_ENABLED"),
        bm25_fallback_enabled=(_env_str(values, "MARATHON_BM25_FALLBACK_ENABLED", "1") != "0"),
        domain_filter_enabled=(_env_str(values, "MARATHON_DOMAIN_FILTER_ENABLED", "1") != "0"),
        sharded_retrieval_enabled=(_env_str(values, "MARATHON_SHARDED_RETRIEVAL_ENABLED", "1") != "0"),
        rerank_enabled=(_env_str(values, "MARATHON_RERANK_ENABLED", "1") != "0"),
        ragas_eval_enabled=_env_flag(values, "MARATHON_RAGAS_EVAL_ENABLED"),
        log_client_ip=(_env_str(values, "MARATHON_LOG_CLIENT_IP", "1") != "0"),
        app_version=_env_str(values, "APP_VERSION", "dev") or "dev",
        sync_key=_env_str(values, "MARATHON_SYNC_KEY"),
    )


def get_settings() -> Settings:
    # Do not cache yet: many tests mutate env within one process and expect immediate visibility.
    return build_settings()


def load_project_dotenv(env_path: Optional[Path] = None) -> bool:
    if _env_flag(os.environ, "PYTHON_DOTENV_DISABLED"):
        return False
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False

    candidate = env_path or (BASE_DIR / "graphrag_project" / ".env")
    if candidate.exists():
        return bool(load_dotenv(candidate))
    return bool(load_dotenv())
