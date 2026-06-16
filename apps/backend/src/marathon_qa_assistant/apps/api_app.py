import json
import os
import re
import sys
import asyncio
import time
import hmac
import ipaddress
import copy
from contextlib import asynccontextmanager
from uuid import uuid4
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 将项目根目录添加到 sys.path
current_file = Path(__file__).absolute()
BASE_DIR = current_file.parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 必须在 workflow/langgraph 之前加载 sentence_transformers：torch 2.12+cu126 与
# workflow 链存在 native 符号冲突，若 workflow 先加载，后续 import sentence_transformers
# 会触发 startup segfault（exit 139，faulthandler 定位到 base/sampler.py）。
# 这里仅提前 import 库（不加载 568MB 模型），让 torch/sentence_transformers 的 native
# 符号先于 langgraph 注册；模型仍在 reranker 首次调用时延迟加载（见 services/reranker.py）。
try:
    import torch  # noqa: F401
    from sentence_transformers import CrossEncoder  # noqa: F401
except Exception as _early_st_error:  # 加载失败不阻断启动，reranker 将降级为纯 FAISS 排序
    import logging as _early_logging
    _early_logging.getLogger("api_app").warning(
        "提前加载 sentence_transformers 失败，reranker 将降级: %s", _early_st_error
    )

from marathon_qa_assistant.core.settings import get_settings, load_project_dotenv

load_project_dotenv()

from marathon_qa_assistant.core.workflow import (
    integrated_app,
    IntegratedState,
)
from marathon_qa_assistant.core.working_state import build_working_state
from marathon_qa_assistant.core.evidence_bundle import build_evidence_bundle
from marathon_qa_assistant.core.training_plan_context import merge_plan_profile_overrides
from marathon_qa_assistant.core.training_plan_skeleton import build_structured_training_plan_skeleton
from marathon_qa_assistant.core.observability import (
    metrics_snapshot,
    record_feedback_risk,
    record_generation_status,
    record_request,
)
from marathon_qa_assistant.core.kb_bootstrap import (
    bootstrap_knowledge_base,
    get_knowledge_base_health_snapshot,
)
from marathon_qa_assistant.core.app_state import DATA_DIR, V2_VECTOR_DIR, check_ollama_status
from marathon_qa_assistant.services.kb.source_inventory import warm_source_inventory_cache
from marathon_qa_assistant.services.database import get_db
from marathon_qa_assistant.core.logging_middleware import (
    RequestIDMiddleware,
    setup_structured_logging,
)
from marathon_qa_assistant.apps.schemas import (
    DayDetailResponse,
    EventScheduleRequest,
    FeedbackActionRequest,
    FeedbackActionResponse,
    FeedbackRequest,
    FeedbackResponse,
    NluExtractRequest,
    OpsMetricsResponse,
    PlanDetailResponse,
    ProfileFieldRequest,
    ProfileRequest,
    QueryRequest,
    QueryResponse,
    SavePlanRequest,
    TrainingCalendarResponse,
    ZoneReference,
    AdminCreateUserRequest,
    UserConsentRequest,
    UserComplianceResponse,
)
from marathon_qa_assistant.apps.response_builders import (
    _attach_citation_gate_to_trace_and_review,
    _has_calendar_source_plan,
    _normalize_provider,
    _public_rag_health,
    _safe_workflow_error_summary,
    _save_plan_if_ready,
    _selected_model,
    _v2_runtime_manifest_overlay,
)
from marathon_qa_assistant.apps.response_projection import (
    _project_feedback_response_for_role as _shared_project_feedback_response_for_role,
    _project_plan_detail_response_for_role as _shared_project_plan_detail_response_for_role,
    _project_query_response_for_role as _shared_project_query_response_for_role,
    _project_training_calendar_response_for_role as _shared_project_training_calendar_response_for_role,
)
from marathon_qa_assistant.apps.security.response_role import _response_role as _shared_response_role

DEFAULT_API_USER_ID = "default_user"


@asynccontextmanager
async def _lifespan(app_instance: FastAPI):
    app_instance.state.rag_bootstrap = bootstrap_knowledge_base()
    try:
        app_instance.state.source_inventory_summary = warm_source_inventory_cache(V2_VECTOR_DIR / "chunks.jsonl")
    except Exception:
        app_instance.state.source_inventory_summary = KnowledgeSourcesResponse().model_dump()
    # 确保至少有一个默认用户（首次启动时自动创建）
    try:
        get_db().ensure_default_user()
    except Exception:
        pass
    yield


