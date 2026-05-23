# 前后端共享交付契约

> 目的：给后端、前端、QA/reviewer 和版本管理 agent 一个共同交付文件。任何 agent 修改计划生成、反馈闭环、证据展示、状态面板、API 契约、数据库迁移或观测逻辑时，都必须先读本文件，并在交付前更新对应条目。

## -1. 无限轮次 Release Hardening 工作法

- 本项目进入可重复 release hardening 循环后，不以单个 agent 自称完成为结束条件。
- 每一轮开始时必须先读本文件、`git status --short --branch`、本轮 TODO 和上一轮 review 结论。
- 每一轮必须产出或更新三类 TODO：
  - `requirements_todo`：面向用户需求、竞品证据、领域标准、知识库厚度和商用化差距。
  - `backend_todo`：面向 API、DB、LLM provider、RAG/KB、训练负荷真实性、观测、安全和测试。
  - `review_todo`：面向验收矩阵、跨端契约、版本边界、agent 工作流和仍值得修的问题。
- 每一轮的需求 TODO 必须包含外部证据来源；只能使用官方文档、可复查公开资料、截图或明确标注为“待验证假设”的材料。
- 每一轮做成熟产品/审美/信息架构结论前，必须至少检索 10 个以上公开网页或 UI 设计来源，并在 TODO 或报告中只选 Top 3 作为本轮迁移对象；其余来源只作背景证据，不得无差别拼接进产品。
- 前端 owner 每轮必须把“高端商用审美迁移学习”作为固定审计面：证据可以来自跑步、健康、可穿戴、生产力、金融、设计工具、操作系统等成熟产品，不局限马拉松竞品。
- 高端商用审美迁移必须写清四件事：`产品/来源`、`可观察事实`、`可迁移范式`、`不可迁移边界`；只允许迁移信息架构、层级、密度、状态表达、可读性和交互节奏，不允许照抄品牌资产、商标、截图素材或伪装成设备/平台真实指标。
- 每一轮至少检查一次“竞品已经做了什么”和“竞品没做好但用户理应需要什么”，不能只按内部技术债推进。
- 每一轮后端 owner 必须提醒前端 owner 阅读本文件，并明确前端本轮需要维护的 DOM/API/状态契约。
- 每一轮最多开启 1 个子智能体；除非用户重新授权，不允许为了“显得并行”扩散 agent 数。
- 本轮开过的子智能体数量必须写入 review TODO；子智能体只做清晰边界内的只读审计或 disjoint 文件改动。
- 子智能体完成后必须及时 `close_agent`；不得保留无用 agent 挂起。若上一轮遗留了已完成 agent，下一轮开始前先关闭。
- 退出条件：后端 owner、前端 owner、QA/reviewer、agent 工作流 reviewer 都在本文件或对应 review TODO 中明确签收“没有值得继续修的问题”；否则继续下一轮。
- 如果自动化测试全绿但共享契约仍有未签收风险，不得宣称最终完成。

## -0. 容易遗忘但必须持续复查的事项

- 用户需求不是内部功能清单，而是跑者在计划生成、执行、反馈、恢复、风险和理解依据时要完成的真实任务。
- 竞品和高端商用 app 调研不能靠猜；必须来自官方文档、可复查公开用户反馈、截图或明确“待验证假设”。
- 跨行业审美对比要覆盖“成熟产品如何减少用户认知负担”，而不只是看颜色和卡片样式；任何建议必须能落回跑者任务：今天怎么练、本周重点、风险是否阻断、反馈后计划如何变化、依据在哪里。
- 阅读疲劳是前端商用化固定门槛：普通层必须先回答“今天怎么练 / 本周重点 / 是否安全 / 如何反馈”，长解释、证据、协议、trace、负荷比例、审计事件和计算中间量必须默认进入按需查看或专家层。
- 渐进披露不能隐藏关键风险：`medical_referral`、安全阻断、待复核日和必要反馈入口必须在普通层可见；被下沉的只能是解释、来源、审计和计算细节。
- 生成后主路径必须是训练执行，不是阅读报告；训练日历、下一次训练和行动摘要的视觉优先级应高于“为什么这样安排”的长解释面板。
- 竞品已证明的基础能力要补齐：计划/完成对比、结构化训练、日历浏览、恢复/睡眠/疲劳反馈、比赛日历与训练建议联动。
- 竞品未必做好的差异化机会要持续保留：证据可解释、反馈后真实改计划、计划 diff、为什么降级、无证据不伪造引用、医疗边界 fail-closed。
- 知识库厚度是商用化核心，不是附属文档；后续必须建设分层知识库：
  - 跑步训练协议层：半马、全马、10K、低跑量、回归训练、减量期。
  - 动作库/训练课层：主课、热身、冷身、强度区间、替代训练、禁忌条件。
  - 风险与运动医学边界层：疼痛、胸痛、头晕、中暑、过度疲劳、睡眠不足。
  - 竞品与用户任务层：竞品功能证据、用户痛点、用户可理解的交互语言。
  - 用户画像与反馈案例层：目标、比赛日期、跑量、可训练日、PB、疲劳/疼痛/睡眠、历史调整。
