"""Phase 0c: Chunk 语义完整性诊断

随机抽 50 个 chunk，DeepSeek v4 判读"仅凭这个片段能否理解其含义"
"""
import json, sys, io, random
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = Path(__file__).absolute().parents[2]
OUTPUT_DIR = Path(__file__).parent / "ab_results"
OUTPUT_DIR.mkdir(exist_ok=True)


async def score_chunks_batch(chunks: list[dict]) -> list[dict]:
    """Use DeepSeek v4 to score each chunk's semantic completeness."""
    from marathon_qa_assistant.nodes.common import ai_invoke

    items = []
    for i, c in enumerate(chunks):
        text = c.get("text", "")[:300].replace("\n", " ")
        items.append(f"[{i}] {text}")

    prompt = (
        "You are evaluating chunk quality for a marathon training knowledge base.\n"
        "For each text chunk below, judge whether you can understand its meaning from this fragment ALONE:\n"
        "  1 = Cannot understand at all (broken sentence, missing subject, code snippet)\n"
        "  2 = Partially understandable (missing context but main idea can be guessed)\n"
        "  3 = Fully understandable (complete thought, clear meaning)\n\n"
        "A chunk might be from Chinese or English sports science literature.\n\n"
        + "\n".join(items) +
        "\n\nReturn ONLY a JSON array of integers: [2, 3, 1, ...] — one per chunk, in order. No other text."
    )

    try:
        result, usage = await ai_invoke(prompt, {}, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        text = result.strip()
        start = text.find("[")
        end = text.rfind("]") + 1
        if 0 <= start < end:
            scores = json.loads(text[start:end])
            if isinstance(scores, list) and len(scores) == len(chunks):
                for c, s in zip(chunks, scores):
                    c["semantic_score"] = int(s) if s in (1, 2, 3) else 2
                return chunks
    except Exception as exc:
        print(f"  Batch scoring failed: {exc}")

    for c in chunks:
        c["semantic_score"] = 2
    return chunks


async def main():
    print("Phase 0c: Chunk Semantic Completeness")
    print(f"{'='*60}\n")

    # Load chunks
    chunks_file = BASE_DIR / "data" / "vector_kb" / "v2" / "chunks.jsonl"
    chunks = []
    with open(chunks_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))

    print(f"Total chunks: {len(chunks)}")

    # Random sample 50
    random.seed(42)
    sample = random.sample(chunks, min(50, len(chunks)))
    print(f"Sampled: {len(sample)}")

    # Score in 2 batches of 25
    print("Scoring with DeepSeek v4...")
    batch1 = sample[:25]
    batch2 = sample[25:]
    await score_chunks_batch(batch1)
    print(f"  Batch 1: {len(batch1)} done")
    await score_chunks_batch(batch2)
    print(f"  Batch 2: {len(batch2)} done")

    all_scored = batch1 + batch2
    scores = [c.get("semantic_score", 2) for c in all_scored]

    # Stats
    from collections import Counter
    dist = Counter(scores)
    complete = sum(1 for s in scores if s == 3)
    partial = sum(1 for s in scores if s == 2)
    broken = sum(1 for s in scores if s == 1)
    complete_rate = complete / len(scores) * 100

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"  Total sampled:       {len(scores)}")
    print(f"  Fully understandable: {complete} ({complete_rate:.0f}%)")
    print(f"  Partially:           {partial} ({partial/len(scores)*100:.0f}%)")
    print(f"  Broken:              {broken} ({broken/len(scores)*100:.0f}%)")
    print(f"  Score distribution:  {dict(dist)}")

    # Show worst chunks
    worst = [c for c in all_scored if c.get("semantic_score") == 1]
    if worst:
        print(f"\n  Worst chunks ({len(worst)}):")
        for c in worst[:3]:
            print(f"    [{c.get('source_file','?')[:30]}] {c.get('text','')[:120]}")

    decision = "START_P3" if complete_rate < 80 else "SKIP_P3"
    print(f"\n  [ACTION] Complete rate {complete_rate:.0f}% {'<' if complete_rate < 80 else '>='} 80% → {decision}")

    out = {
        "results": all_scored,
        "distribution": {str(k): v for k, v in dist.items()},
        "complete_rate": round(complete_rate, 1),
        "decision": decision,
    }
    out_file = OUTPUT_DIR / "chunk_diagnosis.json"
    out_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nSaved to {out_file}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
