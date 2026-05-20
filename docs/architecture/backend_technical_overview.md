# 后端技术文档

## 1 技术栈概览

> 当前状态：Chainlit 可运行开发线已移除；`marathon_qa_assistant/ui/plan_ui.py`、`ui/coach_state.py`、`ui/ui_config.py` 保留原先可复用的纯展示/状态辅助，供 FastAPI、Astro 和测试继续使用。

| 层次 | 技术选型 |
|------|---------|
| 编程语言 | Python |
| UI / 本地服务承载 | Astro（当前主交互 UI） + FastAPI（本地 API） |
| Agent 编排 | LangGraph（`StateGraph`，含 conditional routing / loop / astream 流式事件 / HITL checkpoint） |
| LLM 接入（两条线） | LangChain `ChatOllama`（直连 `http://localhost:11434`）；OpenAI 兼容 SDK `openai`（`base_url="http://localhost:11434/v1"`） |
| RAG（向量检索） | TF‑IDF（scikit‑learn）+ 稀疏矩阵（scipy）+ 本地文件落盘（jsonl / pkl / npz） |
| GraphRAG | Microsoft GraphRAG（CLI）+ LiteLLM（OpenAI provider）+ LanceDB（向量库）+ Parquet（索引表） |

---

## 2 主要入口（Entry Points）

| 文件 | 职责 |
|------|------|
| `apps/web/` / `apps/backend/src/marathon_qa_assistant/apps/api_app.py` | **当前主入口**：Astro 前端调用 FastAPI 本地 API；Chainlit 可运行入口、启动脚本与专属应用包已移除。 |
| `apps/backend/src/marathon_qa_assistant/apps/api_app.py` | **当前 API 入口**：提供 `/health` 与 `/query`；`__main__` 通过 `uvicorn.run(app, host="0.0.0.0", port=8000)` 启动。 |
| `tools/kb/evaluate_rag_ragas.py` | **当前 RAG 评测入口**：读取项目根 `data/vector_kb/default`，执行 Ragas 指标和传统检索指标评测，输出 `rag_eval_report.md`。 |
| `tools/kb/generate_eval_dataset.py` | **评测集生成脚本**：为 RAG 评测生成或整理 `eval_dataset.json`。 |
| `tools/kb/kb_gap_check.py` | **知识库缺口检查脚本**：用于定位知识库覆盖缺失与证据缺口。 |
| `archive/2026-04-30_history_batch/` | **历史原型归档区**：旧版 `langgraph_multi_agent.py`、`evaluate_workflow.py` 等原型脚本已归档，不再作为当前入口。 |

---

### 2.1 当前高风险回归测试

- `tests/test_high_risk_contracts.py`：补充跨模块契约测试，覆盖 `plan_nodes._build_plan_prompt()` 的周计划硬约束与证据引用规则、`profile_and_retrieval.build_ranked_evidence()` 的证据编号顺序、`output_nodes._build_structured_report()` 的结构化报告字段完整性，以及 `chainlit_app.update_sidebar()` 在 Coach Mode 下的 `Z1-Z9` 九区展示一致性。
- `tests/test_wiki_module_contract.py`：补充 Wiki 辅助检索契约测试，覆盖概念类/研究类问题触发 Wiki、计划类问题跳过 Wiki、`expert_nodes._run_expert_llm()` 消费 `wiki_context` 但不把 Wiki 当作编号证据，以及 `output_nodes._build_structured_report()` 保留 Wiki 上下文用于审计。
- `tests/test_api_cli_startup_contract.py`：补充入口启动契约测试，覆盖 `api_app.py` 的 `/health` 默认模型回退、`__main__` 分支对 `uvicorn.run(app, host="0.0.0.0", port=8000)` 的启动参数约束，以及 `app_chainlit.py` 壳入口对 Chainlit 符号透传和命令提示 `chainlit run app_chainlit.py -w` 的稳定性。
- `tests/test_training_plan_models.py`：补充多周训练计划基础层测试，覆盖 `StructuredTrainingPlan` 的 4 周/20 周结构校验、`WeekPlan` 的 7 天完整性，以及相邻周重复检测的 `pass / warn / fail` 判定。
- `tests/test_training_plan_context.py`：补充周数对齐测试，覆盖 `4周/20周` 请求解析、`target_race_date -> plan_duration_weeks` 换算，以及“显式请求优先于画像倒计时”的生成链路前半段契约。
- `tests/test_training_plan_skeleton.py`：补充结构骨架测试，覆盖 `executor` 下游会消费的 `structured_training_plan` 4 周/24 周输出、结构校验与相邻周非 `fail` 约束。
- `tests/test_coach_ui_state_contract.py`：补充 Coach Mode 状态契约测试，按 `M1-STORY-03` 状态流转表覆盖 14 类页面状态 / 消息状态组合，确保极速画像补填、高级画像补全、显式重生成、异常兜底与非 Coach 入口隔离不会回归。
- 测试启动引导统一避免在 `tests/*.py` 中对项目根使用 `Path(__file__).resolve()`；当前项目目录是 Junction，测试侧应保留入口路径（如 `Path(__file__).parents[1]`），否则导入可能漂移到真实物理目录并击穿当前工作区契约。
- `tests/test_high_risk_contracts.py`：当前还额外覆盖 `M1-TASK-11` 与 Week 4-B 的计划交互契约，校验首周执行入口上下文提取、首周执行说明文案、快速反馈模板、训练反馈卡结构与计划失败重试文案，防止“计划能展示但没有下一步入口”或“执行后没有真实反馈提交流程”回归。
- `tests/test_high_risk_contracts.py`：现继续覆盖 `M1-TASK-13` 的 `4/8/12 周` 展示验证矩阵，校验结构化计划优先渲染、长计划不回退旧 Markdown、周卡片数量完整，以及 `>=8 周` 时周卡片导航区块稳定出现。
- `tests/test_high_risk_contracts.py`：现补 Week 5 的自适应契约与展示测试，覆盖训练反馈到 `mild_fatigue / high_fatigue / pain_risk / missed_workout` 的原因映射、4 类原因对应的结构化调整字段产出、无触发原因时的稳定默认值，以及 `structured_report.adaptive_adjustment` / `recommendations` / 共享渲染层自适应卡 / Chainlit 专用调整卡的透出，防止自适应链路继续停留在“有结果但看不见”的弱展示状态。

