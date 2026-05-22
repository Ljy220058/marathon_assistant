# Frontend Product Audit TODO

> 目的：把马拉松助手前端从“功能可用”审计到“可信、专业、可长期使用的训练产品”。
> 当前根目录已有 `TODO.md` 总索引；本文件作为前端产品审核专用 todo.md，避免和总索引混放。
> 执行状态：T0-T9 只读审计已完成，汇总报告见 `docs/product/reports/frontend_product_audit_2026-05-22.md`。本文件定义的是审计任务，不表示 UI 修复已完成。

## Round 10 Frontend Owner Overlay - 白底轻导航商用化修复

- [x] 当前角色：Frontend owner；只代表 Astro 前端、普通用户信息架构、移动端体验、浏览器验证和商用审美迁移，不替 Backend owner 或 QA/reviewer 签最终完成。
- [x] 本轮已读共享契约：`docs/quality/shared_delivery_contract.md`。
- [x] 本轮子智能体计数：1/1，只读设计与审美 reviewer `019e4e53-d09f-7863-bbdc-39bb13da1662`，已关闭。
- [x] 本轮审美证据：用户提供小红书/YouTube 截图偏好；本地归档 Nike/COROS/Runna/Oura 截图；子 agent 只读 review 明确白底、顶部搜索、左侧轻导航、卡片流和小面积科技高光为可迁移方向。
- [x] T0 修复：新增 `apps/web/src/styles/commercial-light.css`，最后加载，压住深色控制台背景、霓虹大面积渐变和暗色输入框。
- [x] T0 修复：`apps/web/src/styles/global.css` 最后引入 `commercial-light.css`，保证浅色商用覆盖优先级稳定。
- [x] T0 修复：顶部新增中文搜索入口 `搜索训练、计划、依据`，迁移小红书/YouTube 的轻搜索，不迁移社交推荐流。
- [x] T0 修复：桌面侧栏初始化默认展开，形成左侧轻导航；移动端默认收起，不和底部快捷导航争抢主路径。
- [x] T0 修复：移动端从两栏错误回到单栏，主卡宽度从 220px 恢复到 366px；悬浮抽屉按钮从内容底部移到顶部空白区。
- [x] T0 修复：普通层移除可见快捷键提示，改为 `准备好后生成训练日历`。
- [x] T0 修复：普通层继续禁止 raw 英文/变量字段：`workflow_trace`、`trace_version`、`legacy_missing`、`risk_gate`、`generation_status`、`Half marathon finish` 等截图状态均不可见。
- [x] T1 修复：`apps/web/scripts/smoke-workspace.mjs` 兼容桌面侧栏默认展开；只在抽屉未打开时点击 toggle。
- [x] T1 视觉约束：主界面仍保持训练工作台，不做营销 hero；科技高光只用于 CTA、当前步骤、状态点。
- [x] T1 视觉约束：不迁移小红书点赞评论、瀑布流娱乐推荐、品牌红大面积占用。
- [x] T1 移动验收：390px 无横向溢出；底部四项导航不与抽屉按钮相交；主 CTA 全宽可点击。
- [x] T1 桌面验收：1440px 白底、顶部搜索可见、左侧导航常驻、主 CTA 可见、无横向溢出。
- [x] T1 截图证据：`artifacts/frontend-audit/round10-commercial-light-desktop-2026-05-22.png`。
- [x] T1 截图证据：`artifacts/frontend-audit/round10-commercial-light-mobile-2026-05-22.png`。
- [x] T1 截图证据：`artifacts/frontend-audit/round10-commercial-light-mobile-drawer-2026-05-22.png`。
- [x] T1 状态证据：`artifacts/frontend-audit/round10-commercial-light-desktop-state-2026-05-22.json`。
- [x] T1 状态证据：`artifacts/frontend-audit/round10-commercial-light-mobile-state-2026-05-22.json`。
- [x] 验证：`C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -m pytest -p no:cacheprovider tests\test_astro_frontend_contract.py -q`，66 passed。
- [x] 验证：`cd apps/web; npm run build` 通过。
- [x] 验证：`WORKSPACE_URL=http://127.0.0.1:4331/#workspace npm run smoke:workspace` 通过。
- [x] 验证：`git diff --check` 通过。
- [ ] T1 待继续：生成后桌面/移动截图仍需补充，尤其是周卡、日卡、依据抽屉和反馈结果，不可只验空态。
- [ ] T1 待继续：普通层仍需继续减少“训练日历生成器/普通模式”等工程感命名，优先改成“今日训练 / 本周计划 / 我的情况 / 为什么这样练”。
- [ ] T1 待继续：移动端详情仍需评估 bottom sheet 或 lighter peek，避免日卡详情像后台 modal。
- [ ] T2 待继续：CSS token 仍需从覆盖层继续沉淀到 base/components，减少同义颜色和局部 hardcoded rgba。
- [ ] 退出条件：未达到。Backend owner、QA/reviewer 和前端生成态截图仍未共同签收“没有值得继续修的问题”。

## Round 5 Frontend Owner Overlay - 商用审美迁移与普通模式降噪

- [x] 当前角色：Frontend owner；只代表 Astro 工作台、日历/日卡、反馈 UI、状态面板、浏览器 smoke 与普通模式信息架构，不替 Backend owner 或 QA/reviewer 签收。
- [x] 本轮已读共享契约：`docs/quality/shared_delivery_contract.md`。
- [x] 本轮已读 hardening 手册：`docs/quality/release_hardening_loop.md`。
- [x] 本轮子智能体计数：2/2，已关闭 Dalton 与 Hume；后续继续本轮前不得再开第三个 agent。
- [x] 外部证据规则：只使用官方文档、应用商店页面、公开可复查页面或本地截图；无证据结论标为“待验证假设”。
- [x] Linear 证据：Display options 允许按视图控制布局、分组、排序和显示属性；迁移为“不同视图控制不同字段可见性”，不迁移项目管理复杂 swimlane。来源：https://linear.app/docs/display-options
- [x] Stripe 证据：Dashboard Home 汇总业务表现与重要通知，Workbench/日志属于监控与调试；迁移为“普通首页只展示结果与通知，专家入口看日志”。来源：https://docs.stripe.com/dashboard/basics
- [x] Notion 证据：每个 database view 有自己的设置，可控制 layout、property visibility、filter、sort、group，页面打开可 side peek/center peek；迁移为“详情层分区和字段可见性”。来源：https://www.notion.com/help/views-filters-and-sorts
- [x] TrainingPeaks 证据：Home 看事件/目标/当前状态/即将训练，Dashboard 看趋势；日历 layout 支持少放数据以节省空间。来源：https://help.trainingpeaks.com/hc/en-us/articles/231472468-TrainingPeaks-Athlete-User-Guide
- [x] WHOOP 证据：把生理洞察压成 daily action，但依赖 wearable 和 HRV/RHR/respiratory/sleep 等数据；迁移“行动导向”，不迁移恢复分/strain 分。来源：https://apps.apple.com/us/app/whoop/id933944389
- [x] Oura 证据：Readiness 来自多项个人长期基线 contributor；迁移“趋势和 contributor 解释层”，不迁移准备度评分。来源：https://support.ouraring.com/hc/en-us/articles/360057791533-Readiness-Contributors
- [x] 当前本地证据：已有 `artifacts/frontend-audit/dashboard-current.png`、`day-modal-current.png`、`mobile-layout-state-2026-05-22.json`，后续每轮必须继续补截图。
- [x] T0 修复：普通导航健康状态默认隐藏，只在后端离线或需要用户行动时显示。
- [x] T0 修复：生成进度 pill 从百分比改为“等待/生成中/可查看/已完成/失败”等产品状态。
- [x] T0 修复：7 步内部流水线保留在专家层，不在普通模式打扰用户。
- [x] T0 修复：日历统计 strip、负荷曲线、7 日/42 日占比默认进入专家层。
- [x] T0 修复：日卡默认只保留训练类型、时长/距离、强度/训练压力、安全状态和详情入口。
- [x] T0 修复：反馈结果把 `risk_gate/protocol_recheck/generation_status` 翻译为“安全判断/是否继续/建议动作”。
- [x] T0 修复：无反馈时调整历史不占位；有反馈时再展示调整记录。
- [x] T0 修复：状态面板不在空态占位；有计划或反馈后才显示本周执行概览。
- [x] T0 待验证：普通模式 DOM 截图中不可见 `workflow_trace`、`trace_version`、`feedback_id`、`risk_gate`、`protocol_recheck`、`generation_status` raw label。证据：`artifacts/frontend-audit/round5-normal-mode-state-2026-05-22.json`。
- [x] T0 已验证：医疗红旗勾选后，本地立即进入安全阻断语义，提交按钮变为“提交安全反馈”，不展示普通 regenerate。证据：`artifacts/frontend-audit/round6-medical-red-flag-feedback-2026-05-22.png`。
- [x] T0 待验证：移动端首屏只保留一个主导航模式，不出现 drawer 入口、bottom nav、sticky header 互相竞争。证据：`artifacts/frontend-audit/round5-mobile-idle-2026-05-22.png` 与 `npm run smoke:workspace`。
- [ ] T1 待修：建立单一专家面板入口，让 token/cost、timings、request id、workflow_trace、load factors、protocol issues 都从同一个入口查看。
- [x] T1 已修：日历默认周视图顶部新增普通层行动摘要面板，优先显示“下一次训练 / 本周重点 / 安全提醒 / 反馈入口”。证据：`artifacts/frontend-audit/round6-action-panel-real-desktop-final-2026-05-22.png`。
- [x] T1 已修：行动摘要面板的“记录反馈”会直接打开日卡反馈区，详情 modal 底部仍保留固定反馈入口。证据：`artifacts/frontend-audit/round6-medical-red-flag-feedback-2026-05-22.png`。
- [ ] T1 待修：移动端详情从 full modal 评估是否改为 bottom sheet 或更轻的 peek，但必须先截图验证。
- [ ] T1 待修：普通模式不展示 `计划总负荷分` 等计算字段；只展示低/中/高训练压力和“计划代理”边界。
- [ ] T2 待修：设计 token 继续收敛，减少局部 rgba 和多重渐变堆叠。
- [ ] T2 待修：保留训练产品的克制、专业、可扫描，不做营销式 hero。
- [ ] T2 待修：补完整截图矩阵：空态、生成中、计划可用、解释失败、缺证据、医疗红旗、反馈调整、移动端。
- [ ] T2 待修：补前端 smoke 覆盖结构化红旗 checkbox、本地 fail-closed、保存上下文缺失提示。
- [ ] Tn 待调研：Runna 导航与计划页官方截图需要继续归档；未截图前只作为待验证参考。
- [ ] Tn 待调研：Garmin Connect/Strava 应用商店截图可辅助视觉密度判断，但不能迁移设备指标语义。

