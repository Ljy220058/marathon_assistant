# Ollama Pro GraphRAG Platform v2.0 项目执行计划书

## 1. 项目基本信息
- **项目名称**: Ollama Pro GraphRAG Platform v2.0
- **需求描述**:
    - 升级原有 LangGraph 工作流为 Team + Subagent 混合架构。
    - 引入全流程 Token 管控模块，实现成本可视化与配额限制。
    - 深度整合前后端，增强当前 Astro/FastAPI 前端的流式反馈与风险拦截能力。
    - 建立 AI 审计机制，确保生成内容的合规性与质量。
- **截止时间**: 2026-04-23 (7天)
- **总 Token 预算**: 5,000,000 Tokens

## 2. 里程碑节点
| 阶段 | 交付物 | 截止日期 | 责任人 |
|------|--------|----------|--------|
| M1: 架构设计 | 《混合架构设计方案》、v2.0 基础框架代码 | D+2 | PM (我) / 开发智能体 |
| M2: 核心功能 | Token 管控模块、AI 审计节点实现 | D+4 | 开发智能体 / 审计员 |
| M3: 前后端整合 | 优化后的 `integrated_platform.py` | D+5 | 前端 / 后端开发智能体 |
| M4: 验收交付 | 《联调问题报告》、《上线验收报告》 | D+7 | 测试工程师 / 审计员 |

## 3. 资源分配 (智能体矩阵)
- **后端开发智能体**: 负责 `workflow_engine.py` 的架构重构、API 接口设计与 Token 统计逻辑。
- **前端开发智能体**: 负责 `integrated_platform.py` 的 UI 交互优化、流式日志展示与前端拦截逻辑。
- **AI 整合审计员**: 负责在 `LangGraph` 中作为独立节点，对 `draft_plan` 和 `final_report` 进行质量审计。
- **测试工程师智能体**: 负责 `evaluate_workflow.py` 的升级与全链路测试。
- **PM 智能体 (我)**: 整体统筹、Token 调度与风险决策。

## 4. 验收标准
1. **混合架构**: 能够根据问题复杂度自动切换 Team (多专家) 或 Subagent (主从) 模式。
2. **Token 管控**: UI 需实时显示当前会话的 Token 消耗，且支持超过配额后的熔断。
3. **零重大事故**: 经过 AI 审计员验证，无内容合规性风险。

## 5. 功能扩展记录 (M4+)
### 5.1 Cross-Document Analytics (跨文档实体分析)
- **技术需求**: 用户在 Graph Explorer 中多选实体，自动触发多智能体跨文档聚合分析，解决实体关联推理的信息过载与碎片化问题。
- **组间实现方法**:
  - `workflow_engine.py`: 新增 `research_analyst_node`，接收多个实体列表，提取相关子图 chunk IDs，使用 Cross-Encoder (ms-marco-MiniLM-L-6-v2) 重排序并过滤 Top 15，组装后送入大模型生成分析报告。
  - `integrated_platform.py`: 修改 `entity_selector` 为多选下拉框，增加 `handle_research_analysis` 异步生成器，与 UI 中的 `analyze_entities_btn` 绑定，实时渲染 JSON 结构化分析报告。

### 5.2 Dynamic Adaptive Planning (动态自适应计划调整)
- **技术需求**: 根据用户近期的疲劳度反馈、异常心率或缺席训练记录，动态调整（Adaptive Planning）当前的马拉松训练计划，防止过度训练。
- **组间实现方法**:
  - `workflow_engine.py`: 在 `IntegratedState` 中新增 `adaptive_feedback` (疲劳度、缺席、异常、备注)。新增 `adaptive_coach_node`，专门处理带反馈的计划调整；修改 `gate_decision` 和 `after_therapist_route` 等路由节点，支持 `mode="adaptive"` 链路。
  - `integrated_platform.py`: 在 UI 中新增 "Adaptive Plan Adjustment" 手风琴面板（包含滑块和复选框）；新增 `handle_adaptive_plan` 方法封装 `handle_qa` 并注入 `adaptive` 模式与反馈数据，绑定至生成按钮。

### 5.3 Weekly Draft Scheduler (周级联合决策调度器)
- **技术需求**: 将周训练计划生成从“逐天独立决策”升级为“带状态推进的周级调度”。新增 `plan_week_drafts(week_skeleton, athlete_profile, graph_engine)` 能力，保证无连续高强度、质量课不超过 2 次、长距离每周不超过 1 次，且每一天都可输出 `status / adjustments / warnings` 供 UI 展示。
- **组间实现方法**:
  - `marathon_qa_assistant/services/knowledge_graph.py`: 在 `GraphEngine` 中新增 `plan_week_drafts()`、`_build_week_planner_context()`、`_evaluate_week_level_rules()`、`_update_week_state()`。通过 `WeekState` 顺序推进 `quality_sessions`、`last_quality_day`、`long_run_done` 等状态，并在 blocked 时按 `轻松跑 -> 恢复跑 -> 休息` 自动降级。
  - `marathon_qa_assistant/nodes/expert_nodes.py`: 不再内嵌逐日 `decide_workout_draft` 循环，而是直接消费 `plan_week_drafts()` 输出的 week drafts，再做表格渲染与结构化 `Decision Draft Objects` 展示。
  - `README_RECONSTRUCTION.md`: 同步记录调度器职责、状态字段、约束传播与可观测性，确保后续维护者能直接定位周级规划入口。

### 5.4 Audit Score UX + Countdown Hardening
- **技术需求**:
  - 前端需要美观展示一致性评分、安全性评分、知识回报率（ROI），且必须能解释这些分数“为什么是这个值”，不能只显示静态数字。
  - 修复“赛事倒计时: 格式错误”问题，使用户画像中的赛事日期支持多种常见格式。
  - 修复 ROI 固化问题，保证分数随证据质量和实体覆盖变化而动态波动。
- **组间实现方法**:
  - `marathon_qa_assistant/nodes/expert_nodes.py`: `auditor_node` 基于 `is_approved`、`iteration_count`、`ranked_evidence[:5].hybrid_score`、`entities` 计算动态分数，并补充 `score_sources` 说明字段。
  - `marathon_qa_assistant/nodes/output_nodes.py`: 将 `audit_scores`、`score_sources` 与 `evidence_base` 装配到统一的 `structured_report.audit_block`，作为前端唯一消费入口。
  - `marathon_qa_assistant/ui/report_ui.py`: 在共享渲染器中新增“质量与安全审计”面板，统一输出“分数 + 评分依据 + 关联证据”，供当前 Astro/FastAPI 链路复用。
  - `marathon_qa_assistant/ui/plan_ui.py`: 保留可复用展示 props 构造逻辑，作为当前 Astro/FastAPI 链路的中立 UI 辅助层。
  - `marathon_qa_assistant/services/vector_store.py`: 在用户知识库构建前显式创建 `faiss_db/`，避免倒计时与审计修复期间被索引构建异常阻断联调。
- **验收标准**:
  - 相同问答在证据列表变化时，ROI 不再长期固定在 `80%`。
  - 报告顶部能看到三项评分及其解释依据。
  - 赛事日期使用上述 4 种格式时，侧边栏均能显示正常倒计时或明确提示。

---
*由 Senior Technical PM 生成 | 2026-04-16*
