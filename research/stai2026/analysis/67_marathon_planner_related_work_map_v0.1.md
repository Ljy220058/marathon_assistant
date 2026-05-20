# 马拉松计划生成助手相关论文地图与投稿方向 v0.1

日期：2026-05-12  
对象：Astro + FastAPI 马拉松训练计划生成器，含跑者画像、HMP 半马协议、RAG/动作库证据、训练日历、日卡解释、疲劳/疼痛反馈与自适应调整。

## 1. 当前项目最适合的论文定位

不要把论文主张写成“LLM 生成马拉松训练计划”。这个表述太宽，也容易被审稿人追问安全性、真实性和专家评估。

更强的定位是：

> 一个面向耐力跑训练的协议约束、证据感知、人机协作训练计划系统。系统把跑者画像、比赛日期、运动训练协议、动作库证据、日历交互和训练反馈闭环放在同一工作流中，用来降低裸 LLM 运动处方的不可控性。

可以拆成三种投稿形态：

| 形态 | 当前成熟度 | 最适合目标 |
|---|---|---|
| Demo / System paper | 高 | SportsHCI Demo、MobileHCI Demo、CUI Interactivity |
| LBW / Short paper | 中高 | SportsHCI LBW、MobileHCI LBW、CUI WiP |
| Full paper | 暂时不足 | 需要用户研究、专家评估、baseline 对比后再冲 CHI / MobileHCI / CUI / IUI |

## 2. 分类文献地图

### A. 马拉松与运动推荐系统

