import json
import hashlib
import re
import sqlite3
import threading
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from marathon_qa_assistant.core.app_state import RUNTIME_DATA_DIR
from marathon_qa_assistant.core.settings import get_settings
from marathon_qa_assistant.core.zone_constants import sanitize_all_pace

def _get_fernet():
    """惰性加载 Fernet 加密器，密钥从环境变量读取。"""
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return None
    key = get_settings().fernet_key
    if not key:
        return None
    try:
        return Fernet(key.encode("utf-8"))
    except Exception:
        return None


def _encrypt_token(token: str) -> str:
    if not token:
        return ""
    fernet = _get_fernet()
    if fernet is None:
        if get_settings().is_production:
            raise RuntimeError("MARATHON_FERNET_KEY is required to store tokens in production.")
        return token
    return fernet.encrypt(token.encode("utf-8")).decode("utf-8")


def _decrypt_token(encrypted: str) -> str:
    if not encrypted:
        return ""
    fernet = _get_fernet()
    if fernet is None:
        return encrypted
    try:
        return fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
    except Exception:
        return encrypted

DB_PATH = RUNTIME_DATA_DIR / "marathon_assistant.db"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
SQLITE_BUSY_TIMEOUT_MS = 5000


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
    lineage_id      TEXT,
    version         INTEGER NOT NULL DEFAULT 1,
    parent_plan_id  TEXT,
    parent_version  INTEGER,
    trigger         TEXT NOT NULL DEFAULT 'initial',
    trigger_detail  TEXT,
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
    risk_gate_json      TEXT,
    protocol_recheck_json TEXT,
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
            conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
            self._local.conn = conn
        return self._local.conn

    def _init_schema(self):
        conn = self._get_conn()
        self._preflight_legacy_schema(conn)
        conn.executescript(SCHEMA_SQL)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now')),
                checksum TEXT NOT NULL
            )
            """
        )
        self._ensure_schema_migrations_checksum(conn)
        self._ensure_columns(
            conn,
            "training_event_feedback",
            {
                "risk_gate_json": "TEXT",
                "protocol_recheck_json": "TEXT",
            },
        )
        self._ensure_columns(
            conn,
            "training_plans",
            {
                "lineage_id": "TEXT",
                "version": "INTEGER NOT NULL DEFAULT 1",
                "parent_plan_id": "TEXT",
                "parent_version": "INTEGER",
                "trigger": "TEXT NOT NULL DEFAULT 'initial'",
                "trigger_detail": "TEXT",
            },
        )
        conn.execute(
            "UPDATE training_plans SET lineage_id = id WHERE lineage_id IS NULL OR lineage_id = ''"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_training_plans_lineage_version ON training_plans(lineage_id, version)"
        )
        # 多用户支持：users 表独立迁移，避免 executescript 冲突
        if not self._table_exists(conn, "users"):
            conn.execute(
                """
                CREATE TABLE users (
                    id                    TEXT PRIMARY KEY,
                    display_name          TEXT NOT NULL,
                    api_token_hash        TEXT NOT NULL UNIQUE,
                    is_active             INTEGER NOT NULL DEFAULT 1,
                    created_at            TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at            TEXT NOT NULL DEFAULT (datetime('now')),
                    birth_year            INTEGER,
                    age_gate_passed_at    TEXT,
                    privacy_consent_at    TEXT,
                    health_data_consent_at TEXT,
                    terms_accepted_at     TEXT
                )
                """
            )
            conn.execute("CREATE INDEX idx_users_token_hash ON users(api_token_hash)")
        else:
            self._ensure_columns(
                conn,
                "users",
                {
                    "display_name": "TEXT NOT NULL DEFAULT ''",
                    "api_token_hash": "TEXT",
                    "is_active": "INTEGER NOT NULL DEFAULT 1",
                    "created_at": "TEXT",
                    "updated_at": "TEXT",
                    "birth_year": "INTEGER",
                    "age_gate_passed_at": "TEXT",
                    "privacy_consent_at": "TEXT",
                    "health_data_consent_at": "TEXT",
                    "terms_accepted_at": "TEXT",
                },
            )
            # Ensure unique constraint on api_token_hash via index
            existing_indexes = {
                row["name"]
                for row in conn.execute("PRAGMA index_list(users)").fetchall()
            }
            if "idx_users_token_hash" not in existing_indexes:
                try:
                    conn.execute("CREATE UNIQUE INDEX idx_users_token_hash ON users(api_token_hash)")
                except Exception:
                    pass
        # users 表已就绪后再跑 migrations：0007_consent_version 需要 ALTER TABLE users。
        # 原顺序 _apply_migrations 在建 users 之前，导致全新 DB 初始化时 0007 报 no such table: users。
        self._apply_migrations(conn)
        conn.commit()

    def _table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        return row is not None

    def _preflight_legacy_schema(self, conn: sqlite3.Connection):
        if self._table_exists(conn, "training_calendar_events"):
            self._ensure_columns(
                conn,
                "training_calendar_events",
                {
                    "warmup_km": "REAL DEFAULT 0",
                    "main_km": "REAL DEFAULT 0",
                    "cooldown_km": "REAL DEFAULT 0",
                    "total_km": "REAL DEFAULT 0",
                    "evidence_ids": "TEXT",
                    "phase": "TEXT",
                    "load_level": "TEXT",
                    "ics_uid": "TEXT",
                    "external_event_id": "TEXT",
                    "external_calendar_provider": "TEXT",
                    "sync_status": "TEXT DEFAULT 'not_synced'",
                    "last_synced_at": "TEXT",
                    "created_at": "TEXT",
                    "updated_at": "TEXT",
                },
            )

    def _ensure_schema_migrations_checksum(self, conn: sqlite3.Connection):
        if not self._table_exists(conn, "schema_migrations"):
            return
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(schema_migrations)").fetchall()}
        if "checksum" not in columns:
            conn.execute("ALTER TABLE schema_migrations ADD COLUMN checksum TEXT")
        if not MIGRATIONS_DIR.exists():
            return
        migration_checksums = {
            path.stem: hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
            for path in sorted(MIGRATIONS_DIR.glob("*.sql"))
        }
        for version, checksum in migration_checksums.items():
            conn.execute(
                "UPDATE schema_migrations SET checksum = ? WHERE version = ? AND (checksum IS NULL OR checksum = '')",
                (checksum, version),
            )

    def _apply_migrations(self, conn: sqlite3.Connection):
        if not MIGRATIONS_DIR.exists():
            return

        applied = {
            row["version"]: row["checksum"]
            for row in conn.execute("SELECT version, checksum FROM schema_migrations").fetchall()
        }
        for migration_path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            version = migration_path.stem
            sql = migration_path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
            if version in applied:
                if applied[version] != checksum:
                    raise RuntimeError(
                        f"Applied migration {version} checksum mismatch. "
                        "Do not edit migration files after they have been applied; create a new migration instead."
                    )
                continue
            if sql.strip():
                conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations (version, checksum) VALUES (?, ?)",
                (version, checksum),
            )

    def _ensure_columns(self, conn: sqlite3.Connection, table_name: str, columns: Dict[str, str]):
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
        for column_name, column_type in columns.items():
            if column_name not in existing:
                conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    def health_check(self) -> bool:
        try:
            self._get_conn().execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False

    # ---- 用户管理 ----

    @staticmethod
    def _hash_api_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_api_token() -> str:
        return f"mara-{uuid.uuid4().hex}"

    def create_user(self, display_name: str, *, birth_year: Optional[int] = None) -> Dict[str, Any]:
        user_id = f"user-{uuid.uuid4().hex[:12]}"
        token = self.generate_api_token()
        conn = self._get_conn()

        age_gate_passed_at = None
        if birth_year is not None:
            from datetime import date as _date
            age = _date.today().year - int(birth_year)
            if age < 14:
                raise ValueError(f"用户年龄不满 14 岁（出生年份 {birth_year}），不符合注册条件。")
            if age < 18:
                pass  # 14-17 岁：允许注册，需监护人同意（由前端流程保障）
            age_gate_passed_at = f"datetime('now')"

        conn.execute(
            "INSERT INTO users (id, display_name, api_token_hash, birth_year, age_gate_passed_at) VALUES (?, ?, ?, ?, ?)",
            (
                user_id,
                display_name,
                self._hash_api_token(token),
                birth_year,
                None if age_gate_passed_at is None else "now",
            ),
        )
        conn.commit()
        return {"user_id": user_id, "display_name": display_name, "api_token": token}

    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        row = self._get_conn().execute(
            "SELECT * FROM users WHERE api_token_hash = ? AND is_active = 1",
            (self._hash_api_token(token),),
        ).fetchone()
        return dict(row) if row else None

    def list_users(self) -> list:
        rows = self._get_conn().execute(
            "SELECT id, display_name, is_active, created_at FROM users ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def record_user_consent(
        self,
        user_id: str,
        *,
        privacy_consent: bool = False,
        health_data_consent: bool = False,
        terms_accepted: bool = False,
        consent_version: str = "v1.0",
    ) -> bool:
        parts = ["updated_at = datetime('now')"]
        if privacy_consent:
            parts.append("privacy_consent_at = datetime('now')")
        if health_data_consent:
            parts.append("health_data_consent_at = datetime('now')")
        if terms_accepted:
            parts.append("terms_accepted_at = datetime('now')")
        if consent_version:
            parts.append(f"consent_version = '{consent_version}'")
        if len(parts) == 1:
            return False
        conn = self._get_conn()
        conn.execute(
            f"UPDATE users SET {', '.join(parts)} WHERE id = ? AND is_active = 1",
            (user_id,),
        )
        conn.commit()
        return conn.total_changes > 0

    def get_user_compliance(self, user_id: str) -> Optional[Dict[str, Any]]:
        row = self._get_conn().execute(
            """SELECT id, birth_year, age_gate_passed_at,
                      privacy_consent_at, health_data_consent_at, terms_accepted_at
               FROM users WHERE id = ? AND is_active = 1""",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        age_gate_passed = bool(data.get("age_gate_passed_at"))
        privacy_consented = bool(data.get("privacy_consent_at"))
        health_data_consented = bool(data.get("health_data_consent_at"))
        terms_ok = bool(data.get("terms_accepted_at"))
        missing = []
        if not age_gate_passed:
            missing.append("age_gate")
        if not privacy_consented:
            missing.append("privacy_consent")
        if not health_data_consented:
            missing.append("health_data_consent")
        if not terms_ok:
            missing.append("terms_accepted")
        return {
            "user_id": user_id,
            "birth_year": data.get("birth_year"),
            "age_gate_passed": age_gate_passed,
            "privacy_consented": privacy_consented,
            "health_data_consented": health_data_consented,
            "terms_accepted": terms_ok,
            "compliance_complete": not missing,
            "missing": missing,
        }

    def deactivate_user(self, user_id: str) -> bool:
        conn = self._get_conn()
        conn.execute(
            "UPDATE users SET is_active = 0, updated_at = datetime('now') WHERE id = ?",
            (user_id,),
        )
        conn.commit()
        return conn.total_changes > 0

    def has_any_user(self) -> bool:
        row = self._get_conn().execute(
            "SELECT COUNT(*) as cnt FROM users WHERE is_active = 1"
        ).fetchone()
        return (row["cnt"] if row else 0) > 0

    def ensure_default_user(self) -> str:
        """初始化时确保至少有一个默认用户。"""
        if self.has_any_user():
            return "existing_users_found"
        result = self.create_user("默认用户")
        return result["user_id"]

    # ---- sync_state 表操作 ----

    def load_sync_token(self, user_id: str, provider: str) -> Optional[Dict[str, Any]]:
        row = self._get_conn().execute(
            "SELECT * FROM sync_state WHERE user_id = ? AND calendar_provider = ?",
            (user_id, provider),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["oauth_access_token"] = _decrypt_token(str(data.get("oauth_access_token") or ""))
        data["oauth_refresh_token"] = _decrypt_token(str(data.get("oauth_refresh_token") or ""))
        return data

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
                    _encrypt_token(str(data.get("oauth_access_token") or "")),
                    _encrypt_token(str(data.get("oauth_refresh_token") or "")),
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
                    _encrypt_token(str(data.get("oauth_access_token") or "")),
                    _encrypt_token(str(data.get("oauth_refresh_token") or "")),
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
        lineage_id: str = "",
        parent_plan_id: str = "",
        trigger: str = "initial",
        trigger_detail: str = "",
    ) -> str:
        meta = plan.get("plan_meta") or {}
        plan_id = str(uuid.uuid4())
        start = self._normalize_start_date(training_start_date or str(meta.get("training_start_date") or ""))
        default_time = self._normalize_start_time(default_start_time or str(meta.get("default_start_time") or ""))
        conn = self._get_conn()
        try:
            parent_plan = self.get_plan(parent_plan_id) if parent_plan_id else None
            if parent_plan:
                lineage_id = str(lineage_id or parent_plan.get("lineage_id") or parent_plan.get("id") or "")
                parent_version = int(parent_plan.get("version") or 1)
            else:
                parent_version = None
            lineage_id = str(lineage_id or plan_id)
            row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) AS max_version FROM training_plans WHERE lineage_id = ?",
                (lineage_id,),
            ).fetchone()
            plan_version = int(row["max_version"] or 0) + 1
            trigger_value = str(trigger or ("initial" if plan_version == 1 else "manual"))
            conn.execute(
                """INSERT INTO training_plans
                    (id, lineage_id, version, parent_plan_id, parent_version, trigger, trigger_detail,
                     user_id, goal, experience_level, requested_weeks, actual_weeks,
                     plan_type, start_date, target_race_date, status, source_query,
                     structured_plan_json, render_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)""",
                (
                    plan_id,
                    lineage_id,
                    plan_version,
                    str(parent_plan_id or ""),
                    parent_version,
                    trigger_value,
                    str(trigger_detail or ""),
                    user_id,
                    str(meta.get("goal") or "????"),
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
                    training_type = str(day.get("training_type") or "??")
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
                            f"\u7b2c{week_no}\u5468{day_label}\uff5c{training_type}",
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
        except Exception:
            conn.rollback()
            raise

    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        row = self._get_conn().execute(
            "SELECT * FROM training_plans WHERE id = ?",
            (plan_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_plan_version(self, lineage_id: str, version: int) -> Optional[Dict[str, Any]]:
        row = self._get_conn().execute(
            "SELECT * FROM training_plans WHERE lineage_id = ? AND version = ?",
            (lineage_id, int(version)),
        ).fetchone()
        return dict(row) if row else None

    def list_plan_versions(self, plan_id: str) -> List[Dict[str, Any]]:
        plan = self.get_plan(plan_id)
        if not plan:
            return []
        lineage_id = str(plan.get("lineage_id") or plan.get("id") or "")
        rows = self._get_conn().execute(
            """SELECT id, lineage_id, version, parent_plan_id, parent_version, trigger,
                      trigger_detail, goal, status, source_query, created_at
               FROM training_plans
               WHERE lineage_id = ?
               ORDER BY version ASC""",
            (lineage_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def rollback_training_plan(
        self,
        plan_id: str,
        to_version: int,
        *,
        user_id: str = "default_user",
        trigger_detail: str = "",
    ) -> str:
        current = self.get_plan(plan_id)
        if not current or current.get("user_id") != user_id:
            raise ValueError("training plan not found")
        lineage_id = str(current.get("lineage_id") or current.get("id") or "")
        target = self.get_plan_version(lineage_id, int(to_version))
        if not target or target.get("user_id") != user_id:
            raise ValueError("target plan version not found")
        try:
            structured_plan = json.loads(target.get("structured_plan_json") or "{}")
        except Exception as exc:
            raise ValueError("target plan version has invalid structured_plan_json") from exc
        if not isinstance(structured_plan, dict):
            raise ValueError("target plan version has invalid structured_plan_json")

        detail = trigger_detail or f"rollback to version {int(to_version)}"
        return self.save_training_plan(
            structured_plan,
            source_query=str(target.get("source_query") or ""),
            user_id=user_id,
            training_start_date=str(target.get("start_date") or ""),
            lineage_id=lineage_id,
            parent_plan_id=str(target.get("id") or ""),
            trigger="manual_rollback",
            trigger_detail=detail,
        )

    def list_training_plans(self, user_id: str = "default_user") -> list:
        rows = self._get_conn().execute(
            """SELECT id, lineage_id, version, parent_plan_id, parent_version, trigger,
                      trigger_detail, goal, experience_level, requested_weeks, actual_weeks,
                      plan_type, start_date, target_race_date, status, source_query, created_at
               FROM training_plans
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT 20""",
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

    def get_event(self, plan_id: str, event_id: str, user_id: str = "default_user") -> Optional[Dict[str, Any]]:
        row = self._get_conn().execute(
            "SELECT * FROM training_calendar_events WHERE plan_id = ? AND id = ? AND user_id = ?",
            (plan_id, event_id, user_id),
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def _feedback_summary(row: sqlite3.Row) -> Dict[str, Any]:
        data = dict(row)
        try:
            reason_codes = json.loads(data.get("adaptive_reason_codes") or "[]")
        except Exception:
            reason_codes = []
        if not isinstance(reason_codes, list):
            reason_codes = []
        try:
            risk_gate = json.loads(data.get("risk_gate_json") or "{}")
        except Exception:
            risk_gate = {}
        if not isinstance(risk_gate, dict):
            risk_gate = {}
        try:
            protocol_recheck = json.loads(data.get("protocol_recheck_json") or "{}")
        except Exception:
            protocol_recheck = {}
        if not isinstance(protocol_recheck, dict):
            protocol_recheck = {}
        return {
            "id": data.get("id"),
            "feedback_id": data.get("id"),
            "event_id": data.get("event_id"),
            "plan_id": data.get("plan_id"),
            "user_id": data.get("user_id"),
            "completion_status": data.get("completion_status"),
            "completion_quality": data.get("completion_quality"),
            "subjective_fatigue": data.get("subjective_fatigue"),
            "pain_status": data.get("pain_status"),
            "sleep_quality": data.get("sleep_quality"),
            "notes": data.get("user_notes"),
            "raw_text": data.get("raw_feedback_text"),
            "reason_codes": reason_codes,
            "next_day_adjustment": data.get("next_day_adjustment"),
            "weekly_adjustment": data.get("weekly_adjustment"),
            "alternative_workout": data.get("alternative_workout"),
            "risk_alert": data.get("risk_alert"),
            "rationale": data.get("adjustment_rationale"),
            "risk_gate": risk_gate,
            "protocol_recheck": protocol_recheck,
            "created_at": data.get("created_at"),
        }

    def save_training_event_feedback(
        self,
        *,
        plan_id: str,
        event_id: str,
        user_id: str = "default_user",
        workout_feedback: Dict[str, Any],
        reason_codes: List[str],
        adaptive_adjustment: Dict[str, Any],
        risk_gate: Dict[str, Any],
        protocol_recheck: Optional[Dict[str, Any]] = None,
        raw_text: str = "",
    ) -> Optional[str]:
        if not self.get_event(plan_id, event_id, user_id):
            return None

        feedback_id = str(uuid.uuid4())
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO training_event_feedback
                (id, event_id, plan_id, user_id, completion_status, completion_quality,
                 subjective_fatigue, pain_status, sleep_quality, user_notes, raw_feedback_text,
                 adaptive_reason_codes, next_day_adjustment, weekly_adjustment,
                 alternative_workout, risk_alert, adjustment_rationale,
                 risk_gate_json, protocol_recheck_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                feedback_id,
                event_id,
                plan_id,
                user_id,
                str(workout_feedback.get("completion_status") or "completed"),
                str(workout_feedback.get("completion_quality") or ""),
                str(workout_feedback.get("subjective_fatigue") or ""),
                str(workout_feedback.get("pain_status") or ""),
                str(workout_feedback.get("sleep_quality") or ""),
                str(workout_feedback.get("notes") or ""),
                str(raw_text or ""),
                json.dumps(list(reason_codes or []), ensure_ascii=False),
                str(adaptive_adjustment.get("next_day_adjustment") or ""),
                str(adaptive_adjustment.get("weekly_adjustment") or ""),
                str(adaptive_adjustment.get("alternative_workout") or ""),
                str(adaptive_adjustment.get("risk_alert") or risk_gate.get("decision_reason") or ""),
                str(adaptive_adjustment.get("rationale") or ""),
                json.dumps(dict(risk_gate or {}), ensure_ascii=False),
                json.dumps(dict(protocol_recheck or {}), ensure_ascii=False),
            ),
        )
        conn.commit()
        return feedback_id

    @staticmethod
    def _event_content(row: Dict[str, Any]) -> Dict[str, Any]:
        raw = row.get("content_json")
        if isinstance(raw, dict):
            return dict(raw)
        if isinstance(raw, str) and raw.strip():
            try:
                parsed = json.loads(raw)
            except Exception:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}

    @staticmethod
    def _future_feedback_effect(
        event: Dict[str, Any],
        *,
        feedback_id: str,
        reason_codes: List[str],
        adaptive_adjustment: Dict[str, Any],
        risk_gate: Dict[str, Any],
    ) -> Dict[str, Any]:
        medical_referral = str(risk_gate.get("product_status") or "") == "medical_referral"
        original_main_set = str(event.get("main_set") or "")
        instruction = str(adaptive_adjustment.get("next_day_adjustment") or adaptive_adjustment.get("alternative_workout") or "")
        if medical_referral:
            instruction = "停止训练，先进行专业医疗评估；评估通过前不继续原计划主课。"
        return {
            "source_feedback_id": feedback_id,
            "reason_codes": list(reason_codes or []),
            "reason": str(adaptive_adjustment.get("rationale") or risk_gate.get("decision_reason") or "训练反馈触发后续调整。"),
            "action": "stop_for_medical_referral" if medical_referral else "downgrade",
            "original_main_set": original_main_set,
            "adjusted_instruction": instruction,
            "risk_status": str(risk_gate.get("product_status") or "generated"),
        }

    def apply_feedback_effect_to_future_events(
        self,
        *,
        plan_id: str,
        event_id: str,
        user_id: str = "default_user",
        feedback_id: str,
        reason_codes: List[str],
        adaptive_adjustment: Dict[str, Any],
        risk_gate: Dict[str, Any],
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        rows = self.list_events(plan_id)
        index = next((idx for idx, row in enumerate(rows) if str(row.get("id")) == str(event_id)), -1)
        if index < 0 or not feedback_id:
            return []
        status = str(risk_gate.get("product_status") or "generated")
        needs_adjustment = status == "medical_referral" or bool(reason_codes or adaptive_adjustment.get("adjustment_required"))
        if not needs_adjustment:
            return []

        conn = self._get_conn()
        affected: List[Dict[str, Any]] = []
        for row in rows[index + 1 :]:
            if str(row.get("user_id") or "") != user_id:
                continue
            if str(row.get("workout_type") or "").lower() == "rest":
                continue
            old_content = self._event_content(row)
            effect = self._future_feedback_effect(
                row,
                feedback_id=feedback_id,
                reason_codes=reason_codes,
                adaptive_adjustment=adaptive_adjustment,
                risk_gate=risk_gate,
            )
            # 只叠加反馈影响层，保留原主课，避免把降级提示误写成新处方。
            new_content = dict(old_content)
            new_content["feedback_effect"] = effect
            new_content["latest_feedback_effect"] = effect
            new_content["card_status"] = "medical_referral" if effect["action"] == "stop_for_medical_referral" else "feedback_adjusted"
            new_content["generation_status"] = new_content["card_status"]
            new_content["adjustment_hint"] = effect["adjusted_instruction"]
            conn.execute(
                """UPDATE training_calendar_events SET
                    content_json = ?, sync_status = 'not_synced', updated_at = datetime('now')
                WHERE id = ?""",
                (json.dumps(new_content, ensure_ascii=False), row.get("id")),
            )
            conn.execute(
                """INSERT INTO training_event_exceptions
                    (id, event_id, plan_id, user_id, exception_type, reason,
                     old_scheduled_date, new_scheduled_date, old_start_time, new_start_time,
                     old_content_json, new_content_json, is_applied)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (
                    str(uuid.uuid4()),
                    row.get("id"),
                    plan_id,
                    user_id,
                    "feedback_effect",
                    ",".join(reason_codes or []),
                    row.get("scheduled_date"),
                    row.get("scheduled_date"),
                    row.get("start_time"),
                    row.get("start_time"),
                    row.get("content_json") or json.dumps(old_content, ensure_ascii=False),
                    json.dumps(new_content, ensure_ascii=False),
                ),
            )
            affected.append(
                {
                    "event_id": row.get("id"),
                    "day_label": row.get("day_label"),
                    "scheduled_date": row.get("scheduled_date"),
                    "title": row.get("title"),
                    "workout_type": row.get("workout_type"),
                    "feedback_effect": effect,
                }
            )
            if len(affected) >= limit:
                break
        conn.commit()
        return affected

    def get_latest_event_feedback(self, event_id: str) -> Optional[Dict[str, Any]]:
        row = self._get_conn().execute(
            "SELECT * FROM training_event_feedback WHERE event_id = ? ORDER BY created_at DESC, rowid DESC LIMIT 1",
            (event_id,),
        ).fetchone()
        return self._feedback_summary(row) if row else None

    def save_feedback_replan(
        self,
        *,
        plan_id: str,
        feedback_id: str,
        user_id: str,
        feedback_replan: Dict[str, Any],
        apply_patch: bool = False,
        exception_type: str = "feedback_replan_suggested",
    ) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        affected: List[Dict[str, Any]] = []
        try:
            for patch in feedback_replan.get("patches") or []:
                event_id = str(patch.get("event_id") or "")
                row = self.get_event(plan_id, event_id, user_id)
                if not row:
                    continue
                old_content = self._event_content(row)
                new_content = dict(old_content)
                event_replan = dict(feedback_replan)
                event_replan["patches"] = [patch]
                if apply_patch:
                    event_replan["status"] = "applied"
                    suggested = patch.get("suggested") or {}
                    new_content["card_status"] = "feedback_replan_applied"
                    new_content["generation_status"] = "feedback_replan_applied"
                    new_content["adjustment_hint"] = str(suggested.get("main_set") or "")
                new_content["feedback_replan"] = event_replan
                conn.execute(
                    """UPDATE training_calendar_events SET
                        content_json = ?, sync_status = 'not_synced', updated_at = datetime('now')
                    WHERE id = ?""",
                    (json.dumps(new_content, ensure_ascii=False), event_id),
                )
                conn.execute(
                    """INSERT INTO training_event_exceptions
                        (id, event_id, plan_id, user_id, exception_type, reason,
                         old_scheduled_date, new_scheduled_date, old_start_time, new_start_time,
                         old_content_json, new_content_json, is_applied)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(uuid.uuid4()),
                        event_id,
                        plan_id,
                        user_id,
                        exception_type,
                        str(feedback_id),
                        row.get("scheduled_date"),
                        row.get("scheduled_date"),
                        row.get("start_time"),
                        row.get("start_time"),
                        row.get("content_json") or json.dumps(old_content, ensure_ascii=False),
                        json.dumps(new_content, ensure_ascii=False),
                        1 if apply_patch else 0,
                    ),
                )
                affected.append({"event_id": event_id, "feedback_replan": event_replan})
            conn.commit()
            return affected
        except Exception:
            conn.rollback()
            raise

    def list_plan_feedback(self, plan_id: str) -> list:
        rows = self._get_conn().execute(
            "SELECT * FROM training_event_feedback WHERE plan_id = ? ORDER BY created_at DESC, rowid DESC",
            (plan_id,),
        ).fetchall()
        return [self._feedback_summary(row) for row in rows]

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

    # ---- user_profiles 表操作 ----

    def load_profile(self, user_id: str) -> Optional[str]:
        row = self._get_conn().execute(
            "SELECT profile_json FROM user_profiles WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return row["profile_json"] if row else None

    def save_profile(self, user_id: str, profile_json: str) -> None:
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT user_id FROM user_profiles WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE user_profiles SET profile_json = ?, updated_at = datetime('now') WHERE user_id = ?",
                (profile_json, user_id),
            )
        else:
            conn.execute(
                "INSERT INTO user_profiles (user_id, profile_json) VALUES (?, ?)",
                (user_id, profile_json),
            )
        conn.commit()

    def delete_profile(self, user_id: str) -> bool:
        conn = self._get_conn()
        conn.execute("DELETE FROM user_profiles WHERE user_id = ?", (user_id,))
        conn.commit()
        return conn.total_changes > 0


_db_instance: Optional[_Database] = None


def get_db() -> _Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = _Database(DB_PATH)
    return _db_instance
