# KG Label Semantic Matching Design

> **Goal:** 将用户自然语言查询对齐到知识图谱标准节点标签（workout_template + category），通过 L1 别名表 + L2 embedding 语义兜底，解决"高强度间歇"→"HIIT" 等模糊匹配问题。

**Architecture:** 新增 `LabelMatcher` 服务（`services/label_matcher.py`），启动时预热 74 个 KG 标签向量；查询时走 L1 别名精确匹配 → L2 bge-m3 cosine 语义匹配 → 合并去重。调用方在 `entity_extraction_node` 中组合结果。同时将 embedding 模型从 `nomic-embed-text` 切换为 `bge-m3`（中英双语），重建全部向量库。

**Tech Stack:** bge-m3 (OllamaEmbeddings), numpy, Python 3.11+

---

## 1. 组件与接口

### 1.1 ALIAS_TABLE（common.py 常量）

```python
ALIAS_TABLE: dict[str, str] = {}
```

静态同义词映射，覆盖 ~33 条高频改写：

| 优先级 | 来源 | 示例 | 数量 |
|--------|------|------|------|
| P0 | 中英对译 | "高强度间歇"→"HIIT"、"阈值"→"Lactate-Threshold" | ~15 |
| P1 | 口语→规范 | "慢跑"→"轻松跑"、"冲刺"→"重复跑" | ~10 |
| P2 | 简称→全称 | "马克操"→"马克操（跑姿步伐操）"、"核心"→"核心力量" | ~8 |

### 1.2 LabelMatcher（services/label_matcher.py）

```python
class LabelMatcher:
    def __init__(self, embedding_model: str = "bge-m3"):
        self._embeddings = OllamaEmbeddings(model=embedding_model, base_url=OLLAMA_BASE_URL)
        self._label_vectors: dict[str, np.ndarray] = {}
        self._labels: list[str] = []
        self._threshold: float = 0.6

    def warm_up(self, labels: list[str], threshold: float = 0.6) -> None:
        """启动时调用。batch embed 所有 KG 标签，缓存向量。labels 为空不报错。"""

    def match(self, query: str, top_k: int = 3) -> list[tuple[str, float]]:
        """L2 语义匹配。返回 [(label, cosine_score), ...]，过滤低于 threshold 的结果。"""
```

### 1.3 semantic_match_entities（common.py 整合入口）

```python
def semantic_match_entities(query: str) -> list[str]:
    """L1 别名精确匹配 + L2 embedding 语义兜底 → 返回 KG 标准标签列表"""
```

**调用方**（`entity_extraction_node` in `profile_and_retrieval.py`）：

```python
entities = infer_entities(query, ...)
semantic_entities = semantic_match_entities(query)
entities = list(dict.fromkeys(entities + semantic_entities))  # 合并去重保序
kg_entities = expand_entities_for_kg(entities)
```

### 1.4 展开触发器可配置

```python
_EXPAND_TRIGGERS = {"动作库", "训练动作", "训练库", "exercise"}
```

`expand_entities_for_kg` 检查 `any(t in e for t in _EXPAND_TRIGGERS for e in entities)`。

---

## 2. 数据流

```
query = "高强度间歇训练怎么做"

1. infer_entities(query)
   → 硬编码正则: ["高强度间歇", "间歇"]
   → KG 子串匹配: []  (query 不含 "HIIT" 子串)

2. semantic_match_entities(query)
   → L1 别名表: "高强度间歇" → "HIIT"
   → L2 embedding: embed(query) · label_vectors → [("HIIT", 0.82), ("Tabata", 0.61)]
   → 合并: ["HIIT", "Tabata"]

3. 合并: entities = ["高强度间歇", "间歇", "HIIT", "Tabata"]

4. expand_entities_for_kg(entities) → 无"动作库"触发词，不展开

5. search_graph(entities) → "HIIT" 命中 category 节点 → 2-hop → 关联 workout_template
```

---

## 3. 错误处理与降级

| 场景 | 行为 |
|------|------|
| Ollama 未启动 / bge-m3 未拉取 | `warm_up()` 抛 RuntimeError，启动直接失败 (fail-fast) |
| 查询时 embedding 调用失败 | `match()` 返回 `[]`，仅用 L1 结果，日志 warn |
| KG 标签列表为空 | `warm_up()` 正常返回（空列表），`match()` 返回 `[]` |
| 环境未配置 Ollama | `LabelMatcher` 初始化不抛异常，`warm_up()` 时才检查 |

---

## 4. 配置

| 配置项 | 环境变量 | 默认值 |
|--------|---------|--------|
| L2 阈值 | `LABEL_MATCH_THRESHOLD` | `0.6` |
| L2 top_k | `LABEL_MATCH_TOPK` | `3` |
| Embedding 模型 | `EMBEDDING_MODEL` | `bge-m3` |
| Ollama URL | `OLLAMA_BASE_URL` | `http://localhost:11434` |

---

## 5. 重建影响

| 影响项 | 说明 |
|--------|------|
| `vector_store.py.EMBEDDING_MODEL` | `"nomic-embed-text"` → `"bge-m3"` |
| `vector_kb/default/` | 全量重建 FAISS 索引 |
| `vector_kb/user/` | 全量重建 FAISS 索引 |
| `vector_kb/knowledge_graph.json` | 不受影响（仅改标签匹配，不改 KG 结构） |
| 现有 chunks.jsonl | 文本内容不变，仅重新 embedding |

---

## 6. 测试

| # | 测试 | 类别 |
|---|------|------|
| 1 | "慢跑" → L1 → "轻松跑" | L1 精确匹配 |
| 2 | "想暴汗" → L2 → "HIIT" (>0.6) | L2 语义兜底 |
| 3 | "今天天气不错" → L2 <0.6 → `[]` | 低置信度过滤 |
| 4 | 两次 `match()` 调用 → 仅一次 Ollama embed API | 向量缓存 |
| 5 | `entity_extraction_node` 端到端合并 | 集成 |
| 6 | Ollama 不可用 → `warm_up()` 抛 RuntimeError | 启动失败 |
| 7 | 查询时 embed 报错 → fallback L1 only | 降级 |
