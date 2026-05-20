# 产品侧未完成 TODO（按组件模块）

> 范围：仅整理产品体验、产品能力和用户可感知功能待办；排除论文项目、实验任务、运行产物、纯技术债和代码内部实现细节。
>
> 组织方式：按产品组件/模块归类，便于后续拆设计、实现、验收任务。优先级可在每个模块内再补 `P0/P1/P2` 标签。

## 日历设计与训练时间模块

- [ ] 在 Astro 前端中完成月历组件点击日期、详情抽屉、移动端布局和视觉表现验收。来源：`TECH_REQUIREMENTS_V2.md`
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

---

# 论文打磨 TODO：STAI 2026 投稿路线图

> 范围：服务当前 STAI 2026 Workshop 论文 `A Workflow-Level Diagnostic Study of Evidence-Gated Advisory RAG for Endurance Training Advice` 的投稿打磨。
> 当前主稿：`docs/paper_project/paper_stai2026/main.tex`
> 当前 PDF：`docs/paper_project/paper_stai2026/build/main.pdf`
> Overleaf 包：`docs/paper_project/stai2026_overleaf_package_v0.1.zip`
> 底线：不编造文献、页码、数据、实验结果；不把 pilot benchmark 写成大规模验证；不把 deterministic hardening 写成通用安全防御；不声称临床安全、教练有效性或部署就绪。
>
> 状态快照（2026-05-11）：P0 主稿可读性、LNCS 编译、主实验/压力实验/补充模型 sanity check、Method 术语与小表、artifact index 已同步；P1 Related Work、审稿人攻击预案、case study polish、写作降调与 artifact 复核已形成 `66_STAI_P1_reviewer_attack_polish_report_v0.1.md`；P2 仍保留为最终打包与可选扩展实验。

## P0：投稿适配与硬约束模块

- [x] 核验 STAI 2026 / ECML PKDD workshop 官方投稿要求：页数、模板、匿名规则、参考文献格式、appendix 规则、AI disclosure 要求。
- [x] 将当前可编译 LaTeX 初稿迁移到官方模板，保留现有 `main.tex` 作为备份参照。
- [x] 检查标题是否过宽或过强，候选标题包括当前标题和更克制的 diagnostic-study 标题。
- [x] 明确最终投稿版本是否匿名：作者名、单位、致谢、数据路径、代码路径是否需要脱敏。
- [x] 更新 README 中的本地编译命令、Overleaf 上传说明和模板适配状态。
- [x] 每次模板迁移后重新编译 PDF，确认无 undefined citation/reference、无 overfull warning、主图和表格正常显示。

## P0：贡献定位与主线论证模块

- [x] 将全文核心定位统一为：workflow-level diagnostic study for safety-sensitive advisory RAG。
- [x] 在 Introduction 中明确本论文不是新 foundation model、不是通用 multi-agent framework、不是临床安全系统。
- [x] 将贡献点压缩为 3-4 条：explicit workflow control points、measurable output states、pilot benchmark + stress suite、diagnostic ablation/case studies。
- [x] 检查 Abstract、Introduction、Conclusion 三处贡献表述是否一致，避免同一工作出现三个不同“创新点”版本。
- [ ] 增加一张 claim boundary 表，区分 supported claims、diagnostic claims、unsupported/forbidden claims。
- [x] 全文统一使用 `answered`、`partial_answer`、`refused`、`citation repair`、`false refusal` 等术语。

## P0：方法模块

- [x] 把 Method 从“系统流程说明”改成“可复现方法描述”：每个 gate 写清 input、decision rule、output state、trace field。
- [x] 明确 refusal 只来自四类控制点：Pre-Gate Request Filter、Evidence Gate、Risk Gate、Independent Grounding Auditor。
- [x] 收窄 Bounded Repair 的语义：只修 citation、grounding、unsupported wording、missing refusal boundary，不修 unsafe request。
- [x] 给出 trace schema 小表：qid、retrieved evidence count、evidence gate、risk gate、audit result、repair result、final status。
- [x] 给出 ablation variant 定义表：full workflow、no_gate、no_audit、no_repair，说明每个 variant 删除了什么、保留了什么。
- [x] 检查方法图 Figure 1 是否与正文术语完全一致，包括 Pre-Gate、Evidence Gate、Risk Gate、Generator、Auditor、Repair、Refusal、Final Answer。