- 无本地证据时允许 `llm_general_knowledge` 做一般说明，但不能伪造 source path、页码、证据 ID，也不能进入核心训练处方字段。
- 后续 LLM 接入方向是 GPT/DeepSeek API；必须有 provider 抽象、服务端密钥边界、超时/重试/降级、token/cost 观测和前端不持久化 key。
- 当前后端 provider 已支持 `ollama`、`ds/deepseek`、`openai/gpt`；OpenAI 路径使用 Responses API，密钥来自服务端 `OPENAI_API_KEY` 或测试注入，不要求前端持久化 key。
- `/llm-options` 必须继续返回 `ollama`、`ds`、`openai` provider 列表、默认模型和 `api_key_configured` 状态，供前端做普通模式降噪和专家配置。
- 默认 GPT/OpenAI-compatible provider 版本为 `gpt-5.5`，默认 `OPENAI_BASE_URL` 为 `https://api.aisz.mom/v1`；密钥仍只允许来自服务端 `OPENAI_API_KEY` 或后端测试注入，任何 agent 不得把用户提供的密钥写入仓库、文档、前端持久化存储、测试快照或最终回复。
- 当 `MARATHON_API_TOKEN` 已配置时，未认证访问 `/llm-options` 只能看到 provider/model 列表，不得暴露 DeepSeek/OpenAI 上游 key 是否已配置；带有效 `Authorization: Bearer ...` 或 `X-Marathon-API-Key` 时才可返回真实 `api_key_configured`。
- 训练负荷必须做真实性把关：当前只允许标为 `planned_load_proxy` 或 `estimated`，不能暗示为 Garmin/COROS/TrainingPeaks 等设备真实生理负荷。
- 训练负荷字段必须保留计算来源、输入字段、缺失字段、置信度、`not_device_metric` 和 disclaimer。
- 前端如果展示负荷，只能展示“计划代理负荷/估算负荷”，不得包装成设备级恢复、HRV 或真实生理指标。
- `/query`、`/training-calendar`、`GET /plans/{plan_id}` 必须返回 `training_plan_review`，用于评审训练负荷、计划结构、周期训练、伤病恢复、康复训练、体能训练、拉伸放松、伤病预防、证据边界和 RAG 相对裸模型的权威性。当前后端只允许把负荷评审称为 `planned_load_proxy`，不得宣称为设备真实生理负荷。
- `training_plan_review.dimensions` 至少维护以下键：`training_load`、`plan_structure`、`periodization`、`injury_recovery`、`rehabilitation`、`strength_conditioning`、`mobility_recovery`、`injury_prevention`、`evidence_control`、`rag_vs_base_model`。
- 前端 owner 本轮需要新增或预留计划评审入口：普通层只展示“计划评审摘要 / 风险与缺口 / 下一步动作”，专家层再展示各维度状态、代理负荷缺失输入、证据覆盖和核心字段来源违规；不得把 raw `training_plan_review` JSON 直接暴露给普通用户。
- 计划评审对标外部依据时必须区分来源：ACSM FITT-VP 支撑处方结构，TrainingPeaks/Garmin/Runna/Oura/WHOOP 支撑竞品任务与状态表达，WHO 健康 AI 支撑透明、解释和责任边界，Mayo/CDC/NHS 或同等级来源支撑医疗红旗与伤后回归边界；没有证据的竞品判断只能写成待验证假设。
- API 商用化仍缺 authN/authZ、租户隔离、rate limit 和 abuse guard；未完成前只能标为本地单用户 release。
- 当前已具备单进程 in-memory rate limit：默认 `MARATHON_RATE_LIMIT_PER_MINUTE=600`，保护 `/query`、`/feedback`、`/training-calendar`、`/plans`、`/profile` 等高成本/写入路径；这只解决本地/预发布资源滥用，不等于完整商用 quota。
- rate limit 默认不得信任客户端自带 `X-Forwarded-For`；只有明确设置 `MARATHON_TRUST_PROXY_HEADERS=1` 且部署在可信反向代理之后，才可使用代理头作为客户端标识。bucket 必须清理过期项并有上限，避免伪造头制造高基数内存增长。
- 当前已具备部署可开启的 API token guard：设置 `MARATHON_API_TOKEN` 后，除 `/health`、引用表、OpenAPI/docs 和 `/llm-options` 外，其余 API 需要 `Authorization: Bearer ...` 或 `X-Marathon-API-Key`；这只解决单 token 保护，不等于用户账号或租户隔离。
- 前端专家设置已支持本页内存态后端访问令牌，并通过 `X-Marathon-API-Key` 注入请求；该令牌不得写入 `localStorage` 或 `sessionStorage`。前端 owner 仍需用浏览器验证 token guard on/off 两种路径。
- 完整商用安全仍需要 authN/authZ、租户隔离、对象级授权、账号/订阅级 quota、分布式 rate limit 和 abuse dashboard。
- 当前对象级保护已覆盖 `GET /plans/{plan_id}`、`PATCH /plans/{plan_id}/events/{event_id}` 和 `DELETE /plans/{plan_id}` 的 plan owner 检查；未来新增 plan/event/feedback endpoint 必须沿用先查 owner 再操作。
- `/feedback` 仅在未提供 `plan_id/event_id` 时走“只计算建议、不入库”的兼容路径；一旦客户端提供 plan/event，就必须先验证事件存在且属于当前 user，非法或不存在时返回 404/400，不得静默返回 `feedback_id=None` 伪装保存成功。
- 后端已新增 runner/expert 响应投影：当 `MARATHON_API_TOKEN` 或 `MARATHON_EXPERT_API_TOKEN` 已配置时，`/query`、`/feedback`、`/training-calendar`、`GET /plans/{plan_id}` 默认按 `runner` 裁掉 `workflow_trace`、`field_sources`、`protocol_check`、`action_match`、`kb_fallback`、`risk_gate`、`protocol_recheck`、`trace`、`content_json`、`raw_text` 等专家/审计字段。
- 前端普通层不得依赖上述专家字段；需要专家面板数据时，请求必须显式带 `X-Marathon-Response-Role: expert`，并提供服务端配置的 `X-Marathon-Expert-Key`。伪造或错误 expert key 返回 403，无效 role 返回 400。
- 本地未配置 API token 与 expert token 时，后端保留 expert 完整响应以兼容现有开发测试；部署或预发布环境必须配置 `MARATHON_API_TOKEN`，如需专家面板再配置 `MARATHON_EXPERT_API_TOKEN`。
- LLM provider 错误必须进入结构化分类：`missing_key`、`timeout`、`rate_limited`、`provider_5xx`、`invalid_request`、`network_error`、`invalid_response` 等；`/ops/metrics` 通过 `llm_provider_error_counts` 汇总 provider/error_code，不记录 prompt 原文、API key 或 Authorization header。
- 数据库 migration 已发布后不得修改旧 SQL；必须 checksum fail-fast，新增变更写新 migration。
- 旧版 `schema_migrations` 如果缺少 `checksum` 列，启动时必须补列并回填已知 migration checksum；已发布 migration 被改写仍必须 fail-fast。
- 未匹配 HTTP 路由不得把原始 path segment 写入 metrics label；统一收敛为 `/__unmatched__`，避免 secret-like 或用户原文进入 `/ops/metrics`。
- 共享契约是前后端共同退出条件，不是后端单方面完成报告。

## 0. 多 Agent 协作门禁

