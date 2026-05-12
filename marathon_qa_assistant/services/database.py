import json
import re
import sqlite3
import threading
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from marathon_qa_assistant.core.app_state import RUNTIME_DATA_DIR
from marathon_qa_assistant.core.zone_constants import sanitize_all_pace

DB_PATH = RUNTIME_DATA_DIR / "marathon_assistant.db"


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sync_state (
    id                  TEXT PRIMARY KEY,
    user_id             TEXT NOT NULL DEFAULT 'default_user',
    plan_id             TEXT,
    calendar_provider   TEXT NOT NULL,          -- google / outlook / caldav
    calendar_id         TEXT,                   -- 目标日历 ID
    sync_enabled        INTEGER DEFAULT 0,
    last_sync_token     TEXT,
    last_full_sync_at   TEXT,
    last_sync_at        TEXT,
    sync_error          TEXT,
    oauth_access_token  TEXT,                   -- Fernet 加密
    oauth_refresh_token TEXT,                   -- Fernet 加密
    oauth_token_expiry  TEXT,
    oauth_client_id     TEXT,
    oauth_client_secret TEXT,
    oauth_token_uri     TEXT,
    caldav_url          TEXT,
    caldav_username     TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sync_state_uk
    ON sync_state(user_id, calendar_provider);

CREATE TABLE IF NOT EXISTS training_plans (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL DEFAULT 'default_user',
    goal            TEXT NOT NULL,
    experience_level TEXT,
    requested_weeks INTEGER NOT NULL,
    actual_weeks    INTEGER NOT NULL,
    plan_type       TEXT NOT NULL,
    start_date      TEXT,
    target_race_date TEXT,
    status          TEXT NOT NULL DEFAULT 'draft',
    source_query    TEXT,
    structured_plan_json TEXT,
    render_version  TEXT DEFAULT 'v1',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS training_calendar_events (
    id              TEXT PRIMARY KEY,
    plan_id         TEXT NOT NULL,
    user_id         TEXT NOT NULL DEFAULT 'default_user',
    week_no         INTEGER NOT NULL,
    day_no          INTEGER NOT NULL,
    day_label       TEXT NOT NULL,
    scheduled_date  TEXT,
    start_time      TEXT,
    duration_min    INTEGER,
    title           TEXT NOT NULL,
    workout_type    TEXT NOT NULL,
    intensity_zone  TEXT,
    warmup          TEXT,
    main_set        TEXT,
    cooldown        TEXT,
    venue           TEXT,
    notes           TEXT,
    warmup_km       REAL DEFAULT 0,
    main_km         REAL DEFAULT 0,
    cooldown_km     REAL DEFAULT 0,
    total_km        REAL DEFAULT 0,
    evidence_ids    TEXT,
    phase           TEXT,
    load_level      TEXT,
    status          TEXT NOT NULL DEFAULT 'planned',
    content_json    TEXT,
    ics_uid         TEXT,
    external_event_id TEXT,
    external_calendar_provider TEXT,
    sync_status     TEXT DEFAULT 'not_synced',
    last_synced_at  TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (plan_id) REFERENCES training_plans(id)
);

CREATE INDEX IF NOT EXISTS idx_events_plan ON training_calendar_events(plan_id);
CREATE INDEX IF NOT EXISTS idx_events_user_date ON training_calendar_events(user_id, scheduled_date);
CREATE INDEX IF NOT EXISTS idx_events_week ON training_calendar_events(plan_id, week_no);
CREATE INDEX IF NOT EXISTS idx_events_sync ON training_calendar_events(sync_status);

CREATE TABLE IF NOT EXISTS training_event_feedback (
    id                  TEXT PRIMARY KEY,
    event_id            TEXT NOT NULL,
    plan_id             TEXT NOT NULL,
    user_id             TEXT NOT NULL DEFAULT 'default_user',
    completion_status   TEXT NOT NULL,
    completion_quality  TEXT,
    subjective_fatigue  TEXT,
    pain_status         TEXT,
    sleep_quality       TEXT,
    user_notes          TEXT,
    raw_feedback_text   TEXT,
    adaptive_reason_codes TEXT,
    next_day_adjustment TEXT,
    weekly_adjustment   TEXT,
    alternative_workout TEXT,
    risk_alert          TEXT,
    adjustment_rationale TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (event_id) REFERENCES training_calendar_events(id),
    FOREIGN KEY (plan_id) REFERENCES training_plans(id)
);

CREATE INDEX IF NOT EXISTS idx_feedback_event ON training_event_feedback(event_id);
CREATE INDEX IF NOT EXISTS idx_feedback_plan ON training_event_feedback(plan_id);

CREATE TABLE IF NOT EXISTS training_event_exceptions (
    id                  TEXT PRIMARY KEY,
    event_id            TEXT NOT NULL,
    plan_id             TEXT NOT NULL,
    user_id             TEXT NOT NULL DEFAULT 'default_user',
    exception_type      TEXT NOT NULL,
    reason              TEXT,
    old_scheduled_date  TEXT,
    new_scheduled_date  TEXT,
    old_start_time      TEXT,
    new_start_time      TEXT,
    old_content_json    TEXT,
    new_content_json    TEXT,
    is_applied          INTEGER DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (event_id) REFERENCES training_calendar_events(id),
    FOREIGN KEY (plan_id) REFERENCES training_plans(id)
);
"""


class _Database:
    """线程安全的 SQLite 数据库单例。"""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._local = threading.local()
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return self._local.conn

    def _init_schema(self):
        conn = self._get_conn()
        conn.executescript(SCHEMA_SQL)
        conn.commit()

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    # ---- sync_state 表操作 ----

    def load_sync_token(self, user_id: str, provider: str) -> Optional[Dict[str, Any]]:
        row = self._get_conn().execute(
            "SELECT * FROM sync_state WHERE user_id = ? AND calendar_provider = ?",
            (user_id, provider),
        ).fetchone()
        return dict(row) if row else None

    def save_sync_token(self, user_id: str, provider: str, data: Dict[str, Any]):
        existing = self.load_sync_token(user_id, provider)
        conn = self._get_conn()
        if existing:
            conn.execute(
                """UPDATE sync_state SET
                    oauth_access_token = ?, oauth_refresh_token = ?,
                    oauth_token_expiry = ?, oauth_client_id = ?,
                    oauth_client_secret = ?, oauth_token_uri = ?,
                    sync_enabled = 1, updated_at = datetime('now')
                WHERE user_id = ? AND calendar_provider = ?""",
                (
                    data.get("oauth_access_token"),
                    data.get("oauth_refresh_token"),
                    data.get("oauth_token_expiry"),
                    data.get("oauth_client_id", ""),
                    data.get("oauth_client_secret", ""),
                    data.get("oauth_token_uri", "https://oauth2.googleapis.com/token"),
                    user_id,
                    provider,
                ),
            )
        else:
            import uuid
            conn.execute(
                """INSERT INTO sync_state
                    (id, user_id, calendar_provider, sync_enabled,
                     oauth_access_token, oauth_refresh_token,
                     oauth_token_expiry, oauth_client_id,
                     oauth_client_secret, oauth_token_uri)
                VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()),
                    user_id,
                    provider,
                    data.get("oauth_access_token"),
                    data.get("oauth_refresh_token"),
                    data.get("oauth_token_expiry"),
                    data.get("oauth_client_id", ""),
                    data.get("oauth_client_secret", ""),
                    data.get("oauth_token_uri", "https://oauth2.googleapis.com/token"),
                ),
            )
        conn.commit()

    def delete_sync_token(self, user_id: str, provider: str):
        conn = self._get_conn()
        conn.execute(
            "DELETE FROM sync_state WHERE user_id = ? AND calendar_provider = ?",
            (user_id, provider),
        )
        conn.commit()

    def update_sync_status(
        self, user_id: str, provider: str, *, sync_token: str = "", error: str = ""
    ):
        parts = ["updated_at = datetime('now')"]
        params: list = []
        if sync_token:
            parts.append("last_sync_token = ?")
            parts.append("last_sync_at = datetime('now')")
            params.extend([sync_token])
        if error:
            parts.append("sync_error = ?")
            params.append(error)
        else:
            parts.append("sync_error = NULL")
        params.extend([user_id, provider])
        conn = self._get_conn()
        conn.execute(
            f"UPDATE sync_state SET {', '.join(parts)} WHERE user_id = ? AND calendar_provider = ?",
            params,
        )
        conn.commit()

    # ---- training_plans / training_calendar_events 表操作 ----

    @staticmethod
    def _weekday_to_day_no(day_label: str) -> int:
        order = {"周一": 1, "周二": 2, "周三": 3, "周四": 4, "周五": 5, "周六": 6, "周日": 7}
        return order.get(str(day_label or "").strip(), 0)

    @staticmethod
    def _infer_workout_type(training_type: str, main_set: str) -> str:
        text = f"{training_type} {main_set}".lower()
        if "休息" in text or "rest" in text:
            return "rest"
        if "长距离" in text or "long" in text:
            return "long_run"
        if "间歇" in text or "interval" in text or "vo2" in text:
            return "interval"
        if "节奏" in text or "tempo" in text:
            return "tempo"
        if "恢复" in text or "recovery" in text:
            return "recovery"
        return "easy"

    @staticmethod
    def _infer_duration_min(main_set: str, workout_type: str) -> int:
        text = str(main_set or "")
        match = re.search(r"(\d+)\s*分钟", text)
        if match:
            return int(match.group(1))
        if workout_type == "rest":
            return 30
        if workout_type == "long_run":
            return 120
        return 60

    @staticmethod
    def _normalize_start_date(value: str = "") -> date:
        try:
            return date.fromisoformat(str(value or "").strip())
        except ValueError:
            return date.today()

    @staticmethod
    def _normalize_start_time(value: str = "") -> str:
        text = str(value or "").strip()
        return text if re.fullmatch(r"\d{2}:\d{2}", text) else "07:00"

    def _event_days_for_plan(
        self,
        plan: Dict[str, Any],
        calendar_days: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        if calendar_days:
            normalized = [day for day in calendar_days if isinstance(day, dict)]
            if normalized:
                return normalized

        rows: List[Dict[str, Any]] = []
        for week in plan.get("week_plans") or []:
            week_no = int(week.get("week_index") or 0)
            phase = str(week.get("phase") or "")
            load_level = str(week.get("load_level") or "")
            for index, day in enumerate(week.get("days") or [], start=1):
                if not isinstance(day, dict):
                    continue
                rows.append({
                    **day,
                    "week_index": int(day.get("week_index") or week_no),
                    "day_index": int(day.get("day_index") or index),
                    "phase": str(day.get("phase") or phase),
                    "load_level": str(day.get("load_level") or load_level),
                })
        return rows

    def save_training_plan(
        self,
        plan: Dict[str, Any],
        *,
        source_query: str = "",
        user_id: str = "default_user",
        calendar_days: Optional[List[Dict[str, Any]]] = None,
        training_start_date: str = "",
        default_start_time: str = "07:00",
    ) -> str:
        meta = plan.get("plan_meta") or {}
        plan_id = str(uuid.uuid4())
        start = self._normalize_start_date(training_start_date or str(meta.get("training_start_date") or ""))
        default_time = self._normalize_start_time(default_start_time or str(meta.get("default_start_time") or ""))
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO training_plans
                (id, user_id, goal, experience_level, requested_weeks, actual_weeks,
                 plan_type, start_date, target_race_date, status, source_query,
                 structured_plan_json, render_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)""",
            (
                plan_id,
                user_id,
                str(meta.get("goal") or "训练计划"),
                str(meta.get("experience_level") or ""),
                int(meta.get("requested_weeks") or len(plan.get("week_plans") or []) or 1),
                int(meta.get("actual_weeks") or len(plan.get("week_plans") or []) or 1),
                str(meta.get("plan_type") or "multi_week"),
                start.isoformat(),
                str(meta.get("target_race_date") or ""),
                source_query,
                json.dumps(plan, ensure_ascii=False),
                str(meta.get("render_version") or "v1"),
            ),
        )
        if calendar_days:
            grouped_weeks: Dict[int, Dict[str, Any]] = {}
            for index, raw_day in enumerate(calendar_days, start=1):
                if not isinstance(raw_day, dict):
                    continue
                week_no = int(raw_day.get("week_index") or ((index - 1) // 7 + 1))
                day_label = str(raw_day.get("day_label") or raw_day.get("day") or "")
                event_day = {
                    **raw_day,
                    "day": day_label,
                    "training_type": raw_day.get("training_type_label") or raw_day.get("training_type") or "",
                }
                grouped_weeks.setdefault(
                    week_no,
                    {
                        "week_index": week_no,
                        "phase": str(raw_day.get("phase") or ""),
                        "load_level": str(raw_day.get("load_level") or ""),
                        "days": [],
                    },
                )["days"].append(event_day)
            if grouped_weeks:
                plan = {
                    **plan,
                    "week_plans": [grouped_weeks[key] for key in sorted(grouped_weeks)],
                }
        for week in plan.get("week_plans") or []:
            week_no = int(week.get("week_index") or 0)
            phase = str(week.get("phase") or "")
            load_level = str(week.get("load_level") or "")
            for index, day in enumerate(week.get("days") or [], start=1):
                day_label = str(day.get("day") or "")
                day_no = self._weekday_to_day_no(day_label) or index
                event_date = start + timedelta(days=(week_no - 1) * 7 + day_no - 1)
                training_type = str(day.get("training_type") or "训练")
                main_set = str(day.get("main_set") or "")
                workout_type = self._infer_workout_type(training_type, main_set)
                duration_min = self._infer_duration_min(main_set, workout_type)
                event_id = str(uuid.uuid4())
                total_km = float(day.get("warmup_km") or 0) + float(day.get("main_km") or 0) + float(day.get("cooldown_km") or 0)
                event_start_time = self._normalize_start_time(str(day.get("start_time") or default_time))
                conn.execute(
                    """INSERT INTO training_calendar_events
                        (id, plan_id, user_id, week_no, day_no, day_label, scheduled_date,
                         start_time, duration_min, title, workout_type, intensity_zone, warmup, main_set,
                         cooldown, venue, notes, warmup_km, main_km, cooldown_km, total_km,
                         phase, load_level, content_json, ics_uid)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event_id,
                        plan_id,
                        user_id,
                        week_no,
                        day_no,
                        day_label,
                        event_date.isoformat(),
                        event_start_time,
                        duration_min,
                        f"第{week_no}周{day_label}｜{training_type}",
                        workout_type,
                        str(day.get("intensity_zone") or day.get("heart_rate_zone") or day.get("zone_range") or ""),
                        sanitize_all_pace(str(day.get("warmup") or "")),
                        sanitize_all_pace(main_set),
                        sanitize_all_pace(str(day.get("cooldown") or "")),
                        str(day.get("venue") or ""),
                        str(day.get("notes") or ""),
                        float(day.get("warmup_km") or 0),
                        float(day.get("main_km") or 0),
                        float(day.get("cooldown_km") or 0),
                        total_km,
                        phase,
                        load_level,
                        json.dumps(day, ensure_ascii=False),
                        f"{plan_id}-{week_no}-{day_no}",
                    ),
                )
        conn.commit()
        return plan_id

    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        row = self._get_conn().execute(
            "SELECT * FROM training_plans WHERE id = ?",
            (plan_id,),
        ).fetchone()
        return dict(row) if row else None

    def list_training_plans(self, user_id: str = "default_user") -> list:
        rows = self._get_conn().execute(
            "SELECT id, goal, experience_level, requested_weeks, actual_weeks, plan_type, start_date, target_race_date, status, source_query, created_at FROM training_plans WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_training_plan(self, plan_id: str) -> bool:
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT id FROM training_plans WHERE id = ?",
            (plan_id,),
        ).fetchone()
        if not existing:
            return False

        conn.execute("DELETE FROM training_event_feedback WHERE plan_id = ?", (plan_id,))
        conn.execute("DELETE FROM training_event_exceptions WHERE plan_id = ?", (plan_id,))
        conn.execute("DELETE FROM training_calendar_events WHERE plan_id = ?", (plan_id,))
        conn.execute("UPDATE sync_state SET plan_id = NULL WHERE plan_id = ?", (plan_id,))
        conn.execute("DELETE FROM training_plans WHERE id = ?", (plan_id,))
        conn.commit()
        return True

    def list_events(self, plan_id: str) -> list:
        rows = self._get_conn().execute(
            "SELECT * FROM training_calendar_events WHERE plan_id = ? ORDER BY week_no, day_no",
            (plan_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_unsynced_events(self, plan_id: str) -> list:
        rows = self._get_conn().execute(
            "SELECT * FROM training_calendar_events WHERE plan_id = ? AND sync_status = 'not_synced'",
            (plan_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_event_sync_status(
        self,
        event_id: str,
        *,
        external_event_id: str = "",
        sync_status: str = "synced",
        provider: str = "google",
    ):
        conn = self._get_conn()
        conn.execute(
            """UPDATE training_calendar_events SET
                external_event_id = ?, external_calendar_provider = ?,
                sync_status = ?, last_synced_at = datetime('now'),
                updated_at = datetime('now')
            WHERE id = ?""",
            (external_event_id, provider, sync_status, event_id),
        )
        conn.commit()

    def update_event_schedule(
        self,
        event_id: str,
        *,
        scheduled_date: str,
        start_time: str,
        duration_min: int,
    ) -> bool:
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT id FROM training_calendar_events WHERE id = ?",
            (event_id,),
        ).fetchone()
        if not existing:
            return False

        conn.execute(
            """UPDATE training_calendar_events SET
                scheduled_date = ?, start_time = ?, duration_min = ?,
                sync_status = 'not_synced', updated_at = datetime('now')
            WHERE id = ?""",
            (
                self._normalize_start_date(scheduled_date).isoformat(),
                self._normalize_start_time(start_time),
                int(duration_min or 0),
                event_id,
            ),
        )
        conn.commit()
        return True


_db_instance: Optional[_Database] = None


def get_db() -> _Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = _Database(DB_PATH)
    return _db_instance
