# Card Layout Fix TODO

> 目标：专门解决截图里“卡片排版太难看”的问题，把侧栏卡片、跑者画像、历史计划、周计划、日卡从挤压式工程卡片改成可商用、可阅读、适合中国马拉松跑者的训练产品界面。
> 范围：`apps/web/src/pages/index.astro`、`apps/web/src/scripts/app.js`、`apps/web/src/styles/components.css`、`apps/web/src/styles/plan.css`、`apps/web/src/styles/profile-status.css`、`apps/web/src/styles/calendar.css`、`apps/web/src/styles/commercial-light.css`、`apps/web/scripts/smoke-workspace.mjs`、`tests/test_astro_frontend_contract.py`。
> 角色：Frontend owner。只处理前端排版、普通用户信息架构、浏览器截图、前端契约测试。不改后端 API 语义，不假装后端已实现新字段。

## 0. Evidence From User Screenshots

- [ ] E001 记录截图 1：移动/窄侧栏里的跑者画像卡片宽度不足，出现单字换行。
- [ ] E002 记录截图 1：`计划画像` 标题被拆成三行，读起来像排版故障。
- [ ] E003 记录截图 1：`来自 API` 暴露内部来源词，普通跑者不关心。
- [ ] E004 记录截图 1：画像字段以 3 列小方块呈现，导致 `15`、`20`、`12` 等值被截断。
- [ ] E005 记录截图 1：`目标 / 经验 / 上个月月跑量` 这类表单字段被塞进侧栏，侧栏不适合承载编辑表单。
- [ ] E006 记录截图 1：`保存画像草稿 / 写入补充说明 / 生成训练日历` 竖排按钮过重，破坏卡片节奏。
- [ ] E007 记录截图 1：右侧文字 `画像会用于生成训练计划...` 和按钮并列后空间不足。
- [ ] E008 记录截图 1：侧栏内部滚动条很粗，视觉上像后台管理控件。
- [ ] E009 记录截图 1：卡片里卡片太多，形成嵌套卡片堆叠。
- [ ] E010 记录截图 1：左侧导航和跑者画像编辑混在一个滚动容器里，任务边界不清。
- [ ] E011 记录截图 2：周视图日卡太窄，7 天卡片在一行里挤成细竖条。
- [ ] E012 记录截图 2：日卡里的 `训练时间 第1周周二 - 61分钟` 文案冗长，不适合卡片首屏。
- [ ] E013 记录截图 2：三个要点 chip 竖向挤压，`61 分钟 / 训练压力稳定 / 安排来源已确认` 不可快速扫描。
- [ ] E014 记录截图 2：休息日卡片和训练日卡片密度相同，导致重点训练不突出。
- [ ] E015 记录截图 2：周说明里的深灰逻辑块和白底商用风格冲突。
- [ ] E016 记录截图 2：周视图下方大片空白，说明网格密度和容器宽度分配不合理。
- [ ] E017 记录截图 2：`周代理负荷 217` 在普通层过专业，优先级高于用户真正关心的“本周怎么练”。
- [ ] E018 记录截图 2：`可查看整周` 作为按钮文案太弱，无法表达实际动作。
- [ ] E019 记录截图 2：周卡的顶部标题、阶段、指标、展开箭头没有形成清晰视觉层级。
- [ ] E020 记录截图 2：日卡之间没有明确节奏，训练重点和休息日混成一组平铺数据库。
- [ ] E021 记录截图 3：历史计划列表被拆成两个窄列，标题和删除按钮都变成竖向块。
- [ ] E022 记录截图 3：`半程马拉松 · 4 周` 这类标题被迫逐字换行，必须视为 T0 排版缺陷。
- [ ] E023 记录截图 3：删除按钮高度过大，像一个空白卡片，不符合常规列表行为。
- [ ] E024 记录截图 3：`17 条历史已折叠` 被放在虚线小卡里，信息位置弱且视觉噪声大。
- [ ] E025 记录截图 3：历史卡片与画像卡片都在侧栏承载复杂内容，说明侧栏职责过载。
- [ ] E026 记录截图 3：侧栏滚动时底部内容被挤压到不可读状态。
- [ ] E027 记录截图 3：`计划历史 / 历史计划` 重复标题占空间。
- [ ] E028 记录截图 3：按钮 `保存当前计划快照 / 刷新本地历史 / 展开全部历史` 作为大块按钮堆叠，像调试面板。
- [ ] E029 记录截图 3：用户任务应是“恢复哪个计划”，而不是管理本地数据库。
- [ ] E030 记录截图 3：所有操作缺少主次层级，删除操作不应和打开计划同级。

## 1. Root Cause Summary

- [ ] R001 侧栏同时承担导航、搜索、画像编辑、历史管理，导致容器宽度和内容复杂度不匹配。
- [ ] R002 组件缺少“最小可读宽度”规则，内容窄到单字换行仍继续显示。
- [ ] R003 日卡内部使用固定 3 列 chip，忽视容器宽度和中文短语长度。
- [ ] R004 历史列表用卡片网格而不是列表行，导致标题和删除操作失衡。
- [ ] R005 周视图把 7 天训练全部等权展示，没有区分训练日、休息日、关键日。
- [ ] R006 普通层仍展示 `API`、`代理负荷` 等工程/计算语义，降低用户可信度。
- [ ] R007 覆盖层 CSS 修视觉色彩，但没有重新定义卡片信息架构。
- [ ] R008 当前卡片没有清晰的 `title / meta / action / detail` 四层结构。
- [ ] R009 按钮过多且都像主按钮，用户不知道该先点哪个。
- [ ] R010 滚动容器嵌套过多，造成移动端截图里的粗滚动条和阅读割裂。

## 2. Non Negotiable Design Rules

