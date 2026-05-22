# Mature Product Acceptance Standard

> 角色：Frontend owner / Requirements support。
> 用途：约束后续前端审计、TODO、报告和修复。任何“成熟商用 app”结论都必须先过本文件的证据门槛。
> 日期：2026-05-22。

## 0. Hard Gate

- 每次做前端审美、信息架构、商用成熟度或竞品迁移结论前，必须至少检索 10 个以上公开网页或 UI 设计来源。
- 每次检索必须记录来源、可观察事实、可迁移范式和不可迁移边界。
- 每次只能选 Top 3 进入本轮实现或 TODO；其余来源只能作为参考，不能把所有竞品特征堆进产品。
- 结论不能靠“感觉高级”；必须落回中国马拉松跑者任务：今天怎么练、本周重点、风险是否阻断、反馈后计划如何变化、依据在哪里、是否值得信任。
- 普通用户界面禁止展示英文 raw 字段、变量名、trace/protocol/workflow/internal id、计算中间量和用户不关心的管理字段。

## 1. Evidence Corpus For Current Standard

本轮共检索并采用 16 类来源，满足 10+ 来源门槛。

| # | 来源 | 类型 | 可观察事实 | 对本产品的启发 |
|---|---|---|---|---|
| 1 | ISO 9241-11:2018 | 可用性标准 | Usability 是使用结果，关注有效性、效率、满意度。 | 验收不能只看“功能能跑”，要看跑者能否完成真实任务。 |
| 2 | NN/g 10 Usability Heuristics | UX 标准 | 系统状态、用户语言、错误预防、一致性、极简设计是基础启发式。 | 普通层必须讲跑者语言，不讲工程字段。 |
| 3 | NN/g Progressive Disclosure | UX 标准 | 初始界面只展示最重要选项，复杂内容用户请求后再展示。 | 外层卡片只放摘要，解释/证据/审计进详情层。 |
| 4 | WCAG 2.2 | 可访问性标准 | 感知、可操作、可理解、稳健；AA 包含对比度、reflow、focus visible、target size。 | 320px/390px、键盘、焦点、对比度是发布门槛。 |
| 5 | GOV.UK Service Standard | 服务标准 | 理解用户需求、解决完整问题、简单易用、人人可用、安全隐私、可靠运营。 | 商用验收要覆盖完整服务链，不只是页面漂亮。 |
| 6 | web.dev Core Web Vitals | 性能标准 | 关注加载、交互、视觉稳定，建议按移动/桌面 75 分位看体验。 | 前端 smoke 之外要逐步加入 LCP/INP/CLS 观测。 |
| 7 | Material Design Cards | 组件范式 | Card 是进入详细信息的入口，主动作通常是卡片本身，补充动作克制。 | 日卡/周卡/历史卡外层不能堆按钮和解释。 |
| 8 | Material Design Lists | 组件范式 | 列表适合同类数据，tile 文字行数有限，主动作与补充动作分离。 | 历史计划适合列表，不适合窄侧栏卡片网格。 |
| 9 | USWDS Card | 公共设计系统 | Card 是更大内容的 summary/entry point，并通过边框/阴影区别集合项。 | 卡片应可扫描、可点击、信息单一。 |
| 10 | Apple Health | 健康产品 | Summary、Pinned、Highlights、Health Checklist 分层展示；重要数据可固定。 | “今日/本周关键”优先，长期趋势和检查项下沉。 |
| 11 | Oura App | 健康产品 | 用健康区域、等级、趋势和数据要求解释状态；数据不足时明确校准。 | 不足证据/画像缺失要明说，不能伪装成确定建议。 |
| 12 | WHOOP | 健康产品 | 把 sleep/strain/recovery 等数据转为 daily guidance，并声明 wellness 非医疗。 | 训练负荷必须转译为建议，不包装成医学诊断。 |
| 13 | TrainingPeaks | 耐力训练产品 | Calendar 是训练入口，可添加 workout/metric/event；计划训练与完成反馈联动。 | 计划-执行-反馈闭环是基础，不是专家功能。 |
| 14 | Garmin Training Readiness | 可穿戴产品 | readiness 由多个 contributors 支撑，给短消息帮助用户决定是否训练。 | 风险/恢复要给短行动建议，细因子进入详情。 |
| 15 | Runna / Strava | 跑步产品 | 训练计划、今日训练、进度和路线/订阅能力围绕跑者任务组织。 | 首屏必须回答“今天练什么”，而不是“系统生成了什么”。 |
| 16 | 小红书 Web / UI 案例 | 中国消费级 UI | 左侧导航克制，主内容信息流以卡片摘要呈现，点击后看详情。 | 可迁移简洁导航、轻卡片和中文内容节奏；不可迁移社交瀑布流、点赞评论、品牌红。 |

## 2. Current Top 3 Migration Patterns

### Top 1: 摘要入口 + 详情层

证据来源：NN/g Progressive Disclosure、Material Cards、USWDS Card、小红书 Web。

