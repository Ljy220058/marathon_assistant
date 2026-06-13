# 产品 Backlog

> 范围：产品体验、产品能力和用户可感知功能。论文、实验运行、仓库治理和纯内部技术债不放在这里。
>
> 来源：`docs/ui_redesign/`、`docs/architecture/marathon_agent_technical_requirements_v3.md`、`docs/audits/half_marathon_source_audit.md`。

## 日历设计与训练时间

- [ ] [product-calendar][P1] 完成月历日期点击、详情抽屉、移动端布局和视觉验收。完成定义：用户可从日历进入单日训练详情，桌面和移动端无明显重叠或溢出。
- [ ] [product-calendar][P1] 开放训练日期与默认训练时间偏好。完成定义：日历事件不再只能按第 1 周周一和 `07:00` 推导。
- [ ] [product-calendar][P2] 评估 Google Calendar 同步入口是否重新启用。完成定义：形成启用、隐藏或删除的产品决策，并同步 API/UI 文档。

## 训练计划总览

- [ ] [product-plan][P1] 落地 `PhaseOverviewBar` 阶段总览条。完成定义：能展示计划目标、总周数、阶段划分与当前阶段。
- [ ] [product-plan][P1] 将训练计划从 Markdown 主渲染迁移到结构化卡片系统。完成定义：核心训练日、周计划和阶段信息可由结构化数据渲染。
- [ ] [product-plan][P2] 决定首周默认展开策略。完成定义：在产品文档中固定为“展开全部每日训练”或“只展开今日训练”。
- [ ] [product-plan][P2] 决定周级卡片导航形态。完成定义：在产品文档中固定为独立页面或纵向滚动。
- [ ] [product-plan][P2] 决定负荷指示器形态。完成定义：在产品文档中固定使用 Progress Bar 或 Badge。

## 周导航与周卡片

- [ ] [product-week][P1] 落地 `WeekNavigator` 周级导航。完成定义：用户可跳转任意周，并看到阶段分组、当前周高亮和已完成周标记。
- [ ] [product-week][P1] 将周级导航升级为所有计划可用。完成定义：少于 8 周的计划也显示一致的周导航。
- [ ] [product-week][P1] 落地 `WeekExplanationSummary`。完成定义：每周卡片内展示关键课摘要和安排理由入口。

## 每日训练卡

- [ ] [product-daily][P1] 落地 `DailyWorkoutDetailCard`。完成定义：替代 `<details>` 文本折叠，展示热身、主课、冷身、场地、备注、心率/强度区间和操作入口。
- [ ] [product-daily][P1] 在每日卡中串联“为什么这样安排？”解释入口。完成定义：入口能打开统一解释层并定位到当前训练。
- [ ] [product-daily][P2] 决定今日训练卡默认展示策略。完成定义：在产品文档中固定为自动展示或点击展开。

## 证据可信

- [x] [product-evidence][P0] 落地 `EvidenceDrawer`。完成定义：点击引用编号或查看证据后展示来源、页码、摘录、证据类型和建议关系；无证据时可展示“模型知识说明（未绑定外部证据）”，但明确不能作为核心处方依据。
- [x] [product-evidence][P0] 统一证据点击链路。完成定义：训练卡、训练依据区和解释引用入口进入同一证据体验，不生成伪引用。
- [ ] [product-evidence][P1] 补齐半马训练专业术语参考表。完成定义：术语表可用于 UI 标准文案、解释和证据展示。
- [ ] [product-evidence][P2] 决定 `EvidenceDrawer` 使用 Dialog 还是侧边 Sheet。完成定义：产品文档固定一种交互形态。

## 解释与自适应说明

- [ ] [product-explanation][P1] 落地 `AdaptiveExplanationCard`。完成定义：用户提交高疲劳、未完成或不适反馈后，能看到计划为何调整。
- [ ] [product-explanation][P2] 决定 `ExplanationDrawer` 使用 Dialog 还是侧边 Sheet。完成定义：产品文档固定一种交互形态。

## 入口工作台

- [ ] [product-workspace][P1] 按四类场景调整入口主操作区。完成定义：首次进入、训练周期中、训练后反馈、自由探索分别呈现合适主动作。
- [ ] [product-workspace][P1] 强化首屏状态信息。完成定义：当前训练状态、今日任务、本周进度、下一步动作在首屏可见。
- [ ] [product-workspace][P2] 决定状态条是否 sticky。完成定义：产品文档固定为置顶状态条或对话流状态消息。

## 用户画像

