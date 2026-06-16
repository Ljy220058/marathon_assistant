# Round 4+ Review TODO：release hardening 复核与叠加签收

> 生成时间：2026-05-22
> 轮次：Round 4+ overlays（保留 Round 3 模板容量并叠加后续轮次记录）
> 产物类型：review todo
> 最低容量要求：500 行以上，本文件设计为 20 个子阶段，每个子阶段包含审计、修复、验收和 review 颗粒度。

## Round 9 Backend Coordinator Review Overlay - 子 agent 收口与全量门禁

- [x] 当前执行角色：Backend / Engineering Coordinator。
- [x] 本轮已复读 `docs/quality/shared_delivery_contract.md` 和 `docs/quality/release_hardening_loop.md`。
- [x] 本轮执行用户新规则：关闭无用子 agent，之后最多只开 1 个。
- [x] 已关闭遗留子 agent：`019e4c04-f87d-7fd3-a3e1-2f3e6bd4bd48`。
- [x] 已关闭遗留子 agent：`019e4c10-51cc-7310-95b8-88a15a706ea1`。
- [x] 已关闭遗留子 agent：`019e4c35-ff2d-7dc3-ae08-8007d875d4aa`。
- [x] 本轮新增子 agent 数量：1/1，且为只读 reviewer；完成后已关闭。
- [x] 本轮不替 Frontend owner 或 QA/reviewer 签收最终完成。
- [x] 本轮唯一新增只读 reviewer：`019e4e49-a51e-7311-80db-e2c330f09b6a`，只读审计后已关闭；最终本轮运行中不存在未关闭子 agent。
- [x] Reviewer 结论 P0：未发现阻止当前最小修复继续进入最终签收流程的后端功能性问题。
- [x] Reviewer 结论 P1：版本边界仍阻止直接提交/打版本；`data/vector_kb/default/*.json`、`artifacts/frontend-audit/`、`papers/`、OCR markdown、`todolist.md` 等必须显式排除。
- [x] Reviewer 结论 P2：文档轮次/角色状态存在历史叠加痕迹；已把循环手册主角色改为以共享契约为准，并把 Round 4 文件标题/元数据改成 Round 4+ overlays。
- [x] 完整 pytest 第一轮结果：403 passed / 5 failed，失败均在 `tests/test_astro_frontend_contract.py`。
- [x] 失败 1：普通用户层仍出现 `ProfileEditor`，来源包括可见 kicker 和 JS 函数/DOM ID 命名。
- [x] 失败 2：证据入口仍出现“证据抽屉”，不符合用户级“为什么这样练 / 依据详情”表达。
- [x] 失败 3：页面仍出现 `Marathon Assistant` 和 `Training Calendar Builder` 英文品牌/内部入口词。
- [x] 失败 4：训练负荷普通层缺少“训练压力”文案，同时必须继续保留“计划代理负荷/代理周负荷”真实性边界。
- [x] 失败 5：日卡可信状态仍出现“动作库命中 / 协议通过”这类内部审计标签。
- [x] 修复 1：`apps/web/src/pages/index.astro` 品牌与 hero kicker 改为中文产品文案。
- [x] 修复 2：`apps/web/src/pages/index.astro` 证据面板可见标题改为“为什么这样练 / 依据详情”，关闭按钮改为“关闭依据面板”。
- [x] 修复 3：画像编辑器按钮 ID 与 JS 函数改为 `ProfilePanel` 系列，保留 `profileEditorDialog` 和 `PROFILE_EDITOR_GROUPS` 契约入口。
- [x] 修复 4：`apps/web/src/scripts/app.js` 日卡证据入口改为“为什么这样练”，说明文案改为“统一依据面板”。
- [x] 修复 5：`apps/web/src/scripts/app.js` 信任条标签改为“安排来源 / 安全检查”，协议状态改为“协议已校验”。
- [x] 修复 6：`apps/web/src/scripts/app.js` 动作库兜底文案改为“动作库提供的主课处方”，不再显示“动作库命中”。
- [x] 修复 7：`apps/web/src/scripts/app.js` 负荷趋势 kicker 改为“训练压力”，同时保留“计划代理负荷 / 7日累计代理负荷 / 42日折算代理周负荷”。
- [x] 修复 8：`apps/backend/src/marathon_qa_assistant/nodes/plan_nodes.py` 清理两处 trailing whitespace。
- [x] 定点验证：`tests/test_astro_frontend_contract.py -q` 65 passed。
- [x] 全量验证：`python -m pytest -q` 408 passed，3 个第三方 warning。
- [x] 前端构建：`npm run build` passed。
- [x] 默认 smoke：`npm run smoke:workspace` passed，URL 为 `http://127.0.0.1:4321/#workspace`。
- [x] 隔离 smoke：`WORKSPACE_URL=http://127.0.0.1:4330/#workspace npm run smoke:workspace` passed。
- [x] 临时进程清理：隔离 smoke 后 `127.0.0.1:4330` 已不可连接。
- [x] `git diff --check`：passed。
- [x] `python tools/dev/check_repo.py --scope hygiene`：passed with known warnings。
- [ ] 仍需 QA/reviewer 独立签收：dirty worktree 中 `data/vector_kb/default/*.json`、`artifacts/frontend-audit/`、`papers/`、OCR markdown、`todolist.md` 等不进入版本单元。
- [ ] 仍需 Frontend owner 浏览器签收：token guard on/off、OpenAI configured/unconfigured、401 failure、红旗反馈、普通日卡与负荷摘要截图。
- [ ] 仍需后续商用化设计：完整 authN/authZ、租户隔离、账号级 quota、分布式 rate limit、abuse dashboard。
- [ ] 仍需后续 LLM 运维设计：provider cost estimation、retry policy、token budget、SLA monitoring。
- [ ] 仍需后续 KB 规划：分层知识库、多专家领域知识、训练处方证据厚度、无证据时模型常识回答与核心处方 fail-closed 的边界。

