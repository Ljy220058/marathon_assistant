"""从已有 chunks.jsonl 构建 BGE-M3 对照索引，避免重新处理文件。

用法:
    MARATHON_EMBEDDING_MODEL=bge-m3 python scripts/build_comparison_index.py
    MARATHON_EMBEDDING_MODEL=multilingual-e5 python scripts/build_comparison_index.py
"""

import json
import os
import sys
import shutil
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / "src"))

from marathon_qa_assistant.services.vector_store import (
    _build_faiss_batched,
    _strip_faiss_docstore_text,
    _validate_embedding_model_on_sample,
    get_embeddings,
    _embedding_model_name,
)
from marathon_qa_assistant.core.settings import get_settings
from langchain_core.documents import Document

BASE = Path(__file__).resolve().parents[1]
CHUNKS_FILE = BASE / "data" / "vector_kb" / "v2" / "chunks.jsonl"
OUTPUT_DIR = BASE / "data" / "vector_kb" / "v2_bge_m3"
FAISS_DIR = OUTPUT_DIR / "faiss_db"


def main():
    model = _embedding_model_name()
    print(f"嵌入模型: {model}")
    print(f"输入: {CHUNKS_FILE}")
    print(f"输出: {OUTPUT_DIR}")

    # 加载 chunks
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f if line.strip()]
    print(f"加载 {len(chunks)} 个片段")

    # 转 Document
    docs = []
    skipped_empty = 0
    for c in chunks:
        text = str(c.get("text") or "")
        if not text.strip():
            skipped_empty += 1
            continue
        meta = {"chunk_id": c.get("chunk_id", ""),
                "source_file": c.get("source_file", ""),
                "source_path": c.get("source_path", ""),
                "page": c.get("page", 1)}
        # 保留所有证据链元数据
        for key in ("domain_terms", "keywords_zh", "keywords_en", "synonyms",
                     "section", "paragraph_index", "char_start", "char_end",
                     "text_span", "chunking_strategy", "source_registry_id",
                     "section_anchor", "paragraph_hash", "text_span_hash",
                     "allowed_use", "prescription_permission", "quality_tier",
                     "review_status", "evidence_domain", "knowledge_layer",
                     "domain_pack", "language", "display_mode", "source_label",
                     "exclude_from_training_generation", "needs_review"):
            if key in c and c.get(key) not in (None, "", {}):
                meta[key] = c[key]
        docs.append(Document(page_content=text, metadata=meta))

    if skipped_empty:
        print(f"跳过 {skipped_empty} 个空文本片段")
    print(f"准备 {len(docs)} 个 Document")

    # 构建 FAISS
    embeddings = get_embeddings()
    print("验证嵌入模型样本...")
    validation = _validate_embedding_model_on_sample(embeddings, docs)
    print(f"  样本验证通过: {validation}")

    print("构建 FAISS 索引 (batch_size=64)...")
    start = time.time()
    faiss_store = _build_faiss_batched(docs, embeddings, batch_size=64)
    elapsed = time.time() - start
    print(f"  完成, 耗时: {elapsed:.1f}s")

    stripped = _strip_faiss_docstore_text(faiss_store)
    print(f"  已释放 docstore 文本: {stripped} 个")

    # 保存
    if FAISS_DIR.exists():
        shutil.rmtree(FAISS_DIR)
        time.sleep(0.5)
    FAISS_DIR.mkdir(parents=True, exist_ok=True)

    faiss_dir_str = str(FAISS_DIR)
    if os.name == 'nt':
        try:
            rel_path = os.path.relpath(faiss_dir_str, os.getcwd())
            faiss_store.save_local(rel_path)
            print(f"  已保存 (相对路径): {rel_path}")
        except Exception as e:
            print(f"  相对路径保存失败: {e}, 尝试绝对路径")
            faiss_store.save_local(faiss_dir_str)
    else:
        faiss_store.save_local(faiss_dir_str)

    # 复制 chunks.jsonl（同源片段，保证比较公平）
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CHUNKS_FILE, OUTPUT_DIR / "chunks.jsonl")

    # 写元数据
    meta = {
        "embedding_model": model,
        "chunk_count": len(chunks),
        "doc_count": len(docs),
        "build_time_s": round(elapsed, 1),
        "stripped_docstore_text_count": stripped,
        "source_index": str(CHUNKS_FILE),
    }
    meta_path = OUTPUT_DIR / "index_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n索引构建完成: {OUTPUT_DIR}")
    print(f"元数据: {meta_path}")


if __name__ == "__main__":
    main()