---

## 3 LangGraph 工作流模块

| 文件 | 模式 | 说明 |
|------|------|------|
| `marathon_qa_assistant/core/workflow.py` | 工作流装配层 | 汇总各节点处理器并导出 `integrated_app`、状态模型与画像读写接口 |
| `marathon_qa_assistant/core/workflow_graph.py` | 图构建 / fallback | 在有 `langgraph` 依赖时构建 `StateGraph`；缺失依赖时退化为 `FallbackIntegratedApp` |
| `marathon_qa_assistant/core/training_plan_models.py` | 多周计划基础层 | 定义多周训练计划数据契约、结构校验与相邻周重复检测，为后续 4-20 周结构化生成与模板渲染提供统一真源 |
| `marathon_qa_assistant/core/training_plan_context.py` | 周数解析与对齐层 | 统一解析用户请求中的 `requested_weeks`，并把 `target_race_date / plan_duration_weeks` 对齐为计划生成阶段消费的周期长度 |
| `marathon_qa_assistant/core/training_plan_skeleton.py` | 多周骨架生成层 | 根据对齐后的周期、画像和训练日约束，生成 `structured_training_plan` 的 `phase_summary + week_plans[] + first_week_actions[]` 骨架，并同步补齐每周 `key_workouts[] / action_suggestions[]` 展示字段 |
| `marathon_qa_assistant/core/state_models.py` | 统一状态与 DTO 契约层 | 现补充 `WorkoutFeedback / AdaptiveReason / AdaptiveFeedback / AdaptiveAdjustment`，并提供训练反馈标准化、Week 5 原因映射、自适应最小规则库与结构化调整结果构造函数 |
| `marathon_qa_assistant/services/analytics.py` | Week 7 埋点记录层 | 统一生成 `event_name / user_id_hash / session_id / version / timestamp / properties` 公共字段，并将路线图核心事件以 JSONL 写入运行期数据目录；`plan_generate_clicked` 只接受显式用户动作来源，`build_plan_click_properties` 追加 `source_type: message|action` 区分自由输入与按钮点击 |
| `marathon_qa_assistant/apps/chainlit/plan_ui.py` | 计划展示交互辅助层 | 从 `structured_report` 提炼首周执行上下文，并生成首周执行说明、快速训练反馈模板、训练反馈卡、反馈状态 bundle 与计划失败重试文案，供 `logic.py / actions.py` 复用 |
| `marathon_qa_assistant/ui/legacy_ui.py` | 多周计划共享渲染层 | 优先消费 `structured_training_plan` 渲染周卡片；对 `>=8 周` 长计划额外输出阶段级“周卡片导航”；同时把 `structured_report.adaptive_adjustment` 渲染为共享 `自适应调整卡`，让 Chainlit 主报告和后续其他入口保持同口径 |
| `marathon_qa_assistant/nodes/security.py` | 安全入口 | 执行安全门控与模式分流前置校验 |
| `marathon_qa_assistant/nodes/router.py` / `nodes/routing/__init__.py` | 条件路由 | 根据问题类型、画像状态与审查结果决定下一节点 |
| `marathon_qa_assistant/nodes/profile_and_retrieval.py` | 画像与检索 | 执行画像补全、实体抽取、Wiki 概念辅助检索与证据融合排序；Wiki 不作为训练处方主证据源 |
| `marathon_qa_assistant/nodes/plan_nodes.py` / `expert_nodes.py` / `output_nodes.py` | 计划生成与输出 | `plan_nodes.py` 同时产出 LLM 文本计划和 `structured_training_plan` 骨架；Week 5 起 `expert_nodes.py` 会把标准化训练反馈交给 `state_models.py` 的最小规则引擎，`output_nodes.py` 除透出 `adaptive_adjustment` 外，还会把明日调整 / 本周微调 / 替代训练写入 `recommendations`，并为共享渲染层 / Chainlit 专用自适应卡提供稳定字段 |

