"""
从 动作库.pdf 提取结构化训练动作数据，生成 chunk_schema_v2 兼容的 JSONL。
生成的 chunks 可直接追加到 data/vector_kb/v2/chunks.jsonl。

用法: python scripts/extract_action_library.py
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 项目根
ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "data" / "domain_docs" / "动作库.pdf"
OUTPUT_JSONL = ROOT / "data" / "knowledge" / "curated" / "action_library" / "action_library_chunks.jsonl"

# ── 区间关键词 → ZONE 映射（与 WORKOUT_TEMPLATE_REGISTRY 对齐）──
# 仅作后备，优先从 PDF 原文提取显式 zone_range 标注
CATEGORY_ZONE_MAP: Dict[str, str] = {
    "aerobic": "Z2-Z4",
    "base": "Z1-Z2",
    "recovery": "Z1-Z2",
    "endurance": "Z2-Z4",
    "steady-state": "Z3-Z4",
    "threshold": "Z4-Z6",
    "lactate-threshold": "Z5-Z6",
    "tempo": "Z4-Z5",
    "speed-endurance": "Z5-Z6",
    "vo2max": "Z6-Z7",
    "intervals": "Z5-Z7",
    "hard": "Z6-Z8",
    "marathon-spec": "Z3-Z5",
    "marathon-pace": "Z3-Z5",
    "long-run": "Z2-Z3",
    "hills": "Z5-Z7",
    "speed": "Z7-Z9",
    "anaerobic": "Z8-Z9",
    "lactate-tolerance": "Z8-Z9",
    "power": "Z7-Z9",
    "fartlek": "Z3-Z6",
    "mix": "Z3-Z6",
    "strength": "Z1-Z2",
    "conditioning": "Z1-Z2",
    "hiit": "Z7-Z9",
    "core": "Z1-Z2",
    "stability": "Z1-Z2",
    "technique": "Z1-Z2",
    "mobility": "Z1-Z2",
    "flexibility": "Z1-Z2",
    "warm-up": "Z1-Z2",
    "activation": "Z1-Z2",
    "pre-run": "Z1-Z2",
    "self-massage": "Z1-Z2",
    "active-rest": "Z1-Z2",
    "simulation": "Z4-Z6",
    "kick": "Z7-Z9",
    "gym": "Z1-Z2, Z7-Z9",
    "drills": "Z1-Z2",
    "cruise-intervals": "Z4-Z6",
    "strength-endurance": "Z5-Z7",
    # 中文分类关键词 → 区间映射（处理无英文名或全中文的 categories）
    "有氧": "Z2-Z4",
    "激活": "Z1-Z2",
}


def _extract_explicit_zone_range(text: str) -> Optional[str]:
    """从文本中提取明确的心率区间标注（如 '心率区间：Z3-Z4'），优先于 CATEGORY_ZONE_MAP。"""
    patterns = [
        r'心率区间[：:\s]*([Zz]\d[\-–][Zz]\d)',
        r'zone[_ ]?range[：:\s]*([Zz]\d[\-–][Zz]\d)',
        r'[（(]\s*([Zz]\d[\-–][Zz]\d)\s*[）)]',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return None


def _resolve_zone(categories: str, full_text: str = "") -> str:
    """从 categories 字段推断训练区间。
    优先从 full_text 提取显式标注（如心率区间：Z3-Z4），CATEGORY_ZONE_MAP 仅作后备。
    """
    # 优先：从 PDF 原文提取显式区间
    if full_text:
        explicit = _extract_explicit_zone_range(full_text)
        if explicit:
            return explicit

    parts = [p.strip().lower() for p in re.split(r"[,，\s]+", categories) if p.strip()]
    zones = []
    for part in parts:
        zone = CATEGORY_ZONE_MAP.get(part)
        if zone and zone not in zones:
            zones.append(zone)
    return ", ".join(zones[:3]) if zones else ""


def _extract_warmup_cooldown(
    raw_text: str,
    workout_name: str = "",
    categories: str = "",
    content: str = "",
    objective: str = "",
) -> Tuple[Optional[str], Optional[str]]:
    """从条目原始文本中提取热身/冷身建议文本。

    策略：
    1. 若条目本身为热身类训练（name/categories 含热身关键词），取其 content 作为热身建议
    2. 若条目自身包含"冷身"关键词，取其 content 作为冷身建议
    3. 否则在已解析的 content/objective 中搜索热身/冷身关键词句
    4. 以上均不满足则返回 None（不编造数据）
    """
    warmup: Optional[str] = None
    cooldown: Optional[str] = None

    cats_lower = (categories or "").lower()
    name_lower = (workout_name or "").lower()
    combined_lower = name_lower + " " + cats_lower

    # ── 判断条目本身是否为热身/冷身类训练 ──
    is_warmup_workout = any(
        kw in combined_lower
        for kw in ['热身', 'warm-up', 'warmup', 'activation']
    )
    is_cooldown_workout = any(
        kw in combined_lower
        for kw in ['冷身', 'cool-down', 'cooldown']
    )

    if is_warmup_workout:
        # 热身类条目：将 content 作为热身建议
        content_m = re.search(
            r"content[：:\s]*(.+?)(?:\nobjective[：:]|\Z)",
            raw_text, re.DOTALL | re.IGNORECASE,
        )
        if content_m and content_m.group(1).strip():
            warmup = content_m.group(1).strip()
        elif objective.strip():
            # 无 content 字段时，用 objective 作为建议
            warmup = objective.strip()
    else:
        # 非热身类条目：在已解析的 content 和 objective 中搜索热身关键词
        search_warmup = (content + "\n" + objective) if content or objective else ""
        if search_warmup and re.search(r'热身', search_warmup):
            warmup_match = re.search(
                r'[^。\n]{0,60}热身[^。\n]{0,80}[。\n]?',
                search_warmup, re.IGNORECASE,
            )
            if warmup_match:
                warmup = warmup_match.group(0).strip()

    if is_cooldown_workout:
        content_m = re.search(
            r"content[：:\s]*(.+?)(?:\nobjective[：:]|\Z)",
            raw_text, re.DOTALL | re.IGNORECASE,
        )
        if content_m and content_m.group(1).strip():
            cooldown = content_m.group(1).strip()
        elif objective.strip():
            cooldown = objective.strip()
    else:
        # 在 content 和 objective 中搜索冷身关键词
        search_fields = (content + "\n" + objective) if content or objective else ""
        if search_fields and re.search(r'(?:冷身|cool[- ]?down)', search_fields, re.IGNORECASE):
            cm = re.search(
                r'[^。\n]{0,60}(?:冷身|cool[- ]?down)[^。\n]{0,80}[。\n]?',
                search_fields, re.IGNORECASE,
            )
            if cm:
                cooldown = cm.group(0).strip()

    return warmup, cooldown


def _clean_text(text: str) -> str:
    """清洗 PDF 提取的文本噪声。"""
    # 修复常见 OCR 错误
    text = text.replace("nam e", "name")
    text = text.replace("m in", "min")
    text = text.replace("\x01", " ")
    # NFKC 规范化：将 CJK 兼容字符（如 ⾝ U+2F9D）转为标准形（身 U+8EAB）
    text = unicodedata.normalize("NFKC", text)
    # 合并多余空白
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_pdf_text(pdf_path: Path) -> str:
    """从 PDF 提取全文。"""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return "\n".join(parts)
    except Exception:
        # 尝试 PyMuPDF
        try:
            import pymupdf
            doc = pymupdf.open(str(pdf_path))
            parts = []
            for page in doc:
                parts.append(page.get_text())
            return "\n".join(parts)
        except ImportError:
            print("错误: 需要安装 pypdf 或 pymupdf", file=sys.stderr)
            sys.exit(1)


def _parse_workout_sections(full_text: str) -> List[Dict[str, Any]]:
    r"""将动作库全文解析为单个训练动作条目。

    两阶段解析策略：
    1. 主分割：按 name 前缀（\d+.\s*name）拆分，保证每个条目的 content 不被截断
    2. 补充分割：在每个主条目内检测遗漏的无 name 前缀条目（如 "5.热身"），
       特征是 \d+.\S+\ncategories： 紧跟在标题行后，而内容子标题不会紧跟 categories
    """
    category_sections = re.split(r"\n(?=【)", full_text)
    workouts: List[Dict[str, Any]] = []
    page_counter = 0

    for cat_section in category_sections:
        cat_section = cat_section.strip()
        if not cat_section:
            continue

        cat_match = re.match(r"【(.+?)】", cat_section)
        category_name = cat_match.group(1) if cat_match else ""

        # ── 阶段1：按 name 前缀拆分（保证 content 不被截断）──
        primary_items = re.split(r"\n(?=\d+\.\s*(?:nam e|name))", cat_section)

        for primary_item in primary_items:
            primary_item = primary_item.strip()
            if not primary_item or len(primary_item) < 20:
                continue

            # ── 阶段2：检测并拆分遗漏的无 name 前缀条目 ──
            # 特征: \d+.\S+ 后紧跟 categories：在同一段落内
            # 此模式只匹配真实训练条目，不匹配内容子标题（子标题后无 categories：）
            orphan_pat = r'\n(?=\d+\.\s*[^\n]+\n\s*categories[：:])'
            sub_items = re.split(orphan_pat, primary_item)

            for sub_item in sub_items:
                sub_item = sub_item.strip()
                if not sub_item or len(sub_item) < 20:
                    continue

                # 清洗文本
                raw_item_cleaned = _clean_text(sub_item)

                # ── 提取 name ──
                # 兼容 "name：xxx" 和无 name 前缀的简写条目（如 "5.热身"）
                name_match = re.search(
                    r"(?:nam e|name)[：:\s]*(.+?)(?:\n|categories)",
                    raw_item_cleaned, re.IGNORECASE,
                )
                if name_match:
                    workout_name = name_match.group(1).strip()
                else:
                    # 无 name 前缀：取 "数字." 后的第一行文本作为 name
                    alt_name = re.match(r"\d+\.\s*(.+?)(?:\n|categories|$)", raw_item_cleaned)
                    workout_name = alt_name.group(1).strip() if alt_name else ""

                if not workout_name:
                    continue

                # ── 提取 categories ──
                cat_match_item = re.search(
                    r"categories[：:\s]*(.+?)(?:\n(?:content|objective|name)|\Z)",
                    raw_item_cleaned, re.IGNORECASE,
                )
                categories = cat_match_item.group(1).strip() if cat_match_item else ""

                # ── 提取 content ──
                content_match = re.search(
                    r"content[：:\s]*(.+?)(?:\nobjective[：:]|\Z)",
                    raw_item_cleaned, re.DOTALL | re.IGNORECASE,
                )
                content = content_match.group(1).strip() if content_match else ""

                # ── 提取 objective ──
                # 兼容 objective 在 content 之前的情况（如 "5.热身" 条目）
                obj_match = re.search(
                    r"objective[：:\s]*(.+?)(?:\ncontent[：:]|\n\d+\.|【|\Z)",
                    raw_item_cleaned, re.DOTALL | re.IGNORECASE,
                )
                objective = obj_match.group(1).strip() if obj_match else ""

                page_counter += 1

                # ── zone_range：优先从 PDF 原文显式提取，CATEGORY_ZONE_MAP 作后备 ──
                zone_range = _resolve_zone(categories, raw_item_cleaned)

                # ── warmup / cooldown：从 PDF 原文搜索提取，不存在则为 null ──
                warmup_suggestion, cooldown_suggestion = _extract_warmup_cooldown(
                    raw_item_cleaned, workout_name, categories, content, objective,
                )

                # ── 构建 text 字段 ──
                text_parts = [f"name：{workout_name}"]
                if categories:
                    text_parts.append(f"categories：{categories}")
                if content:
                    text_parts.append(f"content：\n{content}")
                if zone_range:
                    text_parts.append(f"zone_range：{zone_range}")
                if objective:
                    text_parts.append(f"objective：{objective}")
                if warmup_suggestion:
                    text_parts.append(f"warmup_suggestion：{warmup_suggestion}")
                if cooldown_suggestion:
                    text_parts.append(f"cooldown_suggestion：{cooldown_suggestion}")

                chunk_id = f"动作库_p{page_counter:04d}_c0001"

                workouts.append({
                    "chunk_id": chunk_id,
                    "source_file": "动作库.pdf",
                    "source_registry_id": f"src_local_action_library_{chunk_id}",
                    "source_url": "",
                    "local_path": "data/domain_docs/动作库.pdf",
                    "page": page_counter,
                    "section": category_name,
                    "paragraph_index": 0,
                    "char_start": 0,
                    "char_end": len(text_parts[-1]) if text_parts else 0,
                    "text": "\n".join(text_parts),
                    "language": "zh",
                    "domain_pack": "action_library",
                    "evidence_domain": "action_library",
                    "knowledge_layer": "domain_pack",
                    "allowed_use": "core_prescription",
                    "prescription_permission": "can_write_core",
                    "quality_tier": "reviewed",
                    "needs_review": False,
                    "exclude_from_training_generation": False,
                    "domain_terms": [workout_name] + [
                        c.strip() for c in re.split(r"[,，\s]+", categories) if c.strip()
                    ],
                    "warmup_suggestion": warmup_suggestion,
                    "cooldown_suggestion": cooldown_suggestion,
                    "tags": {
                        "workout_name": workout_name,
                        "categories": categories,
                        "zone_range": zone_range,
                        "has_content": bool(content),
                        "has_objective": bool(objective),
                        "has_warmup": warmup_suggestion is not None,
                        "has_cooldown": cooldown_suggestion is not None,
                    },
                })

    return workouts


def _append_to_chunks_jsonl(workouts: List[Dict[str, Any]], chunks_path: Path) -> None:
    """将提取的动作库条目同步到 v2 chunks.jsonl。
    先移除所有旧的 action_library 条目，再写入新条目，确保字段结构一致。
    """
    new_ids = {w["chunk_id"] for w in workouts}

    # 读取已有条目，过滤掉所有 action_library 旧条目
    existing_entries: List[Dict[str, Any]] = []
    removed_count = 0
    if chunks_path.exists():
        with open(chunks_path, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("domain_pack") == "action_library":
                        removed_count += 1
                    else:
                        existing_entries.append(entry)
                except json.JSONDecodeError:
                    continue

    # 重写整个文件：保留非 action_library 条目 + 追入新条目
    total_before = len(existing_entries) + removed_count
    with open(chunks_path, "w", encoding="utf-8") as f:
        for entry in existing_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        for w in workouts:
            f.write(json.dumps(w, ensure_ascii=False) + "\n")

    total_after = len(existing_entries) + len(workouts)
    print(f"  移除旧 action_library 条目: {removed_count} 条")
    print(f"  写入新条目: {len(workouts)} 条")
    print(f"  chunks.jsonl: {total_before} -> {total_after} 条")
    return len(workouts)


def _save_standalone(workouts: List[Dict[str, Any]], output_path: Path) -> None:
    """保存为独立 JSONL 文件，作为源数据留档。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for w in workouts:
            f.write(json.dumps(w, ensure_ascii=False) + "\n")
    print(f"  独立 JSONL 已保存: {output_path}")


