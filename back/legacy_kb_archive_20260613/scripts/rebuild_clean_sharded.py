"""从 v2 chunks.jsonl 重建清洗版分库索引：页眉剥离 + 语义分组嵌入。

策略：复用 v2 的片段结构（domain_terms 100% 覆盖），只清理文本中的重复页眉，
然后用清理后的文本重建 FAISS 嵌入。这样保证领域标签完整同时消除标题污染。

输出: data/vector_kb/v2_sharded_clean/
"""

import os
import sys
import json
import re
import shutil
import time
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / "src"))

from marathon_qa_assistant.services.vector_store import (
    ALL_DOMAIN_SHARDS,
    _get_primary_domain,
    _build_faiss_batched,
    _strip_faiss_docstore_text,
    _validate_embedding_model_on_sample,
    get_embeddings,
    _embedding_model_name,
)
from marathon_qa_assistant.services.document_preprocess import normalize_text
from langchain_core.documents import Document

BASE = Path(__file__).resolve().parents[1]
INPUT_CHUNKS = BASE / "data" / "vector_kb" / "v2" / "chunks.jsonl"
OUTPUT_BASE = BASE / "data" / "vector_kb" / "v2_sharded_clean"


def _find_file_header(chunks: list[dict]) -> str:
    """对同一源文件的所有片段，检测出现在多数片段开头的公共页眉。"""
    if len(chunks) < 3:
        return ""
    # 取每个片段的前100字符（跳过空白）
    prefixes = []
    for c in chunks:
        text = str(c.get("text") or "").strip()
        if len(text) > 30:
            prefixes.append(text[:100])
    if len(prefixes) < 3:
        return ""

    # 找所有片段共享的最长公共前缀
    def _lcp(a: str, b: str) -> str:
        i = 0
        for ca, cb in zip(a, b):
            if ca != cb:
                break
            i += 1
        return a[:i]

    candidate = prefixes[0]
    for p in prefixes[1:]:
        candidate = _lcp(candidate, p)

    # 在最后一个单词边界截断，避免截断单词
    if " " in candidate and len(candidate) > 30:
        last_space = candidate.rfind(" ")
        if last_space > 20:
            candidate = candidate[:last_space]
    candidate = candidate.rstrip(" ,-.:;0123456789")
    if len(candidate) < 20:
        return ""

    # 确认出现在多数片段开头
    match_count = sum(1 for p in prefixes if p.startswith(candidate))
    if match_count < len(prefixes) * 0.5:
        return ""
    return candidate


def _strip_header_from_chunk(text: str, header: str) -> str:
    """从片段文本中移除页眉前缀及紧随的页码标记。"""
    if not header:
        return text
    t = str(text or "").strip()
    if t.startswith(header):
        t = t[len(header):].strip()
        # 移除 "Page X." / "Page X of Y" 模式的页码
        t = re.sub(r"^[Pp]age\s*\d+(\s*of\s*\d+)?[.\s]*", "", t, count=1)
        t = re.sub(r"^\d{1,4}\s*\n?", "", t, count=1)
        t = re.sub(r"^[.,;:\s]+", "", t)
    return t.strip()