app = FastAPI(title="Marathon QA Assistant API", version="1.0.0", lifespan=_lifespan)

setup_structured_logging()
app.add_middleware(RequestIDMiddleware)

_RATE_LIMIT_BUCKETS: Dict[Tuple[str, str, str], List[float]] = {}
_RATE_LIMITED_PREFIXES = ("/query", "/feedback", "/training-calendar", "/plans", "/profile")
_PUBLIC_API_PREFIXES = ("/health", "/zone-reference", "/evidence-tier-reference", "/llm-options", "/docs", "/openapi.json", "/auth/send-code", "/auth/verify", "/auth/login")


def _rate_limit_per_minute() -> int:
    return get_settings().rate_limit_per_minute


def _rate_limit_client_id(request: Request) -> str:
    if get_settings().trust_proxy_headers:
        forwarded = request.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
        if forwarded:
            try:
                return str(ipaddress.ip_address(forwarded))
            except ValueError:
                return "invalid-forwarded-for"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _rate_limit_route_key(request: Request) -> Optional[Tuple[str, str]]:
    method = request.method.upper()
    if method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    path = request.url.path or "/"
    for prefix in _RATE_LIMITED_PREFIXES:
        if path == prefix or path.startswith(f"{prefix}/"):
            return method, prefix
    return None


def _reset_rate_limit_state_for_tests() -> None:
    _RATE_LIMIT_BUCKETS.clear()


def _rate_limit_max_buckets() -> int:
    return get_settings().rate_limit_max_buckets


def _prune_rate_limit_buckets(now: float) -> None:
    expired_keys = [
        key
        for key, stamps in _RATE_LIMIT_BUCKETS.items()
        if not any(now - stamp < 60 for stamp in stamps)
    ]
    for key in expired_keys:
        _RATE_LIMIT_BUCKETS.pop(key, None)
    max_buckets = _rate_limit_max_buckets()
    if len(_RATE_LIMIT_BUCKETS) <= max_buckets:
        return
    oldest = sorted(
        _RATE_LIMIT_BUCKETS,
        key=lambda key: min(_RATE_LIMIT_BUCKETS.get(key) or [now]),
    )
    for key in oldest[: len(_RATE_LIMIT_BUCKETS) - max_buckets]:
        _RATE_LIMIT_BUCKETS.pop(key, None)


def _configured_api_token() -> str:
    """保留向后兼容：检查是否配置了旧版单 token。"""
    return get_settings().api_token


def _is_production_mode() -> bool:
    return get_settings().is_production


def _production_config_errors() -> List[str]:
    return get_settings().production_config_errors()


def _server_host() -> str:
    return get_settings().host


def _server_port() -> int:
    return get_settings().port


def _is_public_host(host: str) -> bool:
    return get_settings().is_public_host(host)


def _dev_allows_public_no_auth() -> bool:
    settings = get_settings()
    return not settings.is_production and settings.dev_allow_public_no_auth


def _runtime_config_errors(host: Optional[str] = None) -> List[str]:
    return get_settings().runtime_config_errors(host)


def _auth_enabled() -> bool:
    """判断是否强制 API 认证：生产模式或显式配置 MARATHON_API_TOKEN 时启用。
    数据库用户表用于 token→user 映射，不自动开启强制认证。"""
    return get_settings().auth_enabled


def _request_api_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("X-Marathon-API-Key", "").strip()


def _lookup_user_by_request(request: Request) -> Optional[str]:
    """从请求 token 查找用户；返回 user_id 或 None。"""
    token = _request_api_token(request)
    if not token:
        return None
    # 优先尝试数据库查找
    try:
        user = get_db().get_user_by_token(token)
        if user:
            return str(user["id"])
    except Exception:
        pass
    # 向后兼容：旧的单 token 模式
    configured = _configured_api_token()
    if configured and hmac.compare_digest(token, configured):
        return DEFAULT_API_USER_ID
    return None


