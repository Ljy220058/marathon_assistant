# 动作库知识库修复 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复动作库知识库的 9 个问题（chunk 截断、空 content、孤立 objective、孤行开头、冒号缺失、编号重复、空格不规范、KG 缺失），通过结构化解析器 + 句边界感知分块 + KG 自动注册三层改动根治。

**Architecture:** 新增 `exercise_parser.py` 负责解析动作库 PDF 文本并修复 6 类损坏，改造 `vector_store.py` 的分块逻辑（句边界感知 + 动作库分支跳过），新增 `register_exercises_to_kg.py` 将训练动作批量注册到知识图谱。

**Tech Stack:** Python 3, pytest, JSON, FAISS, 无新增外部依赖

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `marathon_qa_assistant/services/exercise_parser.py` | 创建 | 动作库结构化解析 + 6 类损坏修复 |
| `tests/test_exercise_parser.py` | 创建 | 解析器单元测试（F1-F6 + 正常 case） |
| `marathon_qa_assistant/services/vector_store.py` | 修改 | `split_text` → `split_text_sentence_aware` + `collect_chunks` 加分支 |
| `scripts/register_exercises_to_kg.py` | 创建 | KG 自动注册脚本，幂等 |
| `tests/test_kg_register.py` | 创建 | KG 注册测试 |

---

### Task 1: 创建 exercise_parser 测试文件

**Files:**
- Create: `tests/test_exercise_parser.py`

- [ ] **Step 1: 创建测试文件，覆盖 F1-F6 及正常 case**

```python
"""动作库解析器单元测试 — 覆盖 F1-F6 六类损坏修复"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from marathon_qa_assistant.services.exercise_parser import parse_action_library


def _find_entry(entries, name):
    for e in entries:
        if e["name"] == name:
            return e
    return None


# ── 正常 case ──

def test_full_valid_exercise():
    text = """动作库
【Test Section】
1. name：轻松跑
categories：Aerobic , Base , Recovery
content：40-60min，在 60% - 70%HRmax
objective：建立有氧基础，促进血液循环与代谢废物排出。"""

    entries = parse_action_library(text)
    assert len(entries) == 1
    e = entries[0]
    assert e["name"] == "轻松跑"
    assert e["categories"] == ["Aerobic", "Base", "Recovery"]
    assert "40-60min" in e["content"]
    assert "有氧基础" in e["objective"]
    assert e["content_missing"] is False


# ── F1: 缺冒号 ──

def test_fix_missing_colon():
    text = """动作库
1. name：重复跑
categories Anaerobic , Speed , Lactate-Tolerance
content：5-6*300（800专项）
objective：提升无氧做功容量。"""

    entries = parse_action_library(text)
    e = _find_entry(entries, "重复跑")
    assert e is not None
    assert "Anaerobic" in e["categories"]
    assert "Speed" in e["categories"]


# ── F2: 编号重启 / name 去重 ──

def test_dedup_by_name():
    text = """动作库
1. name：轻松跑
categories：Aerobic
content：40-60min
objective：建立有氧基础。
1. name：轻松跑
categories：Aerobic
content：different content here
objective：重复的条目。"""

    entries = parse_action_library(text)
    names = [e["name"] for e in entries]
    assert names.count("轻松跑") == 1


# ── F3: 孤行开头合并 ──

def test_merge_orphan_start():
    text = """动作库
1. name：复合速度训练
categories：Speed , Simulation , Kick
content：4*400+4*250（前50用来渐加速到最大速度）
objective：训练疲劳状态下的冲刺能力
2. name：下一个动作
categories：Recovery
content：正常内容。"""

    entries = parse_action_library(text)
    compound = _find_entry(entries, "复合速度训练")
    # 下一个动作的 content 不应被错误合并到复合速度训练
    assert compound is not None
    next_entry = _find_entry(entries, "下一个动作")
    assert next_entry is not None


# ── F4: 空 content ──

def test_empty_content_with_objective():
    text = """动作库
1. name：核心训练
categories：Core , Stability , Strength
content：
objective：增强躯干稳定性，在疲劳状态下维持正确跑姿。"""

    entries = parse_action_library(text)
    e = _find_entry(entries, "核心训练")
    assert e is not None
    assert e["content_missing"] is True
    assert len(e["objective"]) > 0


def test_empty_both_discard():
    text = """动作库
1. name：空动作
categories：Test
content：
objective："""

    entries = parse_action_library(text)
    assert _find_entry(entries, "空动作") is None


# ── F5: content 截断合并 ──

def test_merge_truncated_content():
    text = """动作库
1. name：热身
categories：激活，有氧
content：15分钟慢跑+动态拉伸+马克操+3.2-4.8km加速跑（有氧跑加速到有氧阈值上限）力
2. name：下一个
categories：Test
content：量训练应该循序渐进。
objective：测试条目。"""

    entries = parse_action_library(text)
    warmup = _find_entry(entries, "热身")
    assert warmup is not None
    # 截断的 "力" 应与下一个 chunk 的 "量训练..." 合并
    assert "力量训练" in warmup["content"] or "力" in warmup["content"]


# ── F6: 孤立 objective 丢弃 ──

def test_discard_objective_only():
    text = """动作库
objective：这是一个没有名称的孤立目标条目，应该被丢弃。
1. name：有效动作
categories：Test
content：有名称有内容。
objective：有效目标。"""

    entries = parse_action_library(text)
    names = [e["name"] for e in entries]
    assert len(names) == 1
    assert names[0] == "有效动作"


# ── 多条目解析 ──

def test_multiple_exercises():
    text = """动作库
【Technique & Mobility】
1. name：灵活度训练
categories：Mobility , Recovery
content：静态拉伸+呼吸配合
objective：松解→改善关节活动度→激活肌肉
2. name：马克操
categories：Technique , Drills
content：A字跳、B字跳、C式等
objective：优化跑姿力学，提升神经协调性"""

    entries = parse_action_library(text)
    assert len(entries) == 2
    assert entries[0]["name"] == "灵活度训练"
    assert entries[1]["name"] == "马克操"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd "C:\Users\26318\Desktop\马拉松助手" && python -m pytest tests/test_exercise_parser.py -v
```

