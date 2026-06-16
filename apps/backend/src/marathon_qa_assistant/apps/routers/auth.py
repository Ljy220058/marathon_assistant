"""认证路由：邮箱验证码注册（OTP+密码），密码登录。

端点：
- POST /auth/send-code  发送验证码（注册用）
- POST /auth/verify     校验验证码 + 创建账号（需同时提交密码）→ api_token
- POST /auth/login      密码登录（注册后使用）→ api_token
- GET  /auth/me         当前登录用户信息（需 Bearer token）
"""
from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from marathon_qa_assistant.services.auth_service import (
    login_with_password,
    send_verification_code,
    verify_code_and_login,
)
from marathon_qa_assistant.services.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


class SendCodeRequest(BaseModel):
    target: str = Field(..., description="邮箱（channel=email）或手机号（channel=sms）")
    channel: str = Field("email", pattern="^(email|sms)$")
    purpose: str = Field("register", pattern="^(register|login|bind)$")


class VerifyCodeRequest(BaseModel):
    target: str
    channel: str = Field("email", pattern="^(email|sms)$")
    purpose: str = Field("register", pattern="^(register|login|bind)$")
    code: str = Field(..., min_length=4, max_length=8)
    password: Optional[str] = Field(None, min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6, max_length=128)


def _validate_target(target: str, channel: str) -> Optional[str]:
    if channel == "email":
        if not _EMAIL_RE.match(target):
            return "邮箱格式不正确"
    elif channel == "sms":
        if not _PHONE_RE.match(target):
            return "手机号格式不正确"
    return None


@router.post("/send-code")
async def send_code(body: SendCodeRequest):
    """发送验证码（注册时使用）。"""
    err = _validate_target(body.target, body.channel)
    if err:
        return {"success": False, "message": err}
    ok, msg = await send_verification_code(body.target, body.channel, body.purpose)
    return {"success": ok, "message": msg}


@router.post("/verify")
async def verify(body: VerifyCodeRequest):
    """校验验证码并注册账号。password 字段为注册密码（必填）。"""
    err = _validate_target(body.target, body.channel)
    if err:
        return {"success": False, "message": err}
    if body.purpose == "register" and not body.password:
        return {"success": False, "message": "注册需要设置密码"}
    ok, msg, user_info = await verify_code_and_login(
        body.target, body.channel, body.purpose, body.code, body.password
    )
    if not ok or not user_info:
        return {"success": False, "message": msg}
    return {
        "success": True,
        "message": msg,
        "user_id": user_info["user_id"],
        "display_name": user_info["display_name"],
        "api_token": user_info["api_token"],
        "is_new": user_info["is_new"],
    }


@router.post("/login")
async def login(body: LoginRequest):
    """密码登录（注册后使用）。"""
    if not _EMAIL_RE.match(body.email):
        return {"success": False, "message": "邮箱格式不正确"}
    ok, msg, user_info = await login_with_password(body.email, body.password)
    if not ok or not user_info:
        return {"success": False, "message": msg}
    return {
        "success": True,
        "message": msg,
        "user_id": user_info["user_id"],
        "display_name": user_info["display_name"],
        "api_token": user_info["api_token"],
        "is_new": False,
    }


@router.get("/me")
async def me(request: Request):
    """当前登录用户信息。需带 X-Marathon-API-Key 或 Authorization: Bearer <token>。"""
    auth = request.headers.get("Authorization", "").strip()
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else request.headers.get("X-Marathon-API-Key", "").strip()
    user_id = getattr(request.state, "user_id", None)
    if not user_id and token:
        user = get_db().get_user_by_token(token)
        if user:
            user_id = user["id"]
    if not user_id:
        return {"authenticated": False}
    user = get_db().get_user_by_token(token) if token else None
    return {
        "authenticated": True,
        "user_id": user_id,
        "display_name": user["display_name"] if user else None,
        "email": user.get("email") if user else None,
        "email_verified": bool(user.get("email_verified")) if user else False,
    }