---

## 4 LLM 接入（Ollama）

### 4.1 LangChain 原生（主要用于 LangGraph 节点）

```python
from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="qwen2.5:latest",   # 或 "qwen2.5"
    base_url="http://localhost:11434"
)
```

调用方：`marathon_qa_assistant/apps/chainlit_app.py`、`apps/backend/src/marathon_qa_assistant/apps/api_app.py` 及当前工作流节点。

### 4.2 OpenAI 兼容 API（用于多模态 / GraphRAG）

```python
from openai import OpenAI

client = OpenAI(
    api_key="ollama",
    base_url="http://localhost:11434/v1"
)
```

调用方：
- `实验七_多模态应用/multimodal_chatbot.py`（视觉模型对比）
- `graphrag_project/settings.yaml`（GraphRAG 的 LiteLLM provider）

---

## 5 本地 RAG（TF‑IDF）

### 5.1 预处理 / 文档抽取

- **当前实现入口**：`marathon_qa_assistant/services/document_preprocess.py` + `marathon_qa_assistant/services/vector_store.py`
- **输入**：PDF（PyMuPDF `fitz` 优先，fallback `pypdf`）、DOCX（`python-docx`）、TXT、MD
- **处理方式**：运行时直接抽取页面文本并做 `normalize_text()` 标准化，再进入切块流程；不再依赖项目根单独的 `preprocess_docs.py` 脚本作为现行入口

### 5.2 向量库构建 / 加载 / 检索

- **当前实现入口**：`marathon_qa_assistant/services/vector_store.py::main()`
- **切块**：`split_text(chunk_size, chunk_overlap)`，每块带 `chunk_id`
- **向量化**：`sklearn.feature_extraction.text.TfidfVectorizer`
- **持久化**：
  - `chunks.jsonl`（文本块列表）
  - `tfidf_vectorizer.pkl`（模型）
  - `tfidf_matrix.npz`（稀疏矩阵，fallback 纯 `pkl`）
- **构建 / 测试 CLI**：仍通过 `--mode build | test` 暴露，但入口已收口到 `vector_store.py`，不再依赖项目根单独的 `build_vector_kb.py`
- **检索**：`retrieve(query, top_k)` — query 归一化 + 关键词 hints 扩展 + 余弦 / 点积相似度

### 5.3 知识库目录结构

```
domain_docs/          # 原始领域文档（PDF 等）
cleaned_docs/         # 清洗后的 .cleaned.txt
data/vector_kb/default/            # 全局 TF‑IDF 知识库（chunks.jsonl / vectorizer.pkl / matrix.npz）
../_runtime_data/<project_name>/data/uploads/seed/   # 运行期上传文档（项目根目录外）
../_runtime_data/<project_name>/data/data/vector_kb/default/user/  # 运行期用户知识库产物（项目根目录外）
```

- **加载优先级**：运行时入口（如 `app_chainlit.py`、`marathon_qa_assistant/apps/chainlit_app.py`、`api_app.py`）会优先加载 `data/data/vector_kb/default/user/`；仅当用户知识库尚未构建时，才回退到 `data/vector_kb/default/`。这样可避免“上传并重建成功，但重启后仍命中旧库”的错位问题。
- **Chainlit 启动时机**：`marathon_qa_assistant/apps/chainlit_app.py` 不再在模块导入阶段同步执行 `init_knowledge_base()`；改为在 `@cl.on_chat_start` 中按需调用 `ensure_knowledge_base_ready()`，并在重建索引后显式 `force_reload=True` 刷新，避免导入测试、热重载和入口探测阶段产生知识库加载副作用。
- **构建落盘约束**：重建 `data/data/vector_kb/default/user/` 时，构建流程会先清理并重新创建 `faiss_db/` 目录，再写入 `index.faiss`；若该子目录不存在，FAISS 会直接报 `could not open ...\index.faiss for writing`。
- **Windows 写盘兜底**：若 FAISS 在 Windows 运行时目录（尤其含中文路径）直接写盘失败，保存链路会先落到系统临时目录下的 ASCII 暂存目录，再将 `index.faiss / index.pkl` 回写到 `data/data/vector_kb/default/user/faiss_db/`，避免因路径兼容性导致重建失败。
- **热重载隔离**：Chainlit 以 `-w` 启动时，项目目录内的运行期文件写入可能触发 `watchfiles` 重载；因此 `data/uploads/seed/` 与 `data/data/vector_kb/default/user/` 已迁移到项目根目录外的 `_runtime_data/`，避免构建 FAISS 时被热重载打断。

---

## 6 GraphRAG（知识图谱 + 向量库）

### 6.1 配置

- **文件**：`graphrag_project/settings.yaml`
- **模型**：LLM `llama3` + Embedding `nomic-embed-text:latest`，均通过 `http://localhost:11434/v1` 走 LiteLLM
- **向量库**：LanceDB（`output/lancedb`）
- **索引表**：Parquet 形式落地到 `output/`

### 6.2 工作流定义