## Round 6 Frontend Owner Overlay - 跨行业高端商用审美迁移学习

- [x] 当前角色：Frontend owner；只代表 Astro 前端、普通用户信息架构、移动端体验、浏览器验证和商用审美迁移，不替 Backend owner 或 QA/reviewer 签收。
- [x] 本轮已读共享契约：`docs/quality/shared_delivery_contract.md`。
- [x] 本轮已读 hardening 手册：`docs/quality/release_hardening_loop.md`。
- [x] 本轮新增用户要求：前端 owner 负责调 agent 看高端商用 app 的审美并做迁移学习；不局限马拉松，可以是任何成熟商用产品。
- [x] 本轮子智能体计数：2/2，Hilbert 与 Herschel 均为只读审美/产品体验研究，均已返回并关闭；本轮未开启第三个 agent。
- [x] Hilbert 范围：Linear、Stripe、Notion、Figma、Apple、Mercury/Ramp/Attio/Superhuman/Arc 等生产力、金融、设计、系统级产品的公开证据。
- [x] Herschel 范围：WHOOP、Oura、Runna、TrainingPeaks、Strava、Garmin Connect、Nike Run Club、Headspace/Calm、Eight Sleep 等健康、训练、可穿戴、习惯类产品的公开证据。
- [x] 证据规则：只使用官方 docs、官网、App Store/公开截图、帮助中心、本地浏览器截图或明确“待验证假设”；禁止用“高端 app 都这样”当论据。
- [x] 迁移边界：只迁移信息层级、字段可见性、状态表达、交互节奏、视觉密度、可信解释和安全文案，不迁移品牌资产、设备真实指标语义或没有本项目数据支撑的恢复分/准备度分。
- [x] T0 已汇总：两个只读 agent 的证据表已追加到 `docs/product/reports/frontend_product_audit_2026-05-22.md`，每条迁移建议标注来源链接和不可迁移边界。
- [x] T0 已汇总：已把“高端商用审美迁移学习”写入 `docs/quality/shared_delivery_contract.md` 的前端 owner 固定职责。
- [x] T0 已汇总：已把“跨行业高端 app 证据四列法”写入 `docs/quality/release_hardening_loop.md` 的每轮步骤。
- [ ] T1 待拆解：把生产力/金融类 app 的“普通层只展示结果和行动、日志进入专家层”映射到当前导航、状态面板、日卡和反馈结果。
- [x] T1 已拆解并部分落地：训练日历已新增普通层行动摘要面板，映射 Runna/Garmin 的“下一次训练 / 本周重点 / 安全提醒 / 反馈入口”范式；EvidenceDrawer contributor 仍待继续。
- [ ] T1 待拆解：把 Apple/Material 类系统设计原则转译为本项目的文字密度、按钮层级、焦点状态、错误/警告/成功色职责，而不是照搬视觉表皮。
- [x] T2 已验证：行动摘要面板加入后，普通层没有 `workflow_trace/risk_gate/protocol_recheck/generation_status/trace_version` raw 字段，也没有 `画像=/候选课表=/HMP协议=` 内部片段。证据：`artifacts/frontend-audit/round6-action-panel-real-desktop-final-2026-05-22.png`。
- [x] T2 已验证：桌面和 375px 移动端行动摘要面板、日卡和反馈入口可见，移动端无横向溢出。证据：`artifacts/frontend-audit/round6-action-panel-mobile-mocked-final-2026-05-22.png`。
- [ ] Tn 待归档：未能找到公开资料的产品只能留在“待验证假设”，不得进入修复依据。

## Audit Context

- 工作目录：`C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手`
- 前端入口：`apps/web/src/pages/index.astro`
- 样式入口：`apps/web/src/styles/global.css`
- 当前本地页面：`http://127.0.0.1:4321/`
- 当前本地 API：`http://127.0.0.1:8010/`
- 浏览器证据目录：`artifacts/frontend-audit/`
- 审计阶段约束：只读审计，不改代码；每个 agent 输出 evidence-backed findings 和可执行 TODO。

## Priority Rules

- `T0`：阻断可用性、可信度或安全理解的问题。进入产品化修复前必须先处理。
- `T1`：强影响核心体验的问题。影响首次使用、计划理解、用户信任或主要路径效率。
- `T2`：中等影响的体验和维护问题。会造成认知负担、视觉噪声或长期迭代成本。
- `T3`：增强项。用于提升精致度、品牌感、可扩展性和细节一致性。

每个 TODO 必须包含：`证据`、`用户影响`、`建议修复`、`验收方式`。

## Agent Assignment Matrix