## P0：实验与结果叙事模块

- [x] Results 先呈现主实验，再呈现 safety stress，再呈现 supplementary model sanity checks，再呈现 case studies 和 ablation。
- [x] 把 100 题主 benchmark 写成 pilot benchmark，不写 large-scale。
- [x] 把 30 条 safety stress 写成 targeted constructed stress suite，不写 general adversarial robustness。
- [x] 把 llama3 / DeepSeek 40 题结果写成 supplementary sanity check，不写 full multi-model evaluation。
- [x] 把 40 题 ablation 写成 diagnostic ablation subset，不写完整 ablation study。
- [ ] 增加一张“实验结果支持哪个 claim”的映射表，防止数字和论点脱节。
- [x] 对 citation repair count = 62 进行解释：这是 audit 暴露 grounding friction，不是简单失败率。
- [x] 对 false refusal = 4 / 90 进行解释：这是 safety-conservative failure mode，需要承认 utility cost。

## P0：证据完整性与反幻觉模块

- [x] 全文逐条核对所有数字是否来自现有 run artifacts，不手动补造结果。
- [x] 全文逐条核对所有 citation key 是否存在于 `references.bib`，且正文引用含义和论文真实贡献匹配。
- [x] 检查 Related Work 中每篇文献是否真的支持所在句子的 claim。
- [x] 检查所有 “we show / demonstrate / prove / robust / safe / effective” 类强动词，必要时改成 “we observe / evaluate / position / suggest / provide evidence that”。
- [x] 检查是否存在未证实页码、DOI、会议版本、实验细节；缺失则标记为待核验，不补编。
- [ ] 保留 `docs/paper_project/55_STAI_claim_evidence_audit_v0.1.md` 作为 claim-evidence audit 的主依据，并在最终前更新一次。

## P1：Related Work 与研究空白模块

- [x] 将 Related Work 改成问题导向，而不是文献罗列。
- [x] 四段式组织：RAG grounding / attribution；self-critique / verifier / repair；agentic workflow / tool use；safety-sensitive advisory setting。
- [x] 每段最后都回扣本文 gap：现有工作较少把 refusal、repair、safety-boundary behavior 作为显式可测 workflow states。
- [x] 补充或核验 agentic RAG、audit-and-repair、self-verification、citation grounding 相关核心论文。
- [x] 避免为了显得丰富而加入不直接相关的 agent 论文。
- [x] Related Work 末段写出本文与既有工作的区别：不是更强生成器，而是更可观察、更可诊断的控制点拆分。

## P1：审稿人攻击与风险预案模块

- [x] 模拟 EIC 视角：是否适合 STAI workshop，是否足够贴合 secure/trustworthy 主题。
- [x] 模拟 Methodology Reviewer：benchmark 是否太小、标签是否作者自建、ablation 是否足够。
- [x] 模拟 Domain Reviewer：endurance training 证据是否足够，是否越界到医学/临床建议。
- [x] 模拟 Security Reviewer：deterministic hardening 是否被过度表述为安全机制。
- [x] 模拟 Devil's Advocate：如果拒稿，最强理由是什么，论文应该如何提前承认。
- [x] 为每个潜在质疑写一条正文内防御或 limitation，不等 rebuttal 时再补。

## P1：写作质量与可读性模块

- [x] 删除 AI 腔常见表达：overly broad opening、throat-clearing、空泛形容词、重复强调 “important/crucial”。
- [x] 检查段落长度，避免每段节奏一致。
- [x] 检查 Introduction 是否形成清晰漏斗：general risk -> advisory RAG problem -> workflow question -> contributions -> scope boundary。
- [x] 检查 Results 是否先讲观察，再讲解释，不把 discussion 混进表格描述。
- [x] 检查 Conclusion 是否只总结已验证内容，不引入新 claim。
- [x] 将中文内部思路全部转换为正式英文学术表达，不留下中文注释或草稿痕迹。

