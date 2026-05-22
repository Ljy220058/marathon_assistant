# Round 4+ Backend TODO：release hardening 后端工程与验证叠加记录

> 生成时间：2026-05-22
> 轮次：Round 4+ overlays（保留 Round 3 模板容量并叠加后续轮次记录）
> 产物类型：audit todo
> 最低容量要求：500 行以上，本文件设计为 20 个子阶段，每个子阶段包含审计、修复、验收和 review 颗粒度。

## Round 4+ 覆盖说明

- [x] 本文件当前是 Round 4+ backend todo；原 Round 3 通用阶段作为 500 行以上容量模板保留在后文。
- [x] 当前主角色：Backend / Engineering Coordinator。
- [x] 历史记录：本轮早期曾按旧规则开启 2 个只读 reviewer/explorer：`019e4c3d-87b7-75b3-bf1b-6efcf3de91b7`、`019e4c3d-ce53-7b73-b274-7b59e7d9ff88`；新规则生效后，后续每轮最多 1 个。2026-05-22 又主动关闭遗留子 agent：`019e4c04-f87d-7fd3-a3e1-2f3e6bd4bd48`、`019e4c10-51cc-7310-95b8-88a15a706ea1`、`019e4c35-ff2d-7dc3-ae08-8007d875d4aa`。
- [ ] 本轮后端优先级来自 shared contract、requirements todo 和 reviewer findings。
- [ ] 本轮必须提醒前端 owner 阅读 `docs/quality/shared_delivery_contract.md`，尤其是反馈状态同步、训练负荷真实性、key 不持久化和普通模式不暴露调试字段。
- [ ] 本轮后端不得 broad stage，不得修改无关用户数据、知识图谱缓存、论文目录或前端 agent 的非阻塞 UI 工作。

## Round 5 Backend / Engineering Coordinator Overlay

- [x] 后端 reviewer T1：旧版 `schema_migrations` 缺 `checksum` 列会启动失败。已补 `_ensure_schema_migrations_checksum`，并用 `test_database_migrates_legacy_schema_migrations_checksum_column` 验证。
- [x] 后端 reviewer T1：未知/404 路径可能把任意 path segment 写入 metrics label。已把未匹配路由收敛为 `/__unmatched__`，并用 `test_ops_metrics_collapses_unknown_routes_without_leaking_segments` 验证。
- [x] 后端 reviewer T2：版本边界只靠人工规则。已在 `tools/dev/check_repo.py` 增加 `version-exclusions`，对 staged 的 `data/vector_kb/default/user_profile.json`、`knowledge_graph.json`、`papers/`、`artifacts/frontend-audit/`、OCR markdown 直接报错，对未暂存 dirty 文件告警。
- [x] 后端 reviewer T2：`calculate_hr_trimp_training_load` 仍使用 `physiology_proxy`。已改为 `hr_trimp_estimated / estimated_heart_rate_proxy / estimated`，并用 `test_heart_rate_trimp_load_keeps_estimated_boundary` 验证。
- [x] 后端 reviewer T3：旧库 `training_calendar_events.sync_status` 补列缺直接断言。已补 `test_database_migrates_legacy_calendar_event_sync_status`。
- [x] 前端 reviewer T1：普通模式暴露 `fail-closed` 技术词。已改为用户可读医疗红旗/安全边界文案，并由 `test_astro_normal_mode_hides_internal_diagnostics_and_connection_labels` 防回归。
- [x] 前端 reviewer T1：调整历史可能把 `feedback_id` 当时间展示。已移除可见 fallback，并由同一普通模式契约测试防回归。
- [x] 前端 reviewer T2：drawer 只移动 profile、可能遮挡 day modal。已恢复 `profile/calendar-section/evidence` 进入 drawer、选择非 drawer 目标时关闭 drawer，并确认 `.day-modal`/`.evidence-drawer` 层级高于移动 drawer。
- [x] 目标矩阵复跑：`tests/test_api_app.py tests/test_api_cli_startup_contract.py tests/test_astro_frontend_contract.py tests/test_daily_schedule_generator.py tests/test_plan_workflow_expectations.py tests/test_state_models.py tests/test_security_guards.py tests/test_database_migrations.py tests/test_openapi_contract.py tests/test_observability_contract.py -q` 当前 172 passed，2 个第三方 warning。
- [x] 完整 `python -m pytest -q`：392 passed，3 个第三方 warning。
- [x] `npm run build` in `apps/web`：passed。
- [x] 隔离 preview smoke：`WORKSPACE_URL=http://127.0.0.1:4322/#workspace npm run smoke:workspace` passed。
- [x] `git diff --check`：passed。
- [x] `tools/dev/check_repo.py --scope hygiene`：passed；新增 `version-exclusions` 对未暂存排除路径告警、对 staged 排除路径 hard fail。

## Round 6 Backend / Security Overlay

