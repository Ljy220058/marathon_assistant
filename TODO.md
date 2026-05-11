# 产品侧未完成 TODO（按组件模块）

> 范围：仅整理产品体验、产品能力和用户可感知功能待办；排除论文项目、实验任务、运行产物、纯技术债和代码内部实现细节。
>
> 组织方式：按产品组件/模块归类，便于后续拆设计、实现、验收任务。优先级可在每个模块内再补 `P0/P1/P2` 标签。

## 日历设计与训练时间模块

- [ ] 在真实 Chainlit 浏览器中完成月历组件点击日期、详情抽屉、移动端布局和视觉表现验收。来源：`TECH_REQUIREMENTS_V2.md`
- [ ] 开放训练日期与默认训练时间偏好，当前日历事件默认以第 1 周周一和 `07:00` 推导。来源：`TECH_REQUIREMENTS_V2.md`
- [ ] 评估是否重新激活 Google Calendar 同步入口。当前授权/同步回调保留，但 UI 入口已移除。来源：`TECH_REQUIREMENTS_V2.md`

## 训练计划总览模块

- [ ] 落地 `PhaseOverviewBar` 阶段总览条，用于展示计划目标、总周数、阶段划分与当前阶段。来源：`docs/ui_redesign/03_训练计划层设计.md`
- [ ] 将训练计划层从 Markdown 主渲染进一步迁移到结构化卡片系统，减少长文本计划依赖。来源：`docs/ui_redesign/03_训练计划层设计.md`
- [ ] 待确认：首周默认展开全部每日训练，还是只展开今日训练。来源：`docs/ui_redesign/03_训练计划层设计.md`
- [ ] 待确认：周级卡片采用独立页面还是纵向滚动。来源：`docs/ui_redesign/03_训练计划层设计.md`
- [ ] 待确认：负荷指示器使用 Progress Bar 还是 Badge。来源：`docs/ui_redesign/03_训练计划层设计.md`

## 周导航与周卡片模块

- [ ] 落地 `WeekNavigator` 周级导航，让用户可快速跳转任意周，并支持阶段分组、当前周高亮和已完成周标记。来源：`docs/ui_redesign/03_训练计划层设计.md`
- [ ] 将周级导航从“仅 8 周及以上计划显示”升级为所有计划均可用。来源：`docs/ui_redesign/03_训练计划层设计.md`
- [ ] 落地 `WeekExplanationSummary` 本周关键课解释摘要，帮助用户在周卡片内快速理解关键训练安排。来源：`docs/ui_redesign/04_关键解释层设计.md`

## 每日训练卡模块

- [ ] 落地 `DailyWorkoutDetailCard` 每日训练详情卡，替代当前 `<details>` 文本折叠，展示热身、主课、冷身、场地、备注、心率/强度区间和操作入口。来源：`docs/ui_redesign/03_训练计划层设计.md`
- [ ] 在 `DailyWorkoutDetailCard` 中嵌入“为什么这样安排？”解释入口，与 `ExplanationDrawer` 串联。来源：`docs/ui_redesign/04_关键解释层设计.md`
- [ ] 待确认：今日训练卡是自动展示，还是需要用户点击后展开。来源：`docs/ui_redesign/01_入口层设计.md`

## 证据可信模块

- [ ] 落地 `EvidenceDrawer` 证据抽屉，点击引用编号或“查看证据”后展示来源、页码、摘录、证据类型和与当前建议的关系。来源：`docs/ui_redesign/05_证据可信层设计.md`
- [ ] 统一证据点击链路：训练卡、解释抽屉、QA 回答中的引用都应进入同一证据抽屉体验。来源：`docs/ui_redesign/05_证据可信层设计.md`
- [ ] 补齐半马 Sub-70 基石资料末尾缺失的“马拉松/半马训练专业术语参考表”，用于术语解释、UI 标准文案和证据展示。来源：`docs/half_marathon_source_audit.md`
- [ ] 待确认：`EvidenceDrawer` 使用 Dialog 还是侧边 Sheet。来源：`docs/ui_redesign/05_证据可信层设计.md`

## 解释与自适应说明模块

- [ ] 落地 `AdaptiveExplanationCard` 自适应调整解释卡，在用户提交高疲劳、未完成或不适反馈后解释计划为何调整。来源：`docs/ui_redesign/04_关键解释层设计.md`
- [ ] 待确认：`ExplanationDrawer` 使用 Dialog 还是侧边 Sheet。来源：`docs/ui_redesign/04_关键解释层设计.md`

## 入口工作台模块

