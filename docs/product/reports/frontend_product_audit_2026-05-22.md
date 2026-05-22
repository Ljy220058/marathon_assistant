# Frontend Product Audit Report

> 执行日期：2026-05-22  
> 范围：`docs/product/frontend_audit_todo.md` 的 T0-T9 全量只读审计  
> 目标：把当前前端从“功能可用”审计到“可信、专业、可长期使用的训练产品”  
> 结论：早期四个前端 T0 阻断项已完成主要修复，当前前端进入 release hardening 复核阶段；仍不能宣称完整商用发布，因为后端完整商用安全、QA/reviewer 最终签收、dirty worktree 版本边界和持续浏览器验收尚未闭合。

## Evidence

- 页面入口：`http://127.0.0.1:4321/`
- API 入口：`http://127.0.0.1:8010/`
- 前端入口：`apps/web/src/pages/index.astro`
- 样式入口：`apps/web/src/styles/global.css`
- 已有生成态截图：`artifacts/frontend-audit/dashboard-current.png`
- 已有训练日详情截图：`artifacts/frontend-audit/day-modal-current.png`
- 已有生成态结构：`artifacts/frontend-audit/page-state.json`
- 新增桌面首屏截图：`artifacts/frontend-audit/desktop-initial-2026-05-22.png`
- 新增移动首屏截图：`artifacts/frontend-audit/mobile-initial-2026-05-22.png`
- 新增移动抽屉截图：`artifacts/frontend-audit/mobile-drawer-open-2026-05-22.png`
- 新增移动布局量测：`artifacts/frontend-audit/mobile-layout-state-2026-05-22.json`
- 浏览器控制台：本轮 `error/warning` 页面日志为空。

## Round 6 Cross-industry Commercial Aesthetic Evidence

> Frontend owner 记录。只代表前端审美迁移、信息架构和普通层降噪视角，不替 Backend owner 或 QA/reviewer 签收。

### Production / Finance / Design Product Evidence

| 产品 | 来源 | 可观察事实 | 可迁移范式 | 不迁移边界 |
|---|---|---|---|---|
| Linear | https://linear.app/docs/display-options / https://linear.app/docs/custom-views | View 可以控制布局、分组、排序和显示属性。 | 普通层字段最少化，专家层再打开更多属性。 | 不迁移 issue/CRM 式高密度字段。 |
| Stripe Dashboard | https://docs.stripe.com/dashboard/basics?locale=en-GB | Dashboard Home 放业务表现和重要通知，Workbench/API log 属于开发者边界。 | 普通首页只放结果和行动，工程日志进入专家入口。 | 不把 API log、request id、trace 字段放普通层。 |
| Notion | https://www.notion.com/help/views-filters-and-sorts | 同一数据可有多个 view，每个 view 有独立 layout、property visibility、filter、sort、group。 | 日历、周视图、风险视图、反馈视图分别控制字段可见性。 | 不迁移复杂 database 操作感。 |
| Figma | https://help.figma.com/hc/en-us/articles/360039831974-View-layers-and-pages-in-the-left-sidebar | Toolbar、side panels、canvas 分层；可隐藏/最小化 UI，把注意力还给画布。 | 训练日历是主画布，侧栏只做导航/筛选/依据。 | 不把核心日历塞成抽屉附属物。 |
| Apple Health | https://www.apple.com/uk/newsroom/2021/06/apple-advances-personal-health-by-introducing-secure-sharing-and-new-insights/ | Summary、Trends、Sharing、alerts 强调重要趋势、用户控制和隐私。 | 先展示趋势/提醒，再解释来源。 | 不复制 Apple 视觉资产或健康环形图。 |
| Mercury / Ramp / Attio | https://support.mercury.com/hc/en-us/articles/44277089544084-Insights-page-overview / https://support.ramp.com/hc/en-us/articles/6048244057747-Real-time-reporting / https://attio.com/help/reference/managing-your-data/views/filter-and-sort-views | 高密度业务数据通过 overview、report、filter、saved view 下钻。 | 专家/审计数据应保存为可恢复视图，不污染普通主路径。 | 不迁移财务/CRM 的字段密度。 |
| Superhuman / Arc | https://new.superhuman.com/split-inbox-power-simplified-159433 / https://resources.arc.net/hc/en-us/articles/19228064149143-Spaces-Distinct-Browsing-Areas | Split Inbox、Spaces、command-style action 降低上下文切换。 | 后续可做快捷命令，但当前优先普通路径清晰。 | 不在核心未稳前加 command palette。 |

### Health / Fitness / Habit Product Evidence