def _requires_api_token(request: Request) -> bool:
    if not _auth_enabled():
        return False
    if request.method.upper() == "OPTIONS":
        return False
    path = request.url.path or "/"
    return not any(path == prefix or path.startswith(f"{prefix}/") for prefix in _PUBLIC_API_PREFIXES)


_COMPLIANCE_EXEMPT_PATHS = (
    "/user/consent",
    "/user/compliance",
    "/health",
    "/admin",
    "/zone-reference",
    "/evidence-tier-reference",
    "/llm-options",
    "/docs",
    "/openapi.json",
)
_COMPLIANCE_REQUIRED_PATHS = ("/query", "/feedback", "/training-calendar", "/plans/")


def _compliance_required(request: Request) -> bool:
    """生产模式下，核心 AI 服务路由要求用户完成合规流程。"""
    if not _is_production_mode():
        return False
    path = request.url.path or "/"
    if any(path == p or path.startswith(p) for p in _COMPLIANCE_EXEMPT_PATHS):
        return False
    return any(path == p or path.startswith(p) for p in _COMPLIANCE_REQUIRED_PATHS)


def _check_user_compliance(user_id: str) -> Optional[str]:
    """返回 None 表示合规；否则返回缺失项描述。"""
    if not user_id or user_id == DEFAULT_API_USER_ID:
        return None
    try:
        compliance = get_db().get_user_compliance(user_id)
    except Exception:
        return None
    if not compliance:
        return None
    if not compliance.get("compliance_complete"):
        missing = compliance.get("missing") or []
        return f"合规流程未完成，缺少：{', '.join(missing)}。请先访问 POST /user/consent 完成授权。"
    return None

def _allowed_cors_origins() -> List[str]:
    return get_settings().allowed_cors_origins()


def _metrics_requires_localhost_when_auth_disabled() -> bool:
    return not _auth_enabled() and _is_public_host(_server_host())


# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_cors_origins(),
    # Browsers reject "*" + credentials, so keep the API permissive but stateless.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _rate_limit_middleware(request: Request, call_next):
    limit = _rate_limit_per_minute()
    route_key = _rate_limit_route_key(request)
    if limit <= 0 or route_key is None:
        return await call_next(request)

    now = time.monotonic()
    _prune_rate_limit_buckets(now)
    bucket_key = (_rate_limit_client_id(request), route_key[0], route_key[1])
    recent = [stamp for stamp in _RATE_LIMIT_BUCKETS.get(bucket_key, []) if now - stamp < 60]
    if len(recent) >= limit:
        return JSONResponse(
            {"detail": "请求过于频繁，请稍后再试。"},
            status_code=429,
            headers={"Retry-After": "60"},
        )
    recent.append(now)
    _RATE_LIMIT_BUCKETS[bucket_key] = recent
    return await call_next(request)


