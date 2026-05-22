# Release Hardening 可重复循环记忆

> 目的：防止长轮次、多 agent、前后端并行交付时遗忘用户验收标准、共享契约、证据规则和商用品质口径。`docs/quality/shared_delivery_contract.md` 是权威入口；本文件是详细执行手册。任何进入 release hardening 的前端、后端、QA、review agent，必须先读共享契约，再按需读本文件。

## 0. 当前硬约束

- 当前 Codex 主角色以 `docs/quality/shared_delivery_contract.md` 的“本线程当前主 Codex 角色”为准；每轮开始必须复读并在本轮 TODO/review 中声明角色。最近一轮主线程角色是 Backend / Engineering Coordinator。
- Frontend owner 可以修改公共契约中前端 UI、DOM/API 依赖、浏览器验证、商用审美质量和普通模式降噪相关条目，也可以记录跨端冲突；但不得替 Backend owner 或 QA/reviewer owner 宣称签收完成。
- Frontend owner 只在严重跨端契约问题影响前端交付时做最小后端兼容修复，并在 review TODO 中标注“前端为保持契约所做的最小后端配合”。
- Backend / Engineering Coordinator 仍负责 API、DB、LLM provider、RAG/KB、训练负荷真实性、observability、安全、验证矩阵、版本边界和 agent 工作流设计；后端 owner 修改契约时也必须声明角色。
- 结束条件不是“我做完一轮”，也不是“测试通过”。结束条件是：共享契约、前端 review、只读后端交付面 review、浏览器验证和报告 TODO 都没有新的值得修问题。
- 每一轮都要回到 `docs/quality/shared_delivery_contract.md` 复核共识。契约仍有未签收项时，不能声称 release hardening 结束。
- 同一时间最多保留一个 subagent。开 agent 前先确认任务能并行、边界只读或写集隔离；agent 完成后及时关闭。上一轮遗留的已完成 agent 必须在下一轮开始前关闭。
- 前端负责前端，不要因为看到后端 dirty worktree 就惊慌。只在 API/安全/观测/数据契约影响前端交付时做最小兼容修复。
- 不允许用猜测描述国外 app 或竞品做法。要么使用官方/公开资料链接，要么使用截图/可复现浏览器观察。没有证据的判断只能标为“待验证假设”。
- 前端 owner 每轮必须主动调研高端商用 app/网页的审美与信息架构范式，不局限马拉松或跑步竞品；可参考生产力、金融、健康、可穿戴、设计工具和操作系统级产品，但必须有官方资料、公开截图或本地浏览器截图。
- 跨行业审美迁移只迁移范式：信息层级、字段可见性、状态表达、交互节奏、密度控制、可信解释和安全边界；不得迁移品牌资产、商标、受版权保护截图、设备真实指标语义或没有数据支撑的恢复/准备度评分。
- 前端默认界面不能展示用户不关心的计算字段、内部状态名、工程调试标签或杂乱指标。普通用户关心结果、下一步动作、风险阻断和计划能不能执行。
- 专家审计、trace、协议细节、request id、调试字段可以保留，但必须放进专家/debug/审计入口，不能淹没主体验。
- 医疗红旗必须 fail-closed。胸痛、头晕/晕厥、疑似热病、呼吸异常、异常心悸等信号不能继续展示普通 regenerate 或高强度替代训练路径。
- DeepSeek API key 只能当前会话使用，禁止恢复 `localStorage.setItem("marathon_ds_api_key", ...)`。
- dirty worktree 很重，禁止 `git add .`，禁止回滚其他 agent 或用户的改动，禁止把数据缓存、用户画像、构建产物纳入版本单元。

## 1. Release Hardening 循环

每轮按固定节奏推进，避免记忆漂移。

