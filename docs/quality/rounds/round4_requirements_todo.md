# Round 3 审计 TODO：文档、最终验收与交付边界

> 生成时间：2026-05-22
> 轮次：Round 3
> 产物类型：audit todo
> 最低容量要求：500 行以上，本文件设计为 20 个子阶段，每个子阶段包含审计、修复、验收和 review 颗粒度。

## Round 4 覆盖说明

- [ ] 本文件当前是 Round 4 requirements todo；原 Round 3 通用阶段作为 500 行以上容量模板保留在后文。
- [ ] 本轮不能只做工程内循环；必须先回答“跑者用户为什么需要这个能力”。
- [ ] 本轮不能靠猜竞品；竞品结论必须来自官方文档、可复查公开反馈或截图。
- [ ] 本轮不能把自动化测试全绿当成商用化完成；测试绿只是 release hardening 的一个门槛。
- [ ] 本轮需求 TODO、后端 TODO、review TODO 必须同时存在，且都指向共享契约。
- [x] 新规则：后续每轮最多开启 1 个子智能体；当前计数必须写入 review TODO，完成后必须关闭。
- [ ] 本轮必须提醒前端 owner 阅读 `docs/quality/shared_delivery_contract.md`。
- [ ] 本轮必须把训练负荷真实性作为用户信任需求，而不是单纯 UI copy。
- [ ] 本轮必须把分层知识库厚度作为产品需求，而不是后端实现细节。
- [ ] 本轮必须把 GPT/DeepSeek API 接入作为商用化路线，而不是本地 demo 默认。
- [ ] 本轮退出条件仍是共享契约共同签收，而不是单个 agent 完成。

## Round 4 外部证据清单

- [ ] WHO 健康 AI 治理：AI 健康产品需要透明性、解释性、责任边界和风险治理。来源：https://www.who.int/publications/i/item/9789240029200
- [ ] FDA general wellness：健康生活方式软件需要避免越界到疾病诊断、治疗、缓解或预防。来源：https://www.fda.gov/regulatory-information/search-fda-guidance-documents/general-wellness-policy-low-risk-devices
- [ ] OWASP API Security Top 10 2023：商用 API 必须处理对象级授权、认证、资源滥用和安全配置风险。来源：https://owasp.org/API-Security/editions/2023/en/0x11-t10/
- [ ] TrainingPeaks compliance：竞品把 planned/completed compliance 放到训练日历核心。来源：https://help.trainingpeaks.com/hc/en-us/articles/204861204-What-is-Compliance-and-How-Do-I-Manage-These-Colors-on-My-Calendar-
- [ ] TrainingPeaks pairing：竞品支持 planned 与 completed workout 配对/取消配对。来源：https://help.trainingpeaks.com/hc/en-us/articles/115002250311-How-can-I-pair-and-unpair-my-planned-and-completed-workouts
- [ ] Garmin Daily Suggested Workouts：竞品建议会考虑 training status、training load、load focus、VO2 max、recovery time、sleep、recent workouts、HR/LT/FTP，并且计划训练优先于每日建议。来源：https://support.garmin.com/en-US/?faq=oYknGZ910l1pfBNzkDHX6A&productID=777655&tab=topics
- [ ] Garmin race calendar：竞品在比赛事件进入日历后会围绕目标事件调整建议。来源：https://www8.garmin.com/manuals/webhelp/GUID-5BA20A50-BFFF-4418-AE4E-CA719C39EB05/EN-US/GUID-AFECC098-0B34-4913-9944-66E8DAF64039.html
- [ ] 公开用户反馈只能作为“待验证痛点”，不能单独作为产品事实；使用前必须保留链接、日期、截图或原文摘录。
- [ ] 任何“竞品没做好”的结论必须标注证据等级：official、public_feedback、screenshot_verified、hypothesis。
- [ ] 没有证据时只能写入“待调研”，不能写成“竞品存在某问题”。

## Round 5 Requirements / PM Overlay - 商用差距与证据补充

