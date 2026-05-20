# 运动处方 M-Agent 论文方向调研包

日期：2026-05-12  
项目：马拉松助手  
定位：从“马拉松计划生成”深化为“证据约束的多专家运动处方式训练决策支持系统”。

## 1. 结论

你的思路有发表空间，而且比“当天训练计划生成”更强。它本质上可以被写成一种“运动处方式训练计划生成”，但建议不要直接宣称为医疗处方，而是定位为：

> 面向耐力跑者的 evidence-gated, protocol-grounded, multi-expert exercise-prescription decision support system。

核心区别是：系统不是让 LLM 自由开训练处方，而是先读取用户画像和风险状态，再用协议、动作库、知识库与专家角色共同形成可审计建议。教练负责最后整合，康复师/安全专家拥有否决权，营养师和体能师只在证据足够时补充各自维度。

## 2. 已使用的团队与技能视角

本轮采用团队模式拆分为 4 个子任务，并综合了 10+ 个技能视角：

- `paper-research-assistant`：论文检索与可核验来源筛选。
- `codex-work-team`：多角色团队拆分。
- `dispatching-parallel-agents`：并行子任务调研。
- `academic-paper`：论文结构与投稿形态。
- `academic-paper-reviewer`：审稿风险视角。
- `brainstorming`：选题深化。
- `api-designer`：处方输出契约。
- `event-driven-architect`：反馈闭环和异步审计。
- `database-architect`：画像、证据、处方轨迹数据结构。
- `senior-backend`：服务化、验证、错误边界。
- `observability-advisor`：计划生成可观测性和审计日志。
- `security-scanner`：提示注入、风险输入和安全边界。
- `project-flow-guardrails`：RAG 证据完整性与评估防错。
- `trae-rules` / `user-habits`：中文优先、最小范围、证据可追溯。

## 3. 调研论文表

PDF 下载目录：`docs/paper_project/magent_exercise_prescription_literature_2026-05-12/pdfs/`