`settings.yaml` 中定义了 GraphRAG indexing 工作流：
`extract_graph → create_communities → generate_text_embeddings → ...`

### 6.3 查询实验

- **脚本**：`graphrag_project/run_query_experiments.py`
- 生成 global / local 查询命令并汇总 `output/*.parquet` 统计索引规模。

### 6.4 Decision Graph 注册表（当前实现）

- **核心文件**：`marathon_qa_assistant/services/knowledge_graph.py`
- **目标**：在现有实体图谱之上补一层可执行的决策骨架，为后续 `decision executor` 提供稳定输入，而不是继续让 LLM 自由编造训练参数。
- **Template Registry**：内置了 `轻松跑 / 长距离 / 有氧阈 / 节奏跑 / 无氧阈 / 摄氧量 / 重复跑` 七类模板，模板节点持久化 `fields / workout_labels / constraint_ids`。
- **Constraint Registry**：内置了 `每周质量课上限 / 高质量课间隔 48h / 每周长距离上限 / 长距离时长上限 / 质量课后恢复优先` 等约束，约束节点持久化 `rule / description`。
- **图谱挂接方式**：初始化 `GraphEngine` 时会自动把 registry 节点和标准边写入图中，形成 `workout -> template -> constraint`，并补充 `workout -> zone / physiology / adaptation` 关系，边上统一带 `decision_graph_registry` evidence。
- **Decision Executor（最小版）**：已新增 `decide_workout_draft(workout_label, athlete_profile, context)`，可基于 registry 输出模板选择、参数草案、约束检查、阻塞告警与调整记录，适合作为后续计划生成器的规则内核。
- **图谱增量构建逻辑**：
  - **分片去重**：通过 `chunk_id` + `text_hash` 判断分片是否为新增或已修改。
  - **顺序批处理**：移除旧的“首中尾抽样 300”策略，改为顺序提取前 100 个新分片（`BATCH_SIZE=100`），确保知识覆盖的连续性。未处理的分片将在下一次构建时自动进入队列。
  - **元数据持久化**：`processed_chunks` 扩展为包含 `hash / processed_at / status / triples_count` 的字典结构，支持审计图谱构建的完整性与时效性。
  - **容错重试**：提取失败（超时或 LLM 报错）的分片不会被记录到 `processed_chunks`，确保其在下一轮增量构建中被重新处理。
- **当前边界**：执行器已接入 `expert_nodes.py` 的逐日生成主链，由 `plan_nodes.py -> _generate_plan_day_by_day()` 调用；现在每一天的主课参数都先由 `decide_workout_draft()` 决定，再做规则渲染与 blocked fallback。尚未实现多天联合优化和 graph-driven retrieval。
- **组间实现方法说明**：
  - `knowledge_graph.py` 负责模板注册、约束注册与 `decide_workout_draft()` 决策执行，不直接产出最终 Markdown。
  - `expert_nodes.py` 负责逐日上下文构建、blocked fallback、`render_day_from_draft()` 规则渲染，以及把 `draft.status / adjustments / warnings` 连同 `decision_trace` 一并落入最终输出。
  - `plan_nodes.py` 负责执行入口与总体验证；当逐日决策链失败或周结构校验不通过时，只回退到静态模板，不再回退到自由生成。
- **本轮验收结果**：
  - 已验证逐日成功路径不再调用 LLM 生成课表行，最终表格正文与 `draft.rendered` 保持一致。
  - 已验证输出保留 `draft.status / draft.adjustments / draft.warnings`，并同时携带 `constraints / template_id / zone_label / parameters / context / decision_trace`。
  - 已验证冒烟产物中不存在 `??,??`、占位词或“详情见引用/待补充”类漂移文本。
  - 已验证 `expert_nodes.py` 去除了旧的日级 LLM 渲染链路及其循环导入依赖，`py_compile` 与最小冒烟均通过。

---

## 7 评测与报告

| 文件 | 职责 |
|------|------|
| `tools/kb/evaluate_rag_ragas.py` | 当前 RAG 评测主脚本，输出 `rag_eval_report.md` 并区分精确块 / 同页 / 同文档命中口径 |
| `tools/kb/generate_eval_dataset.py` | 生成或整理评测样本，供 RAG 评测脚本使用 |
| `tools/kb/kb_gap_check.py` | 检查知识库覆盖缺口与问题-证据不匹配情况 |
| `tests/minimal_import_test.py` | 最小导入冒烟检查，确认核心工作流、节点、服务与 UI 组件可导入 |
| `archive/2026-04-30_history_batch/` | 历史评测原型归档区，旧版 `evaluate_workflow.py` 等文件保留备查，不作为当前评测入口 |

---

## 8 训练生理区间规则（当前实现）

- **心率区间（LTHR）**：采用九区模型 `Z1-Z9`  
  - `Z1 <72%`、`Z2 72-78%`、`Z3 79-84%`、`Z4 85-89%`、`Z5 90-93%`、`Z6 94-97%`、`Z7 98-100%`、`Z8 101-105%`、`Z9 >105%`
