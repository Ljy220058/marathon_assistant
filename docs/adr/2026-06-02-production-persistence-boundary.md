# ADR 2026-06-02: Production Persistence Boundary

## Status

Accepted

## Context

当前计划、反馈、同步状态等核心数据都存放在本地 SQLite 中，底层实现位于 `apps/backend/src/marathon_qa_assistant/services/database.py`。

2026-06-02 审计指出：

- SQLite 适合本地 MVP，但不应被描述成商业化多用户生产存储
- 需要至少明确 `busy_timeout`、健康探针和迁移 checksum 边界
- 文档不能暗示“当前已具备商业级多实例持久化”

## Decision

1. 当前 SQLite scope 明确限定为：
   - 本地开发
   - 单机 MVP
   - 开发者预览 / 受控演示
2. 当前实现保留以下最小安全与一致性边界：
   - `PRAGMA journal_mode=WAL`
   - `PRAGMA foreign_keys=ON`
   - `PRAGMA busy_timeout=5000`
   - `schema_migrations(version, checksum)` 校验
   - 轻量 `health_check()`
3. 不把当前 SQLite 实现描述为：
   - 多实例一致写入方案
   - 商业级多用户生产数据库
   - 完整备份/恢复/删除审计方案
4. 后续如进入真正生产化阶段，应迁移到支持并发、备份、审计和恢复的托管数据库或等价系统。

## Consequences

### Positive

- 当前文档与实际能力保持一致。
- 本地 MVP 仍足够轻便，且有最小事务、迁移和健康探针边界。
- 后续迁移讨论可以围绕“什么时候切库”展开，而不是继续把 SQLite 说成生产最终形态。

### Negative

- 仍然存在单机文件数据库的并发与恢复上限。
- 需要后续明确生产数据库选型与迁移路径。

## Non-Goals

- 不在本 ADR 中直接引入 PostgreSQL/MySQL。
- 不在本 ADR 中实现完整多租户数据隔离。

## Verification

相关契约由以下测试覆盖：

- `tests/test_database_migrations.py`
- `tests/test_database_transactions.py`
- `tests/test_api_app.py`