1. 读取 `docs/quality/shared_delivery_contract.md`。
2. 读取本文件。
3. 读取当前轮 TODO、上一轮 review TODO、最新审计报告。
4. 检查 `git status --short --branch`，只识别相关改动，不清理无关 dirty 文件。
5. 如需竞品/国外 app 对比，先收集证据：官方文档、公开页面、截图或浏览器观察；前端 owner 即使本轮重点是视觉/信息架构，也要把高端商用 app 证据写进 TODO。
6. 高端商用审美迁移必须记录四列：`产品/来源`、`可观察事实`、`可迁移范式`、`不可迁移边界`；没有证据的内容只能写入“待验证假设”。
7. 生成本轮 audit TODO。用户要求轮次 TODO 类产物容量足够大，历史标准是每轮两个 TODO 类文件至少 500 行。
8. 将每个子任务拆成可验收 TODO，不把大任务写成一句话。
9. 优先处理 T0：安全阻断、反馈闭环、契约断裂、无法使用的核心路径。
10. 再处理 T1：商用品质、主体验结构、可读性、可信度、移动端可用性。
11. 最后处理 T2/Tn：视觉 polish、维护性、扩展性、审计面板细节。
12. 每次文件编辑前说明正在改什么；编辑后运行最相关验证。
13. 用浏览器或 Playwright 截图验证关键前端状态，尤其是移动端、日历生成后、日卡 modal、反馈、医疗红旗。
14. 写本轮 review TODO，记录已修、证据、剩余风险、下一轮入口。
15. 更新报告，不得让旧报告继续写“不能发布”的过期结论，也不得过早写“完美商用”。
16. 如有必要，最多启动一个只读 reviewer；选择当前轮风险最高的审计面，不再同时开前端和后端两个 reviewer。完成后关闭。
17. 复查共享契约签收清单。如果仍有未签收项，把它们滚入下一轮。
18. 只有所有 reviewer 和共享契约都没有新的可修项，才能结束 hardening。

## 2. 每轮必须避免的假完成

- 只跑 `npm run build` 就说前端可商用。
- 只看空态截图，不验证生成后日历、日卡、反馈和红旗路径。
- 只改颜色，不修信息架构、主任务路径和安全闭环。
- 把日历塞进侧边抽屉，导致核心训练体验变成导航附属物。
- 让状态面板、trace、审计字段、协议字段压过训练计划本身。
- 把 `Plan Builder`、`StatusPanel`、`RunnerIdentityCard`、`Daily Coach Card`、`Generation Trace` 等内部名暴露给普通用户。
- 用“国外成熟 app 都这样”做论据，但没有链接、截图或可复现观察。
- 只做桌面，不测移动端 sticky nav、底部导航、抽屉、modal、横向溢出。
- 只测普通反馈，不测 `medical_referral` fail-closed。
- 反馈提交缺少 `plan_id/event_id/day_key` 时只等后端报错。
- 保存计划后页面刷新丢掉 `workflow_trace`、`latest_feedback`、`risk_gate`、`protocol_recheck`。
- 后端返回字段变化但前端没有 fallback 或契约测试。
- 修改共享 DOM/data attribute 但不更新 `tests/test_astro_frontend_contract.py`。
- 修改 API/DB/观测契约但不更新 `shared_delivery_contract.md`。

## 3. 用户已经明确提醒过的事项

- 验收标准是能商用的 app，不是 demo，不是内部工具。
- 可以不断审计、不断推进修复，不需要每轮确认。
- 但结束必须等共享契约达成共识，确认没有任何值得修的问题。
- 每个子任务都值得拆成 TODO 列表推进。
- 每个轮次的两个 TODO.md 产物至少需要 500 行容量。
- 美术设计要和国外 app 和网页对比。
- 前端 owner 要负责调 agent 看高端商用 app 的审美并做迁移学习；不局限马拉松，任何成熟高端 app/网页都可以成为证据来源。
- 不能瞎猜别人怎么做；要么截图，要么找资料。
- 前端不要展示用户不感兴趣的计算字段。用户关心结果，不关心乱糟糟的数据展示。
- 最多同时开一个 agent。
- 注意关掉无用 agent。
- 可以定期起只读后端 review 子 agent 检查交付面。
- 共享契约文件已经落地，前后端都需要定期看。