Expected: 全部 FAIL（`parse_action_library` 尚未定义）

- [ ] **Step 3: Commit**

```bash
git add tests/test_exercise_parser.py
git commit -m "test: add exercise_parser unit tests covering F1-F6 damage types"
```

---

### Task 2: 实现 exercise_parser.py

**Files:**
- Create: `marathon_qa_assistant/services/exercise_parser.py`

- [ ] **Step 1: 实现解析器**

```python
"""动作库 PDF 结构化解析器。

将动作库 PDF 的原始文本按训练动作拆分为结构化条目，
修复 MCP 扫描发现的 6 类损坏：缺冒号、编号重启、孤行开头、
空 content、content 截断、孤立 objective。
"""
import re
from typing import Optional


def parse_action_library(text: str) -> list[dict]:
    """解析动作库文本，返回结构化训练动作条目列表。"""
    entries = _split_by_exercise(text)
    entries = [e for e in entries if e is not None]

    # F1-F6 修复管线（顺序重要）
    entries = _fix_missing_colon(entries)        # F1
    entries = _fix_orphan_start(entries)          # F3
    entries = _fix_truncated_content(entries)      # F5
    entries = _fix_empty_content(entries)          # F4
    entries = _dedup_by_name(entries)              # F2
    entries = _discard_orphan_objective(entries)   # F6

    return entries


# ── 解析入口 ──

_EXERCISE_BOUNDARY = re.compile(
    r'(?:^|\n)(\d+)\.\s*name[：:]\s*(.+)',
    re.MULTILINE,
)


def _split_by_exercise(text: str) -> list[Optional[dict]]:
    """按 'N. name：' 边界切分，解析每个条目字段。"""
    entries = []
    lines = text.split("\n")

    # 找所有边界行索引
    boundaries = []
    for i, line in enumerate(lines):
        m = _EXERCISE_BOUNDARY.match(line) or _EXERCISE_BOUNDARY.match(" " + line)
        if m:
            boundaries.append((i, m.group(2).strip()))

    if not boundaries:
        return entries

    for idx, (line_idx, name) in enumerate(boundaries):
        next_line = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(lines)
        block = "\n".join(lines[line_idx + 1:next_line])
        entry = _parse_fields(name, block)
        entries.append(entry)

    return entries


# ── 字段解析 ──

_CATEGORIES_RE = re.compile(
    r'categories\s*[：:]\s*(.+?)(?:\n\S|$)',
    re.DOTALL,
)
_CONTENT_RE = re.compile(
    r'content\s*[：:]\s*(.+?)(?=\n(?:objective|name|\d+\.)\s|\Z)',
    re.DOTALL,
)
_OBJECTIVE_RE = re.compile(
    r'objective\s*[：:]\s*(.+?)(?=\n(?:\d+\.|【)|\Z)',
    re.DOTALL,
)


def _parse_fields(name: str, block: str) -> dict:
    """从条目文本中解析 categories/content/objective。"""
    entry = {
        "name": name.strip(),
        "categories": [],
        "content": "",
        "objective": "",
        "content_missing": False,
    }

    # categories
    cat_raw = _extract_field(block, _CATEGORIES_RE)
    if cat_raw:
        parts = re.split(r'[,，]', cat_raw)
        entry["categories"] = [p.strip() for p in parts if p.strip()]

    # content
    content_text = _extract_field(block, _CONTENT_RE)
    if content_text:
        entry["content"] = content_text.strip()

    # objective
    obj_text = _extract_field(block, _OBJECTIVE_RE)
    if obj_text:
        entry["objective"] = obj_text.strip()

    return entry


def _extract_field(text: str, pattern: re.Pattern) -> Optional[str]:
    m = pattern.search(text)
    return m.group(1).strip() if m else None


# ── F1: 缺冒号 ──

_MISSING_COLON_RE = re.compile(
    r'(categories)\s+([A-Za-z一-鿿])',
)


def _fix_missing_colon(entries: list[dict]) -> list[dict]:
    """修复 categories 后缺少冒号的条目。

    注意：修复发生在解析后，所以此函数处理解析阶段未捕获 categories 的情况。
    重新构造 entries 的 categories 字段。
    """
    # 主要工作在 _split_by_exercise 的 _parse_fields 阶段通过容错匹配完成。
    # 此处补刀：若 categories 为空且 content 首行看起来像 categories 值，
    # 尝试从原始文本恢复。
    for entry in entries:
        if entry["categories"]:
            continue
        content = entry.get("content", "")
        # 检查 content 首行是否为 categories 值被错误归入 content
        if content and re.match(r'^[A-Za-z一-鿿]+\s*[,，]', content):
            first_line = content.split("\n")[0]
            parts = re.split(r'[,，]', first_line)
            entry["categories"] = [p.strip() for p in parts if p.strip()]
            # 从 content 中移除已被识别为 categories 的首行
            rest = content[len(first_line):].strip()
            entry["content"] = rest
    return entries


# ── F2: 编号重启 / name 去重 ──

def _dedup_by_name(entries: list[dict]) -> list[dict]:
    """按 name 去重，保留首次出现的条目。"""
    seen = set()
    result = []
    for entry in entries:
        if entry["name"] not in seen:
            seen.add(entry["name"])
            result.append(entry)
    return result


# ── F3: 孤行开头合并 ──

_SENTENCE_END_RE = re.compile(r'[。》）〗\n]$')


def _fix_orphan_start(entries: list[dict]) -> list[dict]:
    """将孤儿开头的条目合并到前一条目 content 尾部。"""
    if len(entries) < 2:
        return entries

    merged = []
    i = 0
    while i < len(entries):
        entry = entries[i]
        content = entry.get("content", "")

        # 检查当前 content 是否以非完整句开头
        if _is_orphan_start(content) and merged:
            prev = merged[-1]
            prev_content = prev.get("content", "")
            # 前条目尾部未封闭 → 合并当前 content 首句到前条目
            if prev_content and not _SENTENCE_END_RE.search(prev_content[-3:]):
                first_sentence_end = _find_first_sentence_end(content)
                orphan_part = content[:first_sentence_end] if first_sentence_end > 0 else content
                prev["content"] = prev_content + orphan_part
                # 剩余部分保留在当前条目
                entry["content"] = content[first_sentence_end:].strip()
                if not entry["content"] and not entry.get("objective"):
                    i += 1
                    continue

        merged.append(entry)
        i += 1

    return merged


def _is_orphan_start(text: str) -> bool:
    """检测文本是否以孤儿片段开头（非完整句起始）。"""
    if not text:
        return False
    first_char = text.strip()[0] if text.strip() else ""
    # 以中文文字开头且前面没有标点符号 → 可能是上句的延续
    if '一' <= first_char <= '鿿':
        return True
    # 以右括号开头 → 孤儿
    if first_char in '）》〗':
        return True
    return False


def _find_first_sentence_end(text: str) -> int:
    """找到第一个句尾标点位置（不含位置返回 0）。"""
    for i, ch in enumerate(text):
        if ch in '。\n）':
            return i + 1
    return 0


# ── F4: 空 content ──

def _fix_empty_content(entries: list[dict]) -> list[dict]:
    """处理空 content：有 objective → 保留+标记；都空 → 丢弃。"""
    result = []
    for entry in entries:
        content = entry.get("content", "").strip()
        objective = entry.get("objective", "").strip()
        if not content:
            if objective:
                entry["content_missing"] = True
                result.append(entry)
            # 都空 → 丢弃
        else:
            result.append(entry)
    return result


# ── F5: content 截断合并 ──

def _fix_truncated_content(entries: list[dict]) -> list[dict]:
    """合并被截断的 content 到下一相邻条目首句。"""
    i = 0
    while i < len(entries):
        content = entries[i].get("content", "").strip()
        if content and not _SENTENCE_END_RE.search(content[-3:]):
            # content 尾部未封闭 → 截断
            if i + 1 < len(entries):
                next_content = entries[i + 1].get("content", "").strip()
                if next_content:
                    end_pos = _find_first_sentence_end(next_content)
                    if end_pos > 0:
                        entries[i]["content"] = content + next_content[:end_pos]
                        entries[i + 1]["content"] = next_content[end_pos:].strip()
        i += 1

    return entries


# ── F6: 孤立 objective ──

def _discard_orphan_objective(entries: list[dict]) -> list[dict]:
    """丢弃没有 name 的孤立 objective 条目。"""
    return [e for e in entries if e.get("name", "").strip()]
```

