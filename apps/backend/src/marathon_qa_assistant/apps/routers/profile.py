"""Profile router — user profile CRUD, zones, and NLU extract endpoints."""

from fastapi import APIRouter, HTTPException, Request

from marathon_qa_assistant.apps.schemas import (
    NluExtractRequest,
    ProfileFieldRequest,
    ProfileRequest,
)
from marathon_qa_assistant.apps.routers._shared import (
    _auth_enabled,
    _extract_profile_suggestions,
    _profile_zones,
    _resolve_user_id,
    _save_profile_patch,
    DEFAULT_API_USER_ID,
)
from marathon_qa_assistant.core.profile_store import load_user_profile


router = APIRouter()

PROFILE_FIELD_ALLOWLIST = {
    "goal",
    "experience_level",
    "recent_four_week_mileage",
    "current_half_time",
    "target_race_date",
    "available_days",
    "max_session_minutes",
    "target_pace",
    "t_pace",
    "lthr",
    "vo2max",
    "terrain_preference",
    "training_types",
    "notes",
    "weekly_mileage",
    "weight_kg",
    "sex",
    "diet_type",
    "sweat_rate",
    "gi_sensitivity",
    "target_half_time",
    "pb_5k",
    "pb_10k",
    "pb_half",
    "pb_full",
}


def _validated_profile_patch(profile: dict | None) -> dict:
    payload = dict(profile or {})
    invalid = [
        key for key in payload
        if not key or str(key).startswith("_") or str(key) not in PROFILE_FIELD_ALLOWLIST
    ]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"画像字段名无效: {', '.join(str(item) for item in invalid)}",
        )
    return payload


@router.get("/profile")
async def get_profile(http_request: Request, user_id: str = DEFAULT_API_USER_ID):
    """返回当前用户跑者画像，供 Astro 工作台初始化。"""
    uid = _resolve_user_id(http_request) if _auth_enabled() else user_id
    return {"user_id": uid, "profile": load_user_profile(uid)}


@router.post("/profile")
async def save_profile(request: ProfileRequest, http_request: Request):
    """保存 Astro 工作台提交的跑者画像草稿。"""
    uid = _resolve_user_id(http_request)
    profile = _save_profile_patch(_validated_profile_patch(request.profile), user_id=uid)
    return {"user_id": uid, "profile": profile}


@router.get("/profile/{user_id}")
async def get_profile_by_user(user_id: str, http_request: Request):
    """按设计文档路径返回完整用户画像。"""
    uid = _resolve_user_id(http_request) if _auth_enabled() else user_id
    return {"user_id": uid, "profile": load_user_profile(uid)}


@router.put("/profile/{user_id}")
async def put_profile_by_user(user_id: str, request: ProfileRequest, http_request: Request):
    """按设计文档路径更新用户画像；当前单用户模式下采用合并写入。"""
    uid = _resolve_user_id(http_request) if _auth_enabled() else user_id
    profile = _save_profile_patch(_validated_profile_patch(request.profile), user_id=uid)
    return {"user_id": uid, "profile": profile}


@router.patch("/profile/{user_id}/fields/{field_key}")
async def patch_profile_field(user_id: str, field_key: str, request: ProfileFieldRequest, http_request: Request):
    """更新单个画像字段，并同步由画像衍生的强度区间。"""
    uid = _resolve_user_id(http_request) if _auth_enabled() else user_id
    profile = _save_profile_patch(_validated_profile_patch({field_key: request.value}), user_id=uid)
    return {"user_id": uid, "field_key": field_key, "profile": profile}


@router.get("/profile/{user_id}/zones")
async def get_profile_zones(user_id: str, http_request: Request):
    """从当前画像实时衍生 LTHR 九区和配速区间。"""
    uid = _resolve_user_id(http_request) if _auth_enabled() else user_id
    zones = _profile_zones(load_user_profile(uid))
    return {"user_id": uid, **zones}


@router.post("/profile/{user_id}/nlu-extract")
async def preview_profile_nlu_extract(user_id: str, request: NluExtractRequest, http_request: Request):
    """从自然语言中提取画像变更建议；需要用户确认后才写入。"""
    uid = _resolve_user_id(http_request) if _auth_enabled() else user_id
    suggestions = _extract_profile_suggestions(request.text)
    return {
        "user_id": uid,
        "suggested_changes": suggestions,
        "requires_confirmation": True,
    }