- [x] 商用化安全 P0：先落地资源滥用防护，不等完整 auth 系统才开始保护 GPT/DS 成本入口。
- [x] 新增 in-memory rate limit middleware，默认 `MARATHON_RATE_LIMIT_PER_MINUTE=600`，可通过环境变量调整；`0` 表示显式关闭。
- [x] 限流范围只覆盖敏感/写入/高成本路径前缀：`/query`、`/feedback`、`/training-calendar`、`/plans`、`/profile`。
- [x] client key 优先使用 `X-Forwarded-For` 首个 IP，否则使用 `request.client.host`；不把用户 query 原文、token 或 plan_id 放入限流 key。
- [x] 超限返回 429，带 `Retry-After: 60`，文案为用户可读中文，不泄漏内部 bucket key。
- [x] 补测试 `test_api_rate_limit_blocks_repeated_sensitive_requests`，用 `MARATHON_RATE_LIMIT_PER_MINUTE=1` 验证第二次 `/feedback` 被 429 拦截。
- [x] 验证：`tests/test_api_app.py tests/test_security_guards.py tests/test_observability_contract.py tests/test_openapi_contract.py -q` 51 passed，2 warnings。
- [x] 验证：完整 `python -m pytest -q` 395 passed，3 warnings。
- [x] 商用化安全 P0：新增可配置 API token 护栏。设置 `MARATHON_API_TOKEN` 后，除 `/health`、引用表、OpenAPI/docs、`/llm-options` 外，其余 API 需要 `Authorization: Bearer ...` 或 `X-Marathon-API-Key`。
- [x] API token 校验使用 `hmac.compare_digest`，失败返回 401 和 `WWW-Authenticate: Bearer`，不回显 token。
- [x] 补测试 `test_api_token_protects_non_public_endpoints_when_configured`，验证公开健康检查仍可用、`/plans` 无 token/错 token 拒绝、正确 token 放行，且 `/ops/metrics` 在 token 模式下不再裸露。
- [x] CORS preflight 兼容：token 模式下 `OPTIONS` 不要求 token，避免浏览器预检被 401 拦截；同一测试已覆盖。
- [x] 对象级授权补洞：`DELETE /plans/{plan_id}` 现在先读取 plan 并确认 `plan.user_id == user_id`，否则 404，不再允许 default_user 删除未来/旧库中的其他 user plan。
- [x] 补测试 `test_delete_plan_refuses_plan_owned_by_another_user`，确认跨 user plan 不被删除；`test_delete_plan_removes_plan_and_events` 仍通过。
- [x] GPT/DS provider 路线落地第一步：`ai_invoke` 支持 OpenAI Responses API provider，`llm_provider=openai/gpt` 走服务端 `OPENAI_API_KEY` 或测试注入 key。
- [x] `/llm-options` 新增 `openai` provider，返回 `OPENAI_MODEL`、`api_key_configured`，默认模型当前为 `gpt-5.2`。
- [x] OpenAI provider 测试不依赖真实网络：`tests/test_llm_provider_contract.py` 用 fake `httpx.AsyncClient` 验证 `/responses` 请求、Authorization header、usage 汇总和缺 key 错误。
- [x] 验证：`tests/test_llm_provider_contract.py -q` 2 passed；`tests/test_api_app.py::test_llm_options_support_frontend_model_controls -q` passed。
- [x] 验证：`tests/test_llm_provider_contract.py tests/test_api_app.py tests/test_astro_frontend_contract.py tests/test_security_guards.py -q` 107 passed，2 warnings。
- [x] 验证：完整 `python -m pytest -q` 398 passed，3 warnings。
- [ ] 仍未完成：AuthN/AuthZ、租户隔离、对象级授权、登录态、计费级 quota、API key 管理，这些仍是商用发布前 P0。
- [ ] 仍未完成：分布式部署下的 Redis/外部 rate limiter；当前 in-memory 只适合单进程本地/预发布。

## Round 7 Backend / Engineering Coordinator Overlay