def main():
    model = _embedding_model_name()
    print(f"嵌入模型: {model}")
    print(f"输入: {INPUT_CHUNKS}")
    print(f"输出: {OUTPUT_BASE}")

    # ── 步骤1: 加载 + 页眉检测 ──
    print("\n── 步骤1: 加载 v2 chunks，按源文件检测页眉 ──")
    with open(INPUT_CHUNKS, encoding="utf-8") as f:
        all_chunks = [json.loads(line) for line in f if line.strip()]
    print(f"  总片段: {len(all_chunks)}")

    # 按源文件分组
    by_file: dict[str, list] = defaultdict(list)
    for c in all_chunks:
        by_file[c.get("source_file", "unknown")].append(c)

    # 检测每个文件的页眉
    file_headers: dict[str, str] = {}
    total_stripped = 0
    for fname, chunks in by_file.items():
        header = _find_file_header(chunks)
        if header:
            file_headers[fname] = header
            total_stripped += len(chunks)
    print(f"  检测到页眉的文件: {len(file_headers)}/{len(by_file)}")
    print(f"  受影响片段: {total_stripped}/{len(all_chunks)} ({total_stripped/len(all_chunks)*100:.1f}%)")

    # 展示几个页眉样例
    for fname, header in list(file_headers.items())[:5]:
        print(f"    {fname[:50]}: '{header[:80]}...'")

    # ── 步骤2: 清理文本 ──
    print("\n── 步骤2: 剥离页眉 ──")
    cleaned_count = 0
    for c in all_chunks:
        fname = c.get("source_file", "unknown")
        header = file_headers.get(fname, "")
        if header:
            old_text = str(c.get("text") or "")
            new_text = _strip_header_from_chunk(old_text, header)
            if new_text != old_text:
                c["text"] = new_text
                cleaned_count += 1
    print(f"  实际修改片段: {cleaned_count}")

    # ── 步骤2.5: 计算 Parent-Child 上下文 ──
    print("\n── 步骤2.5: 计算 Parent-Child 上下文 ──")
    # 按 (source_file, page) 分组，为每个片段拼接相邻片段的文本作为 parent_text
    page_groups = defaultdict(list)
    for i, c in enumerate(all_chunks):
        key = (c.get("source_file", ""), c.get("page", 0))
        page_groups[key].append(i)
    parent_count = 0
    for indices in page_groups.values():
        n = len(indices)
        for pos, idx in enumerate(indices):
            # 取 ±2 个相邻片段（约 500×5=2500 字符窗口）
            neighbors = []
            for offset in range(-2, 3):
                neighbor_pos = pos + offset
                if 0 <= neighbor_pos < n:
                    neighbors.append(str(all_chunks[indices[neighbor_pos]].get("text") or ""))
            parent = "\n\n".join(neighbors)
            # 截断到 ~3000 字符
            if len(parent) > 3000:
                parent = parent[:3000] + "..."
            all_chunks[idx]["parent_text"] = parent
            parent_count += 1
    print(f"  已添加 parent_text: {parent_count} 个片段")

    # 展示清理效果
    for fname in list(file_headers.keys())[:2]:
        samples = [c for c in all_chunks if c.get("source_file") == fname]
        if samples:
            print(f"\n  {fname[:60]}:")
            for i, c in enumerate(samples[:2]):
                text = c.get("text", "")
                print(f"    片段{i+1} (len={len(text)}): {text[:120]}...")

    # ── 步骤3: 分库 ──
    print("\n── 步骤3: 按领域分库 ──")
    shards = defaultdict(list)
    unlabeled = 0
    for c in all_chunks:
        domain = _get_primary_domain(c)
        if domain in ALL_DOMAIN_SHARDS:
            shards[domain].append(c)
        else:
            unlabeled += 1
    for name in ALL_DOMAIN_SHARDS:
        print(f"  {name:25s}: {len(shards.get(name, [])):>6} 片段")
    if unlabeled:
        print(f"  {'<unlabeled>':25s}: {unlabeled:>6} 片段 (已跳过)")

    # ── 步骤4: 构建分库 FAISS ──
    print("\n── 步骤4: 构建分库 FAISS ──")
    embeddings = get_embeddings()
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
    total_time = 0.0

    for shard_name in ALL_DOMAIN_SHARDS:
        shard_chunks = shards.get(shard_name, [])
        if not shard_chunks:
            continue
        shard_dir = OUTPUT_BASE / shard_name
        faiss_dir = shard_dir / "faiss_db"
        shard_dir.mkdir(parents=True, exist_ok=True)

        print(f"  {shard_name}: {len(shard_chunks)} 片段...")

        docs = []
        skipped = 0
        for c in shard_chunks:
            text = str(c.get("text") or "").strip()
            if not text:
                skipped += 1
                continue
            meta = {k: c[k] for k in (
                "chunk_id", "source_file", "source_path", "page",
                "domain_terms", "keywords_zh", "keywords_en", "synonyms",
                "section", "paragraph_index", "char_start", "char_end",
                "text_span", "chunking_strategy", "source_registry_id",
                "section_anchor", "paragraph_hash", "text_span_hash",
                "allowed_use", "prescription_permission", "quality_tier",
                "review_status", "evidence_domain", "knowledge_layer",
                "domain_pack", "language", "parent_text",
            ) if k in c and c.get(k) not in (None, "", {})}
            docs.append(Document(page_content=text, metadata=meta))

        if skipped:
            print(f"    跳过空文本: {skipped}")

        _validate_embedding_model_on_sample(embeddings, docs)
        t0 = time.time()
        faiss_store = _build_faiss_batched(docs, embeddings, batch_size=64)
        dt = time.time() - t0
        total_time += dt
        print(f"    构建: {dt:.1f}s")

        _strip_faiss_docstore_text(faiss_store)

        if faiss_dir.exists():
            shutil.rmtree(faiss_dir)
            time.sleep(0.3)
        faiss_dir.mkdir(parents=True, exist_ok=True)
        faiss_dir_str = str(faiss_dir)
        if os.name == 'nt':
            try:
                faiss_store.save_local(os.path.relpath(faiss_dir_str, os.getcwd()))
            except Exception:
                faiss_store.save_local(faiss_dir_str)
        else:
            faiss_store.save_local(faiss_dir_str)

        with open(shard_dir / "chunks.jsonl", "w", encoding="utf-8") as f:
            for c in shard_chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # 元数据
    meta = {
        "embedding_model": model,
        "header_stripping": True,
        "stripped_files": len(file_headers),
        "source": "v2 chunks cleaned",
        "shards": {n: len(shards.get(n, [])) for n in ALL_DOMAIN_SHARDS},
        "total_chunks": sum(len(v) for v in shards.values()),
        "build_time_s": round(total_time, 1),
    }
    with open(OUTPUT_BASE / "shard_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n===== 完成 =====")
    print(f"构建耗时: {total_time:.1f}s")
    print(f"输出: {OUTPUT_BASE}")


if __name__ == "__main__":
    main()