| Task | Agent | Scope | Output |
|---|---|---|---|
| T0 | Product Readiness Lead | 审计全局可用性、首屏路径、是否像可交付产品 | T0 blocker list + release gate |
| T1 | Visual Design Agent | 美观度、色彩、对比、视觉层级、品牌感 | 视觉设计 TODO |
| T2 | Information Architecture Agent | 信息结构、页面叙事、训练计划可理解性 | 信息架构 TODO |
| T3 | Interaction UX Agent | 生成、日历、详情、反馈、恢复审计的操作路径 | 交互简化 TODO |
| T4 | Trust & Safety Agent | medical_referral、risk_gate、evidence、workflow_trace 的可信表达 | 安全可信 TODO |
| T5 | Accessibility Agent | 键盘、焦点、语义、对比度、可读性 | WCAG 风险 TODO |
| T6 | Responsive Layout Agent | 桌面/移动布局、溢出、遮挡、密度 | 响应式 TODO |
| T7 | Training Domain Agent | 训练专业度、HMP 术语、计划解释、负荷表达 | 专业内容 TODO |
| T8 | Frontend Architecture Agent | `index.astro`/`global.css` 复杂度、组件边界、状态耦合 | 可维护性 TODO |
| T9 | Verification Agent | 把所有 findings 转成可验收检查清单 | 验收矩阵 |

## T0 - Product Readiness Gate

Agent: Product Readiness Lead

- [ ] 检查首屏是否能让新用户在 10 秒内理解“下一步做什么”。
  - 证据：首屏截图、可见 CTA、用户路径。
  - 用户影响：不清楚先填画像还是直接生成，会降低首次完成率。
  - 建议修复：明确主路径，只保留一个 primary CTA，次要动作降级。
  - 验收方式：首屏无需滚动即可看到目标、输入、主按钮、服务状态。
- [ ] 检查生成后是否有稳定的“结果完成”状态，而不是一直停留在“补充解释中”。
  - 证据：生成 4 周计划后页面状态、进度条、result badge。
  - 用户影响：用户不知道计划是否已经可用，容易重复点击或误判失败。
  - 建议修复：区分 `skeleton_ready`、`calendar_ready`、`explanation_pending`、`complete`。
  - 验收方式：日历可用时明确显示“计划可用”，异步补充解释只作为次级状态。
- [ ] 检查页面是否存在阻断理解的乱码、异常文本或不完整文案。
  - 证据：DOM 文本、截图、控制台。
  - 用户影响：乱码会直接损害专业可信度。
  - 建议修复：统一文件编码、文案源和渲染转义策略。
  - 验收方式：关键 UI 文案在浏览器、测试输出、日志中均无乱码。

## T1 - Visual Design And Brand

Agent: Visual Design Agent

- [ ] 审计当前深色 UI 是否过于单一、发灰或高亮过多。
  - 证据：`dashboard-current.png`、`day-modal-current.png`、CSS 色值。
  - 用户影响：页面信息多时缺少层级，用户会疲劳。
  - 建议修复：建立语义色阶：surface、panel、accent、success、warning、danger、muted。
  - 验收方式：同一屏内只保留 1 个主色强调，状态色仅用于真实状态。
- [ ] 审计按钮、标签、卡片、弹窗的圆角、阴影、边框是否统一。
  - 证据：CSS token、截图对比。
  - 用户影响：组件像临时拼装，降低产品成熟感。
  - 建议修复：定义组件 token：radius、border、shadow、focus ring、badge。
  - 验收方式：主要控件使用同一套视觉参数，不靠局部 override。
- [ ] 审计训练日卡片的可扫读性。
  - 证据：周视图截图，单卡文字密度。
  - 用户影响：卡片同时承载时间、强度、负荷、可信状态、证据，容易压迫。
  - 建议修复：卡片只保留行动信息，证据/负荷细节折叠到详情层。
  - 验收方式：卡片 3 秒内可读出“今天练什么、多久、强度、是否可执行”。

## T2 - Information Architecture

Agent: Information Architecture Agent

- [ ] 审计页面主叙事是否从“生成计划”自然过渡到“执行与反馈”。
  - 证据：导航、状态面板、日历、反馈入口顺序。
  - 用户影响：用户可能把它当一次性计划生成器，而不是训练闭环工具。
  - 建议修复：形成三层信息结构：Plan Builder、Training Calendar、Execution Loop。
  - 验收方式：每层有清晰标题、当前状态、下一步动作。
- [ ] 审计训练负荷、执行状态、证据依据是否抢占主要任务。
  - 证据：生成后页面首屏。
  - 用户影响：专业信息过早出现会压倒“今天怎么练”的核心任务。
  - 建议修复：默认展示日历和今日/本周重点，高级审计信息进入折叠区。
  - 验收方式：普通用户路径不需要先理解 `workflow_trace` 或代理负荷算法。
- [ ] 审计“依据/审计/专业解释”的入口命名是否清楚。
  - 证据：侧边导航、详情 modal、证据按钮。
  - 用户影响：可信信息存在但用户不知道何时需要看。
  - 建议修复：把依据分为“为什么这样练”“安全校验”“证据来源”三类。
  - 验收方式：训练日详情里三类依据各自独立且不重复。

## T3 - Interaction Simplicity

Agent: Interaction UX Agent

- [ ] 审计生成流程是否有过多并行状态。
  - 证据：进度条、结果 badge、query hint、日历状态。
  - 用户影响：同一时间多个状态文本可能相互矛盾。
  - 建议修复：建立单一 `generation_status` 展示源，其他区域只引用该状态。
  - 验收方式：任何生成阶段只有一个主状态、一个辅助说明、一个可用动作。
- [ ] 审计训练日详情 modal 的层级和关闭/返回体验。
  - 证据：modal 截图、按钮顺序、焦点行为。
  - 用户影响：详情信息过多，用户容易迷失。
  - 建议修复：modal 分 tabs：训练安排、依据审计、反馈调整。
  - 验收方式：打开详情默认显示训练安排；审计和反馈不打断阅读。
- [ ] 审计反馈路径是否避免 medical_referral 下的普通 regenerate。
  - 证据：`isMedicalReferralFeedback()`、反馈结果 UI。
  - 用户影响：医疗红旗下展示普通调整会造成安全风险。
  - 建议修复：medical_referral 只显示停止训练和专业评估路径。
  - 验收方式：红旗反馈后无普通“生成调整版计划”入口。

## T4 - Trust, Evidence, And Safety

Agent: Trust & Safety Agent

- [ ] 审计 `workflow_trace` 是否以用户可理解语言呈现，而非工程字段堆叠。
  - 证据：训练日详情审计块。
  - 用户影响：用户看到工程词会以为系统不成熟，或误解审计结果。
  - 建议修复：把 trace 映射为“证据状态、协议状态、风险状态、修复状态”。
  - 验收方式：默认不暴露 raw JSON，不出现 raw chain-of-thought。
- [ ] 审计证据引用是否避免伪造来源。
  - 证据：无证据场景、KB fallback 场景、证据 drawer。
  - 用户影响：伪引用会严重破坏可信度。
  - 建议修复：无外部证据时明确显示“模型知识说明，不能作为核心处方依据”。
  - 验收方式：`evidence_state.status=missing_or_partial` 时不显示伪编号。
- [ ] 审计 HMP 协议、安全约束、容量预算是否能被普通跑者理解。
  - 证据：HMP panel、训练日详情、术语解释。
  - 用户影响：专业度高但不解释，会变成黑箱。
  - 建议修复：术语旁提供短解释和来源链接。
  - 验收方式：关键术语 1 次点击可看到解释、影响和来源。

## T5 - Accessibility And Readability

Agent: Accessibility Agent

- [ ] 检查文本对比度、状态 badge 对比度和按钮对比度。
  - 证据：CSS 色值、浏览器截图。
  - 用户影响：深色界面里灰字和细边框可能不可读。
  - 建议修复：按 WCAG AA 调整 normal text 4.5:1、UI indicator 3:1。
  - 验收方式：核心文本、次级文本、按钮、badge 全部通过对比检查。
- [ ] 检查键盘可达性和焦点可见性。
  - 证据：Tab 顺序、modal 打开后焦点、Escape 关闭。
  - 用户影响：键盘用户无法完成计划生成和反馈。
  - 建议修复：modal focus trap、关闭后恢复焦点、所有 icon button 有 aria-label。
  - 验收方式：只用键盘可以生成、打开详情、提交反馈、关闭弹窗。