| 产品 | 来源 | 可观察事实 | 可迁移范式 | 不迁移边界 |
|---|---|---|---|---|
| WHOOP | https://apps.apple.com/us/app/whoop/id933944389 | Sleep、Strain、Recovery、Stress 被包装成日常行动建议，同时标明非医疗设备。 | 风险/恢复文案行动化：停止、降级、恢复、评估。 | 不迁移 Recovery、Strain、HRV 等设备指标语义。 |
| Oura | https://support.ouraring.com/hc/en-us/articles/360057791533-Readiness-Contributors | Readiness 由多个 contributor 解释。 | 可以迁移“摘要 + contributor 下钻”，但 contributor 是训练依据/风险依据/计划依据。 | 不迁移准备度分、HRV、体温、睡眠阶段。 |
| Runna | https://www.runna.com/en-gb / https://support.runna.com/en/articles/10473504-your-quick-guide-to-navigating-the-runna-app | Today tab 是每日训练主入口；不舒服、假期、比赛变化会进入计划调整。 | 日历上方需要“下一次训练 / 本周重点 / 安全提醒 / 反馈入口”。 | 不声称自动适配拥有 Runna 同等教练服务能力。 |
| TrainingPeaks | https://help.trainingpeaks.com/hc/en-us/articles/231472468-TrainingPeaks-Athlete-User-Guide | Athlete 侧围绕 Calendar、workout、metrics、coach-athlete 协作组织训练。 | 专家层可以保留负荷、阶段、证据、协议校验。 | 普通层不默认展示 Fitness/Fatigue/Form。 |
| Strava | https://support.strava.com/hc/en-us/articles/206535704-Training-Log / https://support.strava.com/hc/en-us/articles/28437860016141-Progress-Summary-Chart | Training Log 和 Progress 支持趋势、过滤、运动类型区分。 | 后续趋势页可按周/月过滤关键训练和完成情况。 | 不迁移社交竞争、排行榜优先级。 |
| Garmin Connect | https://apps.apple.com/us/app/garmin-connect/id583446403 | 首页可个性化，只显示有用信息；活动、健康、训练、路线分层。 | 普通层少字段、今日优先、用户可理解。 | 不迁移设备健康趋势语义。 |
| Nike Run Club | https://about.nike.com/en/newsroom/releases/nike-run-club-app-new-features / https://apps.apple.com/us/app/nike-run-club-running-coach/id387771637 | Guided runs、训练计划、天气/日出日落、实时分享服务于出门准备。 | 安全提醒和出门准备比审计字段更靠前。 | 不迁移品牌语气和素材。 |
| Headspace / Calm / Eight Sleep | https://apps.apple.com/us/app/headspace-sleep-meditation/id493145008 / https://apps.apple.com/us/app/calm/id571800810 / https://apps.apple.com/us/app/eight-sleep/id1086913845 | 高压健康场景用低压力行动语言和 plain-language explanation。 | 红旗/疲劳/疼痛文案要短、明确、低压力。 | 不把心理健康或睡眠设备能力伪装成本项目能力。 |

### Round 6 Migration Decision

- 已落地：`docs/quality/shared_delivery_contract.md` 增加跨行业高端商用审美迁移职责。
- 已落地：`docs/quality/release_hardening_loop.md` 增加证据四列法和迁移边界。
- 已落地：训练日历新增普通层行动摘要面板：下一次训练、本周重点、安全提醒、反馈入口。
- 仍需浏览器验证：桌面/移动端生成后截图、日卡详情、反馈 tab、医疗红旗阻断、普通层 raw 字段不可见。
- 不迁移项：设备真实生理指标、恢复分、准备度分、品牌视觉资产、API log 工作台、CRM/项目管理式字段密度。

## Round 7 Frontend Owner Evidence And Fixes

> Frontend owner 记录。只代表前端普通层信息架构、状态面板和浏览器验证视角，不替 Backend owner 或 QA/reviewer 签收。

### Additional High-end Commercial Evidence