- [x] 当前执行角色：Backend / Engineering Coordinator。
- [x] 本轮已读 `docs/quality/shared_delivery_contract.md` 与 `docs/quality/release_hardening_loop.md`。
- [x] 本轮继承用户硬约束：任何细小问题都必须修复或记录，不允许用“差不多”结束。
- [x] 历史记录：本轮沿用并收拢 2 个只读 reviewer：Backend/Security reviewer 与 Frontend/API contract reviewer；新规则生效后，后续每轮最多 1 个。
- [x] 用户追加新规则：后续轮次最多 1 个子智能体；本轮已关闭两个遗留 reviewer，后续不再同时开两个。
- [x] Backend/Security reviewer T1：rate limit 默认信任 `X-Forwarded-For`，可被伪造绕过并制造高基数 bucket。
- [x] 修复：默认不信任 `X-Forwarded-For`；只有 `MARATHON_TRUST_PROXY_HEADERS=1` 才解析代理头。
- [x] 修复：代理头解析使用 `ipaddress.ip_address` 规范化非法值，避免把任意长字符串直接作为 bucket key。
- [x] 修复：新增 `_prune_rate_limit_buckets`，清理 60 秒外过期 bucket，并用 `MARATHON_RATE_LIMIT_MAX_BUCKETS` 设置上限。
- [x] 验证：新增 `test_api_rate_limit_does_not_trust_spoofed_forwarded_for_by_default`，不同伪造 XFF 第二次仍 429，bucket 数为 1。
- [x] Backend/Security reviewer T2：`/feedback` 提供非法 `plan_id/event_id` 时静默返回 200 和 `feedback_id=None`。
- [x] 修复：未提供 plan/event 时保持“只计算建议、不入库”的兼容路径。
- [x] 修复：只提供 plan 或 event 其中之一时返回 400，避免半绑定状态。
- [x] 修复：同时提供 plan/event 时先 `get_event(plan_id, event_id, user_id)` 验证所属关系，不存在时 404。
- [x] 验证：新增 `test_feedback_endpoint_rejects_invalid_plan_event_fields`，非法事件返回 404。
- [x] 验证：保留 `test_feedback_endpoint_without_plan_event_fields_keeps_contract`，无事件仍可返回调整建议。
- [x] Backend/Security reviewer T2：OpenAI provider async 测试在缺 `pytest-asyncio` 环境被 skip。
- [x] 修复：`tests/test_llm_provider_contract.py` 改为同步 `asyncio.run`，不依赖外部 async pytest 插件。
- [x] 修复：新增 `LLMProviderError`，包含 `provider/error_code/status_code`，并保持 `RuntimeError` 兼容。
- [x] 修复：OpenAI/DeepSeek provider 结构化分类 `missing_key / timeout / rate_limited / provider_5xx / invalid_request / network_error / invalid_response`。
- [x] 修复：`/ops/metrics` 新增 `llm_provider_error_counts`，只记录 provider 与错误代码，不记录 prompt、密钥或上游错误体。
- [x] 验证：新增 OpenAI 429 分类测试，`error_code=rate_limited` 且 `status_code=429`。
- [x] Backend/Security reviewer T3：token guard 模式下 `/llm-options` 公开暴露上游 key 是否配置。
- [x] 修复：`/llm-options` 接收 `Request`，在 `MARATHON_API_TOKEN` 配置时，未认证请求隐藏 `api_key_configured`。
- [x] 修复：带有效 `Authorization: Bearer` 或 `X-Marathon-API-Key` 时返回真实 provider key 配置状态。
- [x] 验证：新增 `test_llm_options_masks_provider_key_status_when_token_guard_is_enabled`。
- [x] Frontend/API reviewer T1：API token guard 开启后前端无全局 token 注入。
- [x] 修复：前端专家设置新增 `apiToken`，仅本页内存态；请求通过 `X-Marathon-API-Key` 注入。
- [x] 验证：新增前端契约断言，不存在 `localStorage/sessionStorage` token 持久化。
- [x] Frontend/API reviewer T2：OpenAI provider 忽略 `api_key_configured`，未配置时拖到 `/query` 才失败。
- [x] 修复：前端记录 provider config；OpenAI 未配置时生成前阻断并提示服务端配置 `OPENAI_API_KEY` 或切换 Ollama。
- [x] 修复：专家快捷 provider 按钮补 OpenAI，和动态 select 保持一致。
- [x] Frontend/API reviewer T2：普通可见负荷文案仍有“计划负荷/周负荷”孤立标签。
- [x] 修复：统一为“计划代理负荷 / 周代理负荷 / 代理周负荷”。
- [x] 目标验证：`tests/test_security_guards.py ... tests/test_astro_frontend_contract.py -q` 当前 94 passed；随后新增 smoke 契约测试已单独通过。
- [x] 验证：完整 `python -m pytest -q` 已重跑，405 passed。
- [x] 验证：`npm run build` in `apps/web` 已重跑，passed。
- [x] 验证：隔离 preview 自动落到 `http://127.0.0.1:4325/#workspace`，`npm run smoke:workspace` passed；preview 进程已停止。
- [x] 验证：`git diff --check` passed。
- [x] 验证：`python tools/dev/check_repo.py --scope hygiene` passed with expected historical warnings only。
- [ ] 仍未完成：token guard on/off 与 OpenAI configured/unconfigured 需要浏览器或 smoke 矩阵覆盖。
- [ ] 仍未完成：完整商用 AuthN/AuthZ、租户隔离、账号级 quota、分布式限流、abuse dashboard。
- [ ] 仍未完成：provider 成本估算、重试策略、token budget、provider SLA 监控。

## Round 8 Backend / Error Boundary Overlay