适用范围：
- 日训练卡、周计划卡、历史计划卡、依据入口卡。
- 外层只显示“是什么 / 何时 / 做多久或多远 / 安全状态 / 查看安排”。
- 解释、证据、容量预算、协议复核、修复日志和调试字段全部进入详情层或专家审计层。

不可迁移边界：
- 不把训练日历改成瀑布流。
- 不把社交点赞、收藏、评论带进训练工具。
- 不在一张卡里塞多个同级 CTA。

### Top 2: 健康状态转译为行动建议

证据来源：Apple Health、Oura、WHOOP、Garmin。

适用范围：
- 风险状态、恢复状态、训练压力、反馈结果、画像缺失。
- 普通层用中文行动语言：`可以继续`、`建议降级`、`先休息并观察`、`需要就医评估`、`资料不足，先按保守计划`。
- 数据不足时明确显示“资料不足 / 正在校准 / 只能给保守建议”，不伪造 certainty。

不可迁移边界：
- 不声称拥有设备级 HRV、真实恢复分或医学诊断。
- 不展示 raw contributors、算法字段、英文状态码。
- 不把 wellness 产品的分数体系直接套到训练处方。

### Top 3: 任务优先的训练闭环

证据来源：TrainingPeaks、Runna、Strava、GOV.UK Service Standard。

适用范围：
- 首屏优先回答“今天怎么练、本周重点、比赛目标是否在轨、反馈后哪里变了”。
- 日历是主任务面，不是报告附属物。
- 反馈、计划 diff、红旗阻断和历史恢复必须围绕用户完成训练闭环呈现。

不可迁移边界：
- 不把专业平台的复杂指标直接暴露给普通跑者。
- 不用英文训练平台术语替代中文跑者语言。
- 不展示用户不关心的 API、DB、trace、request id、protocol issue。

## 3. Mature Product Acceptance Matrix

| 维度 | 商用验收标准 | 当前 UI/TODO 落点 |
|---|---|---|
| 用户任务 | 用户能在 1 屏内知道下一步该做什么。 | 首屏显示今日/本周/生成入口，不显示工程状态。 |
| 信息架构 | 普通层、详情层、专家审计层边界清楚。 | 卡片摘要化，解释和证据下沉。 |
| 中文语境 | 中国跑者能自然理解文案。 | 禁止 raw 英文枚举和变量字段。 |
| 可访问性 | WCAG 2.2 AA 作为最低线。 | 390px/320px、focus visible、Esc、target size、对比度。 |
| 可信度 | 数据不足、无证据、医疗边界必须明说。 | `missing_or_partial` 不伪造引用；红旗 fail-closed。 |
| 视觉成熟度 | 留白、字号、层级、颜色、阴影克制统一。 | 白底轻导航；单屏强调色不超过 1 个主色 + 状态色。 |
| 交互效率 | 常用动作在前，少用/高级动作按需展开。 | 生成、查看安排、反馈优先；审计详情后置。 |
| 训练专业度 | 训练建议能解释阶段目标、强度、恢复和降级。 | 关键课详情至少回答练什么、为什么、如何降级。 |
| 安全边界 | 风险阻断优先于 regenerate。 | `medical_referral` 不展示普通重生成路径。 |
| 性能稳定 | 页面加载、交互和布局稳定可测。 | build/smoke + 后续 Core Web Vitals 观测。 |

## 4. Reusable Research Template

每轮需求 TODO 必须包含如下结构：

```markdown
## Evidence Scan

- 检索日期：
- 检索者角色：
- 本轮检索来源总数：至少 10
- 本轮 Top 3：

| 来源 | 类型 | 可观察事实 | 可迁移范式 | 不可迁移边界 | 是否进入实现 |
|---|---|---|---|---|---|
|  |  |  |  |  |  |
```

## 5. Source Links

- ISO 9241-11:2018: https://www.iso.org/standard/63500.html
- NN/g 10 Usability Heuristics: https://www.nngroup.com/articles/ten-usability-heuristics/
- NN/g Progressive Disclosure: https://www.nngroup.com/articles/progressive-disclosure/
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- GOV.UK Service Standard: https://www.gov.uk/service-manual/service-standard
- web.dev Web Vitals: https://web.dev/articles/vitals
- Material Cards: https://m1.material.io/components/cards.html
- Material Lists: https://m1.material.io/components/lists.html
- USWDS Card: https://designsystem.digital.gov/components/card
- Apple Health Support: https://support.apple.com/en-us/104997
- Oura App Help: https://support.ouraring.com/hc/en-us/articles/42987005571859-How-to-Use-the-Oura-App
- WHOOP How It Works: https://www.whoop.com/us/en/how-it-works/
- TrainingPeaks Mobile Calendar: https://help.trainingpeaks.com/hc/en-us/articles/360054734312-How-to-add-metrics-workouts-and-events-to-TrainingPeaks-mobile-App
- Garmin Training Readiness: https://support.garmin.com/en-US/?faq=hsKqNlQksk0Q6Zf1EbIjO9
- Strava Features: https://www.strava.com/features
- Runna: https://www.runna.com/
- 小红书 Web: https://www.xiaohongshu.com/explore