## 4. 容易忘的商用品质维度

### 4.1 主体验

- 训练日历应是生成成功后的主产品面，而不是被藏在侧边抽屉。
- 主工作区优先显示：本周要练什么、今天要做什么、下一步怎么做、哪里需要停下。
- 空态不应像占位符。空态应告诉用户当前还缺什么、下一步做什么、系统是否可用。
- 结果摘要要像教练摘要，而不是 API response 展示器。
- 日卡要能快速扫读：训练类型、距离/时长、强度、目的、注意事项、反馈入口。
- 历史计划应能恢复审计视图，但普通用户默认不需要看完整 trace。

### 4.2 安全与健康

- 医疗红旗必须是结构化输入，而不是只靠备注解析。
- 任一红旗勾选后，前端也应立即进入 fail-closed 语义：停止训练、专业评估、隐藏普通调整版计划。
- 疼痛/高疲劳不等同医疗红旗，但应默认降级，避免展示 interval、tempo、VO2、threshold 等高强度建议。
- 风险未知不能写“可执行”。应写“执行前完成疼痛/疲劳自检”。
- 无风险门或风险门未知时，普通 UI 要诚实展示“未完成风险自检”或等价文案。

### 4.3 可信度

- 证据来源要区分本地证据、协议规则、计划规则、模型知识说明。
- 无证据不能伪造 source path、页码、引用编号或证据 ID。
- HMP 协议路径统一到真实文档，避免旧路径污染 UI。
- `workflow_trace` 是可展示决策摘要，不是 raw chain-of-thought。
- 用户可见文案要避免“内部工程语义”。普通用户不应该看到 `feedback_id`、`risk_gate`、`protocol_recheck` 这类原始字段名。

### 4.4 信息简洁度

- 默认视图不要堆计算字段。计算字段只在它们直接回答用户问题时出现。
- 状态面板应变成“本周进展 + 下次建议 + 风险提醒”，不展示 CycleProgressBar/PhaseTimeline/CompletedWeeksList 这类内部组件名。
- 进度条 idle 状态不应展示 7 个步骤压迫用户；生成中再展开细节。
- request id、trace version、protocol issue count 等字段应进入专家审计，不进入普通首页。
- 图表和指标必须服务决策：为什么今天降级、为什么本周负荷高、下一次怎么做。

### 4.5 移动端

- 移动端只能保留一个主导航模式，避免底部 tab、抽屉入口、sticky 顶栏互相竞争。
- sticky 顶栏和 hash 锚点不能遮住标题。
- modal 要有 focus trap、Escape、焦点恢复、body lock。
- 抽屉打开时背景 inert，关闭后恢复焦点。
- 日卡要允许换行，不为追求整齐而截断关键信息。
- 所有按钮文案必须适配窄屏，不溢出、不重叠。

### 4.6 视觉和美术

- 避免只有暗底 + 青/蓝/紫发光的工程控制台感。
- 品牌、状态色、风险色要分层；不要让品牌色和风险色混在一起。
- 训练产品可以克制、专业、信息密集，但不能像调试台。
- 不做营销式 hero、大插画、玻璃拟态首页；当前产品主入口应是工作台。
- 卡片半径保持克制，避免嵌套卡片和重阴影堆叠。
- 国外 app 对比只迁移范式，不照抄品牌和视觉资产。
- 高端商用 app 对比不能只停留在“好看”：必须转译成具体 UI 决策，例如普通层字段裁剪、专家层入口、日卡密度、状态颜色职责、风险阻断文案、反馈后下一步动作。

## 5. 国外产品对比证据规则

可参考对象，但每次引用必须带证据：