- [ ] 让入口层在首次进入、训练周期中、训练后反馈和自由探索四类场景下展示不同主操作区。来源：`docs/ui_redesign/01_入口层设计.md`
- [ ] 入口工作台继续强化“当前训练状态、今日任务、本周进度、下一步动作”的首屏呈现。来源：`docs/ui_redesign/00_UI改进路线总纲.md`
- [ ] 待确认：状态条是否需要 sticky 置顶，还是保留为对话流中的状态消息。来源：`docs/ui_redesign/01_入口层设计.md`

## 用户画像模块

- [ ] 落地 `RunnerIdentityCard` 跑者身份卡，替代当前侧边栏纯文本画像区，展示跑者类型、目标、训练水平、关键约束与强度区间。来源：`docs/ui_redesign/02_用户画像层设计.md`
- [ ] 落地 `ProfileEditor` 画像编辑器，支持按分组查看和编辑画像字段，并在保存后刷新计划相关状态。来源：`docs/ui_redesign/02_用户画像层设计.md`
- [ ] 画像数据来源需要统一，避免侧边栏、向导和计划链路各自读写不同状态。来源：`docs/ui_redesign/02_用户画像层设计.md`
- [ ] 待确认：画像身份卡放在 Chat 区置顶、侧边栏还是独立面板。来源：`docs/ui_redesign/02_用户画像层设计.md`
- [ ] 待确认：画像编辑器使用全屏 Sheet 还是居中 Dialog。来源：`docs/ui_redesign/02_用户画像层设计.md`
- [ ] 待确认：NLP 自动提取画像变更是否必须用户手动确认。来源：`docs/ui_redesign/02_用户画像层设计.md`

## 训练反馈模块

- [ ] 落地 `FeedbackDetailForm` 反馈详细表单，支持完成质量、主观疲劳、不适部位、睡眠恢复和备注的渐进式填写。来源：`docs/ui_redesign/06_训练反馈层设计.md`
- [ ] 落地 `AdaptiveAdjustmentNotice` 调整提示，在反馈后清楚展示“是否调整、调整了什么、为什么调整”。来源：`docs/ui_redesign/06_训练反馈层设计.md`
- [ ] 对“过去训练未反馈”的场景设计提醒或补录入口。来源：`docs/ui_redesign/06_训练反馈层设计.md`
- [ ] 待确认：反馈表单默认展开详细项，还是渐进式展开。来源：`docs/ui_redesign/06_训练反馈层设计.md`

## 数据状态与风险面板模块

- [ ] 落地 `StatusPanel` 数据状态面板，聚合展示本周完成度、当前训练负荷、恢复状态、风险等级和下次训练建议。来源：`docs/ui_redesign/07_数据状态层设计.md`
- [ ] 明确疲劳、睡眠、不适、训练负荷如何共同决定恢复状态和风险等级。来源：`docs/ui_redesign/07_数据状态层设计.md`
- [ ] 待确认：状态面板放在入口层还是独立面板。来源：`docs/ui_redesign/07_数据状态层设计.md`

## 长期进度模块

- [ ] 落地 `CycleProgressBar` 周期进度条，展示第几周、总周数和周期完成比例。来源：`docs/ui_redesign/08_长期进度层设计.md`
- [ ] 落地 `PhaseTimeline` 阶段时间轴，展示各阶段起止周、状态和当前所在阶段。来源：`docs/ui_redesign/08_长期进度层设计.md`
- [ ] 落地 `CompletedWeeksList` 已完成周列表，支持回看每周完成度和关键训练摘要。来源：`docs/ui_redesign/08_长期进度层设计.md`
- [ ] 落地 `AdjustmentHistory` 调整记录，记录每次计划调整的日期、内容和原因。来源：`docs/ui_redesign/08_长期进度层设计.md`
- [ ] 落地 `PhaseReviewCard` 阶段复盘卡，在阶段完成后总结目标达成、关键数据和下一阶段展望。来源：`docs/ui_redesign/08_长期进度层设计.md`
- [ ] 待确认：`PhaseTimeline` 使用横向步骤条还是纵向列表。来源：`docs/ui_redesign/08_长期进度层设计.md`
- [ ] 待确认：调整记录是否对用户默认可见。来源：`docs/ui_redesign/08_长期进度层设计.md`

## 训练规则与个性化配置模块

- [ ] 支持用户自定义板块节奏比例，例如 `2:1:1` 块模式。来源：`TECH_REQUIREMENTS_V2.md`
- [ ] 针对 3 天及以下训练日的高负荷场景做特殊适配，避免高负荷被不合理压缩到少数训练日。来源：`TECH_REQUIREMENTS_V2.md`
- [ ] 将用户个性化周结构约束从“优先作用于首周”扩展到多周逐周差异化约束。来源：`TECH_REQUIREMENTS_V2.md`
- [ ] 接入模板库兜底，避免动作库缺证据时长期只展示“还需要补充课表库”。来源：`TECH_REQUIREMENTS_V2.md`
