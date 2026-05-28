# 说明文档

## 1. 架构概览

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
- **`app_state.py`**: 维护项目全局路径（BASE\_DIR）及配置。

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

```powershell
# 编译检查核心模块（需设置 monorepo PYTHONPATH）
$env:PYTHONPATH="apps/backend/src"; python -m py_compile apps/backend/src/marathon_qa_assistant/core/workflow.py
```

或运行集成测试脚本：

```powershell
$env:PYTHONPATH="apps/backend/src"; python -m pytest tests/test_training_plan_skeleton.py tests/test_api_cli_startup_contract.py -q
```

## 6. 系统要求

### 最低配置
- **CPU**: 4 核以上
- **内存**: 8GB RAM
- **存储**: 5GB 可用空间（模型 + 向量库）

### 推荐配置（LLM 实时推理）
- **GPU**: NVIDIA GPU 6GB+ VRAM（运行 qwen2.5:latest 等 7B 模型）
- **或**: DeepSeek API Key（设置 `DS_API_KEY` 环境变量使用云端推理）
- **内存**: 16GB RAM

### CPU-only 环境说明
在仅有 CPU 的环境下：
- LLM 推理可能超时（qwen2.5/llama3 在 CPU 上生成复杂训练计划需要 >60 秒）
- 可使用 `response_mode: "skeleton"` 获得规则驱动的骨架训练计划（无需 LLM）
- 或配置 `DS_API_KEY` 环境变量使用 DeepSeek 云端 API 获得完整 AI 教练体验

## 7. 快速启动

### 准备工作

1. 确保已安装 Ollama 并拉取对应模型：
   ```bash
   ollama pull qwen2.5:latest
   ollama pull llama3.2-vision:latest
   ```
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

### 启动前端 (Astro)

当前主交互界面是 `apps/web/` 下的 Astro 前端。请先启动 FastAPI 后端，再启动前端：

```bash
cd apps/web
npm run dev
```

中文路径下建议使用 `apps/web/start_ascii.cmd`，脚本会把前端同步到临时英文路径后启动，避免 Vite/esbuild 解析路径失败。

### 启动后端 API (FastAPI)

如果需要通过接口调用：

```bash
$env:PYTHONPATH="apps/backend/src"; python -m uvicorn marathon_qa_assistant.apps.api_app:app --host 127.0.0.1 --port 8000
```

当前 `/query` 接口按项目现状仅支持单用户画像，`user_id` 需传 `default_user`；传入其他值会被显式拒绝，避免误以为已经支持多用户隔离。

### RAG 评测脚本

项目内置 RAG 评测脚本：

```bash
$env:PYTHONPATH="apps/backend/src"; python tools/kb/evaluate_rag_ragas.py
```

该脚本使用当前 `marathon_qa_assistant.services.vector_store` 中的向量库实现，并默认读取项目根目录下的 `data/vector_kb/default`。运行前需确保已安装 `requirements.txt` 中的 RAG 评测依赖，并已准备 `data/vector_kb/default/eval_dataset.json`。
评测报告默认输出到当前项目根目录下的 `rag_eval_report.md`。脚本只汇总显式启用的 Ragas 评分项，不再把 `reference` 之类的数据列误记为指标。
传统检索部分默认输出三档 Top-5 口径：`精确块命中`（同一 `chunk_id`）、`同页命中`（同一 `source_file` 且同页）、`同文档命中`（同一 `source_file`），便于区分“没召回到参考文档”和“召回到相邻块但未命中精确 chunk”这两类情况。
当前检索侧还会对中文问题额外构造一个偏英文术语的查询变体，并与原查询结果做融合重排，用于缓解“中文问题检索英文知识库”时的召回偏弱。

## 8. 最近更新 (2026-04-29)

- **Git 仓库初始化**: 已完成项目根目录 Git 初始化。
- **依赖收口**: 统一 `requirements_api.txt` 为根目录 `requirements.txt`，保留 FastAPI、FAISS 等核心依赖；Chainlit 运行入口已移除。
- **Gradio 废弃**: 已移除 `legacy_ui.py` 中的 Gradio 锁屏逻辑，准备清理冗余 entry points。