- [ ] D000 设计范式改为“摘要卡入口 + 点击查看解释”，外层卡片不承载完整解释、证据、计算字段和管理操作。
- [ ] D001 侧栏只放导航、搜索、轻摘要，不放完整编辑表单。
- [ ] D002 侧栏内卡片最小可读宽度不足时，必须切换为一列摘要，而不是继续显示表格。
- [ ] D003 跑者画像完整编辑必须进入主内容区、dialog、drawer full panel 或 bottom sheet。
- [ ] D004 历史计划完整列表必须进入主内容区或独立历史面板，侧栏只展示最近 2 条摘要。
- [ ] D005 所有普通用户卡片不得出现 `API`、`raw`、`workflow`、`trace`、`protocol`、`generation_status` 等字段名。
- [ ] D006 普通层不显示 `周代理负荷 217` 作为主信息；可转译为 `本周训练压力：适中/偏高/偏低`。
- [ ] D007 单张卡片只能有一个主要行动按钮。
- [ ] D008 危险操作如删除必须是次级图标/菜单/确认，不和打开计划同级。
- [ ] D009 卡片内部不得出现连续 2 层以上的嵌套卡片。
- [ ] D010 每张卡片必须有清晰主标题，主标题不允许逐字竖排。
- [ ] D011 中文卡片正文行长要控制在 14-28 个中文字符左右。
- [ ] D012 字号层级：卡片标题 16-18px，正文 13-14px，辅助 12px。
- [ ] D013 训练日卡必须优先展示“练什么、多久、强度、安全状态、详情入口”。
- [ ] D014 休息日卡必须更轻，不占用和关键训练同等视觉重量。
- [ ] D015 周说明卡只展示一段核心逻辑，详细依据放入“为什么这样练”。
- [ ] D016 所有 chip 必须允许自然换行或转为横向短标签，不允许单字折行。
- [ ] D017 移动端底部导航不覆盖卡片最后一行内容。
- [ ] D018 移动端 drawer 打开后可以阅读；关闭后不遮挡主内容。
- [ ] D019 视觉风格继续采用白底、浅灰边、克制阴影、小面积科技高光。
- [ ] D020 不把小红书/YouTube 的社交、瀑布流、点赞评论迁移进训练工具。

## 2A. Evidence For Summary Card Plus Details Pattern

- [ ] EV001 Material Design 卡片指南明确：卡片应作为进入更详细信息的入口，不应塞入额外信息或过多动作。迁移：训练日卡外层只放“星期、训练类型、时长、强度/风险、查看安排”。
- [ ] EV002 Material Design 卡片指南明确：卡片主动作通常是卡片本身，补充动作需要克制且位置一致。迁移：日卡点击打开详情；删除、依据、反馈不在每张外层卡片重复堆叠。
- [ ] EV003 Material Design 卡片指南明确：移动端避免卡片内部再放滚动区。迁移：侧栏里的画像/历史不能再出现内部滚动表单和长列表。
- [ ] EV004 Material Design 列表指南明确：列表 tile 最多三行文本，超过三行应进入卡片或后续视图。迁移：侧栏导航项保持 1-2 行，不塞画像字段和历史记录。
- [ ] EV005 Material Design 列表指南明确：最重要内容在左，补充动作在右，主动作占主要空间。迁移：历史列表用“计划名/周期/时间 + 恢复入口”，删除放次级。
- [ ] EV006 Apple HIG disclosure controls 说明：细节应隐藏到相关时再展示。迁移：训练依据、容量解释、证据来源、协议校验默认隐藏在详情层。
- [ ] EV007 UXPin progressive disclosure 总结：复杂信息应按步骤/条件/上下文逐步露出。迁移：计划生成、周计划、日卡详情、依据解释分层，不在同屏全露出。
- [ ] EV008 Microsoft Atlas summary card 模式使用标题、简短说明和截断摘要。迁移：跑者画像摘要只保留目标/水平/可训练日，不再展示完整字段网格。
- [ ] EV009 VA.gov 卡片指南提醒：类似卡片的链接容器不一定是 Card，多个响应项/表单 loop 不应当都伪装成卡片。迁移：画像编辑和历史管理不应藏在侧栏卡片里。
- [ ] EV010 用户提供的小红书截图显示：外层瀑布流只展示封面、短标题、作者/互动等极少摘要，点击进入详情页再看完整内容。迁移：我们保留“轻摘要 + 详情”的节奏，不迁移社交流内容。
- [ ] EV011 用户提供的小红书截图显示：左侧导航是轻量固定入口，主内容是连续内容流，不是左侧滚动表单。迁移：左栏只做导航和摘要，主面板承载完整编辑/历史/详情。
- [ ] EV012 对当前截图的结论：我们的面板割裂，是因为同屏同时存在“导航卡、表单卡、历史管理卡、训练日卡、解释卡”，而且都像同级卡片。下一版必须减少外层卡片种类。
- [ ] EV013 来源：Material Cards，https://www.mdui.org/en/design/1/components/cards.html
- [ ] EV014 来源：Material Lists，https://www.mdui.org/en/design/1/components/lists.html
- [ ] EV015 来源：Apple Disclosure Controls，https://developer.apple.com/design/human-interface-guidelines/disclosure-controls
- [ ] EV016 来源：UXPin Progressive Disclosure，https://www.uxpin.com/studio/blog/what-is-progressive-disclosure/
- [ ] EV017 来源：Microsoft Atlas Card，https://design.learn.microsoft.com/patterns/card.html
- [ ] EV018 来源：VA.gov Card，https://dev-design.va.gov/5612/components/card/

## 2B. Revised Target Pattern

- [ ] RP001 外层日卡只显示 5 件事：日期/星期、训练名、时长或距离、强度/安全状态、详情入口。
- [ ] RP002 外层周卡只显示 4 件事：第几周、阶段、本周重点、训练压力摘要。
- [ ] RP003 外层画像卡只显示 3 件事：目标、当前水平、可训练日。
- [ ] RP004 外层历史卡只显示 3 件事：计划名、周期、更新时间。
- [ ] RP005 外层依据卡只显示“依据是否充足/查看为什么这样练”，不显示证据路径和协议字段。
- [ ] RP006 所有解释信息进入详情层：训练逻辑、依据、容量预算、负荷解释、风险判断、修复日志。
- [ ] RP007 所有管理操作进入详情层或专门面板：删除历史、刷新历史、保存草稿、API 来源。
- [ ] RP008 卡片点击打开详情，而不是在外层展开大段说明。
- [ ] RP009 详情层优先用 side sheet / bottom sheet，而不是继续堆嵌套卡片。
- [ ] RP010 列表/卡片外层要像小红书一样形成统一信息流：同一容器、同一边距、同一圆角、同一文字密度。
- [ ] RP011 侧栏不要再出现“大卡片套小卡片”，只出现导航项和一个轻摘要块。
- [ ] RP012 主面板不要再左一块右一块漂浮，改为连续内容流：生成器、结果摘要、周计划、历史/依据入口。
- [ ] RP013 点击卡片后，详情层标题必须回答“这一天怎么练”。
- [ ] RP014 点击详情后，第二层才回答“为什么这样练”。
- [ ] RP015 点击详情后，第三层才回答“证据和安全边界是什么”。
- [ ] RP016 普通模式默认不展示第三层；专家/依据入口可看第三层。
- [ ] RP017 详情层必须有返回/关闭，不打断当前滚动位置。
- [ ] RP018 详情层不允许出现 raw JSON 或 raw enum。
- [ ] RP019 详情层里的解释必须是中文跑者语言。
- [ ] RP020 该范式优先级高于之前“卡片内直接展示解释”的方案。

