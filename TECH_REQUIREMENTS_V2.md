# 马拉松多智能体系统技术需求文档 (v2.0)

## 1. 多天联合决策调度器 (Multi-day Joint Decision Scheduler)

### 1.1 背景与动机
原有的计划生成逻辑采用“逐天独立决策”，模型在生成周二计划时无法感知周一的强度，导致经常出现连续高强度课（如连续两天间歇跑）或周质量课超标的情况。

### 1.2 实现方法
引入了 `plan_week_drafts` 全局调度器，采用“带状态推进”的算法：

- **状态对象 (WeekState)**: 追踪 `quality_count` (质量课计数), `last_quality_day` (上一个质量课索引), `long_run_done` (长距离是否完成)。
- **约束传播 (Constraint Propagation)**:
    - **48h 间隔**: 任何强度在 Z4 (Tempo) 及以上的课程，必须与上一个高质量课间隔至少 48 小时。
    - **周上限**: 每周高质量课 (Quality Sessions) 不超过 2 次，长距离 (Long Run) 不超过 1 次。
- **自动降级机制 (Auto-downgrade)**: 当某天预定的训练类型触发约束（Blocked）时，调度器会自动尝试从 `["轻松跑", "恢复跑", "休息"]` 中寻找替代方案，并记录 `adjustments`。

### 1.3 核心组件
- **服务层**: `marathon_qa_assistant/services/knowledge_graph.py` 中的 `plan_week_drafts`。
- **节点层**: `marathon_qa_assistant/nodes/expert_nodes.py` 已重构，不再调用 LLM 循环生成每一天，而是通过调度器一次性获取所有草案。

---

## 2. 多模态处理实时反馈机制 (Real-time Multimodal Feedback)

### 2.1 背景
多模态模型（如 Llama 3.2-Vision）加载与推理耗时较长（30s - 2min），用户在等待期间无法感知后端进度，且日志仅存在于终端，不利于生产环境调试。

### 2.2 实现方法
实现了基于回调的异步通知机制：

- **Provider 修改**: `multimodal.py` 中的 `call_vlm` 及其相关方法新增 `log_callback` 参数。
- **UI 挂载**: 在 `chainlit_app.py` 中，图片处理任务会创建一个临时的 `cl.Message`，并将其更新方法作为 `vlm_log_callback` 注入。
- **心跳式进度反馈**: 当图片已编码并进入 `Ollama` 推理等待后，前端每 3 秒刷新一次状态消息，持续显示“当前阶段 + 已等待秒数 + 最近一条后端状态”，避免用户误判为页面卡死。
- **反馈链路**:
    1. 开始调用 VLM (显示模型名与路径)
    2. 图片读取与 Base64 编码
    3. 请求发送至 Ollama API
    4. 长耗时阶段显示“已等待 N 秒”
    5. 显存不足自动切换模型 (如 11b -> 7b)
    6. 解析成功并回显总耗时

### 2.3 收益
用户可以在 UI 界面看到“图片编码完成”、“正在发送请求”、“已等待 27s”等具体步骤，能够区分“正在慢速推理”与“程序已卡死”，显著提升交互确定性与可诊断性。

---

## 4. 结构化报告渲染与 PDF 预览交互 (Structured Report & PDF Interaction)

### 4.1 背景
重构后的系统采用多智能体协作，最终输出为结构化 JSON。在 UI 展示时，需要将报告中的学术引用（如 `[1]`）与知识库原文关联，并支持在侧边栏即时预览 PDF，以实现“所见即所得”的证据溯源。

