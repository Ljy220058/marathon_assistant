# 动作库知识库修复 — 设计规格

## 背景

MCP `ds4pro_repo_scan` 对 `vector_kb_user/chunks.jsonl` 中 17 个动作库 chunk 扫描，发现 9 个问题：

| 严重性 | 数量 | 典型问题 |
|--------|------|----------|
| 高 | 4 | chunk 截断、空 content（力量激活、核心训练）、句子孤儿 |
| 中 | 4 | 孤立 objective、孤行开头、冒号缺失、编号重复 |
| 低 | 1 | categories 逗号前后多余空格 |
| 数据流 | 1 | knowledge_graph.json 零动作库条目 |

根因：`vector_store.py::split_text` 按固定 500 字符硬切，不感知语义边界。动作库 PDF 每个训练动作（name/categories/content/objective）被跨 chunk 切断，部分字段提取丢失。

## 目标

- 修复 9 个已知问题，保证动作库所有训练动作在 RAG 中可完整检索
- 动作库条目注册到知识图谱，fusion retrieval 图搜索可命中
- 通用分块器对非动作库文档不受影响
- 新增代码有单元测试覆盖（6 类损坏各至少 1 个 case）

## 非目标

- 不改动 FAISS embedding 模型或检索融合算法
- 不改动 LangGraph workflow 路由逻辑
- 不动 `vector_kb/`（系统知识库），仅重建 `vector_kb_user/`（用户知识库）

---

## 架构

### 三层改动 + 一条执行路径

```
动作库.pdf
  → document_preprocess.py           (不变：PDF → 纯文本)
  → vector_store.py::collect_chunks()
      ├─ 分支: source_file == "动作库.pdf"
      │    → exercise_parser.py      (新增第1层)
      │        → 修复 6 类损坏
      │        → 输出结构化条目 (skip 通用分块器)
      └─ else
           → split_text_sentence_aware()  (改造第2层)
  → chunks.jsonl 写入
  → FAISS index 重建
  → register_exercises_to_kg.py      (新增第3层)
      → 解析 chunk → 写入 knowledge_graph.json
```

### 模块边界

| 模块 | 职责 | 依赖 |
|------|------|------|
| `exercise_parser.py` | 解析动作库文本，修复损坏，输出结构化条目 | 无外部依赖 |
| `vector_store.py::split_text_sentence_aware` | 句边界感知通用分块 | 无外部依赖 |
| `vector_store.py::collect_chunks` | 分块入口，加动作库分支 | exercise_parser |
| `register_exercises_to_kg.py` | KG 注册脚本，幂等 | knowledge_graph.json, chunks.jsonl |

---

## 第 1 层：exercise_parser.py

### 入口

```python
def parse_action_library(text: str) -> list[dict]:
```

### 解析流程

1. 按 `\d+\.\s*name[：:]` 正则检测动作边界，切分为条目列表
2. 逐条目解析 `name` / `categories` / `content` / `objective` 字段
3. 对每个条目依次执行以下修复（顺序重要）：

#### 修复 F1：缺冒号

- 模式匹配：`categories\s+[A-Za-z一-鿿]`（冒号缺失，英文/中文直接紧跟）
- 动作：补全为 `categories：`（全角冒号，与 PDF 原始风格一致）
- 示例：`categories Anaerobic , Speed` → `categories：Anaerobic , Speed`

#### 修复 F2：编号重启

- 不依赖 `N. name：` 中的数字编号
- 以 `name` 值作为去重 key
- 若同名已存在，跳过（保留首次出现）

#### 修复 F3：孤行开头

- 检查当前条目 content 首部：若以非完整句开头（不以 `\d` `【` `name` `a.` 起始，且前一条目 content 尾部非 `。` `）` 结尾）
- 动作：将当前条目 content 首部（到第一个 `。` 或 `\n` 为止）合并到前一条目的 content 尾部
- 若当前条目被掏空，丢弃当前条目

#### 修复 F4：空 content

- `content` 为空 且 `objective` 有值 → 保留条目，标记 `content_missing: true`
- 两者都为空 → 丢弃条目（不输出）

#### 修复 F5：content 截断

- 检查 content 尾部：最后一个非空白字符是否为 `。` `）` `〗` 或 `\n`
- 若不是，合并下一个相邻条目 content 的首句（最多合并 2 个相邻条目）
- 被合并的内容从源条目移除；源条目若变空则丢弃

#### 修复 F6：孤立 objective

- 条目没有 `name` 字段 → 丢弃（无法注册为独立动作）

### 输出结构

