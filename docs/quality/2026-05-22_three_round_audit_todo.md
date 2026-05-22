# 2026-05-22 三轮工程审计 TODO

## 范围

本文件记录本次自动化执行的三轮闭环：审计 TODO -> 按 TODO 修复 -> Review TODO。审计视角覆盖架构、API、后端、数据库、前端、安全、观测、RAG 证据边界、Git 风险和验证门禁。

## 使用的技能视角

- codex-engineering-workflow：端到端执行、验证、交付边界。
- codex-todo-automation：TODO 拆解、执行状态与验收记录。
- architecture-quality-workflow：模块边界、风险面和架构决策。
- improve-codebase-architecture：单文件过载、浅模块、接口深度。
- api-designer：OpenAPI、响应模型和兼容契约。
- senior-backend：FastAPI 路由、错误契约、风险门和可运维性。
- database-architect：SQLite schema version、migration、旧库升级。
- frontend-designer：Astro 入口、脚本/CSS 拆分、状态可见性。
- security-scanner：CORS、浏览器密钥持久化、敏感信息泄漏。
- observability-advisor：request id、metrics、SLO 和运行手册。
- project-flow-guardrails：RAG/证据边界、UI 渲染、交付验证。
- git-workflow-guardrails：dirty worktree、暂存范围、数据文件风险。
- karpathy-guidelines：最小改动、测试先行、避免过度重构。

## Round 1：核心断点审计 TODO

- [x] 1. 建立 P0 前端拆分契约测试，锁住 `index.astro` 入口 DOM、data attribute 和脚本入口。
- [x] 2. 审计 `index.astro` 单文件职责，确认页面装配与运行脚本需要拆分。
- [x] 3. 抽出 `apps/web/src/scripts/app.js`，保持 Astro `/` 路由不变。
- [x] 4. 建立 API、calendar、evidence、feedback、status 五个前端域模块入口，先保持兼容。
- [x] 5. 拆分 `global.css` 到 base/components/plan/profile-status/modal/calendar/evidence/responsive。
- [x] 6. 增加 API schema 抽离，创建 `apps/schemas.py` 并保持 `api_app:app` 导入兼容。
- [x] 7. 审计默认 CORS，发现 `allow_origins=["*"]` 不适合生产默认。
- [x] 8. 审计 DeepSeek API key 存储，发现浏览器 localStorage 持久化风险。
- [x] 9. 审计 OpenAPI，发现 `/feedback` 和 `/plans/{plan_id}` 响应 schema 为空。
- [x] 10. 审计 SQLite 初始化，发现只有 `CREATE TABLE IF NOT EXISTS` 和补列，没有 `schema_migrations`。
- [x] 11. 审计观测链路，发现已有 workflow trace 但缺 request id 和 metrics 入口。
- [x] 12. 审计旧库升级，发现旧 `training_calendar_events` 缺 `sync_status` 时索引创建会失败。

## Round 1：修复 TODO 与验收

- [x] 1. 新增 `_allowed_cors_origins()`，默认只允许 `127.0.0.1:4321` 和 `localhost:4321`。
- [x] 2. 支持 `MARATHON_ALLOWED_ORIGINS` 显式配置生产来源。
- [x] 3. 仅在 `MARATHON_DEV_PERMISSIVE_CORS=1` 时允许 `*`。
- [x] 4. 前端移除 `localStorage.setItem("marathon_ds_api_key", ...)`。
- [x] 5. 前端启动时清理旧 `marathon_ds_api_key`，避免历史持久化残留。
- [x] 6. 新增 `FeedbackResponse`、`PlanDetailResponse`、`OpsMetricsResponse`。
- [x] 7. 为 `/feedback` 和 `/plans/{plan_id}` 添加 response model。
- [x] 8. 新增 `core/observability.py`，聚合 request、generation status、feedback risk 指标。
- [x] 9. 新增 request id middleware，回写 `X-Request-ID`。
- [x] 10. 新增 `/ops/metrics` 只读端点。
- [x] 11. 新增 migration 目录、`0001_initial.sql`、`0002_feedback_audit_fields.sql`。
- [x] 12. 新增 `schema_migrations` 记录 version/checksum/applied_at。
- [x] 13. 添加旧库 preflight 补列，确保旧 `training_calendar_events` 可升级。
- [x] 14. 修复 feedback summary 兼容 `feedback_id` 字段。