| 产品 | 来源 | 可观察事实 | 可迁移范式 | 不可迁移边界 |
|---|---|---|---|---|
| Oura | https://support.ouraring.com/hc/pl/articles/360025589793-Readiness-Score | Readiness 用短状态与 contributor 解释低状态原因。 | 训练状态面板应显示用户行动语言：待反馈确认、需要关注、建议降级、建议医疗评估。 | 不迁移 readiness 分、HRV、体温或睡眠阶段语义。 |
| WHOOP | https://www.whoop.com/us/en/product-feature/ / https://support.whoop.com/s/article/How-to-Use-the-AI-Powered-WHOOP-Coach | Sleep、Recovery、Strain、Coach 以日常行动建议组织信息。 | 首屏行动摘要优先回答今天/本周怎么练、是否需要降级。 | 不迁移 AI Coach 的持续生理感知能力或医疗承诺。 |
| Garmin | https://support.garmin.com/en-IE/?faq=hsKqNlQksk0Q6Zf1EbIjO9&productID=125677&tab=topics | Training readiness 用短消息和影响因素解释训练准备度。 | 风险提醒使用“短消息 + 原因”，不要显示原始枚举。 | 不迁移 HRV、压力、急性负荷等设备指标。 |
| TrainingPeaks | https://www.trainingpeaks.com/ / https://apps.apple.com/us/app/trainingpeaks/id408047715 | Athlete 侧围绕 today workout、calendar、schedule、summary。 | 训练日历和下一次训练是主产品面，执行状态只是辅助。 | 不迁移 TSS/CTL/ATL 等专业指标到普通层。 |
| Nike Run Club | https://about.nike.com/newsroom/releases/nike-run-club-app-new-features / https://apps.apple.com/us/app/nike-run-club-running-coach/id387771637 | Guided runs 和 training plans 强调用可执行指导语降低认知负担。 | 单日卡和状态面板使用教练式动作文案。 | 不迁移品牌语气、音频内容或名人教练资产。 |
| Apple Health | https://support.apple.com/en-us/ht203037 | Summary tab 有 Pinned、Highlights、Health Checklist。 | 关键结果固定展示，内部审计与趋势下钻。 | 不迁移系统级健康身份或医疗生态暗示。 |
| Strava | https://support.strava.com/hc/en-us/articles/18001474720397-Creating-Routes-on-Mobile | 移动端围绕当前任务与高级偏好下钻。 | 移动端优先下一次训练和安全提醒，高级筛选放日历控制。 | 不迁移排行榜和社交竞争优先级。 |
| Linear | https://linear.app/docs/triage / https://linear.app/docs/inbox | Triage/Inbox 把异常从正常 workflow 分离。 | 证据缺口、待协议复核、红旗反馈进入复核层，不压主界面。 | 不迁移工程工具字段密度。 |
| Stripe Radar | https://docs.stripe.com/radar/reviews / https://docs.stripe.com/radar/risk-evaluation | 风险 review queue 和详情页分离，风险状态有 unknown/not evaluated。 | 训练风险 unknown 不应伪装为安全通过；普通层显示“待反馈确认”。 | 不迁移支付风控术语或业务风险模型。 |

### Round 7 Finding

- 发现：普通层状态面板在浏览器实测中显示英文枚举 `attention`，违反“普通用户不看内部状态字段”的契约。
- 修复：`statusLabel()` 增加 `attention -> 需要关注`、`unknown -> 待反馈确认`、`deescalate -> 建议降级`。
- 发现：新生成计划尚未开始执行时，状态面板把未来训练当作漏反馈，显示 `补录 16 天反馈`，这会制造不必要的焦虑和错误欠账感。
- 修复：新增 `hasFeedbackRecord()` 与 `isFeedbackDue()`；只有已到期日期或显式执行状态且没有反馈的训练日才计入 `missed_feedback_count`。
- 测试：`tests/test_astro_frontend_contract.py` 已补状态面板契约断言。
- 待复核：重新构建后需要桌面/移动浏览器截图确认普通层不再显示英文枚举和未来漏反馈。

## T0 Blockers

### T0-1 生成完成态不稳定

- 证据：T0 实测生成后已有 28 个 `.day-card`，但主状态仍显示“补充解释中”，最终可能从 90% 回落到 86% fallback。相关状态分散在 `planProgress`、`resultBadge`、`queryHint`、`workspaceFlow`，见 `apps/web/src/pages/index.astro:728`、`apps/web/src/pages/index.astro:4481`。
- 用户影响：用户不知道计划是完成、可执行、失败还是仍在等待，可能重复点击生成、取消请求或误以为产品卡住。
- 建议修复：建立单一 `GenerationStatusViewModel`。日历骨架可用后主状态固定为“计划可用”，`explanation_pending/fallback` 只作为次级说明，不再覆盖主完成态，进度条不允许回退。
- 验收方式：生成 4 周计划后，日历出现时主 badge 显示“计划可用”；LLM 超时只提示“解释稍后可重试”；进度不从高值回退。

### T0-2 未提供成绩时展示异常 PB/目标成绩

- 证据：T0 用“目标完赛、每周跑量 25 km、最长跑 12 km、无伤病”生成后，摘要出现“当前半马 PB 1:11 / 目标半马 1:08:59”。前端成绩展示入口见 `apps/web/src/pages/index.astro:2902`。
- 用户影响：普通完赛用户看到精英级配速，会直接怀疑计划基于错误画像生成。
- 建议修复：对 `performanceCalibration` 增加 provenance gate。缺少用户输入或后端明确来源时，不展示具体 PB、目标成绩或能力差距；改为“未提供当前成绩，暂不做能力差距评估”。
- 验收方式：同样输入重新生成时，页面不得展示 `1:11`、`1:08:59` 或任何未输入成绩。

