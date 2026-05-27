# KG Label Semantic Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将用户自然语言查询语义对齐到知识图谱标准节点标签，通过 L1 别名表 + L2 bge-m3 embedding 语义兜底。

**Architecture:** 新增 `LabelMatcher` 服务（启动时预热 74 个 KG 标签向量），查询时 L1 精确匹配 → L2 cosine 语义匹配 → 合并去重注入 `entity_extraction_node`。同时切换 embedding 模型 `nomic-embed-text` → `bge-m3`。

**Tech Stack:** bge-m3 (OllamaEmbeddings), numpy, Python 3.11+

---

## File Map

| 文件 | 操作 | 职责 |
|------|------|------|
| `apps/backend/src/marathon_qa_assistant/services/label_matcher.py` | 创建 | `LabelMatcher` 类：向量缓存 + cosine 匹配 |
| `apps/backend/src/marathon_qa_assistant/nodes/common.py` | 修改 | `ALIAS_TABLE` 常量、`_EXPAND_TRIGGERS`、`semantic_match_entities()` |
| `apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py` | 修改 | `entity_extraction_node` 调用 `semantic_match_entities` |
| `apps/backend/src/marathon_qa_assistant/core/kb_bootstrap.py` | 修改 | 启动时调用 `label_matcher.warm_up()` |
| `apps/backend/src/marathon_qa_assistant/services/vector_store.py` | 修改 | `EMBEDDING_MODEL = "bge-m3"` |
| `tests/test_label_matcher.py` | 创建 | 7 个测试 |

---

### Task 1: LabelMatcher 服务

**Files:**
- Create: `apps/backend/src/marathon_qa_assistant/services/label_matcher.py`
- Create: `tests/test_label_matcher.py`

- [ ] **Step 1: 写 L1 别名表测试**

```python
"""test_label_matcher.py — L1 alias + L2 embedding semantic matching"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _make_mock_embeddings(labels_to_vectors: dict[str, list[float]]):
    """构造 mock embedding 实例，返回预定义向量"""
    mock = MagicMock()
    mock.model = "bge-m3"

    def embed_documents(texts):
        results = []
        for t in texts:
            if t in labels_to_vectors:
                results.append(labels_to_vectors[t])
            else:
                results.append([0.0] * 4)
        return results

    mock.embed_documents = embed_documents

    def embed_query(text):
        return embed_documents([text])[0]

    mock.embed_query = embed_query
    return mock


class TestSemanticMatchEntities:
    def test_l1_exact_match_returns_standard_label(self):
        """L1: "慢跑" → "轻松跑" """
        from marathon_qa_assistant.nodes.common import ALIAS_TABLE, semantic_match_entities

        # 确保别名表存在
        assert "慢跑" in ALIAS_TABLE
        assert ALIAS_TABLE["慢跑"] == "轻松跑"

    def test_l1_no_match_falls_to_l2(self):
        """L1 无匹配 → L2 embedding → "HIIT" (>0.6)"""
        from marathon_qa_assistant.nodes.common import semantic_match_entities
        from marathon_qa_assistant.services.label_matcher import label_matcher

        with patch.object(label_matcher, "_embeddings", _make_mock_embeddings({
            "HIIT": [0.9, 0.1, 0.0, 0.0],
            "轻松跑": [0.0, 0.9, 0.0, 0.1],
        })):
            label_matcher._label_vectors = {
                "HIIT": np.array([0.9, 0.1, 0.0, 0.0], dtype=np.float32),
                "轻松跑": np.array([0.0, 0.9, 0.0, 0.1], dtype=np.float32),
            }
            label_matcher._labels = ["HIIT", "轻松跑"]
            label_matcher._threshold = 0.6
            label_matcher._warmed = True

            with patch.object(label_matcher, "_embeddings") as emb:
                emb.embed_query = lambda q: [0.85, 0.15, 0.0, 0.05]

    def test_l2_below_threshold_returns_empty(self):
        """余弦相似度 < 0.6 → 返回空列表"""
        from marathon_qa_assistant.services.label_matcher import LabelMatcher

        matcher = LabelMatcher.__new__(LabelMatcher)
        matcher._label_vectors = {
            "轻松跑": np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32),
        }
        matcher._labels = ["轻松跑"]
        matcher._threshold = 0.6
        matcher._warmed = True

        matcher._embeddings = _make_mock_embeddings({})
        matcher._embeddings.embed_query = lambda q: [1.0, 0.0, 0.0, 0.0]

        result = matcher.match("今天天气不错")
        assert result == []

    def test_embedding_cached_across_calls(self):
        """LabelMatcher.warm_up() batch embed 一次，match() 复用缓存向量"""
        from marathon_qa_assistant.services.label_matcher import LabelMatcher

        matcher = LabelMatcher.__new__(LabelMatcher)
        labels = ["HIIT", "轻松跑"]
        call_count = [0]

        mock_emb = MagicMock()
        mock_emb.model = "bge-m3"

        def embed_docs(texts):
            call_count[0] += 1
            return [[1.0, 0.0] for _ in texts]

        mock_emb.embed_documents = embed_docs
        mock_emb.embed_query = lambda q: [0.9, 0.1]
        matcher._embeddings = mock_emb
        matcher._threshold = 0.6

        matcher.warm_up(labels)
        assert call_count[0] == 1  # batch embed 一次

        matcher.match("测试查询")
        matcher.match("另一个查询")
        assert call_count[0] == 1  # match() 不触发 embed_documents
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd "C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手" && PYTHONIOENCODING=utf-8 python -m pytest tests/test_label_matcher.py -v`
Expected: 全部 FAIL（LabelMatcher / semantic_match_entities 不存在）

