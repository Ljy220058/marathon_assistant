# 方案五「温感大地」前端重构 TODO

> 角色：Frontend owner  
> 工作目录：`C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手`  
> 目标：把已选配色方案五「温感大地」落成可商用的浅色训练助手 UI。  
> 边界：不改后端，不新增依赖，不破坏现有 DOM/data attribute 契约，不把 raw 字段暴露给普通跑者。  
> 本轮实际子智能体数量：0。DS4Pro batch 只作为并发评审工具，不算挂起子智能体。  

## 0. 方案五基线

- 名称：温感大地。
- 用途：默认浅色商业主题候选。
- 背景：`#FAF8F5`。
- 卡片：`#FFFFFF`。
- 次级卡片：`#F5F1EC`。
- 主文字：`#1E1C1A`。
- 次文字：`#7A7268`。
- 边框：`#E8E2DA`。
- 主行动色：`#C5764A`。
- 成功：`#5B8C5A`。
- 警告：`#D9974A`。
- 危险：`#C1554A`。
- 使用边界：陶土色只用于主行动、当前选中态和极少量品牌强调，不能用于风险/警告/危险状态。

## 1. DS4Pro 并发代码审计记录

- 工具：`mcp__deepseek_ds4pro__.ds4pro_batch`。
- 并发：10。
- 任务数：10。
- 成功：10。
- 失败：0。
- 审计域：
  - token 架构。
  - `commercial-light.css` 覆盖层。
  - 顶部导航和左侧抽屉。
  - 日卡和周卡。
  - `#calendarActionPanel`。
  - day modal 与 feedback。
  - 前端契约测试。
  - 共享契约与文档。
  - phase/task/agent/skills。
  - 风险审计。
- DS4Pro 主要结论：
  - 当前 `--accent-1/2/3` 和 `--tech-accent` 是颜色命名，不是语义命名，迁移到方案五会失控。
  - `commercial-light.css` 是最终覆盖层巨石，应先 token 化，再逐步迁移组件选择器。
  - 导航现有红点、lime 渐变、cyan 强调会造成拼贴感，应统一成暖土语义。
  - 日卡/周卡在 `calendar.css` 和 `commercial-light.css` 中存在暗色与浅色双重定义，长期应收敛到 token 驱动。
  - `#calendarActionPanel` 必须确保主训练行动卡视觉权重高于安全和反馈 mini 卡。
  - day modal active tab、feedback selected summary、medical_referral fail-closed 是强契约。
  - 测试中旧色值硬编码会阻塞重构，应迁移为 token/语义契约。
  - 陶土主色与 warning/danger 色相接近，是 T0 风险，必须靠用途隔离和非颜色辅助降低误判。

## 2. 参与角色与 Skills

### 2.1 Agent 角色

- Frontend owner：
  - 负责方案五落地。
  - 负责 Astro 工作台、日历、日卡、EvidenceDrawer、反馈、状态面板 UI。
  - 负责普通用户层隐藏内部字段。
  - 负责前端 build、browser smoke、截图验收。
- DS4Pro 并发 reviewer：
  - 只做分析与方案拆解。
  - 不直接改文件。
  - 每轮可按 10 到 20 并发分批跑，避免不稳定 wrapper。
- QA/reviewer：
  - 只读复核截图、合同测试、色彩语义、医疗红旗路径和脏工作区边界。
  - 不替 Frontend owner 签收。
- Backend read-only reviewer：
  - 只检查 API 字段和共享契约是否影响前端。
  - 不改前端文件。
  - 需要时最多开 1 个子智能体，完成后必须关闭。
- Version owner：
  - 只负责 dirty worktree 边界、禁止 broad stage、文件清单和最终 git 建议。

### 2.2 Skills 分派

- `frontend-designer`：
  - Mode C Theme：定义 token。
  - Mode D Refactor：迁移样式覆盖。
  - Mode E Audit：审计色彩、可读性、交互状态。
- `browser:browser`：
  - 打开本地预览。
  - 桌面和移动截图。
  - 检查 hover、modal、feedback、medical_referral。
- `DeepSeek DS4Pro`：
  - 批量代码审计。
  - 并发评审设计迁移风险。
  - 输出下一轮 TODO 和验收矩阵。
- `codex-engineering-workflow`：
  - 按 TODO 执行。
  - 每阶段完成后运行验证。
- `security-scanner`：
  - 只在涉及 token、localStorage、API token 显示、反馈安全路径时调用。