### T0-3 医疗红旗结果仍混入普通训练调整结构

- 证据：`isMedicalReferralFeedback()` 已阻断普通 regenerate，见 `apps/web/src/pages/index.astro:2239`、`apps/web/src/pages/index.astro:2464`；但 medical referral 结果仍可能渲染“明日调整 / 本周微调 / 替代训练 / 计划差异”等普通字段，见 `apps/web/src/pages/index.astro:2367`。后端医疗调整文案入口见 `apps/backend/src/marathon_qa_assistant/apps/api_app.py:366`。
- 用户影响：胸痛、头晕、热病等红旗场景下，普通“调整计划”结构会削弱停止训练和专业评估的安全信号。
- 建议修复：为 `medical_referral` 建独立红旗结果卡，只展示“停止训练”“不要生成调整计划”“建议专业医疗评估”“触发信号”。隐藏计划差异、替代训练、受影响训练日等普通训练优化字段。
- 验收方式：提交包含 chest pain、dizzy 或 heat illness 的反馈后，结果区域无“生成调整版计划”、无普通计划差异字段，红旗文案为中文且明确 fail-closed。

### T0-4 “可执行”与 `not_evaluated` 同屏冲突

- 证据：`page-state.json` 和详情截图显示“复核动作：可执行”与“风险状态：not_evaluated”并列。前端渲染入口见 `apps/web/src/pages/index.astro:4110`、`apps/web/src/pages/index.astro:4146`。
- 用户影响：用户可能把“可执行”误读为风险已评估通过，但实际风险门未评估。
- 建议修复：建立 `TrustStatusViewModel`。当 `risk_gate` 缺失或为 `not_evaluated` 时，不显示无条件“可执行”，改为“训练结构可执行；风险未评估，请按疲劳/疼痛自检后执行”。
- 验收方式：普通用户 UI 不出现 raw `not_evaluated`；风险未评估状态不会与“安全通过”同屏混淆。

## T1 Product Experience

### 训练日详情信息过载

- 证据：`buildDayModalHtml()` 在一个 modal 内连续渲染可信状态、产品状态、指标、热身/主课/冷身、解释、审计、历史反馈和反馈表单，见 `apps/web/src/pages/index.astro:4146`；截图 `day-modal-current.png` 首屏主要是状态和指标，反馈入口不可见。
- 建议修复：详情改为三层：`训练安排`、`依据/审计`、`反馈调整`。默认展示训练安排；审计默认折叠；反馈入口固定在 header/footer。
- 验收方式：打开训练日后，首屏能看到主课、强度、时长和反馈入口。

### 日历卡片密度过高

- 证据：生成态有 28 张 day card，单卡同时承载日期、强度、时长、负荷、协议状态、动作库命中、累计负荷和详情入口。`.calendar-grid` 为 `repeat(auto-fit, minmax(170px, 1fr))`，`.day-card` 最小高度 168px，见 `apps/web/src/styles/global.css:2540`。
- 建议修复：卡片只保留“练什么、多久/多远、强度、执行状态”；证据、负荷解释和审计进入详情层。桌面按周扫读，移动端今日优先。
- 验收方式：3 秒内能读出今日训练内容、强度和是否可执行。

### 移动端抽屉遮挡阅读路径

- 证据：375x667 量测中 `.side-drawer[open]` 为 `x=12 y=34 w=336 h=547`，覆盖主内容；移动布局状态见 `artifacts/frontend-audit/mobile-layout-state-2026-05-22.json`，CSS 见 `apps/web/src/styles/global.css:3312`。
- 建议修复：移动端保留底部入口，但打开后使用明确的全屏/半屏 drawer，并让主内容背景 inert；关闭后恢复阅读位置。
- 验收方式：375px 打开日历和导航时，主训练内容可读；关闭入口不遮挡卡片 CTA。

### 工程态暴露给普通用户

- 证据：详情中出现 `WorkflowTrace`、`Trace 节点`、`KB 未触发`、`AET-006`、`not_evaluated`。相关渲染见 `apps/web/src/pages/index.astro:1476`、`apps/web/src/pages/index.astro:4085`、`apps/web/src/pages/index.astro:4090`。
- 建议修复：普通模式只展示“证据状态、协议状态、风险状态、修复状态”的用户化标签；expert 面板也只渲染白名单字段，不输出 raw JSON。
- 验收方式：前端可见文案不出现 `WorkflowTrace`、`Trace 节点`、raw `not_evaluated`、内部 action id。

### HMP 术语未进入 UI 解释层

