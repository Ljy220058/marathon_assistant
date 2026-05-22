-- Baseline marker for the existing SQLite schema.
-- The application still creates the current bootstrap schema before recording
-- this migration so legacy local databases keep opening without data loss.
SELECT '0001_initial';
