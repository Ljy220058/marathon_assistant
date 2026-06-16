# 工程债收口 TODO 与验收清单

> 工作目录：`C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手`
>
> 范围：解决当前点评中列出的五类工程风险：前端单文件过载、后端 API 聚合层过重、数据库缺少迁移纪律、安全边界未产品化、可观测性不足。
>
> 执行原则：每个任务必须先补契约或回归测试，再改实现；每个任务完成后必须填写“验收记录”。当前仓库存在大量既有 dirty worktree，执行时只允许暂存本任务相关文件，禁止 `git add .`。

## 验收状态约定

- `[ ]` 未开始
- `[~]` 实现中
- `[x]` 已通过本条验收
- `[!]` 阻塞，需要写清阻塞原因

每个任务完成时必须补充：

```text
验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：
```

## 全局验收闸口

- [ ] 所有新增/拆分文件都保持现有公共入口兼容：`marathon_qa_assistant.apps.api_app:app`、`/query`、`/feedback`、`/plans/{plan_id}`、Astro `/` 页面路由不变。
- [ ] 不删除用户现有 dirty worktree 内容，不回滚其他 agent 的修改。
- [ ] 不提交 `data/vector_kb/default/knowledge_graph.json`、本地 profile、缓存、构建产物、API key 或 token。
- [ ] 每个 P0/P1/P2 完成后运行对应测试命令；最终集成验收运行“最终验收命令矩阵”。
- [ ] 无本地证据时允许展示 `llm_general_knowledge` 一般说明，但不得写入核心处方字段、风险等级、风险原因或伪引用。

---

## P0：拆分 Astro 单页入口

目标：把 `apps/web/src/pages/index.astro` 从页面、状态、API、日历、反馈、证据、历史混合文件，拆成可维护的页面装配 + 客户端模块 + 样式分域。首轮只做结构拆分，不改变用户可见功能。

### P0.1 前端拆分前契约加固

- [ ] 在 `tests/test_astro_frontend_contract.py` 增加拆分保护测试。

验收标准：

