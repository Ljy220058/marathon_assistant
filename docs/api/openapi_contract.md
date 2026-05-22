# API 契约快照：训练日历、反馈与观测

> 范围：本文件固定当前 Astro 前端依赖的核心 FastAPI surface，避免后续继续靠散落 `dict` 维护契约。

## 公共约定

- 应用入口保持 `marathon_qa_assistant.apps.api_app:app`。
- 默认用户为 `default_user`；当前 API 仍是单用户本地模式。
- 默认 CORS 只允许 `http://127.0.0.1:4321` 和 `http://localhost:4321`。
- `MARATHON_ALLOWED_ORIGINS` 可用逗号配置允许来源。
- 只有显式设置 `MARATHON_DEV_PERMISSIVE_CORS=1` 才允许 `*`。
- 每个 HTTP 响应都会回写 `X-Request-ID`；请求没有传入时由后端生成。

## `POST /query`

用途：生成或回答训练相关请求。计划类请求支持 skeleton-first，前端主按钮“生成训练日历”依赖该路径。

请求模型：`QueryRequest`

关键请求字段：

- `query`：用户输入或前端基于画像构造的计划 prompt。
- `mode`：默认 `team`。
- `user_id`：默认 `default_user`。
- `llm_provider`：`ollama` 或 `ds`。
- `llm_model`：可选模型名。
- `ds_api_key`：仅本次会话提交，不应由浏览器持久化。
- `response_mode`：`full`、`skeleton` 或 `skeleton_first`。
- `timeout_sec`：5 到 180 秒。

响应模型：`QueryResponse`

核心响应字段：

- `report`
- `structured_training_plan`
- `structured_report`
- `training_explanation_panel`
- `monthly_training_calendar`
- `daily_schedule_cards`
- `phases`
- `training_load_summary`
- `training_plan_id`
- `generation_status`
- `generation_timings`
- `workflow_trace`

计划类请求验收：

- `generation_status=skeleton_ready` 时仍必须返回完整结构化计划骨架。
- `llm_timeout_skeleton` 和 `llm_error_skeleton` 必须回退到结构化骨架，而不是只返回 Markdown。
- `workflow_trace` 必须保留生成路径、证据摘要和状态。
- `generation_timings.total_sec` 用于前端展示和 `/ops/metrics` 聚合。

## `POST /feedback`

用途：用户完成、部分完成、不适或跳过训练后，返回风险门、协议复核和调整建议。

请求模型：`FeedbackRequest`

关键请求字段：

- `user_id`
- `plan_id`：可选；与 `event_id` 同时有效时写入反馈。
- `event_id`：可选；无有效事件时只计算建议，不阻塞用户。
- `day_key`：可选；前端日卡定位辅助字段。
- `raw_text`
- `feedback`

响应模型：`FeedbackResponse`

核心响应字段：

- `workout_feedback`
- `risk_gate`
- `protocol_recheck`
- `adaptive_feedback`
- `adaptive_adjustment`
- `plan_diff`
- `generation_status`
- `feedback_id`
- `workflow_trace`

风险契约：

- 胸痛、头晕/晕厥、中暑迹象必须返回 `generation_status=medical_referral`。
- 医疗红旗不能继续生成训练负荷调整。
- 疼痛风险和医疗红旗不得生成 threshold、interval、tempo、VO2 等高强度替代训练。
- 替代训练必须是休息、低冲击或明确等待专业评估。
- 成功入库时返回 `feedback_id`；无有效事件时 `feedback_id=null`，但仍返回调整建议。

## `GET /plans/{plan_id}`

用途：加载已保存计划、日历事件、最近一次反馈、执行状态总览和调整历史。

响应模型：`PlanDetailResponse`

核心响应字段：

- `plan`
- `structured_training_plan`
- `workflow_trace`
- `events`
- `execution_status_summary`
- `adjustment_history`

验收要点：

- `events[].latest_feedback` 必须能回显最近一次反馈摘要。
- `execution_status_summary` 必须区分完成、部分完成、跳过、缺反馈和医疗风险。
- `adjustment_history` 必须保留 `risk_gate`、`protocol_recheck`、`adaptive_adjustment` 和受影响训练日。
- 旧计划没有反馈时返回空摘要，不应 500。

## `GET /ops/metrics`

用途：轻量进程内观测端点，用于本地运行与后续生产指标接入前的契约基线。

响应模型：`OpsMetricsResponse`

字段：

- `requests_total`
- `errors_total`
- `generation_status_counts`
- `feedback_risk_reason_counts`
- `plan_generation_duration_buckets`
- `medical_referral_total`

数据安全：

- 不暴露用户原始 query。
- 不暴露 API key、OAuth token、refresh token 或 authorization header。
- 不使用用户输入作为高基数 label。

## 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_openapi_contract.py tests/test_api_app.py tests/test_observability_contract.py -q
```