## Round 10 Review Overlay - 计划评审、Agent 收口与前后端契约

- [x] 当前执行角色：Backend / Engineering Coordinator，自审时采用 reviewer 立场，但不替 QA/reviewer owner 做最终签收。
- [x] 本轮遵守用户最新规则：优先关闭不用的 agent；后续最多 1 个子 agent。
- [x] 本轮曾启动唯一只读 reviewer `019e4e94-54b2-7460-af29-7052329e075b`，但上游返回 504，无有效产出。
- [x] 已尝试关闭 `019e4e94-54b2-7460-af29-7052329e075b`，工具返回 `not found`。
- [x] 已从本地 session 记录提取最近 24 个 subagent 候选 id，并逐个调用 `close_agent`。
- [x] 24 个候选 id 关闭结果均为 `not found`，说明当前运行时没有这些 agent 的活动句柄，或已经结束/被系统清理。
- [x] 本轮后续未再开启子 agent。
- [x] 版本边界复查：当前 worktree 仍有大量前端/数据/文档 dirty 文件，本轮不做 broad stage，不回滚其他 agent 改动。
- [x] 安全复查：用户提供的 API key 未写入任何仓库文件；文档只写 provider 边界，不写密钥。
- [x] 安全复查：默认 base URL 是公开网关地址，仍需部署时通过环境变量管理和供应商 SLA 监控。
- [x] 契约复查：共享契约已写入 `training_plan_review` 字段、维度、前端展示边界、计划代理负荷真实性和外部证据来源类型。
- [x] 前端提醒：前端 owner 必须读取共享契约，新增或预留计划评审入口，普通层只展示摘要/风险/下一步动作，专家层展示 raw 维度。
- [x] 前端提醒：不得把 `training_plan_review.dimensions` 原始 JSON 直接丢给普通用户。
- [x] 前端提醒：不得把 `training_load.not_device_metric` 隐藏掉后却把负荷包装成设备恢复或真实生理指标。
- [x] 前端提醒：当 `rag_vs_base_model.status=llm_general_knowledge_only` 或 `needs_evidence_count>0` 时，普通层不能显示“权威处方已验证”。
- [x] 后端风险：`training_plan_review` 当前是确定性启发式评审，不能被宣传成医学审核或真实效果评估。
- [x] 后端风险：rehab/strength/mobility 维度目前主要依赖关键词，后续必须接入动作库和分层知识库标签。
- [x] 后端风险：RAG vs 裸模型当前证明的是证据可追溯和核心字段边界，不证明训练效果或比赛成绩提升。
- [x] 后端风险：OpenAI-compatible 默认网关可能 504；测试应只锁定配置默认值，不依赖真实网络。
- [x] 后端风险：本机 `.env` 可能覆盖默认值；测试已用 `PYTHON_DOTENV_DISABLED=1` 和 `delenv` 避免误判。
- [x] 测试复查：计划评审新增单元测试覆盖 10 个维度和 strength/mobility gap。
- [x] 测试复查：API skeleton path 测试断言 `training_plan_review` 出现在 `/query` 响应。
- [x] 测试复查：OpenAPI 测试断言 `QueryResponse`、`PlanDetailResponse`、`TrainingCalendarResponse` 均暴露 `training_plan_review`。
- [x] 测试复查：OpenAI 默认 provider 测试通过，不需要真实 key。
- [x] 目标验证记录：`tests/test_training_plan_review.py tests/test_api_app.py::test_plan_query_skeleton_mode_returns_without_integrated_app tests/test_llm_provider_contract.py::test_openai_defaults_use_configured_commercial_gateway tests/test_openapi_contract.py::test_openapi_response_schemas_match_shared_delivery_contract -q` 通过。
- [x] P0 review：更宽矩阵已通过：`tests/test_api_app.py tests/test_llm_provider_contract.py tests/test_openapi_contract.py tests/test_profile_field_gating.py tests/test_training_plan_review.py -q`，结果 50 passed，2 个第三方 warning。
- [x] 全量验证：`python -m pytest -q` 通过，结果 414 passed，3 个第三方 warning。
- [x] 前端构建：`npm run build` in `apps/web` 通过，确认当前前端工程仍可构建。
- [x] 空白验证：`git diff --check` 通过。
- [x] 仓库卫生：`python tools/dev/check_repo.py --scope hygiene` 通过；仍有已知 warnings，包括 `papers/`、OCR markdown、`todolist.md`、`data/vector_kb/default/*.json`、`artifacts/frontend-audit/` dirty 排除路径和历史大文件提示。
- [ ] P1 review：需要检查 `training_plan_review` 是否增加响应体体积过大，必要时前端默认只用摘要。
- [ ] P1 review：需要前端契约测试覆盖字段存在和普通/专家层分离。
- [ ] P1 review：需要浏览器确认计划评审入口不会挤占日历主路径。
- [ ] P2 review：需要把计划评审纳入 docs/api/openapi_contract.md 或等价 API 文档。
- [ ] P2 review：需要把分层知识库路线转为数据模型和 ingestion TODO，而不是只写产品愿景。
- [ ] P2 review：需要建立 RAG vs 裸模型 benchmark：同一画像下裸 GPT、RAG GPT、规则骨架三类计划由专家维度评分。
- [ ] P2 review：需要真实训练负荷数据接入前的免责声明 UI 截图验收。
- [ ] P2 review：需要医疗红旗路径联动计划评审，确保 red flag 不被 review 总结弱化为普通 gap。
- [ ] P2 review：最终退出前仍需 Frontend owner、Backend owner、QA/reviewer、agent workflow reviewer 在共享契约中明确签收无可修问题。