- 进入可重复 release hardening 循环前，必须先读取本文件；需要详细执行手册时，再读取 `docs/quality/release_hardening_loop.md`。
- 每个后端、前端、QA、review、版本管理 agent 开始工作前，必须先读取本文件。
- 每个 agent 交付前，必须复查本文件中自己负责的契约条目。
- 如果任一 agent 修改了跨端契约、DOM/data attribute、API response model、migration、状态枚举、验证命令或版本范围，必须同步更新本文件。
- 如果发现其他 agent 的改动与本文件冲突，不允许静默覆盖；应先在本文件中记录冲突点，再做最小兼容修复。
- 本文件不是一次性文档，而是当前版本单元的共享交付看板。
- 每个 agent 修改本文件时必须知道并写清自己的角色，不允许用“我们都负责”模糊边界。
- Backend / Engineering Coordinator 角色：负责 API、DB、LLM provider、RAG/KB、训练负荷真实性、observability、安全、验证矩阵、版本边界和 agent 工作流设计。具体哪位 agent 当前承担该角色，必须在本轮 TODO/review 中声明。
- Frontend owner 角色：负责 Astro 工作台、日历/日卡/EvidenceDrawer/反馈/状态面板 UI、浏览器状态同步、普通模式隐藏调试信息、跨行业高端商用审美迁移、前端 build 与 smoke。
- Frontend owner 在阅读疲劳轮次中必须维护 `data-reading-fatigue-guard`、`data-secondary-reading-layer`、`#calendarActionPanel`、周卡默认折叠策略、day modal 默认 plan tab 与 expert-only 审计边界；如果改动这些 DOM/CSS/交互契约，必须同步更新前端契约测试和本文件。
- QA/reviewer 角色：负责独立审计、失败态验证、跨端契约、测试矩阵、未签收风险和“是否还有值得修的问题”的判断。
- Version owner 角色：负责 dirty worktree 边界、禁止 broad stage、提交文件清单、密钥/缓存/数据文件排除和最终 git 建议。
- Requirements/PM 角色：负责用户任务、竞品证据、商用化差距、需求优先级和验收标准，不负责直接改实现。
- 文档修改格式建议：`角色 / 改动范围 / 新增约束 / 仍未签收项 / 验证命令`。
- 本线程当前主 Codex 角色：Backend / Engineering Coordinator。修改公共契约时代表 API、DB、LLM provider、RAG/KB、训练负荷真实性、observability、安全、验证矩阵、版本边界和 agent 工作流设计；不替 Frontend owner 或 QA/reviewer owner 签收完成。
- 前端 owner 每轮必须检查：
  - `apps/web/src/scripts/app.js` 是否仍为真实运行主逻辑。
  - marker 模块是否被误称为真实模块化完成。
  - 反馈提交后当前页状态、状态面板、调整历史和历史计划回显是否一致。
  - DeepSeek/GPT key 是否被 localStorage/sessionStorage 持久化。
  - 训练负荷是否显示为“计划代理负荷/估算”，而不是设备真实负荷。
  - 普通模式是否只展示结果、下一步动作、安全判断和训练安排；token/timing/request id/workflow_trace/protocol issue/load factors/7日与42日占比等调试或计算字段必须进入专家/审计层。
  - 离线或需要用户行动时才在普通导航暴露服务健康状态；服务正常在线不应占用用户注意力。
  - 反馈结果普通层必须翻译为“安全判断 / 是否继续 / 建议动作 / 影响范围”，不得直接展示 `risk_gate`、`protocol_recheck`、`generation_status` 等 raw 字段名。
  - 高端商用审美迁移必须每轮至少沉淀到 TODO 或报告中；来源可以包括 Linear/Stripe/Notion/Apple/WHOOP/Oura/Runna/TrainingPeaks/Strava/Garmin 等，也可以扩展到任何可复查的高端商用 app，但必须标明证据和不可迁移边界。
- 后端 owner 每轮必须向前端 owner 明确本轮变更涉及的 API 字段、DOM 依赖、失败态、证据态和验证命令。
- 所有 agent 修改本文件时必须先声明自己的 owner 角色；可以讨论公共契约，但不能替其他 owner 签收完成。
- Frontend owner 的权责边界：Astro 工作台、日历/日卡/证据/反馈 UI、普通用户信息架构、跨行业高端商用审美迁移、移动端可用性、前端 build、workspace smoke、DOM/data attribute 契约。仅在跨端契约阻塞前端时做最小后端兼容。
- Backend owner 的权责边界：API response model、DB/migration、LLM provider、RAG/KB、风险门、安全、观测和 pytest 门禁。后端改字段时必须通知前端依赖。
- QA/reviewer owner 的权责边界：验收矩阵、脏工作区边界、跨端一致性、外部证据是否可复查、是否仍有值得修问题。

## 1. 当前版本单元

- 版本单元名称：`training-calendar-engineering-hardening-2026-05-22`
- 负责人角色：
  - Backend owner：API 契约、反馈风险门、SQLite migration、observability、pytest 门禁。
  - Frontend owner：Astro 工作台、日历/日卡/证据/反馈 UI、前端 build 与 workspace smoke。
  - QA/reviewer owner：跨端契约、版本边界、dirty worktree 风险、最终验收矩阵。
- 当前分支：`codex/5/20`
- 当前仓库状态：dirty worktree 很重，禁止 `git add .`，禁止提交数据缓存、用户画像、构建产物和无关 agent 改动。

## 2. 共享入口不可破坏

- 后端 app 入口：`marathon_qa_assistant.apps.api_app:app`
- 前端主入口：`apps/web/src/pages/index.astro`
- Astro 页面路由：`/`
- 计划生成入口：`POST /query`
- 反馈入口：`POST /feedback`
- 训练日历入口：`POST /training-calendar`
- 历史计划入口：`GET /plans/{plan_id}`
- 观测入口：`GET /ops/metrics`
- 前端主按钮文案：`生成训练日历`
- 前端主流程 DOM：`#workspaceFlow`
- 前端主工作台卡片：`[data-primary-workspace-card]`

## 3. API 契约

### `POST /query`

后端必须返回：

- `report`
- `structured_training_plan`
- `monthly_training_calendar`
- `daily_schedule_cards`
- `training_plan_id`
- `generation_status`
- `generation_timings`
- `training_plan_review`
- `workflow_trace`

前端依赖：

- `structured_training_plan.week_plans`
- `monthly_training_calendar.days`
- `daily_schedule_cards`
- `generation_status`
- `training_plan_id`
- `training_plan_review.summary`
- `training_plan_review.dimensions`
- `workflow_trace`

禁止行为：