验收命令：

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_security_guards.py::test_api_cors_defaults_to_local_origins tests/test_security_guards.py::test_api_cors_allows_explicit_dev_permissive_mode tests/test_security_guards.py::test_frontend_does_not_persist_deepseek_api_key -q
python -m pytest tests/test_openapi_contract.py -q
python -m pytest tests/test_database_migrations.py -q
python -m pytest tests/test_observability_contract.py -q
```

结果：全部通过。

## Round 1：Review TODO

- [x] 1. Review CORS 默认是否仍可本地开发。
- [x] 2. Review `* + credentials` 是否被默认避免。
- [x] 3. Review API key 是否仍可当前会话内提交给 `/query`。
- [x] 4. Review API key 是否刷新后不再保留。
- [x] 5. Review OpenAPI schema 是否有命名组件。
- [x] 6. Review migration 是否可空库初始化。
- [x] 7. Review migration 是否可旧库升级。
- [x] 8. Review migration 是否可重复执行。
- [x] 9. Review request id 是否覆盖 `/health`。
- [x] 10. Review metrics 是否不暴露用户原文和密钥。
- [x] 11. Review dirty worktree 是否未执行 broad stage。

## Round 2：扩大契约审计 TODO

- [x] 1. 运行 `tests/test_api_app.py` 和 API startup 契约。
- [x] 2. 运行 Astro 前端契约。
- [x] 3. 运行计划工作流、日卡生成、状态模型契约。
- [x] 4. 运行安全、DB、OpenAPI、观测聚合契约。
- [x] 5. 审计反馈风险边界，发现疼痛/医疗风险替代训练缺英文安全关键词。
- [x] 6. 审计执行状态面板，发现医疗红旗建议缺 `Stop training` 可机器断言文本。
- [x] 7. 审计 Evidence Preview，发现 HMP 协议中文产品名没有落到拆分后的源文本。
- [x] 8. 审计能力校准，发现 `renderPerformanceCalibration` 仍直接依赖 `targetPace` 字段名。
- [x] 9. 审计前端拆分契约，确认 `index.astro` 已明显瘦身。
- [x] 10. 审计 backend schema 抽离，确认 app 入口兼容。
- [x] 11. 审计观测指标，确认 feedback medical_referral 会进入 metrics。
- [x] 12. 审计旧库反馈回显，确认 `latest_feedback` 可读回。

## Round 2：修复 TODO 与验收

- [x] 1. 强化医疗红旗 `_medical_referral_adjustment`，明确 `rest` 和 `low impact` 安全词。
- [x] 2. 医疗风险继续 fail-closed，不生成跑步替代课。
- [x] 3. 状态模型医疗红旗建议加入 `Stop training` 标记。
- [x] 4. 保持中文用户提示不丢失，同时满足机器契约断言。
- [x] 5. 前端 HMP 证据 fallback 增加 `半马 HMP 基石协议` 产品名。
- [x] 6. 移除 `renderPerformanceCalibration` 对 `state.lastPlanIntent?.targetPace` 的直接依赖。
- [x] 7. 保留通过 `source_fields` 判断目标来源的能力校准逻辑。
- [x] 8. 回跑 API 失败用例。
- [x] 9. 回跑 Astro 失败用例。
- [x] 10. 回跑更宽契约矩阵，确认第 2 轮通过。

验收命令：

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_api_app.py tests/test_api_cli_startup_contract.py -q
python -m pytest tests/test_astro_frontend_contract.py -q
python -m pytest tests/test_plan_workflow_expectations.py tests/test_daily_schedule_generator.py tests/test_state_models.py -q
python -m pytest tests/test_security_guards.py tests/test_database_migrations.py tests/test_openapi_contract.py tests/test_observability_contract.py -q
```