- `humanizer-zh`：
  - 用于普通用户层中文文案复核，避免变量名和英文原始字段。

## 3. Phase 0：基线冻结和证据准备

### P0.T1 读取共享契约

- 文件：`docs/quality/shared_delivery_contract.md`。
- TODO：
  - [ ] 确认本轮角色是 Frontend owner。
  - [ ] 确认普通层不能展示 raw 字段。
  - [ ] 确认 `medical_referral` 必须 fail-closed。
  - [ ] 确认 `training_load` 只能面向用户说“计划代理负荷/估算”。
  - [ ] 确认 dirty worktree 很重，禁止 `git add .`。
- 验收：
  - [ ] 本文档记录角色和边界。
  - [ ] 后续任何共享契约变更都写清角色、范围、未签收项、验证命令。

### P0.T2 冻结当前前端入口

- 文件：
  - `apps/web/src/pages/index.astro`。
  - `apps/web/src/scripts/app.js`。
  - `apps/web/src/styles/global.css`。
- TODO：
  - [ ] 确认 `global.css` 仍按最后导入 `commercial-light.css`。
  - [ ] 确认 `app.js` 仍是真实运行主逻辑。
  - [ ] 确认 marker 模块没有被误称为模块化完成。
  - [ ] 确认 `#workspaceFlow`、`#calendarActionPanel`、`data-reading-fatigue-guard`、`data-secondary-reading-layer` 仍存在。
- 验收：
  - [ ] 不改变 DOM/data attribute 契约。
  - [ ] 不改变 API 调用路径。

### P0.T3 生成本轮代码扫描清单

- 命令：
  - `git status --short --branch`
  - `rg -n "#|rgba|gradient|shadow|accent|tech-accent|primary-button|day-card|calendar-action|side-drawer|top-nav|feedback|risk|warning|danger|success|modal|segmented|model-provider" apps/web/src/styles apps/web/src/pages apps/web/src/scripts tests/test_astro_frontend_contract.py`
- TODO：
  - [ ] 列出所有硬编码旧色。
  - [ ] 列出所有 `--accent-1/2/3` 和 `--tech-accent` 用法。
  - [ ] 列出所有 active/hover/selected/focus 颜色。
  - [ ] 列出所有 medical_referral、risk、feedback 相关普通层 selector。
- 验收：
  - [ ] 扫描结果沉淀到本文件或后续 review TODO。

## 4. Phase 1：Token 架构重构

### P1.T1 建立方案五语义 token

- 文件：`apps/web/src/styles/commercial-light.css`。
- 优先策略：先在现有覆盖层中建立语义 token，不立即拆新文件，降低 diff 风险。
- TODO：
  - [ ] 将 `:root` 的色值改成方案五。
  - [ ] 保留兼容 token：`--bg`、`--panel`、`--panel-muted`、`--border`、`--text`、`--muted`、`--success`、`--warning`、`--danger`。
  - [ ] 新增语义别名：
    - `--surface`
    - `--surface-muted`
    - `--text-primary`
    - `--text-secondary`
    - `--action-primary`
    - `--action-primary-hover`
    - `--state-success`
    - `--state-warning`
    - `--state-danger`
    - `--focus-ring`
    - `--selection-bg`
  - [ ] 将 `--tech-accent` 改为过渡兼容 token，不再用于大面积填充。
  - [ ] 注释标记 `--accent-1/2/3` 为 legacy aliases。
- 验收：
  - [ ] 任意组件新增样式不直接写 `#C5764A`，必须走 token。
  - [ ] `--tech-accent: #eafe52` 不再作为测试硬要求。
  - [ ] 主色不和 danger/warning 共享状态语义。

### P1.T2 定义状态色边界

- 文件：`apps/web/src/styles/commercial-light.css`。
- TODO：
  - [ ] success 只用于“可以执行/完成/正常”。
  - [ ] warning 只用于“注意恢复/待复核/负荷偏高”。
  - [ ] danger 只用于“医疗红旗/停止训练/删除等危险操作”。
  - [ ] accent 只用于主按钮、当前选中、链接小面积强调。
  - [ ] 不允许 accent 用作 risk pill 的状态色。
- 验收：
  - [ ] 安全 chip 不是单靠颜色，还要保留文字。
  - [ ] danger 和 warning 在灰度截图里仍能靠文案识别。

### P1.T3 降低视觉重量 token