- [ ] **Step 3: 实现 LabelMatcher**

```python
"""label_matcher.py — KG 标签语义匹配：向量缓存 + cosine 检索"""
import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np

try:
    from langchain_ollama import OllamaEmbeddings
except ImportError:
    OllamaEmbeddings = None  # type: ignore[assignment]

logger = logging.getLogger("workflow_engine")

_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """手算余弦相似度，避免引入 scipy 依赖"""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class LabelMatcher:
    """KG 标签语义匹配器：启动时预热向量缓存，查询时 cosine 检索"""

    def __init__(self, embedding_model: str = "bge-m3"):
        if OllamaEmbeddings is None:
            raise RuntimeError("langchain_ollama 不可用，无法初始化 LabelMatcher")
        self._embeddings = OllamaEmbeddings(model=embedding_model, base_url=_OLLAMA_BASE_URL)
        self._label_vectors: Dict[str, np.ndarray] = {}
        self._labels: List[str] = []
        self._threshold: float = 0.6
        self._warmed: bool = False

    def warm_up(self, labels: List[str], threshold: float = 0.6) -> None:
        """启动时调用。batch embed 所有 KG 标签，缓存向量"""
        self._threshold = threshold
        if not labels:
            self._warmed = True
            return
        self._labels = list(labels)
        try:
            vectors = self._embeddings.embed_documents(self._labels)
        except Exception as exc:
            raise RuntimeError(
                f"LabelMatcher 预热失败: 无法 embed {len(self._labels)} 个标签。"
                f"请检查 Ollama 是否运行且模型 {self._embeddings.model} 已拉取。"
            ) from exc
        for label, vec in zip(self._labels, vectors):
            self._label_vectors[label] = np.array(vec, dtype=np.float32)
        self._warmed = True
        logger.info("[label_matcher] 预热完成，已缓存 %d 个标签向量 (threshold=%.2f)", len(self._label_vectors), self._threshold)

    def match(self, query: str, top_k: int = 3) -> List[tuple[str, float]]:
        """L2 语义匹配。返回 [(label, cosine_score), ...]，低于 threshold 的被过滤"""
        if not self._warmed:
            return []
        if not self._label_vectors or not query.strip():
            return []
        try:
            query_vec = np.array(self._embeddings.embed_query(query), dtype=np.float32)
        except Exception as exc:
            logger.warning("[label_matcher] embedding 查询失败: %s，回退到空结果", exc)
            return []
        scored = []
        for label, label_vec in self._label_vectors.items():
            sim = _cosine_similarity(query_vec, label_vec)
            if sim >= self._threshold:
                scored.append((label, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


label_matcher = LabelMatcher()
```

- [ ] **Step 4: 运行测试验证 LabelMatcher 部分通过**

Run: `cd "C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手" && PYTHONIOENCODING=utf-8 python -m pytest tests/test_label_matcher.py::TestSemanticMatchEntities::test_l2_below_threshold_returns_empty tests/test_label_matcher.py::TestSemanticMatchEntities::test_embedding_cached_across_calls -v`
Expected: 2 PASS（L2 阈值 + 缓存测试），其余 2 个 L1 测试 FAIL（ALIAS_TABLE / semantic_match_entities 不存在）

