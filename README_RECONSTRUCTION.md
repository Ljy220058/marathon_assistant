# Marathon QA Assistant 重建说明文档

## 1. 架构概览
本项目已从单体 2300+ 行的 `workflow.py` 迁移到模块化的 `marathon_qa_assistant` 包结构。

### 核心设计原则：
- **职责分离**：将状态定义、图构建逻辑、节点实现、工具函数彻底拆分。
- **环境韧性 (Fallback)**：在缺少 `langgraph`、`pydantic` 或 `fastapi` 等依赖的环境下，通过 `FallbackIntegratedApp` 和本地 Mock 类保证代码仍可导入并执行最小功能。
- **单向依赖**：`nodes` 依赖 `core.state_models` 与 `core.kb_provider`/`core.kb_runtime`，`core.workflow` 只负责最终装配。

## 2. 目录结构说明

### `marathon_qa_assistant/core/`
- **`workflow.py`**: 对外统一入口，导出 `integrated_app` 及核心模型。
- **`workflow_graph.py`**: 负责 LangGraph `StateGraph` 的构建及 `FallbackIntegratedApp` 实现。
- **`state_models.py`**: 定义 `IntegratedState` (TypedDict) 和相关数据模型。
- **`kb_provider.py`**: 对外提供知识库运行时访问入口，避免 `workflow` 与节点/界面层互相导入。
- **`kb_runtime.py`**: 维护全局知识库运行时数据（RAG 上下文）。
- **`app_state.py`**: 维护项目全局路径（BASE_DIR）及配置。

### `marathon_qa_assistant/nodes/`
- **`common.py`**: 所有节点的基石，包含 LLM 初始化、安全护栏 Fallback 和通用工具。
- **`security.py`**: 第一道防线，处理输入/输出安全检查。
- **`router.py`**: 意图识别，判定是 QA、PLAN 还是 RESEARCH 模式。
- **`profile_and_retrieval.py`**: 处理用户画像计算、实体抽取及 RAG 检索。
- **`plan_nodes.py`**: 包含 `planner` (生成任务) 和 `executor` (并发执行子任务)。
- **`expert_nodes.py`**: 马拉松专家团（Coach, Therapist, Nutritionist, Auditor）。
- **`output_nodes.py`**: 格式化最终报告并生成引导性问题。
- **`routing/`**: 包含 LangGraph 的条件路由逻辑。

## 4. 训练计划调度补充
- **周级联合调度**：`services/knowledge_graph.py` 中新增 `GraphEngine.plan_week_drafts()`，不再让 `expert_nodes.py` 逐天各自决策，而是以 `WeekState` 顺序推进整周草案。
- **状态推进字段**：调度器在每一天决策前维护 `quality_sessions`、`last_quality_day`、`last_quality_index`、`long_run_done`、`long_run_day`、`history` 等周上下文。
- **约束传播策略**：若当前训练被周级规则阻断，会按 `轻松跑 -> 恢复跑 -> 休息` 顺序降级，避免连续高强度、质量课超 2 次、长距离重复安排、长距离次日继续上强度。
- **可观测性**：每个 day draft 都保留 `status`、`adjustments`、`warnings`、`decision_trace`、`week_state_before`、`week_state_after`，便于 UI 和调试层直接展开。

## 3. 命名映射清单 (旧 -> 新)
- `IntegratedState` -> `marathon_qa_assistant.core.state_models.IntegratedState`
- `security_gate_node` -> `marathon_qa_assistant.nodes.security.security_gate_node`
- `router_node` -> `marathon_qa_assistant.nodes.router.router_node`
- `workflow.py` (旧) -> `marathon_qa_assistant/core/workflow.py` (装配层)

## 5. 验证方式
执行以下命令验证核心链路可用性：
```bash
py -3 -m py_compile marathon_qa_assistant/core/workflow.py
```
或运行集成测试脚本：
```bash
py -3 tests/integration_workflow_test.py
```

## 6. 最近更新 (2026-04-26)
- **Service 层全面重建**: 完成了 `WikiAgent`, `FAISS Vector Store`, `KnowledgeGraph` 的重构与路径修复。
- **多模态功能修复**: `chainlit_app.py` 中的 PDF 视觉提取与 VLM (Llama 3.2-Vision) 逻辑已调通。
- **项目清理**: 彻底移除了 `test_chroma*` 等过时目录，清理了冗余日志。
- **集成测试通过**: 16 节点工作流已通过长链路稳定性验证。
- **周计划调度升级**: `plan_week_drafts()` 已接管周计划草案决策，训练生成从“逐天局部规则”升级为“周级状态推进 + 约束传播”。
- **审计评分前端升级**: `auditor_node` 不再输出固定的 `85 / 90 / 80%`，而是根据 `is_approved`、`iteration_count`、`ranked_evidence.hybrid_score` 与 `entities` 动态计算一致性、安全性和 ROI，并由 `ui/legacy_ui.py` 在 Chainlit/Gradio 共用渲染器中展示“分数 + 评分依据 + 关联证据”。
- **赛事倒计时容错修复**: `apps/chainlit_app.py` 的侧边栏倒计时已支持 `YYYY-MM-DD`、`YYYY/MM/DD`、`YYYY年MM月DD日`、`DD/MM/YYYY` 等日期格式；无法解析时给出明确格式提示，不再直接抛出“格式错误”。
- **FAISS 落盘稳健性修复**: `services/vector_store.py` 在保存用户知识库前会显式重建 `faiss_db/` 目录，避免 Windows 环境下 `index.faiss for writing: No such file or directory`。