- **配速区间（T-Pace）**：已升级为九区模型 `Z1-Z9`
  - `Z1 115%-130%`、`Z2 108%-115%`、`Z3 102%-108%`、`Z4 98%-102%`、`Z5 95%-100%`、`Z6 92%-96%`、`Z7 90%-94%`、`Z8 85%-92%`、`Z9 75%-88%`
- **展示与生成对齐策略**：Chainlit 侧边栏 `update_sidebar()` 已改为通过共享的九区顺序渲染完整 `心率 Z1-Z9 + 配速 Z1-Z9` 表格；画像持久化与训练计划 Prompt 继续复用同一套九区口径，不再将 `Z6-Z9` 的配速列写死为 `—`
- **训练计划稳定性保障**：
  - **周结构约束**：强制执行“双质一长、高强度间隔、周末长距离”等规则，并引入 `repair_week_structure` 自动修复不合理骨架。
  - **参数唯一来源**：逐日生成中，`reps / distance / duration / rest / zone` 等主课参数统一来自 `decide_workout_draft()`；渲染层只负责把 draft 转成表格文本，不再允许 LLM 自由决定训练参数。
  - **上下文感知**：逐日生成会从“已生成天”累积 `week_history / quality_sessions_this_week / last_quality_hours_ago / previous_day_was_quality` 等上下文，再送入执行器做约束检查。
  - **输出拦截策略**：`formatter_node` 不再仅记录告警；若检测到占位词、空字段、列数异常或周结构冲突，会直接拦截坏课表并返回失败提示，避免错误课表进入 UI。
  - **执行回退可观测性**：逐日执行器若返回 `blocked` 或 `no_template`，会按 `轻松跑 -> 恢复跑 -> 休息` 顺序自动 fallback，并在输出 JSON 中保留 `draft.status / adjustments / warnings / decision_trace / context`；`executor_node` 失败时只回退到静态模板，不再绕回自由生成。
- **LLM 调用签名约束**：`common.py::ai_invoke(prompt, config, current_usage)` 当前只接受 3 个参数，节点侧不得继续透传 `num_predict` 等未声明关键字；否则会在 Python 层先抛 `TypeError`，并被上游宽泛 `except` 误吞。
- **异常日志规范**：`expert_nodes.py` 的通用问答与周计划骨架生成在调用 `ai_invoke()` 前后统一记录 debug 日志（至少包含 prompt 长度与是否进入调用）；若出现异常或空字符串返回，必须记录异常类型与 message，并显式写入 `used_fallback / fallback_reason` 供 `output_nodes.py` 后续排查。
  - **句内引用规则**：`expert_nodes.py` 的通用问答提示词与 `plan_nodes.py` 的 LLM 计划提示词统一要求：凡使用 RAG 证据中的事实句，必须在句末追加 `[1]`、`[2]` 或 `[1][2]`，且编号只能来自 `format_evidence_lines()` 输出的证据列表；无直接证据时允许给出建议，但不得伪造引用。
- **Graph Retrieval 增强引用链路（当前实现）**：
  - **统一 Evidence 结构**：定义了 `Evidence` 数据结构（含 `evidence_id / kind / chunk_id / snippet / hybrid_score / citation_label / trace`），融合向量检索与图谱关联。
  - **Hybrid Scoring 排序**：实现 `hybrid_score = 向量分(0.4) + 图置信度(0.3) + 实体重合度(0.2) + 融合奖励(0.1)`，确保最相关的证据排在最前。
  - **融合去重规则**：`profile_and_retrieval.py::build_ranked_evidence()` 先以 `chunk_id` 为主键去重，缺失 `chunk_id` 时退化为 `source_file + page`；若同一分片同时命中向量检索与图谱边，则合并为单条 `fusion` 证据，并在 `trace` 中记录 `graph_hit / graph_relation / fusion_bonus`。
  - **图谱证据映射**：`knowledge_graph.py::map_edge_to_evidence()` 会把图谱边统一映射为 `Evidence` 对象，补齐 `kind / source_file / chunk_id / graph_confidence / trace` 等字段，避免下游再区分 vector-only 与 graph-only 的输入格式。
  - **稳定 Citation 编号**：在 `retrieval` 聚合层即完成去重、排序与编号分配（`[1][2][3]`），编号一旦分配则贯穿 Prompt 注入、LLM 生成与输出校验；`common.py::format_evidence_lines()` 默认优先消费 `ranked_evidence`，仅保留 `rag_sources` 作为兼容兜底。
  - **输出合法性校验**：在 `formatter_node` 增加引用校验，检测 LLM 回复中的 `[n]` 是否存在于当前证据池中；若检测到无效引用，在计划模式下直接拦截输出，在 QA 模式下自动移除越界编号并记录降级日志，避免伪造引用继续外显。
  - **可观测性日志**：`build_ranked_evidence()` 会输出排序前来源分布（vector / graph / fusion / merged）以及 Top-N 证据的 `kind / hybrid_score / trace`，便于定位证据融合、降权或错误引用问题。