- 证据：`half_marathon_glossary.py` 已定义 `HMP`、`95% HMP 专项耐力`、`HMP 容量预算`、`动态配速校准`、`疲劳降级`、`恢复窗口`；`output_nodes.py` 输出 `glossary_terms`，但 `apps/web/src/pages/index.astro:2574` 只收集证据项，没有消费术语解释。
- 建议修复：单日 modal、证据抽屉或 HMP 面板渲染 `glossary_terms`，每个术语显示主名称、简短定义和训练影响。
- 验收方式：任一 HMP/阈值/恢复窗口相关训练日，1 次点击内能看到术语解释。

## T2 Quality Backlog

### 无证据与内置协议规则混淆

- 证据：无外部证据时前端会构造 `HMP-1/HMP-2` fallback，见 `apps/web/src/pages/index.astro:2609`；后端 `state_models.py` 默认列出协议 `source_docs`。
- 建议修复：区分 `evidence`、`protocol_rule`、`model_knowledge`。只有真实 evidence item、页码或 source binding 才显示编号证据；协议 fallback 标为“内置规则说明，非外部证据”。
- 验收方式：`evidence_state.status=missing_or_partial` 或 `evidence_count=0` 时，不显示 `#HMP-*` 伪证据编号。

### 可访问性基础需要补齐

- 证据：T5 发现 `openDayModal()`、`openEvidenceDrawer()` 只聚焦关闭按钮，没有 focus trap 或背景 `inert`，见 `apps/web/src/pages/index.astro:2753`、`apps/web/src/pages/index.astro:4294`。全局 focus 样式主要覆盖输入框，见 `apps/web/src/styles/global.css:691`。
- 建议修复：建立全局 `:focus-visible` token；自定义 modal/drawer 增加 focus trap、背景 inert、Esc 关闭、触发器焦点恢复。
- 验收方式：只用键盘可以生成计划、打开训练日、打开证据、提交反馈并关闭弹层，焦点始终可见。

### 训练解释缺少结构化剂量逻辑

- 证据：前端主要取 `training_objective / why_scheduled / decision_summary / week_goal` 一段文本，见 `apps/web/src/pages/index.astro:4201`。
- 建议修复：关键课解释拆成“阶段目标、单课目标、剂量依据、恢复窗口、容量预算、后续承接关系”。
- 验收方式：每个关键课至少展示“练什么能力 / 为什么这个强度和距离 / 如何恢复或降级”三段解释。

### 负荷表达容易被误读为生理诊断

- 证据：总览有代理负荷免责声明，见 `apps/web/src/pages/index.astro:1200`；但日卡直接显示“90 负荷 / 稳定”。
- 建议修复：日卡使用“计划代理负荷 90”“课表内稳定”，并在高负荷/稳定旁显示“不是疲劳诊断”。
- 验收方式：日卡、modal、负荷曲线三处均明确“代理负荷/课表内比较/非生理诊断”。

## T3 Polish

- 视觉色彩：当前 `:root` 有语义 token，但全局仍有大量 `rgba()`、渐变和局部色值；`--accent`、`--accent-1`、`--accent-2`、`--success`、`--warning`、`--danger` 高频同屏出现。建议将主强调色限制到一个，状态色只用于真实状态。
- 圆角/阴影：`--radius: 8px` 与 drawer 14px、圆形关闭按钮、999px pill 等混用。建议定义组件 token：`radius-control`、`radius-card`、`radius-pill`、`shadow-overlay`。
- 信息命名：导航中的“依据 / 训练依据 / Training Basis / 基石依据 / 依据影响 / 安全校验”需要统一为“为什么这样练 / 安全校验 / 证据来源”。
- 首屏路径：主卡片提示“先完善画像”，但画像字段主要在侧栏。建议主工作区保留最小画像字段或把“直接输入目标即可生成”作为唯一主路径。

## T8 Frontend Architecture

### 现状

- `apps/web/src/pages/index.astro`：4925 行。
- `apps/web/src/styles/global.css`：3478 行。
- `index.astro` 同时承担 API 调用、状态管理、本地存储、画像编辑、日历渲染、训练日 modal、反馈提交、证据抽屉、workflow trace 展示和事件绑定。
- 静态扫描显示大量 `innerHTML` 渲染和事件重绑，关键入口包括 `renderReport()`、`renderCalendar()`、`buildDayModalHtml()`、`buildFeedbackResultHtml()`、`renderEvidencePreview()`、`runQuery()`。

### 风险

- 状态源太多，导致 T0/T3 的“计划可用但仍显示补充解释中”。
- raw trace、证据 fallback、医疗红旗卡片等安全表达散落在多个渲染函数里，容易出现前后口径不一致。
- CSS 缺少 token 分层，视觉修改容易靠局部 override 堆叠。

### 推荐拆分

1. `src/lib/view-models/generation-status.js`
   - 输入 API payload、skeleton/enrichment 状态、错误状态。
   - 输出唯一 `GenerationStatusViewModel`。