@app.middleware("http")
async def _api_token_middleware(request: Request, call_next):
    config_errors = _runtime_config_errors()
    if config_errors:
        return JSONResponse(
            {"detail": "Production configuration is incomplete.", "errors": config_errors},
            status_code=503,
        )
    if not _requires_api_token(request):
        return await call_next(request)

    user_id = _lookup_user_by_request(request)
    if not user_id:
        return JSONResponse(
            {"detail": "API 访问需要有效凭据。"},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.state.user_id = user_id

    if _compliance_required(request):
        compliance_error = _check_user_compliance(user_id)
        if compliance_error:
            return JSONResponse(
                {"detail": compliance_error, "error_code": "COMPLIANCE_REQUIRED"},
                status_code=403,
            )

    return await call_next(request)


@app.middleware("http")
async def _request_observability_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req-{uuid4().hex}"
    request.state.request_id = request_id
    route_path = getattr(request.scope.get("route"), "path", None) or "/__unmatched__"
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        route_path = getattr(request.scope.get("route"), "path", None) or route_path
        record_request(
            method=request.method,
            path=route_path,
            status_code=500,
            duration_ms=(time.perf_counter() - started) * 1000,
            error_type=exc.__class__.__name__,
        )
        raise
    route_path = getattr(request.scope.get("route"), "path", None) or route_path
    response.headers["X-Request-ID"] = request_id
    record_request(
        method=request.method,
        path=route_path,
        status_code=response.status_code,
        duration_ms=(time.perf_counter() - started) * 1000,
    )
    return response

def _require_default_user(user_id: str):
    """向后兼容：开发模式下允许 default_user，生产模式下由 token 中间件保证 user_id。"""
    if not _auth_enabled():
        return
    # 生产模式：不做额外校验，token 中间件已经设置了正确的 user_id
    # 保留此函数以保持最小 diff
_response_role = _shared_response_role
_project_query_response_for_role = _shared_project_query_response_for_role
_project_feedback_response_for_role = _shared_project_feedback_response_for_role
_project_plan_detail_response_for_role = _shared_project_plan_detail_response_for_role
_project_training_calendar_response_for_role = _shared_project_training_calendar_response_for_role



def _check_database_health() -> bool:
    """Probe SQLite database connectivity with a lightweight query."""
    try:
        return bool(get_db().health_check())
    except Exception:
        return False


def _require_expert_token(request: Request):
    """Validate Bearer token against MARATHON_EXPERT_API_TOKEN env var."""
    expert_token = get_settings().expert_api_token
    if not expert_token:
        raise HTTPException(status_code=501, detail="Expert mode not configured.")
    auth = request.headers.get("Authorization", "")
    supplied = auth[len("Bearer "):] if auth.startswith("Bearer ") else ""
    # 使用常量时间比较，避免专家令牌校验暴露时序差异。
    if not supplied or not hmac.compare_digest(supplied, expert_token):
        raise HTTPException(status_code=403, detail="Expert access required.")


@app.get("/health")
async def health_check():
    """Public health check — returns KB, DB, and Ollama status."""
    kb_snapshot = get_knowledge_base_health_snapshot()
    db_ok = _check_database_health()
    ollama_ok = await check_ollama_status()
    all_ok = kb_snapshot.get("ready", False) and db_ok and ollama_ok
    return {
        "status": "healthy" if all_ok else "degraded",
        "kb": kb_snapshot.get("ready", False),
        "db": db_ok,
        "ollama": ollama_ok,
    }


@app.get("/admin/health")
async def admin_health_check(request: Request):
    """Admin health check — full component status including KB, DB, Ollama, and model info.

    Requires expert token.  Returns never-null status field.
    """
    _require_expert_token(request)

    # 收集各组件健康状态，用 try/except 确保 status 永不为 null
    kb_snapshot: Dict[str, Any] = {}
    db_ok: bool = False
    ollama_ok: bool = False

    try:
        kb_snapshot = get_knowledge_base_health_snapshot()
    except Exception:
        kb_snapshot = {"ready": False, "reason": "KB health check failed"}

    try:
        db_ok = _check_database_health()
    except Exception:
        db_ok = False

    try:
        ollama_ok = await check_ollama_status()
    except Exception:
        ollama_ok = False

    kb_ready = bool(kb_snapshot.get("ready", False)) if isinstance(kb_snapshot, dict) else False
    all_ok = kb_ready and db_ok and ollama_ok

    # 根据 LLM_PROVIDER 决定模型名称
    settings = get_settings()
    provider = settings.llm_provider
    if provider in ("ds", "deepseek"):
        model = settings.deepseek_model
    elif provider in ("openai", "gpt"):
        model = settings.openai_model
    else:
        model = settings.ollama_model

    return {
        "status": "healthy" if all_ok else "degraded",
        "kb": kb_ready,
        "db": db_ok,
        "ollama": ollama_ok,
        "model": model,
    }


def _load_kb_governance_artifact(governance_dir: Path, filename: str) -> Tuple[str, Dict[str, Any]]:
    path = governance_dir / filename
    if not path.exists():
        return "missing", {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "unreadable", {}
    if not isinstance(payload, dict):
        return "unreadable", {}
    return "ready", payload


def _admin_kb_governance_summary() -> Dict[str, Any]:
    governance_dir = DATA_DIR / "knowledge" / "governance"
    artifact_files = {
        "kb_release_report": "kb_release_report.json",
        "source_gap_report": "source_gap_report.json",
        "runtime_index_v2_manifest": "runtime_index_v2_manifest.json",
    }
    artifacts: Dict[str, str] = {}
    payloads: Dict[str, Dict[str, Any]] = {}
    for key, filename in artifact_files.items():
        status, payload = _load_kb_governance_artifact(governance_dir, filename)
        artifacts[key] = status
        payloads[key] = payload

    release_report = payloads["kb_release_report"]
    source_gap_report = payloads["source_gap_report"]
    runtime_manifest = payloads["runtime_index_v2_manifest"]
    can_replace_runtime = bool(runtime_manifest.get("can_replace_runtime"))
    commercial_release_ready = bool(release_report.get("commercial_release_ready"))
    ready = can_replace_runtime and commercial_release_ready
    if any(status == "unreadable" for status in artifacts.values()):
        status = "unreadable"
    elif any(status == "missing" for status in artifacts.values()):
        status = "unavailable"
    else:
        status = "ready" if ready else "blocked"

    # 管理接口只返回治理摘要，避免把 registry/local_path 等机器细节透出到 API。
    return {
        "status": status,
        "artifacts": artifacts,
        "runtime": {
            "status": str(runtime_manifest.get("status") or ""),
            "can_replace_runtime": can_replace_runtime,
            "first_batch_release_ready": bool(runtime_manifest.get("first_batch_release_ready")),
            "replacement_blockers": list(runtime_manifest.get("replacement_blockers") or []),
        },
        "release_gate": {
            "commercial_release_ready": commercial_release_ready,
            "ready_for_next_batch": bool(release_report.get("ready_for_next_batch")),
            "first_batch_release_ready": bool(release_report.get("first_batch_release_ready")),
            "readiness_blockers": list(release_report.get("readiness_blockers") or []),
            "evaluation_gate_summary": dict(release_report.get("evaluation_gate_summary") or {}),
        },
        "domain_gap_summary": dict(release_report.get("domain_gap_summary") or {}),
        "top_actionable_domain_gaps": list(release_report.get("actionable_domain_gaps") or [])[:5],
        "release_work_queue": list(source_gap_report.get("release_work_queue") or [])[:20],
    }


@app.get("/admin/kb-governance")
async def admin_kb_governance(request: Request):
    """Admin KB governance release gate summary. Requires expert token."""
    _require_expert_token(request)
    return _admin_kb_governance_summary()


@app.get("/admin/users")
async def admin_list_users(request: Request):
    """列出所有已注册用户。需要 expert token。"""
    _require_expert_token(request)
    return {"users": get_db().list_users()}


@app.post("/admin/users")
async def admin_create_user(body: AdminCreateUserRequest, request: Request):
    """创建新用户并返回 API token。需要 expert token。"""
    _require_expert_token(request)
    try:
        result = get_db().create_user(body.display_name, birth_year=body.birth_year)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if body.age_confirmed and body.birth_year is None:
        # admin 通过 age_confirmed=true 显式确认年龄时，补记 age_gate
        try:
            get_db().record_user_consent(result["user_id"], privacy_consent=False, health_data_consent=False, terms_accepted=False)
            conn_patch = get_db()._get_conn()
            conn_patch.execute(
                "UPDATE users SET age_gate_passed_at = datetime('now') WHERE id = ?",
                (result["user_id"],),
            )
            conn_patch.commit()
        except Exception:
            pass
    return {"created": True, **result}


@app.delete("/admin/users/{user_id}")
async def admin_deactivate_user(user_id: str, request: Request):
    """停用用户。需要 expert token。"""
    _require_expert_token(request)
    ok = get_db().deactivate_user(user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="用户不存在。")
    return {"deactivated": True, "user_id": user_id}


@app.post("/user/consent", response_model=UserComplianceResponse)
async def record_user_consent(body: UserConsentRequest, request: Request):
    """记录用户对隐私政策、健康数据处理和服务协议的同意。需要有效 token。"""
    if not _auth_enabled():
        raise HTTPException(status_code=403, detail="认证未启用，无法记录同意。")
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="需要有效的用户 token。")
    if not (body.privacy_consent or body.health_data_consent or body.terms_accepted):
        raise HTTPException(status_code=422, detail="至少需要同意一项。")
    try:
        get_db().record_user_consent(
            user_id,
            privacy_consent=body.privacy_consent,
            health_data_consent=body.health_data_consent,
            terms_accepted=body.terms_accepted,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"记录同意失败：{exc}")
    compliance = get_db().get_user_compliance(user_id)
    if not compliance:
        raise HTTPException(status_code=404, detail="用户不存在。")
    return UserComplianceResponse(**compliance)


@app.get("/user/compliance", response_model=UserComplianceResponse)
async def get_user_compliance_status(request: Request):
    """查询当前用户的合规状态（年龄验证、同意记录）。需要有效 token。"""
    if not _auth_enabled():
        raise HTTPException(status_code=403, detail="认证未启用。")
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="需要有效的用户 token。")
    compliance = get_db().get_user_compliance(user_id)
    if not compliance:
        raise HTTPException(status_code=404, detail="用户不存在。")
    return UserComplianceResponse(**compliance)