## 3. Target Information Architecture

- [ ] IA001 左侧训练导航保留：完善资料、快捷模板、训练日历、训练依据、历史计划。
- [ ] IA002 左侧训练导航每项最多两行：标题一行，说明一行。
- [ ] IA003 左侧跑者资料只显示摘要：目标、当前水平、可训练日。
- [ ] IA004 左侧跑者资料摘要提供一个行动：`编辑我的情况`。
- [ ] IA005 左侧历史计划只显示最近 2 条：计划名称、周期、更新时间。
- [ ] IA006 左侧历史计划摘要提供一个行动：`查看全部历史`。
- [ ] IA007 主工作区保留生成器，但空态标题改为更产品化的 `制定本周训练`。
- [ ] IA008 主工作区下方显示 `我的情况` 主面板，承载完整画像。
- [ ] IA009 历史计划完整列表从侧栏移到主工作区可折叠面板。
- [ ] IA010 周计划区按“本周重点 + 日训练卡片”展示。
- [ ] IA011 周计划顶部保留一行状态：本周训练压力、本周关键课、恢复日数。
- [ ] IA012 周计划不要把所有指标都放进顶部右侧。
- [ ] IA013 周说明里的 `本周安排逻辑` 保留，但不要使用深灰块。
- [ ] IA014 周说明里的 `本周关键词` 和 `执行提醒` 转为浅色 inline chips 或小提示条。
- [ ] IA015 日卡信息顺序：星期/日期、训练类型、时间距离、强度区间、安全状态、详情。
- [ ] IA016 日卡不显示 `训练时间 第1周周二` 这种生成字段。
- [ ] IA017 日卡把 `安排来源已确认` 放入详情或底部微文案，不占主要 chip。
- [ ] IA018 休息日只显示 `休息`、恢复提醒、是否需要反馈。
- [ ] IA019 关键课加轻边框或小标签，不要全卡高亮。
- [ ] IA020 反馈入口保持明显，但不在每张卡片重复大按钮。

## 4. Component Ownership Map

- [ ] C001 `renderRunnerIdentityCard()` 负责跑者摘要，不再负责完整编辑布局。
- [ ] C002 `renderProfilePanel()` 或画像编辑 dialog 负责完整表单。
- [ ] C003 `renderPlanHistory()` 需要拆出 sidebar summary 和 full history list 两种 view。
- [ ] C004 `renderWeekExplanationSummary()` 负责周说明浅卡片化。
- [ ] C005 `renderCalendarGroup()` 负责周卡 header 和日卡 grid。
- [ ] C006 `renderDayCard()` 负责日卡可扫描信息。
- [ ] C007 `components.css` 负责 drawer shell、drawer action、drawer summary。
- [ ] C008 `plan.css` 负责 runner identity summary。
- [ ] C009 `profile-status.css` 负责 full profile/history/feedback panel。
- [ ] C010 `calendar.css` 负责 week/day card grid。
- [ ] C011 `commercial-light.css` 只能做轻主题 token 和最终少量 override，不继续堆大量结构修正。
- [ ] C012 `tests/test_astro_frontend_contract.py` 负责防止 raw 字段和窄卡回归。
- [ ] C013 `smoke-workspace.mjs` 负责浏览器宽度和基础可见性 smoke。
- [ ] C014 文档记录写回 `docs/product/frontend_audit_todo.md`。
- [ ] C015 任何涉及 API 字段变更必须通知 Backend owner，不在本 TODO 内假装完成。

## 5. T0 Fix Slice A - Sidebar Responsibility Reset

- [ ] A001 把侧栏定位为导航栏，不再承载完整画像编辑表单。
- [ ] A002 在 `moveWorkspaceSectionsToDrawer()` 中停止把完整 `#profile` section 移入 drawer。
- [ ] A003 新增轻量 `runner-summary-card`，只显示 3 个摘要字段。
- [ ] A004 摘要字段 1：目标，例如 `半马 PB`。
- [ ] A005 摘要字段 2：经验/水平，例如 `新手/中级/进阶`。
- [ ] A006 摘要字段 3：可训练日，例如 `周二/周四/周末`。
- [ ] A007 摘要卡只保留一个按钮：`编辑我的情况`。
- [ ] A008 摘要卡不显示 `来自 API`。
- [ ] A009 摘要卡的数据来源只在专家层显示。
- [ ] A010 如果资料不足，摘要卡显示 `资料待完善`。
- [ ] A011 如果资料不足，按钮文案仍为 `完善我的情况`。
- [ ] A012 摘要卡宽度必须适配 220px 侧栏。
- [ ] A013 摘要卡内任何中文词不得单字换行。
- [ ] A014 摘要卡标题一行显示不下时使用省略，而不是逐字折行。
- [ ] A015 摘要卡中的数值不要使用小方块网格。
- [ ] A016 摘要卡禁用 3 列 metrics。
- [ ] A017 摘要卡使用纵向 list：label 左、value 右或上下两行。
- [ ] A018 摘要卡用浅色背景，不再嵌套内部卡片。
- [ ] A019 摘要卡和导航项之间留 12px 间距。
- [ ] A020 侧栏滚动区域减少内部滚动条存在感。
- [ ] A021 移动 drawer 打开时摘要卡仍保持一列。
- [ ] A022 移动 drawer 关闭时摘要卡不可见且 inert。
- [ ] A023 修改 `components.css`，让 `.drawer-workspace-sections` 不再承担复杂表单布局。
- [ ] A024 修改 `plan.css`，拆出 `.runner-summary-card` 样式。
- [ ] A025 更新 smoke，检查侧栏可见文本不包含 `来自 API`。
- [ ] A026 更新测试，断言普通层不出现 `来自 API`。
- [ ] A027 浏览器截图：桌面侧栏摘要卡。
- [ ] A028 浏览器截图：移动 drawer 打开摘要卡。
- [ ] A029 验收：侧栏不再出现 `目标 / 经验 / 上个月月跑量` 的完整编辑字段网格。
- [ ] A030 验收：侧栏没有单字竖排。

