# 模块边界审计 V1

> 快照日期：2026-05-21
>
> 目标：决定后续代码应该怎么拆，不在本轮改产品代码、API、前端路由或测试入口。

## 结论

仓库目录已经基本完成 monorepo 分层，下一阶段的维护风险主要在模块边界，而不是目录命名。当前最需要控制的是：

- 前端单页入口过重：[index.astro](../../apps/web/src/pages/index.astro) 约 4261 行，[global.css](../../apps/web/src/styles/global.css) 约 3156 行。
- 后端计划生成链路的大文件承担多类职责：规则生成、周级约束、日程编排、证据回填、API 响应装配混在少数模块中。
- 测试有一部分直接绑定实现文件和私有 helper，后续拆分前需要先标注契约测试与实现细节测试。

建议拆分顺序：先前端入口拆分，再后端计划/日程服务拆分，最后处理测试耦合和 legacy wrapper。

## 当前热点

| 文件 | 行数 | 当前职责 | 风险等级 | 后续处理 |
|---|---:|---|---|---|
| [index.astro](../../apps/web/src/pages/index.astro) | 4261 | 页面布局、状态管理、API 请求、日历渲染、画像编辑、历史记录、事件绑定 | P0 | 先拆 UI 区块和客户端脚本，保留路由不变 |
| [global.css](../../apps/web/src/styles/global.css) | 3156 | 全局变量、布局、组件样式、日历样式、弹窗样式 | P0 | 按 base/layout/components/calendar/modal 分域 |
| [training_plan_skeleton.py](../../apps/backend/src/marathon_qa_assistant/core/training_plan_skeleton.py) | 1623 | 周计划骨架、周期阶段、跑量分配、HMP 协议接入、结构化输出 | P1 | 保留 `build_structured_training_plan_skeleton()` 外观，内部拆规则域 |
| [knowledge_graph.py](../../apps/backend/src/marathon_qa_assistant/services/knowledge_graph.py) | 1585 | 图谱存储、schema 迁移、实体/关系抽取、模板注册、周级训练决策、Mermaid 输出 | P1 | 先拆 workout decision / registry / graph IO |
| [report_ui.py](../../apps/backend/src/marathon_qa_assistant/ui/report_ui.py) | 1591 | 共享 Markdown 渲染、证据预览、协议面板、每日课表卡 | P1 | 保留 `UIHelper`，把渲染片段移到子模块 |
| [plan_ui.py](../../apps/backend/src/marathon_qa_assistant/ui/plan_ui.py) | 1551 | 前端展示 props、反馈卡、解释卡、日历 props、DB 到 UI 映射 | P2 | 待前端拆分后再评估是否继续保留 |
| [daily_schedule_generator.py](../../apps/backend/src/marathon_qa_assistant/services/daily_schedule_generator.py) | 1472 | 月历编排、动作库映射、KB fallback、风险门、证据来源字段 | P1 | 保留 `generate_daily_schedule()` 外观，拆 composer / evidence / guards |
| [api_app.py](../../apps/backend/src/marathon_qa_assistant/apps/api_app.py) | 919 | FastAPI app、请求/响应模型、画像、计划、日历、LLM 选项、持久化编排 | P1 | 先抽 schema 和 response builders，再抽 routers |

## 关键函数与方法

| 文件 | 最大职责块 | 风险 |
|---|---|---|
| `training_plan_skeleton.py` | `_allocate_weekly_volume` 175 行、`build_structured_training_plan_skeleton` 135 行、`_build_quality_session` 117 行 | 跑量、周期、HMP 和展示字段互相牵连 |
| `daily_schedule_generator.py` | `generate_daily_schedule` 481 行、`_build_field_sources` 112 行 | 编排主流程过长，难以局部验证证据和风险门 |
| `knowledge_graph.py` | `GraphEngine` 45 个方法，`generate_mermaid` 110 行、`plan_week_drafts` 102 行 | 图谱能力和训练决策能力共享一个类 |
| `report_ui.py` | `_render_structured_training_plan_md` 204 行、`_render_half_marathon_protocol_panel_md` 176 行 | Markdown 展示细节会阻碍结构化 API 演进 |
| `api_app.py` | `_build_skeleton_plan_response` 65 行、`_query_response_from_state` 59 行、`execute_query` 50 行 | API 层承担过多响应装配和领域补丁 |