## Round 5 Frontend Owner Review Overlay - 审美迁移、降噪与退出门槛

- [x] 当前执行角色：Frontend owner。
- [x] 角色边界：只签收前端 UI/交互/浏览器状态/前端契约测试，不替 Backend owner 或 QA/reviewer 宣称 release hardening 完成。
- [x] 本轮已读 `docs/quality/shared_delivery_contract.md`。
- [x] 本轮已读 `docs/quality/release_hardening_loop.md`。
- [x] 本轮遵守最多两个 agent：Dalton 和 Hume 已返回，均为只读，均已关闭。
- [x] Dalton 任务：高端商用 app/网页审美证据采集，输出官方来源和迁移边界。
- [x] Hume 任务：商业 UX 信息架构/简洁度迁移，只读指出普通用户噪音与专家面板边界。
- [x] 子智能体计数记录：2/2，本轮继续前必须不再新增第三个 agent。
- [x] 外部证据来源记录：Linear、Stripe、Notion、Apple、WHOOP、Oura、Runna、TrainingPeaks、Strava/Garmin 官方或应用商店页面。
- [x] 已纳入审美原则：默认只显示今天/本周做什么，把证据、协议、trace、负荷解释放入详情层。
- [x] 已纳入审美原则：日卡只保留训练类型、时长/距离、强度、执行/风险状态。
- [x] 已纳入审美原则：颜色只表达状态，不让品牌色、风险色、警告色同时抢主层级。
- [x] 已纳入审美原则：任何负荷/恢复/准备度都必须带来源，不伪装设备数据。
- [x] 已修复：导航健康状态默认不再显示“服务在线”，避免普通用户被运维状态打扰。
- [x] 已修复：生成状态 pill 不再显示 92%/94% 这类内部等待百分比。
- [x] 已修复：7 步 pipeline DOM 保留为专家层，普通模式不展示流水线。
- [x] 已修复：日历统计 strip 默认专家层，普通用户不先看到总天数/周数/休息日/关键课计数。
- [x] 已修复：负荷曲线默认专家层，普通用户不先看到 7 日/42 日曲线。
- [x] 已修复：日卡 7 日/42 日占比、负荷 meter、tooltip 默认专家层。
- [x] 已修复：日卡产品状态从多字段来源矩阵降为“状态 + 执行提示”，来源细节专家层。
- [x] 已修复：反馈结果把风险门和协议复核改为“安全判断”和“是否继续”。
- [x] 已修复：反馈结果中的生成状态和计划差异计数默认专家层。
- [x] 已修复：状态面板空态不占位。
- [x] 已修复：调整历史空态不占位，有反馈后再出现。
- [x] 已修复：WeekNavigator / WeekExplanationSummary / PhaseOverviewBar / Training Load Curve 等可见内部英文术语改为中文产品文案。
- [x] 待验证：普通模式浏览器截图必须证明上述专家层字段不可见。证据：`artifacts/frontend-audit/round5-desktop-idle-2026-05-22.png`、`round5-normal-mode-state-2026-05-22.json`。
- [x] 待验证：移动端截图必须证明底部快捷导航和侧栏入口不竞争。证据：`artifacts/frontend-audit/round5-mobile-idle-2026-05-22.png`、workspace smoke。
- [ ] 待验证：红旗 feedback 勾选后普通 regenerate 不出现。
- [ ] 待验证：正常 feedback 缺 plan_id/event_id 时给“先保存这份日历”，不让后端 raw 错误暴露。
- [ ] 待验证：保存计划后从 `/plans/{plan_id}` 恢复 latest_feedback 与 workflow_trace，不丢审计恢复。
- [x] 待验证：普通模式不可见 `feedback_id`、`risk_gate`、`protocol_recheck`、`workflow_trace` 原始字段名。证据：`round5-normal-mode-state-2026-05-22.json` 中 `rawLabelsVisible=[]`。
- [ ] 待验证：专家面板仍可追溯 request id、trace_version、evidence_state、protocol_state、risk_state、repair_state。
- [ ] 待验证：无本地证据时 EvidenceDrawer 不伪造 source path/page/citation id。
- [ ] 待验证：负荷文案只能写“计划代理负荷/估算训练压力”，不能写设备级恢复或真实生理负荷。
- [ ] 待验证：日卡首屏 3 秒内能读出练什么、多久、强度、能不能做。
- [ ] 待验证：详情 modal 默认停在训练安排 tab，审计细节不抢首屏。
- [ ] 待验证：反馈 tab 能快速到达，训练后操作不被长解释淹没。
- [ ] 待验证：医疗红旗卡只展示停止训练、触发信号、专业评估、禁止继续，不展示调整版计划。
- [ ] 待验证：状态面板 medical_referral 后不继续显示 normal/generated 总结。
- [x] 待验证：日历周导航中文 aria label 和可见文案符合无内部术语要求。
- [x] 待验证：前端契约测试仍覆盖 shared DOM marker，不因降噪把主路径测丢。
- [x] 待验证：`npm run build` 必须通过。记录：2026-05-22 passed。
- [x] 待验证：`tests/test_astro_frontend_contract.py -q` 必须通过。记录：随目标矩阵通过。
- [x] 待验证：共享目标矩阵 `tests/test_api_app.py tests/test_state_models.py tests/test_astro_frontend_contract.py -q` 必须通过。记录：95 passed，2 个第三方 deprecation warning。
- [x] 待验证：隔离 preview + workspace smoke 必须跑，不能只看 4321 上的旧服务。记录：`WORKSPACE_URL=http://127.0.0.1:4322/#workspace npm run smoke:workspace` passed。
- [x] 待验证：`git diff --check` 必须通过。记录：passed。
- [ ] 仍不允许结束：Backend owner 未明确签收无可修问题。
- [ ] 仍不允许结束：QA/reviewer 未明确签收无可修问题。
- [ ] 仍不允许结束：共享契约未写明所有 owner 均无可修问题。
- [ ] 仍不允许结束：还有移动端、红旗路径、专家面板统一入口待浏览器验证。