- [ ] 检查字号、行高、按钮文字是否在移动端溢出。
  - 证据：移动宽度截图。
  - 用户影响：中文长词和专业术语容易挤压布局。
  - 建议修复：限制按钮文案长度，必要时换行或图标化。
  - 验收方式：375px 宽度无水平滚动、无文字重叠。

## T6 - Responsive Layout

Agent: Responsive Layout Agent

- [ ] 审计侧边导航在移动端是否遮挡主内容。
  - 证据：移动截图。
  - 用户影响：浮层导航占据视觉中心，日历阅读被打断。
  - 建议修复：移动端改为底部工具栏或可收起 drawer，默认不覆盖内容。
  - 验收方式：移动端打开日历时，主内容完整可读。
- [ ] 审计日历卡片网格在桌面和移动端的密度。
  - 证据：周视图/全部视图截图。
  - 用户影响：桌面过密、移动过长都会降低执行效率。
  - 建议修复：桌面使用周分组密集表格，移动使用今日优先列表。
  - 验收方式：桌面一屏能扫一周，移动首屏能看到今日训练和下一步。
- [ ] 检查 modal 高度、滚动、固定按钮区。
  - 证据：day modal 截图。
  - 用户影响：反馈按钮和详情内容混在长滚动中，不易操作。
  - 建议修复：modal header/footer 固定，内容区滚动。
  - 验收方式：任何高度下关闭、反馈、查看证据入口可见或易达。

## T7 - Training Professionalism

Agent: Training Domain Agent

- [ ] 审计计划专业度是否能解释“为什么是这个强度和距离”。
  - 证据：训练日详情、HMP 协议字段、负荷曲线。
  - 用户影响：用户可能只看到课表，不知道系统是否懂训练周期。
  - 建议修复：每周显示阶段目标、关键课目的、恢复安排理由。
  - 验收方式：每周至少有 1 条阶段解释，每个关键课有训练目的。
- [ ] 审计风险语言是否保守且一致。
  - 证据：疼痛、疲劳、医疗红旗反馈路径。
  - 用户影响：过度自信会造成训练安全风险。
  - 建议修复：疼痛/胸痛/头晕/热病均 fail-closed，文案避免“保证恢复”等绝对表达。
  - 验收方式：所有风险分支与 `risk_gate.product_status` 一致。
- [ ] 审计专业术语是否统一使用 HMP glossary。
  - 证据：卡片、modal、协议面板、反馈结果。
  - 用户影响：同一概念多种说法会降低专业感。
  - 建议修复：术语从 `half_marathon_glossary.py` 和协议文档统一映射。
  - 验收方式：UI、解释、测试中同一术语只有一个主名称。

## T8 - Frontend Architecture And Maintainability

Agent: Frontend Architecture Agent

- [ ] 审计 `index.astro` 是否承担过多 UI、状态、渲染、API、业务逻辑。
  - 证据：文件行数、函数分布、状态对象。
  - 用户影响：新增功能容易互相影响，回归风险高。
  - 建议修复：按 feature 拆分：plan builder、calendar、day modal、feedback、audit panel。
  - 验收方式：入口页面只负责装配，核心渲染逻辑进入独立模块。
- [ ] 审计 `global.css` 是否缺少 token 分层。
  - 证据：硬编码颜色、重复 class、局部 override。
  - 用户影响：视觉一致性靠复制，后续改主题成本高。
  - 建议修复：建立 `:root` 设计 token 和组件 token。
  - 验收方式：主色、surface、text、border、radius、shadow 均有单一来源。
- [ ] 审计前端契约是否依赖字符串搜索而不是结构化 schema。
  - 证据：测试和渲染函数。
  - 用户影响：字段漂移时 UI 静默降级或显示错误。
  - 建议修复：抽取 `workflow_trace`、calendar day、feedback result 的前端 contract helpers。
  - 验收方式：核心渲染函数只接受规范化后的 view model。

## T9 - Verification And Acceptance Matrix

Agent: Verification Agent

- [ ] 为每个 T 产出验收命令或手工检查项。
  - 证据：测试命令、截图路径、浏览器步骤。
  - 用户影响：没有验收标准会让 UI 改动变成主观争论。
  - 建议修复：每个 TODO 必须配一个 objective gate。
  - 验收方式：TODO 可直接转 issue 或分派给实现 agent。
- [ ] 建立桌面/移动截图基线。
  - 证据：`artifacts/frontend-audit/*.png`。
  - 用户影响：没有视觉基线就无法判断改动是否变好。
  - 建议修复：每次 UI 审计保存 dashboard、day modal、feedback、medical_referral 四类截图。
  - 验收方式：每次审计报告引用具体截图。
- [ ] 建立最小产品可用性脚本。
  - 证据：浏览器步骤。
  - 用户影响：只跑单元测试不能证明产品可用。
  - 建议修复：固定脚本：打开页面 -> health -> 生成计划 -> 打开训练日 -> 提交普通反馈 -> 提交医疗红旗反馈。
  - 验收方式：脚本通过且无 console error。

## Subagent Output Template

每个 agent 必须按下面格式返回：

```markdown
## Agent: <name>

### Summary
- 结论：<一句话>
- 最大风险：<一句话>

### Findings
- [Tn][severity] <标题>
  - 证据：<截图/文件/DOM/交互步骤>
  - 用户影响：<影响>
  - 建议修复：<具体做法>
  - 验收方式：<如何判断完成>

### Top 3 TODO
1. <最应该立刻做的任务>
2. <第二任务>
3. <第三任务>
```

## Final Audit Deliverable

主 agent 汇总时输出：

- `T0 blockers`：必须先修。
- `T1 product experience`：核心体验改进。
- `T2 quality backlog`：可分批实现。
- `T3 polish`：精修项。
- `Agent disagreement`：不同 agent 对同一问题的冲突意见。
- `Implementation slices`：每个 slice 的推荐文件范围、测试和验收截图。

## Round 1 Executable Checklist - Shared Contract Edition

本节是第 1 轮落地后的可执行审计清单。每个子任务都可单独分派给 agent；后续轮次必须先读取 `docs/quality/shared_delivery_contract.md`，再执行对应检查。

- [x] R1-A001 读取共享交付契约并确认前端真实入口。
  - 验收：确认入口为 `apps/web/src/pages/index.astro`。
  - 证据：`docs/quality/shared_delivery_contract.md` 第 2、7 节。
  - Owner：Frontend reviewer。
  - 状态：已纳入固定轮次。
- [x] R1-A002 审计 `POST /query` 前端依赖字段。
  - 验收：`workflow_trace`、`daily_schedule_cards`、`monthly_training_calendar` 均在前端契约测试中出现。
  - 证据：`tests/test_astro_frontend_contract.py`。
  - Owner：Contract reviewer。
  - 状态：已加固。
- [x] R1-A003 审计 `POST /feedback` 前端依赖字段。
  - 验收：风险门、协议复核、反馈 ID、计划差异均可渲染且 medical 分支 fail-closed。
  - 证据：`tests/test_api_app.py`、`apps/web/src/scripts/app.js`。
  - Owner：Frontend + backend readonly reviewer。
  - 状态：已加固。
- [x] R1-A004 审计普通模式是否暴露专家设置。
  - 验收：普通页面不显示 API、Token、FastAPI、Generation Trace。
  - 证据：`npm run smoke:workspace`。
  - Owner：Frontend reviewer。
  - 状态：已通过。
- [x] R1-A005 审计 DeepSeek key 是否持久化。
  - 验收：页面启动清理旧 key，浏览器 smoke 中 localStorage 不保存 `marathon_ds_api_key`。
  - 证据：`round1-browser-smoke.json`。
  - Owner：Security reviewer。
  - 状态：已通过。
- [x] R1-A006 审计生成状态是否会回退。
  - 验收：新请求先 `resetPlanProgress()`，旧计划的 `planReady` 不污染新 run。
  - 证据：`runQuery()`。
  - Owner：State reviewer。
  - 状态：已修复。