- [x] 当前执行角色：Backend / Engineering Coordinator。
- [x] 本轮遵守新 agent 规则：未新开子智能体；当前 0/1。
- [x] 审计发现：`/query` plan fallback 曾把 `str(e)` 拼入用户可见 `message`，provider 原始错误体有泄漏风险。
- [x] 审计发现：`/training-calendar` 500 曾返回 `detail=str(e)`，同样可能泄漏内部异常、URL 或供应商错误体。
- [x] 修复：新增 `_safe_workflow_error_summary`，provider 错误只暴露 `provider/error_code`，其他异常只暴露稳定摘要。
- [x] 修复：`/query` 的 `llm_error_skeleton` message 不再包含原始异常字符串。
- [x] 修复：非计划 `/query` 500 detail 不再使用 `str(e)`。
- [x] 修复：`/training-calendar` 500 detail 不再使用 `str(e)`。
- [x] 修复：`plan_nodes` 的 LLM fallback reason 不再拼接原始异常，只保留异常类或 provider/error_code。
- [x] 测试：`test_plan_query_full_error_falls_back_to_error_skeleton` 断言 `model provider failed` 不泄漏。
- [x] 测试：`test_plan_query_provider_error_message_does_not_leak_raw_details` 断言 `sk-secret` 与原始错误体不泄漏。
- [x] 测试：`test_training_calendar_error_does_not_leak_raw_exception` 断言 500 detail 为稳定摘要。
- [x] 验证：错误边界目标矩阵 11 passed。
- [x] 最终验证：完整 `python -m pytest -q`、`npm run build`、workspace smoke、repo hygiene 已在 Round 9 overlay 重跑并记录。

## Round 10 Backend / Engineering Coordinator Overlay - 计划评审与 GPT 默认接入

- [x] 当前执行角色：Backend / Engineering Coordinator。
- [x] 本轮使用 `codex-work-team`：主线程承担 coordinator/backend/reviewer 的整合职责，不把阻塞实现交给子 agent。
- [x] 子 agent 管理：尝试开启 1 个只读 reviewer，因上游 504 无结果；随后按用户要求尝试关闭最近 24 个候选 id，工具返回 `not found`，当前不再开启新 agent。
- [x] TDD 红灯 1：`tests/test_llm_provider_contract.py::test_openai_defaults_use_configured_commercial_gateway` 先失败，旧默认仍为 `gpt-5.2` / OpenAI 官方 base URL 或受 dotenv 覆盖。
- [x] 修复 1：`apps/backend/src/marathon_qa_assistant/nodes/common.py` 默认 `OPENAI_MODEL=gpt-5.5`，默认 `OPENAI_BASE_URL=https://api.aisz.mom/v1`。
- [x] 修复 2：`apps/backend/src/marathon_qa_assistant/apps/api_app.py` 的 `_selected_model()` 与 `/llm-options` OpenAI 默认模型同步为 `gpt-5.5`。
- [x] 测试加固：默认 provider 测试禁用 dotenv 影响，避免本机 `.env` 把默认契约误判为实现失败。
- [x] 安全边界：未把用户提供的 API key 写入任何文件、测试、TODO、契约或最终输出；后端只依赖服务端环境变量。
- [x] TDD 红灯 2：新增 `tests/test_training_plan_review.py` 时先因模块不存在失败。
- [x] 修复 3：新增 `apps/backend/src/marathon_qa_assistant/services/training_plan_review.py`，提供 `build_training_plan_review()`。
- [x] 修复 4：`QueryResponse`、`PlanDetailResponse`、`TrainingCalendarResponse` 增加 `training_plan_review` 字段。
- [x] 修复 5：`/query` skeleton-first 路径构建日历后同步构建 `training_plan_review`。
- [x] 修复 6：完整 `/query` 状态响应在缺少评审时从 `structured_training_plan` 与 `daily_schedule_cards` 回填 `training_plan_review`。
- [x] 修复 7：`/training-calendar` 返回 `training_plan_review`，供前端直接对接。
- [x] 修复 8：`GET /plans/{plan_id}` 返回 `training_plan_review`，历史计划保留评审入口。
- [x] 修复 9：OpenAPI 契约测试断言三类响应 schema 都暴露 `training_plan_review`。
- [x] 计划评审维度：`training_load` 明确 `planned_load_proxy`、`not_device_metric`、缺失 HR/HRV/sleep/device recovery 等输入。
- [x] 计划评审维度：`plan_structure` 统计总天数、训练日、休息日、质量课、每周质量课密度。
- [x] 计划评审维度：`periodization` 统计计划周数、阶段数量、阶段名称和阶段边界。
- [x] 计划评审维度：`injury_recovery` 读取 `risk_gate` 状态并识别 blocked/medical referral。
- [x] 计划评审维度：`rehabilitation` 识别 recovery、pain、bike/cycling/elliptical/swim/walk/低冲击/康复 等回归训练信号。
- [x] 计划评审维度：`strength_conditioning` 识别 strength/conditioning/core/力量/体能/核心，没有则标为 gap。
- [x] 计划评审维度：`mobility_recovery` 统计 warmup/cooldown 覆盖率和 stretch/mobility/foam roll/拉伸/放松等信号。
- [x] 计划评审维度：`injury_prevention` 检查无休息周、过多质量课、周负荷大跳变和恢复覆盖。
- [x] 计划评审维度：`evidence_control` 统计 evidence tier，检查核心处方字段是否由 forbidden LLM source 越权。
- [x] 计划评审维度：`rag_vs_base_model` 输出可追溯天数、模型通用知识天数、证明点和边界说明。
- [x] 核心字段边界：`workout_type/main_set/intensity/duration/weekly_quality_count/long_run_cap/progression/risk_downgrade` 不允许 `llm_expression` 或 `llm_general_knowledge` 作为核心来源。
- [x] 目标验证：`tests/test_training_plan_review.py` 通过。
- [x] 目标验证：`tests/test_api_app.py::test_plan_query_skeleton_mode_returns_without_integrated_app` 通过。
- [x] 目标验证：`tests/test_llm_provider_contract.py::test_openai_defaults_use_configured_commercial_gateway` 通过。
- [x] 目标验证：`tests/test_openapi_contract.py::test_openapi_response_schemas_match_shared_delivery_contract` 通过。
- [ ] P0 后续：`/query` 完整 LLM 路径若 `structured_report` 自带旧式日历但无 day cards，应补更强的兼容测试。
- [ ] P1 后续：`training_plan_review` 当前是 deterministic review，不等于运动医学临床评估；前端文案必须避免“医学认证/设备恢复”暗示。
- [ ] P1 后续：`rehabilitation` 和 `strength_conditioning` 目前依赖关键词启发式，后续应改为动作库/知识库标签驱动。
- [ ] P1 后续：`periodization` 只检查阶段存在性，不检查阶段比例是否合理；后续需要根据 5K/10K/HM/FM/回归训练协议分型。
- [ ] P1 后续：`training_load` 只检查代理负荷和周变化，仍缺真实执行反馈后 acute/chronic 趋势与个体恢复状态。
- [ ] P1 后续：`rag_vs_base_model` 目前证明的是“可追溯/可复核/可 fail-closed”，不是“训练效果优于裸模型”；后续需要计划评审 benchmark 和专家评分数据。
- [ ] P2 后续：把计划评审指标进入 `/ops/metrics`，例如 review_status_counts、needs_evidence_count、core_source_violation_count。
- [ ] P2 后续：把计划评审结果写入保存计划时的 snapshot，避免后续算法变化导致历史计划回显不一致。
- [ ] P2 后续：把分层知识库 metadata 接入评审，输出 evidence domain、evidence freshness、applicability 和 contraindications。
- [ ] P2 后续：为医疗红旗场景新增计划评审夹具，确保 high intensity replacement 不进入 rehab/injury recovery 维度。

