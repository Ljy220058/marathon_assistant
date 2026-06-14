CREATE TABLE IF NOT EXISTS session_memories (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    content       TEXT NOT NULL,
    source        TEXT NOT NULL DEFAULT 'llm_inferred',
    confidence    REAL NOT NULL DEFAULT 0.5,
    category      TEXT NOT NULL DEFAULT 'general',
    tags          TEXT DEFAULT '[]',
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_memories_user ON session_memories(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_memories_category ON session_memories(user_id, category);