- [x] R1-A007 审计“补充解释中”是否覆盖主完成态。
  - 验收：计划骨架可用后主 badge 为“计划可用”。
  - 证据：`buildGenerationStatusViewModel()`。
  - Owner：Product UX reviewer。
  - 状态：已修复。
- [x] R1-A008 审计成绩校准是否把泛化 goal 当成绩来源。
  - 验收：`hasTargetSource` 不接受裸 `goal`。
  - 证据：`renderPerformanceCalibration()`。
  - Owner：Trust reviewer。
  - 状态：已修复。
- [x] R1-A009 审计无成绩来源时是否伪展示 PB。
  - 验收：无 current/target 来源时显示 warning card，不展示推断 PB。
  - 证据：契约测试 performance renderer。
  - Owner：Product reviewer。
  - 状态：已修复。
- [x] R1-A010 审计单边成绩来源时是否展示能力差距。
  - 验收：缺 current 或 target 时能力差距显示待补，不显示推算 gap。
  - 证据：`hasCalibrationPair`。
  - Owner：Training domain reviewer。
  - 状态：已修复。
- [x] R1-A011 审计 medical referral 是否消费普通调整字段。
  - 验收：红旗卡使用固定 fail-closed 文案，不消费后端普通训练字段。
  - 证据：`medicalCopy`。
  - Owner：Safety reviewer。
  - 状态：已修复。
- [x] R1-A012 审计 medical referral 是否显示普通 regenerate。
  - 验收：红旗分支不显示生成调整版计划按钮。
  - 证据：`isMedicalReferralFeedback()`。
  - Owner：Safety reviewer。
  - 状态：已通过。
- [x] R1-A013 审计 medical referral 是否显示计划差异。
  - 验收：红旗卡不展示普通 plan diff 卡片。
  - 证据：`buildFeedbackResultHtml()`。
  - Owner：Safety reviewer。
  - 状态：已通过。
- [x] R1-A014 审计 medical referral 文案是否中英混排。
  - 验收：前端红旗分支无 `Rest only`。
  - 证据：`rg` 扫描。
  - Owner：Copy reviewer。
  - 状态：已修复。
- [x] R1-A015 审计风险未知是否显示正常。
  - 验收：缺 risk_gate 时显示“未完成风险自检”。
  - 证据：`buildTrustStatusHtml()`。
  - Owner：Trust reviewer。
  - 状态：已修复。
- [x] R1-A016 审计动作库命中是否显示无条件可执行。
  - 验收：动作库命中显示“结构可追踪；执行前完成疲劳/疼痛自检”。
  - 证据：`protocolRecheckActionText()`。
  - Owner：Training safety reviewer。
  - 状态：已修复。
- [x] R1-A017 审计恢复日是否显示无条件可执行。
  - 验收：恢复日也提示疲劳/疼痛自检。
  - 证据：`protocolRecheckActionText()`。
  - Owner：Training safety reviewer。
  - 状态：已修复。
- [x] R1-A018 审计内置 HMP 规则是否伪装成检索证据。
  - 验收：显示“内置规则”，说明“非外部检索证据”。
  - 证据：`protocolRuleEvidenceItems()`。
  - Owner：Evidence reviewer。
  - 状态：已修复。
- [x] R1-A019 审计模型知识是否伪引用。
  - 验收：模型知识显示“未绑定证据”，不生成伪引用。
  - 证据：`evidenceDisplayId()`。
  - Owner：Evidence reviewer。
  - 状态：已修复。
- [x] R1-A020 审计计划规则是否显示 `#day_rule_basis`。
  - 验收：计划规则显示“计划规则”，不显示 hash 编号。
  - 证据：`evidenceDisplayId()`。
  - Owner：Evidence reviewer。
  - 状态：已修复。
- [x] R1-A021 审计动作库证据是否暴露 action id。
  - 验收：普通 UI 显示“动作库”或来源页码，不显示内部 action id。
  - 证据：`sourceStateLabel()`、`buildTrustStatusHtml()`。
  - Owner：Trust reviewer。
  - 状态：已修复。
- [x] R1-A022 审计 HMP 协议路径是否统一。
  - 验收：前端 fallback 使用 `docs/product/half_marathon_hmp_protocol.md`。
  - 证据：`describeDayBasis()`。
  - Owner：Contract reviewer。
  - 状态：已修复。
- [x] R1-A023 审计 `WorkflowTrace` 是否可见给普通用户。
  - 验收：普通文案改为“追踪版本”，审计详情 hidden + expert-only。
  - 证据：`buildAuditTraceHtml()`。
  - Owner：Expert UI reviewer。
  - 状态：已修复。
- [x] R1-A024 审计 `Trace 节点` 是否可见。
  - 验收：普通源文件中可见标签为“审计节点”。
  - 证据：`rg` 扫描。
  - Owner：Copy reviewer。
  - 状态：已修复。
- [x] R1-A025 审计 raw JSON 是否暴露在普通面板。
  - 验收：审计面板渲染白名单摘要。
  - 证据：`buildAuditTraceHtml()`。
  - Owner：Expert UI reviewer。
  - 状态：已修复。
- [x] R1-A026 审计最近反馈是否显示 raw `reason_codes`。
  - 验收：最近反馈显示“调整原因”用户化标签。
  - 证据：`buildLatestFeedbackHtml()`。
  - Owner：Copy reviewer。
  - 状态：已修复。
- [x] R1-A027 审计调整历史是否显示 raw `risk_gate`。
  - 验收：调整历史显示“风险门”。
  - 证据：`renderAdjustmentHistory()`。
  - Owner：Copy reviewer。
  - 状态：已修复。
- [x] R1-A028 审计调整历史是否显示 raw `protocol_recheck`。
  - 验收：调整历史显示“协议复核”。
  - 证据：`renderAdjustmentHistory()`。
  - Owner：Copy reviewer。
  - 状态：已修复。
- [x] R1-A029 审计反馈结果是否显示 raw `feedback_id`。
  - 验收：普通反馈结果不显示 `feedback_id` 行。
  - 证据：`buildFeedbackResultHtml()`。
  - Owner：Copy reviewer。
  - 状态：已修复。
- [x] R1-A030 审计证据覆盖是否显示 raw enum。
  - 验收：证据覆盖显示“动作库 / 内置规则”。
  - 证据：`renderRacePrepOverview()`。
  - Owner：Copy reviewer。
  - 状态：已修复。
- [x] R1-A031 审计 day modal 是否分层。
  - 验收：训练安排、依据审计、反馈调整三 tab。
  - 证据：`buildDayModalHtml()`。
  - Owner：UX reviewer。
  - 状态：已修复。
- [x] R1-A032 审计 day modal tab 是否可访问。
  - 验收：tab/tablist/tabpanel、aria-controls、aria-labelledby 均存在。
  - 证据：契约测试。
  - Owner：Accessibility reviewer。
  - 状态：已修复。
- [x] R1-A033 审计 day modal tab 键盘导航。
  - 验收：ArrowLeft、ArrowRight、Home、End 支持切换。
  - 证据：`handleDayModalTabKeydown()`。
  - Owner：Accessibility reviewer。
  - 状态：已修复。
- [x] R1-A034 审计 day modal focus trap。
  - 验收：Tab 不逃逸，Escape 关闭，关闭后恢复触发按钮。
  - 证据：`handleFocusTrapKeydown()`。
  - Owner：Accessibility reviewer。
  - 状态：已修复。
- [x] R1-A035 审计 evidence drawer focus trap。
  - 验收：drawer 打开时背景 inert，关闭后恢复。
  - 证据：`openEvidenceDrawer()`、`closeEvidenceDrawer()`。
  - Owner：Accessibility reviewer。
  - 状态：已修复。
- [x] R1-A036 审计 mobile side drawer 是否 modal 化。
  - 验收：移动端打开 drawer 后 body lock、背景 inert、Escape 关闭。
  - 证据：`round1-browser-smoke.json`。
  - Owner：Mobile reviewer。
  - 状态：已修复。