## Round 9 Backend / Coordinator Retest Overlay

- [x] 本轮仍由 Backend / Engineering Coordinator 负责，不替 Frontend owner 或 QA/reviewer 最终签收。
- [x] 先跑完整 `python -m pytest -q`，命中前端契约 5 个失败，失败集中在普通用户层文案：`ProfileEditor`、`证据抽屉`、`Marathon Assistant`、`Training Calendar Builder`、`动作库命中`、`协议通过`、缺少 `训练压力`。
- [x] 最小修复：把品牌与普通层文案改为中文产品化表达；把画像编辑器内部 camelCase 识别名替换为 `ProfilePanel` 系列；把证据面板改为 `为什么这样练 / 依据详情`；把信任条改为 `安排来源 / 安全检查`；把负荷面板标题改为 `训练压力`。
- [x] 额外修复：`apps/backend/src/marathon_qa_assistant/nodes/plan_nodes.py` 两处 trailing whitespace 已清理，避免 `git diff --check` 失败。
- [x] 定点验证：`$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; C:\\Users\\26318\\anaconda3\\envs\\torch2.5.1\\python.exe -m pytest tests/test_astro_frontend_contract.py -q` 65 passed。
- [x] 全量验证：`$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; C:\\Users\\26318\\anaconda3\\envs\\torch2.5.1\\python.exe -m pytest -q` 408 passed，3 warnings。
- [x] 构建验证：`npm run build` in `apps/web` passed。
- [x] smoke 验证：默认 `npm run smoke:workspace` passed（命中 4321 既有 dev server）；隔离端口 `WORKSPACE_URL=http://127.0.0.1:4330/#workspace npm run smoke:workspace` 也 passed，且 4330 临时进程已关闭。
- [x] 仓库验证：`git diff --check` passed；`python tools/dev/check_repo.py --scope hygiene` passed with已有 dirty/version-excluded warnings。
- [x] 结论：当前没有新的后端/前端契约失败，但仍存在需要 QA/reviewer 独立签收的 dirty worktree 和版本边界告警。