2. `src/lib/view-models/trust-status.js`
   - 输入 `workflow_trace`、`risk_gate`、`protocol_recheck`。
   - 输出用户化证据/协议/风险/修复标签。
3. `src/lib/view-models/evidence-items.js`
   - 严格区分真实证据、内置规则、模型知识说明。
   - 禁止无证据时生成伪编号。
4. `src/lib/view-models/feedback-result.js`
   - 独立处理 `medical_referral` 红旗卡。
   - 普通调整与红旗 fail-closed 分支互斥。
5. `src/lib/view-models/day-card.js`
   - 将日卡压缩为执行必要信息。
6. `src/styles/tokens.css`
   - 只放 primitive + semantic token。
7. `src/styles/components/*.css`
   - 拆出 calendar、modal、drawer、feedback、audit panel。

## T9 Verification Matrix

| Gate | 验收项 | 命令或步骤 |
|---|---|---|
| 生成状态 | 日历可用后主状态为“计划可用”，解释补充为次级状态，进度不回退 | 浏览器：输入完赛型 prompt -> 生成 4 周计划 -> 观察 badge/progress |
| 成绩 provenance | 未输入 PB/目标成绩时不显示推断成绩 | 浏览器：使用“目标完赛、每周跑量 25 km、最长跑 12 km、无伤病”生成 |
| medical_referral | 红旗反馈不展示 regenerate、普通计划差异、替代训练 | 浏览器：提交 chest pain/dizzy/heat illness 反馈 |
| 风险文案 | 普通 UI 不出现 raw `not_evaluated`，不与“安全通过”混淆 | `rg -n "not_evaluated|WorkflowTrace|Trace 节点|AET-" apps/web/src/pages/index.astro` 并浏览器复核 |
| 证据引用 | 无 evidence 时不显示 `#HMP-*` 伪证据 | 构造 `evidence_count=0` 响应或 skeleton-first 响应，打开证据抽屉 |
| 详情层级 | 打开训练日首屏可见主课、强度、时长、反馈入口 | 浏览器桌面 + 375px 移动截图 |
| 移动布局 | 375px 无水平滚动；抽屉打开不遮挡阅读路径 | 浏览器 viewport 375x667，保存 `mobile-drawer-open` 截图 |
| 键盘可达 | Tab 在 modal/drawer 内循环，Esc 关闭后焦点返回触发器 | 手工键盘路径：生成 -> 打开日 -> 查看证据 -> Esc -> Tab |
| HMP 术语 | HMP/容量预算/恢复窗口等 1 次点击内有定义和训练影响 | 打开关键课详情，检查术语解释入口 |
| 构建 | 前端可构建 | `cd apps/web && npm run build` |
| 契约回归 | workflow trace、feedback、frontend contract 不回退 | `C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -m pytest tests\test_astro_frontend_contract.py tests\test_api_app.py tests\test_state_models.py -q` |

## Implementation Slices

### Slice 1: 状态出口收敛

- 优先级：T0
- 文件范围：`apps/web/src/pages/index.astro`，新增 `apps/web/src/lib/view-models/generation-status.js`
- 内容：收敛 `planProgress/resultBadge/queryHint/workspaceFlow` 为一个 view model；日历 ready 后主状态不可被 enrichment/fallback 覆盖。
- 验收：生成态矩阵截图 + frontend contract 测试。

### Slice 2: 可信状态与证据分层

- 优先级：T0/T1
- 文件范围：`apps/web/src/pages/index.astro`，新增 `trust-status.js`、`evidence-items.js`
- 内容：用户化 `workflow_trace`；禁止 raw JSON；区分真实证据、协议规则、模型知识。
- 验收：无 `Trace 节点`、`WorkflowTrace`、伪 `HMP-*` 可见文案。

### Slice 3: 医疗红旗独立结果卡

- 优先级：T0
- 文件范围：`apps/web/src/pages/index.astro`，必要时同步 `apps/backend/src/marathon_qa_assistant/apps/api_app.py`
- 内容：`medical_referral` 独立 fail-closed UI，中文文案，普通调整字段互斥。
- 验收：普通反馈与红旗反馈各一张截图；红旗无 regenerate。

### Slice 4: 训练日详情重构

- 优先级：T1
- 文件范围：`buildDayModalHtml()`、modal CSS。
- 内容：三层详情结构：训练安排、依据审计、反馈调整；固定 header/footer；内容区滚动。
- 验收：桌面和 375px 下反馈入口可见或一跳可达。

### Slice 5: 日历密度与移动端主路径

- 优先级：T1
- 文件范围：`renderDayCard()`、calendar CSS、mobile drawer CSS。
- 内容：日卡只保留执行必要信息；桌面周视图、移动今日优先；移动 drawer 不覆盖阅读路径。
- 验收：1280px 一屏扫一周，375px 首屏见今日训练。