| 论文 | 年份 / 来源 | 核心贡献 | 对本项目的启发 |
|---|---:|---|---|
| Fit to Run: Personalised Recommendations for Marathon Training | 2020, ACM RecSys | 使用大量跑者训练数据，为马拉松训练推荐未来训练周模式。链接：[DBLP](https://dblp.org/rec/conf/recsys/BerndsenSL20.html) | 证明“马拉松训练推荐”是已有研究方向；我们的差异是协议、解释、反馈闭环，而不是只做相似跑者推荐。 |
| Recommendations for marathon runners: recommender systems and ML to support recreational marathon runners | 2022, User Modeling and User-Adapted Interaction | 总结马拉松训练、配速、完赛预测相关推荐系统。链接：[Springer](https://link.springer.com/article/10.1007/s11257-021-09299-3) | 可作为相关工作核心综述入口；指出已有工作多偏数据驱动，缺少证据边界与交互式调整。 |
| Physical Exercise Recommendation and Success Prediction Using Interconnected RNNs | 2021, IEEE ICDH | 推荐下一次运动活动，并预测完成概率。链接：[arXiv](https://arxiv.org/abs/2010.00482) | 可借鉴“可完成性预测”，后续把疲劳、睡眠、疼痛映射为计划可执行性评分。 |
| An AI-Based Exercise Prescription Recommendation System | 2021, Applied Sciences | 基于用户基础健康数据推荐 1/2/3 个月运动模式。链接：[MDPI](https://www.mdpi.com/2076-3417/11/6/2661) | 与“画像 -> 处方”链路相似，但输出粒度粗；我们的优势是多周日历和日卡级解释。 |

### B. 运动处方与临床规则系统

| 论文 | 年份 / 来源 | 核心贡献 | 对本项目的启发 |
|---|---:|---|---|
| EXPERT tool: digital decision support for optimized exercise prescription in cardiovascular disease | 2017, European Journal of Preventive Cardiology | 使用专家共识和规则算法生成 FITT 运动处方。链接：[SAGE](https://journals.sagepub.com/doi/abs/10.1177/2047487317702042) | 可作为“规则化、安全优先运动处方”的标杆；HMP 协议可类比为跑步专项规则层。 |
| P3-EX: clinical decision support system for exercise prescription | 2021, Mayo Clinic Proceedings: Innovations, Quality & Outcomes | 整合 ACSM/AHA 等原则，为多 CVD 风险人群生成运动处方。链接：[ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2542454820301570) | 支撑“画像缺口、风险分层、禁忌和约束优先”的设计。 |
| FITILP: End-to-End Differentiable MILP for Personalized Exercise-Prescription Generation | 2025, ICMLCA | 将运动处方建模为带时间和疲劳硬约束的优化问题。链接：[EurekaMag](https://eurekamag.com/research/104/992/104992060.php) | 后续可把当前 HMP 容量预算升级为约束优化模块。 |

### C. LLM 个性化运动计划与健康建议

| 论文 | 年份 / 来源 | 核心贡献 | 对本项目的启发 |
|---|---:|---|---|
| PlanFitting: Personalized Exercise Planning with Large Language Model-driven Conversational Agent | 2023 arXiv / ACM CUI 2025 | 对话收集目标、可用时间和障碍，生成个性化周运动计划。链接：[arXiv](https://arxiv.org/abs/2309.12555)，[作者 PDF](https://faculty.washington.edu/garyhs/docs/shin-cui2025-planfitting-paper.pdf) | 最接近“画像 + 会话 + 运动计划”；我们的差异是专项周期化、证据绑定、协议校验、训练反馈后再规划。 |
| Using artificial intelligence for exercise prescription in personalised health promotion | 2024, Biology of Sport | 专家评价 GPT-4 生成运动处方，指出需要专家监督和安全验证。链接：[BCU repository](https://www.open-access.bcu.ac.uk/15383/) | 为“不能裸用通用 LLM 生成训练处方”提供动机。 |
| Using Large Language Models to Enhance Exercise Recommendations and Physical Activity | 2025, JMIR Medical Informatics | 综述 LLM 在运动建议和身体活动中的应用与局限。链接：[JMIR](https://medinform.jmir.org/2025/1/e59309) | 可作为健康 LLM 相关工作入口，支持我们写“需要可执行、安全、可解释的垂直系统”。 |
| Knowledge-grounded large language model for personalized sports training plan generation | 2026, Scientific Reports | LLM + 运动科学知识图谱 + 动态用户画像 + 结构化计划校验。链接：[Nature Scientific Reports](https://www.nature.com/articles/s41598-026-37075-z) | 与我们最接近。必须明确差异：我们强调跑步专项 HMP、可点击日历、证据状态、反馈闭环和产品化交互。 |
| Artificial intelligence in sport: using ChatGPT in resistance training prescription | 2024, Biology of Sport | 测试 ChatGPT 生成 12 周抗阻训练计划，指出个体化和专家修正问题。链接：[DOAJ](https://doaj.org/article/af9a9d5256d046b5a914e126cef67d05) | 支撑“LLM 草稿可以用，但需要规则、专家逻辑和审计”。 |

### D. SportsHCI、跑步反馈与训练负荷交互

| 论文 | 年份 / 来源 | 核心贡献 | 对本项目的启发 |
|---|---:|---|---|
| Using Shared Decision-Making Approach in Workout Adjustment Guidance | 2025, SportsHCI / ACM | 将共享决策用于跑步训练调整。链接：[ACM DOI](https://doi.org/10.1145/3749385.3749399) | 可把“疲劳/疼痛后调整”设计为多个可选方案，而非系统单方面覆盖计划。 |
| Is it just a score? Understanding Training Load Management Practices Beyond Sports Tracking | 2024, CHI | 调查/访谈跑者如何理解训练负荷数据。链接：[ACM DOI](https://doi.org/10.1145/3613904.3642051) | 支撑“负荷不是一个分数，而要解释原因、身体感受和下一步动作”。 |
| Exploring Large Language Model as an Interactive Sports Coach | 2025, arXiv | 半马备赛中使用 LLM 做计划、解释和动机支持。链接：[arXiv](https://arxiv.org/abs/2509.26593) | 与本项目近邻；我们的创新要落在可审计协议和系统化 UI，而不是“LLM coach”本身。 |
| Inspirun E-Coach personalization study | 2020, Sensors | 基于心率、GPS、RPE 个性化跑步训练方案并评估体验。链接：[MDPI Sensors](https://www.mdpi.com/1424-8220/20/16/4590) | 后续可接入 RPE、心率和 Garmin/Apple Watch 数据做长期能力更新。 |
| Running with Technology: Where Are We Heading? | 2014, OzCHI | 梳理跑步技术从配速/距离走向技术反馈和体验设计。链接：[ACM DOI](https://doi.org/10.1145/2686612.2686696) | 可作为跑步技术设计空间背景。 |
| Strive: Exploring Assistive Haptic Feedback on the Run | 2017, OzCHI | 探索跑步中的触觉反馈。链接：[ACM DOI](https://doi.org/10.1145/3152771.3152801) | 后续可把日卡转成跑中提醒策略。 |
| RunBuddy: A Smartphone System for Running Rhythm Monitoring | 2015, UbiComp | 手机与耳机监测呼吸/步频节律。链接：[ACM DOI](https://dl.acm.org/doi/10.1145/2750858.2804293) | 可支撑多模态扩展方向。 |
| PoseCoach: Video-Based Running Coaching | 2024, IEEE TVCG | 视频跑姿分析与可视化。链接：[IEEE DOI](https://doi.org/10.1109/TVCG.2022.3230855) | 可为“训练解释 + 动作 cue 卡片”提供远期参考。 |

### E. RAG、证据 grounding 与人机协作评价

| 论文 | 年份 / 来源 | 核心贡献 | 对本项目的启发 |
|---|---:|---|---|
| Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks | 2020, NeurIPS | RAG 基础论文。链接：[NeurIPS](https://papers.neurips.cc/paper_files/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html) | 你的证据库不是只回答问题，而是约束训练计划生成和解释。 |
| Ragas: Automated Evaluation of Retrieval Augmented Generation | 2023, arXiv | 自动评估 RAG 检索与生成质量。链接：[arXiv](https://arxiv.org/abs/2309.15217) | 可扩展为“训练计划 RAGAS”：证据命中、处方一致性、解释 faithful。 |
| Grounding LLMs in Clinical Evidence: NICE guideline RAG | 2025, arXiv | 用临床指南 RAG 降低 unsafe response，并做专家评价。链接：[arXiv](https://arxiv.org/abs/2510.02967) | 可类比为“运动训练指南/动作库/OCR 资料 grounding”。 |
| Large language models encode clinical knowledge | 2023, Nature | Med-PaLM 多维健康问答评价。链接：[Nature](https://www.nature.com/articles/s41586-023-06291-2) | 可借鉴 factuality、harm、reasoning 等维度，构造运动计划评价表。 |
| When combinations of humans and AI are useful | 2024, Nature Human Behaviour | 元分析 human-AI augmentation 与 synergy。链接：[Nature](https://www.nature.com/articles/s41562-024-02024-1) | 不能空喊人机协作，应设计 AI-only / human-only / human+AI 对照。 |
| Human-centered design and evaluation of AI-empowered clinical decision support systems | 2023, Frontiers in Computer Science | 总结 AI-CDSS 的人本设计和评价。链接：[Frontiers](https://doi.org/10.3389/fcomp.2023.1187299) | 可把系统定位为“跑者/教练决策支持”，不是替代教练。 |

## 3. 运动处方生成之后的创新方向

### 方向 1：协议约束的训练计划生成

核心问题：LLM 计划看起来合理，但可能违反周期化、恢复间隔、容量预算或专项训练原则。

可写贡献：
- HMP 半马协议作为确定性约束层。
- 计划生成后执行 protocol validation / repair。
- 输出计划时保留 decision trace。

适合投稿：
- SportsHCI LBW / Demo：系统体验与跑步专项协议。
- IUI / CUI short：智能系统如何把协议约束嵌入生成式交互。
- Full paper 前提：做 protocol violation ablation，对比 no-protocol LLM。

### 方向 2：证据感知的运动处方解释

核心问题：训练计划解释容易变成泛泛而谈，用户不知道哪些内容有证据、哪些只是模型推断。

可写贡献：
- 证据状态分层：动作库直接证据、HMP 协议规则、知识库参考、证据不足。
- 日卡级解释绑定 evidence id / source。
- 无证据时显式降级，不展示模板化主课。

适合投稿：
- Demo/System：展示证据抽屉与日卡解释。
- Trustworthy AI / health AI workshop：评估 hallucination 与 unsafe prescription 降低。
- Full paper 前提：做证据覆盖率、解释 faithful、专家评分。

### 方向 3：共享决策式训练反馈调整

核心问题：跑者反馈“累/疼/没完成”后，系统不应直接覆盖计划，而应解释风险并给出可选择的调整。

可写贡献：
- 疲劳、疼痛、睡眠、完成度映射到调整原因。
- 输出 2-3 个调整选项：保守降载、维持但替换、取消关键课。
- 用户选择后更新本周和后续训练。

适合投稿：
- SportsHCI LBW：共享决策 + 跑步训练调整。
- MobileHCI Demo：移动端训练反馈闭环。
- HCI full 前提：做 expert walkthrough 或跑者小样本研究。

### 方向 4：训练负荷解释与风险可视化

核心问题：训练负荷分数本身不够，跑者需要知道“为什么高、是否危险、接下来做什么”。

可写贡献：
- 周级/日级负荷卡。
- 近期跑量、上月月跑量、计划周跑量之间的容量依据解释。
- 风险提示与动作建议分离。

适合投稿：
- CHI/MobileHCI LBW：训练负荷解释 UI。
- SportsHCI Demo：以日历和日卡展示。
- Full paper 前提：用户理解度/信任/决策质量实验。

### 方向 5：长期跑者画像与计划记忆

核心问题：一次性画像不足以支持长期训练；训练表现、疲劳和偏好会变化。

可写贡献：
- 跑者画像从静态字段变成长期状态。
- 反馈和完成记录更新能力估计。
- 比赛日期倒推周期、月跑量估算基础周量。

适合投稿：
- CUI / IUI：个性化智能助手的长期用户模型。
- SportsHCI：跑者训练中的 longitudinal personalization。
- Full paper 前提：至少 2-4 周 longitudinal pilot。

### 方向 6：RAG/协议系统的评测基准

核心问题：现有运动计划系统通常缺少可复现评测，尤其是安全边界和证据边界。

可写贡献：
- 训练计划问答/生成 benchmark。
- 指标：protocol compliance、evidence coverage、unsafe adjustment rate、false refusal、actionability。
- Ablation：no evidence gate / no protocol / no repair / no feedback。

适合投稿：
- NLP/AI workshop：RAG evaluation / trustworthy health AI。
- IUI / CUI full：智能交互系统评测。
- Full paper 前提：整理公开或半公开 benchmark，补专家标注。

### 方向 7：可演示的端到端训练计划系统

核心问题：很多论文停留在 recommendation model 或 prompt study，缺少完整可用工作流。

可写贡献：
- 画像填写 -> 生成 12/20 周计划 -> 点击日卡 -> 查看证据 -> 反馈疲劳/疼痛 -> 调整解释。
- 完整视频 demo 和交互脚本。
- 讨论设计经验和系统边界。

适合投稿：
- SportsHCI Demo：首选。
- MobileHCI Demo / Interactivity：如果强调移动端训练流程。
- CUI Interactivity：如果强调对话式画像和计划解释。

## 4. 投稿目标矩阵

| 目标 | 截止/状态（截至 2026-05-12 检索） | 推荐形态 | 适配度 | 需要补的材料 |
|---|---|---|---|---|
| SportsHCI 2026 LBW | 2026-05-25，官网：[LBW](https://www.sportshci2026.com/late-breaking-works) | 4 页左右 short / LBW | 很高 | 系统截图、相关工作、1 个 walkthrough、设计贡献。 |
| SportsHCI 2026 Demo | 2026-07-01，官网：[Demos](https://www.sportshci2026.com/demos) | 6 页 demo + 3 分钟视频 | 最高 | 录屏、demo 脚本、系统架构图、现场展示计划。 |
| MobileHCI 2026 Demo / Interactivity | 2026-06-04 附近，官网：[Demos & Interactivity](https://mobilehci.acm.org/2026/submit/demos-interactivity.html) | Demo / Interactivity | 中高 | 移动端 drawer/sheet、日卡交互、手机视口录屏。 |
| MobileHCI 2026 LBW / Poster | 官网：[LBW Posters](https://mobilehci.acm.org/2026/submit/lbw-posters.html) | LBW poster | 中 | 强调移动使用情境、跑后反馈、日历交互。 |
| ACM CUI 2026 | full/short 截止已过；官网：[Submission](https://cui.acm.org/2026/submission/) | 后续年份或扩展版 | 中 | 需要把系统改写为 conversational planning agent。 |
| ACM CI/HCOMP 2026 | 摘要/全文 6 月，官网：[CFP](https://ci.acm.org/2026/cfp.html) | Talk / short system angle | 中 | 强调 human-AI complementarity，做 AI-only vs human+AI 设计。 |
| UIST 2026 Demo | 2026-07-10 附近，官网：[CFP](https://uist.acm.org/2026/cfp/) | Demo | 低到中 | 需要更强的交互技术创新，不只是应用系统。 |
| RecSys 2026 | 官网：[Call](https://recsys.acm.org/recsys26/call/) | 不建议当前主投 | 低到中 | 需要真实跑者数据集、推荐算法和离线指标。 |

## 5. 建议的近期论文路线

### 路线 A：最快发表 / 最贴当前产品

目标：SportsHCI 2026 Demo。  
题目：

> Protocol-Grounded Interactive Marathon Training Planner with Adaptive Feedback and Evidence-Aware Explanations

最小需要：
- 3 分钟视频：画像 -> 生成计划 -> 日卡 -> 证据 -> 反馈 -> 调整。
- 6 页 demo paper：系统动机、相关工作、架构、交互 walkthrough、局限。
- 截图：训练导航、画像侧栏、训练日历、日卡解释、反馈调整。

### 路线 B：短论文 / LBW

目标：SportsHCI 2026 LBW。  
题目：

> Designing Evidence-Aware Shared-Decision Interfaces for Adaptive Marathon Training Plans

最小需要：
- 相关工作压缩到 4 类。
- 1 个真实使用情景。
- 设计原则：协议约束、证据边界、共享决策、负荷解释。

### 路线 C：后续 full paper

目标：MobileHCI / CUI / IUI / CHI。  
必须补：
- 5-8 名跑者可用性研究，或 3-5 名教练/专家 walkthrough。
- Baseline：普通 LLM prompt、无协议版本、无证据版本。
- 指标：计划可执行性、协议违规数、证据覆盖、用户理解、信任、调整满意度。

## 6. 最推荐的创新组合

优先组合：

1. 协议约束生成：HMP 让计划不是裸 LLM。
2. 证据感知解释：日卡显示哪些安排来自协议/动作库/知识库。
3. 共享决策反馈：疲劳或疼痛后给出调整选项，而不是自动覆盖。
4. 训练负荷可解释：说明风险来自哪里，下一步怎么做。

这四点组合起来，和现有 PlanFitting、Fit to Run、LLM-SPTRec 都能拉开距离：不是单纯推荐，也不是单纯聊天生成，而是“可执行、可审计、可交互修正”的训练处方系统。