- 文件：`apps/web/src/styles/commercial-light.css`。
- TODO：
  - [ ] `--shadow` 降低为浅暖灰阴影。
  - [ ] `--shadow-soft` 改为极轻边界阴影。
  - [ ] `--card-surface` 保持白色或近白，不使用灰重底。
  - [ ] `--soft-line` 改为暖灰分隔线。
- 验收：
  - [ ] 卡片淡，但边界可辨。
  - [ ] 不再靠大阴影制造层级。

## 5. Phase 2：覆盖层债务收敛

### P2.T1 改造 `commercial-light.css` 注释和职责

- 当前问题：文件头注释乱码且指向“小红书式轻导航”，容易误导后续开发。
- TODO：
  - [ ] 修复文件头中文编码。
  - [ ] 改成“温感大地商业浅色主题覆盖层”。
  - [ ] 写清本文件只允许做 token 和最终轻覆盖，不承担长期组件结构。
- 验收：
  - [ ] 注释是可读中文。
  - [ ] 不出现“照抄小红书”的表达。

### P2.T2 清除大面积 lime/cyan/red 旧风格

- 文件：`apps/web/src/styles/commercial-light.css`。
- TODO：
  - [ ] `body::selection` 从 lime 改为淡陶土或暖沙。
  - [ ] `brand-mark` 从 lime/cyan 渐变改为极淡暖土面或单色浅底。
  - [ ] `side-drawer[open] .side-drawer-toggle` 去掉 lime gradient。
  - [ ] `drawer-toggle-affordance` 去掉 lime 底。
  - [ ] `drawer-action.primary/is-active` 去掉 lime gradient。
  - [ ] `drawer-action::before` active 不用 red dot。
  - [ ] `progress-track-fill` 去掉 success/teal/lime 三色高饱和渐变。
  - [ ] `phase-progress-track i` 不再用 `var(--tech-accent)`。
- 验收：
  - [ ] `rg "#eafe52|234, 254, 82|lime|cyan"` 在普通主题关键路径中不再命中视觉输出规则。
  - [ ] 仍允许文档或历史注释中出现旧色，但不得影响 CSS。

### P2.T3 保留轻覆盖，不做结构大改

- TODO：
  - [ ] 不改变 `.app-layout` 主布局。
  - [ ] 不改变日历默认折叠行为。
  - [ ] 不改变 day modal tab DOM。
  - [ ] 不改变 feedback quick-first DOM。
- 验收：
  - [ ] `tests/test_astro_frontend_contract.py` 的结构契约仍过。

## 6. Phase 3：导航与左侧抽屉

### P3.T1 顶部导航

- 文件：`apps/web/src/styles/commercial-light.css`。
- TODO：
  - [ ] top-nav 背景从冷白改为暖白半透明。
  - [ ] nav pill 背景改为 `surface-muted`。
  - [ ] nav hover 使用淡陶土底，不用红点。
  - [ ] focus-visible 使用 `--focus-ring`。
  - [ ] 搜索框背景使用 `surface-muted`，placeholder 保持可读。
- 验收：
  - [ ] 顶部导航不抢主训练卡。
  - [ ] hover/focus 在键盘操作下可见。

### P3.T2 左侧抽屉

- 文件：
  - `apps/web/src/styles/components.css`。
  - `apps/web/src/styles/commercial-light.css`。
- TODO：
  - [ ] 抽屉默认态保持轻边框和白底。
  - [ ] 打开态用暖灰面和细边框，不用大面积渐变。
  - [ ] active 位置提示改为左侧短线或小圆点，颜色为 `--action-primary`，不是 red。
  - [ ] 导航说明文字使用 `--text-secondary`。
  - [ ] 移动端抽屉阴影降低，避免像浮层广告。
- 验收：
  - [ ] 左侧导航像工具导航，不像社交 feed。
  - [ ] 移动端无横向溢出。

## 7. Phase 4：按钮、流程条和基础控件

### P4.T1 主按钮

- 文件：
  - `apps/web/src/styles/components.css`。
  - `apps/web/src/styles/commercial-light.css`。
- TODO：
  - [ ] `.primary-button` 从 lime gradient 改成实色陶土或深陶土。
  - [ ] hover 改成更深一档，不使用发光。
  - [ ] disabled 使用暖灰，不使用低对比文字。
  - [ ] 反馈 modal 的提交按钮保持实色。
  - [ ] “生成调整建议”等次级操作使用 secondary/ghost。
