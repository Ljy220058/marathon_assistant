-- 移除 user_profiles 表的外键约束
-- SQLite 不支持 ALTER TABLE DROP CONSTRAINT，需要重建表
PRAGMA foreign_keys=OFF;

CREATE TABLE IF NOT EXISTS user_profiles_new (
    user_id        TEXT PRIMARY KEY,
    profile_json   TEXT NOT NULL DEFAULT '{}',
    schema_version INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO user_profiles_new (user_id, profile_json, schema_version, created_at, updated_at)
    SELECT user_id, profile_json, schema_version, created_at, updated_at FROM user_profiles;

DROP TABLE IF EXISTS user_profiles;

ALTER TABLE user_profiles_new RENAME TO user_profiles;

PRAGMA foreign_keys=ON;
