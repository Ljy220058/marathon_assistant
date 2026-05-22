import json
import sqlite3
import pytest

from marathon_qa_assistant.services import database as database_module
from marathon_qa_assistant.services.database import _Database


def _create_old_feedback_db(path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE training_plans (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL DEFAULT 'default_user',
            goal TEXT NOT NULL,
            experience_level TEXT,
            requested_weeks INTEGER NOT NULL,
            actual_weeks INTEGER NOT NULL,
            plan_type TEXT NOT NULL,
            start_date TEXT,
            target_race_date TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            source_query TEXT,
            structured_plan_json TEXT,
            render_version TEXT DEFAULT 'v1',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE training_calendar_events (
            id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            user_id TEXT NOT NULL DEFAULT 'default_user',
            week_no INTEGER NOT NULL,
            day_no INTEGER NOT NULL,
            day_label TEXT NOT NULL,
            scheduled_date TEXT,
            start_time TEXT,
            duration_min INTEGER,
            title TEXT NOT NULL,
            workout_type TEXT NOT NULL,
            intensity_zone TEXT,
            warmup TEXT,
            main_set TEXT,
            cooldown TEXT,
            venue TEXT,
            notes TEXT,
            content_json TEXT,
            status TEXT NOT NULL DEFAULT 'planned'
        );
        CREATE TABLE training_event_feedback (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            plan_id TEXT NOT NULL,
            user_id TEXT NOT NULL DEFAULT 'default_user',
            completion_status TEXT NOT NULL,
            completion_quality TEXT,
            subjective_fatigue TEXT,
            pain_status TEXT,
            sleep_quality TEXT,
            user_notes TEXT,
            raw_feedback_text TEXT,
            adaptive_reason_codes TEXT,
            next_day_adjustment TEXT,
            weekly_adjustment TEXT,
            alternative_workout TEXT,
            risk_alert TEXT,
            adjustment_rationale TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO training_plans
            (id, user_id, goal, requested_weeks, actual_weeks, plan_type, structured_plan_json)
        VALUES
            ('plan-1', 'default_user', 'legacy plan', 1, 1, 'single_week', '{}');
        INSERT INTO training_calendar_events
            (id, plan_id, user_id, week_no, day_no, day_label, title, workout_type, content_json)
        VALUES
            ('event-1', 'plan-1', 'default_user', 1, 1, 'Mon', 'Easy', 'easy', '{}');
        INSERT INTO training_event_feedback
            (id, event_id, plan_id, user_id, completion_status, adaptive_reason_codes, next_day_adjustment)
        VALUES
            ('feedback-1', 'event-1', 'plan-1', 'default_user', 'completed', '[]', 'keep easy');
        """
    )
    conn.commit()
    conn.close()


def _create_old_schema_migrations_db(path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO schema_migrations (version) VALUES ('0001_initial');
        """
    )
    conn.commit()
    conn.close()


def test_database_applies_schema_migrations_to_empty_db(tmp_path):
    db = _Database(tmp_path / "empty.db")
    conn = db._get_conn()

    versions = [
        row["version"]
        for row in conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
    ]

    assert "0001_initial" in versions
    assert "0002_feedback_audit_fields" in versions
    assert conn.execute("PRAGMA table_info(training_event_feedback)").fetchall()


def test_database_migrates_legacy_feedback_audit_fields(tmp_path):
    db_path = tmp_path / "legacy.db"
    _create_old_feedback_db(db_path)

    db = _Database(db_path)
    columns = {
        row["name"]
        for row in db._get_conn().execute("PRAGMA table_info(training_event_feedback)").fetchall()
    }

    assert "risk_gate_json" in columns
    assert "protocol_recheck_json" in columns
    latest = db.get_latest_event_feedback("event-1")
    assert latest["feedback_id"] == "feedback-1"
    assert latest["risk_gate"] == {}
    assert latest["protocol_recheck"] == {}


def test_database_migrates_legacy_schema_migrations_checksum_column(tmp_path, monkeypatch):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    migration_path = migrations_dir / "0001_initial.sql"
    migration_sql = "CREATE TABLE IF NOT EXISTS legacy_marker (id TEXT PRIMARY KEY);\n"
    migration_path.write_text(migration_sql, encoding="utf-8")
    monkeypatch.setattr(database_module, "MIGRATIONS_DIR", migrations_dir)

    db_path = tmp_path / "legacy_schema_migrations.db"
    _create_old_schema_migrations_db(db_path)

    db = _Database(db_path)
    rows = db._get_conn().execute("SELECT version, checksum FROM schema_migrations").fetchall()

    assert rows[0]["version"] == "0001_initial"
    assert rows[0]["checksum"]


def test_database_migrates_legacy_calendar_event_sync_status(tmp_path):
    db_path = tmp_path / "legacy_sync_status.db"
    _create_old_feedback_db(db_path)

    db = _Database(db_path)
    columns = {
        row["name"]
        for row in db._get_conn().execute("PRAGMA table_info(training_calendar_events)").fetchall()
    }

    assert "sync_status" in columns
    row = db._get_conn().execute("SELECT sync_status FROM training_calendar_events WHERE id = 'event-1'").fetchone()
    assert row["sync_status"] == "not_synced"


def test_database_migration_is_idempotent_and_feedback_still_writes(tmp_path):
    db_path = tmp_path / "idempotent.db"
    db = _Database(db_path)
    db.close()
    db = _Database(db_path)

    plan = {
        "plan_meta": {"goal": "migration feedback", "actual_weeks": 1, "requested_weeks": 1},
        "week_plans": [
            {
                "week_index": 1,
                "days": [{"day": "周一", "training_type": "Easy", "main_set": "30 min"}],
            }
        ],
    }
    plan_id = db.save_training_plan(plan)
    event_id = db.list_events(plan_id)[0]["id"]
    feedback_id = db.save_training_event_feedback(
        plan_id=plan_id,
        event_id=event_id,
        workout_feedback={"completion_status": "completed"},
        reason_codes=["mild_fatigue"],
        adaptive_adjustment={"next_day_adjustment": "easy"},
        risk_gate={"status": "passed"},
        protocol_recheck={"allowed": True},
    )

    latest = db.get_latest_event_feedback(event_id)
    assert latest["feedback_id"] == feedback_id
    assert latest["reason_codes"] == ["mild_fatigue"]
    assert latest["risk_gate"]["status"] == "passed"
    assert latest["protocol_recheck"]["allowed"] is True

    stored_versions = db._get_conn().execute("SELECT version, checksum FROM schema_migrations").fetchall()
    assert all(row["checksum"] for row in stored_versions)


def test_database_rejects_modified_applied_migration(tmp_path, monkeypatch):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    migration_path = migrations_dir / "0001_initial.sql"
    migration_path.write_text(
        "CREATE TABLE migration_guard (id TEXT PRIMARY KEY);\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(database_module, "MIGRATIONS_DIR", migrations_dir)

    db_path = tmp_path / "checksum.db"
    _Database(db_path).close()

    migration_path.write_text(
        "CREATE TABLE migration_guard (id TEXT PRIMARY KEY, edited TEXT);\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        _Database(db_path)