## Round 6 Frontend Owner Review Overlay - 跨行业高端商用审美迁移

- [x] 当前执行角色：Frontend owner。
- [x] 本轮新增用户要求：前端 owner 负责调 agent 研究高端商用 app 审美并迁移学习，不局限马拉松。
- [x] 本轮已复读 `docs/quality/shared_delivery_contract.md`。
- [x] 本轮已复读 `docs/quality/release_hardening_loop.md`。
- [x] 本轮最多两个 agent：Hilbert 与 Herschel；均为只读外部证据/审美迁移研究，不改文件。
- [x] Hilbert 已返回并关闭：生产力/金融/设计/系统级高端 app 证据与迁移边界。
- [x] Herschel 已返回并关闭：健康/训练/可穿戴/习惯类 app 证据与迁移边界。
- [x] 已补契约：共享契约现在要求前端 owner 每轮进行跨行业高端商用审美迁移学习，并记录产品/来源、可观察事实、可迁移范式、不可迁移边界。
- [x] 已补手册：hardening 循环现在把跨行业审美证据四列法加入每轮步骤。
- [x] 已补前端 TODO：Round 6 overlay 记录两个只读 agent、证据规则、迁移边界和后续验证项。
- [x] 已补报告：agent 返回的证据表已写入 `docs/product/reports/frontend_product_audit_2026-05-22.md`。
- [x] 已补前端实现：训练日历新增普通层行动摘要面板，优先显示下一次训练、本周重点、安全提醒和反馈入口。
- [ ] 待补浏览器验证：计划可用态的行动摘要面板、日卡详情、反馈普通路径、医疗红旗阻断、移动端密度和专家入口。
- [ ] 待验证：跨行业迁移建议不能引入任何品牌资产、设备真实指标语义或无数据支撑的恢复/准备度评分。
- [ ] 待验证：普通用户主路径仍只看结果、下一步动作、安全信号和训练安排。
- [x] 已解除：两个只读 agent 已返回并关闭。
- [x] 已解除：高端商用审美证据已汇总到报告。
- [ ] 仍不允许结束：Backend owner、QA/reviewer、agent workflow reviewer 尚未共同签收“没有值得继续修的问题”。