## 6. T0 Fix Slice B - Profile Editor Relocation

- [ ] B001 完整画像编辑必须在主内容区或 dialog 展示。
- [ ] B002 保留现有 `profileEditorDialog`，优先复用，不新增复杂路由。
- [ ] B003 点击侧栏 `编辑我的情况` 打开 `profileEditorDialog`。
- [ ] B004 主工作区可提供 `我的情况` summary panel，但不塞进 drawer。
- [ ] B005 `profile-derived-metrics` 只在宽容器中两列展示。
- [ ] B006 窄容器下 `profile-derived-metrics` 一列展示。
- [ ] B007 字段 label 与 input 不得在 220px 侧栏里出现。
- [ ] B008 `系统估算平均周跑量` 改为普通层 `估算周跑量`。
- [ ] B009 `系统倒推计划周期` 改为普通层 `建议周期`。
- [ ] B010 来源 `API` 改成 `已同步` 或隐藏。
- [ ] B011 完整编辑页可以显示 `来自 API` 吗：普通模式不显示，专家模式可显示。
- [ ] B012 保存草稿按钮在 dialog footer。
- [ ] B013 写入补充说明按钮在 dialog footer 次级位置。
- [ ] B014 生成训练日历按钮不放在画像编辑卡内部。
- [ ] B015 dialog footer 按钮顺序：取消、保存、使用资料生成。
- [ ] B016 移动 dialog 或 bottom sheet 按钮全宽堆叠。
- [ ] B017 桌面 dialog 按钮右对齐。
- [ ] B018 表单分组标题使用 14px，不抢主标题。
- [ ] B019 表单输入框最小宽度不小于 128px。
- [ ] B020 表单每行最多 2 列，不使用 3 列。
- [ ] B021 移动端表单一列。
- [ ] B022 长字段如 `伤病/疲劳限制` 使用 textarea 或 full-width。
- [ ] B023 输入框 placeholder 不出现过长句。
- [ ] B024 默认值为空时显示 `未填写`，不显示 `unknown`。
- [ ] B025 修改 `renderRunnerIdentityCard()` 输出轻摘要。
- [ ] B026 修改 `renderProfilePanel()` 保留完整面板。
- [ ] B027 修改 `openProfilePanel()` 路径，保证侧栏按钮能打开编辑。
- [ ] B028 更新测试：`runner-identity-card` 只含摘要，不含完整字段网格。
- [ ] B029 截图：主内容画像编辑 dialog 桌面。
- [ ] B030 截图：画像编辑移动。

## 7. T0 Fix Slice C - History List Redesign

- [ ] C001 侧栏内历史计划只显示最近 2 条摘要。
- [ ] C002 摘要行格式：计划名、周期、更新时间。
- [ ] C003 摘要行点击打开计划。
- [ ] C004 删除按钮不在侧栏摘要里展示。
- [ ] C005 删除操作移动到完整历史列表里的 overflow 菜单或次级按钮。
- [ ] C006 侧栏历史卡不使用两列网格。
- [ ] C007 侧栏历史卡标题不允许逐字换行。
- [ ] C008 `保存当前计划快照` 不作为侧栏大卡按钮。
- [ ] C009 `刷新本地历史` 不作为侧栏大卡按钮。
- [ ] C010 `展开全部历史` 改成 `查看全部` 链接。
- [ ] C011 完整历史列表放到主内容区。
- [ ] C012 完整历史列表行布局：左侧计划信息，右侧恢复/删除。
- [ ] C013 删除按钮使用危险色文字或图标，不占整列。
- [ ] C014 历史列表支持空态：`还没有保存过计划`。
- [ ] C015 历史列表支持折叠提示：`还有 17 条，可展开查看`。
- [ ] C016 折叠提示不使用虚线卡片，改为普通文本按钮。
- [ ] C017 历史计划标题行最多两行，超出省略。
- [ ] C018 历史计划时间使用 `今天 06:39` 或 `5月22日 06:39`。
- [ ] C019 不在普通层显示数据库 ID。
- [ ] C020 不在普通层显示 `localStorage`。
- [ ] C021 修改 `renderPlanHistory()`，拆分 `renderHistorySummary()`。
- [ ] C022 新增 `renderHistoryFullList()`。
- [ ] C023 侧栏调用 summary 渲染。
- [ ] C024 主内容调用 full list 渲染。
- [ ] C025 更新保存后刷新逻辑，两个视图都更新。
- [ ] C026 更新删除后刷新逻辑，两个视图都更新。
- [ ] C027 更新测试：历史卡不允许出现窄列删除卡。
- [ ] C028 截图：侧栏最近历史。
- [ ] C029 截图：完整历史列表。
- [ ] C030 验收：没有标题逐字换行。

## 8. T0 Fix Slice D - Week Card Header Cleanup

- [ ] D021 周卡 header 左侧显示 `第 1 周` 和阶段。
- [ ] D022 周卡 header 中间只显示 2-3 个轻 chip。
- [ ] D023 chip 文案使用 `7 天`、`3 休`、`2 关键`。
- [ ] D024 周卡 header 右侧显示 `本周训练压力：适中`。
- [ ] D025 不在普通层显示 `周代理负荷 217`。
- [ ] D026 `可查看整周` 改为 `展开本周` 或 `收起本周`。
- [ ] D027 展开箭头对齐到最右，不挤压标题。
- [ ] D028 header 高度控制在 64-76px。
- [ ] D029 header 不使用大面积浅青渐变。
- [ ] D030 阶段名如 `基础适应期` 放在标题下方小字。
- [ ] D031 负荷值如 217 可保留到专家层。
- [ ] D032 如果后端只给数字，前端用阈值转译为低/适中/偏高。
- [ ] D033 状态转译逻辑必须集中在 helper，不能散落模板。
- [ ] D034 周卡 header 在 720px 下变成两行。
- [ ] D035 周卡 header 在 390px 下不横向溢出。
- [ ] D036 修改 `.week-card-toggle` grid。
- [ ] D037 修改 `.week-card-load` 文案层级。
- [ ] D038 修改 `renderCalendarGroup()` loadLabel。
- [ ] D039 更新测试：普通层不出现 `周代理负荷`。
- [ ] D040 截图：桌面周卡 header。