@app.get("/ops/metrics", response_model=OpsMetricsResponse)
async def get_ops_metrics():
    if _metrics_requires_localhost_when_auth_disabled():
        raise HTTPException(
            status_code=403,
            detail="Metrics endpoint requires auth when binding a public host.",
        )
    return metrics_snapshot()


# -------- ACWR Training Load endpoint (P2-3) ---------------------------------

from marathon_qa_assistant.services.training_load import (
    calculate_acwr,
    acute_load,
    chronic_load,
    classify_risk,
    compute_acwr_summary,
)


@app.get("/training-load")
async def get_training_load(
    loads: str = "",
    acute_window: int = 7,
    chronic_window: int = 28,
):
    """计算 ACWR 训练负荷比。

    Query params:
      - loads: 逗号分隔的每日负荷值，最近的排在最后。
        例: ?loads=120,135,110,140,0,125,130,...
      - acute_window: 急性窗口天数（默认 7）
      - chronic_window: 慢性窗口天数（默认 28）

    返回 ACWR 摘要，含风险等级和安全阈值参考。
    参考 Gabbett 2016: Br J Sports Med. 2016;50(5):273-280.
    """
    if not loads:
        # 返回模板响应，提示如何使用
        return {
            "acwr": None,
            "risk_level": "insufficient_data",
            "acute_load": None,
            "chronic_load": None,
            "note": "请通过 ?loads=120,135,... 提供每日负荷数据（逗号分隔，最近的在末尾）。",
            "method": "acwr_gabbett_2016",
            "reference": "Gabbett TJ. Br J Sports Med. 2016;50(5):273-280.",
            "risk_thresholds": {
                "undertraining": "< 0.8",
                "safe": "0.8 - 1.3",
                "elevated": "1.3 - 1.5",
                "high_risk": "> 1.5",
            },
        }

    try:
        daily_loads = [float(v.strip()) for v in loads.split(",") if v.strip()]
    except ValueError:
        return {
            "error": "loads 格式错误，需为逗号分隔的数字，如 ?loads=120,135,110",
        }

    return compute_acwr_summary(
        daily_loads,
        acute_window=acute_window,
        chronic_window=chronic_window,
    )