### Slice 6: 可访问性基线

- 优先级：T1/T2
- 文件范围：global focus styles、modal/drawer JS。
- 内容：全局 focus ring、focus trap、背景 inert、可访问 H1、skip link。
- 验收：键盘路径完整通过；heading outline exactly one H1。

### Slice 7: HMP 专业解释层

- 优先级：T1/T2
- 文件范围：前端术语渲染，必要时后端 `glossary_terms` payload。
- 内容：消费 glossary，关键课解释结构化，负荷表达标注代理性质。
- 验收：关键课有“练什么 / 为什么 / 如何恢复或降级”；术语口径与 `half_marathon_glossary.py` 一致。

### Slice 8: CSS token 与组件边界

- 优先级：T2/T3
- 文件范围：`apps/web/src/styles/global.css` 拆分或分层。
- 内容：primitive/semantic/component token，收敛色彩、圆角、阴影、状态 badge。
- 验收：主要控件来自同一套 token；同屏主强调色不超过 1 个。

## Agent Disagreement

- 无实质冲突。所有 agent 都收敛到同一方向：不要增加更多表层信息，先把状态、信任、安全和训练解释做成稳定 view model。
- T5 对 H1 的判断来自初始可见页面；本轮移动抽屉打开态能量测到一个 H1，但它不等价于稳定页面级标题。实现时应以 Accessibility Tree 和初始页面 heading outline 为准。
- T4 认为 expert 面板默认隐藏是合理的；T8 仍建议删除 raw trace 可见输出，因为隐藏态不应成为安全边界。

## Release Gate

当前发布门：不通过。

必须先完成：

1. `GenerationStatusViewModel`，保证计划可用态稳定。
2. 成绩/配速 provenance gate，避免伪能力评估。
3. `medical_referral` 独立 fail-closed UI。
4. `TrustStatusViewModel`，消除 raw 工程态和风险状态冲突。

完成以上四项并通过 T9 验收后，再进入视觉 token、移动布局和组件拆分的产品化迭代。

## Round 11 Card Layout Hardening

### 本轮结论

本轮按成熟产品标准补齐了证据门槛，并把卡片排版从“侧栏表单 + 管理卡片 + 日卡计算字段”推进到“轻摘要 + 详情下钻”的产品结构。重点不是换颜色，而是减少普通跑者的认知负担。

### 证据门槛

- 新增 `docs/product/mature_product_acceptance_standard.md`。
- 本轮成熟产品标准基于 16 类公开来源：ISO 9241-11、NN/g、WCAG 2.2、GOV.UK、web.dev、Material、USWDS、Apple Health、Oura、WHOOP、TrainingPeaks、Garmin、Runna、Strava、小红书等。
- 已写入共享契约：以后每轮做成熟产品/审美/信息架构结论前，必须检索 10+ 来源，并只选 Top 3 迁移。

### 已完成修复

- 侧栏只保留跑者情况摘要，不再塞完整画像表单、强度表或 `来自 API`。
- 完整画像编辑进入 `profileEditorDialog`。
- 历史计划默认显示最近 2 条轻列表，删除入口只在展开后出现。
- 周卡普通层改为 `本周训练压力 稳定/较高/待估`，不展示计算数字。
- 日卡外层只保留日期、训练名、时长/区间、压力、安全自检和 `查看安排`。
- 清理本周关键课和时间设置的大面积深灰后台块。

### 视觉证据

- `artifacts/frontend-audit/round11-card-layout-desktop-2026-05-22.png`
- `artifacts/frontend-audit/round11-card-layout-mobile-2026-05-22.png`
- `artifacts/frontend-audit/round11-card-layout-mobile-drawer-2026-05-22.png`
- 状态 JSON 显示：桌面日卡 7 张，最小宽度 263px；移动端无横向溢出；可见普通层无 `来自 API`、`计划画像`、`周代理负荷 512`、`查看详情`、`generation_status`、`workflow_trace`。

### 验证

- `C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -m pytest -p no:cacheprovider tests\test_astro_frontend_contract.py -q`：66 passed。
- `cd apps/web; npm run build`：passed。
- `WORKSPACE_URL=http://127.0.0.1:4325/#workspace npm run smoke:workspace`：passed。第一次在构建同时运行出现移动端瞬时失败，随后 DOM 诊断正常并重跑通过。

### 仍未签收

- 首屏顶部在 full-page 截图中仍有轻微 sticky nav 覆盖感。
- 结果摘要仍偏长，下一轮应继续压缩成更明确的“今日怎么练 / 本周重点 / 反馈入口”。
- 本轮不替 backend、QA/reviewer 签收最终商用完成。

## Round 12 Reading Fatigue Reduction

### 本轮问题

用户明确指出：作为真实用户，不会愿意在计划生成后持续往下滑很多页面。本轮把“阅读疲劳”作为独立产品问题处理，不再只做视觉美化。

