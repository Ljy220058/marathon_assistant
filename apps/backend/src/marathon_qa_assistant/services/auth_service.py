"""邮箱验证码登录服务（OTP 模式）。

注册/登录合一：用户提交邮箱 → 发 N 位验证码 → 验证通过后签发长期 api_token。
- SMTP：QQ 邮箱（smtp.qq.com:465 SSL / 587 STARTTLS），用标准库 smtplib + asyncio.to_thread 避免阻塞事件循环。
- SMS：通道预留接口（未接入服务商，dev 阶段验证码打印到日志，不真发短信）。
- 限流：同一 target+channel 在窗口内不超过 max 次（防滥用）。
- 安全：验证码 hash 存储（不存明文），过期/超限自动作废（见 database.consume_verification_code）。
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac as _hmac
import logging
import os as _os
import random
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from marathon_qa_assistant.core.settings import get_settings
from marathon_qa_assistant.services.database import get_db

logger = logging.getLogger("auth_service")

_PURPOSE_LABEL = {"register": "注册", "login": "登录", "bind": "绑定"}


# ── 密码哈希（标准库 pbkdf2_hmac，无额外依赖）──────────────────────────

def hash_password(password: str) -> str:
    """PBKDF2-SHA256，16 字节随机 salt，100k 迭代，结果 base64 编码（salt+dk）。"""
    salt = _os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return base64.b64encode(salt + dk).decode("ascii")


def verify_password(password: str, stored: str) -> bool:
    """比较密码与存储 hash。使用 compare_digest 防止时序攻击。"""
    try:
        raw = base64.b64decode(stored.encode("ascii"))
        salt, dk = raw[:16], raw[16:]
        test = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return _hmac.compare_digest(test, dk)
    except Exception:
        return False


def generate_code(length: int = 6) -> str:
    """生成指定位数的数字验证码。"""
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def _build_code_email(to_addr: str, code: str, purpose: str, from_name: str) -> MIMEMultipart:
    """构造验证码邮件（纯文本 + HTML 双份）。"""
    s = get_settings()
    label = _PURPOSE_LABEL.get(purpose, "验证")
    ttl = s.mail_code_ttl_minutes
    msg = MIMEMultipart("alternative")
    # Header.encode() 返回 RFC2047 编码串（=?utf-8?b?...?=），避免中文名称触发 QQ SMTP 550
    encoded_name = Header(from_name, "utf-8").encode()
    msg["From"] = f"{encoded_name} <{s.smtp_user}>"
    msg["To"] = to_addr
    msg["Subject"] = Header(f"【马拉松助手】您的{label}验证码", "utf-8")
    text = f"您的{label}验证码是：{code}，{ttl} 分钟内有效。如非本人操作请忽略。"
    html = (
        f"<div style='font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px'>"
        f"<h2 style='color:#2b6cb0'>马拉松助手</h2>"
        f"<p>您的{label}验证码：</p>"
        f"<p style='font-size:32px;font-weight:bold;letter-spacing:6px;color:#2b6cb0'>{code}</p>"
        f"<p style='color:#666'>{ttl} 分钟内有效。如非本人操作请忽略此邮件。</p>"
        f"</div>"
    )
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def _smtp_send_sync(to_addr: str, msg: MIMEMultipart) -> None:
    """同步发送邮件（在线程池中调用，避免阻塞 FastAPI 事件循环）。"""
    s = get_settings()
    ctx = ssl.create_default_context()
    if s.smtp_port == 465:
        # 465: 隐式 SSL（QQ 邮箱默认推荐）
        with smtplib.SMTP_SSL(s.smtp_host, s.smtp_port, context=ctx, timeout=15) as server:
            server.login(s.smtp_user, s.smtp_password)
            server.sendmail(s.smtp_user, [to_addr], msg.as_string())
    else:
        # 587/25: STARTTLS
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as server:
            if s.smtp_use_tls:
                server.starttls(context=ctx)
            server.login(s.smtp_user, s.smtp_password)
            server.sendmail(s.smtp_user, [to_addr], msg.as_string())


async def send_verification_code(
    target: str, channel: str, purpose: str
) -> tuple[bool, str]:
    """发送验证码：生成 → 限流检查 → 存储（hash）→ 发送（SMTP/SMS/日志）。

    Args:
        target: 邮箱地址（channel=email）或手机号（channel=sms）
        channel: "email" | "sms"
        purpose: "register" | "login" | "bind"

    Returns:
        (是否成功, 原因/提示)。成功时验证码已入库（hash），dev 模式明文同时打印到日志。
    """
    s = get_settings()
    db = get_db()

    # 限流：同一 target+channel 在窗口内不超过 max 次
    recent = db.count_recent_codes(target, channel, s.mail_rate_limit_window_sec)
    if recent >= s.mail_rate_limit_max:
        window_min = s.mail_rate_limit_window_sec // 60
        return False, f"发送过于频繁，请 {window_min} 分钟后再试"

    code = generate_code(s.mail_code_length)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=s.mail_code_ttl_minutes)
    ).isoformat(timespec="seconds")
    db.create_verification_code(target, channel, purpose, code, expires_at)

    if channel == "email":
        # 未配置 SMTP 或显式 dev 打印模式：只记录日志（便于本地开发）
        if not s.smtp_configured or s.mail_dev_print_code:
            logger.warning(
                "[AUTH][dev-print] 验证码 %s -> %s (purpose=%s, expires=%s)",
                code, target, purpose, expires_at,
            )
            if not s.smtp_configured:
                logger.warning(
                    "SMTP 未配置（MARATHON_SMTP_USER/PASSWORD），验证码仅打印到日志。"
                    "配置后或设 MARATHON_MAIL_DEV_PRINT_CODE=0 走真实发送。"
                )
            return True, "验证码已发送"
        try:
            msg = _build_code_email(target, code, purpose, s.smtp_from_name)
            await asyncio.to_thread(_smtp_send_sync, target, msg)
            logger.info("[AUTH] 验证码邮件已发送 -> %s (purpose=%s)", target, purpose)
            return True, "验证码已发送至邮箱"
        except Exception as exc:
            logger.error("[AUTH] 邮件发送失败 %s: %s", target, exc)
            return False, f"邮件发送失败：{exc}"

    if channel == "sms":
        # SMS 通道预留：未接入服务商，dev 打印到日志。接入时在此调用 SMS API。
        logger.warning(
            "[AUTH][sms-placeholder] 验证码 %s -> %s (purpose=%s)。SMS 服务商未接入，仅打印日志。",
            code, target, purpose,
        )
        return True, "验证码已发送（SMS 通道未接入，见日志）"

    return False, f"不支持的通道: {channel}"


async def verify_code_and_login(
    target: str, channel: str, purpose: str, code: str, password: Optional[str] = None
) -> tuple[bool, str, Optional[dict]]:
    """验证码校验 + 注册/登录合一。

    password 仅在 purpose=register 时有效：新用户会同时存储密码 hash。
    Returns:
        (是否成功, 提示, user_info)。成功时 user_info={user_id, display_name, api_token, is_new}。
    """
    db = get_db()
    ok, reason = db.consume_verification_code(target, channel, purpose, code)
    if not ok:
        return False, reason, None

    if channel == "email":
        result = db.find_or_create_user_by_email(target)
        # 注册时设置密码
        if password and result["is_new"]:
            db.set_user_password(result["user_id"], hash_password(password))
        token = db.issue_new_api_token(result["user_id"])
        if not token:
            return False, "登录失败：账号状态异常", None
        db.touch_last_login(result["user_id"])
        return True, "注册成功" if result["is_new"] else "登录成功", {
            "user_id": result["user_id"],
            "display_name": result["display_name"],
            "api_token": token,
            "is_new": result["is_new"],
        }

    # SMS 登录暂未实现（预留）
    return False, "SMS 登录暂未实现", None


async def login_with_password(
    email: str, password: str
) -> tuple[bool, str, Optional[dict]]:
    """密码登录：邮箱 + 密码 → api_token。注册后首选登录方式。"""
    db = get_db()
    user = db.get_user_by_email(email)
    if not user:
        return False, "邮箱未注册，请先注册", None
    stored_hash = user.get("password_hash")
    if not stored_hash:
        return False, "账号未设置密码，请使用验证码登录", None
    if not verify_password(password, stored_hash):
        return False, "密码不正确", None
    token = db.issue_new_api_token(user["id"])
    if not token:
        return False, "登录失败：账号状态异常", None
    db.touch_last_login(user["id"])
    return True, "登录成功", {
        "user_id": user["id"],
        "display_name": user["display_name"],
        "api_token": token,
        "is_new": False,
    }