## 9. T0 Fix Slice E - Week Explanation Card

- [ ] E031 周说明卡从深灰块改为浅色信息区。
- [ ] E032 `训练重点` 左对齐，标题 13px。
- [ ] E033 主说明最多两行，超出放 `查看依据`。
- [ ] E034 `本周关键词` 用 inline chips，不用深色块。
- [ ] E035 `执行提醒` 用 inline note，不用深色块。
- [ ] E036 关键词 chip 不超过 3 个。
- [ ] E037 执行提醒不超过 32 个中文字符。
- [ ] E038 周说明卡内部不嵌套大卡。
- [ ] E039 背景使用 #ffffff 或 #f8fafc。
- [ ] E040 边框使用 `--border`。
- [ ] E041 不使用 `#4b5563` 大面积深灰背景。
- [ ] E042 `本周安排逻辑` 移到右上角或 summary label。
- [ ] E043 视觉重点是训练逻辑，不是 debug box。
- [ ] E044 移动端周说明卡一列。
- [ ] E045 桌面端周说明可 2 列：说明 + 提醒。
- [ ] E046 修改 `.week-explanation-summary` 样式。
- [ ] E047 修改 `renderWeekExplanationSummary()` HTML 结构。
- [ ] E048 更新测试：样式不包含深灰 logic block。
- [ ] E049 截图：周说明桌面。
- [ ] E050 截图：周说明移动。

## 10. T0 Fix Slice F - Day Card Layout

- [ ] F001 日卡不再使用 3 个等宽窄 chip。
- [ ] F002 日卡顶部：星期 + 强度标签。
- [ ] F003 日卡标题：训练类型，例如 `基础期阈值/渐速跑`。
- [ ] F004 日卡标题最多两行。
- [ ] F005 日卡次级：`61 分钟` 或 `休息日`。
- [ ] F006 日卡状态：`训练压力稳定` 改为小状态点 + 文案。
- [ ] F007 `安排来源已确认` 放到底部小字或详情页。
- [ ] F008 `查看详情 >` 改成 `查看安排`。
- [ ] F009 日卡底部左侧显示安全提示。
- [ ] F010 日卡底部右侧显示详情链接。
- [ ] F011 休息日卡标题为 `休息`。
- [ ] F012 休息日卡不显示空 `-` chip。
- [ ] F013 休息日卡显示 `恢复日，完成疲劳/疼痛自检`。
- [ ] F014 关键课卡显示 `关键课` 标签。
- [ ] F015 恢复日卡显示 `恢复` 标签。
- [ ] F016 日卡最小宽度桌面不小于 220px。
- [ ] F017 日卡 grid 桌面使用 `repeat(auto-fit, minmax(220px, 1fr))` 或更合理容器查询。
- [ ] F018 1440px 下不要强行一行 7 张窄卡。
- [ ] F019 可接受 4+3 两行布局，优先可读。
- [ ] F020 移动端一列日卡。
- [ ] F021 日卡内 chip 使用 flex wrap。
- [ ] F022 chip 最小宽度不小于内容宽度。
- [ ] F023 chip 不允许单字换行。
- [ ] F024 chip 文案超过 6 字时改成普通小字。
- [ ] F025 日卡高度不强行一致到过高。
- [ ] F026 日卡避免大面积空白。
- [ ] F027 修改 `renderDayCard()` HTML。
- [ ] F028 修改 `.day-card-essentials`。
- [ ] F029 修改 `.day-card-footer`。
- [ ] F030 更新测试：日卡不渲染 `-` 作为可见 chip。
- [ ] F031 更新测试：日卡包含 `查看安排`。
- [ ] F032 截图：训练日卡桌面。
- [ ] F033 截图：休息日卡桌面。
- [ ] F034 截图：训练日卡移动。
- [ ] F035 截图：休息日卡移动。

## 11. T1 Fix Slice G - Calendar Density Modes

- [ ] G001 周视图默认优先可读，不追求一行塞满 7 天。
- [ ] G002 增加 `紧凑 / 舒适` 视图不在本轮做，先记录为 T2。
- [ ] G003 桌面默认 `舒适`。
- [ ] G004 移动默认 `今日优先`。
- [ ] G005 如果日卡超过 5 张，允许自动换行。
- [ ] G006 关键课可以排在视觉上更突出位置，但不改变实际日期顺序。
- [ ] G007 不使用 masonry 瀑布流，训练日历要保持时间顺序。
- [ ] G008 休息日可以更短，但仍占日期位置。
- [ ] G009 全周概览可以用横向 date strip，但本轮优先修卡片。
- [ ] G010 `calendar-grid` gap 统一 12-14px。
- [ ] G011 大屏最大内容宽度不要让卡片过宽到松散。
- [ ] G012 周卡 body padding 16px。
- [ ] G013 空白区域减少：周卡只包裹实际内容高度。
- [ ] G014 如果一周只有 7 天，不保留多余空白 grid row。
- [ ] G015 更新 1440px 截图。
- [ ] G016 更新 1280px 截图。
- [ ] G017 更新 390px 截图。
- [ ] G018 验收无横向滚动。
- [ ] G019 验收无大面积深色块。
- [ ] G020 验收无单字换行。

## 12. T1 Fix Slice H - Text And Terminology Cleanup