- **组间实现方法说明（引用链路）**：
  - `knowledge_graph.py` 提供 `map_edge_to_evidence()`，将图谱边证据映射为统一格式。
  - `profile_and_retrieval.py` 实现 `build_ranked_evidence()`，负责聚合、去重、融合、打分、日志追踪与固定编号。
  - `common.py` 更新 `format_evidence_lines()`，优先消费 `ranked_evidence` 并输出带稳定编号的文本块。
  - `expert_nodes.py` / `plan_nodes.py` 仅消费 `ranked_evidence` 的 top_k 结果构造 Prompt，不再直接拼接 `graph_context` 或旧版 `rag_sources` 内容。
  - `output_nodes.py` 负责 `evidence_base` 的对齐渲染、引用合法性校验，以及 QA 模式下的越界引用降级清洗。

---

## 9 模块依赖关系（简化）

```
app_chainlit.py / run.bat（主入口）
├── marathon_qa_assistant/apps/chainlit_app.py（Chainlit UI）
│   ├── marathon_qa_assistant/core/workflow.py（工作流装配）
│   │   └── marathon_qa_assistant/core/workflow_graph.py（图构建 / fallback）
│   ├── marathon_qa_assistant/services/vector_store.py（检索与索引）
│   └── ChatOllama（LLM）
│
apps/backend/src/marathon_qa_assistant/apps/api_app.py（FastAPI 入口）
├── marathon_qa_assistant/core/workflow.py
└── uvicorn

tools/kb/evaluate_rag_ragas.py / generate_eval_dataset.py / kb_gap_check.py
└── marathon_qa_assistant/services/vector_store.py
```

---

## 10 审计评分与前端展示（当前实现）

- **动态评分入口**：`marathon_qa_assistant/nodes/expert_nodes.py::auditor_node`
- **前端统一渲染入口**：`marathon_qa_assistant/ui/legacy_ui.py::UIHelper.render_structured_report`
- **结果装配入口**：`marathon_qa_assistant/nodes/output_nodes.py::_build_structured_report`

### 10.1 一致性 / 安全性 / ROI 计算规则

- **一致性评分**：
  - 基础分由 `is_approved` 决定：通过终审取高分，未通过显著降分。
  - 再叠加 `iteration_count` 惩罚，表示本轮输出经历的回退/修正次数越多，一致性越低。
- **安全性评分**：
  - 以 `therapist_node` 的审查结果为核心依据。
  - 若 `review_feedback` 出现“风险 / 拦截”等关键词，进一步扣分。
  - 对训练计划模式额外检查“是否存在证据缺口”，防止无证据课表直接高分放行。
- **知识回报率（ROI）**：
  - 不再写死为 `80%`。
  - 由 `ranked_evidence[:5]` 的 `hybrid_score` 累积值和 `entities` 覆盖数共同决定。
  - 因此当检索证据更强、实体覆盖更全时，ROI 会自然提升；若证据弱或几乎没有命中，ROI 会下降。

### 10.2 前端展示策略

- **展示位置**：最终结构化报告顶部增加“质量与安全审计”区块，先展示三项分数，再展示“评分依据”与“关联证据”。
- **当前入口**：审计区块当前由 Chainlit 链路消费；`UIHelper.render_structured_report()` 仍保留为共享 Markdown 渲染器，但项目已不再维护 Gradio 作为现行主入口。
- **Wiki 补充展示**：当 `structured_report.analysis_framework.wiki_context` 非空时，Chainlit 会在主报告下方额外发送一个 `Wiki补充` 区块，显式展示外部概念背景，并提示该内容不作为训练处方依据。
- **来源说明**：
  - 一致性：展示“审核状态 + 迭代次数”。
  - 安全性：展示“治疗师审查反馈 + 计划模式证据校验结果”。
  - ROI：展示“证据命中数 + Top5 平均 hybrid_score + 实体覆盖数”。
  - 若存在稳定引用编号（如 `[1]`、`[2]`），额外展示对应来源文件与片段摘要，方便用户理解分数来源。

### 10.3 组间实现方法说明

- `expert_nodes.py` 负责计算动态分数与评分依据，不关心 UI 样式。
- `output_nodes.py` 负责把 `audit_scores`、`score_sources` 和 `evidence_base` 组装进 `structured_report.audit_block`，并把 `structured_training_plan.week_plans[]` 规范化为可渲染的周级块。
- `legacy_ui.py` 负责将审计元数据、`Wiki补充` 和结构化多周计划渲染成 Markdown 面板；当存在 `structured_training_plan` 时优先消费结构真源，`raw_report` 仅作为兜底。
- `services/analytics.py` 负责 Week 7 事件契约、匿名用户标识、会话标识复用、JSONL 落盘和 `plan_generate_clicked` 口径收口，并在 `build_plan_click_properties` 中区分 `source_type: message|action`；`apps/chainlit_app.py` 接入 `app_opened`（附加 `entry/initial_mode/profile_field_count`）；`apps/chainlit/logic.py` 接入 `plan_generate_clicked / plan_generated`（附加 `final_report_length/plan_type/actual_weeks/rag_source_count`）/ `adaptive_plan_generated`（附加 `recommendation_count/has_training_feedback`）；`apps/chainlit/actions.py` 接入 `profile_wizard_started`（附加 `has_existing_profile/pre_filled_field_count`）/ `profile_submitted`（附加 `total_fields_available`）/ `weekly_review_viewed`（附加 `workout_count`）/ `evidence_opened`（附加 `source_type/snippet_length`），并把 `profile_submit / regen_plan_from_profile / retry_plan_generation / cancel_fill` 等显式按钮动作透传为点击来源，同时继续与 `logic.py` 一起覆盖文本反馈与快捷反馈两条 `workout_feedback_submitted` 路径，区分 `source_type: text|action`。