```python
{
    "name": str,              # "轻松跑"
    "categories": list[str],  # ["Aerobic", "Base", "Recovery"]
    "content": str,           # "40-60min，在 60% - 70%HRmax"
    "objective": str,         # "建立有氧基础..."
    "content_missing": bool,  # 默认 false
    "source_file": "动作库.pdf",
    "page": int,              # 来源页码
}
```

### categories 规范化

- 按逗号（中英文）拆分
- 每条 trim 去首尾空格
- 过滤空字符串

---

## 第 2 层：vector_store.py 改造

### split_text → split_text_sentence_aware

两处改动：

1. 函数重命名，逻辑改为句边界感知：

```python
def split_text_sentence_aware(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """
    在 chunk_size 范围内向前搜索最近的句边界（。\\n\\n）作为断点。
    若区间内无句边界，回退到 ，；）→ 若无，回退到硬切。
    """
```

- 默认参数不变：`chunk_size=500, chunk_overlap=50`
- 搜索结果优先级：`。` > `\n\n` > `，` > `；` > `）` > 硬切
- 把原 `split_text` 逻辑保留为 `_split_text_fixed` 内部回退函数

2. `collect_chunks()` 加分支：

```python
from marathon_qa_assistant.services.exercise_parser import parse_action_library

if source_file == "动作库.pdf":
    parsed = parse_action_library(text)
    # 每个解析后的条目作为独立 chunk，fields 序列化为 text 字段
    for entry in parsed:
        text = f"name：{entry['name']}\ncategories：{', '.join(entry['categories'])}\ncontent：{entry['content']}\nobjective：{entry['objective']}"
        ...
```

### 向后兼容

- `--chunk-size` / `--chunk-overlap` CLI 参数不变
- 非动作库文档走 `split_text_sentence_aware`，行为改善但不破坏现有 chunk

---

## 第 3 层：register_exercises_to_kg.py

### 前置检查

```python
def ensure_schema(kg: dict) -> dict:
```

- 检查 `nodes` 中是否有 `type: "workout_template"`，若无 → 无操作（KG 不强制 schema）
- 检查 `edges` 中是否有 `relation: "has_category"`，若无 → 无操作
- 实际注册时直接写入，读入端按字段存在性容错

### 批量注册

```python
def register_exercises(chunks_path: Path, kg_path: Path) -> dict:
```

1. 读取 `vector_kb_user/chunks.jsonl`，筛选 `source_file == "动作库.pdf"`
2. 从 chunk text 解析 `name` / `categories` / `objective`
3. 为每个 `name` 创建节点：
   - `id`: `sha1("动作库_" + name)`
   - `type`: `"workout_template"`
   - `label`: `name`
   - `source_chunks`: `[chunk_id]`
   - `properties`: `{"categories": [...], "objective": "..."}`
4. 为每个 category 创建 `has_category` 边连接动作节点

### 幂等

- 按 `id`（sha1 哈希）去重
- 已存在的节点跳过，仅新增未知动作

---

## 测试计划

### `tests/test_exercise_parser.py`

覆盖 F1-F6 每类损坏至少 1 个单元测试：

| 测试 | 输入 | 期望 |
|------|------|------|
| `test_fix_missing_colon` | `"categories Anaerobic"` | `categories：Anaerobic` |
| `test_dedup_by_name` | 两个同名 "轻松跑" 条目 | 仅输出 1 个 |
| `test_merge_orphan_start` | 前条目 content 未封闭 + 当前条目孤行开头 | 合并到前条目 content 尾部 |
| `test_empty_content_with_objective` | content 空, objective 有值 | 保留, `content_missing: true` |
| `test_empty_both_discard` | content 空, objective 空 | 丢弃 |
| `test_merge_truncated_content` | content 尾非完整标点 | 合并下一 chunk 首句 |
| `test_discard_objective_only` | 仅 objective, 无 name | 丢弃 |
| `test_full_valid_exercise` | 完整四字段条目 | 正确解析 |

### `tests/test_vector_store.py`（已有，增量）

- 增加 `split_text_sentence_aware` 句边界切分 case
- 增加动作库分支跳过通用分块器 case

### `tests/test_kg_register.py`（新增）

- 验证 KG 注册幂等
- 验证 `workout_template` 节点正确创建
- 验证 `has_category` 边正确连接

---

## 风险

| 风险 | 缓解 |
|------|------|
| 修复逻辑意外合并/丢弃正确内容 | F1-F6 均为保守规则，仅触发已知模式；单元测试覆盖 |
| 句边界感知分块导致 chunk 变长，embedding 质量变化 | 保持 500 默认值，句边界仅在 ≤chunk_size 范围内优化断点 |
| 动作库分支硬编码文件名 | 当前仅一个动作库 PDF，后续可扩展为文件名匹配列表 |
| KG 注册后 fusion 权重未调优 | 注册仅保证可检索，权重调优独立进行 |
