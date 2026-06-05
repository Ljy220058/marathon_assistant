# 2026-06-02 OllamaPro Audit Fix Closure Report

> Status: final
> Scope: `2026-06-02_ollamapro_quality_and_runtime_todo.md`（KnowledgeHub 审计清单镜像）
> Purpose: 作为最终 closure report 的工作底稿，按当前代码与已执行验证记录 `closed / partially_closed / deferred`。

## Current Verdict

当前审计 TODO 已执行到可交接关闭状态：

- 所有原始问题编号均已给出最终状态
- release blocker 级问题已关闭
- 剩余未继续深挖的项被明确标记为 `partially_closed`，并说明剩余风险与下一位 owner
- 最终门禁证据已补齐到“后端主矩阵 + 前端主矩阵 + 安装级验证 + 文档/扫描 + git 检查”

## Status Matrix

### P0

| Item | Status | Notes |
|---|---|---|
| P0-1 import smoke / 去掉过时 monkeypatch | closed | `tests/test_import_smoke.py` 已落地，相关导入契约已验证。 |
| P0-2 fallback route parity | closed | `workflow_graph.py` 复用共享 `after_executor_route`。 |
| P0-3 feedback XSS | closed | `apps/web/src/scripts/feedbackModal.js` 已安全转义；前后端契约测试已覆盖。 |
| P0-4 calendar fallback XSS | closed | `apps/web/src/scripts/calendarRenderer.js` 已安全转义；前后端契约测试已覆盖。 |
| P0-5 DB rollback | closed | `save_training_plan()` / `save_feedback_replan()` 已显式 rollback；事务测试通过。 |
| P0-6 expert role fail-closed | closed | `apps/security/response_role.py` 已集中处理并默认 fail-closed。 |
| P0-7 non-plan `/query` error semantics | closed | 非计划查询异常已变为 `503 + {error_code, request_id, message}`。 |
| P0-8 default auth exposure boundary | closed | runtime config guard + 默认 host `127.0.0.1` 已落地。 |
| 运行态问题 1：日历默认折叠 | closed | 周卡默认展开当前周/首周。 |
| 运行态问题 2：前端 key 门控与 skeleton-first 不一致 | closed | skeleton-first 计划生成不再被前端 API key 门控阻断。 |
| 运行态 P2：计划生成后引导文案不足 | partially_closed | 结构化骨架返回文案已增强，但尚未做单独文案验收或更完整 UX 回归。 |

### P1 Original Audit Issues

| Item | Status | Notes |
|---|---|---|
| P1-1 `api_app.py` 过大且职责混杂 | partially_closed | routers / builders / projection 已拆出，`api_app.py` 已从更大的历史状态压缩到约 500 行，但仍不是纯 assembly 层。 |
| P1-2 `api_app.py` 与 `routers/_shared.py` 逻辑重复 | closed | role / projection / plan classifier / feedback helper 的重复逻辑已明显收敛，`api_app.py` 中一整块反馈 helper 已删除。 |
| P1-3 前端 `app.js` 约 7000 行，模块边界不清 | partially_closed | 已拆出 `apiClient.js`、`calendarRenderer.js`、`feedbackModal.js`、状态/组件脚本，但 `app.js` 仍然明显偏大。 |
| P1-4 前端 API client 逻辑重复 | closed | `apiClient.js` 已成为统一入口；`app.js` 不再持有完整重复 client 逻辑。 |
| P1-5 前端画像保存不是原子操作 | closed | 前端改为单次提交，后端非法字段整单 `422`。 |
| P1-6 月视图 monkey patch 重写 `renderCalendar` | closed | month view 已并回主渲染路径，原 monkey patch 已删。 |
| P1-7 输入契约过宽，非法输入被静默改写 | closed | `QueryRequest.query` 长度限制、日期时间校验、未知字段 `422` 已落实。 |
| P1-8 `/knowledge/sources` 同步全量读 chunks | closed | 现已改为缓存摘要。 |
| P1-9 `/query` 同步懒加载 KB | closed | 请求热路径已移除同步 bootstrap。 |
| P1-10 evidence_bundle visible evidence 限制 | closed | 默认可见 evidence top-k 已加。 |
| P1-11 计划证据 gate 判断过宽 | closed | 路由判断与计划证据 gate 已收紧。 |
| P1-12 Knowledge Graph 路径与 v2 runtime 不一致 | closed | graph path 已切到 `v2`，并有 mismatch fail-safe。 |
| P1-13 FAISS trusted loader 边界 | closed | trusted loader 统一后，非受信目录不再反序列化。 |