## Round 7 Frontend Owner Review Overlay - 状态面板商用品质收敛

- [x] 当前执行角色：Frontend owner。
- [x] 本轮已复读 `docs/quality/shared_delivery_contract.md`。
- [x] 本轮已复读 `docs/quality/release_hardening_loop.md`。
- [x] 本轮 `git status --short` 已检查；dirty worktree 很重，前端 owner 只处理前端 UI/契约测试/文档记录，不回滚后端或数据文件。
- [x] 本轮最多两个 agent：`Nash` 负责高端商用审美迁移只读 review，`Cicero` 负责后端/API 交付面只读 review。
- [x] 两个只读 agent 均已返回并关闭；当前无挂起子智能体。
- [x] Nash 证据来源覆盖 Oura、WHOOP、Garmin、TrainingPeaks、Nike Run Club、Apple Health、Strava、Linear、Stripe。
- [x] Nash 迁移结论：普通层只显示今日/下一步/风险/计划，审计和内部指标下钻到专家层。
- [x] Nash 不可迁移边界：不迁移 HRV、恢复分、准备度分、品牌视觉资产、支付风控术语或无设备数据支撑的生理判断。
- [x] Cicero 确认：本次抽查没有发现阻塞前端主路径的新增 T0。
- [x] Cicero 确认：完整 authN/authZ、租户隔离、对象级授权、quota、分布式 rate limit、abuse dashboard 仍属于后端 owner 未签收商用安全项。
- [x] Cicero 确认：`/feedback` 缺少 `plan_id/event_id` 时后端仍是“计算但不保存”的软契约；前端必须继续阻止普通提交并显示保存边界。
- [x] 浏览器实测发现：普通层状态面板显示英文枚举 `attention`，属于用户不关心的内部状态词。
- [x] 已修复：`statusLabel()` 增加 `attention -> 需要关注`、`unknown -> 待反馈确认`、`deescalate -> 建议降级`。
- [x] 浏览器实测发现：新生成计划还未开始执行时，状态面板把未来训练全部算为“漏反馈”，显示 `补录 16 天反馈` 和“先补录遗漏反馈”。
- [x] 已修复：新增 `hasFeedbackRecord()`，统一判断单日是否已有反馈闭环。
- [x] 已修复：新增 `isFeedbackDue()`，只有已到期日期或显式完成/未完成状态且无反馈的训练日才计入 `missed_feedback_count`。
- [x] 已修复：无日期的未来训练骨架不再被当作漏反馈。
- [x] 已修复：当天训练不提前算漏反馈；只有早于今天的训练日期才默认要求补反馈。
- [x] 已补契约测试：`tests/test_astro_frontend_contract.py` 覆盖 `hasFeedbackRecord`、`isFeedbackDue`、未来日不误算漏反馈和状态枚举中文化。
- [x] 已验证：重新构建后浏览器刷新，状态面板不再显示英文 `attention`。证据：`round7-status-panel-desktop-state-2026-05-22.json`、`round7-status-panel-mobile-state-2026-05-22.json` 中 `hasAttentionEnglish=false`。
- [x] 已验证：重新构建后浏览器刷新，新生成未来计划不再显示 `补录 16 天反馈`。证据：同上 `hasFutureMissedPrompt=false`。
- [x] 已验证：桌面截图已保存到 `artifacts/frontend-audit/round7-status-panel-desktop-2026-05-22.png`。
- [x] 已验证：移动截图已保存到 `artifacts/frontend-audit/round7-status-panel-mobile-2026-05-22.png`，并补充状态面板细节截图 `round7-status-panel-mobile-detail-2026-05-22.png`。
- [x] 已验证：普通模式仍不显示 `workflow_trace`、`risk_gate`、`protocol_recheck`、`generation_status`、`trace_version`、`feedback_id`、`FastAPI`、`fail-closed`。证据：桌面/移动 state JSON 中 `rawTerms=[]`。
- [x] 已验证：移动端状态面板不再三列挤压，375px 下 `statusGridColumns=289px`，截图可读。
- [x] 已验证：`npm run build` 通过。
- [x] 已验证：`tests/test_astro_frontend_contract.py tests/test_api_app.py tests/test_state_models.py -q` 通过，101 passed，2 warnings。
- [x] 已验证：隔离 preview `WORKSPACE_URL=http://127.0.0.1:4324/#workspace npm run smoke:workspace` 通过。
- [x] 已验证：`git diff --check` 通过。
- [ ] 仍不允许结束：后端完整商用安全未签收。
- [ ] 仍不允许结束：QA/reviewer 未独立签收 dirty worktree、版本边界和“没有值得修的问题”。
- [ ] 仍不允许结束：`app.js` 仍是超大真实逻辑文件，marker 模块不能宣称真实模块化完成。