- [ ] H001 `计划画像` 改为 `我的情况`。
- [ ] H002 `来自 API` 改为 `已同步` 或隐藏。
- [ ] H003 `训练时间 第1周周二 - 61分钟` 改为 `61 分钟`。
- [ ] H004 `安排来源已确认` 改为详情里的 `安排依据已确认`。
- [ ] H005 `周代理负荷` 普通层改为 `本周训练压力`。
- [ ] H006 `系统估算平均周跑量` 改为 `估算周跑量`。
- [ ] H007 `系统倒推计划周期` 改为 `建议周期`。
- [ ] H008 `保存当前计划快照` 改为 `保存当前计划`。
- [ ] H009 `刷新本地历史` 改为 `刷新历史`。
- [ ] H010 `展开全部历史` 改为 `查看全部历史`。
- [ ] H011 `训练日历生成器` 后续改为 `制定训练计划`。
- [ ] H012 `普通模式` 后续改为更自然的状态，如 `跑者视图` 或隐藏。
- [ ] H013 不在普通层出现 `API`。
- [ ] H014 不在普通层出现 `proxy`。
- [ ] H015 不在普通层出现 `trace`。
- [ ] H016 不在普通层出现 `protocol`。
- [ ] H017 不在普通层出现 `workflow`。
- [ ] H018 保留 `PB`、`km`，但必须有中文上下文。
- [ ] H019 HMP 缩写只在解释层出现。
- [ ] H020 更新 `runnerFacingText()` fallback 映射。

## 13. T1 Fix Slice I - Visual Token Cleanup

- [ ] I001 定义卡片边框统一 token。
- [ ] I002 定义卡片阴影统一 token。
- [ ] I003 定义 chip 背景统一 token。
- [ ] I004 定义 danger action 样式。
- [ ] I005 定义 subtle link button 样式。
- [ ] I006 定义 sidebar summary card 样式。
- [ ] I007 定义 day card status dot。
- [ ] I008 定义 key workout badge。
- [ ] I009 定义 rest day badge。
- [ ] I010 定义 training pressure badge。
- [ ] I011 把重复 rgba 收敛。
- [ ] I012 把商业轻主题稳定规则迁入组件 CSS。
- [ ] I013 `commercial-light.css` 保留 token 与少量跨组件 override。
- [ ] I014 不再在覆盖层继续堆结构布局。
- [ ] I015 8px 圆角用于内部组件。
- [ ] I016 12-14px 圆角用于外层 panel。
- [ ] I017 主 CTA 只保留一个科技高光。
- [ ] I018 删除按钮不使用主 CTA 色。
- [ ] I019 标签色不超过三类：恢复、关键、风险。
- [ ] I020 验收同屏不出现 5 种以上强调色。

## 14. T1 Fix Slice J - Accessibility And Interaction

- [ ] J001 侧栏摘要按钮必须 keyboard focus 可见。
- [ ] J002 打开画像 dialog 后焦点进入标题或第一个字段。
- [ ] J003 关闭画像 dialog 后焦点回到触发按钮。
- [ ] J004 移动 drawer 打开后背景 inert。
- [ ] J005 移动 drawer 关闭后背景恢复。
- [ ] J006 历史删除需要确认。
- [ ] J007 删除确认文案中文、明确计划名。
- [ ] J008 `查看全部历史` 是 button 或 link，语义正确。
- [ ] J009 日卡 clickable 区域不和内部按钮冲突。
- [ ] J010 日卡详情入口 aria-label 包含日期和训练名。
- [ ] J011 周卡展开按钮 aria-expanded 正确。
- [ ] J012 周卡展开后内容 id 和 aria-controls 对齐。
- [ ] J013 色彩对比达到 WCAG AA。
- [ ] J014 状态不能只靠颜色表达。
- [ ] J015 移动端底部导航不遮挡焦点元素。
- [ ] J016 不使用 `display:none` 隐藏仍可聚焦内容。
- [ ] J017 抽屉滚动条不覆盖内容文字。
- [ ] J018 支持 320px 最小宽度不崩。
- [ ] J019 支持 390px 截图验收。
- [ ] J020 支持 1440px 截图验收。

## 15. T0 Tests To Add

- [ ] T001 测试：普通层源码或渲染文本不包含 `来自 API`。
- [ ] T002 测试：普通层源码或渲染文本不包含 `周代理负荷`。
- [ ] T003 测试：`runner-identity-card` 不包含完整画像字段 label 网格。
- [ ] T004 测试：`runner-identity-card` 包含 `编辑我的情况`。
- [ ] T005 测试：历史侧栏摘要不包含删除按钮。
- [ ] T006 测试：完整历史列表才包含删除入口。
- [ ] T007 测试：日卡不显示 `训练时间 第`。
- [ ] T008 测试：日卡不把 `-` 渲染为 chip。
- [ ] T009 测试：日卡包含 `查看安排`。
- [ ] T010 测试：周说明不使用深灰大块样式。
- [ ] T011 测试：`.calendar-grid` min card width 不小于 220px。
- [ ] T012 测试：`.day-card-essentials` 不再固定三列。
- [ ] T013 测试：移动端 `.focused-workspace` 为单列。
- [ ] T014 测试：侧栏摘要不出现 `API`。
- [ ] T015 测试：普通层不出现 `localStorage`。
- [ ] T016 测试：普通层不出现 `workflow_trace`。
- [ ] T017 测试：普通层不出现 `generation_status`。
- [ ] T018 测试：移动 drawer inert 仍正确。
- [ ] T019 测试：桌面侧栏默认打开不影响 smoke。
- [ ] T020 测试：搜索 `历史` 后能找到历史入口。

## 16. Browser Screenshot Matrix

- [ ] S001 截图：桌面 1440，侧栏默认展开，画像摘要可读。
- [ ] S002 截图：桌面 1440，点击编辑我的情况后 dialog。
- [ ] S003 截图：桌面 1440，历史摘要侧栏。
- [ ] S004 截图：桌面 1440，完整历史列表。
- [ ] S005 截图：桌面 1440，周视图展开。
- [ ] S006 截图：桌面 1440，日卡训练日。
- [ ] S007 截图：桌面 1440，日卡休息日。
- [ ] S008 截图：桌面 1440，周说明浅色卡。
- [ ] S009 截图：移动 390，主生成卡。
- [ ] S010 截图：移动 390，drawer 打开。
- [ ] S011 截图：移动 390，画像编辑。
- [ ] S012 截图：移动 390，历史列表。
- [ ] S013 截图：移动 390，周视图。
- [ ] S014 截图：移动 390，训练日卡。
- [ ] S015 截图：移动 390，休息日卡。
- [ ] S016 截图：移动 390，底部导航不遮挡。
- [ ] S017 截图：320px 最小宽度 smoke。
- [ ] S018 截图：1280px 常见笔记本。
- [ ] S019 截图：生成后有反馈历史。
- [ ] S020 截图：医疗红旗路径保持阻断。

## 17. Visual Acceptance Checks