### P2 Original Audit Issues

| Item | Status | Notes |
|---|---|---|
| P2-1 SQLite 与同步 I/O 不适合多实例高并发 | partially_closed | 已补 `busy_timeout`、health probe、`asyncio.to_thread` 包装和 ADR，但仍明确限定为本地 MVP / 单机预览边界，不是多实例生产方案。 |
| P2-2 内存限流只适合单进程本地 | closed | 文档已明确当前限流只是单进程兜底，生产应交给 API Gateway / Redis 等共享基础设施。 |
| P2-3 进程内 metrics 不适合生产观测 | closed | `/ops/metrics` 已加公共暴露保护，文档已明确这不是 Prometheus/OTel 级生产观测。 |
| P2-4 依赖声明分裂且版本策略不一致 | partially_closed | `pyproject.toml`、`requirements-runtime.txt`、`requirements-dev.txt`、`constraints.txt`、Docker、CI、README 已收敛，且已做安装级验证；但 constraints 仍是当前环境可运行带，不是长期稳定锁定方案。 |
| P2-5 覆盖率阈值本地与 CI 不一致 | closed | coverage gate 统一到 `pytest.ini --cov-fail-under=70`，CI 不再单独覆写。 |
| P2-6 配置管理分散 | partially_closed | `core/settings.py` 已落地并接管关键入口，但 `app_state.py` 等少数低层路径/env 仍未完全并入 settings。 |
| P2-7 前端缺少 lint/typecheck/JS 行为测试入口 | closed | `lint / build / check / smoke / test` 入口与 CI 已落地，并完成验证。 |

### P3

| Item | Status | Notes |
|---|---|---|
| P3-1 SQLite 生产边界 | tracked via original P2-1 | 已纳入上表。 |
| P3-2 metrics / 限流生产 caveat | tracked via original P2-2 / P2-3 | 已纳入上表。 |
| P3-3 依赖与 coverage gate 统一 | tracked via original P2-4 / P2-5 | 已纳入上表。 |
| P3-4 前端 lint/check/test 入口 | tracked via original P2-7 | 已纳入上表。 |

### P4

| Item | Status | Notes |
|---|---|---|
| P4-1 架构/运行手册/ADR | closed | `openapi_contract.md`、`observability_baseline.md`、`repository_governance.md`、`workflow_node_glossary.md` 与三份 ADR 已补齐，并做了文档级 path/secret 清理。 |
| P4-2 最终关闭报告 | closed | 当前文件已升级为最终关闭报告，并已同步到 KnowledgeHub 审计目录。 |

## Remaining Partials

| Item | Remaining Risk | Next Owner |
|---|---|---|
| 运行态 P2：计划生成后引导文案不足 | 文案已更清楚，但没有单独做更细的 UX 验收 | `frontend/product` |
| P1-1 `api_app.py` 过大且职责混杂 | 当前已大幅收缩，但仍不是纯 assembly 层，后续继续重构时容易再次吸收业务逻辑 | `backend` |
| P1-3 前端 `app.js` 约 7000 行，模块边界不清 | 已拆掉若干模块，但大文件本身仍提高理解和修改成本 | `frontend` |
| P2-1 SQLite 与同步 I/O 不适合多实例高并发 | 代码与文档已 fail-safe，但架构上仍不支持真正多实例生产 | `backend/platform` |
| P2-4 依赖声明分裂且版本策略不一致 | 入口已统一并验证可安装，但 constraints 仍是“当前可运行带”，不是长期冻结版本策略 | `backend/platform` |
| P2-6 配置管理分散 | 绝大多数入口已统一，但 `app_state.py` 这类低层路径/env 仍有少量直接读取 | `backend` |

## Verification Evidence

以下命令已在当前工作树执行并通过：