# -------- include routers (extracted in P1.3) ---------------------------------

from marathon_qa_assistant.apps.routers.query import router as query_router
from marathon_qa_assistant.apps.routers.feedback import router as feedback_router
from marathon_qa_assistant.apps.routers.plans import router as plans_router
from marathon_qa_assistant.apps.routers.profile import router as profile_router
from marathon_qa_assistant.apps.routers.reference import router as reference_router, get_evidence_tier_reference
from marathon_qa_assistant.apps.routers.data_rights import router as data_rights_router
from marathon_qa_assistant.apps.routers.auth import router as auth_router

app.include_router(query_router)
app.include_router(feedback_router)
app.include_router(plans_router)
app.include_router(profile_router)
app.include_router(reference_router)
app.include_router(data_rights_router)
app.include_router(auth_router)

if __name__ == "__main__":
    import uvicorn

    host = _server_host()
    port = _server_port()
    config_errors = _runtime_config_errors(host)
    if config_errors:
        raise RuntimeError("; ".join(config_errors))
    workers = get_settings().web_workers
    if workers > 1:
        # 多 worker 必须传 import string（uvicorn 要求 workers>1 时 app 为字符串而非对象）；
        # 每个 worker 是独立进程，各自加载 KB + 持有 per-worker Semaphore（上限 = 总额度 / workers）。
        uvicorn.run(
            "marathon_qa_assistant.apps.api_app:app",
            host=host, port=port, workers=workers,
        )
    else:
        uvicorn.run(app, host=host, port=port)