- [ ] 测试断言 `index.astro` 仍保留关键 DOM id：`runQuery`、`calendar`、`dayModal`、`evidenceDrawer`、`statusPanel`、`adjustmentHistory`。
- [ ] 测试断言关键 data attribute 仍存在：`data-plan-generation-entry`、`data-evidence-open`、`data-modal-feedback-action`、`data-calendar-view`。
- [ ] 测试断言拆分后的脚本入口存在，例如 `src/scripts/app.js` 或等价入口。
- [ ] 命令通过：

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/test_astro_frontend_contract.py -q
```

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

### P0.2 抽出前端 API client

- [ ] 新增 `apps/web/src/scripts/apiClient.js`，承载 `apiFetch`、`detectApiBase`、`requestQueryPayload`、`submitFeedbackApi`、计划保存/加载相关请求。
- [ ] `index.astro` 只保留 API client 的导入和事件接线，不再直接散落 `fetch()` 细节。

验收标准：

- [ ] `apiClient.js` 对外暴露稳定函数：`apiFetch`、`detectApiBase`、`requestQueryPayload`、`submitFeedback`、`loadPlanDetail`。
- [ ] 所有 API 错误仍能被前端转成用户可读提示，后端不可用时不清空已生成日历。
- [ ] `tests/test_astro_frontend_contract.py` 覆盖默认 `8010`、自动探测、超时文案、反馈提交路径。
- [ ] 命令通过：

```powershell
cd apps/web
npm run build
cd ../..
$env:PYTHONUTF8='1'
python -m pytest tests/test_astro_frontend_contract.py -q
```

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

### P0.3 抽出日历与日卡渲染模块

- [ ] 新增 `apps/web/src/scripts/calendarRenderer.js`，承载日历分组、周/月/阶段/全部视图、筛选、日卡 HTML、日卡弹窗打开逻辑。
- [ ] `index.astro` 不再直接维护大段日历 HTML 字符串。

验收标准：

- [ ] `calendarRenderer.js` 对外暴露 `renderCalendar`、`openDayModal`、`normalizeCalendarDays`。
- [ ] 周/月/阶段/全部视图切换不丢失 `field_sources`、`risk_gate`、`protocol_check`、`latest_feedback`。
- [ ] 日卡弹窗继续显示热身、主课、冷身、强度、负荷、目的、风险和依据。
- [ ] 命令通过：

```powershell
cd apps/web
npm run build
npm run smoke:workspace
cd ../..
$env:PYTHONUTF8='1'
python -m pytest tests/test_astro_frontend_contract.py tests/test_plan_ui_display_props.py -q
```

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

### P0.4 抽出 EvidenceDrawer、FeedbackModal、StatusPanel

- [ ] 新增 `apps/web/src/scripts/evidenceDrawer.js`，统一证据抽屉数据归一化和打开/关闭逻辑。
- [ ] 新增 `apps/web/src/scripts/feedbackModal.js`，承载快捷反馈、反馈表单、反馈结果卡和生成调整版计划入口。
- [ ] 新增 `apps/web/src/scripts/statusPanel.js`，承载 `StatusPanel`、`CycleProgressBar`、`PhaseTimeline`、`CompletedWeeksList`、`AdjustmentHistory` 渲染。

验收标准：

- [ ] `needs_evidence`、`needs_protocol_recheck`、`medical_referral` 三种状态在 UI 上可区分。
- [ ] 证据不足时展示 `llm_general_knowledge` 说明，不生成伪来源、伪页码、伪引用编号。
- [ ] 医疗风险反馈不展示普通“已生成训练安排”状态，不展示继续生成高强度替代训练入口。
- [ ] 命令通过：

```powershell
cd apps/web
npm run build
cd ../..
$env:PYTHONUTF8='1'
python -m pytest tests/test_astro_frontend_contract.py -q
```

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

### P0.5 拆分 `global.css`

- [ ] 将 `apps/web/src/styles/global.css` 拆为 `base.css`、`layout.css`、`components.css`、`calendar.css`、`modal.css`、`evidence.css`、`status.css`。
- [ ] `global.css` 只保留 `@import` 聚合和极少量全局变量。

验收标准：

- [ ] `global.css` 行数下降到 300 行以内。
- [ ] 任何一个样式子文件不超过 900 行。
- [ ] 桌面和移动端不出现日历卡片、按钮、弹窗文字明显重叠。
- [ ] 命令通过：

```powershell
cd apps/web
npm run build
npm run smoke:workspace
cd ../..
$env:PYTHONUTF8='1'
python -m pytest tests/test_astro_frontend_contract.py -q
```

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

---

## P1：拆分 FastAPI 聚合层并固化契约

目标：保持 `api_app.py` 作为 FastAPI app 装配入口，把 schema、router、response builder、依赖装配拆开，让 API 契约不再靠散落 dict 维护。

### P1.1 抽出 API schema

- [ ] 新增 `apps/backend/src/marathon_qa_assistant/apps/schemas.py`。
- [ ] 移动 `QueryRequest`、`QueryResponse`、`ProfileRequest`、`FeedbackRequest`、`SavePlanRequest`、`TrainingCalendarResponse`、`DayDetailResponse`、`ZoneReference`。

验收标准：

- [ ] `api_app.py` 不再定义大型 Pydantic request/response class。
- [ ] `from marathon_qa_assistant.apps.api_app import app` 仍可用。
- [ ] `/openapi.json` 中仍包含 `/query`、`/feedback`、`/plans/{plan_id}`。
- [ ] 命令通过：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_api_cli_startup_contract.py tests/test_api_app.py -q
```

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

### P1.2 抽出 response builders