- 验收：
  - [ ] 主按钮是页面唯一高视觉权重行动。
  - [ ] 主按钮文字对比度大于等于 4.5:1。

### P4.T2 次级按钮与 text-action

- 文件：`apps/web/src/styles/calendar.css`、`commercial-light.css`。
- TODO：
  - [ ] `.text-action` 使用陶土文字和极浅陶土底。
  - [ ] 次级按钮使用白底暖灰边框。
  - [ ] 危险按钮使用 danger，不复用 accent。
- 验收：
  - [ ] “查看依据”视觉权重低于“记录反馈”。
  - [ ] “跳过/不适”不被误认为普通主行动。

### P4.T3 流程条和进度

- 文件：`apps/web/src/styles/components.css`、`commercial-light.css`。
- TODO：
  - [ ] `progress-track-fill` 改为单色或低饱和两色。
  - [ ] `progress-runner` 光环改为极淡暖土。
  - [ ] `workspace-flow-step.is-current` 改为细下划线或淡底。
  - [ ] 不再用 lime 下划线表达当前步骤。
- 验收：
  - [ ] 流程条是辅助反馈，不抢“今日训练”。

## 8. Phase 5：日历行动面板

### P5.T1 `#calendarActionPanel` 主卡

- 文件：`apps/web/src/styles/calendar-actions.css`、`commercial-light.css`。
- TODO：
  - [ ] 主下一次训练卡使用白底和轻阴影。
  - [ ] 左侧或顶部用细陶土线表达主行动。
  - [ ] 标题/训练内容对比度高于 mini 卡。
  - [ ] 主卡按钮使用 primary 或 text-action high emphasis。
  - [ ] 不使用大面积陶土背景。
- 验收：
  - [ ] 第一眼能看到下一次怎么练。

### P5.T2 三个 mini 摘要

- 文件：`apps/web/src/styles/calendar-actions.css`。
- TODO：
  - [ ] 本周重点使用中性暖灰。
  - [ ] 安全提醒仅在 warning/danger 时用状态边框。
  - [ ] 反馈入口使用中性或浅陶土，不用危险色。
  - [ ] mini 卡说明文字默认隐藏策略不变。
  - [ ] mobile 下 mini 卡不挤压主卡。
- 验收：
  - [ ] 右侧 mini 卡不比主卡更抢眼。
  - [ ] 安全提醒仍能在风险时可见。

## 9. Phase 6：日卡和周卡

### P6.T1 日卡

- 文件：`apps/web/src/styles/calendar.css`、`commercial-light.css`。
- TODO：
  - [ ] `.day-card` 默认背景使用 `surface`。
  - [ ] `.day-card.rest` 使用 `surface-muted`，不是冷灰。
  - [ ] hover 用边框和微阴影，不用蓝色渐变。
  - [ ] `.day-card-top span` 用暖灰 pill。
  - [ ] `.day-card-essentials span` 用低视觉重量暖灰底。
  - [ ] `.day-risk-pill` 正常态使用 success，warning/danger 使用对应状态色。
  - [ ] `.day-load-tooltip` 改成浅色可读，避免暗底。
- 验收：
  - [ ] 单张日卡只回答当天训练重点。
  - [ ] 不展示 7日/42日占比等计算字段。

### P6.T2 周卡

- 文件：`apps/web/src/styles/calendar.css`、`commercial-light.css`。
- TODO：
  - [ ] `.week-card` 白底暖灰边框。
  - [ ] `.week-card.is-expanded` 使用淡陶土边框或顶部线。
  - [ ] `.week-card-metrics i` 使用暖灰 pill，不用紫色。
  - [ ] `.week-card-chevron` 使用文本色或 accent 小面积。
  - [ ] 周卡默认折叠策略不变。
- 验收：
  - [ ] 默认视图不造成长页面阅读疲劳。

## 10. Phase 7：Day modal 与反馈

### P7.T1 Modal 基础层

- 文件：`apps/web/src/styles/modal.css`、`commercial-light.css`。
- TODO：
  - [ ] backdrop 保持安全聚焦，但透明度降低到不压迫。
  - [ ] modal card 使用白底和暖灰边框。
  - [ ] modal hero 不用青色渐变。
  - [ ] sticky actions 使用暖白半透明。
- 验收：
  - [ ] 移动端 bottom-sheet 仍正常。
  - [ ] 关闭按钮可见、可点击、可键盘聚焦。