- Strava：训练日志、周视图、活动记录和训练趋势。
- TrainingPeaks：训练日历、指标、教练/运动员协作、设备同步。
- Garmin Connect：日历、训练计划、设备同步、训练状态。
- Runna：训练计划日历、移动训练、状态不好时调整训练。
- Nike Run Club：跑步体验、训练引导、移动端简洁度。

使用规则：

- 优先官方支持文档、官网功能页、应用商店官方截图、公开帮助中心截图。
- 如果用浏览器截图，保存到 `artifacts/frontend-audit/` 并在报告里引用路径。
- 如果只是从截图归纳，写“从截图观察到”，不要写成产品事实。
- 如果没有资料，写“待验证假设”，不要进入修复依据。

## 6. 当前必须滚入下一轮的已知问题

- 反馈提交前需要确认 `plan_id + event_id`，或后端认可的 `day_key` 可用；否则应禁用提交或给出自动保存/恢复路径。
- 前端需要结构化医疗红旗 checklist，并能在本地先 fail-closed。
- 生成成功后训练日历应回到主工作区，侧边抽屉只做导航/筛选/依据入口。
- 画像生成门槛不能只看任意字段；目标、能力或跑量、比赛日期/周期、可训练日、伤病/限制应有明确缺项提示。
- 普通用户文案需要产品化，移除内部组件名和英文调试标签。
- 本地 `localStorage` 存画像、计划历史和完整响应的隐私边界需要说明或收窄。
- workspace smoke 需要覆盖填画像、生成计划、打开日卡、打开证据、提交普通反馈、提交红旗反馈。
- 日历 view/filter 控件需要完整 tab/segmented control 语义和键盘支持。
- 前端需要在合适位置消费 `X-Request-ID`，但不能让普通用户被排障字段干扰。
- 保存计划页面提交 medical feedback 后，普通状态面板不能继续显示旧 summary 的 normal/generated。
- 后端 HMP evidence bundle 的协议主路径不能继续指向不存在的旧路径。
- `/query` 空输入但已有画像时，full mode 也不能误判普通 QA。

## 7. 每轮验证命令

前端：

```powershell
cd apps/web
npm run build
```

隔离 preview 和 workspace smoke：

```powershell
cd apps/web
npm run preview -- --host 127.0.0.1 --port 4322
$env:WORKSPACE_URL='http://127.0.0.1:4322/#workspace'
npm run smoke:workspace
```

目标 Python 测试：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -m pytest tests\test_astro_frontend_contract.py tests\test_api_app.py tests\test_state_models.py -q
```

仓库卫生：

```powershell
git diff --check
git status --short --branch
```

## 8. 每轮报告必须回答的问题

- 本轮读了哪些契约和记忆文件？
- 本轮参考了哪些外部产品证据？链接或截图在哪里？
- 本轮 T0/T1/T2 分别修了什么？
- 哪些问题只是记录，尚未修？
- 普通用户默认界面是否只展示结果、行动和安全信号？
- 专家审计字段是否仍可追踪但不污染主界面？
- 医疗红旗是否 fail-closed？
- 反馈闭环是否可保存、可恢复、可审计？
- 移动端是否无遮挡、无横向溢出、无导航竞争？
- 是否运行了 build、pytest、smoke、browser screenshot、`git diff --check`？
- 是否还有 reviewer 或共享契约未签收项？

## 9. 下一轮启动口令

当继续 hardening 时，从这里开始：

1. 读 `docs/quality/shared_delivery_contract.md`，以共享契约为权威入口。
2. 读 `docs/quality/release_hardening_loop.md`，作为详细执行手册。
3. 读最新 `docs/quality/rounds/*review_todo.md`。
4. 读最新 `docs/product/reports/frontend_product_audit_2026-05-22.md`。
5. 查 `git status --short --branch`。
6. 收集国外产品证据或截图。
7. 写下一轮 500+ 行 audit TODO。
8. 修 T0/T1。
9. 写下一轮 500+ 行 review TODO。
10. 验证并继续循环，直到共享契约达成无可修共识。