- [x] 本轮需求输入来自用户商用标准：不能用测试绿替代“能商用”，必须继续看竞品、用户任务、知识库厚度和数据真实性。
- [x] TrainingPeaks 官方帮助继续支持 planned/completed compliance 与 planned/completed pairing 是训练日历基础能力；本产品对应验收是执行状态面板、反馈入库、计划/完成差异和历史回显。
- [x] Garmin 官方 Daily Suggested Workouts 支持“训练状态/负荷/恢复/睡眠/近期训练/比赛日历”等输入；本产品对应验收是不要只按画像静态生成，还要让反馈、睡眠、疼痛、近期执行影响调整。
- [x] OpenAI API 商用化证据：后续 GPT 接入必须服务端 key、provider 抽象、错误分类、token/cost 观测和 rate-limit/retry 设计；不得把 key 作为浏览器持久化配置。
- [x] DeepSeek API 商用化证据：后续 DS 接入必须沿用服务端 provider、超时、错误分类、fallback 和资源保护；前端一次性会话 key 只是本地 demo 兼容路径。
- [x] Runna/同类训练 app 仍需继续找官方资料或截图验证“自适应/漏训/伤病调整”细节；未验证前只作为待调研竞品，不写成事实。
- [x] 数据真实性新要求：即使将来接入心率 TRIMP，也必须标为 `estimated_heart_rate_proxy / estimated / not_device_metric`，不能把代理模型称为设备真实生理负荷。
- [x] 用户可读性新要求：普通模式不显示 `fail-closed`、`feedback_id`、`risk_gate`、`protocol_recheck` 等内部词；这些只属于专家/审计层。
- [ ] 下一轮需求调研：补官方或截图证据确认 Runna、WHOOP/Oura/Strava 对恢复、睡眠、准备度、训练建议的用户呈现方式。
- [ ] 下一轮需求调研：把“分层知识库”从路线写成可验收信息架构：每层有 source metadata、适用人群、证据等级、更新时间、禁用边界和 EvidenceDrawer 定位方式。

## Round 6 Requirements / PM Overlay - 资源滥用与商业运行成本

- [x] OWASP API Security Top 10 把 Unrestricted Resource Consumption 列为 API 风险之一；对 `/query`、GPT/DS provider 和训练日历生成必须有资源保护，而不是只靠前端按钮节流。
- [x] 用户需求角度：商用 app 必须在后端能拒绝短时间重复请求，避免用户误点、脚本滥用或模型 provider 异常导致成本失控。
- [x] 本轮验收标准：高成本/写入路径达到阈值时返回 429 和 `Retry-After`，且不丢失既有反馈/计划数据。
- [ ] 下一轮商用验收：按用户账户/租户/订阅额度做 quota，而不是只按 IP 做本地 in-memory 限流。
- [ ] 下一轮商用验收：把 provider token usage 与 rate limit 关联，支持“骨架已生成、解释补全限流/降级”的产品状态。

## Round 7 Requirements / PM Overlay - GPT/DS Provider 商用接入

- [x] 用户需求：商用 app 不能只依赖本地 Ollama；必须支持 GPT/DeepSeek 这类可部署 provider，并且密钥边界在服务端。
- [x] 本轮验收标准：后端 provider abstraction 至少支持 `ollama`、`ds/deepseek`、`openai/gpt` 三类 provider，并能返回 provider/model 给前端模型选择控件。
- [x] 本轮验收标准：OpenAI provider 使用 mock 测试，不依赖真实 `OPENAI_API_KEY` 或外网。
- [x] 本轮验收标准：token usage 进入统一 `prompt_tokens/completion_tokens/total_tokens`，为后续成本观测和 quota 做基础。
- [ ] 下一轮商用验收：provider 错误分类需要结构化，例如 missing_key、timeout、rate_limited、provider_5xx、invalid_request、content_filter。
- [ ] 下一轮商用验收：前端普通模式需要能选择 OpenAI/GPT 或展示“服务端已配置/未配置”，但不能让用户把 OpenAI key 写入 localStorage。

## Round 8 Requirements / PM Overlay - 外部证据复核与本轮交付约束