- [ ] V001 没有任何卡片标题逐字换行。
- [ ] V002 没有任何按钮文字逐字换行。
- [ ] V003 没有任何 chip 只显示单个数字且无上下文。
- [ ] V004 没有 `API` 出现在普通层。
- [ ] V005 没有 `代理负荷` 出现在普通层主信息。
- [ ] V006 没有深灰逻辑块破坏白底风格。
- [ ] V007 侧栏可一眼看出是导航，不是表单。
- [ ] V008 画像编辑可一眼看出是编辑，不是导航卡。
- [ ] V009 历史计划可一眼看出计划名、周期、时间。
- [ ] V010 删除操作不抢主要视觉。
- [ ] V011 周计划可一眼看出本周重点。
- [ ] V012 日卡可一眼看出今天练什么。
- [ ] V013 休息日比训练日更轻。
- [ ] V014 关键训练比普通训练更醒目但不夸张。
- [ ] V015 移动端无横向滚动。
- [ ] V016 移动端底部导航不挡文字。
- [ ] V017 drawer 内部滚动条不压内容。
- [ ] V018 主 CTA 仍明显。
- [ ] V019 次级按钮不会像主按钮。
- [ ] V020 空态不显得像后台配置页。

## 18. Implementation Order

- [ ] O001 先做侧栏职责切分。
- [ ] O002 再做画像摘要。
- [ ] O003 再迁移完整画像编辑入口。
- [ ] O004 再拆历史摘要和完整历史列表。
- [ ] O005 再修周卡 header 文案。
- [ ] O006 再修周说明浅色卡。
- [ ] O007 再修日卡 HTML 结构。
- [ ] O008 再修 calendar grid。
- [ ] O009 再收敛普通层术语。
- [ ] O010 再补前端契约测试。
- [ ] O011 再跑 build。
- [ ] O012 再跑 pytest。
- [ ] O013 再跑 smoke。
- [ ] O014 再截桌面图。
- [ ] O015 再截移动图。
- [ ] O016 再做人工视觉复核。
- [ ] O017 再更新报告。
- [ ] O018 再更新共享契约。
- [ ] O019 再决定下一轮是否进入详情 modal。
- [ ] O020 不在这轮引入新依赖。

## 19. File Level TODO

- [ ] F101 `apps/web/src/scripts/app.js`：拆 `renderRunnerIdentityCard()` 为 summary 输出。
- [ ] F102 `apps/web/src/scripts/app.js`：新增 `renderRunnerProfileSummary()`.
- [ ] F103 `apps/web/src/scripts/app.js`：保留 full profile editor 在 dialog。
- [ ] F104 `apps/web/src/scripts/app.js`：拆 `renderPlanHistory()`。
- [ ] F105 `apps/web/src/scripts/app.js`：新增 `renderPlanHistorySummary()`.
- [ ] F106 `apps/web/src/scripts/app.js`：新增 `renderPlanHistoryFullList()`.
- [ ] F107 `apps/web/src/scripts/app.js`：删除侧栏 summary 中的删除按钮。
- [ ] F108 `apps/web/src/scripts/app.js`：转译 `来自 API`。
- [ ] F109 `apps/web/src/scripts/app.js`：转译 `周代理负荷`。
- [ ] F110 `apps/web/src/scripts/app.js`：简化日卡时间文案。
- [ ] F111 `apps/web/src/scripts/app.js`：日卡休息日不显示 `-`。
- [ ] F112 `apps/web/src/scripts/app.js`：周说明 HTML 改浅色结构。
- [ ] F113 `apps/web/src/pages/index.astro`：确认主内容存在历史 full panel 容器。
- [ ] F114 `apps/web/src/pages/index.astro`：确认侧栏只包含 summary 容器。
- [ ] F115 `components.css`：侧栏 summary card 样式。
- [ ] F116 `components.css`：drawer scrollbar 和 spacing。
- [ ] F117 `plan.css`：runner summary 样式。
- [ ] F118 `profile-status.css`：full history list 样式。
- [ ] F119 `calendar.css`：week header 样式。
- [ ] F120 `calendar.css`：day card 样式。
- [ ] F121 `commercial-light.css`：删除临时结构性 override。
- [ ] F122 `responsive.css`：移动端单列确认。
- [ ] F123 `smoke-workspace.mjs`：增加无 raw 字段检查。
- [ ] F124 `test_astro_frontend_contract.py`：增加布局契约。
- [ ] F125 `docs/product/frontend_audit_todo.md`：记录完成状态。

## 20. Regression Commands

- [ ] RC001 `C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -m pytest -p no:cacheprovider tests\test_astro_frontend_contract.py -q`
- [ ] RC002 `cd apps/web; npm run build`
- [ ] RC003 `cd apps/web; $env:WORKSPACE_URL='http://127.0.0.1:4331/#workspace'; npm run smoke:workspace`
- [ ] RC004 `git diff --check`
- [ ] RC005 Playwright desktop screenshot 1440x960。
- [ ] RC006 Playwright mobile screenshot 390x844。
- [ ] RC007 Playwright mobile drawer screenshot。
- [ ] RC008 Manual visual check against user screenshots。
- [ ] RC009 Verify no unrelated backend files touched by frontend owner.
- [ ] RC010 Verify no new dependency added.

## 21. Explicit Non Goals

- [ ] N001 不在本轮重做整个视觉系统。
- [ ] N002 不在本轮迁移到 Figma。
- [ ] N003 不在本轮引入 shadcn/ui。
- [ ] N004 不在本轮改后端 API。
- [ ] N005 不在本轮修改训练算法。
- [ ] N006 不在本轮新增多 agent 编排。
- [ ] N007 不在本轮做完整 GraphRAG UI。
- [ ] N008 不在本轮增加社交功能。
- [ ] N009 不在本轮模仿小红书品牌红。
- [ ] N010 不在本轮把训练日历变成瀑布流。
- [ ] N011 不在本轮展示设备级恢复分。
- [ ] N012 不在本轮展示 Garmin/COROS 真实生理负荷。
- [ ] N013 不在本轮做订阅商业化页面。
- [ ] N014 不在本轮做登录/多租户。
- [ ] N015 不在本轮提交 git。

## 22. Definition Of Done

