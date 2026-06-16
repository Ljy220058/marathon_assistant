# ADR 2026-06-02: Auth And Expert Response Boundary

## Status

Accepted

## Context

当前仓库既要支持本地开发调试，又要避免把专家视图、调试字段和运维接口默认暴露给普通请求。

在 2026-06-02 审计中，几个问题被明确指出：

- 默认认证边界过于偏开发态
- `expert` 响应不应只靠 header 自我声明
- `runner / expert` projection 需要 fail-closed

当前实现里，核心边界已经落在：

- `apps/backend/src/marathon_qa_assistant/apps/security/response_role.py`
- `apps/backend/src/marathon_qa_assistant/apps/response_projection.py`
- `apps/backend/src/marathon_qa_assistant/apps/api_app.py`

## Decision

1. 默认响应角色是 `runner`。
2. 请求头里声明 `X-Marathon-Response-Role: expert` 不能单独升级为专家响应。
3. 只有满足以下其一时才允许 `expert`：
   - 已配置 `MARATHON_EXPERT_API_TOKEN` 且 `X-Marathon-Expert-Key` 与之常量时间匹配
   - 非 production 且显式开启 `MARATHON_DEV_ALLOW_EXPERT_RESPONSE=1`
4. production 模式下，`MARATHON_API_TOKEN` 和 `MARATHON_FERNET_KEY` 必须齐备。
5. `runner` 响应继续使用 allowlist projection，不暴露 expert/debug-only 字段。

## Consequences

### Positive

- 普通请求即使伪造 expert header，也只会拿到 `runner` 视图。
- 本地开发仍可通过显式开关保留专家调试能力。
- API 与前端契约能稳定地区分“用户可见字段”和“调试字段”。

### Negative

- 本地调试 expert 输出时需要额外配置 token 或显式 dev 开关。
- 旧测试若直接 monkeypatch `api_app` 级别的 role 判断，容易和当前 router/projection 边界脱节。

## Non-Goals

- 不在本 ADR 中引入复杂 RBAC。
- 不在本 ADR 中实现多租户权限体系。

## Verification

相关契约由以下测试覆盖：

- `tests/test_security_guards.py`
- `tests/test_api_app.py`
- `tests/test_openapi_contract.py`