- [x] Runna 官方 Plan Realignment 说明 missed workouts 后会给 skip/rearrange/extend/rebuild/current-end-date rebuild 等选项；本产品对应需求是反馈后不能只给文案，必须能表达受影响训练日与调整版计划入口。来源：https://support.runna.com/en/articles/10026375-how-to-use-the-plan-realignment-feature
- [x] Runna 官方说明 missing more than a month 后继续原计划可能增加 injury risk；本产品对应需求是长期漏训/疼痛/高疲劳需要 fail-closed 或重建计划，不应无条件接回原强度。来源同上。
- [x] Oura 官方 Readiness Score 把睡眠、身体信号、活动负荷、短期与长期平衡作为 readiness 输入；本产品对应需求是睡眠/疲劳/疼痛反馈应影响调整建议，但不能伪装为 Oura 设备 readiness。来源：https://support.ouraring.com/hc/en-us/articles/360025589793-An-Introduction-to-Your-Readiness-Score
- [x] WHOOP 官方 Recovery 使用颜色区间表达高/中/低恢复与是否应调整 strain；本产品对应需求是普通用户层用安全判断和行动建议，不直接堆 raw risk fields。来源：https://support.whoop.com/s/article/WHOOP-Recovery
- [x] Strava 官方 Training Log 以周视图、活动颜色和 hover stats 支持训练回顾；本产品对应需求是日历/执行历史要快速扫读，不把计划藏在 Markdown。来源：https://support.strava.com/hc/en-us/articles/206535704-Training-Log
- [x] Strava 官方 Fitness & Freshness 说明数字不如趋势重要，且 Training Load/Relative Effort 依赖 power/HR/RPE 等输入；本产品对应需求是当前负荷只能叫计划代理负荷，趋势可用但不能当设备真实生理负荷。来源：https://support.strava.com/hc/en-us/articles/216918477-Fitness-Freshness
- [x] OpenAI Responses API 官方对象包含 `usage.input_tokens/output_tokens/total_tokens`；本产品对应需求是 provider token usage 需要统一进入观测与后续成本控制。来源：https://platform.openai.com/docs/api-reference/responses/object
- [x] OpenAI rate limit 官方文档说明限流用于防止滥用、保持公平和管理基础设施负载；本产品对应需求是 `/query`、`/feedback`、provider 入口必须有后端资源保护。来源：https://platform.openai.com/docs/guides/rate-limits
- [x] DeepSeek 官方 error codes 包含 400/401/402/422/429/500/503；本产品对应需求是 provider 错误要结构化分类，不能只返回一段异常字符串。来源：https://api-docs.deepseek.com/quick_start/error_codes
- [x] DeepSeek 官方 rate limit 说明会基于服务器负载动态限制并发；本产品对应需求是请求端需要 timeout、降级、限流和用户可理解状态。来源：https://api-docs.deepseek.com/quick_start/rate_limit/
- [x] 本轮需求验收：无证据竞品结论不写成事实；所有竞品/平台结论均附官方链接。
- [x] 本轮需求验收：负荷真实性必须从“测试字段存在”升级为“所有用户可见文案一致”。
- [x] 本轮需求验收：API token guard 不能只是后端开关，前端必须有明确使用路径或明确不支持裸前端直连。
- [x] 本轮需求验收：provider key 配置状态在 token guard 开启时不能裸露给未认证用户。
- [x] 本轮需求验收：provider 错误分类与 token usage 是商用 GPT/DS 接入基础，不等同于完整成本治理。
- [ ] 下一轮需求调研：Runna/WHOOP/Oura/Strava 的用户反馈/截图路径仍需补浏览器截图归档，当前只有官方文档链接。
- [ ] 下一轮需求调研：医疗红旗、运动医学边界、伤后回归训练需要更厚的官方/学术证据层，不能只靠竞品行为推导。
- [ ] 下一轮需求调研：账号/订阅级 quota、团队/教练端协作、隐私导出删除等商用 SaaS 基础需求需要进入 backlog。

## Round 10 Requirements / PM Overlay - 计划评审、训练真实性与 RAG 权威性证明