- 计划类请求只返回 Markdown。
- LLM timeout/error 后不返回 skeleton fallback。
- 空输入但已有画像时误判为普通 QA。

### `POST /training-calendar`

后端必须返回：

- `year`
- `month`
- `start_week_index`
- `end_week_index`
- `total_days`
- `days`
- `phases`
- `evidence_summary`
- `monthly_training_calendar`
- `daily_schedule_cards`
- `training_load_summary`
- `training_plan_review`

前端依赖：

- `days[]`
- `monthly_training_calendar.days`
- `daily_schedule_cards`
- `training_load_summary.source_type`
- `training_load_summary.not_device_metric`
- `training_plan_review.summary`
- `training_plan_review.dimensions`

禁止行为：

- 日历接口只返回月视图而不返回完整日卡。
- 负荷字段省略 `planned_load_proxy` / `not_device_metric` 真实性边界。
- 计划评审缺失时让前端伪造“权威评审”或“设备级负荷”。

### `POST /feedback`

后端必须返回：

- `workout_feedback`
- `risk_gate`
- `protocol_recheck`
- `adaptive_feedback`
- `adaptive_adjustment`
- `plan_diff`
- `generation_status`
- `feedback_id`
- `workflow_trace`

前端依赖：

- `generation_status` 区分 `generated`、`partial_generated`、`risk_refused`、`medical_referral`。
- `adaptive_adjustment.next_day_adjustment`
- `adaptive_adjustment.weekly_adjustment`
- `adaptive_adjustment.alternative_workout`
- `risk_gate.status`
- `risk_gate.triggers`
- `protocol_recheck.allowed`
- `feedback_id`

禁止行为：

- 医疗红旗继续生成高强度替代训练。
- 疼痛风险展示 threshold、interval、tempo、VO2 等高强度选项。
- 后端无有效 `plan_id/event_id` 时直接报错阻断用户。

### `GET /plans/{plan_id}`

后端必须返回：

- `plan`
- `structured_training_plan`
- `events`
- `execution_status_summary`
- `adjustment_history`
- `training_plan_review`
- `workflow_trace`

前端依赖：

- `events[].latest_feedback`
- `execution_status_summary.completion_rate`
- `execution_status_summary.risk_level`
- `adjustment_history[].adaptive_adjustment`
- `training_plan_review.summary`
- `training_plan_review.dimensions`

禁止行为：

- 历史计划丢失反馈审计链。
- `latest_feedback` 没有 `feedback_id` 兼容字段。

## 4. 数据库迁移契约

- SQLite 必须存在 `schema_migrations(version, applied_at, checksum)`。
- migration 文件位于 `apps/backend/src/marathon_qa_assistant/services/migrations/`。
- 当前 baseline：
  - `0001_initial.sql`
  - `0002_feedback_audit_fields.sql`
- 启动时必须兼容：
  - 空库初始化。
  - 旧库缺少 `training_event_feedback.risk_gate_json`。
  - 旧库缺少 `training_event_feedback.protocol_recheck_json`。
  - 旧库缺少 `training_calendar_events.sync_status`。
  - migration 重复执行。

禁止行为：

- 在没有迁移和测试的情况下直接改 `SCHEMA_SQL` 破坏旧库。
- 删除用户已有训练计划或反馈。
- 把 migration 写成破坏性 DDL。

## 5. 安全契约

- 默认 CORS 只允许：
  - `http://127.0.0.1:4321`
  - `http://localhost:4321`
- `MARATHON_ALLOWED_ORIGINS` 可显式配置来源。
- 只有 `MARATHON_DEV_PERMISSIVE_CORS=1` 才允许 `*`。
- `MARATHON_API_TOKEN` 开启后，前端必须在专家设置中填写本页内存态后端访问令牌，核心 `/query`、`/feedback`、`/plans` 请求通过 `X-Marathon-API-Key` 发送；令牌不得持久化。
- 未认证 `/llm-options` 不得公开 `api_key_configured=true`，避免泄漏部署 provider key 状态。
- DeepSeek API key 只能在当前浏览器会话内使用。
- 前端禁止 `localStorage.setItem("marathon_ds_api_key", ...)`。
- 页面启动时应清理旧 `marathon_ds_api_key`。
- metrics 和日志禁止记录：
  - `ds_api_key`
  - OAuth access token
  - refresh token
  - authorization header
  - 用户 query 原文作为高基数 label

## 6. 观测契约

- 每个 HTTP 响应必须回写 `X-Request-ID`。
- 请求没有传入 `X-Request-ID` 时后端生成。
- `/ops/metrics` 返回：
  - `requests_total`
  - `errors_total`
  - `generation_status_counts`
  - `feedback_risk_reason_counts`
  - `plan_generation_duration_buckets`
  - `medical_referral_total`
- `/query` skeleton-first 和完整工作流都应记录 `generation_status`。
- `/feedback` 应记录风险原因和 `medical_referral` 计数。
- LLM provider 失败应记录结构化错误分类 `llm_provider_error_counts`，但不得记录用户 prompt、密钥、Authorization header 或上游完整错误体。
- API 用户可见错误不得直接回显 `str(e)`、上游 provider 原始错误体、URL、密钥片段或内部堆栈类细节。计划 fallback message 只能显示稳定中文摘要；provider 类错误最多显示 `provider/error_code`。

## 7. 前端交付契约

前端真实入口：

- `apps/web/src/pages/index.astro`

当前拆分状态：

- `index.astro` 已从超大单文件缩到页面装配层。
- 运行脚本主要在 `apps/web/src/scripts/app.js`。
- CSS 由 `apps/web/src/styles/global.css` 聚合多个子样式文件。
- `apiClient.js`、`calendarRenderer.js`、`evidenceDrawer.js`、`feedbackModal.js`、`statusPanel.js` 当前是 ownership marker，不代表真实逻辑已完全搬迁。

前端 owner 必须维护：

- `#workspaceFlow`
- `[data-primary-workspace-card]`
- `[data-plan-generation-entry]`
- `[data-evidence-open]`
- `[data-modal-feedback-action]`
- `[data-calendar-view]`
- `day-card-essentials` smoke contract marker
- Evidence drawer 打开/关闭链路
- Day modal 反馈提交链路
- Status panel 与 adjustment history 展示

禁止行为：