## 11 赛事倒计时与日期容错（当前实现）

- **入口**：`marathon_qa_assistant/apps/chainlit_app.py::update_sidebar`
- **问题背景**：用户画像中的 `target_race_date` 可能来自手填、表单回写或旧数据文件，格式并不总是统一，曾导致侧边栏显示“格式错误”。
- **当前策略**：
  
## 12 训练画像向导交互稳定性（当前实现）

- **入口**：`marathon_qa_assistant/apps/chainlit_app.py` 作为壳入口，实际向导实现在 `marathon_qa_assistant/apps/chainlit/actions.py` 与 `marathon_qa_assistant/apps/chainlit/wizard_logic.py`
- **问题背景**：训练画像中的 `available_days / terrain_preference / training_types` 属于多选题。旧版本在 Chainlit 消息更新失败后可能残留历史按钮；若用户继续点击旧按钮，会把过期步骤的回调再次写入当前会话态，表现为勾选状态来回跳变、确认项数忽多忽少。
- **当前策略**：
  - **步骤令牌防串写**：每次渲染画像步骤时，都会为当前步骤生成新的 `step_token`，并写入每个 Action 的 payload；回调执行前必须同时匹配 `field + step_token`，旧按钮即使仍显示在界面上，也不会再改写当前状态。
  - **多选值规范化**：进入向导和确认提交前，统一清洗多选字段，兼容英文逗号、中文逗号、顿号、空格等分隔符；`available_days` 还会额外按 `周一..周日` 规则抽取，避免历史脏值污染“已选”显示。
  - **固定顺序输出**：多选结果在 UI 展示和最终保存前都会按预设选项顺序排序，避免同一组选择因点击顺序不同而出现回显抖动。
  - **缺失信息显式状态**：计划模式下若仍缺训练画像，`missing_info_handler_node` 不再把 `final_report="__FILL_FIELDS__"` 作为主协议，而是显式写入 `IntegratedState.missing_info_status="awaiting_profile"`；`logic.py` 依据该状态弹出逐字段补填入口，`guided_questions_node` 也按该状态跳过追问，避免 UI 依赖隐式哨兵文本。
  - **跨消息状态清理**：`logic.py` 在每次新请求进入工作流前都会主动清空 `missing_info_status`，防止上一轮"待补画像"状态污染下一条消息。
  - **画像字段分层（极速画像 M1）**：`profile_and_retrieval.py` 将训练画像字段分为两层——`MINIMUM_REQUIRED_FIELDS = ["goal", "weekly_mileage", "available_days"]` 为最小必要字段（硬阻塞，缺一不可生成计划）；`ENHANCEMENT_FIELDS`（vo2max、lthr、t_pace、experience_level、target_race_date、max_session_minutes、pace_preference、terrain_preference、training_types）为增强精度字段（缺失不阻塞生成，由 `_detect_missing_enhancement_fields()` 独立检测）。
  - **增强字段补全提示**：`plan_nodes.py::_build_plan_prompt()` 在 LLM 提示中注入缺失增强字段清单，让 LLM 知晓当前使用默认估算值；`logic.py` 在计划生成后弹出逐字段补全入口（最多展示 5 个），引导用户后续补充精度。
  - **基础画像与高级画像分流**：`logic.py` 现按 `filling_field_mode` 区分“最小必要字段补填”和“增强字段补填”。基础画像补齐后会自动继续生成基础计划；高级画像补齐后只提示“可重生成更精准计划”，不再打断当前计划浏览。
  - **高级画像完整入口**：`actions.py` 新增 `fill_advanced_profile` 与 `regen_plan_from_profile`。前者从缺失的高级字段开始进入完整画像向导，后者允许用户在补充后手动触发基于最新画像的计划重生成。
  - **Coach 状态契约真源**：新增 `apps/chainlit/coach_state.py`，集中定义 Coach Mode 的 session 默认值、页面状态、消息状态、状态文案与下一步提示；`chainlit_app.py / logic.py / actions.py / setup.py` 统一复用该模块，不再各自维护零散状态判断。
  - **状态可视化收口**：`setup.py::update_sidebar()` 会同步渲染 `Coach 状态` 区块，显示当前页面状态、消息状态、下一步提示、待补字段计数与挂起交互类型，便于前端调试和主链路验收。
  - **演示向交互文案**：`setup.py::show_profile_summary()` 在欢迎区展示可选入口和下一步建议；`actions.py::on_fill_field()` 明确基础画像/高级画像的输入方式；`logic.py` 在缺字段、补字段、基础计划完成后补高级画像等阶段明确提示用户下一步点击位置。
  - **首周执行入口与失败兜底（M1-TASK-11）**：`logic.py` 在计划成功后发送“开始第1周训练”动作，并在计划异常或未拿到可展示结果时发送“重试计划生成 / 检查训练画像”动作；`actions.py` 新增 `start_first_week / retry_plan_generation` 回调，统一复用 `plan_ui.py` 的上下文提取和文案模板。
  - **训练反馈快速提交（Week 4-B）**：`actions.py` 现在通过 `submit_training_feedback` 把用户引导到模板化反馈输入；`logic.py` 在 `pending_operation=training_feedback` 时解析 `完成状态 / 完成质量 / 疲劳 / 不适 / 睡眠 / 备注`，并同步写回 `latest_training_feedback_card`、`adaptive_feedback` 与 `adaptive_adjustment`，使真实反馈可直接进入后续 Week 5 自适应链路。