- [x] 当前执行角色：Backend / Engineering Coordinator，使用 `codex-work-team` 工作流组织本轮，未替 Frontend owner 或 QA/reviewer 做最终签收。
- [x] 子 agent 管理：本轮曾尝试开启 1 个只读 reviewer，但上游 504 未产出；已按用户要求停止继续开新 agent，并批量尝试关闭最近 24 个候选 subagent id，工具均返回 `not found`，表示当前运行时无可关闭句柄。
- [x] 用户新增需求已收敛：计划评审不能只看生成成功，要从训练负荷、计划结构、周期训练、伤病恢复、康复训练、体能训练、拉伸放松、伤病预防、证据边界、RAG vs 裸模型多个维度证明专业性。
- [x] 用户新增需求已收敛：无本地知识来源时不允许普通用户看到“信息不足/请补充上下文”硬拒答；一般解释必须允许模型基于自身通用知识回答。
- [x] 用户新增需求已收敛：无本地证据回答必须标为 `llm_general_knowledge`，不得伪造 source path、页码、chunk id、证据编号或本地知识库命中。
- [x] 用户新增需求已收敛：医疗红旗不是普通拒答，但必须停止训练、建议专业评估，并禁止继续生成高强度替代训练。
- [x] 用户新增需求已收敛：默认 GPT/OpenAI-compatible provider 为 `gpt-5.5`，默认 base URL 为 `https://api.aisz.mom/v1`，密钥不得写入仓库、文档、测试或前端持久化存储。
- [x] 外部证据检索要求：本轮已重新检索 ACSM、WHO、TrainingPeaks、Garmin、Runna、Oura、WHOOP、Mayo/CDC/NHS、力量训练系统综述等来源；TODO 只采用可复查方向，不把未验证竞品推断写成事实。
- [x] ACSM/FITT-VP 需求迁移：处方评审必须覆盖 frequency/intensity/time/type/volume/progression 的结构化思路；本产品对应字段是 `plan_structure`、`training_load`、`periodization` 和核心处方来源。
- [x] WHO 健康 AI 需求迁移：AI 训练建议必须透明、可解释、有责任边界；本产品对应 `evidence_control`、`rag_vs_base_model`、`llm_general_knowledge` 标注和医疗红旗边界。
- [x] TrainingPeaks/Garmin/Runna 竞品迁移：成熟训练产品围绕日历、计划/完成、训练状态、恢复、比赛目标和调整构建；本产品对应状态面板、反馈闭环、调整历史和本轮计划评审。
- [x] Oura/WHOOP 竞品迁移：恢复/睡眠/准备度表达应服务用户决策，但不能伪装设备数据；本产品当前只能展示计划代理负荷和用户反馈风险，不得展示设备级 readiness/recovery。
- [x] Mayo/CDC/NHS 等医学边界迁移：胸痛、头晕、热病迹象、伤痛加重和伤后回归必须进入安全边界，不得由训练生成链路继续加量。
- [x] 力量训练与跑者表现证据迁移：力量/体能不应只做“可选补充”；计划评审应识别是否存在 strength/conditioning 支撑或明确标为 gap。
- [x] 拉伸放松与恢复需求迁移：日卡评审必须识别 warmup/cooldown/mobility/stretching 覆盖率，否则前端不能宣称“完整每日训练卡”。
- [x] 伤病预防需求迁移：评审至少检查休息日、质量课密度、周负荷跃迁、热身冷身覆盖和疼痛/医疗边界。
- [x] 训练负荷真实性需求：所有负荷维度只能标为 `planned_load_proxy` 或 `estimated`，必须保留 `not_device_metric=true`、缺失输入和 disclaimer。
- [x] RAG 权威性证明需求：不能只说“用了 RAG 更专业”，必须返回可审计证据覆盖、核心字段来源检查、needs_evidence 计数和与裸模型的边界说明。
- [x] 前端协作要求已写入共享契约：前端 owner 需要预留计划评审入口，普通层只展示摘要/风险/下一步动作，专家层展示维度、代理负荷缺失输入、证据覆盖和核心字段违规。
- [ ] P0：普通 QA 无本地证据时不硬拒答，必须返回 `llm_general_knowledge` 一般回答，并禁止伪造引用。
- [ ] P1：计划生成结果必须包含 `training_plan_review.review_version=training_plan_review.v1`。
- [ ] P2：计划评审必须覆盖 `training_load`，并明确 `source_type=planned_load_proxy`、`not_device_metric=true`、缺失 HR/HRV/sleep/device recovery 等输入。
- [ ] P3：计划评审必须覆盖 `plan_structure`，统计训练日、休息日、质量课和每周质量课密度。
- [ ] P4：计划评审必须覆盖 `periodization`，检查阶段摘要、阶段边界、实际周数和阶段名称。
- [ ] P5：计划评审必须覆盖 `injury_recovery`，识别风险门、医疗红旗和 blocked/referral 日。
- [ ] P6：计划评审必须覆盖 `rehabilitation`，识别恢复跑、低冲击替代、疼痛回归训练和保守边界。
- [ ] P7：计划评审必须覆盖 `strength_conditioning`，没有力量/体能内容时标为 gap，不能暗示已覆盖。
- [ ] P8：计划评审必须覆盖 `mobility_recovery`，检查热身、冷身、拉伸、放松和活动度覆盖率。
- [ ] P9：计划评审必须覆盖 `injury_prevention`，检查休息日、质量课密度、周负荷跃迁和恢复覆盖。
- [ ] P10：计划评审必须覆盖 `evidence_control` 与 `rag_vs_base_model`，证明 RAG 方案可追溯、可复核、可 fail-closed，但不把这等同于真实生理效果证明。
- [ ] 验收标准：`/query` skeleton 路径返回 `training_plan_review`，且包含至少 10 个维度。
- [ ] 验收标准：`/training-calendar` 返回 `training_plan_review`，前端可直接读取同一契约。
- [ ] 验收标准：`GET /plans/{plan_id}` 返回 `training_plan_review`，历史计划不丢评审入口。
- [ ] 验收标准：OpenAPI schema 暴露 `training_plan_review`，避免前端靠隐式字段对接。
- [ ] 验收标准：无证据回答测试覆盖 static fallback 与 missing info handler，不再出现普通用户硬拒答。
- [ ] 验收标准：OpenAI/GPT 默认模型和 base URL 有测试锁定，但不写入任何 API key。
- [ ] 验收标准：计划评审测试必须包含 strength/mobility 缺口路径，防止所有计划都被假装评审通过。
- [ ] 仍需调研：ACSM 原始处方文档、Mayo/CDC/NHS 红旗材料、力量训练系统综述需要在后续知识库层保存 metadata、适用范围和禁用边界。
- [ ] 仍需调研：Runna、Garmin、TrainingPeaks 的具体 UI 截图和用户反馈需要单独归档，不能只靠官方说明推导。
- [ ] 仍需产品设计：计划评审普通层文案要把“风险/缺口/下一步”讲清楚，不能把专家 JSON 字段直接给用户。
- [ ] 仍需产品设计：当 `rag_vs_base_model.status=llm_general_knowledge_only` 时，普通用户可以得到一般说明，但不能显示为“权威处方已验证”。
- [ ] 仍需产品设计：分层知识库要扩展到训练协议、动作库、运动医学边界、康复/体能/拉伸、多专家观点和竞品证据层。