- 把占位模块标为“彻底模块化已完成”。
- 删除 `app.js` 中真实逻辑但不接入新模块。
- 默认把专家设置、API、Token、FastAPI、Generation Trace 暴露给普通模式。
- 恢复浏览器持久化 DeepSeek key。

## 8. Evidence / LLM General Knowledge 契约

- 有本地证据时，日卡和抽屉应展示证据来源、证据层级和依据影响。
- 无本地证据时，允许展示 `llm_general_knowledge` 一般说明。
- `llm_general_knowledge` 不能写入核心训练处方字段。
- 无证据时不能伪造 source path、页码、引用编号或证据 ID。
- HMP 路径应能展示 `半马 HMP 基石协议` 或等价协议来源。

### Layered KB / GraphRAG 契约

- Backend / Engineering Coordinator 已确认下一轮路线 C：优先重构分层知识库、GraphRAG、动作库和证据内核；本轮不要求前端 UI 大改。
- 后端可以增量添加以下字段，且必须保持 API 向后兼容：`knowledge_layer`、`evidence_domain`、`source_registry_id`、`source_quality`、`retrieval_mode`、`prescription_permission`、`rag_eval`、`kb_metadata`。
- `knowledge_layer` 可取值：`source_registry`、`document_index`、`domain_graph`、`prescription_library`、`evaluation`、`domain_pack`。
- `evidence_domain` 可取值：`protocol`、`action_library`、`sports_science_reference`、`medical_safety`、`rehab_strength_mobility`、`nutrition_race_fueling`、`environment_race_context`、`competitor_product_reference`、`user_profile_case`、`llm_general_knowledge`。
- `retrieval_mode` 可取值：`vector`、`lexical`、`graph_local`、`graph_global`、`graph_drift`、`action_library`、`protocol_rule`、`none`。
- `prescription_permission` 可取值：`can_write_core`、`explanation_only`、`blocked_needs_evidence`。
- 只有 `prescription_permission=can_write_core` 的来源可以写入核心处方字段；`llm_general_knowledge`、普通 vector 命中和 graph-only 证据默认只能做解释或进入 `needs_evidence`。
- GraphRAG 用于跨文档关系、概念解释、证据发现和候选生成，不得绕过动作库或协议直接写入 `main_set`、`intensity`、`duration`、`progression`、`risk_downgrade`。
- Frontend owner 未来消费这些字段时，普通模式只显示用户可理解标签，例如“协议依据”“动作库”“知识库解释”“安全边界”“模型常识说明”；不得在普通层展示 raw `source_registry_id`、`prescription_permission`、`retrieval_mode`。
- 当 `prescription_permission` 不是 `can_write_core` 时，前端不得显示“权威处方已验证”或等价表述。
- `rag_eval` 只用于专家/审计层，普通用户层最多展示“证据覆盖完整 / 部分缺证据 / 需要补证据”。
- Backend / Engineering Coordinator 在 P0-P9 已落地后端最小证据内核：`services/kb/source_registry.py`、`evidence_binding.py`、`graph_evidence.py`、`evaluation.py`、`health.py`，以及日卡 `kb_metadata` 和 `training_plan_review.dimensions.layered_kb`。
- Backend / Engineering Coordinator 在知识库 P0-P12 hardening 中新增治理产物：`data/knowledge/governance/source_registry_v2.jsonl`、`coverage_matrix.json`、`domain_pack_seed_catalog.json`、`chunk_schema_v2_preview.jsonl`、`chunk_schema_v2_health.json`、`legacy_chunk_health.json`、`golden_questions_summary.json`、`kb_release_report.json`。这些产物用于审计与下一批 ingest；`chunk_schema_v2_preview.jsonl` 暂不替换 runtime FAISS 索引。
- `/evidence-tier-reference` 必须继续返回 `evidence_drawer_contract.display_modes = verified_source / model_general_knowledge / needs_evidence`，以及 `core_prescription_permissions.allowed_domains = protocol / action_library`，供前端 EvidenceDrawer 和普通/专家层边界复用。
- Frontend owner 下一轮如消费 `daily_schedule_cards[].kb_metadata` 或 `training_plan_review.dimensions.layered_kb`，普通层只能展示“协议依据 / 动作库 / 知识库解释 / 需补证据”等短标签；专家层才展示 `source_registry_id`、`retrieval_mode`、`prescription_permission`、`rag_eval`。
- QA/reviewer 下一轮必须验证：无 source path/page 时不伪造引用，`llm_general_knowledge` 不进入核心处方字段，graph-only 证据不显示为“已验证处方”。

## 9. 共同验收命令

后端与契约：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest -q
```

目标矩阵：

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
  tests/test_observability_contract.py `
  tests/test_llm_provider_contract.py `
  tests/test_training_plan_review.py `
  tests/test_kb_source_registry.py `
  tests/test_kb_evidence_binding.py `
  tests/test_kb_graph_evidence.py `
  tests/test_kb_evaluation.py `
  tests/test_kb_health.py -q