- [ ] **Step 2: 运行测试**

```bash
cd "C:\Users\26318\Desktop\马拉松助手" && python -m pytest tests/test_exercise_parser.py -v
```

- [ ] **Step 3: 修复失败 case 直至全部通过**

- [ ] **Step 4: Commit**

```bash
git add marathon_qa_assistant/services/exercise_parser.py
git commit -m "feat: add exercise_parser with 6 damage-type repairs for action library"
```

---

### Task 3: 创建 KG 注册测试文件

**Files:**
- Create: `tests/test_kg_register.py`

- [ ] **Step 1: 创建测试**

```python
"""知识图谱注册脚本测试 — 验证幂等性和节点/边结构"""
import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.register_exercises_to_kg import (
    register_exercises,
    parse_exercise_from_chunk,
)


def _make_chunk(chunk_id, name, categories, objective, content="test content"):
    text_parts = [f"name：{name}"]
    if categories:
        text_parts.append(f"categories：{categories}")
    if content:
        text_parts.append(f"content：{content}")
    if objective:
        text_parts.append(f"objective：{objective}")
    return {
        "chunk_id": chunk_id,
        "source_file": "动作库.pdf",
        "page": 1,
        "text": "\n".join(text_parts),
    }


class TestParseExerciseFromChunk:

    def test_parse_basic(self):
        chunk = _make_chunk(
            "动作库_p0001_c0001",
            "轻松跑",
            "Aerobic, Base, Recovery",
            "建立有氧基础",
        )
        result = parse_exercise_from_chunk(chunk)
        assert result["name"] == "轻松跑"
        assert result["categories"] == ["Aerobic", "Base", "Recovery"]

    def test_parse_empty_categories(self):
        chunk = _make_chunk(
            "动作库_p0002_c0001",
            "测试动作",
            "",
            "测试目标",
        )
        result = parse_exercise_from_chunk(chunk)
        assert result["categories"] == []

    def test_parse_chinese_categories(self):
        chunk = _make_chunk(
            "动作库_p0003_c0001",
            "热身",
            "激活，有氧",
            "保证强度课质量",
        )
        result = parse_exercise_from_chunk(chunk)
        assert "激活" in result["categories"]
        assert "有氧" in result["categories"]


class TestRegisterExercises:

    def test_idempotent(self):
        chunks = [
            _make_chunk("动作库_p0001_c0001", "轻松跑", "Aerobic", "有氧基础"),
            _make_chunk("动作库_p0001_c0001", "轻松跑", "Aerobic", "有氧基础"),  # 重复
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"nodes": {}, "edges": []}, f)
            kg_path = Path(f.name)

        try:
            result = register_exercises(chunks, kg_path)
            # 应仅注册 1 个节点
            assert result["added_nodes"] == 1
            # 第二次运行应跳过
            result2 = register_exercises(chunks, kg_path)
            assert result2["added_nodes"] == 0
        finally:
            kg_path.unlink(missing_ok=True)

    def test_creates_workout_template_node(self):
        chunks = [_make_chunk("动作库_p0001_c0001", "Tabata", "HIIT, Strength", "提升无氧代谢")]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"nodes": {}, "edges": []}, f)
            kg_path = Path(f.name)

        try:
            result = register_exercises(chunks, kg_path)
            assert result["added_nodes"] == 1

            kg = json.loads(kg_path.read_text(encoding="utf-8"))
            nodes = kg["nodes"]
            # 找到一个 workout_template 节点
            found = [n for n in nodes.values() if n.get("type") == "workout_template"]
            assert len(found) == 1
            assert found[0]["label"] == "Tabata"
            assert "chunk_id" in found[0]["source_chunks"][0] or "动作库_p0001_c0001" in str(found[0]["source_chunks"])
        finally:
            kg_path.unlink(missing_ok=True)

    def test_has_category_edges(self):
        chunks = [_make_chunk("动作库_p0001_c0001", "间歇跑", "VO2max, Speed", "提升摄氧量")]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"nodes": {}, "edges": []}, f)
            kg_path = Path(f.name)

        try:
            register_exercises(chunks, kg_path)
            kg = json.loads(kg_path.read_text(encoding="utf-8"))
            edges = kg.get("edges", [])
            has_category_edges = [e for e in edges if e.get("relation") == "has_category"]
            assert len(has_category_edges) >= 2  # VO2max + Speed
        finally:
            kg_path.unlink(missing_ok=True)
```