## Round 5 Backend Coordinator Review Overlay - 子审计修复记录

- [x] 当前执行角色：Backend / Engineering Coordinator。
- [x] 本轮已读 `docs/quality/shared_delivery_contract.md`。
- [x] 本轮最多两个子智能体：Copernicus 负责前端契约只读审计，Erdos 负责后端/安全/版本只读审计。
- [x] 子智能体计数记录：2/2，本轮继续前不得再新增第三个 agent。
- [x] Erdos T1：旧版 `schema_migrations` 无 `checksum` 列会导致启动失败。修复并补测试。
- [x] Erdos T1：未知路由 metrics label 可能泄漏 path segment。修复为 `/__unmatched__` 并补测试。
- [x] Erdos T2：版本边界只靠人工规则。`check_repo.py` 已增加 staged excluded path hard fail。
- [x] Erdos T2：未接入 TRIMP 负荷字段仍叫 `physiology_proxy`。已改为 `estimated` 边界并补测试。
- [x] Erdos T3：旧库 `sync_status` 补列缺直接测试。已补测试。
- [x] Copernicus T1：普通模式暴露 `fail-closed` 技术词。已改为用户可读文案并补契约测试。
- [x] Copernicus T1：调整历史可能展示 `feedback_id`。已移除可见 fallback 并补契约测试。
- [x] Copernicus T2：移动 drawer / day modal 层级与状态存在风险。已做最小兼容修复并补字符串契约。
- [x] 目标矩阵验证：172 passed，2 warnings。
- [x] 完整验证：`python -m pytest -q` 392 passed，3 warnings；`npm run build` passed；隔离 preview smoke passed；`git diff --check` passed；`check_repo.py --scope hygiene` passed with expected warnings。
- [ ] 不允许结束：前端 owner 仍需对浏览器截图/普通模式/红旗路径/专家面板签收。
- [ ] 不允许结束：QA/reviewer 仍需独立确认无新的 T0/T1/T2。
- [ ] 不允许结束：authN/authZ、租户隔离、rate limit、abuse guard 仍是商用发布前的 P0 路线项。

## Round 6 Review Overlay - Rate Limit 与商用安全边界

- [x] Backend owner 已落地第一层 resource abuse guard：敏感/写入/高成本 API 的 in-memory rate limit。
- [x] Backend owner 已落地部署可开启的 API token guard：`MARATHON_API_TOKEN` 配置后保护非公开 API，避免裸露计划、画像、反馈和 metrics。
- [x] 验证：`tests/test_security_guards.py::test_api_rate_limit_blocks_repeated_sensitive_requests -q` passed；安全/API/观测目标矩阵 51 passed；完整 pytest 395 passed，3 warnings。
- [x] 验证：`tests/test_security_guards.py::test_api_token_protects_non_public_endpoints_when_configured -q` passed。
- [x] 对象级授权补洞：`DELETE /plans/{plan_id}` 现在先读取 plan 并确认 `plan.user_id == user_id`，否则 404，不再允许 default_user 删除未来/旧库中的其他 user plan。
- [x] 验证：`tests/test_api_app.py::test_delete_plan_refuses_plan_owned_by_another_user tests/test_api_app.py::test_delete_plan_removes_plan_and_events -q` passed。
- [x] GPT provider 补齐：`ai_invoke` 支持 `openai/gpt`，`/llm-options` 暴露 `openai` provider，测试使用 fake HTTP client 不依赖真实 key。
- [x] 验证：`tests/test_llm_provider_contract.py -q` 2 passed；`tests/test_api_app.py::test_llm_options_support_frontend_model_controls -q` passed。
- [x] 验证：provider/API/前端/安全矩阵 107 passed，2 warnings；完整 pytest 398 passed，3 warnings。
- [x] 限流实现未使用用户 query 原文、plan_id、event_id、API key 或 Authorization header 作为 bucket key。
- [x] 超限响应是 429 + `Retry-After`，不伪装成生成失败或训练建议失败。
- [ ] Reviewer 待复核：middleware 顺序、异常路径 metrics、rate limit 与 TestClient/前端重试是否有冲突。
- [ ] 仍不允许结束：API token + rate limit 不是完整商用安全；authN/authZ、租户隔离、对象级授权、quota、分布式限流仍未完成。

## Round 7 Review Overlay - Security / Provider / Frontend Contract Follow-up