## 依赖方向

当前主要依赖方向是：

- `api_app.py -> core.workflow / training_plan_skeleton / daily_schedule_generator / database`
- `plan_nodes.py -> training_plan_skeleton`
- `output_nodes.py -> daily_schedule_generator / workout_template_retriever`
- `daily_schedule_generator.py -> vector_store / workout_template_retriever / training_load`
- `training_plan_skeleton.py -> half_marathon_* / periodization / workout_template_retriever`
- `knowledge_graph.py -> app_state`

边界要求：

- API 层只做 HTTP 契约、认证/用户限制、响应装配，不新增训练规则。
- `core/` 负责领域规则和结构化计划，不直接处理 FastAPI、DOM 或 Markdown。
- `services/` 负责检索、图谱、日历、持久化等可复用服务，不反向依赖 API。
- `ui/` 只做展示转换；长期目标是减少 `report_ui.py` 的业务判断。

## 测试耦合矩阵

| 模块 | 直接测试 | 类型 | 后续动作 |
|---|---|---|---|
| `training_plan_skeleton.py` | [test_training_plan_skeleton.py](../../tests/test_training_plan_skeleton.py)、[test_volume_allocation.py](../../tests/test_volume_allocation.py)、[test_half_marathon_schedule_composer.py](../../tests/test_half_marathon_schedule_composer.py)、[test_plan_workflow_expectations.py](../../tests/test_plan_workflow_expectations.py)、[test_sk_plan_validation.py](../../tests/test_sk_plan_validation.py)、[test_workout_template_retriever.py](../../tests/test_workout_template_retriever.py) | 多数为契约测试，少量绑定实现细节 | 拆分时保持 public facade，不改测试入口 |
| `daily_schedule_generator.py` | [test_daily_schedule_generator.py](../../tests/test_daily_schedule_generator.py)、[test_plan_workflow_expectations.py](../../tests/test_plan_workflow_expectations.py) | 契约 + monkeypatch 私有 helper | 先补服务级输入输出契约，再移动私有 helper |
| `api_app.py` | [test_api_app.py](../../tests/test_api_app.py)、[test_api_cli_startup_contract.py](../../tests/test_api_cli_startup_contract.py)、[test_plan_workflow_expectations.py](../../tests/test_plan_workflow_expectations.py) | API 契约 + 模块 monkeypatch | 抽 router 前先保留 `marathon_qa_assistant.apps.api_app.app` |
| `index.astro` / `global.css` | [test_astro_frontend_contract.py](../../tests/test_astro_frontend_contract.py) | 字符串契约测试 | 前端拆分前先调整测试为组件/脚本入口契约 |
| `knowledge_graph.py` | `minimal_import_test.py` 间接覆盖，当前直接测试不足 | 低覆盖 | 拆分前补 registry / decision / graph IO characterization |

## 拆分顺序

### 1. 前端入口拆分

目标：保持 `/` 页面路由、DOM id、data attribute、API base 候选和现有 smoke 不变。

拆分边界：

- `src/pages/index.astro` 只保留页面装配、静态常量和组件引用。
- `src/components/` 承载 Plan Builder、Runner Profile、Training Calendar、Evidence、History、Modals。
- `src/scripts/` 承载 API client、state、calendar rendering、profile editor、history、event binding。
- `src/styles/` 按 `base.css`、`layout.css`、`components.css`、`calendar.css`、`modal.css` 分域；第一批可由 `global.css` 继续汇总 import。

验收：