- [ ] **Step 5: 实现 ALIAS_TABLE + _EXPAND_TRIGGERS + semantic_match_entities**

在 `common.py` 中 `_KG_ENTITY_LABELS_CACHE` 行之前添加：

```python
import os

ALIAS_TABLE: dict[str, str] = {
    "高强度间歇": "HIIT",
    "间歇训练": "HIIT",
    "暴汗运动": "HIIT",
    "慢跑": "轻松跑",
    "恢复跑": "轻松跑",
    "减脂跑": "轻松跑",
    "有氧慢跑": "轻松跑",
    "核心": "核心力量",
    "核心训练": "核心力量",
    "腰腹": "核心力量",
    "爆发力": "复合速度训练",
    "冲刺": "重复跑",
    "短距离冲刺": "重复跑",
    "跑姿": "马克操（跑姿步伐操）",
    "马克操": "马克操（跑姿步伐操）",
    "步伐训练": "马克操（跑姿步伐操）",
    "滚泡沫轴": "泡沫轴放松",
    "筋膜放松": "泡沫轴放松",
    "按摩": "泡沫轴放松",
    "拉伸": "灵活度训练",
    "柔韧性": "灵活度训练",
    "爬坡": "冲坡训练 ≥300m",
    "冲坡": "冲坡训练 ≥300m",
    "上坡跑": "冲坡训练 ≥300m",
    "长距离慢跑": "长距离",
    "LSD": "长距离",
    "lsd": "长距离",
    "节奏": "节奏渐进跑",
    "变速跑": "法特莱克",
    "法特莱克跑": "法特莱克",
    "阈值": "Lactate-Threshold",
    "阈值跑": "Lactate-Threshold",
    "乳酸阈": "Lactate-Threshold",
    "力量": "Strength",
    "举铁": "Strength",
    "热身": "Warm-up",
    "激活": "Activation",
    "摄氧量": "VO2max",
    "最大摄氧量": "VO2max",
}

_EXPAND_TRIGGERS = {"动作库", "训练动作", "训练库", "exercise"}
```

修改 `expand_entities_for_kg` 中的触发逻辑：

```python
def expand_entities_for_kg(entities: List[str]) -> List[str]:
    """若实体中包含展开触发词，展开为所有 workout_template 和 category 标签。"""
    if not entities:
        return entities
    has_trigger = any(
        t.lower() in e.lower()
        for t in _EXPAND_TRIGGERS
        for e in entities
    )
    if not has_trigger:
        return entities
    kg_labels = _get_kg_entity_labels()
    expanded = list(entities)
    for label in kg_labels:
        if label not in expanded:
            expanded.append(label)
        if len(expanded) >= 25:
            break
    return expanded
```

在 `expand_entities_for_kg` 函数之后添加 `semantic_match_entities`：

```python
def semantic_match_entities(query: str) -> List[str]:
    """L1 别名精确匹配 + L2 embedding 语义兜底 → 返回 KG 标准标签列表。"""
    if not query or not query.strip():
        return []
    result: List[str] = []
    query_lower = query.lower()

    # L1: 别名表精确匹配
    for alias, standard in ALIAS_TABLE.items():
        if alias.lower() in query_lower and standard not in result:
            result.append(standard)

    # L2: embedding 语义兜底
    try:
        from marathon_qa_assistant.services.label_matcher import label_matcher
        l2_matches = label_matcher.match(query)
        for label, _score in l2_matches:
            if label not in result:
                result.append(label)
    except Exception:
        pass  # L2 失败不阻断

    return result
```

- [ ] **Step 6: 运行全部 LabelMatcher 测试**

Run: `cd "C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手" && PYTHONIOENCODING=utf-8 python -m pytest tests/test_label_matcher.py -v`
Expected: 4 PASS

- [ ] **Step 7: Commit**

```bash
git add apps/backend/src/marathon_qa_assistant/services/label_matcher.py apps/backend/src/marathon_qa_assistant/nodes/common.py tests/test_label_matcher.py
git commit -m "feat: add LabelMatcher service + ALIAS_TABLE + semantic_match_entities"
```

---