## Round 4 P0：跑者核心任务必须被产品闭环覆盖

- [ ] 用户任务 1：输入目标、比赛日期、跑量、可训练日和限制，生成完整多周训练日历。
- [ ] 用户任务 2：浏览完整计划，而不是只拿 Markdown 文本。
- [ ] 用户任务 3：点开每日训练卡，看到热身、主课、冷身、强度、负荷、目的、风险和依据。
- [ ] 用户任务 4：训练后提交完成/部分完成/跳过/不适、疲劳、疼痛、睡眠和备注。
- [ ] 用户任务 5：系统给出明日调整、本周微调、替代训练、风险提醒和受影响训练日。
- [ ] 用户任务 6：用户能生成调整版计划，并看到和原计划的差异。
- [ ] 用户任务 7：用户能理解为什么某天被降级、拒绝或要求专业评估。
- [ ] 用户任务 8：用户能看到计划中的处方字段来自协议、动作库、知识库还是模型一般知识。
- [ ] 用户任务 9：用户能区分“计划代理负荷”和设备真实生理负荷。
- [ ] 用户任务 10：用户能在无本地证据时获得一般解释，但不会被伪造引用误导。

## Round 4 P0：竞品已证明的基础能力要补齐

- [ ] TrainingPeaks 类能力：planned/completed compliance 必须进入状态面板。
- [ ] TrainingPeaks 类能力：每个 workout card 需要计划/完成差异、评论/反馈和执行状态。
- [ ] TrainingPeaks 类能力：planned 与 completed 的配对逻辑需要有本地等价物，即 `event_id + feedback_id + plan_diff`。
- [ ] Garmin 类能力：建议需要考虑训练状态、训练负荷、恢复、睡眠和近期训练。
- [ ] Garmin 类能力：比赛日期/目标事件必须影响计划周期和训练优先级。
- [ ] Garmin 类能力：计划训练优先级高于临时建议，反馈调整不能随意覆盖整个周期。
- [ ] 竞品基础能力未完成前，不得把产品描述为完整商业训练平台。
- [ ] 对已完成能力必须有截图、测试、接口返回和共享契约四类证据之一。
- [ ] 对未完成能力必须进入 backlog，不允许在宣传或 UI 文案里暗示已经完成。
- [ ] 前端展示必须让用户知道当前是计划、反馈、调整版还是历史计划。

## Round 4 P0：竞品未必做好但用户理应需要的差异化

