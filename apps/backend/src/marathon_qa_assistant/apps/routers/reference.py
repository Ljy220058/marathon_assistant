"""Reference router — zone reference, evidence tier reference, LLM options."""

import asyncio
import hmac

from fastapi import APIRouter, HTTPException, Request

from marathon_qa_assistant.apps.schemas import (
    KnowledgeSourcesResponse,
    ZoneReference,
)
from marathon_qa_assistant.apps.response_builders import _normalize_provider
from marathon_qa_assistant.apps.routers._shared import (
    _request_api_token,
)
from marathon_qa_assistant.apps.security.response_role import _response_role
from marathon_qa_assistant.core.app_state import V2_VECTOR_DIR
from marathon_qa_assistant.core.settings import get_settings
from marathon_qa_assistant.services.workout_template_retriever import (
    EVIDENCE_TIER_LABELS,
    ZONE_LABELS,
    ZONE_LABELS_DETAIL,
)
from marathon_qa_assistant.services.kb.evidence_chain import (
    ANSWER_SOURCE_MODES,
    EVIDENCE_CHAIN_DISPLAY_MODES,
)
from marathon_qa_assistant.services.kb.source_inventory import (
    load_source_inventory_summary,
    public_source_inventory_summary,
)


router = APIRouter()


def _require_expert_source_access(request: Request) -> None:
    if _response_role(request) != "expert":
        raise HTTPException(status_code=403, detail="Expert access required.")


@router.get("/knowledge/sources", response_model=KnowledgeSourcesResponse)
def list_knowledge_sources(request: Request):
    _require_expert_source_access(request)
    chunks_path = V2_VECTOR_DIR / "chunks.jsonl"
    if not chunks_path.exists():
        return KnowledgeSourcesResponse()
    return load_source_inventory_summary(chunks_path)


@router.get("/knowledge/sources/summary", response_model=KnowledgeSourcesResponse)
def get_knowledge_sources_summary():
    chunks_path = V2_VECTOR_DIR / "chunks.jsonl"
    if not chunks_path.exists():
        return KnowledgeSourcesResponse()
    return public_source_inventory_summary(chunks_path)


@router.get("/zone-reference", response_model=ZoneReference)
async def get_zone_reference():
    """返回 Z1-Z9 强度区间中文术语参考表"""
    return ZoneReference(
        zones=ZONE_LABELS,
        zones_detail=ZONE_LABELS_DETAIL,
    )


@router.get("/evidence-tier-reference")
async def get_evidence_tier_reference():
    """返回证据分层标记的中文映射"""
    return {
        "evidence_tiers": EVIDENCE_TIER_LABELS,
        "evidence_drawer_contract": {
            "display_modes": EVIDENCE_CHAIN_DISPLAY_MODES,
            "answer_source_modes": ANSWER_SOURCE_MODES,
            "public_fields": [
                "evidence_id",
                "display_mode",
                "source_label",
                "source_url",
                "page",
                "section",
                "evidence_domain",
                "prescription_permission",
                "user_facing_summary",
            ],
            "expert_only_fields": [
                "source_registry_id",
                "retrieval_mode",
                "score",
                "chunk_id",
                "rag_eval",
                "source_quality",
                "expert_metadata",
            ],
            "no_fake_citation_rule": "When source_url/page/section are missing, display model_general_knowledge or needs_evidence instead of a citation badge.",
        },
        "core_prescription_permissions": {
            "allowed_domains": ["protocol", "action_library"],
            "required_permission": "can_write_core",
            "blocked_sources": ["llm_general_knowledge", "sports_science_reference_without_structured_rule"],
        },
        "descriptions": {
            "action_library": "课表数据来自动作库直接证据，训练方案经过验证。",
            "protocol_rule": "课表由 HMP 基石协议确定性排课，动作库注册表提供执行细节和替代方案。",
            "kb_fallback": "动作库中未找到该训练类型的直接证据，已基于其他知识库内容生成参考课表。",
            "needs_evidence": "当前训练类型缺少可绑定动作库证据，暂不向用户展示模板化主课。",
            "plan_only": "当前训练类型在知识库中暂无充分证据支撑，基于训练计划骨架生成。",
        },
    }


@router.get("/llm-options")
async def get_llm_options(request: Request):
    """返回前端模型选择控件所需的可用模型清单。"""
    settings = get_settings()
    ollama_model = settings.ollama_model
    deepseek_model = settings.deepseek_model
    openai_model = settings.openai_model
    default_provider = _normalize_provider(settings.llm_provider)
    default_model = {
        "ds": deepseek_model,
        "openai": openai_model,
    }.get(default_provider, ollama_model)
    configured_token = settings.api_token
    can_show_private_config = not configured_token or hmac.compare_digest(_request_api_token(request), configured_token)
    return {
        "default": {
            "provider": default_provider,
            "model": default_model,
        },
        "providers": [
            {
                "id": "ollama",
                "label": "Ollama",
                "default_model": ollama_model,
                "models": [ollama_model],
            },
            {
                "id": "ds",
                "label": "DeepSeek",
                "default_model": deepseek_model,
                "models": [deepseek_model],
                "api_key_configured": bool(settings.deepseek_api_key) if can_show_private_config else False,
                "api_key_config_visible": bool(can_show_private_config),
            },
            {
                "id": "openai",
                "label": "OpenAI GPT",
                "default_model": openai_model,
                "models": [openai_model],
                "api_key_configured": bool(settings.openai_api_key) if can_show_private_config else False,
                "api_key_config_visible": bool(can_show_private_config),
            },
        ],
    }
