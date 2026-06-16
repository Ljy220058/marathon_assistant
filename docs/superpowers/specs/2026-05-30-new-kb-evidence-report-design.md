---
name: 2026-05-30-new-kb-evidence-report-design
description: 新知识库 v2 独占检索、旧库归档、可见证据闭环与报告强制包含证据的设计说明
metadata:
  type: project
---

# 新知识库 v2 可见证据闭环设计

## 1. 背景

当前“查知识库 / 查训练依据”链路存在三个问题：

1. 运行时可能静默回退到 legacy 知识库。
2. 命中的 evidence 里混入旧库解释性来源、图谱线索和模型常识，前端标题和正文容易把它们包装成强依据。
3. AI 报告正文没有强制包含“知识库可见证据”板块，导致用户看到的正文与证据抽屉脱节。

本设计的目标是把知识库问答改成“新知识库 v2 独占检索 + 证据可见 + 报告强制引用”的闭环。

## 2. 目标

### 2.1 运行时只使用新知识库 v2

- 默认知识库路径必须指向 `data/vector_kb/v2`。
- 默认索引 schema 必须是 `chunk_schema_v2`。
- legacy 知识库不再作为 fallback。
- 若 v2 不可用，health 必须显式 degraded，不允许静默回退。

### 2.2 旧库退出运行链路

- 旧库从运行路径移出并归档到 `archive/legacy_vector_kb_YYYYMMDD/`。
- 运行时不得扫描 `archive/`。
- 代码中不得再把 legacy 路径作为默认来源。

### 2.3 可见证据闭环

- 检索到的合格 chunk 应进入可见 evidence 流程，不因 UI 人为截断而丢失。
- 每条 evidence 必须带上可解释的定位与来源信息，例如：
  - `chunk_id`
  - `source_label`
  - `text_span`
  - `locator_hint`
  - `display_mode`
  - `retrieval_mode`
  - `score_breakdown` / `why_retrieved`

### 2.4 报告必须包含知识库可见证据

- 对知识库问答类请求，LLM 报告正文必须包含固定章节：
  - `结论`
  - `训练建议`
  - `专项不受影响的边界`
  - `知识库可见证据`
  - `证据不足或待核验之处`
- “知识库可见证据”必须逐条覆盖传入 LLM 的 visible evidence。
- 报告不得只给结论而不展示证据。

## 3. 非目标

- 不重建整个知识库内容。
- 不引入新的外部检索源。
- 不重写整个 LangGraph 工作流。
- 不删除 legacy 文件本体到不可恢复程度；本次采用归档而非物理销毁。

## 4. 方案概述

### 4.1 KB runtime / provider

后端启动时只选择 v2 运行时：

- `vector_dir = data/vector_kb/v2`
- `index_schema_version = chunk_schema_v2`
- `runtime_core_prescription_enabled = True` 只在 v2 就绪时成立

若 v2 缺失、损坏或 schema 不匹配：

- health 返回 degraded
- `rag_health.ready = False`
- `degraded_reason` 必须明确说明原因
- 不允许 fallback 到 legacy

### 4.2 Retrieval ranking

`build_ranked_evidence()` 保留相关性排序，但不再把 legacy / 图谱线索当作默认强依据。

- v2 chunk 进入 visible evidence。
- graph-only 证据只能作为解释线索，不能伪装为可定位强证据。
- 非 v2 或无有效定位的来源应被标记为 rejected / needs_evidence，而不是混入核心训练处方依据。

### 4.3 Evidence gating

证据分层不用于“隐藏”，而用于“标注能做什么”：

- `verified_source`：可作为核心建议依据。
- `legacy_explanation`：归档期保留，但不可进入运行时核心建议链路。
- `graph_hint`：只能做背景线索。
- `model_general_knowledge`：只能做背景说明，不可当作知识库依据。
- `needs_evidence` / `rejected_source`：必须显式标注。

### 4.4 LLM 报告模板

Prompt 强制要求回答包含证据段落，并把可见 evidence 变成正文的一部分。报告格式固定为：

```markdown
## 结论

## 训练建议

## 专项不受影响的边界

## 知识库可见证据

## 证据不足或待核验之处
```

## 5. 用户可见效果

用户问：

```text
中长跑选手怎么把短跑技术融入进去，不影响专项？
```

系统会表现为：

- 只检索新知识库 v2。
- 页面展示所有合格命中的可见证据，不再用“基于 N 组依据生成”这种模糊标题。
- AI 报告正文里会直接列出知识库可见证据。
- 如果某些建议没有证据支撑，会明确写进“证据不足或待核验之处”。
- 不再把旧库解释、图谱线索、模型常识伪装成强依据。

## 6. 验收标准

1. `/health` 或 `rag_health` 明确显示 v2 正在运行，且不会静默回退 legacy。
2. legacy 知识库已从运行路径移出并归档。
3. 知识库问答报告正文包含“知识库可见证据”章节。
4. 前端不再显示“基于 11 组依据生成”这类混淆不同证据层级的标题。
5. 命中的可见证据能进入 LLM 报告，不因前端截断或隐藏而消失。

## 7. 风险与约束

- 如果 v2 覆盖不足，部分问题会从“强答案”退化为“证据不足”。这是预期行为，不是失败。
- 归档 legacy 后，如果后续需要对比或回溯，必须从 archive 路径显式读取，不能自动参与运行。
- 如果 prompt 没有强制报告格式，LLM 仍可能只给结论不列证据，所以模板约束必须在后端强制执行。

## 8. 后续实现顺序

1. 调整 KB runtime/provider，只允许 v2。
2. 归档 legacy 知识库并移出运行路径。
3. 重构 evidence chain / retrieval policy，让可见证据进入 LLM。
4. 修改报告模板，强制包含“知识库可见证据”。
5. 更新前端标题和证据展示逻辑。
6. 补齐后端与前端契约测试。