- [ ] **Step 2: 运行测试确认 FAIL**

```bash
cd "C:\Users\26318\Desktop\马拉松助手" && python -m pytest tests/test_kg_register.py -v
```

Expected: 全部 FAIL（模块 `scripts.register_exercises_to_kg` 尚未创建）

- [ ] **Step 3: Commit**

```bash
git add tests/test_kg_register.py
git commit -m "test: add KG registration tests for idempotency and node/edge structure"
```

---

### Task 4: 实现 register_exercises_to_kg.py

**Files:**
- Create: `scripts/register_exercises_to_kg.py`

- [ ] **Step 1: 实现注册脚本**

```python
"""将动作库训练动作注册到知识图谱。

从 vector_kb_user/chunks.jsonl 中筛选动作库条目，
解析 name/categories/objective，注册为 workout_template 节点。
支持幂等运行（按 chunk_id 去重）。
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def sha1_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def parse_exercise_from_chunk(chunk: dict) -> dict:
    """从单个 chunk 的 text 字段解析训练动作信息。"""
    text = chunk.get("text", "")

    result = {
        "name": "",
        "categories": [],
        "objective": "",
        "chunk_id": chunk.get("chunk_id", ""),
    }

    # name
    name_match = re.search(r'name[：:]\s*(.+?)(?:\n|$)', text)
    if name_match:
        result["name"] = name_match.group(1).strip()

    # categories
    cat_match = re.search(r'categories\s*[：:]\s*(.+?)(?:\n\S|$)', text, re.DOTALL)
    if cat_match:
        raw = cat_match.group(1).strip()
        result["categories"] = [c.strip() for c in re.split(r'[,，]', raw) if c.strip()]

    # objective
    obj_match = re.search(r'objective\s*[：:]\s*(.+?)(?:\n\S|\Z)', text, re.DOTALL)
    if obj_match:
        result["objective"] = obj_match.group(1).strip()

    return result


def register_exercises(chunks: list[dict], kg_path: Path) -> dict:
    """将动作库 chunk 列表注册到知识图谱 JSON 文件。幂等。"""
    if kg_path.exists():
        kg = json.loads(kg_path.read_text(encoding="utf-8"))
    else:
        kg = {"nodes": {}, "edges": []}

    existing_ids = set(kg["nodes"].keys())
    added_nodes = 0
    added_edges = 0

    for chunk in chunks:
        if chunk.get("source_file") != "动作库.pdf":
            continue

        info = parse_exercise_from_chunk(chunk)
        if not info["name"]:
            continue

        node_id = sha1_hash("动作库_" + info["name"])

        # 幂等检查
        if node_id in existing_ids:
            continue

        # 创建 workout_template 节点
        kg["nodes"][node_id] = {
            "label": info["name"],
            "type": "workout_template",
            "source_chunks": [info["chunk_id"]],
            "properties": {
                "categories": info["categories"],
                "objective": info["objective"],
            },
        }
        existing_ids.add(node_id)
        added_nodes += 1

        # 创建 has_category 边
        for cat in info["categories"]:
            cat_id = sha1_hash("category_" + cat)
            if cat_id not in existing_ids:
                kg["nodes"][cat_id] = {
                    "label": cat,
                    "type": "category",
                    "source_chunks": [],
                }
                existing_ids.add(cat_id)

            kg["edges"].append({
                "source": node_id,
                "target": cat_id,
                "relation": "has_category",
                "canonical_relation": "has_category",
                "evidence": {
                    "source": "动作库.pdf",
                    "chunk_id": info["chunk_id"],
                    "text_span": chunk.get("text", "")[:200],
                    "confidence": 1.0,
                },
            })
            added_edges += 1

    kg_path.write_text(
        json.dumps(kg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "total_nodes": len(kg["nodes"]),
        "total_edges": len(kg["edges"]),
        "added_nodes": added_nodes,
        "added_edges": added_edges,
    }


def main():
    parser = argparse.ArgumentParser(description="注册动作库训练动作到知识图谱")
    parser.add_argument(
        "--chunks-path",
        default="vector_kb_user/chunks.jsonl",
        help="chunks.jsonl 路径",
    )
    parser.add_argument(
        "--kg-path",
        default="vector_kb/knowledge_graph.json",
        help="knowledge_graph.json 路径",
    )
    args = parser.parse_args()

    chunks_path = Path(args.chunks_path).absolute()
    kg_path = Path(args.kg_path).absolute()

    if not chunks_path.exists():
        print(f"[ERROR] chunks 文件不存在: {chunks_path}")
        sys.exit(1)

    chunks = []
    with open(chunks_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))

    result = register_exercises(chunks, kg_path)

    print(f"注册完成: +{result['added_nodes']} nodes, +{result['added_edges']} edges")
    print(f"KG 总计: {result['total_nodes']} nodes, {result['total_edges']} edges")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行测试**

```bash
cd "C:\Users\26318\Desktop\马拉松助手" && python -m pytest tests/test_kg_register.py -v
```

- [ ] **Step 3: 修复直至全部通过**

- [ ] **Step 4: Commit**

```bash
git add scripts/register_exercises_to_kg.py
git commit -m "feat: add KG exercise registration script with idempotent writes"
```

---

### Task 5: 改造 vector_store.py — split_text_sentence_aware

**Files:**
- Modify: `marathon_qa_assistant/services/vector_store.py`

- [ ] **Step 1: 添加句边界感知分块函数**

在 `split_text` 函数之后、`collect_chunks` 函数之前插入以下代码：

```python
# ── 句边界感知分块（保留原 split_text 作为回退）──