### 证据门槛

本轮检索并记录 10+ 公开来源，见 `docs/product/reading_fatigue_reduction_todo.md`。核心来源包括：

- NN/g Progressive Disclosure、F-shaped Pattern、How Users Read on the Web、Minimize Cognitive Load。
- W3C COGA Making Content Usable。
- GOV.UK Writing for GOV.UK / Content Design。
- Material Cards/Lists、Apple HIG、Fluent、Baymard、TrainingPeaks、Apple Health 等公开资料。

### Top 3 迁移结论

1. **渐进披露**：长解释、证据、协议、trace 和计算细节默认下沉，普通层只保留结果和行动。
2. **任务优先首屏**：生成后优先看训练日历、下一次训练、本周重点、安全提醒和反馈入口。
3. **中文跑者任务语言**：避免 raw 英文变量、工程状态和后台字段；普通层用“今天怎么练 / 本周安排 / 为什么这样练 / 记录反馈”。

### 已完成修复

- `report-panel` 改为默认折叠 `details`，标题从结果报告感更强的“结果摘要”改为“为什么这样安排”。
- 新增 `data-reading-fatigue-guard` 和 `data-secondary-reading-layer`，把长解释定义为二级阅读层。
- 视觉顺序把训练日历放在二级报告之前，让用户先进入训练执行路径。
- `calendarActionPanel` 从四张并列大卡改为“一张下一次训练主卡 + 本周重点/安全提醒/反馈入口三条短摘要”。
- 周视图默认不再展开第一周 7 张日卡，用户需要查看整周时再展开。
- `dayModal` 默认 tab 先显示时长、强度、安全和热身/主课/冷身；可信状态、产品状态、负荷指标和审计信息移动到“训练依据”tab。
- 反馈 tab 改为 quick-first：默认只显示“完成 / 部分 / 跳过/不适”、选中摘要、提交反馈和生成调整建议；疲劳、睡眠、疼痛、红旗和补充说明进入默认折叠的“补充细节”。
- 按高级感配色原则修正浅色商业主题的反馈区对比：普通文本使用清晰深灰，说明/详情区使用白底和浅边框，主行动色保留少量高亮，不再用低对比灰块伪装“高级”。

### 验证结果

- `node --check apps/web/src/scripts/app.js` 通过。
- `C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -m pytest -p no:cacheprovider tests\test_astro_frontend_contract.py -q`：67 passed。
- `npm run build` in `apps/web`：通过。
- `WORKSPACE_URL=http://127.0.0.1:4342/#workspace npm run smoke:workspace`：通过。
- 反馈 quick-first 截图：`artifacts/frontend-audit/round12-feedback-quick-first-desktop-2026-05-22.png`、`artifacts/frontend-audit/round12-feedback-quick-first-mobile-2026-05-22.png`。
- 反馈 quick-first 状态 JSON：桌面/移动均 `quickFirst=true`、`detailOpen=false`、`quickButtonCount=3`、`pressedCount=1`、`submitVisible=true`、`redFlagCount=5`、`horizontalOverflow=false`、`consoleMessages=[]`。
- 对比度量测：`已选择` 文本 10.35:1，`补充细节` 标题 17.74:1，超过 WCAG AA 普通文本门槛。
- modal polish 复核：`WORKSPACE_URL=http://127.0.0.1:4343/#workspace npm run smoke:workspace` 通过；截图 `artifacts/frontend-audit/round12-modal-polish-*.png`、`artifacts/frontend-audit/round12-modal-scroll-fix-*.png`。
- modal polish 状态 JSON：移动端 `modalBottomGap=0`、`modalBorderRadius=18px 18px 0px 0px`、`modalScrollTop=0`、`titleVisible=true`；桌面/移动均 `horizontalOverflow=false`、`consoleMessages=[]`。
- 普通层文案守卫：`WORKSPACE_URL=http://127.0.0.1:4344/#workspace npm run smoke:workspace` 通过；截图 `artifacts/frontend-audit/round12-copy-guard-desktop-2026-05-22.png`、`artifacts/frontend-audit/round12-copy-guard-mobile-2026-05-22.png`。
- 普通层文案状态 JSON：桌面/移动均 `visibleForbidden=[]`、`title=马拉松训练助手`、`workspaceHeading=训练日历`、`modePill=跑者视图`、`horizontalOverflow=false`、`consoleMessages=[]`。

### 仍未签收

- 红旗反馈路径仍需单独截图签收，确认 `medical_referral` 不展示普通 regenerate。
- OpenAI/DeepSeek/API Key 等专家设置文案仍保留在高级配置入口，不作为普通训练结果层展示。
- 本轮不替 Backend owner、QA/reviewer 签收最终商用完成。