- [ ] DONE001 用户截图里的三类丑卡问题都有对应修复。
- [ ] DONE002 侧栏不再有完整画像编辑表单。
- [ ] DONE003 侧栏不再有完整历史管理列表。
- [ ] DONE004 周卡没有深灰逻辑块。
- [ ] DONE005 日卡没有三列窄 chip。
- [ ] DONE006 桌面截图无单字换行。
- [ ] DONE007 移动截图无单字换行。
- [ ] DONE008 普通层无 `API`。
- [ ] DONE009 普通层无 `周代理负荷`。
- [ ] DONE010 普通层无 raw enum。
- [ ] DONE011 契约测试通过。
- [ ] DONE012 build 通过。
- [ ] DONE013 smoke 通过。
- [ ] DONE014 diff check 通过。
- [ ] DONE015 文档记录截图证据。
- [ ] DONE016 共享契约更新前端 owner 签收范围。
- [ ] DONE017 未替 backend/QA 签收。
- [ ] DONE018 未触碰无关后端改动。
- [ ] DONE019 未新增依赖。
- [ ] DONE020 用户可以从截图直观看到“这不是后台控制台”。

## 23. Micro Tasks For Sidebar Summary

- [ ] M001 设计 summary card HTML。
- [ ] M002 设计 summary row 样式。
- [ ] M003 设计 summary empty state。
- [ ] M004 设计 summary edit action。
- [ ] M005 设计 summary history action。
- [ ] M006 替换旧 identity metrics。
- [ ] M007 删除三列 identity metrics 在侧栏的使用。
- [ ] M008 保留 profile editor 数据绑定。
- [ ] M009 确认保存后 summary 更新。
- [ ] M010 确认载入后 summary 更新。
- [ ] M011 确认 API 失败后 summary 不崩。
- [ ] M012 确认本地 draft 后 summary 文案。
- [ ] M013 确认空目标显示。
- [ ] M014 确认可训练日过长省略。
- [ ] M015 确认 PB 信息不过度展示。
- [ ] M016 确认伤病限制不挤入摘要。
- [ ] M017 确认移动 drawer 摘要可读。
- [ ] M018 确认桌面侧栏摘要可读。
- [ ] M019 确认没有二级滚动条。
- [ ] M020 确认截图保存。

## 24. Micro Tasks For History

- [ ] M021 设计 history summary row。
- [ ] M022 设计 full history row。
- [ ] M023 设计 recent history limit。
- [ ] M024 设计 empty history。
- [ ] M025 设计 collapsed count。
- [ ] M026 设计 delete confirm。
- [ ] M027 设计 restore action。
- [ ] M028 设计 saved timestamp。
- [ ] M029 设计 plan duration chip。
- [ ] M030 设计 title truncation。
- [ ] M031 确认 2 条 summary。
- [ ] M032 确认 17 条折叠文案。
- [ ] M033 确认删除不在侧栏。
- [ ] M034 确认刷新不作为大按钮。
- [ ] M035 确认保存计划不作为大按钮堆叠。
- [ ] M036 确认历史标题不重复。
- [ ] M037 确认主内容历史列表可读。
- [ ] M038 确认移动历史列表可读。
- [ ] M039 确认截图保存。
- [ ] M040 确认测试覆盖。

## 25. Micro Tasks For Day Cards

- [ ] M041 设计 day card header。
- [ ] M042 设计 date label。
- [ ] M043 设计 intensity badge。
- [ ] M044 设计 workout title。
- [ ] M045 设计 duration line。
- [ ] M046 设计 pressure state。
- [ ] M047 设计 source note。
- [ ] M048 设计 safety note。
- [ ] M049 设计 detail link。
- [ ] M050 设计 rest day variant。
- [ ] M051 设计 key workout variant。
- [ ] M052 设计 recovery variant。
- [ ] M053 设计 needs recheck variant。
- [ ] M054 设计 high load variant。
- [ ] M055 删除固定三列 chip。
- [ ] M056 删除 `-` chip。
- [ ] M057 改 footer copy。
- [ ] M058 改 title max lines。
- [ ] M059 改 min card width。
- [ ] M060 截图验证。

## 26. Micro Tasks For Week Cards

- [ ] M061 设计 week header left。
- [ ] M062 设计 week header metrics。
- [ ] M063 设计 week pressure translation。
- [ ] M064 设计 expand action。
- [ ] M065 设计 shallow explanation card。
- [ ] M066 设计 keyword chips。
- [ ] M067 设计 execution note。
- [ ] M068 删除 dark logic block。
- [ ] M069 改 expanded body padding。
- [ ] M070 改 calendar grid。
- [ ] M071 改 1440 layout。
- [ ] M072 改 1280 layout。
- [ ] M073 改 mobile layout。
- [ ] M074 改 empty area。
- [ ] M075 改 rest day density。
- [ ] M076 改 key workout emphasis。
- [ ] M077 改 aria labels。
- [ ] M078 改 tests。
- [ ] M079 截图验证。
- [ ] M080 文档记录。

## 27. QA Checklist

- [ ] Q001 桌面打开页面。
- [ ] Q002 生成一个 4 周半马计划。
- [ ] Q003 展开第 1 周。
- [ ] Q004 检查周说明。
- [ ] Q005 检查 7 天卡片。
- [ ] Q006 打开训练日详情。
- [ ] Q007 打开休息日详情。
- [ ] Q008 打开训练依据。
- [ ] Q009 打开侧栏。
- [ ] Q010 编辑我的情况。
- [ ] Q011 保存画像。
- [ ] Q012 保存计划。
- [ ] Q013 查看历史。
- [ ] Q014 恢复历史。
- [ ] Q015 删除历史。
- [ ] Q016 移动端重复 Q001-Q010。
- [ ] Q017 检查无 raw 字段。
- [ ] Q018 检查无横向滚动。
- [ ] Q019 检查按钮可点击。
- [ ] Q020 检查焦点可见。

## 28. Final Signoff Notes

- [ ] SIGN001 完成后更新 `docs/product/frontend_audit_todo.md`。
- [ ] SIGN002 完成后更新 `docs/product/reports/frontend_product_audit_2026-05-22.md`。
- [ ] SIGN003 完成后更新 `docs/quality/shared_delivery_contract.md` 的前端签收范围。
- [ ] SIGN004 完成后不要说最终商用完成，除非生成态、反馈态、红旗态、QA 都签收。
- [ ] SIGN005 完成后报告精确命令和截图路径。