- [ ] 新增 `apps/backend/src/marathon_qa_assistant/apps/response_builders.py`。
- [ ] 移动 `_build_skeleton_plan_response`、`_query_response_from_state`、训练日历 response 装配、workflow trace fallback 装配。

验收标准：

- [ ] `/query` skeleton-first 返回字段不变：`structured_training_plan`、`monthly_training_calendar`、`daily_schedule_cards`、`training_plan_id`、`generation_timings`。
- [ ] LLM timeout 和 LLM error 时仍能返回 skeleton plan。
- [ ] 命令通过：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_api_app.py tests/test_plan_workflow_expectations.py tests/test_training_plan_skeleton.py -q
```

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

### P1.3 抽出 routers

- [ ] 新增 `apps/backend/src/marathon_qa_assistant/apps/routers/query.py`。
- [ ] 新增 `apps/backend/src/marathon_qa_assistant/apps/routers/feedback.py`。
- [ ] 新增 `apps/backend/src/marathon_qa_assistant/apps/routers/plans.py`。
- [ ] 新增 `apps/backend/src/marathon_qa_assistant/apps/routers/profile.py`。
- [ ] 新增 `apps/backend/src/marathon_qa_assistant/apps/routers/reference.py`。
- [ ] `api_app.py` 只负责创建 `FastAPI`、CORS、startup、router include。

验收标准：

- [ ] 所有现有 API 路径和 HTTP method 保持不变。
- [ ] `tests/test_api_app.py` 不需要大规模改写，只调整 import 路径或 monkeypatch 入口。
- [ ] `/feedback` 老客户端只传 `raw_text + feedback` 仍可用。
- [ ] 命令通过：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_api_app.py tests/test_api_plan_validation.py tests/test_high_risk_contracts.py -q
```

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

### P1.4 固化 OpenAPI 契约快照

- [ ] 新增 `docs/api/openapi_contract.md`，记录核心端点、请求字段、响应字段、错误状态。
- [ ] 新增 `tests/test_openapi_contract.py`，从 `app.openapi()` 验证核心端点和字段存在。

验收标准：

- [ ] 测试断言 `/query` 响应 schema 包含训练计划核心字段。
- [ ] 测试断言 `/feedback` 响应 schema 包含风险门和调整建议字段。
- [ ] 测试断言 `/plans/{plan_id}` 响应 schema 或文档说明包含 `execution_status_summary`、`adjustment_history`。
- [ ] 命令通过：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_openapi_contract.py tests/test_api_app.py -q
```

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

---

## P1：建立 SQLite migration 与 schema version

目标：把当前启动时建表和 `_ensure_columns` 补列方式收敛为可追踪、可回滚、可测试的 migration 机制，同时保留现有本地数据库兼容。

### P1.5 建立 migration 目录与版本表

- [ ] 新增 `apps/backend/src/marathon_qa_assistant/services/migrations/0001_initial.sql`。
- [ ] 新增 `apps/backend/src/marathon_qa_assistant/services/migrations/0002_feedback_audit_fields.sql`。
- [ ] 新增 `schema_migrations` 表，记录 `version`、`applied_at`、`checksum`。
- [ ] 在 `database.py` 启动时执行未应用 migration。

验收标准：

- [ ] 新建空 DB 后能得到与当前 schema 等价的表结构。
- [ ] 已存在旧 DB 时能补齐反馈审计字段，不丢失旧计划和日历事件。
- [ ] migration 重复执行不会重复加列或破坏数据。
- [ ] 命令通过：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_database_migrations.py tests/test_api_app.py -q
```

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

### P1.6 增加 migration 回归测试

- [ ] 新增 `tests/test_database_migrations.py`。
- [ ] 覆盖空库初始化、旧库升级、重复启动、反馈写入后读取四条路径。

验收标准：

