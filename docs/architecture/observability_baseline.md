# 可观测性基线：训练计划生成与反馈闭环

> 范围：本文件定义当前本地 API 的最低可观测性契约。目标不是替代生产级 APM，而是让计划生成、反馈风险和旧库迁移问题可以被稳定定位。

## 关键用户旅程

1. 用户从 Astro 点击“生成训练日历”。
2. 前端调用 `/query`，优先得到 skeleton-first 结构化计划。
3. 用户浏览日历并打开每日训练卡。
4. 用户提交完成、部分完成、不适或跳过反馈。
5. 后端 `/feedback` 返回风险门、协议复核和调整建议。
6. 用户加载历史计划时，`/plans/{plan_id}` 回显执行状态和调整历史。

## 关联标识

- HTTP 请求统一使用 `X-Request-ID`。
- 客户端可传入 `X-Request-ID`；未传入时后端生成。
- 响应必须回写同一个 `X-Request-ID`。
- `workflow_trace` 是业务工作流级关联字段。
- `training_plan_id`、`feedback_id`、`event_id` 是计划与反馈闭环的业务定位字段。

## 指标字段

`GET /ops/metrics` 返回进程内聚合 JSON：

- `requests_total`：总 HTTP 请求数。
- `errors_total`：5xx 或中间件捕获异常总数。
- `generation_status_counts`：按 `generation_status` 聚合的计划或反馈状态。
- `feedback_risk_reason_counts`：反馈风险原因分布。
- `plan_generation_duration_buckets`：计划生成耗时桶。
- `medical_referral_total`：医疗红旗反馈次数。

## 当前适用边界

- 当前 `/ops/metrics` 是进程内聚合端点，只适用于本地开发、测试和受控调试环境。
- 当服务以公共 host 暴露且没有 auth 时，`/ops/metrics` 应拒绝访问；当前实现已经按此边界 fail-closed。
- 这不是 Prometheus、OpenTelemetry 或多实例聚合方案。
- 生产环境如果需要稳定观测，应把进程内计数迁移到正式指标管道，而不是继续依赖单进程内存状态。

## 生产接入接口方向

- Prometheus 路线：
  - 保留当前指标语义，但改为 exporter 或集中 metrics backend。
- OpenTelemetry 路线：
  - 把 request id、duration、generation status、provider error 等结构化信号统一送入 trace / metric pipeline。
- 当前不做的事情：
  - 不在这个仓库里把进程内 JSON 端点包装成“生产级观测系统”。

## SLI / SLO

### SLI 1：Skeleton 可用率

- Numerator：`/query` 计划类请求返回 `structured_training_plan`、`monthly_training_calendar`、`daily_schedule_cards` 的次数。
- Denominator：所有计划类 `/query` 请求。
- Target：本地验收 100%；生产目标 99%。
- Window：本地按测试运行；生产按 7 天滚动。
- Exclusions：非计划类普通 QA 请求、客户端主动取消请求。

### SLI 2：计划生成延迟

- Numerator：`generation_timings.total_sec <= 5` 或 skeleton-first 首包成功的计划类请求。
- Denominator：所有计划类 `/query` 请求。
- Target：本地 skeleton-first 路径 100%；生产 P95 小于 5 秒。
- Window：本地按测试运行；生产按 24 小时和 7 天滚动。
- Exclusions：外部 LLM 完整解释补全过程。

### SLI 3：反馈计算成功率

- Numerator：`/feedback` 返回 `risk_gate`、`protocol_recheck`、`adaptive_adjustment` 的次数。
- Denominator：所有 `/feedback` 请求。
- Target：本地验收 100%；生产目标 99.5%。
- Window：本地按测试运行；生产按 7 天滚动。
- Exclusions：请求体非法导致的 4xx。

### SLI 4：医疗风险 fail-closed 正确率

- Numerator：胸痛、头晕/晕厥、中暑迹象返回 `generation_status=medical_referral` 且不生成高强度替代训练的次数。
- Denominator：包含医疗红旗的反馈请求。
- Target：100%。
- Window：本地按测试运行；生产按 30 天滚动。
- Exclusions：无医疗红旗关键词且用户未表达相关症状的反馈。

### SLI 5：证据缺失可见率

- Numerator：缺少本地证据时 UI 或响应明确标注 `llm_general_knowledge`、`needs_evidence` 或等价说明的次数。
- Denominator：缺少本地证据但仍需要解释的请求。
- Target：100%。
- Window：本地按契约测试；生产按 7 天滚动。
- Exclusions：核心处方字段。核心处方字段不能由一般知识填充。

## 排查顺序

1. 先拿 `X-Request-ID`。
2. 查看 HTTP status 和 `/ops/metrics.requests_total/errors_total`。
3. 查看响应里的 `generation_status`。
4. 查看 `workflow_trace` 的 `status`、`intent_type`、`workflow_kind`。
5. 对计划问题查看 `training_plan_id` 和 `/plans/{plan_id}`。
6. 对反馈问题查看 `feedback_id`、`risk_gate.triggers`、`protocol_recheck.allowed`。
7. 对延迟问题查看 `generation_timings` 与 `plan_generation_duration_buckets`。
8. 对医疗风险问题查看 `medical_referral_total` 和 `feedback_risk_reason_counts`。
9. 对证据问题查看 `field_sources`、`evidence_tier`、`needs_evidence`。

## 告警分级建议

- P0：医疗红旗未 fail-closed，或高强度替代训练进入医疗风险响应。
- P0：计划类 `/query` 无结构化计划且没有 skeleton fallback。
- P1：`/feedback` 无风险门或调整建议。
- P1：`/plans/{plan_id}` 无法回显已保存反馈。
- P2：`/ops/metrics` 不增长或 request id 丢失。
- P2：OpenAPI schema 为空导致前端契约漂移。

## 数据安全约束

- 不记录完整 query 原文到 metrics。
- 不记录 `ds_api_key`、OAuth token、refresh token、authorization header。
- 不把用户备注作为 metrics label。
- 不把 profile 私密字段写入公开文档或测试快照。

## 限流 Caveat

- 当前限流实现是单进程内存字典，适合作为本地开发和轻量兜底。
- 当前实现不保证多实例、跨进程或跨节点的一致限流。
- 如果进入真正生产环境，限流应交给 API Gateway、负载均衡器或 Redis token bucket 一类的共享基础设施。

## 验证命令

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_observability_contract.py tests/test_security_guards.py -q
```