### P7.T2 Tab active

- 文件：`apps/web/src/styles/modal.css`、`commercial-light.css`。
- TODO：
  - [ ] `.day-modal-tab-nav button.active` 从 `#e9fbff` 改为淡陶土或暖灰底。
  - [ ] active 用底部 2px 线或边框表达，不大面积填色。
  - [ ] plan/audit/feedback 三个 tab 保持一致。
- 验收：
  - [ ] 测试不再硬断言旧 teal border。

### P7.T3 Feedback quick-first

- 文件：`apps/web/src/scripts/app.js`、`modal.css`、`commercial-light.css`。
- TODO：
  - [ ] 不改变 quick-first 流程。
  - [ ] 完成/部分/跳过不适按钮的 active 态使用明确选中样式。
  - [ ] 跳过/不适使用 danger 边界，但不要铺满红底。
  - [ ] `feedback-selected-summary` 使用暖白或 `surface-muted`，文字对比足够。
  - [ ] `modal-feedback-detail` 默认折叠不变。
- 验收：
  - [ ] 普通用户先看到“已选择”和提交按钮。
  - [ ] 补充细节不抢主路径。

### P7.T4 Medical referral fail-closed

- 文件：`apps/web/src/scripts/app.js`。
- TODO：
  - [ ] 确认 `isMedicalReferralFeedback()` 仍阻断普通 regenerate。
  - [ ] medical_referral 卡使用 danger 边界、图标/文字，不只靠红色。
  - [ ] 不展示“生成调整版计划”的普通路径。
  - [ ] 浏览器截图覆盖选择医疗红旗后的结果。
- 验收：
  - [ ] medical_referral 仍 fail-closed。

## 11. Phase 8：证据、审计、专家层

### P8.T1 普通层和专家层边界

- 文件：`apps/web/src/scripts/app.js`。
- TODO：
  - [ ] 普通层不显示 `workflow_trace`、`protocol_state`、`risk_gate`、`protocol_recheck` 字段名。
  - [ ] 专家层可以展示审计指标，但要中文解释。
  - [ ] Audit panel 配色可以更密，但仍使用 warm-earth tokens。
- 验收：
  - [ ] 普通用户只看到安全判断、是否继续、建议动作、影响范围。

### P8.T2 EvidenceDrawer

- 文件：`apps/web/src/styles/evidence.css`、`commercial-light.css`。
- TODO：
  - [ ] 证据卡片使用浅底和暖灰边框。
  - [ ] source path、raw id 默认专家层或折叠层。
  - [ ] 无证据空态用“暂无可核验证据”，不要伪造引用。
- 验收：
  - [ ] 证据层不破坏阅读疲劳策略。

## 12. Phase 9：测试迁移

### P9.T1 契约测试从旧色硬编码迁移

- 文件：`tests/test_astro_frontend_contract.py`。
- TODO：
  - [ ] `--bg: #f7f8fb` 改为断言 `--bg: #FAF8F5` 或更稳妥的 warm-earth token 注释。
  - [ ] `--tech-accent: #eafe52` 删除或改为 legacy token 不含旧 lime。
  - [ ] `.day-modal-tab-nav button.active` 不再硬断言 teal rgba。
  - [ ] `.day-modal-sticky-actions` 不再硬断言 `#dbe6ea`。
  - [ ] 保留结构契约：`data-reading-fatigue-guard`、`#calendarActionPanel`、day modal tabs、feedback quick-first。
- 验收：
  - [ ] 测试验证主题方向和语义，不阻塞合理色值微调。

### P9.T2 新增配色契约测试

- TODO：
  - [ ] 断言普通层没有 `#eafe52`。
  - [ ] 断言 `commercial-light.css` 存在温感大地主题注释。
  - [ ] 断言 `--danger` 与 `--accent` 不相同。
  - [ ] 断言 `.primary-button` 使用 action token。
  - [ ] 断言 `.day-risk-pill` 使用 success/warning/danger 语义。
- 验收：
  - [ ] 防止后续又回到 lime/cyan 拼贴风。

### P9.T3 浏览器 smoke

- 命令：
  - `node --check apps\web\src\scripts\app.js`
  - `C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -m pytest -p no:cacheprovider tests\test_astro_frontend_contract.py -q`
  - `npm run build`，工作目录 `apps/web`。
  - `node_modules\.bin\astro.cmd preview --host 127.0.0.1 --port <free-port>`，工作目录 `apps/web`。
  - `WORKSPACE_URL=http://127.0.0.1:<port>/#workspace npm run smoke:workspace`，工作目录 `apps/web`。
  - `git diff --check`。