- [ ] 测试构造旧版 `training_event_feedback` 缺少 `risk_gate_json`、`protocol_recheck_json` 的 DB，升级后字段存在。
- [ ] 写入 `/feedback` 后能从 `/plans/{plan_id}` 读回 `latest_feedback`、`execution_status_summary`、`adjustment_history`。
- [ ] 命令通过：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_database_migrations.py tests/test_state_models.py -q
```

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

---

## P1：安全边界产品化

目标：保留本地开发便利，但部署前不允许开放 CORS、持久化浏览器 API key、开发 token 和敏感日志成为默认行为。

### P1.7 收紧 CORS 配置

- [ ] 后端增加 `MARATHON_ALLOWED_ORIGINS` 环境变量。
- [ ] 默认允许本地开发源：`http://127.0.0.1:4321`、`http://localhost:4321`。
- [ ] 只有显式设置 `MARATHON_DEV_PERMISSIVE_CORS=1` 时才允许 `*`。

验收标准：

- [ ] 默认 `allow_origins` 不再是 `["*"]`。
- [ ] 测试覆盖默认本地源、显式开发宽松模式、生产模式拒绝 `*`。
- [ ] 命令通过：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_security_guards.py tests/test_api_cli_startup_contract.py -q
```

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

### P1.8 移除浏览器持久化 DeepSeek API key

- [ ] 前端不再使用 `localStorage.setItem("marathon_ds_api_key", ...)` 保存密钥。
- [ ] 改为只支持本次会话内存或提示用户使用后端环境变量 `DEEPSEEK_API_KEY` / `DS_API_KEY`。
- [ ] 清除旧 localStorage key 的迁移逻辑：页面启动时删除 `marathon_ds_api_key`。

验收标准：

- [ ] `rg "marathon_ds_api_key|localStorage.setItem\\(.*api_key|localStorage.setItem\\(.*ApiKey" apps/web/src` 无持久化写入。
- [ ] 前端仍能在本次会话内发起 DeepSeek 请求；刷新后不保留密钥。
- [ ] 命令通过：

```powershell
cd apps/web
npm run build
cd ../..
$env:PYTHONUTF8='1'
python -m pytest tests/test_astro_frontend_contract.py tests/test_security_guards.py -q
```

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

### P1.9 清理开发 token 默认值与敏感日志

- [ ] `knowledge_graph.py` 不再把 `"default_token_for_dev"` 作为可误用的生产默认认证值。
- [ ] 日志不得输出 API key、OAuth token、refresh token、authorization header。
- [ ] Google Calendar token 相关错误只输出错误类型，不输出 token 内容。

验收标准：

- [ ] `rg "default_token_for_dev|sk-|refresh_token=.*|Authorization:" apps/backend/src` 不出现可提交的真实或默认敏感值。
- [ ] `tests/test_security_guards.py` 覆盖敏感字段脱敏。
- [ ] 命令通过：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_security_guards.py -q
```

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

---

## P2：建立可观测性基线

目标：把已有 `workflow_trace` 和 `generation_timings` 扩展成可运营的请求关联、结构化日志、轻量指标和 SLO 文档。

### P2.1 增加 request id 中间件

- [ ] 后端增加 request id middleware。
- [ ] 读取传入 `X-Request-ID`，没有则生成。
- [ ] 响应头写回 `X-Request-ID`。
- [ ] workflow trace 和错误响应中带上 request id。

验收标准：

- [ ] `/health`、`/query`、`/feedback`、`/plans/{plan_id}` 都返回 `X-Request-ID`。
- [ ] 同一请求的日志、`workflow_trace.run_id` 或 `workflow_trace.request_id` 可关联。
- [ ] 命令通过：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_api_app.py tests/test_observability_contract.py -q
```

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

### P2.2 增加结构化日志

- [ ] 新增 `apps/backend/src/marathon_qa_assistant/core/observability.py`。
- [ ] 记录字段：`request_id`、`path`、`method`、`status_code`、`duration_ms`、`generation_status`、`plan_id`、`feedback_id`、`error_type`。
- [ ] 日志中不得包含 query 原文全文、API key、token、OAuth secret。

验收标准：

- [ ] 单元测试能捕获一条结构化日志并验证字段。
- [ ] 错误路径也记录 `error_type` 和 `request_id`。
- [ ] 命令通过：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_observability_contract.py tests/test_security_guards.py -q
```

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