- [ ] [product-profile][P1] 落地 `RunnerIdentityCard`。完成定义：替代侧边栏纯文本画像，展示跑者类型、目标、训练水平、关键约束和强度区间。
- [ ] [product-profile][P1] 落地 `ProfileEditor`。完成定义：用户能按分组查看和编辑画像字段，保存后刷新计划状态。
- [ ] [product-profile][P0] 统一画像数据来源。完成定义：侧边栏、向导和计划链路读写同一状态契约。
- [ ] [product-profile][P2] 决定画像身份卡位置。完成定义：产品文档固定为 Chat 置顶、侧边栏或独立面板。
- [ ] [product-profile][P2] 决定画像编辑器形态。完成定义：产品文档固定为全屏 Sheet 或居中 Dialog。
- [ ] [product-profile][P1] 决定 NLP 自动提取画像变更是否需要手动确认。完成定义：产品文档固定确认策略，并有对应 UI 状态。

## 训练反馈

- [ ] [product-feedback][P1] 落地 `FeedbackDetailForm`。完成定义：支持完成质量、主观疲劳、不适部位、睡眠恢复和备注的渐进式填写。
- [ ] [product-feedback][P1] 落地 `AdaptiveAdjustmentNotice`。完成定义：反馈后清楚展示是否调整、调整了什么、为什么调整。
- [ ] [product-feedback][P2] 设计过去训练未反馈的提醒或补录入口。完成定义：用户可补录遗漏反馈，不破坏当前计划状态。
- [ ] [product-feedback][P2] 决定反馈表单展开策略。完成定义：产品文档固定为默认展开详细项或渐进式展开。

## 数据状态与风险面板

- [ ] [product-status][P1] 落地 `StatusPanel`。完成定义：聚合展示本周完成度、当前训练负荷、恢复状态、风险等级和下次训练建议。
- [ ] [product-status][P0] 明确恢复状态和风险等级规则。完成定义：疲劳、睡眠、不适、训练负荷到风险等级的规则可测试。
- [ ] [product-status][P2] 决定状态面板位置。完成定义：产品文档固定为入口层或独立面板。

## 长期进度

- [ ] [product-progress][P1] 落地 `CycleProgressBar`。完成定义：展示第几周、总周数和周期完成比例。
- [ ] [product-progress][P1] 落地 `PhaseTimeline`。完成定义：展示各阶段起止周、状态和当前所在阶段。
- [ ] [product-progress][P1] 落地 `CompletedWeeksList`。完成定义：支持回看每周完成度和关键训练摘要。
- [ ] [product-progress][P1] 落地 `AdjustmentHistory`。完成定义：记录每次计划调整日期、内容和原因。
- [ ] [product-progress][P2] 落地 `PhaseReviewCard`。完成定义：阶段完成后总结目标达成、关键数据和下一阶段展望。
- [ ] [product-progress][P2] 决定 `PhaseTimeline` 使用横向步骤条还是纵向列表。完成定义：产品文档固定一种布局。
- [ ] [product-progress][P2] 决定调整记录是否默认可见。完成定义：产品文档固定默认可见性和隐私边界。

## 训练规则与个性化配置

- [ ] [product-rules][P1] 支持用户自定义板块节奏比例。完成定义：例如 `2:1:1` 块模式能进入计划生成约束。
- [ ] [product-rules][P0] 适配 3 天及以下训练日的高负荷场景。完成定义：高负荷不会被不合理压缩到少数训练日。
- [ ] [product-rules][P1] 将个性化周结构约束扩展到多周。完成定义：约束可逐周差异化生效，不只作用于首周。
- [ ] [product-rules][P1] 接入模板库兜底。完成定义：动作库缺证据时仍能给出可解释的保守课表模板。
## 执行状态与调整历史闭环

- [x] [product-status][P0] 固化 `ExecutionStatusSummary`。完成定义：`/plans/{plan_id}` 返回本周完成度、完成/部分/跳过/漏反馈计数、风险等级、恢复状态和下次训练建议，风险来源标记为 `deterministic_feedback_rules`。
- [x] [product-status][P1] 落地 `StatusPanel`。完成定义：日历上方展示本周执行状态、风险等级、漏反馈提醒和下次训练建议；`medical_referral` 视觉上区别于普通已生成状态。
- [x] [product-progress][P1] 落地 `AdjustmentHistory` 最小闭环。完成定义：保存反馈后，历史计划详情回显 `risk_gate`、`protocol_recheck`、`adaptive_adjustment`、`plan_diff` 和受影响后续训练日。
- [x] [product-status][P0] 明确 LLM 通用知识边界。完成定义：无证据时可展示 `llm_general_knowledge` 解释，但不能写入风险规则、核心处方、`risk_level` 或伪引用。
