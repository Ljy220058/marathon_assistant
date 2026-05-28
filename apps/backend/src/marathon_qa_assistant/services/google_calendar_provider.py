import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from cryptography.fernet import Fernet

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None

    class HttpError(Exception):
        pass

logger = logging.getLogger("google_calendar")

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

TOKEN_KEY_FIELDS = [
    "token", "refresh_token", "token_uri", "client_id",
    "client_secret", "scopes", "expiry", "id_token",
]

WORKOUT_COLOR_MAP = {
    "easy": "2",
    "tempo": "5",
    "interval": "11",
    "long_run": "9",
    "rest": "8",
    "recovery": "7",
    "race": "11",
}


def _get_encryption_key() -> Optional[bytes]:
    key = os.getenv("MARATHON_SYNC_KEY", "")
    if key:
        return key.encode()
    return None


def _encrypt_token(plain: str) -> str:
    key = _get_encryption_key()
    if not key:
        raise RuntimeError("MARATHON_SYNC_KEY 环境变量未设置，无法加密令牌")
    return Fernet(key).encrypt(plain.encode()).decode()


def _decrypt_token(cipher: str) -> str:
    key = _get_encryption_key()
    if not key:
        raise RuntimeError("MARATHON_SYNC_KEY 环境变量未设置，无法解密令牌")
    return Fernet(key).decrypt(cipher.encode()).decode()


def _decrypt_optional_token(cipher: str) -> str:
    # 兼容历史明文 client_secret，同时优先读取新加密值。
    if not cipher:
        return ""
    try:
        return _decrypt_token(cipher)
    except Exception:
        return cipher


class GoogleCalendarProvider:
    """管理单个用户的 Google Calendar OAuth 2.0 授权与 API 调用。"""

    def __init__(
        self,
        credentials_path: Path,
        user_id: str = "default_user",
    ):
        self._credentials_path = credentials_path
        self._user_id = user_id
        self._credentials: Optional[Any] = None
        self._service = None

    @property
    def _db(self):
        from marathon_qa_assistant.services.database import get_db
        return get_db()

    # -------- 授权流程 --------

    def is_authorized(self) -> bool:
        creds = self._load_or_refresh_credentials()
        return creds is not None and creds.valid

    def authorize_interactive(self) -> str:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(self._credentials_path), SCOPES
        )
        self._credentials = flow.run_local_server(
            port=0,
            open_browser=True,
            authorization_prompt_message="请前往浏览器完成 Google 账号授权",
            success_message="授权成功！可以关闭此页面。",
        )
        self._persist_credentials()
        try:
            service = self._build_service()
            about = service.calendars().get(calendarId="primary").execute()
            return about.get("id", "unknown")
        except HttpError:
            return "unknown"

    def _load_or_refresh_credentials(self) -> Optional[Credentials]:
        if self._credentials and self._credentials.valid:
            return self._credentials

        row = self._db.load_sync_token(self._user_id, "google")
        if not row or not row.get("oauth_refresh_token"):
            return None

        try:
            refresh_token = _decrypt_token(row["oauth_refresh_token"])
            access_token = row.get("oauth_access_token")
            if access_token:
                access_token = _decrypt_token(access_token)
        except RuntimeError:
            logger.warning("无法解密 Google 令牌：MARATHON_SYNC_KEY 未设置或不正确")
            return None

        client_secret = _decrypt_optional_token(str(row.get("oauth_client_secret") or ""))
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=row.get("oauth_token_uri", "https://oauth2.googleapis.com/token"),
            client_id=row.get("oauth_client_id", ""),
            client_secret=client_secret,
            scopes=SCOPES,
        )

        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._credentials = creds
                self._persist_credentials()
            except Exception as exc:
                logger.warning(f"刷新 Google token 失败: {exc}")
                return None
        elif not creds.valid:
            return None

        self._credentials = creds
        return creds

    def _persist_credentials(self):
        if not self._credentials:
            return
        data: Dict[str, Any] = {}
        if self._credentials.token:
            data["oauth_access_token"] = _encrypt_token(self._credentials.token)
        if self._credentials.refresh_token:
            data["oauth_refresh_token"] = _encrypt_token(self._credentials.refresh_token)
        if self._credentials.expiry:
            data["oauth_token_expiry"] = self._credentials.expiry.isoformat()
        data["oauth_client_id"] = self._credentials.client_id or ""
        data["oauth_client_secret"] = _encrypt_token(self._credentials.client_secret) if self._credentials.client_secret else ""
        data["oauth_token_uri"] = getattr(
            self._credentials, "token_uri", "https://oauth2.googleapis.com/token"
        )
        self._db.save_sync_token(self._user_id, "google", data)

    def revoke(self):
        self._db.delete_sync_token(self._user_id, "google")
        self._credentials = None
        self._service = None

    def _build_service(self):
        creds = self._load_or_refresh_credentials()
        if not creds:
            raise RuntimeError("未授权 Google Calendar，请先调用 authorize_interactive()")
        if not self._service:
            self._service = build("calendar", "v3", credentials=creds)
        return self._service

    # -------- 事件 CRUD --------

    def push_event(self, calendar_id: str, event_data: Dict[str, Any]) -> str:
        service = self._build_service()
        try:
            result = service.events().insert(calendarId=calendar_id, body=event_data).execute()
            return result["id"]
        except HttpError as exc:
            if exc.resp.status == 409:
                ics_uid = event_data.get("id", "")
                if ics_uid:
                    existing = self._find_event_by_uid(calendar_id, ics_uid)
                    if existing:
                        return self.update_event(calendar_id, existing["id"], event_data)
            raise

    def push_events_batch(
        self, calendar_id: str, events: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        results: Dict[str, str] = {}
        for event_data in events:
            ics_uid = event_data.get("id", "")
            try:
                google_id = self.push_event(calendar_id, event_data)
                results[ics_uid] = google_id
            except HttpError as exc:
                logger.error(f"推送事件失败 {ics_uid}: {exc}")
                results[ics_uid] = f"ERROR:{exc.resp.status}"
        return results

    def update_event(
        self, calendar_id: str, google_event_id: str, event_data: Dict[str, Any]
    ) -> str:
        service = self._build_service()
        result = (
            service.events()
            .update(calendarId=calendar_id, eventId=google_event_id, body=event_data)
            .execute()
        )
        return result["id"]

    def delete_event(self, calendar_id: str, google_event_id: str) -> bool:
        service = self._build_service()
        try:
            service.events().delete(
                calendarId=calendar_id, eventId=google_event_id
            ).execute()
            return True
        except HttpError as exc:
            if exc.resp.status == 410:
                return True
            raise

    def _find_event_by_uid(self, calendar_id: str, ics_uid: str) -> Optional[Dict]:
        service = self._build_service()
        try:
            result = (
                service.events()
                .list(calendarId=calendar_id, iCalUID=f"{ics_uid}@marathon-assistant")
                .execute()
            )
            items = result.get("items", [])
            return items[0] if items else None
        except HttpError:
            return None

    def list_events(
        self, calendar_id: str, time_min: str, time_max: str
    ) -> List[Dict]:
        service = self._build_service()
        events: List[Dict] = []
        page_token = None
        while True:
            result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    pageToken=page_token,
                    maxResults=250,
                    singleEvents=True,
                )
                .execute()
            )
            events.extend(result.get("items", []))
            page_token = result.get("nextPageToken")
            if not page_token:
                break
        return events