- [x] R1-A037 审计 mobile side drawer 是否有关闭入口。
  - 验收：存在 `.side-drawer-close` 和 backdrop。
  - 证据：`index.astro`、`responsive.css`。
  - Owner：Mobile reviewer。
  - 状态：已修复。
- [x] R1-A038 审计 desktop side drawer 是否保持非 modal。
  - 验收：桌面 Escape 不强制关闭 sticky drawer，不锁 body。
  - 证据：`round1-browser-smoke.json`。
  - Owner：Desktop UX reviewer。
  - 状态：已确认。
- [x] R1-A039 审计移动端横向溢出。
  - 验收：375px `scrollWidth == clientWidth`。
  - 证据：`round1-browser-smoke.json`。
  - Owner：Responsive reviewer。
  - 状态：已通过。
- [x] R1-A040 审计桌面端横向溢出。
  - 验收：1440px `scrollWidth == clientWidth`。
  - 证据：`round1-browser-smoke.json`。
  - Owner：Responsive reviewer。
  - 状态：已通过。
- [x] R1-A041 审计日卡要点是否被 ellipsis 截断。
  - 验收：`.day-card-essentials span` 允许换行。
  - 证据：`calendar.css`。
  - Owner：Calendar reviewer。
  - 状态：已修复。
- [x] R1-A042 审计移动端日卡要点列数。
  - 验收：移动端从三列收为两列。
  - 证据：`responsive.css`。
  - Owner：Calendar reviewer。
  - 状态：已修复。
- [x] R1-A043 审计小字号弱文本对比。
  - 验收：`--faint` 提亮到 `#858fa3`。
  - 证据：`base.css`。
  - Owner：Visual reviewer。
  - 状态：已修复。
- [x] R1-A044 审计主按钮白字对比。
  - 验收：主按钮渐变末端加深。
  - 证据：`components.css`。
  - Owner：Visual reviewer。
  - 状态：已修复。
- [x] R1-A045 审计页面 favicon 404。
  - 验收：桌面/移动 console errors 为空。
  - 证据：内联 favicon + browser smoke。
  - Owner：Polish reviewer。
  - 状态：已修复。
- [x] R1-A046 审计 H1 可访问名称。
  - 验收：主界面存在 `.sr-only` h1。
  - 证据：`index.astro`。
  - Owner：Accessibility reviewer。
  - 状态：已修复。
- [x] R1-A047 审计全局 focus-visible。
  - 验收：按钮、链接、输入、summary 都有明显 focus ring。
  - 证据：`base.css`。
  - Owner：Accessibility reviewer。
  - 状态：已修复。
- [x] R1-A048 审计 `setBackgroundInert` 是否误 inert modal 父级。
  - 验收：存在 `root.contains(activeLayer)` 保护。
  - 证据：`app.js`。
  - Owner：Accessibility reviewer。
  - 状态：已修复。
- [x] R1-A049 审计前端 build。
  - 验收：`npm run build` 通过。
  - 证据：2026-05-22 回归命令。
  - Owner：Verification reviewer。
  - 状态：已通过。
- [x] R1-A050 审计前端契约测试。
  - 验收：`tests/test_astro_frontend_contract.py` 通过。
  - 证据：66 passed。
  - Owner：Verification reviewer。
  - 状态：已通过。
- [x] R1-A051 审计 API/状态目标回归。
  - 验收：`tests/test_api_app.py tests/test_state_models.py` 通过。
  - 证据：94 passed 目标矩阵。
  - Owner：Verification reviewer。
  - 状态：已通过。
- [x] R1-A052 审计 workspace smoke。
  - 验收：隔离 preview `http://127.0.0.1:4323/#workspace` 通过。
  - 证据：`npm run smoke:workspace`。
  - Owner：Browser reviewer。
  - 状态：已通过。
- [x] R1-A053 审计浏览器截图基线。
  - 验收：桌面、移动、drawer 打开四张截图已生成。
  - 证据：`artifacts/frontend-audit/round1-*.png`。
  - Owner：Visual reviewer。
  - 状态：已完成。
- [x] R1-A054 审计浏览器控制台。
  - 验收：桌面和移动 console error 为空。
  - 证据：`round1-browser-smoke.json`。
  - Owner：Browser reviewer。
  - 状态：已通过。
- [x] R1-A055 审计 `git diff --check`。
  - 验收：无 whitespace error。
  - 证据：`git diff --check`。
  - Owner：Repo hygiene reviewer。
  - 状态：已通过。
- [ ] R1-A056 等待只读后端交付面 reviewer 结果。
  - 验收：后端 reviewer 明确 T0/T1/T2 或“没有值得修的问题”。
  - 证据：子 agent `Sartre`。
  - Owner：Backend readonly reviewer。
  - 状态：进行中。
- [ ] R1-A057 审计共享契约签收清单是否需要更新。
  - 验收：前端 owner 条目能对应 build、smoke、普通模式隐藏专家词。
  - 证据：`docs/quality/shared_delivery_contract.md` 第 12 节。
  - Owner：QA reviewer。
  - 状态：待下一轮。
- [ ] R1-A058 审计报告是否标记已修复项。
  - 验收：报告从“阻断”更新为“R1 已修复 / R2 待审”。
  - 证据：`docs/product/reports/frontend_product_audit_2026-05-22.md`。
  - Owner：Documentation reviewer。
  - 状态：待更新。
- [ ] R1-A059 审计后续轮次是否继续拆分 TODO。
  - 验收：每个新 finding 进入 audit todo 和 review todo。
  - 证据：新增 round2 文档。
  - Owner：Coordinator。
  - 状态：持续。
- [ ] R1-A060 审计终止条件。
  - 验收：多角色 review 均无值得修问题，且所有共同验收命令通过。
  - 证据：最终轮次报告。
  - Owner：Coordinator。
  - 状态：未达到。

## R7 Frontend Owner Audit Overlay：状态面板与高端商用审美迁移复核

- [x] R7-A001 读取共享契约。
  - 验收：已读取 `docs/quality/shared_delivery_contract.md`。
  - 证据：本轮执行记录。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R7-A002 读取 hardening 循环手册。
  - 验收：已读取 `docs/quality/release_hardening_loop.md`。
  - 证据：本轮执行记录。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R7-A003 检查 dirty worktree。
  - 验收：已运行 `git status --short`，确认存在大量后端/数据/文档变更。
  - 证据：本轮 shell 输出。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R7-A004 开启高端商用审美只读 reviewer。
  - 验收：只读 agent `Nash` 已返回。
  - 证据：Round 7 review overlay。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R7-A005 开启后端交付面只读 reviewer。
  - 验收：只读 agent `Cicero` 已返回。
  - 证据：Round 7 review overlay。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R7-A006 关闭无用 agent。
  - 验收：两个只读 agent 均已关闭。
  - 证据：`close_agent` 返回。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R7-A007 高端来源 Oura。
  - 验收：记录 Readiness 分层与不可迁移边界。
  - 证据：https://support.ouraring.com/hc/pl/articles/360025589793-Readiness-Score
  - Owner：Product design reviewer。
  - 状态：已完成。
- [x] R7-A008 高端来源 WHOOP。
  - 验收：记录 daily summary / Coach 行动化表达与非医疗边界。
  - 证据：https://www.whoop.com/us/en/product-feature/ 与 https://support.whoop.com/s/article/How-to-Use-the-AI-Powered-WHOOP-Coach
  - Owner：Product design reviewer。
  - 状态：已完成。
- [x] R7-A009 高端来源 Garmin。
  - 验收：记录 training readiness 的短消息 + contributors 范式。
  - 证据：https://support.garmin.com/en-IE/?faq=hsKqNlQksk0Q6Zf1EbIjO9&productID=125677&tab=topics
  - Owner：Product design reviewer。
  - 状态：已完成。
- [x] R7-A010 高端来源 TrainingPeaks。
  - 验收：记录 Plan / Train / calendar / today workout 信息架构。
  - 证据：https://www.trainingpeaks.com/ 与 https://apps.apple.com/us/app/trainingpeaks/id408047715
  - Owner：Product design reviewer。
  - 状态：已完成。
