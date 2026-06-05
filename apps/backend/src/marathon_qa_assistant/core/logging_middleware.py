"""Structured logging middleware with request-id injection."""

import json
import logging
import time
from uuid import uuid4
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from marathon_qa_assistant.core.settings import get_settings


LOG_RECORD_ATTRS = {
    "request_id", "method", "path", "status_code",
    "duration_ms", "client_ip",
}


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for attr in LOG_RECORD_ATTRS:
            val = getattr(record, attr, None)
            if val is not None:
                payload[attr] = val
        if record.exc_info and record.exc_info[0]:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _log_client_ip(client_ip: str) -> str:
    # 生产环境可关闭客户端 IP 记录，降低日志中的个人信息暴露。
    if not get_settings().log_client_ip:
        return "redacted"
    return client_ip


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        start = time.perf_counter()

        response: Response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        logger = logging.getLogger("http")
        logger.info(
            "",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": _log_client_ip(request.client.host if request.client else ""),
            },
        )
        return response


def setup_structured_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
