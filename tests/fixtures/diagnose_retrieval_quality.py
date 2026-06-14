"""Phase 0a: 检索相关率诊断 + 阈值校准

输出:
- 100 条 query-hit pairs 的 BGE-M3 cosine 相似度
- DeepSeek v4 批量标注 relevance (0/1)
- Scatter plot 数据 (cosine × relevance)
- 推荐阈值 (F1 最优切分点)
"""
import json, sys, io, random, math, time
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = Path(__file__).absolute().parents[2]
OUTPUT_DIR = Path(__file__).parent / "ab_results"
OUTPUT_DIR.mkdir(exist_ok=True)


def compute_cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def load_queries() -> list[str]:
    """Load queries from eval dataset and safety bench."""
    queries = []
    # From eval dataset
    eval_file = BASE_DIR / "eval_dataset_golden.json"
    if eval_file.exists():
        data = json.loads(eval_file.read_text(encoding='utf-8'))
        if isinstance(data, list):
            queries.extend(item.get("question", item.get("query", "")) for item in data if isinstance(item, dict))
        elif isinstance(data, dict):
            queries.extend(v.get("question", v.get("query", "")) for v in data.values() if isinstance(v, dict))

    # From safety bench
    bench_file = Path(__file__).parent / "p0_safety_bench_30_queries.json"
    if bench_file.exists():
        bench = json.loads(bench_file.read_text(encoding='utf-8'))
        queries.extend(q["query"] for q in bench.get("queries", []))

    # Deduplicate, filter empty, sample 50
    queries = list(dict.fromkeys(q for q in queries if q and len(q) >= 6))
    if len(queries) > 50:
        random.seed(42)
        queries = random.sample(queries, 50)

    return queries


def retrieve_hits(query: str, faiss_store, chunks: list[dict], bm25_index: dict, top_k: int = 4) -> list[dict]:
    """FAISS + BM25 dual retrieval, return deduped top-8."""
    from marathon_qa_assistant.services.vector_store import fallback_search, _rrf_fusion

    # FAISS
    faiss_hits = []
    try:
        results = faiss_store.similarity_search_with_score(query, k=top_k * 2)
        from marathon_qa_assistant.services.vector_store import _doc_to_hit
        for doc, distance in results:
            hit = _doc_to_hit(doc, distance=distance)
            hit["retrieval_mode"] = "vector"
            faiss_hits.append(hit)
    except Exception:
        pass

    # BM25
    bm25_hits = fallback_search(query, chunks, bm25=bm25_index, top_k=top_k * 2)

    # RRF fusion, dedup to top-8
    fused = _rrf_fusion(faiss_hits, bm25_hits, top_k=8)
    return fused


async def label_relevance_batch(pairs: list[dict]) -> list[dict]:
    """Use DeepSeek v4 to batch-label relevance of query-hit pairs."""
    from marathon_qa_assistant.nodes.common import ai_invoke

    # Build batch prompt
    items = []
    for i, p in enumerate(pairs):
        items.append(f"[{i}] Query: {p['query'][:60]}\n    Hit: {p['text'][:200]}")

    prompt = (
        "You are evaluating retrieval quality for a marathon training knowledge base.\n"
        "For each query-hit pair below, judge whether the hit is RELEVANT (1) or IRRELEVANT (0) to the query.\n"
        "Relevant means: the hit contains information that directly helps answer the query.\n"
        "Irrelevant means: the hit is about a different topic or provides no useful information.\n\n"
        + "\n\n".join(items) +
        "\n\nReturn ONLY a JSON array of integers: [0, 1, 0, ...] — one per pair, in order. No other text."
    )

    try:
        result, usage = await ai_invoke(prompt, {}, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        # Parse JSON array
        text = result.strip()
        start = text.find("[")
        end = text.rfind("]") + 1
        if 0 <= start < end:
            labels = json.loads(text[start:end])
            if isinstance(labels, list) and len(labels) == len(pairs):
                for p, label in zip(pairs, labels):
                    p["relevance"] = int(label) if label in (0, 1) else 0
                return pairs
    except Exception as exc:
        print(f"  Batch labeling failed: {exc}")

    # Fallback: mark all as 0
    for p in pairs:
        p["relevance"] = 0
    return pairs


def find_best_threshold(pairs: list[dict]) -> dict:
    """Find cosine similarity threshold that maximizes F1."""
    best = {"threshold": 0.15, "f1": 0, "precision": 0, "recall": 0}
    for threshold in [round(x * 0.02, 2) for x in range(5, 46)]:  # 0.10 to 0.90
        tp = sum(1 for p in pairs if p["cosine"] >= threshold and p["relevance"] == 1)
        fp = sum(1 for p in pairs if p["cosine"] >= threshold and p["relevance"] == 0)
        fn = sum(1 for p in pairs if p["cosine"] < threshold and p["relevance"] == 1)
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 0.001)
        if f1 > best["f1"]:
            best = {"threshold": threshold, "f1": round(f1, 4),
                    "precision": round(precision, 4), "recall": round(recall, 4)}

    # Compute overall relevance rate
    relevant = sum(1 for p in pairs if p["relevance"] == 1)
    total = len(pairs)
    best["relevance_rate"] = round(relevant / total * 100, 1)
    best["total_pairs"] = total
    best["relevant_pairs"] = relevant

    return best