- [x] R7-A011 高端来源 Nike Run Club。
  - 验收：记录 guided action 文案范式。
  - 证据：https://about.nike.com/newsroom/releases/nike-run-club-app-new-features 与 https://apps.apple.com/us/app/nike-run-club-running-coach/id387771637
  - Owner：Product design reviewer。
  - 状态：已完成。
- [x] R7-A012 高端来源 Apple Health。
  - 验收：记录 Summary / Pinned / Highlights / Health Checklist 的信息分层。
  - 证据：https://support.apple.com/en-us/ht203037
  - Owner：Product design reviewer。
  - 状态：已完成。
- [x] R7-A013 高端来源 Strava。
  - 验收：记录 mobile task-first 与高级层下钻边界。
  - 证据：https://support.strava.com/hc/en-us/articles/18001474720397-Creating-Routes-on-Mobile
  - Owner：Product design reviewer。
  - 状态：已完成。
- [x] R7-A014 高端来源 Linear。
  - 验收：记录 triage/inbox 作为异常复核层，不污染主 workflow。
  - 证据：https://linear.app/docs/triage 与 https://linear.app/docs/inbox
  - Owner：Product design reviewer。
  - 状态：已完成。
- [x] R7-A015 高端来源 Stripe Radar。
  - 验收：记录风险队列与详情下钻范式。
  - 证据：https://docs.stripe.com/radar/reviews 与 https://docs.stripe.com/radar/risk-evaluation
  - Owner：Product design reviewer。
  - 状态：已完成。
- [x] R7-A016 审计普通状态面板英文枚举。
  - 验收：浏览器实测发现 `attention` 可见。
  - 证据：当前 `http://127.0.0.1:4322/#workspace` 截图。
  - Owner：Frontend owner。
  - 状态：已发现并修复。
- [x] R7-A017 修复 `attention` 用户化。
  - 验收：`statusLabel()` 映射为 `需要关注`。
  - 证据：`apps/web/src/scripts/app.js`。
  - Owner：Frontend owner。
  - 状态：已修复。
- [x] R7-A018 修复 `unknown` 用户化。
  - 验收：`statusLabel()` 映射为 `待反馈确认`。
  - 证据：`apps/web/src/scripts/app.js`。
  - Owner：Frontend owner。
  - 状态：已修复。
- [x] R7-A019 修复 `deescalate` 用户化。
  - 验收：`statusLabel()` 映射为 `建议降级`。
  - 证据：`apps/web/src/scripts/app.js`。
  - Owner：Frontend owner。
  - 状态：已修复。
- [x] R7-A020 审计未来训练误判漏反馈。
  - 验收：浏览器实测新生成计划显示 `补录 16 天反馈`。
  - 证据：当前 `http://127.0.0.1:4322/#workspace` 截图。
  - Owner：Frontend owner。
  - 状态：已发现并修复。
- [x] R7-A021 新增反馈记录统一判断。
  - 验收：`hasFeedbackRecord(day)` 成为状态面板与行动摘要的共享判断。
  - 证据：`apps/web/src/scripts/app.js`。
  - Owner：Frontend owner。
  - 状态：已修复。
- [x] R7-A022 新增反馈到期判断。
  - 验收：`isFeedbackDue(day)` 只把已到期或显式执行状态的训练日计入漏反馈。
  - 证据：`apps/web/src/scripts/app.js`。
  - Owner：Frontend owner。
  - 状态：已修复。
- [x] R7-A023 保护未来训练。
  - 验收：无日期或未来日期训练不计入漏反馈。
  - 证据：`return trainingDate.getTime() < today.getTime();`。
  - Owner：Frontend owner。
  - 状态：已修复。
- [x] R7-A024 补契约测试。
  - 验收：前端契约测试包含状态枚举中文化和 `isFeedbackDue` 检查。
  - 证据：`tests/test_astro_frontend_contract.py`。
  - Owner：Frontend owner。
  - 状态：已修复。
- [ ] R7-A025 构建验证。
  - 验收：`cd apps/web; npm run build` 通过。
  - 证据：待运行。
  - Owner：Frontend owner。
  - 状态：待验证。
- [ ] R7-A026 目标 pytest 验证。
  - 验收：`tests/test_astro_frontend_contract.py tests/test_api_app.py tests/test_state_models.py -q` 通过。
  - 证据：待运行。
  - Owner：Frontend owner。
  - 状态：待验证。
- [ ] R7-A027 workspace smoke 验证。
  - 验收：隔离 preview `smoke:workspace` 通过。
  - 证据：待运行。
  - Owner：Frontend owner。
  - 状态：待验证。
- [ ] R7-A028 浏览器桌面复核。
  - 验收：桌面普通模式无 raw 字段、无 `attention` 英文、无未来漏反馈。
  - 证据：待截图。
  - Owner：Frontend owner。
  - 状态：待验证。
- [ ] R7-A029 浏览器移动复核。
  - 验收：375px 无水平溢出，行动摘要面板与状态面板可读。
  - 证据：待截图。
  - Owner：Frontend owner。
  - 状态：待验证。
- [ ] R7-A030 仓库 whitespace 验证。
  - 验收：`git diff --check` 通过。
  - 证据：待运行。
  - Owner：Frontend owner。
  - 状态：待验证。
- [ ] R7-A031 共享契约前端签收项更新。
  - 验收：前端 owner 只签自己已验证的普通模式与 key 边界，不替 QA/backend 签最终完成。
  - 证据：待更新。
  - Owner：Frontend owner。
  - 状态：待验证后更新。
- [ ] R7-A032 退出条件复核。
  - 验收：若 backend/QA/reviewer 仍未签收无可修项，则不能结束 release hardening。
  - 证据：共享契约第 13 节。
  - Owner：Frontend owner。
  - 状态：未达到。

## Round 11 - Card Layout Commercial Hardening

- [x] R11-A001 固化成熟产品验收标准。
  - 验收：新增 `docs/product/mature_product_acceptance_standard.md`，每轮成熟产品/审美/信息架构结论必须检索 10+ 公开来源并只选 Top 3 迁移。
  - 证据：ISO 9241-11、NN/g、WCAG 2.2、GOV.UK、web.dev、Material、USWDS、Apple Health、Oura、WHOOP、TrainingPeaks、Garmin、Runna、Strava、小红书等来源已记录。
  - Owner：Frontend owner / Requirements support。
  - 状态：已完成。