## Round 4 P0：后端已处理项

- [x] 反馈提交后前端状态同步：补 `applyLatestFeedbackToLastResponse`，把最新反馈写回 `monthly_training_calendar.days`、`daily_schedule_cards`、`structured_training_plan.week_plans[].days` 和 `adjustment_history`。
- [x] 前端契约测试：补断言，防止只更新 `state.selectedDay` 导致状态面板/调整历史读旧数据。
- [x] SQLite migration checksum：已应用 migration 文件 checksum 改写时 fail-fast，避免已发布 migration 被静默篡改。
- [x] migration 测试：新增“已应用 migration 被修改应抛错”测试。
- [x] observability 高基数路径：请求指标改用 route template，避免 `/plans/{uuid}` 进入指标 label。
- [x] observability 契约：`/ops/metrics` 增加 `request_route_counts`，测试断言动态 plan id 不泄漏到 route key。
- [x] OpenAPI 契约：补 `FeedbackResponse`、`PlanDetailResponse`、`OpsMetricsResponse` required 字段断言。
- [x] 训练负荷真实性：`calculate_plan_training_load` 改为 `planned_zone_duration_proxy`，增加 `source_type/load_kind/is_estimated/not_device_metric/calculation_inputs/missing_inputs/disclaimer`。
- [x] 训练负荷真实性测试：新增日卡和 summary 负荷字段必须明确估算边界。
- [x] 共享契约：固化无限轮次 release hardening、角色边界、需求证据、知识库厚度、GPT/DS API 和负荷真实性。

## Round 4 P0：后端验证记录

- [x] 跑 `tests/test_database_migrations.py`，确认 checksum fail-fast 不破坏空库/旧库/重复启动。验证：目标矩阵 110 passed，完整 pytest 387 passed。
- [x] 跑 `tests/test_observability_contract.py`，确认 route template 指标和 request id 正常。验证：目标矩阵 110 passed，完整 pytest 387 passed。
- [x] 跑 `tests/test_openapi_contract.py`，确认 schema required 字段稳定。验证：目标矩阵 110 passed，完整 pytest 387 passed。
- [x] 跑 `tests/test_daily_schedule_generator.py`，确认负荷字段和日卡生成未回归。验证：目标矩阵 110 passed，完整 pytest 387 passed。
- [x] 跑 `tests/test_astro_frontend_contract.py`，确认反馈状态同步字符串契约通过。验证：目标矩阵 110 passed，完整 pytest 387 passed。
- [x] 跑完整 `python -m pytest -q`，确认当前 pytest.ini 只收集项目 tests。验证：387 passed，3 个第三方 deprecation warning。
- [x] 跑前端 build，确认最小前端兼容修复未破坏 Astro 构建。验证：`npm run build` passed。
- [x] 跑隔离 preview smoke，避免 4321 旧服务污染。验证：`WORKSPACE_URL=http://127.0.0.1:4322/#workspace npm run smoke:workspace` passed。
- [x] 跑 `git diff --check`。验证：passed。
- [x] 跑 `tools/dev/check_repo.py --scope hygiene`，只接受已知历史 warning，不接受新增 hard fail。验证：passed with historical WARNs only。

## Round 4 P1：后端后续商用化路线

- [ ] AuthN/AuthZ：当前仍是本地单用户 `default_user`，商用前必须设计租户隔离和对象级授权。
- [ ] Rate limit：GPT/DS API 接入前必须有限流、并发、timeout 和 max token 预算。
- [ ] Provider 抽象：把 GPT/DeepSeek 作为服务端 provider，不让浏览器持久化 key。
- [ ] KB 分层：把训练协议、动作库、运动医学边界、负荷解释、竞品证据和用户案例分层管理。
- [ ] Evidence API：EvidenceDrawer 需要可点击证据定位，而不是只展示字段来源。
- [ ] Plan diff：反馈生成调整版计划后，后端应返回结构化 diff，不只依赖 prompt。
- [ ] Metrics export：当前 `/ops/metrics` 是进程内 JSON，生产前需要 scrape/export/alert owner。
- [ ] Migration discipline：后续 schema 变化必须新增 SQL，不修改旧 migration。
- [ ] Training load versioning：负荷算法变更需要 `load_model_version` 和回放测试。
- [ ] Commercial disclaimer：健康/训练建议边界需要产品级 copy 和 API-level status，不仅靠前端文本。

## 执行原则