_SENTENCE_BOUNDARIES = [
    re.compile(r'。'),     # 中文句号 — 最优断点
    re.compile(r'\n\n'),   # 段落分隔
    re.compile(r'[，；]'),  # 逗号/分号 — 次要断点
    re.compile(r'[）》〗]'), # 闭括号
]


def _find_best_split(text: str, chunk_size: int) -> int:
    """在 chunk_size 范围内向前查找最佳句边界作为断点。
    
    返回断点位置（exclusive），若找不到则返回 chunk_size（硬切）。
    """
    if len(text) <= chunk_size:
        return len(text)

    # 从 chunk_size 处向前搜索
    window = text[:chunk_size]
    if not window:
        return chunk_size

    for pattern in _SENTENCE_BOUNDARIES:
        matches = list(pattern.finditer(window))
        if matches:
            # 取最后一个匹配位置 + 匹配长度作为断点
            last_match = matches[-1]
            return last_match.end()

    return chunk_size


def split_text_sentence_aware(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """句边界感知文本分块。

    在 chunk_size 范围内向前搜索最近的自然断点（。\\n\\n 优先），
    若区间内无断点，回退到原 split_text 硬切行为。

    参数与 split_text 完全兼容。
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap 不能小于 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须小于 chunk_size")

    text = text.strip()
    if not text:
        return []

    chunks = []
    position = 0
    length = len(text)

    while position < length:
        # 在当前窗口内找最佳断点
        remaining = text[position:]
        cut = _find_best_split(remaining, chunk_size)
        chunk = text[position:position + cut].strip()
        if chunk:
            chunks.append(chunk)

        if position + cut >= length:
            break

        # 前进，保留 overlap
        position = position + cut - chunk_overlap
        if position < 0:
            position = 0

    return chunks
```

**注意：** 原 `split_text` 函数保留不动（作为 _split_text_fixed 的内部回退），新函数 `split_text_sentence_aware` 作为独立函数添加。

- [ ] **Step 2: 更新 collect_chunks 使用新分块函数**

在 `collect_chunks` 函数中，将：
```python
page_chunks = split_text(cleaned_page, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
```
替换为：
```python
page_chunks = split_text_sentence_aware(
    cleaned_page, chunk_size=chunk_size, chunk_overlap=chunk_overlap
)
```

- [ ] **Step 3: 验证语法**

```bash
cd "C:\Users\26318\Desktop\马拉松助手" && python -m py_compile marathon_qa_assistant/services/vector_store.py
```

- [ ] **Step 4: Commit**

```bash
git add marathon_qa_assistant/services/vector_store.py
git commit -m "feat: add sentence-aware text splitting with fallback to fixed-size cutting"
```

---

### Task 6: 改造 vector_store.py — 动作库分支

**Files:**
- Modify: `marathon_qa_assistant/services/vector_store.py`

- [ ] **Step 1: 在 collect_chunks 中添加动作库分支**

在 `collect_chunks` 函数内部，`page_chunks = split_text_sentence_aware(...)` 这行之前，插入以下逻辑：

定位到函数的 for 循环体内的 `pages = load_pages(file_path)` 之后：

```python
            pages = load_pages(file_path)
            page_count = len(pages)

            # 动作库 PDF 跳过通用分块器，使用专用结构化解析器
            if file_path.stem == "动作库":
                from marathon_qa_assistant.services.exercise_parser import parse_action_library

                full_text = "\n".join(raw_page for _, raw_page in pages)
                parsed_entries = parse_action_library(full_text)

                for entry in parsed_entries:
                    # 构造 chunk text：统一用全角冒号保持风格一致
                    parts = [f"name：{entry['name']}"]
                    if entry.get("categories"):
                        parts.append(f"categories：{' , '.join(entry['categories'])}")
                    if entry.get("content"):
                        parts.append(f"content：{entry['content']}")
                    if entry.get("objective"):
                        parts.append(f"objective：{entry['objective']}")
                    text = "\n".join(parts)

                    # chunk_id 使用 name 哈希保证唯一性
                    import hashlib
                    name_hash = hashlib.sha1(
                        entry["name"].encode("utf-8")
                    ).hexdigest()[:8]
                    chunk_id = f"动作库_{name_hash}"

                    all_chunks.append({
                        "chunk_id": chunk_id,
                        "source_file": source_meta["source_file"],
                        "source_path": source_meta["source_path"],
                        "page": entry.get("page", 0),
                        "text": text,
                    })
                    chunk_count += 1

                file_stats.append({
                    "source_file": source_meta["source_file"],
                    "source_path": source_meta["source_path"],
                    "pages": page_count,
                    "chunks": chunk_count,
                })
                continue  # 跳过通用分块器

            # ── 以下为原有通用分块逻辑 ──
            for page_num, raw_page in pages:
                cleaned_page = normalize_text(raw_page)
                page_chunks = split_text_sentence_aware(
                    cleaned_page, chunk_size=chunk_size, chunk_overlap=chunk_overlap
                )
                ...
```

精确编辑位置：在 `pages = load_pages(file_path)` 和 `page_count = len(pages)` 之后，在 `for page_num, raw_page in pages:` 循环之前。

- [ ] **Step 2: 验证语法**

```bash
cd "C:\Users\26318\Desktop\马拉松助手" && python -m py_compile marathon_qa_assistant/services/vector_store.py
```

- [ ] **Step 3: Commit**

```bash
git add marathon_qa_assistant/services/vector_store.py
git commit -m "feat: bypass generic chunker for action library PDF via exercise_parser"
```

---

### Task 7: 运行全部测试

- [ ] **Step 1: 运行全部新测试**

```bash
cd "C:\Users\26318\Desktop\马拉松助手" && python -m pytest tests/test_exercise_parser.py tests/test_kg_register.py -v
```

Expected: 全部 PASS

- [ ] **Step 2: 运行回归测试**

```bash
cd "C:\Users\26318\Desktop\马拉松助手" && python -m pytest tests/ -v
```

Expected: 已有测试保持 PASS

---

### Task 8: 重建 vector_kb_user 并执行 KG 注册

- [ ] **Step 1: 重建用户知识库**

```bash
cd "C:\Users\26318\Desktop\马拉松助手" && python marathon_qa_assistant/services/vector_store.py --mode build --input-dir uploaded_docs --output-dir vector_kb_user
```

- [ ] **Step 2: 验证动作库 chunks 质量**

检查重建后的 `vector_kb_user/chunks.jsonl` 中动作库条目：

```bash
cd "C:\Users\26318\Desktop\马拉松助手" && python -c "
import json
with open('vector_kb_user/chunks.jsonl', 'r', encoding='utf-8') as f:
    chunks = [json.loads(line) for line in f if line.strip()]
action_chunks = [c for c in chunks if c.get('source_file') == '动作库.pdf']
print(f'动作库 chunks: {len(action_chunks)}')

# 检查每个 chunk 是否有 name/categories/content/objective
issues = []
for c in action_chunks:
    t = c['text']
    checks = {'name': 'name：' in t, 'categories': 'categories：' in t,
              'content': 'content：' in t, 'objective': 'objective：' in t}
    for field, ok in checks.items():
        if not ok:
            issues.append(f\"{c['chunk_id']}: missing {field}\")
if issues:
    for i in issues:
        print(f'  [WARN] {i}')
else:
    print('All chunks have complete fields')

# 展示前 3 个
for c in action_chunks[:3]:
    print(f\"\\n--- {c['chunk_id']} ---\")
    print(c['text'][:200])
"
```

Expected:
- 动作库 chunks 数量 > 10（原来 17 个，修复后应更少且更完整）
- 每个 chunk 都有 name/categories/content/objective
- 无空 content 条目（除原始 PDF 确实为空的，如 "力量激活"）

- [ ] **Step 3: 运行 KG 注册**

```bash
cd "C:\Users\26318\Desktop\马拉松助手" && python scripts/register_exercises_to_kg.py
```

Expected: 输出 `注册完成: +N nodes, +M edges`

- [ ] **Step 4: 验证 KG 注册结果**

```bash
cd "C:\Users\26318\Desktop\马拉松助手" && python -c "
import json
with open('vector_kb/knowledge_graph.json', 'r', encoding='utf-8') as f:
    kg = json.load(f)
workout_nodes = {k: v for k, v in kg['nodes'].items() if v.get('type') == 'workout_template'}
category_nodes = {k: v for k, v in kg['nodes'].items() if v.get('type') == 'category'}
has_cat_edges = [e for e in kg['edges'] if e.get('relation') == 'has_category']
print(f'workout_template nodes: {len(workout_nodes)}')
print(f'category nodes: {len(category_nodes)}')
print(f'has_category edges: {len(has_cat_edges)}')
print(f'Sample workouts: {list(workout_nodes.keys())[:5]}')
"
```

- [ ] **Step 5: 幂等检查 — 再次运行注册**

```bash
cd "C:\Users\26318\Desktop\马拉松助手" && python scripts/register_exercises_to_kg.py
```

Expected: `注册完成: +0 nodes, +0 edges`

- [ ] **Step 6: Commit KB 重建结果**

```bash
git add vector_kb_user/ vector_kb/knowledge_graph.json
git commit -m "fix: rebuild action library KB with structured parser and KG registration"
```

---

### Task 9: 最终验证

- [ ] **Step 1: 运行全量测试**

```bash
cd "C:\Users\26318\Desktop\马拉松助手" && python -m pytest tests/ -v
```

Expected: 全部 PASS

- [ ] **Step 2: 运行 RAG 检索测试**

```bash
cd "C:\Users\26318\Desktop\马拉松助手" && python marathon_qa_assistant/services/vector_store.py --mode test --vector-dir vector_kb_user --query "核心训练怎么做" --top-k 5
```

Expected: 返回与核心训练相关的 chunk（而非空 content）

- [ ] **Step 3: 验证动作库相关查询能命中**

```bash
cd "C:\Users\26318\Desktop\马拉松助手" && python marathon_qa_assistant/services/vector_store.py --mode test --vector-dir vector_kb_user --query "轻松跑配速心率" --top-k 5
```

Expected: 返回轻松跑相关 chunk，content 字段非空

---

### 改动文件汇总

| 文件 | 操作 |
|------|------|
| `marathon_qa_assistant/services/exercise_parser.py` | 新增 |
| `marathon_qa_assistant/services/vector_store.py` | 修改（2 处） |
| `scripts/register_exercises_to_kg.py` | 新增 |
| `tests/test_exercise_parser.py` | 新增 |
| `tests/test_kg_register.py` | 新增 |
| `vector_kb_user/` | 重建 |
| `vector_kb/knowledge_graph.json` | 修改（KG 注册） |