```powershell
$env:MARATHON_RUNTIME_DATA_DIR=(Resolve-Path '.').Path + '\_runtime_test'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_api_app.py -q -k "non_plan_query_does_not_bootstrap_kb_in_request_path"
python -m pytest tests/test_api_cli_startup_contract.py tests/test_kb_bootstrap.py tests/test_kb_v2_runtime_contract.py -q
python -m pytest tests/test_settings_contract.py tests/test_api_cli_startup_contract.py tests/test_security_guards.py tests/test_provider_secret_contract.py tests/test_vector_kb_runtime_contract.py -q
python -m pytest tests/test_source_inventory.py tests/test_api_app.py tests/test_security_guards.py tests/test_astro_frontend_contract.py -q -k "knowledge_sources or llm_options_returns_providers or expert_role"
python -m pytest tests/test_vector_kb_runtime_contract.py tests/test_kb_graph_evidence.py tests/test_evidence_chain_contract.py -q
python -m pytest tests/test_observability_contract.py tests/test_security_guards.py tests/test_api_app.py -q -k "ops_metrics or api_token_protects_non_public_endpoints_when_configured"
python -m pytest tests/test_database_migrations.py tests/test_database_transactions.py tests/test_api_app.py -q -k "busy_timeout or health_check or health_returns or health_reports_db_false or transaction"
python -m pytest tests/test_backend_packaging_contract.py -q
python -m pytest tests/test_plan_query_classifier.py tests/test_api_app.py tests/test_openapi_contract.py tests/test_observability_contract.py -q
python -m pytest tests/test_import_smoke.py tests/test_security_guards.py tests/test_api_app.py tests/test_openapi_contract.py tests/test_router_behavior.py tests/test_plan_workflow_expectations.py tests/test_database_migrations.py tests/test_database_transactions.py tests/test_evidence_chain_contract.py tests/test_vector_kb_runtime_contract.py tests/test_observability_contract.py -q
python -m pytest tests/test_astro_frontend_contract.py tests/test_frontend_xss_contract.py -q
python -m pytest tests/test_response_trace_boundary.py tests/test_observability_contract.py tests/test_api_app.py tests/test_openapi_contract.py -q
python -m pytest tests/test_async_db_boundary.py tests/test_api_app.py tests/test_database_migrations.py tests/test_database_transactions.py tests/test_observability_contract.py -q
python -m pytest tests/test_import_smoke.py tests/test_security_guards.py tests/test_api_app.py tests/test_openapi_contract.py tests/test_router_behavior.py tests/test_plan_workflow_expectations.py tests/test_database_migrations.py tests/test_database_transactions.py tests/test_evidence_chain_contract.py tests/test_vector_kb_runtime_contract.py tests/test_observability_contract.py tests/test_astro_frontend_contract.py tests/test_frontend_xss_contract.py tests/test_settings_contract.py tests/test_response_trace_boundary.py tests/test_async_db_boundary.py tests/test_backend_packaging_contract.py tests/test_plan_query_classifier.py -q
```

以下前端验证已通过：

```powershell
cd apps/web
cmd.exe /c npm run lint
cmd.exe /c npm run build
cmd.exe /c npm run check
cmd.exe /c npm run smoke
cmd.exe /c npm run test
```

以下安装级验证已通过：

```powershell
python -m venv C:\tmp\ma_backend_pkgcheck
& 'C:\tmp\ma_backend_pkgcheck\Scripts\python.exe' -m pip install .
& 'C:\tmp\ma_backend_pkgcheck\Scripts\python.exe' -m pip install -r requirements-dev.txt
& 'C:\tmp\ma_backend_pkgcheck\Scripts\python.exe' -c "import marathon_qa_assistant; import pytest; print('dev-install-ok')"
```

以下前端命令已在当前环境复跑通过：

```powershell
cd apps/web
cmd.exe /c npm run build
cmd.exe /c npm run check
```

以下额外门禁已通过：

```powershell
python tools/dev/check_repo.py --scope hygiene
git diff --check
git status --short --branch
```

## Remaining High-Signal Gaps

1. `api_app.py` 仍有历史包袱，虽已明显收缩，但还不能称为纯 assembly 层。
2. `app.js` 仍然偏大，后续功能迭代时容易再次积累耦合。
3. 前端虽已具备 `lint/build/check/smoke/test` 入口，但自动化深度仍偏轻量。
4. SQLite、单进程限流、进程内 metrics 的生产边界已经写清，但架构本身仍不是多实例商业部署方案。

## Next Recommended Actions

1. 继续压缩 `api_app.py` 剩余业务逻辑，至少把反馈重排/画像 patch 的残余 helper 再外提一轮。
2. 补 `P4-1` 文档与 ADR。
3. 跑一次更接近全量的后端/前端验收矩阵。
4. 再把本报告从 `in_progress` 提升到最终 closure report。