- [x] 原则：中文优先记录结论，技术标识保持原文。
- [x] 原则：只处理当前 TODO 相关文件，不回滚其他 agent 或用户改动。
- [x] 原则：所有行为以测试或可复查证据闭环，不靠口头完成。
- [x] 原则：前端真实入口是 apps/web 的 Astro 页面，不修改 Chainlit 当作主入口。
- [x] 原则：无本地证据时允许 llm_general_knowledge 一般说明，但不能进入核心处方字段。
- [x] 原则：医疗红旗和疼痛风险必须 fail-closed。
- [x] 原则：数据库演进必须兼容旧库、空库和重复启动。
- [x] 原则：默认安全配置不能依赖开发者记忆。
- [x] 原则：观测信号必须能定位请求、生成状态和风险原因。
- [x] 原则：Git 只检查状态，不 broad stage，不 commit，不 push。

## 技能调用矩阵

- [x] Skill 1：codex-engineering-workflow，用于 audit todo 中的对应审计或 review 视角。
- [x] Skill 2：codex-todo-automation，用于 audit todo 中的对应审计或 review 视角。
- [x] Skill 3：architecture-quality-workflow，用于 audit todo 中的对应审计或 review 视角。
- [x] Skill 4：improve-codebase-architecture，用于 audit todo 中的对应审计或 review 视角。
- [x] Skill 5：api-designer，用于 audit todo 中的对应审计或 review 视角。
- [x] Skill 6：senior-backend，用于 audit todo 中的对应审计或 review 视角。
- [x] Skill 7：database-architect，用于 audit todo 中的对应审计或 review 视角。
- [x] Skill 8：frontend-designer，用于 audit todo 中的对应审计或 review 视角。
- [x] Skill 9：security-scanner，用于 audit todo 中的对应审计或 review 视角。
- [x] Skill 10：observability-advisor，用于 audit todo 中的对应审计或 review 视角。
- [x] Skill 11：project-flow-guardrails，用于 audit todo 中的对应审计或 review 视角。
- [x] Skill 12：git-workflow-guardrails，用于 audit todo 中的对应审计或 review 视角。
- [x] Skill 13：karpathy-guidelines，用于 audit todo 中的对应审计或 review 视角。

## 轮次叙述

第 3 轮聚焦最终收口：OpenAPI 文档、观测基线、维护路线图链接、最终测试矩阵、仓库卫生和 Git 风险清单。

## P01：前端入口拆分

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：index.astro 单文件过载导致 UI 改动高风险。
- [ ] Skill 主视角：codex-engineering-workflow。
- [ ] Skill 交叉视角：codex-todo-automation。
- [ ] Skill Review 视角：architecture-quality-workflow。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P02：前端域模块

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：模块只有占位元数据时容易被误认为完成彻底拆分。
- [ ] Skill 主视角：codex-todo-automation。
- [ ] Skill 交叉视角：architecture-quality-workflow。
- [ ] Skill Review 视角：improve-codebase-architecture。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P03：Astro 契约测试

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：字符串契约需要覆盖拆分后的脚本和样式源。
- [ ] Skill 主视角：architecture-quality-workflow。
- [ ] Skill 交叉视角：improve-codebase-architecture。
- [ ] Skill Review 视角：api-designer。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P04：API schema 抽离

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：Pydantic class 留在聚合层会继续扩大 api_app.py。
- [ ] Skill 主视角：improve-codebase-architecture。
- [ ] Skill 交叉视角：api-designer。
- [ ] Skill Review 视角：senior-backend。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P05：OpenAPI 响应模型

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：/feedback 与 /plans/{id} schema 为空会阻塞 contract-first 联调。
- [ ] Skill 主视角：api-designer。
- [ ] Skill 交叉视角：senior-backend。
- [ ] Skill Review 视角：database-architect。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P06：反馈风险边界

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：疼痛或医疗红旗不能生成高强度替代训练。
- [ ] Skill 主视角：senior-backend。
- [ ] Skill 交叉视角：database-architect。
- [ ] Skill Review 视角：frontend-designer。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P07：SQLite migration

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：旧库缺列会在索引或反馈读取阶段失败。
- [ ] Skill 主视角：database-architect。
- [ ] Skill 交叉视角：frontend-designer。
- [ ] Skill Review 视角：security-scanner。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P08：反馈持久化回显

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：latest_feedback 和 adjustment_history 不能丢审计链。
- [ ] Skill 主视角：frontend-designer。
- [ ] Skill 交叉视角：security-scanner。
- [ ] Skill Review 视角：observability-advisor。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P09：CORS 安全默认

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：生产默认全开放 CORS。
- [ ] Skill 主视角：security-scanner。
- [ ] Skill 交叉视角：observability-advisor。
- [ ] Skill Review 视角：project-flow-guardrails。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P10：浏览器密钥处理

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：DeepSeek API key 不应持久化到 localStorage。
- [ ] Skill 主视角：observability-advisor。
- [ ] Skill 交叉视角：project-flow-guardrails。
- [ ] Skill Review 视角：git-workflow-guardrails。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P11：请求关联

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：无 X-Request-ID 时日志、trace、metrics 难以关联。
- [ ] Skill 主视角：project-flow-guardrails。
- [ ] Skill 交叉视角：git-workflow-guardrails。
- [ ] Skill Review 视角：karpathy-guidelines。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P12：运行指标

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：没有 generation_status 和 feedback risk 分布就无法运营排障。
- [ ] Skill 主视角：git-workflow-guardrails。
- [ ] Skill 交叉视角：karpathy-guidelines。
- [ ] Skill Review 视角：codex-engineering-workflow。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P13：证据链 UI

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：无证据时不能伪造引用，但可展示 llm_general_knowledge 说明。
- [ ] Skill 主视角：karpathy-guidelines。
- [ ] Skill 交叉视角：codex-engineering-workflow。
- [ ] Skill Review 视角：codex-todo-automation。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P14：HMP 协议展示

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：半马 HMP 基石协议需要用户可见。
- [ ] Skill 主视角：codex-engineering-workflow。
- [ ] Skill 交叉视角：codex-todo-automation。
- [ ] Skill Review 视角：architecture-quality-workflow。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P15：能力校准

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：旧画像 targetPace 不应直接污染当前计划展示。
- [ ] Skill 主视角：codex-todo-automation。
- [ ] Skill 交叉视角：architecture-quality-workflow。
- [ ] Skill Review 视角：improve-codebase-architecture。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P16：响应构建器候选

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：response builder 未抽离导致 QueryResponse 字段散落。
- [ ] Skill 主视角：architecture-quality-workflow。
- [ ] Skill 交叉视角：improve-codebase-architecture。
- [ ] Skill Review 视角：api-designer。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P17：路由拆分候选

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：过早大搬迁会破坏 monkeypatch 测试。
- [ ] Skill 主视角：improve-codebase-architecture。
- [ ] Skill 交叉视角：api-designer。
- [ ] Skill Review 视角：senior-backend。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P18：文档契约

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：实现变化未沉淀会让下轮 agent 重复踩坑。
- [ ] Skill 主视角：api-designer。
- [ ] Skill 交叉视角：senior-backend。
- [ ] Skill Review 视角：database-architect。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P19：Repo hygiene

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：缓存、数据和个人画像容易混入提交。
- [ ] Skill 主视角：senior-backend。
- [ ] Skill 交叉视角：database-architect。
- [ ] Skill Review 视角：frontend-designer。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P20：Git 交付边界

