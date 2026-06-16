"""从已有 chunks.jsonl 构建分库索引（per-domain FAISS shards）。

输出目录结构:
    data/vector_kb/v2_sharded/
      training_protocol/
        chunks.jsonl
        faiss_db/
      nutrition/
        ...
"""

import json
import os
import sys
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
    EVIDENCE_CHAIN_METADATA_KEYS,
)
from langchain_core.documents import Document

BASE = Path(__file__).resolve().parents[1]
CHUNKS_FILE = BASE / "data" / "vector_kb" / "v2" / "chunks.jsonl"
OUTPUT_BASE = BASE / "data" / "vector_kb" / "v2_sharded"


def main():
    model = _embedding_model_name()
    print(f"嵌入模型: {model}")
    print(f"输入: {CHUNKS_FILE}")
    print(f"输出: {OUTPUT_BASE}")

    # 加载全部 chunk
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        all_chunks = [json.loads(line) for line in f if line.strip()]
    print(f"总片段: {len(all_chunks)}")

    # 按主领域分库
    shards: dict[str, list] = defaultdict(list)
    unlabeled = 0
    for c in all_chunks:
        domain = _get_primary_domain(c)
        if domain in ALL_DOMAIN_SHARDS:
            shards[domain].append(c)
        else:
            unlabeled += 1

    print("\n分库分布:")
    for name in ALL_DOMAIN_SHARDS:
        count = len(shards.get(name, []))
        print(f"  {name:25s}: {count:>6} 片段")
    if unlabeled:
        print(f"  {'<unlabeled>':25s}: {unlabeled:>6} 片段 (已跳过)")

    # 构建每个分库
    embeddings = get_embeddings()
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    total_build_time = 0.0
    for shard_name in ALL_DOMAIN_SHARDS:
        shard_chunks = shards.get(shard_name, [])
        if not shard_chunks:
            print(f"\n跳过空分库: {shard_name}")
            continue

        shard_dir = OUTPUT_BASE / shard_name
        faiss_dir = shard_dir / "faiss_db"
        shard_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n构建分库: {shard_name} ({len(shard_chunks)} 片段)")

        # 转 Document
        docs = []
        skipped_empty = 0
        for c in shard_chunks:
            text = str(c.get("text") or "")
            if not text.strip():
                skipped_empty += 1
                continue
            meta = {}
            for key in ("chunk_id", "source_file", "source_path", "page",
                        "domain_terms", "keywords_zh", "keywords_en", "synonyms",
                        "section", "paragraph_index", "char_start", "char_end",
                        "text_span", "chunking_strategy", "source_registry_id",
                        "section_anchor", "paragraph_hash", "text_span_hash",
                        "allowed_use", "prescription_permission", "quality_tier",
                        "review_status", "evidence_domain", "knowledge_layer",
                        "domain_pack", "language", "display_mode", "source_label"):
                if key in c and c.get(key) not in (None, "", {}):
                    meta[key] = c.get(key)
            docs.append(Document(page_content=text, metadata=meta))

        if skipped_empty:
            print(f"  跳过 {skipped_empty} 个空文本")

        # 验证
        _validate_embedding_model_on_sample(embeddings, docs)

        # 构建 FAISS
        start = time.time()
        try:
            faiss_store = _build_faiss_batched(docs, embeddings, batch_size=64)
            elapsed = time.time() - start
            total_build_time += elapsed
            print(f"  构建完成: {elapsed:.1f}s")

            stripped = _strip_faiss_docstore_text(faiss_store)
            if stripped:
                print(f"  已释放 docstore 文本: {stripped}")

            # 保存 FAISS
            if faiss_dir.exists():
                shutil.rmtree(faiss_dir)
                time.sleep(0.3)
            faiss_dir.mkdir(parents=True, exist_ok=True)

            faiss_dir_str = str(faiss_dir)
            if os.name == 'nt':
                try:
                    rel = os.path.relpath(faiss_dir_str, os.getcwd())
                    faiss_store.save_local(rel)
                except Exception:
                    faiss_store.save_local(faiss_dir_str)
            else:
                faiss_store.save_local(faiss_dir_str)
        except Exception as e:
            print(f"  构建失败: {e}")
            continue

        # 保存 chunks.jsonl
        chunks_path = shard_dir / "chunks.jsonl"
        with open(chunks_path, "w", encoding="utf-8") as f:
            for c in shard_chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # 元数据
    meta = {
        "embedding_model": model,
        "shards": {n: len(shards.get(n, [])) for n in ALL_DOMAIN_SHARDS},
        "total_chunks": sum(len(v) for v in shards.values()),
        "total_build_time_s": round(total_build_time, 1),
    }
    with open(OUTPUT_BASE / "shard_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n===== 分库索引构建完成 =====")
    print(f"总耗时: {total_build_time:.1f}s")
    print(f"输出: {OUTPUT_BASE}")


if __name__ == "__main__":
    main()