- [x] R11-A002 更新共享交付契约的证据门槛。
  - 验收：`docs/quality/shared_delivery_contract.md` 新增 10+ 来源与 Top 3 迁移约束。
  - 证据：共享契约第 -1 节。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R11-A003 侧栏画像摘要化。
  - 验收：`runner-identity-card` 只展示目标、水平、可训练日和一个 `编辑我的情况` 入口；不再展示完整字段网格、强度区间表或 `来自 API`。
  - 证据：`apps/web/src/scripts/app.js`、`apps/web/src/styles/plan.css`、截图 `round11-card-layout-mobile-drawer-2026-05-22.png`。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R11-A004 完整画像编辑从侧栏下沉到 dialog。
  - 验收：点击 `完善跑者资料` 直接打开 `profileEditorDialog`；`moveWorkspaceSectionsToDrawer()` 不再把完整 `#profile` 表单移入 drawer。
  - 证据：`tests/test_astro_frontend_contract.py::test_astro_profile_moves_to_sidebar_while_calendar_remains_primary_surface`。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R11-A005 历史计划轻列表化。
  - 验收：侧栏默认只显示最近 2 条历史摘要；删除入口只在展开后出现；文案改为 `保存当前计划 / 刷新历史 / 查看全部历史`。
  - 证据：`apps/web/src/scripts/app.js`、`apps/web/src/pages/index.astro`、移动状态 JSON `round11-card-layout-mobile-state-2026-05-22.json`。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R11-A006 周卡普通层去计算字段。
  - 验收：普通层周卡显示 `本周训练压力 较高/稳定/待估`，不再显示 `周代理负荷 512` 这类数字计算字段。
  - 证据：桌面状态 JSON `containsRawVisible=[]`。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R11-A007 日卡摘要化。
  - 验收：日卡外层只显示日期、类型、训练名、时长/区间、训练压力、安全自检、查看安排；隐藏负荷比例、证据源、协议细节。
  - 证据：`sampleDayCard` 为中文摘要，无 `查看详情`、`workflow_trace`、`generation_status`。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R11-A008 深灰后台块清理。
  - 验收：本周关键课列表和时间设置折叠条改为白底轻边框，不再出现大面积深灰管理块。
  - 证据：桌面截图 `round11-card-layout-desktop-2026-05-22.png`。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R11-A009 浏览器截图复核。
  - 验收：桌面 1440、移动 390、移动 drawer 截图均已保存；状态 JSON 显示无横向溢出、无 raw 字段。
  - 证据：
    - `artifacts/frontend-audit/round11-card-layout-desktop-2026-05-22.png`
    - `artifacts/frontend-audit/round11-card-layout-mobile-2026-05-22.png`
    - `artifacts/frontend-audit/round11-card-layout-mobile-drawer-2026-05-22.png`
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R11-A010 前端契约测试。
  - 验收：`C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -m pytest -p no:cacheprovider tests\test_astro_frontend_contract.py -q` 通过。
  - 证据：66 passed。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R11-A011 前端构建。
  - 验收：`cd apps/web; npm run build` 通过。
  - 证据：Astro build complete，1 page built。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R11-A012 workspace smoke。
  - 验收：隔离 preview `WORKSPACE_URL=http://127.0.0.1:4325/#workspace npm run smoke:workspace` 通过。
  - 证据：第一次在构建同时运行出现移动端瞬时失败；诊断确认 DOM 正常，重跑通过。
  - Owner：Frontend owner。
  - 状态：已完成。
- [ ] R11-A013 后续仍需修复。
  - 验收：首屏顶部在 full-page 截图中仍有轻微 sticky nav 覆盖感；结果摘要仍偏长，下一轮应继续压缩为更直接的今日/本周主路径。
  - 证据：`round11-card-layout-desktop-2026-05-22.png`。
  - Owner：Frontend owner。
  - 状态：待下一轮。

## Round 12 - Reading Fatigue Reduction

- [x] R12-A001 阅读疲劳公开证据门槛。
  - 验收：新增 `docs/product/reading_fatigue_reduction_todo.md`，不少于 500 行，记录 10+ 公开来源和 Top 3 迁移对象。
  - 证据：NN/g Progressive Disclosure、NN/g F-pattern、NN/g How Users Read、NN/g Cognitive Load、W3C COGA、GOV.UK、Material Cards/Lists、Apple HIG、Fluent、Baymard、TrainingPeaks、Apple Health 等来源。
  - Owner：Frontend owner / Requirements support。
  - 状态：已完成。
- [x] R12-A002 本轮只读子 agent 审计。
  - 验收：最多 1 个子 agent；本轮只开启 `019e4f4d-9b2f-79f2-ba86-05a2660a097b`，范围是阅读疲劳代码/文档只读审计，不联网、不改文件。
  - 证据：子 agent 返回 T0/T1/T2 findings，指出 day modal 默认信息过重、周视图默认展开过长、反馈表单偏重。
  - Owner：Frontend owner。
  - 状态：已完成，待关闭记录。
- [x] R12-A003 结果摘要降为二级阅读层。
  - 验收：`report-panel` 改为默认折叠 `details`；标题改为 `为什么这样安排`；新增 `data-reading-fatigue-guard` 与 `data-secondary-reading-layer`。
  - 证据：`apps/web/src/pages/index.astro`、`apps/web/src/styles/components.css`、`tests/test_astro_frontend_contract.py::test_astro_reading_fatigue_guard_prioritizes_calendar_over_long_reports`。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R12-A004 生成后主路径改为日历优先。
  - 验收：视觉顺序中 `#calendar-section` 位于 `.dashboard-grid` 前；用户不需要先读完整解释才能进入训练日历。
  - 证据：`apps/web/src/styles/components.css` order contract。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R12-A005 行动摘要从四张大卡压缩为一张主卡 + 三条短摘要。
  - 验收：`renderCalendarActionPanel()` 保留 `下一次训练` 主卡；`本周重点 / 安全提醒 / 反馈入口` 进入 `calendar-action-secondary` 与 `calendar-action-mini`。
  - 证据：`apps/web/src/scripts/app.js`、`apps/web/src/styles/calendar.css`。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R12-A006 周计划默认折叠，减少生成后长滚动。
  - 验收：`isWeekGroupExpanded()` 默认返回 `false`；用户点击周卡或周导航后再展开 7 天日卡。
  - 证据：`apps/web/src/scripts/app.js`、前端契约测试。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R12-A007 日卡详情首屏先显示“今天怎么练”。
  - 验收：`buildDayModalHtml()` 的默认 `plan` tab 只前置时长、强度、安全、热身、主课、冷身；可信状态、产品状态、负荷指标和审计信息移动到 `audit` tab。
  - 证据：`apps/web/src/scripts/app.js`、`apps/web/src/styles/modal.css`、前端契约测试。
  - Owner：Frontend owner。
  - 状态：已完成。
- [x] R12-A008 阅读疲劳契约测试。
  - 验收：测试覆盖二级阅读层、日历优先、行动面板摘要化、周默认折叠、日卡详情默认不前置 trust/metric。
  - 证据：`tests/test_astro_frontend_contract.py`。
  - Owner：Frontend owner。
  - 状态：已完成，待运行。
- [x] R12-A009 浏览器截图复核。
  - 验收：桌面和 390px 移动端截图显示 report 默认折叠、日历在解释前、action panel 变短、周卡默认折叠、日卡详情首屏先见主课。
  - 证据：`artifacts/frontend-audit/round12-reading-fatigue-desktop-2026-05-22.png`、`artifacts/frontend-audit/round12-reading-fatigue-mobile-2026-05-22.png`、`artifacts/frontend-audit/round12-reading-fatigue-day-modal-desktop-2026-05-22.png`；状态 JSON 同目录。
  - Owner：Frontend owner。
  - 状态：已完成。关键状态：`reportOpen=false`、`actionCardCount=1`、`actionMiniCount=3`、`expandedWeekCount=0`、`calendarBeforeReport=true`、`rawVisible=[]`、modal 默认 `activePanel=plan`。
- [x] R12-A010 反馈页 quick-first 阅读疲劳修复。
  - 验收：反馈 tab 默认显示“完成 / 部分 / 跳过/不适”三选一、选中摘要和提交按钮；疲劳、疼痛、睡眠、红旗和补充说明进入默认折叠的“补充细节”。
  - 证据：`apps/web/src/scripts/app.js` 中 `data-feedback-quick-first`、`data-feedback-detail`、`syncFeedbackQuickChoiceUi()`；`apps/web/src/styles/modal.css` 中 `.feedback-selected-summary`、`.modal-feedback-detail`；截图 `artifacts/frontend-audit/round12-feedback-quick-first-desktop-2026-05-22.png` 和 `artifacts/frontend-audit/round12-feedback-quick-first-mobile-2026-05-22.png`。
  - Owner：Frontend owner。
  - 状态：已完成。关键状态：桌面/移动均 `quickFirst=true`、`detailOpen=false`、`submitVisible=true`、`redFlagCount=5`、`horizontalOverflow=false`；对比度 `已选择=10.35:1`、`补充细节=17.74:1`。
- [ ] R12-A011 仍需后续处理。
  - 验收：移动端 day modal 可继续评估 bottom sheet；普通层“训练日历生成器/普通模式/完整计划未截断”等系统文案仍需下一轮中文用户任务化；红旗反馈路径仍需单独截图签收。
  - 证据：本轮只读 agent findings 与 fresh browser state。
  - Owner：Frontend owner。
  - 状态：待下一轮。