- **组间实现方法说明**：
  - `chainlit_app.py` 仅负责 Chainlit 启动挂载、会话初始化与模块接线，不再承载具体画像交互细节。
  - `actions.py` 负责画像向导动作回调、步骤推进、返回上一步与最终回写；同时区分 `full` 与 `enhancement` 两类向导模式，避免高级画像补全时误触发默认“第一周计划”重生成。
  - `coach_state.py` 负责将 `user_session` 与 LangGraph 返回状态折叠为可追踪的 Coach UI 快照，并把状态枚举与下一步提示作为前端唯一契约导出。
  - `setup.py / actions.py / logic.py` 分别承接欢迎区、字段输入和工作流阶段消息展示，所有展示文案都围绕状态契约说明“当前在干什么、下一步点哪里”。
  - `plan_ui.py` 负责把 `structured_report.training_plan_overview / training_plan_weeks[]` 提炼为首周执行上下文，并统一生成“首周执行入口 / 快速训练反馈模板 / 训练反馈卡 / 计划失败重试”文案以及反馈状态 bundle；`logic.py` 决定何时展示动作按钮并在收到反馈文本后写回统一状态，`actions.py` 负责点击后的会话内交互。
  - Week 6 新增 `structured_report.training_explanation_panel` 作为解释层唯一消费入口：`output_nodes.py` 负责按周装配关键训练的 `为什么安排 / 主要训练目标 / 风险提醒 / 替代方案 / 决策摘要`，优先消费 day draft 中已有的 `template_id / constraints / warnings / decision_trace`，字段不足时退化为基于 `week_goal / phase / training_type / execution_reminder` 的稳定解释。
  - Week 6 后端增强版进一步把解释 DTO 从“可展示文本”收口为“可复用结构契约”：面板级新增 `panel_version / coverage_status`，周级新增 `week_goal / execution_reminder / item_count`，解释项新增 `item_id / explanation_source / target_labels / warnings / adjustments / constraints / decision_trace`，便于前端面板、埋点与后续 API 共用同一真源。
  - `legacy_ui.py` 负责在共享报告里渲染周级 `关键训练解释面板`，并把解释区块中的引用一并纳入证据预览提取；`plan_ui.py` 同步提供 Week 6 专用 `training_explanation_card`，两者现在都把 `warnings / adjustments / constraints / decision_trace / target_labels / evidence_ids` 放进 `<details>` 展开块，并把 `evidence_ids` 渲染为高亮编号与“同编号按钮可预览原文”提示；同时保证 `evidence_ids` 即使只存在于结构化字段中，也会被提取进 `参考来源 / 查看证据（同号按钮）` 预览链。多周场景下，Chainlit 卡片会显式说明当前展示周次与完整覆盖周次；若解释项为空、未提取到证据编号或原文路径缺失，则改为显式空态/异常态提示而非静默丢失。
  - `apps/api_app.py` 的 `QueryResponse` 额外暴露顶层 `training_explanation_panel`，其内容直接映射自 `structured_report.training_explanation_panel`，方便前端少解析一层结构即可消费 Week 6 解释结果。
  - `wizard_logic.py` 负责步骤令牌校验、多选值清洗、旧按钮失效与单消息原地更新。
  - `profile_and_retrieval.py` 继续负责训练画像字段定义、落盘映射与 `missing_info_status` 写入，不承担前端多选状态控制。
  - `output_nodes.py` 负责消费 `missing_info_status`，在“待补画像”场景下跳过引导追问，保证计划链路的后置节点契约稳定。
  - 依次尝试 `YYYY-MM-DD`、`YYYY/MM/DD`、`YYYY年MM月DD日`、`DD/MM/YYYY`。
  - 成功解析后输出“X 天 / 就在今天 / 已赛完（X 天前）”。
  - 若值为 `无比赛`、`待定`、`赛期未定` 这类非日期描述，侧边栏直接显示原文本，不再误报格式错误。
  - 其他无法解析的字符串也保留原值展示，避免因为历史画像或自由输入导致侧边栏提示失真。
- **实现边界**：当前倒计时容错已覆盖常见日期格式，并兼容非日期型赛事描述；但仍以“单个字符串字段”作为输入，不做自然语言日期推理。

---

*文档版本：2026-04-28（随代码变更同步更新）*