- 浏览器验收：
  - [ ] 桌面 1440 或 1512 宽截图。
  - [ ] 移动 390 宽截图。
  - [ ] day modal plan tab 截图。
  - [ ] feedback tab quick-first 截图。
  - [ ] medical_referral fail-closed 截图。
- 验收：
  - [ ] 无横向滚动。
  - [ ] 无文本重叠。
  - [ ] 控制台无 error。

## 13. Phase 10：文档与共享契约

### P10.T1 更新产品审计 TODO

- 文件：`docs/product/frontend_audit_todo.md`。
- TODO：
  - [ ] 追加“方案五温感大地落地轮次”。
  - [ ] 写明 Top 3 迁移来源：
    - Polaris color tokens：surface 状态。
    - Radix 12-step scale：背景/组件/边框/文字层级。
    - Fluent neutral/shared/semantic：中性色主导和语义色节制。
  - [ ] 写明不可迁移边界：不照抄任何品牌视觉资产。
  - [ ] 写明 DS4Pro 10 并发审计结果。
- 验收：
  - [ ] 外部证据可复查。

### P10.T2 更新产品报告

- 文件：`docs/product/reports/frontend_product_audit_2026-05-22.md`。
- TODO：
  - [ ] 记录用户选择方案五。
  - [ ] 记录陶土主色风险。
  - [ ] 记录浏览器截图路径。
  - [ ] 记录验证命令结果。
- 验收：
  - [ ] 报告不宣称最终商用完成，只描述本轮改动。

### P10.T3 必要时更新共享契约

- 文件：`docs/quality/shared_delivery_contract.md`。
- TODO：
  - [ ] 如果新增/修改 DOM/data attribute，必须更新契约。
  - [ ] 如果改变普通层术语，必须更新契约。
  - [ ] 如果只改配色 token，不需要大幅改 API 契约。
- 验收：
  - [ ] 不替 backend/QA/version owner 签收。

## 14. T0/T1/T2 风险

### T0 风险

- [ ] 陶土 accent 与 warning/danger 混淆。
  - 缓解：accent 只做行动，不做状态。
  - 验收：安全/警告/危险 chip 都有中文文字。
- [ ] medical_referral 普通 regenerate 泄漏。
  - 缓解：保留 `isMedicalReferralFeedback()` 阻断。
  - 验收：浏览器截图医疗红旗路径。
- [ ] 测试硬编码旧色导致重构误判。
  - 缓解：先改契约测试为 token/语义。
  - 验收：pytest 通过。
- [ ] 普通层展示 raw 字段。
  - 缓解：raw 只进专家/审计层。
  - 验收：可见文本扫描无 `risk_gate`、`protocol_recheck`、`workflow_trace`。

### T1 风险

- [ ] 暖色过多导致不够专业。
  - 缓解：80% 中性色，accent 面积小于 5%。
- [ ] 卡片太淡导致边界不清。
  - 缓解：使用暖灰边框和极轻阴影。
- [ ] `commercial-light.css` 继续膨胀。
  - 缓解：本轮只做 token 和必要覆盖，后续单独拆分组件样式。
- [ ] 移动端抽屉/弹窗压迫。
  - 缓解：截图验证 390 宽。

### T2 风险

- [ ] 多主题能力未完成。
  - 说明：本轮只落默认浅色主题。
- [ ] 真正组件化未完成。
  - 说明：后续需要把 `commercial-light.css` 的结构性覆盖迁移回组件文件。
- [ ] 高级感仍需用户主观复核。
  - 说明：需要截图给用户审核。

## 15. 执行顺序建议

- [ ] 第 1 批：P1、P2、P9.T1。
- [ ] 第 2 批：P3、P4、P5。
- [ ] 第 3 批：P6、P7。
- [ ] 第 4 批：P8、P9.T2、P9.T3。
- [ ] 第 5 批：P10 文档和共享契约复查。

## 16. Done 标准