```powershell
cd apps/web
npm run build
npm run smoke:workspace
cd ../..
pytest tests/test_astro_frontend_contract.py -q
```

### 2. 后端计划生成拆分

目标：保留 `build_structured_training_plan_skeleton()` 作为唯一外观入口。

拆分边界：

- 周结构解析与可训练日约束进入 `core/training_constraints.py`。
- 跑量分配和负荷预算进入 `core/training_volume.py`。
- HMP 协议适配进入 `core/half_marathon_plan_adapter.py`。
- 周/日骨架组装保留在 `training_plan_skeleton.py`，但只做 orchestration。

验收：

```powershell
$env:PYTHONPATH="apps/backend/src"
pytest tests/test_training_plan_skeleton.py tests/test_volume_allocation.py tests/test_half_marathon_schedule_composer.py -q
```

### 3. 日程生成服务拆分

目标：保留 `generate_daily_schedule()` 返回结构和 `MonthlyTrainingCalendar` 契约不变。

拆分边界：

- `schedule_composer.py`：从结构化计划生成日期序列和基础课表。
- `schedule_evidence.py`：动作库、KB fallback、来源字段。
- `schedule_guards.py`：HMP/风险门/负荷守卫。
- `daily_schedule_generator.py`：保持 facade，协调以上模块。

验收：

```powershell
$env:PYTHONPATH="apps/backend/src"
pytest tests/test_daily_schedule_generator.py tests/test_plan_workflow_expectations.py -q
```

### 4. Knowledge Graph 拆分

目标：保留 `GraphEngine` 和 `plan_week_drafts()` 兼容入口。

拆分边界：

- 图谱 IO、schema migration、node/edge upsert 进入 `graph_store.py`。
- 模板/约束 registry 进入 `workout_registry.py`。
- 训练草案决策和周级状态推进进入 `workout_decision_engine.py`。
- 实体关系抽取、搜索、Mermaid 输出进入独立 graph utilities。

验收：

```powershell
$env:PYTHONPATH="apps/backend/src"
pytest tests/minimal_import_test.py tests/test_plan_workflow_expectations.py -q
```

后续应补 `knowledge_graph` 的直接 characterization tests。

### 5. API 层收口

目标：`marathon_qa_assistant.apps.api_app:app`、请求/响应字段和启动命令保持不变。

拆分边界：

- Pydantic schema 进入 `apps/schemas.py`。
- query response builders 进入 `apps/query_response.py`。
- profile/calendar/llm routers 后续进入 `apps/routers/`。
- `api_app.py` 只创建 app、注册 router、保留兼容导入。

验收：

```powershell
$env:PYTHONPATH="apps/backend/src"
pytest tests/test_api_app.py tests/test_api_cli_startup_contract.py -q
python -m uvicorn marathon_qa_assistant.apps.api_app:app --host 127.0.0.1 --port 8000
```

## 实施 Gate

进入任何拆分实施前必须满足：

- 当前改动分支中没有未说明的产品代码混入。
- 每批只拆一个模块族，不跨前端和后端同时改。
- public facade 先保留一轮：`build_structured_training_plan_skeleton()`、`generate_daily_schedule()`、`GraphEngine`、`api_app.app` 不在第一批删除。
- 拆分前先跑对应 targeted tests，拆分后跑同一组 tests，确认行为不变。
- 如果测试直接断言私有 helper，优先把测试提升为输入输出契约，再移动 helper。

## 下一批建议

1. 前端拆分准备：把 [test_astro_frontend_contract.py](../../tests/test_astro_frontend_contract.py) 中对 `index.astro` 的字符串断言改成“页面入口 + 脚本入口 + 样式入口”契约。
2. 前端第一批拆分：抽 API client、calendar rendering、profile editor，保持 DOM id 和 data attribute 不变。
3. 后端第一批拆分：从 `daily_schedule_generator.py` 抽 evidence 和 guards，因为它的 public facade 清晰、测试集中，风险比 `training_plan_skeleton.py` 更可控。