### Task 2: 集成到 entity_extraction_node

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py:13-22, 684-696`

- [ ] **Step 1: 写集成测试**

```python
# 追加到 tests/test_label_matcher.py
class TestIntegrationWithEntityExtraction:
    def test_semantic_entities_merged_into_entities(self):
        """端到端：infer_entities + semantic_match_entities → 合并去重"""
        from unittest.mock import patch
        from marathon_qa_assistant.nodes.common import (
            ALIAS_TABLE,
            infer_entities,
            semantic_match_entities,
        )
        from marathon_qa_assistant.services.label_matcher import label_matcher

        # 模拟 bge-m3 将 "想暴汗" 匹配到 "HIIT"
        with patch.object(label_matcher, "match", return_value=[("HIIT", 0.82)]):
            with patch.object(label_matcher, "_warmed", True):
                entities = infer_entities("想暴汗有什么训练动作")
                semantic = semantic_match_entities("想暴汗有什么训练动作")
                merged = list(dict.fromkeys(entities + semantic))

                # L1: "暴汗运动" 在 ALIAS_TABLE → "HIIT"
                # L2: match() → "HIIT" 
                # 去重后只保留一个 "HIIT"
                assert "HIIT" in merged
                assert merged.count("HIIT") == 1
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd "C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手" && PYTHONIOENCODING=utf-8 python -m pytest tests/test_label_matcher.py::TestIntegrationWithEntityExtraction -v`
Expected: PASS（因为 semantic_match_entities 已实现，但 entity_extraction_node 还没改）

- [ ] **Step 3: 修改 entity_extraction_node**

在 `profile_and_retrieval.py` 的 import 中添加：

```python
from marathon_qa_assistant.nodes.common import (
    ai_invoke,
    build_rag_sources,
    ensure_usage,
    expand_entities_for_kg,
    get_context,
    get_graph_context,
    graph_engine,
    infer_entities,
    semantic_match_entities,
)
```

修改 `entity_extraction_node` 中的 entities 合并逻辑：

```python
async def entity_extraction_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    query = state.get("query", "")
    entities = infer_entities(query, state.get("selected_entities"))

    # 语义匹配：L1 别名 + L2 embedding → KG 标准标签
    semantic_entities = semantic_match_entities(query)
    entities = list(dict.fromkeys(entities + semantic_entities))

    hits = await get_context(query, top_k=6)
    if not hits and entities:
        hits = await get_context(" ".join(entities), top_k=6)

    rag_sources = build_rag_sources(hits)

    # 获取图谱上下文（展开"动作库"等通用实体为具体标签）
    kg_entities = expand_entities_for_kg(entities)
    # ... 其余不变
```

- [ ] **Step 4: 运行全量测试**

Run: `cd "C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手" && PYTHONIOENCODING=utf-8 python -m pytest tests/test_label_matcher.py tests/test_exercise_parser.py tests/test_kg_register.py -v`
Expected: 所有测试 PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/src/marathon_qa_assistant/nodes/profile_and_retrieval.py tests/test_label_matcher.py
git commit -m "feat: integrate semantic_match_entities into entity_extraction_node"
```

---