| # | 方向 | 论文 | 年份 | 来源 / DOI | 本地 PDF | 对本论文的作用 |
|---:|---|---|---:|---|---|---|
| 1 | 运动处方 CDSS | The European Association of Preventive Cardiology EXPERT tool | 2017 | https://doi.org/10.1177/2047487317702042 | 未保留，官方页可读 | 规则化运动处方标杆：画像、风险、FITT 与禁忌优先。 |
| 2 | 运动处方 CDSS | Development of a Novel Clinical Decision Support System for Exercise Prescription Among Patients With Multiple Cardiovascular Disease Risk Factors | 2021 | https://doi.org/10.1016/j.mayocpiqo.2020.08.005 | `p3ex_pescatello_2021.pdf` | P3-EX 流程可借鉴为 Prioritize -> Personalize -> Prescribe。 |
| 3 | 运动处方算法 | An exercise prescription algorithm for clinicians to use with their patients with cardiovascular disease risk factors | 2025 | https://doi.org/10.1177/20552076251360884 | `p3ex_algorithm_digital_health_2025.pdf` | 临床端低时间成本、输入容错和满意度评估。 |
| 4 | AI 运动处方评估 | Using artificial intelligence for exercise prescription in personalised health promotion | 2024 | https://doi.org/10.5114/biolsport.2024.133661 | `gpt4_exercise_prescription_biology_sport_2024.pdf` | 证明裸 GPT-4 处方需要专家监督和安全校验。 |
| 5 | AI 训练计划 | Artificial intelligence in sport: using ChatGPT in resistance training prescription | 2024 | Biology of Sport / DOAJ | `chatgpt_resistance_training_biology_sport_2024.pdf` | LLM 草案可用，但个体化、进阶负荷和专家修正不足。 |
| 6 | 对话式运动计划 | PlanFitting: Personalized Exercise Planning with Large Language Model-driven Conversational Agent | 2023 / CUI 2025 | https://arxiv.org/abs/2309.12555 | `planfitting_2023.pdf` | 最接近的 LLM 运动计划系统；我们的差异应落在证据门、专项协议和多专家审计。 |
| 7 | 运动 LLM 综述 | Using Large Language Models to Enhance Exercise Recommendations and Physical Activity | 2025 | JMIR Medical Informatics | `llm_exercise_recommendations_jmir_2025.pdf` | 可作为健康运动 LLM 相关工作入口。 |
| 8 | 健康推荐系统 | Development and Evaluation of Health Recommender Systems: Systematic Scoping Review and Evidence Mapping | 2023 | https://doi.org/10.2196/38184 | `hci_health_recommender_review_2023.pdf` | 评估设计参考：不仅看推荐准确率，还看用户、临床和实现证据。 |
| 9 | 体力活动用户模型 | User Models for Personalized Physical Activity Interventions: Scoping Review | 2019 | https://doi.org/10.2196/11098 | `hci_user_models_physical_activity_2019.pdf` | 用户画像字段、长期状态和个性化干预设计参考。 |
| 10 | 马拉松推荐 | Recommendations for marathon runners: recommender systems and ML to support recreational marathon runners | 2022 | https://doi.org/10.1007/s11257-021-09299-3 | 未下载到本包，Springer OA 可取 | 马拉松推荐系统核心综述，对比现有推荐/预测工作。 |
| 11 | 马拉松 APP 数据 | Retrospective Analysis of Training and Its Response in Marathon Finishers Based on Fitness App Data | 2021 | https://doi.org/10.3389/fphys.2021.669884 | `train_app_data_marathon_2021.pdf` | 训练响应、真实 APP 数据和跑者分层参考。 |
| 12 | 马拉松生理 | Physiology and Pathophysiology of Marathon Running | 2025 | https://doi.org/10.1186/s40798-025-00810-3 | `train_marathon_physiology_2025.pdf` | 马拉松生理、风险与训练解释背景。 |
| 13 | 训练强度分布 | Recent advances in training intensity distribution theory for cyclic endurance sports | 2025 | https://doi.org/10.3389/fphys.2025.1657892 | `train_tid_theory_2025.pdf` | 周期化和强度分布协议层参考。 |
| 14 | 低强度训练 | Why low-intensity endurance training for athletes? | 2025 | https://doi.org/10.1007/s00421-025-05843-w | `train_low_intensity_2025.pdf` | 支持“多数训练保持低强度”的容量控制逻辑。 |
| 15 | 减量训练 | Effects of tapering on performance in endurance athletes | 2023 | https://doi.org/10.1371/journal.pone.0282838 | `train_tapering_meta_2023.pdf` | 赛前 2-3 周 taper 的处方规则来源。 |
| 16 | 跑步伤病 | The Prevention and Treatment of Running Injuries: A State of the Art | 2021 | https://doi.org/10.26603/001c.25754 | `safety_running_injuries_state_art_2021.pdf` | 康复师/安全专家的跑步伤病知识源。 |
| 17 | 训练负荷主观监控 | The Current State of Subjective Training Load Monitoring | 2018 | https://doi.org/10.1007/s40279-018-0967-3 | `safety_subjective_load_2018.pdf` | RPE、疲劳反馈与自适应调整输入。 |
| 18 | 跑步伤病连续体 | The Running Injury Continuum | 2023 | https://doi.org/10.1371/journal.pone.0292369 | `safety_injury_continuum_2023.pdf` | 疼痛反馈不应一刀切，可转化为分级风险处理。 |
| 19 | 运动营养立场 | Nutrition and Athletic Performance | 2016 | https://doi.org/10.1016/j.jand.2015.12.006 | `nutrition_acsm_position_2016.pdf` | 营养师 agent 的训练前中后补给依据。 |
| 20 | 耐力跑营养 | Contemporary Nutrition Strategies to Optimize Performance in Distance Runners and Race Walkers | 2019 | World Athletics | `nutrition_distance_runners_2019.pdf` | 马拉松/半马补给、碳水和水合策略。 |
| 21 | RAG 基础 | Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks | 2020 | https://arxiv.org/abs/2005.11401 | `ai_rag_foundation_2020.pdf` | 证据检索增强生成基础。 |
| 22 | 医疗 RAG 综述 | Retrieval augmented generation for large language models in healthcare | 2025 | https://doi.org/10.1371/journal.pdig.0000877 | `ai_healthcare_rag_review_2025.pdf` | 健康场景 RAG 评估、安全和伦理参考。 |
| 23 | 引用生成 | Enabling Large Language Models to Generate Text with Citations | 2023 | https://arxiv.org/abs/2305.14627 | `ai_generate_citations_2023.pdf` | 每条训练建议绑定证据 ID 的技术依据。 |
| 24 | 原子事实评估 | FActScore | 2023 | https://arxiv.org/abs/2305.14251 | `ai_factscore_2023.pdf` | 将处方拆成原子 claim 逐条查证。 |
| 25 | RAG 评测 | Ragas | 2023 | https://arxiv.org/abs/2309.15217 | `ai_ragas_2023.pdf` | 扩展为 Exercise-RAGAS：faithfulness、evidence coverage、answer relevancy。 |
| 26 | 人机交互准则 | Guidelines for Human-AI Interaction | 2019 | https://doi.org/10.1145/3290605.3300233 | `hci_human_ai_guidelines_2019.pdf` | AI 处方解释、可控性和纠错交互准则。 |
| 27 | 过度依赖 AI | To Trust or to Think | 2021 | https://doi.org/10.1145/3411764.3445172 | `hci_cognitive_forcing_2021.pdf` | 防止用户盲从计划：用认知强制设计让用户确认风险与偏好。 |

本包当前保留 29 个有效 PDF；上表只列最适合写论文的 27 个。两个下载失败的 HTML 伪 PDF 已删除。

## 4. 建议的创新工作流

建议命名：

> M-EXRx Agent: Evidence-Gated Multi-Expert Exercise Prescription for Endurance Training

核心工作流：