```

前端：

```powershell
cd apps/web
npm run build
```

如果 4321 有旧进程或异常服务，workspace smoke 必须使用隔离 preview：

```powershell
cd apps/web
npm run preview -- --host 127.0.0.1 --port 4322
$env:WORKSPACE_URL='http://127.0.0.1:4322/#workspace'
npm run smoke:workspace
```

仓库卫生：

```powershell
python tools/dev/check_repo.py --scope hygiene
git diff --check
git status --short --branch
```

## 10. 版本管理规则

- 不允许 `git add .`。
- 不允许把 `data/vector_kb/default/user_profile.json`、`knowledge_graph.json`、`apps/web/dist/`、`.pytest_cache/` 加入本版本单元。
- 本版本单元建议只包含：
  - `pytest.ini`
  - `apps/backend/src/marathon_qa_assistant/apps/api_app.py`
  - `apps/backend/src/marathon_qa_assistant/apps/schemas.py`
  - `apps/backend/src/marathon_qa_assistant/core/observability.py`
  - `apps/backend/src/marathon_qa_assistant/core/state_models.py`
  - `apps/backend/src/marathon_qa_assistant/nodes/common.py`
  - `apps/backend/src/marathon_qa_assistant/services/database.py`
  - `apps/backend/src/marathon_qa_assistant/services/kb/*.py`
  - `apps/backend/src/marathon_qa_assistant/services/migrations/*.sql`
  - `apps/backend/src/marathon_qa_assistant/services/training_plan_review.py`
  - `apps/web/src/pages/index.astro`
  - `apps/web/src/scripts/*.js`
  - `apps/web/src/styles/*.css`
  - `tests/test_security_guards.py`
  - `tests/test_database_migrations.py`
  - `tests/test_llm_provider_contract.py`
  - `tests/test_openapi_contract.py`
  - `tests/test_observability_contract.py`
  - `tests/test_training_plan_review.py`
  - `tests/test_astro_frontend_contract.py`
  - `tests/test_kb_*.py`
  - `docs/api/openapi_contract.md`
  - `docs/architecture/observability_baseline.md`
  - `docs/quality/*.md`
  - `docs/quality/rounds/*.md`
  - `docs/superpowers/plans/2026-05-22-layered-kb-graphrag-refactor-todo.md`
- 任何提交前必须重新跑共同验收命令。

## 11. 当前已知风险

- `apps/web/src/scripts/app.js` 仍然很大；这次只完成了从 Astro 抽出，不代表真实模块拆分完成。
- 多个 `apps/web/src/scripts/*` 文件目前只是 ownership marker，下一轮应真实迁移函数。
- `api_app.py` 仍是路由聚合层；已抽出 schema，但 routers 和 response builders 尚未完全拆分。
- 4321 端口可能存在旧 dev server；默认 `npm run smoke:workspace` 会被污染，最终验收应用隔离端口。
- 仓库已有大量其他 agent/user dirty 文件，本版本不能 broad stage。
- 当前 API 仍是本地单用户 release，商用 authN/authZ、租户隔离、rate limit、abuse guard 未完成前不能宣称多租户商用安全完成。
- 分层知识库厚度仍是后续路线；当前不能宣称训练协议、动作库、运动医学边界、负荷解释、竞品证据和用户案例层都已完备。
- GPT/DeepSeek API 商用接入仍是路线；当前不能宣称 provider 抽象、服务端 key、成本观测和资源限制全部完成。
- 训练负荷当前只能按 `planned_load_proxy` / estimated 展示；不能宣称为 Garmin/COROS/TrainingPeaks 等设备真实生理负荷。
- 前端普通层和专家层所有负荷入口都必须统一“计划代理负荷/估算负荷”口径；不得出现让用户误读为设备真实负荷的“计划负荷/周负荷”孤立标签。
- GPT/OpenAI provider 已有后端 Responses API 路径、服务端 key 边界、结构化错误分类和 mock 测试门禁；仍未完成成本估算、账号级 quota、重试策略和供应商 SLA 监控。
- `/query`、`/training-calendar` 和 plan executor fallback 已做错误摘要脱敏；后续新增端点不得使用 `detail=str(e)` 作为用户响应。

## 12. Review 签收清单

- [x] Backend owner 确认 API response model 与 OpenAPI 文档一致。验证：`tests/test_openapi_contract.py` 随完整 `python -m pytest -q` 通过，且 `FeedbackResponse`、`PlanDetailResponse`、`OpsMetricsResponse` required 字段已测试。
- [x] Backend owner 确认 migration 可空库、旧库、重复启动，并补充已应用 migration checksum mismatch fail-fast、旧 `schema_migrations.checksum` 补列回填、旧 `training_calendar_events.sync_status` 补列测试。验证：目标矩阵 172 passed；完整 `python -m pytest -q` 398 passed，3 个第三方 warning。
- [x] Backend owner 确认 lifespan startup 不再产生 FastAPI `on_event` deprecation warning。验证：完整 `python -m pytest -q` 通过，未出现 FastAPI on_event warning。
- [x] Frontend owner 确认 workspace smoke 在隔离 preview 通过。验证：`WORKSPACE_URL=http://127.0.0.1:4322/#workspace npm run smoke:workspace` 通过；本项仍需前端 owner 复核签字。
- [ ] Frontend owner 确认普通模式不暴露专家调试词；Backend coordinator 已补契约测试拦截 `FastAPI 后端`、`fail-closed` 和可见 `feedback_id` fallback，仍需前端 owner 浏览器截图签收。
- [ ] Frontend owner 确认 DeepSeek key 不持久化。
- [x] QA owner 确认 `python -m pytest -q` 只收集项目 `tests/`。验证：398 passed。
- [x] QA owner 确认 `git diff --check` 通过。
- [ ] QA owner 确认 dirty worktree 中数据/缓存/个人 profile 不进入版本单元；`check_repo.py` 已新增 staged excluded path hard fail，仍需最终 stage 清单复核。
- [ ] Reviewer 确认没有把未完成的大路由拆分或真实前端模块化说成已完成。
- [x] Backend/security reviewer T1：rate limit 默认信任 `X-Forwarded-For` 可被绕过。已修为默认不信任代理头、可信代理显式开关、bucket 清理与上限；验证：`tests/test_security_guards.py` 通过。
- [x] Backend/security reviewer T2：`/feedback` 非法 plan/event 静默返回 200。已修为未提供 plan/event 时兼容只计算，提供非法 plan/event 时 404，部分字段时 400；验证：`tests/test_api_app.py::test_feedback_endpoint_rejects_invalid_plan_event_fields` 通过。
- [x] Backend/security reviewer T2：OpenAI provider 异步测试被跳过。已改为 `asyncio.run` 同步测试，并新增 rate limit 错误分类测试；验证：`tests/test_llm_provider_contract.py` 无 skip 通过。
- [x] Backend/security reviewer T3：token 模式下 `/llm-options` 暴露上游 key 配置状态。已修为未认证隐藏 `api_key_configured`，认证后显示真实状态；验证：`tests/test_api_app.py::test_llm_options_masks_provider_key_status_when_token_guard_is_enabled` 通过。
- [x] Frontend/API reviewer T1：API token guard 开启后前端无 token 注入。已补专家设置中的本页内存态后端访问令牌与 `X-Marathon-API-Key` 请求头；验证：`tests/test_astro_frontend_contract.py` 通过，仍需浏览器 smoke 覆盖 401/on/off。
- [x] Frontend/API reviewer T2：OpenAI provider 未处理服务端 key 配置状态。已读取 `api_key_configured` 并在 OpenAI 未配置时阻断生成、提示切换或服务端配置；验证：`tests/test_astro_frontend_contract.py` 通过。
- [x] Frontend/API reviewer T2：负荷文案仍有真实性边界不一致。已统一为计划代理负荷/代理周负荷；验证：`tests/test_astro_frontend_contract.py` 通过。
- [x] Backend coordinator fresh verification T：2026-05-22 重新执行完整门禁，先发现 `tests/test_astro_frontend_contract.py` 5 个普通用户层文案失败，已修复后验证：`tests/test_astro_frontend_contract.py -q` 65 passed；完整 `$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -m pytest -q` 408 passed，3 个第三方 warning；`npm run build` passed；默认 `npm run smoke:workspace` passed；隔离端口 `WORKSPACE_URL=http://127.0.0.1:4330/#workspace npm run smoke:workspace` passed 且临时 4330 已关闭；`git diff --check` passed；`python tools/dev/check_repo.py --scope hygiene` passed with known warnings。
- [x] Round 9 只读 reviewer 已完成并关闭：`019e4e49-a51e-7311-80db-e2c330f09b6a` 未发现阻止当前最小修复继续的 P0/P1 后端代码问题；指出 P1 版本边界仍阻止直接提交/打版本、P2 文档轮次/角色叠加已由 Backend coordinator 收口。
- [x] Backend / Engineering Coordinator 契约复核：已把 `training_plan_review` 从全局说明同步到 `POST /query`、`POST /training-calendar`、`GET /plans/{plan_id}` 的必返字段、前端依赖和目标测试矩阵；历史 398/408 passed 记录保留为当轮验证证据，当前最新完整基线以 Round 10 记录的 414 passed 为准，后续声称完成前仍需重新执行 fresh verification。
- [ ] Frontend owner 仍需浏览器签收：token guard on/off、OpenAI configured/unconfigured、401 失败态、普通日卡/负荷摘要截图、红旗反馈路径。
- [x] Frontend owner Round 11：卡片排版商业化修复已完成并浏览器复核。范围：侧栏画像摘要化、历史计划轻列表、日卡外层摘要化、周卡普通层隐藏计算数字、深灰后台块清理、成熟产品 10+ 来源 Top 3 证据门槛。验证：`tests/test_astro_frontend_contract.py -q` 66 passed；`npm run build` passed；`WORKSPACE_URL=http://127.0.0.1:4325/#workspace npm run smoke:workspace` passed；截图见 `artifacts/frontend-audit/round11-card-layout-*.png`。不替 backend/QA 签收最终商用完成。
- [x] Frontend owner Round 12：阅读疲劳和浅色商业主题对比度修复已完成并浏览器复核。范围：长报告默认折叠、日历优先、行动面板摘要化、周卡默认折叠、日卡 plan/audit/feedback 分层、反馈 quick-first、补充细节默认折叠、浅色主题反馈区文字对比修正、移动端 day modal 底部面板化、从行动面板打开反馈时 scrollTop 复位、普通层系统视角文案改为中国跑者任务语言。验证：`node --check apps/web/src/scripts/app.js` 通过；`tests/test_astro_frontend_contract.py -q` 67 passed；`npm run build` passed；`WORKSPACE_URL=http://127.0.0.1:4342/#workspace npm run smoke:workspace` passed；`WORKSPACE_URL=http://127.0.0.1:4343/#workspace npm run smoke:workspace` passed；`WORKSPACE_URL=http://127.0.0.1:4344/#workspace npm run smoke:workspace` passed；截图见 `artifacts/frontend-audit/round12-reading-fatigue-*.png`、`artifacts/frontend-audit/round12-feedback-quick-first-*.png`、`artifacts/frontend-audit/round12-modal-polish-*.png`、`artifacts/frontend-audit/round12-modal-scroll-fix-*.png`、`artifacts/frontend-audit/round12-copy-guard-*.png`；对比度量测 `已选择` 10.35:1、`补充细节` 17.74:1；移动端 `modalBottomGap=0`、`modalScrollTop=0`、`titleVisible=true`；普通层文案 `visibleForbidden=[]`。红旗反馈路径仍需单独截图签收；不替 backend/QA 签收最终商用完成。
- [ ] QA/version owner 仍需最终复核：Backend coordinator 已完成本批修复后的完整 `python -m pytest -q`、前端 build、默认与隔离 preview smoke、`git diff --check`、repo hygiene；Round 9 只读 reviewer 已确认无后端 P0/P1 代码阻塞，但 dirty worktree、stage 清单和版本单元边界仍需最终签收。

### Round 10 Backend / Engineering Coordinator Update

- Backend owner 已新增 `training_plan_review` 后端契约，覆盖训练负荷、计划结构、周期训练、伤病恢复、康复训练、体能训练、拉伸放松、伤病预防、证据边界和 RAG vs 裸模型。验证：`python -m pytest -q` 通过，414 passed，3 个第三方 warning；`npm run build` in `apps/web` 通过；`git diff --check` 通过；`python tools/dev/check_repo.py --scope hygiene` 通过且仅有已知 warning。
- Frontend owner 下一步需读取本契约并对接 `training_plan_review`：普通层只展示计划评审摘要、风险缺口和下一步动作；专家层展示 `dimensions`、代理负荷缺失输入、证据覆盖和核心字段来源违规。
- 本轮子 agent 管理：尝试开启 1 个只读 reviewer 但上游 504 未产出；随后尝试关闭最近 24 个候选 subagent id，运行时均返回 `not found`。后续继续执行“最多 1 个子 agent，完成后立即关闭并写入 review TODO”。

## 13. Release hardening 退出条件

- [x] 已读取并执行 `docs/quality/release_hardening_loop.md`。当前 Backend / Engineering Coordinator 已按本轮循环读取共享契约、检查 dirty worktree、修复失败项、重跑完整门禁并记录结果；仍不替 Frontend owner 或 QA/reviewer 做最终签收。
- [ ] 前端默认界面只展示用户关心的结果、行动、安全信号和计划内容；内部计算字段、trace、协议细节和排障 ID 不污染普通模式。
- [x] 国外 app/网页对比均有官方资料、公开页面、截图或浏览器观察支撑；没有证据的判断只作为待验证假设。Round 11 已固化 `docs/product/mature_product_acceptance_standard.md`，要求每轮 10+ 来源并只选 Top 3 迁移。
- [x] 同一时间最多保留一个 subagent，且完成后必须关闭。2026-05-22 已关闭上一轮遗留 reviewer：`019e4c66-7b31-7131-9b9e-ad8b7ab596f8`、`019e4c66-cc9b-72d3-a1cd-9b8d21ba76fb`；本轮又关闭遗留子 agent：`019e4c04-f87d-7fd3-a3e1-2f3e6bd4bd48`、`019e4c10-51cc-7310-95b8-88a15a706ea1`、`019e4c35-ff2d-7dc3-ae08-8007d875d4aa`；Round 9 唯一只读 reviewer `019e4e49-a51e-7311-80db-e2c330f09b6a` 已完成并关闭。当前规则：未来最多开 1 个，且完成后立即关闭并写入 review TODO。
- [ ] 前端、后端、QA/reviewer 的最新 review 都没有新的 T0/T1/T2 可修项。
- [ ] 共享契约中所有签收项均完成，且没有新的跨端冲突记录。

## 14. Knowledge Base P13 Release Gate Update

- Backend / Engineering Coordinator 当前分支：`codex/kb-p13-release-gate`。
- P13 已把 source registry release gate 从“schema 通过”收紧为“必须有 approved + ready source”。`internal_structured_rule_seed` 一律归类为 `review_status=seed_only`，即使误标 `needs_review=false` 或 `review_status=approved`，也不得计入 `ready_records`。
- `source_registry_v2.jsonl` 当前审计事实：`750` records，`707` seed records，`0` approved records，`0` ready records。它们可以作为治理种子和后续审核队列，不得被前端或产品文案称为“已审核知识库”。
- `kb_release_report.json.ready_for_next_batch=false`；当前 blockers 为 `no_approved_sources`、`no_ready_sources`、`all_domain_packs_still_have_gaps`。
- Frontend owner 需要继续遵守 EvidenceDrawer 边界：seed、candidate、reviewed-but-not-approved、`model_general_knowledge` 都不能显示成“权威证据”或“已验证处方”；核心处方字段缺 approved `protocol/action_library` 时只能展示 `needs_evidence`。
- QA/reviewer 下一轮必须验证：无 approved source 时，不出现 fake citation、verified-source badge、已验证处方文案或把占位 seed 主课展示为正式动作库证据。
- P13 验证命令：`$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_kb_source_registry.py tests/test_kb_governance.py tests/test_kb_health.py -q`，结果 `22 passed in 0.09s`。

## 15. Knowledge Base P14 Runtime Index Boundary

- Backend / Engineering Coordinator 当前分支：`codex/kb-p14-runtime-v2-index`。
- P14 已让 runtime health 区分 `legacy`、`chunk_schema_v2`、`mixed` 和 `empty`。当前 `data/vector_kb/default/chunks.jsonl` 仍是 legacy；它可以继续作为兼容检索 fallback，但不得作为核心处方证据来源。
- `probe_vector_kb_health`、`bootstrap_knowledge_base` 和 `get_knowledge_base_health_snapshot` 现在会携带 `index_schema_version`、`metadata_completeness`、`runtime_core_prescription_enabled`。
- Vector hit -> EvidenceBinding 现在会保留 v2 metadata：`source_registry_id`、`evidence_domain`、`knowledge_layer`、`domain_pack`、`allowed_use`、`prescription_permission`、`source_url`、`section`、`quality_tier`。
- 新增 artifact：`data/knowledge/governance/runtime_index_v2_manifest.json`。当前状态为 `preview_only_not_runtime`，`can_replace_runtime=false`。切换 runtime 前必须构建独立 v2 vector dir，并通过 health、evidence、evaluation gates；不得覆盖 `data/vector_kb/default`。
- Frontend owner 不能因为后端存在 `chunk_schema_v2_preview` 就显示“运行时已接入 v2 知识库”。普通层只能表达“当前证据链仍需补充审核/运行时仍在 legacy fallback”。
- P14 验证命令：`$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_kb_health.py tests/test_kb_evidence_binding.py tests/test_kb_bootstrap.py tests/test_vector_kb_runtime_contract.py -q`，结果 `14 passed in 0.10s`。

## 16. Knowledge Base P15 Source Review Queue

- Backend / Engineering Coordinator 当前分支：`codex/kb-p15-source-review`。
- P15 已新增 source review workflow：`source_review_queue.jsonl` 记录每个 source 的 `review_status`、结构检查、阻断原因和 `can_enter_runtime_index`；`source_review_summary.json` 汇总状态与 Top blockers。
- 当前审计事实：`750` 条 source 全部 `can_enter_runtime_index=0`；其中 `707` 条 `seed_only`、`43` 条 `candidate`。主要 blockers：`needs_review`、`not_approved`、`local_file_missing`、`seed_only_not_runtime_source`、`url_reachability_not_verified`。
- Frontend owner 不得把 `candidate`、`seed_only` 或 source review queue 中 `can_enter_runtime_index=false` 的来源显示为可点击权威证据；这类来源只能显示为“待审核/待补证据”。
- QA/reviewer 下一轮必须验证：重复 DOI/title/hash 不贡献 coverage，未做 URL/PDF/canonical 检查的来源不能进入 v2 runtime，blocked reasons 不被吞掉。
- P15 验证命令：`$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_kb_source_review.py tests/test_kb_source_registry.py tests/test_kb_governance.py -q`，结果 `21 passed in 0.10s`。

## 17. Knowledge Base P16 Legacy Runtime Quarantine

- Backend / Engineering Coordinator 当前分支：`codex/kb-p16-runtime-quarantine`。
- P16 已新增 `legacy_runtime_quarantine_report.json`，对当前 legacy runtime 的 `9` 个 source / `1160` chunks 做 source 级隔离决策。
- 当前 `10078-60-2017-v60-2017-28.pdf` 被标记为 `quarantine`，原因 `book_review_not_training_evidence`；其余 legacy source 暂为 `explanation_only_legacy`，原因 `legacy_chunk_missing_v2_metadata`。
- `vector_store.load_chunks` 会默认读取 quarantine report 并过滤被隔离 source；原始 `data/vector_kb/default/chunks.jsonl` 不删除、不改写，避免破坏其他 agent 或回滚路径。
- Frontend owner 不得显示被 quarantine source 的 citation；若证据来自 `explanation_only_legacy`，只能作为解释性背景，不能显示为核心处方证据。
- QA/reviewer 下一轮必须验证：book review 不出现在用户可见证据中，legacy source 不获得 `can_write_core`，quarantine report 有 sample preview 和 reasons。
- P16 验证命令：`$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest tests/test_kb_runtime_quarantine.py tests/test_vector_kb_runtime_contract.py tests/test_kb_health.py -q`，结果 `13 passed in 0.10s`。