- [x] 当前执行角色：Backend / Engineering Coordinator。
- [x] 历史记录：本轮按旧规则收拢 2 个 reviewer：Backend/Security reviewer 与 Frontend/API contract reviewer；新规则生效后，后续每轮最多 1 个。
- [x] 用户新增约束：以后最多开 1 个子智能体；无用或已完成子智能体必须关闭。
- [x] 已关闭遗留 reviewer：`019e4c66-7b31-7131-9b9e-ad8b7ab596f8`、`019e4c66-cc9b-72d3-a1cd-9b8d21ba76fb`。
- [x] 已同步共享契约与 release hardening 手册：后续每轮最多 1 个 subagent，完成后必须 `close_agent`。
- [x] Backend/Security reviewer 结论：仍有值得修问题，集中在 XFF 限流绕过、非法 feedback plan/event、provider 测试 skip、`/llm-options` 配置泄漏。
- [x] Frontend/API reviewer 结论：仍有值得修问题，集中在 token guard 前端不可用、OpenAI key 状态未处理、负荷文案不一致、OpenAI 快捷按钮缺失。
- [x] T1 已修：rate limit 默认不信任 `X-Forwarded-For`，可信代理头需要显式 `MARATHON_TRUST_PROXY_HEADERS=1`。
- [x] T1 已修：rate limit bucket 清理与上限，防止高基数 key 长期占用内存。
- [x] T1 已修：前端在专家设置支持后端访问令牌，并通过 `X-Marathon-API-Key` 注入请求。
- [x] T2 已修：`/feedback` 提供非法 plan/event 时 404，未提供 plan/event 时继续只计算建议。
- [x] T2 已修：OpenAI provider 测试去掉 async plugin 依赖，无 skip。
- [x] T2 已修：OpenAI/DeepSeek provider 错误结构化分类并进入 `llm_provider_error_counts`。
- [x] T2 已修：`/llm-options` token guard 开启时隐藏 provider key 配置状态，认证后才显示。
- [x] T2 已修：前端读取 `api_key_configured`，OpenAI 未配置时生成前阻断。
- [x] T2 已修：所有已发现普通负荷入口改为“计划代理负荷/代理周负荷”口径。
- [x] T3 已修：专家 provider 快捷按钮加入 OpenAI。
- [x] 目标验证：94 passed，覆盖安全、反馈、LLM provider、观测、OpenAPI、前端契约；新增 smoke 契约测试单独通过。
- [x] 验证：完整 `python -m pytest -q` 405 passed。
- [x] 验证：`npm run build` passed。
- [x] 验证：隔离 preview workspace smoke passed，URL `http://127.0.0.1:4325/#workspace`；preview listener 已停止。
- [x] 验证：`git diff --check` passed。
- [x] 验证：`python tools/dev/check_repo.py --scope hygiene` passed，只有既有 root/dirty excluded/legacy path/large file warnings。
- [ ] 待验证：token guard on/off 浏览器或 smoke matrix。
- [ ] 待验证：OpenAI configured/unconfigured 浏览器或 smoke matrix。
- [ ] 待验证：401 失败态不暴露 raw token/API 字段。
- [ ] 待验证：Front-end owner 需截图签收普通模式负荷文案、日卡 modal、反馈红旗路径。
- [ ] 仍不允许结束：共享契约仍有前端 owner、QA/reviewer、agent workflow reviewer 未签收项。
- [ ] 仍不允许结束：完整商用 authN/authZ、租户隔离、quota、分布式限流、abuse dashboard 未完成。

## Round 8 Review Overlay - Error Detail Redaction

- [x] 当前执行角色：Backend / Engineering Coordinator。
- [x] 子智能体计数：0/1，未开启新 agent。
- [x] 审计范围：后端用户可见异常 detail、计划 fallback message、provider 原始错误体泄漏风险。
- [x] 已修复：`/query` plan fallback 不再回显 `str(e)`。
- [x] 已修复：`/training-calendar` 500 不再回显 `str(e)`。
- [x] 已修复：plan executor fallback reason 不再回显原始异常。
- [x] 已验证：11 passed，覆盖 plan fallback、provider 错误、training-calendar 错误边界、provider contract 和 observability。
- [ ] 待验证：完整回归矩阵需在本轮末尾重跑。
- [ ] 仍不允许结束：共享契约仍有前端浏览器签收、QA/reviewer 签收和商用 auth/tenant/quota 路线项。

## Round 4+ 覆盖说明

- [ ] 本文件当前是 Round 4 review todo；原 Round 3 通用阶段作为 500 行以上容量模板保留在后文。
- [x] 当前主角色：Backend / Engineering Coordinator。
- [x] 本轮子智能体计数：2/2，已开启只读 reviewer/explorer `019e4c3d-87b7-75b3-bf1b-6efcf3de91b7`、`019e4c3d-ce53-7b73-b274-7b59e7d9ff88`。
- [x] 本轮 reviewer 发现已纳入：最终 release gate 未闭合、migration checksum 不校验、商用 auth/tenant/rate-limit 缺失、observability 高基数路径、OpenAPI required 字段测试不足、旧 schema_migrations 兼容、未知路由 metrics label、普通模式 debug 词、feedback_id 可见风险、drawer/modal 层级。
- [ ] 本轮必须等共享契约前端/后端/QA/reviewer 共同签收，不能因为本轮修复和测试通过就结束。
- [x] 已提醒并固化：前端 owner 需继续维护反馈状态同步、训练负荷真实性、key 不持久化、普通模式不展示调试字段；后续最多 1 个子智能体且完成后关闭。