def _print_summary(workouts: List[Dict[str, Any]]) -> None:
    """打印提取摘要。"""
    print(f"\nFound {len(workouts)} workout entries:")
    for w in workouts:
        name = (w.get("tags") or {}).get("workout_name", w.get("text", "")[:40])
        zone = (w.get("tags") or {}).get("zone_range", "")
        cats = (w.get("tags") or {}).get("categories", "")
        has_c = "Y" if (w.get("tags") or {}).get("has_content") else "N"
        has_o = "Y" if (w.get("tags") or {}).get("has_objective") else "N"
        has_w = "Y" if (w.get("tags") or {}).get("has_warmup") else "N"
        has_cd = "Y" if (w.get("tags") or {}).get("has_cooldown") else "N"
        warmup_val = w.get("warmup_suggestion")
        cooldown_val = w.get("cooldown_suggestion")
        # ASCII-safe output to avoid Windows GBK encoding issues
        safe_name = name.encode('ascii', errors='replace').decode('ascii')[:30]
        safe_cats = cats[:50].encode('ascii', errors='replace').decode('ascii')
        w_str = f"{'Y' if warmup_val else 'N'}/{len(warmup_val) if warmup_val else 0}"
        cd_str = f"{'Y' if cooldown_val else 'N'}/{len(cooldown_val) if cooldown_val else 0}"
        print(f"  [{w['chunk_id']}] {safe_name:30s} zone={zone:12s} c={has_c} o={has_o} w={has_w}({len(warmup_val) if warmup_val else 0}) cd={has_cd} cats={safe_cats}")


def main():
    print(f"读取: {PDF_PATH}")
    full_text = _extract_pdf_text(PDF_PATH)
    print(f"PDF 文本长度: {len(full_text)} 字符")

    workouts = _parse_workout_sections(full_text)
    _print_summary(workouts)

    # 1. 保存独立 JSONL（源数据留档）
    _save_standalone(workouts, OUTPUT_JSONL)

    # 2. 追加到 v2 chunks.jsonl
    v2_chunks_path = ROOT / "data" / "vector_kb" / "v2" / "chunks.jsonl"
    if v2_chunks_path.exists():
        print(f"\n追加到 v2 chunks: {v2_chunks_path}")
        _append_to_chunks_jsonl(workouts, v2_chunks_path)
    else:
        print(f"\n⚠ v2 chunks.jsonl 不存在，跳过追加。独立 JSONL 位于 {OUTPUT_JSONL}")

    print("\nDone. Next: rebuild FAISS index.")


if __name__ == "__main__":
    main()