结果：全部通过。

## Round 2：Review TODO

- [x] 1. Review 医疗风险是否不再出现高强度替代训练。
- [x] 2. Review 疼痛风险是否只给降级或低冲击建议。
- [x] 3. Review `generation_status=medical_referral` 是否被前后端区分。
- [x] 4. Review HMP 证据名是否可被用户和测试识别。
- [x] 5. Review 画像目标配速是否不直接污染校准渲染。
- [x] 6. Review `source_fields` 是否仍是校准展示依据。
- [x] 7. Review tests 是否覆盖旧客户端 `/feedback` 调用。
- [x] 8. Review 新增 response model 是否没有破坏 JSON 形状。
- [x] 9. Review metrics 是否可连续调用增长。
- [x] 10. Review FastAPI deprecation warning 是否为既有低风险项。

## Round 3：最终审计 TODO

- [ ] 1. 补写 OpenAPI 契约文档，覆盖 `/query`、`/feedback`、`/plans/{plan_id}`、`/ops/metrics`。
- [ ] 2. 补写观测基线文档，定义 SLI/SLO、request id、metrics、排查顺序。
- [ ] 3. 从 README 或维护路线图链接观测基线文档。
- [ ] 4. 审计 `todolist.md`，补充已完成验收记录。
- [ ] 5. 审计新增 docs 是否不扩展到无关产品需求。
- [ ] 6. 审计新增 migration SQL 是否不含破坏性 DDL。
- [ ] 7. 审计新增测试是否不依赖本地 profile 或数据缓存。
- [ ] 8. 审计新增前端模块是否没有误导为完成彻底模块化。
- [ ] 9. 审计安全扫描是否没有泄露真实密钥。
- [ ] 10. 审计最终测试矩阵是否包含后端、前端、build、smoke、repo hygiene。
- [ ] 11. 审计 Git 状态，只报告本轮相关文件和既有 dirty 风险。
- [ ] 12. 审计遗留风险，特别是 `api_app.py` 路由仍未完全拆分、`app.js` 仍较大。

## Round 3：修复 TODO

- [ ] 1. 创建 `docs/api/openapi_contract.md`。
- [ ] 2. 创建 `docs/architecture/observability_baseline.md`。
- [ ] 3. 更新 README 或维护路线图链接。
- [ ] 4. 更新 `todolist.md` 的全局验收状态。
- [ ] 5. 运行 Python 最终测试矩阵。
- [ ] 6. 运行 `apps/web` build。
- [ ] 7. 运行 `apps/web` smoke。
- [ ] 8. 运行 `tools/dev/check_repo.py --scope hygiene`。
- [ ] 9. 运行 `git diff --check`。
- [ ] 10. 运行 `git status --short --branch`。
- [ ] 11. 汇总通过、失败、warning 和剩余风险。

## Round 3：Review TODO

- [ ] 1. Review 所有新增文档链接可读。
- [ ] 2. Review OpenAPI 文档是否匹配当前 response model。
- [ ] 3. Review SLO 文档是否包含 numerator、denominator、目标、窗口、排除项。
- [ ] 4. Review metrics 字段是否与 `/ops/metrics` 返回一致。
- [ ] 5. Review browser API key 文案是否不再声称“保存到浏览器”。
- [ ] 6. Review CORS 文档是否说明 dev permissive 开关。
- [ ] 7. Review migration 文档是否说明旧库兼容和 checksum。
- [ ] 8. Review 最终测试失败时是否记录具体 blocker。
- [ ] 9. Review dirty worktree 是否未包含 broad staging。
- [ ] 10. Review 最终交付是否不声称未完成的大路由拆分已经完成。
