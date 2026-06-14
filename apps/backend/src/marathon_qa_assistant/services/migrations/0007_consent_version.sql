-- 添加同意版本号到 users 表
ALTER TABLE users ADD COLUMN consent_version TEXT DEFAULT 'v1.0';