async def main():
    print("Phase 0a: Retrieval Quality Diagnosis")
    print(f"{'='*60}\n")

    # Load FAISS
    from langchain_community.vectorstores import FAISS
    from langchain_ollama import OllamaEmbeddings
    from marathon_qa_assistant.services.vector_store import load_chunks

    print("Loading FAISS...")
    emb = OllamaEmbeddings(model='bge-m3:latest', base_url='http://localhost:11434')
    # FAISS C++ can't handle Chinese paths — copy to temp dir
    import tempfile, shutil
    faiss_src = BASE_DIR / "data" / "vector_kb" / "v2" / "faiss_db"
    tmp_dir = Path(tempfile.mkdtemp()) / "faiss_db"
    shutil.copytree(faiss_src, tmp_dir)
    faiss = FAISS.load_local(str(tmp_dir), emb, allow_dangerous_deserialization=True)
    shutil.rmtree(tmp_dir.parent, ignore_errors=True)
    chunks = load_chunks(BASE_DIR / "data" / "vector_kb" / "v2" / "chunks.jsonl")
    print(f"  FAISS: {faiss.index.ntotal} vectors x {faiss.index.d} dim")
    print(f"  Chunks: {len(chunks)}")

    # Build BM25
    from marathon_qa_assistant.services.vector_store import build_bm25_fallback_index
    bm25 = build_bm25_fallback_index(chunks)
    print(f"  BM25: ready\n")

    # Load queries
    queries = load_queries()
    print(f"Testing {len(queries)} queries...")

    # Retrieve hits and compute cosine similarity
    all_pairs = []
    for qi, query in enumerate(queries):
        hits = retrieve_hits(query, faiss, chunks, bm25, top_k=4)
        if not hits:
            continue

        # Compute BGE-M3 cosine similarity for each hit
        try:
            query_vec = emb.embed_query(query)
        except Exception:
            continue

        for hit in hits:
            text = hit.get("parent_text") or hit.get("text", "")
            try:
                text_vec = emb.embed_query(text[:500])
            except Exception:
                continue
            cosine = compute_cosine(query_vec, text_vec)
            all_pairs.append({
                "query": query,
                "text": text[:200],
                "chunk_id": hit.get("chunk_id", ""),
                "source_file": str(hit.get("source_file", ""))[:40],
                "cosine": round(cosine, 6),
            })

        if (qi + 1) % 10 == 0:
            print(f"  {qi + 1}/{len(queries)} queries, {len(all_pairs)} pairs")

        # Cap at 100 pairs
        if len(all_pairs) >= 100:
            break

    print(f"\n  Total pairs: {len(all_pairs)}")
    print(f"  Cosine range: [{min(p['cosine'] for p in all_pairs):.4f}, {max(p['cosine'] for p in all_pairs):.4f}]")

    # AI labeling
    print(f"\nLabeling relevance with DeepSeek v4...")
    batch_size = 20
    for i in range(0, len(all_pairs), batch_size):
        batch = all_pairs[i:i + batch_size]
        await label_relevance_batch(batch)
        labeled = sum(1 for p in batch if "relevance" in p)
        print(f"  Batch {i // batch_size + 1}: {labeled}/{len(batch)} labeled")

    # Find best threshold
    best = find_best_threshold(all_pairs)

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"  Total pairs:         {best['total_pairs']}")
    print(f"  Relevant pairs:      {best['relevant_pairs']}")
    print(f"  Relevance rate:      {best['relevance_rate']}%")
    print(f"  Best threshold:      {best['threshold']}")
    print(f"  F1 at best:          {best['f1']}")
    print(f"  Precision:           {best['precision']}")
    print(f"  Recall:              {best['recall']}")

    if best["relevance_rate"] < 85:
        print(f"\n  [ACTION] Relevance rate {best['relevance_rate']}% < 85% → Start P1 (CRAG)")
        print(f"           Use threshold = {best['threshold']}")
    else:
        print(f"\n  [ACTION] Relevance rate {best['relevance_rate']}% >= 85% → Skip P1")

    # Save
    out = {
        "pairs": all_pairs,
        "best_threshold": best,
        "scatter_data": {
            "x": [p["cosine"] for p in all_pairs],
            "y": [p.get("relevance", 0) for p in all_pairs],
        },
        "decision": "START_P1" if best["relevance_rate"] < 85 else "SKIP_P1",
    }
    out_file = OUTPUT_DIR / "retrieval_diagnosis.json"
    out_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nSaved to {out_file}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