## Round 4 Review Gate：必须重新验收

- [x] Requirements gate：`round4_requirements_todo.md` 已记录用户任务、竞品证据、差异化机会、知识库厚度、GPT/DS API 和负荷真实性。
- [x] Backend gate：migration checksum mismatch 有测试且 fail-fast。
- [x] Backend gate：observability route key 不包含动态 UUID。
- [x] Backend gate：OpenAPI public response schema required 字段与共享契约一致。
- [x] Backend gate：训练负荷字段明确为 proxy/estimated，不伪装成设备真实负荷。
- [x] Frontend gate：反馈提交后状态面板、调整历史、当前日卡和历史回显都能读到最新反馈；已补契约测试。
- [ ] Frontend gate：前端 owner 已读共享契约并确认没有冲突。
- [ ] Security gate：DeepSeek/GPT key 不进入 localStorage/sessionStorage；需要前端 owner 最终复核。
- [x] Version gate：dirty worktree 中数据缓存、论文、OCR、用户画像不进入版本单元；`check_repo.py` 已对 staged excluded path hard fail，当前未 stage。
- [x] Agent workflow gate：本轮最多两个子智能体，角色清楚，子智能体结果已纳入 review。

## Round 4 验证记录

- [x] `C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -m pytest -q`：387 passed，3 个第三方 deprecation warning。
- [x] 目标矩阵 `tests/test_database_migrations.py tests/test_observability_contract.py tests/test_openapi_contract.py tests/test_daily_schedule_generator.py tests/test_astro_frontend_contract.py -q`：110 passed，2 个第三方 warning。
- [x] `npm run build` in `apps/web`：passed。
- [x] 隔离 preview smoke：`WORKSPACE_URL=http://127.0.0.1:4322/#workspace npm run smoke:workspace`：passed。
- [x] `git diff --check`：passed。
- [x] `tools/dev/check_repo.py --scope hygiene`：passed with historical WARNs only。
- [x] `git status --short --branch`：dirty worktree 仍然很重，未 stage、未 commit、未 push。

## Round 4 本轮实际修复摘要

- [x] 修复反馈提交后只更新 `state.selectedDay` 的状态漂移，改为同步 `state.lastResponse` 内 calendar/cards/week plans/history。
- [x] 修复 SQLite 已应用 migration checksum 不校验的问题。
- [x] 修复 observability 原始动态 path 进入指标 key 的问题。
- [x] 强化 OpenAPI public response schema required 字段测试。
- [x] 把训练负荷字段明确标为 `planned_zone_duration_proxy` 与 `planned_load_proxy`。
- [x] 修复英文 adaptive feedback query 未命中 skeleton plan path 的问题。
- [x] 修复移动端 drawer 关闭态不可点击导致 smoke 失败的问题。
- [x] 恢复 drawer 只显示一个 active section，且画像/日历/依据都进入 drawer。
- [x] 固化共享契约中的无限轮次、角色边界、需求证据、知识库厚度和前端协作规则。
- [x] 创建/更新 Round 4 requirements/backend/review TODO。

## Round 4 仍不允许宣称完成的事项

- [ ] 不允许宣称 app 已商用发布；当前仍是 release hardening。
- [ ] 不允许宣称真实前端模块化完成；`app.js` 仍是主逻辑。
- [ ] 不允许宣称后端路由完全拆分；`api_app.py` 仍是聚合层。
- [ ] 不允许宣称多租户商用安全完成；当前仍是本地单用户。
- [ ] 不允许宣称知识库厚度完成；分层 KB 仍是后续路线。
- [ ] 不允许宣称 GPT/DS API 已完成商用接入；当前只是路线和边界固化。
- [ ] 不允许宣称训练负荷是真实生理负荷；当前仅为计划代理负荷。
- [ ] 不允许使用未经证据支持的竞品结论。
- [ ] 不允许把测试绿等同于共享契约共同签收。
- [ ] 不允许 broad stage、commit 或 push。

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

- [x] Skill 1：codex-engineering-workflow，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 2：codex-todo-automation，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 3：architecture-quality-workflow，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 4：improve-codebase-architecture，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 5：api-designer，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 6：senior-backend，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 7：database-architect，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 8：frontend-designer，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 9：security-scanner，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 10：observability-advisor，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 11：project-flow-guardrails，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 12：git-workflow-guardrails，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 13：karpathy-guidelines，用于 review todo 中的对应审计或 review 视角。

## 轮次叙述

第 3 轮 Review 聚焦交付不夸大、不混入无关 dirty 文件、不遗漏失败命令和 residual risk。

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
