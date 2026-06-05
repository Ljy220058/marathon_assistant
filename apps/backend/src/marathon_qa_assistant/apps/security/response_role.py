import hmac

from fastapi import HTTPException, Request

from marathon_qa_assistant.core.settings import get_settings


def _configured_expert_api_token() -> str:
    return get_settings().expert_api_token


def _dev_allows_expert_response() -> bool:
    settings = get_settings()
    return not settings.is_production and settings.dev_allow_expert_response


def _request_expert_api_token(request: Request) -> str:
    return request.headers.get("X-Marathon-Expert-Key", "").strip()


def _request_has_expert_response_access(request: Request) -> bool:
    expected = _configured_expert_api_token()
    supplied = _request_expert_api_token(request)
    return bool(expected and supplied and hmac.compare_digest(supplied, expected))


def _response_role(request: Request) -> str:
    requested = str(request.headers.get("X-Marathon-Response-Role") or "").strip().lower()
    if requested == "runner":
        return "runner"
    if requested == "expert":
        if _request_has_expert_response_access(request):
            return "expert"
        if _dev_allows_expert_response():
            return "expert"
        return "runner"
    if requested:
        raise HTTPException(status_code=400, detail="无效 response role。")
    return "runner"