## P1：案例研究模块

- [x] 最终保留 3-4 个 case：correct refusal、citation repair、false refusal、safety stress blocking。
- [x] 每个 case 提供 qid、question type、gate decision、audit/repair signal、final status、lesson。
- [x] correct refusal 案例要强调 refusal 是 intended success state。
- [x] citation repair 案例要强调 audit/repair 不是装饰模块。
- [x] false refusal 案例要主动暴露 utility cost。
- [x] safety stress 案例要强调 targeted pre-gate blocking，不推广到未知攻击。

## P1：可复现性与 artifact 模块

- [x] 在 Experimental Setup 中列出 dataset、run id、model、evidence mode、prompt template version、evaluation script。
- [x] 检查 `docs/paper_project/stai_benchmark_v0.3_100_question_draft.jsonl` 是否与论文中的 category count 一致。
- [x] 检查 `docs/paper_project/stai_safety_stress_benchmark_v0.2_30_question.jsonl` 是否与论文中的 stress category count 一致。
- [x] 检查所有 run artifacts 是否仍存在，包括 main 100q、stress qwen、stress llama3、llama3 40q、v0.3 ablation subset。
- [x] 生成最终 artifact index，说明哪些文件用于论文结果，哪些文件只是开发过程记录。
- [x] 如果需要公开仓库，准备最小 reproducibility package，避免泄露本地绝对路径和无关工程文件。

## P2：扩展实验模块

- [ ] 评估是否补跑 v0.3 100q full ablation：no_gate、no_audit、no_repair。
- [x] 评估并加入第三个 API 模型 `deepseek-v4-pro` 作为 40-question supplementary model check。
- [ ] 评估是否扩展 safety stress 到 multi-turn stress prompts。
- [ ] 评估是否加入 retrieval-only vs retrieval_plus_gold 的对比，以区分检索失败和 workflow gate 失败。
- [ ] 评估是否邀请外部跑者/教练做小规模 expert spot-check，但不把它写成正式专家验证，除非流程足够规范。

## P2：投稿材料模块

- [ ] 准备 final PDF。
- [ ] 准备 anonymized source zip。
- [ ] 准备 abstract 和 keywords。
- [ ] 准备 data/code availability statement。
- [ ] 准备 ethics / conflict of interest / funding / AI usage disclosure。
- [ ] 准备一页式投稿前自查表：claim boundary、citation integrity、template compliance、artifact reproducibility。

## 当前建议执行顺序

1. [x] 先做 P0 投稿适配与硬约束。
2. [x] 再做 P0 贡献定位与主线论证。
3. [x] 再做 P0 方法模块。
4. [x] 再做 P0 实验与结果叙事。
5. [x] 再做 P0 证据完整性与反幻觉。
6. [x] 然后进入 P1 Related Work、审稿人攻击、写作质量、案例研究。
7. [ ] 最后根据时间决定 P2 扩展实验和投稿材料。
## STAI final closeout update (2026-05-13)

- [x] Prepared anonymous compact submission PDF: `docs/paper_project/stai2026_submission_main_8p_anonymous.pdf`.
- [x] Prepared anonymous full manuscript PDF: `docs/paper_project/stai2026_submission_main_full_anonymous.pdf`.
- [x] Prepared anonymous source package: `docs/paper_project/stai2026_anonymous_source_package_v0.2.zip`.
- [x] Added final submission checklist: `docs/paper_project/67_STAI_final_submission_checklist_v0.1.md`.
- [x] Updated `docs/paper_project/paper_stai2026/README.md` for `main_8p.tex`, current Figure 1, and current Tectonic build command.
- [x] Recompiled `main_8p.tex` and `main.tex`; verified page count, anonymity, no undefined citation/reference, and no Overfull hbox warnings.