### 4.2 实现方法
- **引用展示与动作解耦**: 在 `legacy_ui.py` 中，正文与“参考来源”区块中的 `[n]` 仅作为展示标记，不再生成 `action:` Markdown 链接，避免被前端渲染为普通 `<a target="_blank">` 超链接。
- **统一预览入口**: PDF 预览统一通过 `build_evidence_preview_bundle()` 生成的 `view_pdf` 显式 Action 按钮触发，点击后始终在当前界面的侧边栏打开原文。
- **防御性路径补全 (Defensive Path Fallback)**: 在 `view_pdf` 动作回调（`chainlit_app.py` 及 `actions.py`）中增加兜底逻辑：若 `payload.path` 缺失、失效或仅为纯文件名，系统将自动调用 `infer_source_path()` 在 `uploaded_docs`、`domain_docs` 等预设目录中搜索匹配的绝对路径，确保预览的高可用性。
- **Chainlit Action 注册**: 在 `chainlit_app.py` 的消息发送链路中，必须通过 `msg.actions` 或独立消息 `actions` 显式注册预览 Action，禁止依赖正文中的超链接承担预览职责。
- **证据源路径持久化**: 在 `vector_store.py` 的分片采集、`chunks.jsonl` 持久化和 FAISS `Document.metadata` 中同时保存 `source_file` 与 `source_path`；其中 `source_file` 仅用于界面展示，`source_path` 必须保持绝对路径，供 `rag_sources -> structured_report.evidence_base -> view_pdf` 预览链路直接使用。
- **正文主展示字段不可裁剪**: `structured_report.summary` 当前承担 Chainlit/Gradio 共享渲染器中的正文主展示职责，因此格式化阶段必须保留完整 `final_report`，不得再用固定字符数截断，否则研究类长回答会在“核心摘要”区被提前截断。
- **Markdown 表格容错**: 为确保在深色模式下的渲染稳定性，对所有表格增加了强制空行隔离（Padding），并将单元格内的非法字符（如 `|`）转义为 `&#124;`。

### 4.3 交互链路
1. LLM 生成带 `[n]` 的 Markdown 正文。
2. 检索层返回证据时保留 `source_file + source_path` 双字段。
3. `UIHelper` 保留正文中的 `[n]` 引用展示，并生成同编号的 PDF 预览按钮。
4. 用户点击消息下方的 `view_pdf` 按钮，触发侧边栏预览。
5. 后端接收 `payload`（含绝对路径与页码），调用 `cl.Pdf` 在侧边栏渲染对应文档。

---

## 5. 训练画像九区模型全链路适配 (Full-stack Adaptation of 9-Zone Model)

### 5.1 背景
根据最新的运动生理学需求，系统需从传统的 5 区强度模型全面升级为 **LTHR (乳酸阈心率) 9 区** 与 **T-Pace (阈值配速) 9 区** 模型。原有的画像填写向导、缺失检查逻辑及计划生成 Prompt 仍停留在旧模型阶段，导致用户无法录入核心生理指标，且生成的计划配速不准。

### 5.2 实现方法
实现了从“数据录入 -> 逻辑校验 -> 自动化计算 -> 计划生成”的全链路闭环：

- **向导字段补全**: 在 `profile_and_retrieval.py` 中将 `lthr` 与 `t_pace` 插入 `PROFILE_FIELD_ORDER`。更新 `PROFILE_OPTIONS` 增加专业级备选项，并支持“自定义输入”以满足精英跑者需求。
- **缺失逻辑加固**: 修改 `_detect_missing_fields()`，将 `lthr` 提升为计划生成前的“必须指标”，若缺失则强制引导用户通过向导补全。
- **生理学计算引擎升级**: 在 `physiology.py` 中将 `is_zone_empty()` 的默认预期区间数由 5 提升至 9，确保 `profile_store.py` 在加载/保存时能准确识别并自动同步最新的 9 区数据。
- **UI 标签专业化**: 更新 `ui_config.py` 中的 `ZONE_LABELS`，采用“Z4 阈值下限”、“Z6 无氧阈”等专业生理学名词，提升报告的科学性。
- **计划生成深度适配**: 重构 `plan_nodes.py` 中的 `_compute_pace_zones()`，废弃旧的 7 类型偏移算法，优先读取画像中持久化的 9 区配速表；若数据缺失，则调用生理学引擎进行 9 区反推，确保生成的周计划配速与侧边栏显示的区间完全一致。

### 5.3 收益
- **高精度处方**: 训练计划中的“间歇跑”、“节奏跑”等配速现在精确对应用户的 LTHR 九区，不再依赖模糊的经验值。
- **一致性体验**: 用户填写的 LTHR 实时转化为 9 区表展示在侧边栏，并同步驱动后台 LLM 的 Prompt 构建，实现了“所填即所得”。
- **系统稳健性**: 彻底解决了“填了画像但生成的计划还是旧配速”以及“缺失核心指标仍盲目生成计划”的问题。

## 6. 待优化与未来方向