- [ ] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [ ] 风险：dirty worktree 很重，不能 broad stage。
- [ ] Skill 主视角：database-architect。
- [ ] Skill 交叉视角：frontend-designer。
- [ ] Skill Review 视角：security-scanner。
- [ ] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [ ] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [ ] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [ ] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [ ] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [ ] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [ ] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [ ] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [ ] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [ ] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [ ] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [ ] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [ ] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [ ] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [ ] 前端验收：在 pps/web 运行 
pm run build，必要时运行 
pm run smoke:workspace。
- [ ] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [ ] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [ ] Review 问题 1：这个阶段是否夸大了完成度。
- [ ] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [ ] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [ ] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [ ] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## 最终验收矩阵

- [ ] pytest tests/test_api_app.py tests/test_api_cli_startup_contract.py -q
- [ ] pytest tests/test_astro_frontend_contract.py -q
- [ ] pytest tests/test_plan_workflow_expectations.py tests/test_daily_schedule_generator.py tests/test_state_models.py -q
- [ ] pytest tests/test_security_guards.py tests/test_database_migrations.py tests/test_openapi_contract.py tests/test_observability_contract.py -q
- [ ] cd apps/web; npm run build
- [ ] cd apps/web; npm run smoke:workspace
- [ ] python tools/dev/check_repo.py --scope hygiene
- [ ] git diff --check
- [ ] git status --short --branch
- [ ] 人工 review：确认没有把未完成的大路由拆分说成完成

## 验收记录模板

- [ ] 验收记录占位 1：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 2：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 3：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 4：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 5：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 6：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 7：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 8：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 9：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 10：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 11：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 12：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 13：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 14：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 15：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 16：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 17：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 18：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 19：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 20：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 21：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 22：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 23：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 24：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 25：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 26：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 27：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 28：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 29：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 30：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 31：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 32：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 33：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 34：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 35：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 36：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 37：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 38：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 39：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 40：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 41：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 42：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 43：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 44：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 45：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 46：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 47：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 48：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 49：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 50：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 51：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 52：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 53：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 54：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 55：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 56：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 57：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 58：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 59：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 60：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 61：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 62：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 63：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 64：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 65：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 66：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 67：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 68：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 69：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 70：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 71：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 72：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 73：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 74：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 75：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 76：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 77：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 78：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 79：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [ ] 验收记录占位 80：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