### Task 3: 启动时 warm_up LabelMatcher

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/core/kb_bootstrap.py:33-73`

- [ ] **Step 1: 修改 bootstrap_knowledge_base**

在 `bootstrap_knowledge_base` 函数中，`set_kb_data(chunks, vectorizer, matrix, retrieve, bm25=bm25)` 之后、`report = {...}` 之前添加 warm_up 调用：

```python
        set_kb_data(chunks, vectorizer, matrix, retrieve, bm25=bm25)

        # 预热 LabelMatcher：batch embed KG 标签向量
        try:
            from marathon_qa_assistant.nodes.common import _get_kg_entity_labels
            from marathon_qa_assistant.services.label_matcher import label_matcher

            kg_labels = _get_kg_entity_labels()
            threshold = float(os.getenv("LABEL_MATCH_THRESHOLD", "0.6"))
            label_matcher.warm_up(kg_labels, threshold=threshold)
        except Exception as exc:
            logger.warning("[kb_bootstrap] LabelMatcher 预热失败: %s", exc)
            # 不阻断启动 — 降级到仅 L1 别名匹配

        report = {
```

需要确保 `import os` 在 `kb_bootstrap.py` 顶部。

- [ ] **Step 2: 验证编译**

Run: `cd "C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手" && PYTHONIOENCODING=utf-8 python -c "from marathon_qa_assistant.core.kb_bootstrap import bootstrap_knowledge_base; print('import ok')"`
Expected: "import ok"

- [ ] **Step 3: Commit**

```bash
git add apps/backend/src/marathon_qa_assistant/core/kb_bootstrap.py
git commit -m "feat: warm up LabelMatcher during KB bootstrap"
```

---

### Task 4: 切换 embedding 模型 bge-m3

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/services/vector_store.py:84`

- [ ] **Step 1: 改 EMBEDDING_MODEL**

```python
# 改前
EMBEDDING_MODEL = "nomic-embed-text"

# 改后
EMBEDDING_MODEL = "bge-m3"
```

- [ ] **Step 2: 确认 bge-m3 可用**

Run: `cd "C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手" && PYTHONIOENCODING=utf-8 python -c "
import os
os.environ['OLLAMA_BASE_URL'] = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
from marathon_qa_assistant.services.vector_store import get_embeddings
emb = get_embeddings()
print(f'model={emb.model}')
vec = emb.embed_query('测试')
print(f'vec_len={len(vec)}')
print('OK')
"`
Expected: `model=bge-m3` + `vec_len=1024` + `OK`

- [ ] **Step 3: Commit**

```bash
git add apps/backend/src/marathon_qa_assistant/services/vector_store.py
git commit -m "feat: switch embedding model from nomic-embed-text to bge-m3"
```

---

### Task 5: 重建向量库

**Files:** 无代码变更（纯操作）

- [ ] **Step 1: 确保 bge-m3 已拉取**

Run: `ollama pull bge-m3`

- [ ] **Step 2: 重建 vector_kb/default**

```bash
cd "C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手" && \
PYTHONIOENCODING=utf-8 python -c "
from marathon_qa_assistant.services.vector_store import build_vector_kb
from marathon_qa_assistant.core.app_state import DEFAULT_VECTOR_DIR
build_vector_kb(DEFAULT_VECTOR_DIR)
"
```

Expected: 无错误输出，`data/vector_kb/default/faiss_db/index.faiss` 更新

- [ ] **Step 3: 重建 vector_kb/user**

```bash
cd "C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手" && \
PYTHONIOENCODING=utf-8 python -c "
from marathon_qa_assistant.services.vector_store import build_vector_kb
from marathon_qa_assistant.core.app_state import USER_VECTOR_DIR
build_vector_kb(USER_VECTOR_DIR)
"
```

Expected: 无错误输出，`data/vector_kb/user/faiss_db/index.faiss` 更新

- [ ] **Step 4: 验证 KB 加载正常**

```bash
cd "C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手" && \
PYTHONIOENCODING=utf-8 python -c "
from marathon_qa_assistant.core.kb_bootstrap import bootstrap_knowledge_base
report = bootstrap_knowledge_base()
print(f'ok={report[\"ok\"]}, chunks={report[\"chunks_count\"]}')
"
```

Expected: `ok=True`, chunks > 0

- [ ] **Step 5: Commit**

```bash
git add data/vector_kb/
git commit -m "feat: rebuild vector KB with bge-m3 embeddings"
```

---

### Task 6: 全量回归 + 配置追加

- [ ] **Step 1: 追加 _EXPAND_TRIGGERS 测试**

```python
# 追加到 tests/test_common.py（如果存在）或 tests/test_label_matcher.py
def test_expand_triggers_not_hardcoded():
    """_EXPAND_TRIGGERS 为可配置集合，新增触发词不改逻辑"""
    from marathon_qa_assistant.nodes.common import _EXPAND_TRIGGERS
    assert isinstance(_EXPAND_TRIGGERS, set)
    assert "动作库" in _EXPAND_TRIGGERS
```

- [ ] **Step 2: 全量运行测试**

Run: `cd "C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手" && PYTHONIOENCODING=utf-8 python -m pytest tests/test_label_matcher.py tests/test_exercise_parser.py tests/test_kg_register.py tests/test_common.py -v 2>&1`

- [ ] **Step 3: 追加配置文档到环境变量说明**

Run:
```bash
echo "" >> .env.example 2>/dev/null || true
echo "# LabelMatcher semantic matching (L1 alias + L2 embedding)" >> .env.example
echo "LABEL_MATCH_THRESHOLD=0.6" >> .env.example
echo "LABEL_MATCH_TOPK=3" >> .env.example
```

- [ ] **Step 4: 最终 Commit**

```bash
git add tests/ .env.example
git commit -m "test: add expand trigger test + env config docs for LabelMatcher"
```