```text
User Query
  -> Load User Profile Summary
  -> Pre-Gate Request Filter
  -> Intent + Risk + Prescription Parser
  -> Prescription Contract Builder
       FITT-VP + HMP protocol + available days + race date + contraindications
  -> Evidence Router
       action library, HMP protocol, endurance KB, injury KB, nutrition KB, user history
  -> Expert Panel Drafting
       Coach Agent: macrocycle / mesocycle / weekly structure
       S&C Agent: strength, capacity, load progression
       Rehab Agent: injury risk, pain/fatigue downgrade, referral boundary
       Nutrition Agent: fueling, hydration, recovery nutrition
       Evidence Librarian: citation and source binding
  -> Conflict Arbitration
       safety > protocol > user constraints > performance optimization
  -> Coach Synthesizer
       final plan only from approved candidates
  -> Independent Audit
       protocol audit + safety audit + citation audit + unsupported-claim audit
  -> Bounded Repair
       repair citation, wording, evidence tier, refusal boundary only
  -> Final Output
       prescription plan + trace + evidence_ids + audit_result + user choice points
```

与现有工作的较大创新点：

1. **从单智能体计划生成变成“处方合同”**  
   系统先构造 `PrescriptionContract`，包含 FITT-VP、HMP 阶段、容量预算、风险禁忌、证据需求，再允许生成。

2. **多专家不是 prompt 角色扮演，而是有权限边界**  
   康复/安全 agent 可以否决教练计划；营养师只能补充补给建议，不能改变主课；教练只能整合已批准候选。

3. **动作库优先于 LLM 自由生成**  
   训练主课来自 action library 和协议候选。知识库只补解释、缺失字段和安全说明，不允许凭空开新处方。

4. **冲突仲裁可审计**  
   当性能目标与安全风险冲突，系统按 `medical referral / safety downgrade / protocol repair / coach optimization` 的顺序裁决。

5. **提出运动处方专用评测基准**  
   可设计 `M-EXRxBench`：覆盖目标备赛、伤痛反馈、营养补给、疲劳漏训、证据不足、诱导越权等场景。

## 5. 评测设计

最小可投稿实验：

| 设置 | 描述 |
|---|---|
| S0 裸 LLM | 只给用户画像和请求，直接生成计划。 |
| S1 Vanilla RAG | 检索知识库后让 LLM 生成。 |
| S2 Single Coach + Protocol | 单教练 agent，加入 HMP 协议约束。 |
| S3 Multi-Agent without Evidence Gate | 多专家输出，但缺少硬证据门。 |
| S4 Full M-EXRx Agent | 协议 + 动作库 + 多专家 + 证据门 + 审计修复。 |

指标：

- `protocol_violation_rate`：违反周期化、恢复间隔、容量预算的比例。
- `unsupported_prescription_rate`：无证据支持的训练主课/补给/风险建议比例。
- `safety_downgrade_recall`：疲劳、疼痛、异常心率等场景是否正确降级。
- `citation_validity`：引用是否存在、是否对应证据。
- `expert_actionability_score`：教练/康复/营养专家对可执行性的评分。
- `conflict_resolution_quality`：专家意见冲突时是否给出合理裁决。
- `user_control_score`：用户是否能理解并选择调整方案。

## 6. 投稿方向

| 目标 | 状态（2026-05-12） | 推荐形态 | 建议 |
|---|---|---|---|
| SportsHCI 2026 | LBW 2026-05-25；Demo 2026-07-01 | LBW / Demo | 最优先，强调跑步训练决策支持、伤病预防、人机协作。 |
| MobileHCI 2026 | Demo / Panel 2026-06-18 | Demo & Interactivity | 如果突出移动端训练日历、反馈闭环、可穿戴数据。 |
| RecSys 2026 | Industry 2026-05-21；Demo/R&P 2026-07-15 | Industry / Demo / R&P Note | 如果强调推荐系统、约束满足、可解释推荐。 |
| CUI 2027 | 2026 已错过 | Full / Short / Provocation | 如果强化对话式画像采集、多专家对话与风险追问。 |
| JMIR mHealth and uHealth | 期刊滚动投稿 | Original Paper / Implementation Report | 需要用户研究或真实使用数据。 |
| Scientific Reports | 期刊滚动投稿 | Article | 需要更强实验证据和统计评估。 |

短期建议：

1. **先冲 SportsHCI Demo / LBW**：用现有系统展示画像、计划、证据、反馈、审计轨迹。
2. **同时准备 RecSys R&P Note**：把工作流写成可解释、安全约束的训练推荐系统。
3. **中期做 full paper**：补 3-5 名教练/康复/营养专家 walkthrough，加 30-50 个 benchmark case。

## 7. 下一步落地清单

- 明确 `PrescriptionContract` schema：用户画像、目标、风险、FITT-VP、HMP 阶段、证据需求。
- 把专家输出标准化为 `proposal / contraindications / evidence_ids / confidence / repair_request`。
- 增加 `EvidenceGate`：动作库不足时禁止 LLM 自由生成主课。
- 增加 `ConflictArbitrator`：安全优先的多专家意见裁决。
- 扩展 benchmark：至少 30 个案例，覆盖训练计划、疲劳反馈、疼痛风险、补给、缺证拒答。
- 准备 demo 视频脚本：画像 -> 生成 -> 证据日卡 -> 疲劳反馈 -> 多专家审查 -> 教练最终方案。