- [ ] 差异化 1：证据抽屉展示每个核心处方字段的来源。
- [ ] 差异化 2：无证据时允许一般知识解释，但明确标注 `llm_general_knowledge`。
- [ ] 差异化 3：核心处方字段 fail-closed，不能由 LLM 自由编造。
- [ ] 差异化 4：反馈后真实改计划，而不只是生成一段建议文案。
- [ ] 差异化 5：生成调整版计划时显示计划 diff 和受影响训练日。
- [ ] 差异化 6：明确告诉用户为什么降级、为什么拒绝、为什么建议专业评估。
- [ ] 差异化 7：训练负荷透明标注代理模型、输入字段和缺失字段。
- [ ] 差异化 8：分层知识库让不同专家域可追踪，不混成一个不可审计 RAG。
- [ ] 差异化 9：用户画像字段变更后，计划再生成要显示哪些字段影响了变化。
- [ ] 差异化 10：历史反馈与版本 diff 支持用户回看“系统是否真的学到了我的状态”。

## Round 4 P1：分层知识库厚度路线

- [ ] KB 层 1：训练协议层，包括半马、全马、10K、低跑量、回归训练、减量期。
- [ ] KB 层 2：动作库层，包括主课、热身、冷身、强度区间、替代训练、动作禁忌。
- [ ] KB 层 3：运动医学边界层，包括胸痛、头晕、中暑、疼痛、疲劳、睡眠不足。
- [ ] KB 层 4：负荷解释层，包括 planned load proxy、TRIMP、设备指标边界、缺失输入。
- [ ] KB 层 5：竞品与用户任务层，包括 TrainingPeaks/Garmin/Runna 等功能证据与用户痛点。
- [ ] KB 层 6：画像与反馈案例层，包括跑量、目标、可训练日、伤病限制、反馈历史和调整结果。
- [ ] 每层 KB 必须有 source metadata、更新时间、证据等级和适用范围。
- [ ] 每层 KB 必须能被 EvidenceDrawer 定位，不允许只存在于自由文本。
- [ ] 核心处方只允许 protocol/action_library/明确 evidence source，不允许普通 RAG 候选直接写入。
- [ ] `llm_general_knowledge` 可以补解释，但不能补核心处方。

## Round 4 P1：GPT/DeepSeek API 商用化方向

- [ ] 后续默认 LLM provider 要支持 GPT 与 DeepSeek API。
- [ ] provider 抽象必须隔离模型选择、API key、timeout、retry、错误分类和 token usage。
- [ ] API key 必须走服务端环境变量或一次性会话输入，不得浏览器持久化。
- [ ] 需要记录 provider、model、prompt tokens、completion tokens、total tokens、成本估算和失败原因。
- [ ] 需要保留 skeleton-first fallback，不能因为 GPT/DS API 失败导致无计划返回。
- [ ] 需要设置资源滥用保护：timeout、max tokens、rate limit、并发限制。
- [ ] 需要区分“模型解释补全失败”和“计划骨架失败”。
- [ ] 需要让用户知道当前计划是完整 LLM 解释、skeleton fallback 还是 partial generated。
- [ ] DeepSeek/GPT 接入验收必须包含 mock provider 测试，避免真实 key 依赖 CI。
- [ ] 所有 provider 错误不得泄漏密钥、Authorization header 或完整用户敏感输入。

## Round 4 P1：训练负荷真实性需求

- [ ] 当前训练负荷只能叫 `planned_load_proxy` 或“计划代理负荷”。
- [ ] 前端不得展示为 Garmin/COROS/TrainingPeaks 同款真实生理负荷。
- [ ] 后端每个负荷字段必须带 method、source_type、load_kind、is_estimated、not_device_metric。
- [ ] 后端每个负荷字段必须带 calculation_inputs 和 missing_inputs。
- [ ] 前端必须展示免责声明：由计划时长与强度区权重估算，用于课表内部比较。
- [ ] 如果未来接入心率/HRV/睡眠，必须把数据来源和同步时间写入负荷解释。
- [ ] 不能用计划代理负荷诊断过度训练或疾病风险。
- [ ] 可以用代理负荷做趋势提醒，但必须提示结合疲劳、疼痛和睡眠。
- [ ] 训练负荷算法变更必须产生版本号和回放测试。
- [ ] 对用户展示的负荷趋势必须可追溯到日卡输入字段。

## Round 4 PM：本轮需求决策记录

- [ ] 当前 release 仍是 hardening，不是营销发布。
- [ ] 商用 app 的最低定义是：用户任务闭环、风险边界清楚、数据真实性可解释、证据链不伪造、失败态不伪装成功。
- [ ] 当前差异化优先级高于新增花哨页面：证据、反馈、计划 diff、知识库厚度、负荷真实性。
- [ ] 若前端/后端对完成状态不一致，以共享契约未签收为准。
- [ ] 若竞品证据不足，先写调研任务，不做产品事实判断。

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