def build_google_calendar_event(
    local_event: Dict[str, Any],
    timezone: str = "Asia/Shanghai",
) -> Dict[str, Any]:
    scheduled_date = local_event.get("scheduled_date", "")
    start_time_str = local_event.get("start_time", "07:00")
    duration_min = int(local_event.get("duration_min") or 60)
    title = local_event.get("title", "训练")
    workout_type = local_event.get("workout_type", "easy")
    ics_uid = local_event.get("ics_uid", "")

    start_dt_str = f"{scheduled_date}T{start_time_str}:00"
    try:
        start_dt = datetime.fromisoformat(start_dt_str)
        end_dt = start_dt + timedelta(minutes=duration_min)
        end_dt_str = end_dt.isoformat()
    except ValueError:
        start_dt = datetime.now()
        end_dt = start_dt + timedelta(minutes=duration_min)
        start_dt_str = start_dt.isoformat()
        end_dt_str = end_dt.isoformat()

    desc_parts = []
    for key, label in [
        ("warmup", "热身"), ("main_set", "主课"), ("cooldown", "放松"),
        ("venue", "场地"), ("notes", "备注"),
    ]:
        val = (local_event.get(key) or "").strip()
        if val:
            desc_parts.append(f"{label}：{val}")

    phase = local_event.get("phase", "")
    week_no = local_event.get("week_no", "")
    if phase or week_no:
        desc_parts.append(f"阶段：{phase} 第{week_no}周")

    intensity = local_event.get("intensity_zone", "")
    if intensity:
        desc_parts.append(f"强度：{intensity}")

    description = "\n".join(desc_parts)

    event = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_dt_str, "timeZone": timezone},
        "end": {"dateTime": end_dt_str, "timeZone": timezone},
        "colorId": WORKOUT_COLOR_MAP.get(workout_type, "1"),
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 30},
            ],
        },
    }

    if ics_uid:
        event["id"] = f"{ics_uid}@marathon-assistant"

    return event