### P2.3 增加轻量指标端点

- [ ] 新增只读端点 `/ops/metrics`。
- [ ] 返回进程内聚合指标：请求总数、错误数、`generation_status` 计数、`medical_referral` 计数、计划生成耗时分桶、反馈风险原因分布。
- [ ] 不引入新依赖，不暴露用户原文和密钥。

验收标准：

- [ ] `/ops/metrics` 返回 JSON，字段稳定。
- [ ] 连续调用 `/query` skeleton 和 `/feedback` 后，指标计数增加。
- [ ] 医疗风险反馈会增加 `medical_referral` 指标。
- [ ] 命令通过：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_observability_contract.py tests/test_api_app.py -q
```

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

### P2.4 写入 SLO 与运营手册

- [ ] 新增 `docs/architecture/observability_baseline.md`。
- [ ] 定义用户旅程 SLI/SLO：计划 skeleton 可用性、计划生成延迟、反馈计算成功率、医疗风险 fail-closed 正确率、证据缺失可见率。
- [ ] 写明报警分级：本地开发只记录，生产部署时接入指标系统。

验收标准：

- [ ] 文档列出每个 SLI 的 numerator、denominator、目标、窗口、排除条件。
- [ ] 文档列出一线排查顺序：请求 id、generation status、workflow trace、metrics、日志。
- [ ] `README.md` 或维护路线图链接到该文档。

验收记录：
- 日期：
- 执行人：
- 代码范围：
- 验收命令：
- 结果：
- 遗留风险：

---

## 最终验收命令矩阵

全部任务完成后运行：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest -p no:cacheprovider `
  tests/test_api_app.py `
  tests/test_api_cli_startup_contract.py `
  tests/test_astro_frontend_contract.py `
  tests/test_daily_schedule_generator.py `
  tests/test_plan_workflow_expectations.py `
  tests/test_state_models.py `
  tests/test_security_guards.py `
  tests/test_database_migrations.py `
  tests/test_openapi_contract.py `
  tests/test_observability_contract.py -q

cd apps/web
npm run build
npm run smoke:workspace
cd ../..

python tools/dev/check_repo.py --scope hygiene
git diff --check
git status --short --branch
```

最终验收标准：

- [ ] 上述测试和构建命令通过；若有失败，失败原因和修复计划写入对应任务的“验收记录”。
- [ ] `git status --short --branch` 中本轮新增/修改文件只属于本 TODO 对应任务，不混入数据缓存、大文件、个人 profile 或其他 agent 的不相关改动。
- [ ] `api_app.py`、`index.astro`、`global.css` 行数明显下降，并且公共入口不变。
- [ ] `/query`、`/feedback`、`/plans/{plan_id}` 仍满足现有产品契约。
- [ ] 安全验收确认：默认 CORS 不再全开放，浏览器不再持久化 API key，日志不输出密钥。
- [ ] 可观测性验收确认：每个关键请求可通过 request id 关联日志、trace 和指标。

## 推荐执行顺序

1. 先做 `P0.1`，锁住前端契约。
2. 再做 `P0.2` 到 `P0.5`，拆前端，保持 UI 行为不变。
3. 做 `P1.1` 到 `P1.4`，拆 FastAPI app 并固化 OpenAPI。
4. 做 `P1.5` 到 `P1.6`，建立数据库 migration。
5. 做 `P1.7` 到 `P1.9`，收紧安全边界。
6. 做 `P2.1` 到 `P2.4`，补可观测性和运营文档。
7. 跑最终验收命令矩阵，补完整验收记录。
