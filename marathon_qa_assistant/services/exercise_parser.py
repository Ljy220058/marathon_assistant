"""动作库 PDF 结构化解析器。

将动作库 PDF 的原始文本按训练动作拆分为结构化条目，
修复 MCP 扫描发现的 6 类损坏：缺冒号、编号重启、孤行开头、
空 content、content 截断、孤立 objective。
"""
import re
from typing import Optional

_EXERCISE_BOUNDARY = re.compile(
    r'(?:^|\n)(\d+)\.\s*name[：:]\s*(.+)',
    re.MULTILINE,
)

_CATEGORIES_RE = re.compile(
    r'categories[：:]?\s*(.+?)(?:\n\S|$)',
    re.DOTALL,
)
_CONTENT_RE = re.compile(
    r'content[：:][ \t]*(.*?)(?=\n(?:objective|categories|name)[：:]|\n【|\Z)',
    re.DOTALL,
)
_OBJECTIVE_RE = re.compile(
    r'objective[：:][ \t]*(.*?)(?=\n(?:categories|name)[：:]|\n【|\Z)',
    re.DOTALL,
)

_SENTENCE_END_RE = re.compile(r'[。》）〗\n]$')
_MISSING_COLON_RE = re.compile(
    r'(categories)\s+([A-Za-z一-鿿])',
)


def parse_action_library(text: str) -> list[dict]:
    """解析动作库文本，返回结构化训练动作条目列表。"""
    entries = _split_by_exercise(text)
    entries = [e for e in entries if e is not None]

    entries = _fix_missing_colon(entries)
    entries = _fix_empty_content(entries)
    entries = _fix_orphan_start(entries)
    entries = _fix_truncated_content(entries)
    entries = _dedup_by_name(entries)
    entries = _discard_orphan_objective(entries)

    return entries


def _split_by_exercise(text: str) -> list[Optional[dict]]:
    """按 'N. name：' 边界切分，解析每个条目字段。"""
    lines = text.split("\n")
    boundaries = []
    for i, line in enumerate(lines):
        m = _EXERCISE_BOUNDARY.match(line) or _EXERCISE_BOUNDARY.match(" " + line)
        if m:
            boundaries.append((i, m.group(2).strip()))

    if not boundaries:
        return []

    entries = []
    for idx, (line_idx, name) in enumerate(boundaries):
        next_line = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(lines)
        block = "\n".join(lines[line_idx + 1 : next_line])
        entry = _parse_fields(name, block)
        entries.append(entry)

    return entries


def _parse_fields(name: str, block: str) -> dict:
    """从条目文本中解析 categories/content/objective。"""
    entry = {
        "name": name.strip(),
        "categories": [],
        "content": "",
        "objective": "",
        "content_missing": False,
    }

    cat_raw = _extract_field(block, _CATEGORIES_RE)
    if cat_raw:
        parts = re.split(r'[,，]', cat_raw)
        entry["categories"] = [p.strip() for p in parts if p.strip()]

    content_text = _extract_field(block, _CONTENT_RE)
    if content_text:
        entry["content"] = content_text.strip()

    obj_text = _extract_field(block, _OBJECTIVE_RE)
    if obj_text:
        entry["objective"] = obj_text.strip()

    return entry


def _extract_field(text: str, pattern: re.Pattern) -> Optional[str]:
    m = pattern.search(text)
    return m.group(1).strip() if m else None


def _fix_missing_colon(entries: list[dict]) -> list[dict]:
    """F1: 修复 categories 未捕获的情况 — content 首行可能是 categories 值。"""
    for entry in entries:
        if entry["categories"]:
            continue
        content = entry.get("content", "")
        if content and re.match(r'^[A-Za-z一-鿿]+\s*[,，]', content):
            first_line = content.split("\n")[0]
            parts = re.split(r'[,，]', first_line)
            entry["categories"] = [p.strip() for p in parts if p.strip()]
            rest = content[len(first_line) :].strip()
            entry["content"] = rest
    return entries


def _fix_empty_content(entries: list[dict]) -> list[dict]:
    """F4: 空 content → 有 objective 保留+标记，都空丢弃。"""
    result = []
    for entry in entries:
        content = entry.get("content", "").strip()
        objective = entry.get("objective", "").strip()
        if not content:
            if objective:
                entry["content_missing"] = True
                result.append(entry)
        else:
            result.append(entry)
    return result


def _fix_orphan_start(entries: list[dict]) -> list[dict]:
    """F3: 孤行开头合并到前一条目 content 尾部。"""
    if len(entries) < 2:
        return entries

    merged = []
    i = 0
    while i < len(entries):
        entry = entries[i]
        content = entry.get("content", "")

        if _is_orphan_start(content) and merged:
            prev = merged[-1]
            prev_content = prev.get("content", "")
            if prev_content and not _SENTENCE_END_RE.search(prev_content[-3:]):
                first_end = _find_first_sentence_end(content)
                orphan_part = content[:first_end] if first_end > 0 else content
                prev["content"] = prev_content + orphan_part
                entry["content"] = content[first_end:].strip()
                if not entry["content"] and not entry.get("objective"):
                    i += 1
                    continue

        merged.append(entry)
        i += 1

    return merged


def _is_orphan_start(text: str) -> bool:
    if not text:
        return False
    first_char = text.strip()[0] if text.strip() else ""
    if "一" <= first_char <= "鿿":
        return True
    if first_char in "）》〗":
        return True
    return False


def _find_first_sentence_end(text: str) -> int:
    for i, ch in enumerate(text):
        if ch in "。\n）":
            return i + 1
    return 0


def _fix_truncated_content(entries: list[dict]) -> list[dict]:
    """F5: content 尾部未封闭 → 合并下一相邻条目首句。"""
    i = 0
    while i < len(entries):
        content = entries[i].get("content", "").strip()
        if content and not _SENTENCE_END_RE.search(content[-3:]):
            if i + 1 < len(entries):
                next_content = entries[i + 1].get("content", "").strip()
                if next_content:
                    end_pos = _find_first_sentence_end(next_content)
                    if end_pos > 0:
                        entries[i]["content"] = content + next_content[:end_pos]
                        entries[i + 1]["content"] = next_content[end_pos:].strip()
        i += 1
    return entries


def _dedup_by_name(entries: list[dict]) -> list[dict]:
    """F2: 按 name 去重，保留首次出现。"""
    seen = set()
    result = []
    for entry in entries:
        if entry["name"] not in seen:
            seen.add(entry["name"])
            result.append(entry)
    return result


def _discard_orphan_objective(entries: list[dict]) -> list[dict]:
    """F6: 丢弃没有 name 的孤立 objective 条目。"""
    return [e for e in entries if e.get("name", "").strip()]