- [ ] 方案五色值已落到 token。
- [ ] 普通层不再出现大面积 lime/cyan/旧红点。
- [ ] 主按钮、导航选中、反馈主行动使用陶土色但不混淆风险。
- [ ] 日卡、周卡、行动面板更淡且不割裂。
- [ ] day modal 和 feedback quick-first 保持可读。
- [ ] medical_referral 路径仍阻断普通 regenerate。
- [ ] 契约测试通过。
- [ ] `npm run build` 通过。
- [ ] workspace smoke 通过。
- [ ] desktop/mobile/modal/feedback/red-flag 截图已保存。
- [ ] `git diff --check` 通过。
- [ ] docs/product 报告更新。
- [ ] 共享契约没有未处理的前端条目。

## 17. Agent 与 Skills 执行矩阵

### 17.1 Frontend owner 主线任务

- [ ] 负责 P1 token 改造。
- [ ] 负责 P2 覆盖层止血。
- [ ] 负责 P3 导航和抽屉。
- [ ] 负责 P4 按钮和流程条。
- [ ] 负责 P5 行动面板。
- [ ] 负责 P6 日卡和周卡。
- [ ] 负责 P7 day modal 和 feedback。
- [ ] 负责 P8 普通层/专家层边界。
- [ ] 负责 P9 前端契约测试。
- [ ] 负责 P10 文档同步。
- [ ] 每次改动前读相关 CSS 和测试，不依赖记忆直接改。
- [ ] 每次改动后先跑最小检查，再跑完整前端 smoke。

### 17.2 DS4Pro 并发 reviewer 批次

- [ ] Batch A：10 并发审计 token 命名、旧色硬编码、旧色测试硬编码。
- [ ] Batch B：10 并发审计导航、按钮、行动面板、日卡、周卡、modal、feedback、EvidenceDrawer、移动端、可读性。
- [ ] Batch C：10 并发审计截图结果，输入 desktop/mobile/modal/feedback 状态摘要。
- [ ] Batch D：10 并发审计报告和 TODO 是否覆盖共享契约。
- [ ] 每个 DS job 必须声明“不能访问文件系统，只基于输入摘要”。
- [ ] DS 输出只能作为 reviewer 建议，不能替代本地浏览器验证。

### 17.3 Browser skill 验收任务

- [ ] 打开本地预览 URL。
- [ ] 截 desktop workspace。
- [ ] 截 mobile workspace。
- [ ] 截 mobile drawer closed/open。
- [ ] 截 day modal plan tab。
- [ ] 截 day modal audit tab。
- [ ] 截 day modal feedback tab。
- [ ] 截 feedback quick selected。
- [ ] 截 medical red flag result。
- [ ] 记录 console error 数。
- [ ] 记录 horizontal overflow。
- [ ] 记录按钮文字是否截断。
- [ ] 记录卡片是否过重或割裂。

### 17.4 QA/reviewer 只读任务

- [ ] 检查普通层是否出现英文 provider/raw 字段。
- [ ] 检查普通层是否出现 `risk_gate`。
- [ ] 检查普通层是否出现 `protocol_recheck`。
- [ ] 检查普通层是否出现 `workflow_trace`。
- [ ] 检查医疗红旗是否 fail-closed。
- [ ] 检查截图中主行动是否唯一突出。
- [ ] 检查陶土色是否误用为警告或危险。
- [ ] 检查移动端是否可单手完成反馈。
- [ ] 检查所有状态色是否有文字辅助。
- [ ] 检查文档是否没有替其他 owner 签收。

### 17.5 Backend read-only reviewer 触发条件

- [ ] 只有当 UI 依赖 API 字段不清晰时触发。
- [ ] 只有当 feedback/risk/plan_review 字段语义影响普通层时触发。
- [ ] 只读检查 `/query`、`/feedback`、`GET /plans/{plan_id}` 契约。
- [ ] 不改后端文件。
- [ ] 完成后关闭子智能体。

## 18. 后续可拆 Issue

- [ ] Issue 1：温感大地 token 化，不改变组件结构。
- [ ] Issue 2：移除 lime/cyan/red 旧视觉输出。
- [ ] Issue 3：导航和抽屉温感化。
- [ ] Issue 4：主按钮、次按钮、流程条统一。
- [ ] Issue 5：日历行动面板主次层级调整。
- [ ] Issue 6：日卡和周卡淡化。
- [ ] Issue 7：day modal 和 feedback 温感化。
- [ ] Issue 8：medical_referral 视觉和交互复核。
- [ ] Issue 9：前端契约测试去脆性硬编码。
- [ ] Issue 10：浏览器截图和报告签收。

