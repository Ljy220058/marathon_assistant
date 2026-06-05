"""用重建后的 v2 索引重新建立标准问题集的片段对应关系。

对每条正例问题：
1. 用 question 原文在 v2 索引上检索 top-10
2. 文本相似度匹配 top-1 同文档片段 -> 自动赋值 reference_chunk_id
3. 收集同文档 top-5 片段 -> relevant_ids
4. 标记匹配质量（confidence 分三档：high/medium/needs_review）
"""

import json
import sys
import re
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / "src"))

from marathon_qa_assistant.services.vector_store import (
    load_vector_kb,
    retrieve,
    get_settings,
)

# 强制开启领域过滤，关闭多路变体以加快重映射速度（66 条 × 4 变体 = 264 次嵌入 → 66 次）
import os
os.environ["MARATHON_DOMAIN_FILTER_ENABLED"] = "1"
os.environ["MARATHON_RETRIEVAL_VARIANTS_ENABLED"] = "0"


def _text_overlap(a: str, b: str) -> float:
    """计算两段文本的字符级 Jaccard 重叠度。"""
    a_set = set(str(a or ""))
    b_set = set(str(b or ""))
    if not a_set or not b_set:
        return 0.0
    return len(a_set & b_set) / len(a_set | b_set)


def _find_best_match(ref_chunk: dict, hits: list[dict]) -> tuple[dict | None, float]:
    """在检索命中里找与参考片段最匹配的。"""
    ref_text = str(ref_chunk.get("text") or "")
    best_hit = None
    best_score = 0.0
    for hit in hits:
        hit_text = str(hit.get("text") or "")
        overlap = _text_overlap(ref_text[:300], hit_text[:300])
        if overlap > best_score:
            best_score = overlap
            best_hit = hit
    return best_hit, best_score


def main():
    base = Path(__file__).resolve().parents[1]
    vector_dir = base / "data" / "vector_kb" / "v2"
    eval_file = base / "eval_dataset_final.json"
    output_file = base / "eval_dataset_golden.json"

    print(f"加载 v2 索引: {vector_dir}")
    chunks, vectorizer, matrix, bm25 = load_vector_kb(vector_dir)
    chunk_lookup = {c["chunk_id"]: c for c in chunks if c.get("chunk_id")}

    print(f"加载评测集: {eval_file}")
    with open(eval_file, encoding="utf-8") as f:
        dataset = json.load(f)

    positives = [d for d in dataset if d.get("reference_chunk_id")]
    negatives = [d for d in dataset if not d.get("reference_chunk_id") and d.get("sample_type") in ("out_of_domain", "near_miss")]

    print(f"正例: {len(positives)}, 反例: {len(negatives)}")

    confirmed = 0
    corrected = 0
    needs_review = 0
    results = []

    for idx, item in enumerate(positives):
        question = item.get("question", "")
        domain = item.get("domain", "")
        old_ref_id = item.get("reference_chunk_id", "")

        # 检索 top-10
        hits = retrieve(question, chunks, vectorizer, matrix, top_k=10, bm25=bm25)

        # 找 top-5 同文档同领域片段作为 relevant_ids
        ref_chunk = chunk_lookup.get(old_ref_id, {})
        ref_source = ref_chunk.get("source_file", "")

        # 自动匹配：在 hits 中找与旧 reference 最相似的
        best_hit, best_overlap = _find_best_match(ref_chunk, hits) if ref_chunk else (None, 0.0)

        relevant_ids = []
        for hit in hits[:10]:
            hit_chunk = chunk_lookup.get(hit["chunk_id"], {})
            # 同文档或同领域
            if hit_chunk.get("source_file") == ref_source or (
                domain and domain in str(hit_chunk.get("domain_terms") or [])
            ):
                if hit["chunk_id"] not in relevant_ids:
                    relevant_ids.append(hit["chunk_id"])

        # 判定匹配质量
        new_ref_id = old_ref_id
        confidence = "medium"
        note = ""

        if best_hit and best_overlap > 0.6:
            # 找到了高重叠的新片段
            if best_hit["chunk_id"] != old_ref_id:
                new_ref_id = best_hit["chunk_id"]
                confidence = "high"
                note = f"自动修正: {old_ref_id} -> {new_ref_id} (重叠度={best_overlap:.2f})"
                corrected += 1
            else:
                confidence = "high"
                note = f"确认: 原 reference 在检索 top-10 中 (重叠度={best_overlap:.2f})"
                confirmed += 1
        elif best_hit and best_overlap > 0.3:
            if best_hit["chunk_id"] != old_ref_id:
                new_ref_id = best_hit["chunk_id"]
                confidence = "medium"
                note = f"中等匹配修正: {old_ref_id} -> {new_ref_id} (重叠度={best_overlap:.2f})"
                corrected += 1
            else:
                confidence = "medium"
                note = f"中等匹准确认 (重叠度={best_overlap:.2f})"
                confirmed += 1
        elif ref_chunk:
            # 在检索结果中找不到匹配
            confidence = "needs_review"
            note = f"未找到可靠匹配 (最佳重叠度={best_overlap:.2f})。旧 reference: {old_ref_id}"
            needs_review += 1
        else:
            confidence = "needs_review"
            note = "旧 reference_chunk_id 在索引中不存在"
            needs_review += 1

        result = dict(item)
        result["reference_chunk_id"] = new_ref_id
        result["relevant_ids"] = relevant_ids[:5]  # 最多 5 个
        result["_remap_confidence"] = confidence
        result["_remap_note"] = note
        results.append(result)

        if (idx + 1) % 10 == 0:
            print(f"  进度: {idx+1}/{len(positives)}")

    # 合并反例
    results.extend(negatives)

    # 输出
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n===== 重映射完成 =====")
    print(f"输出: {output_file}")
    print(f"总计: {len(results)} 条 (正例={len(positives)}, 反例={len(negatives)})")
    print(f"确认: {confirmed} 条")
    print(f"修正: {corrected} 条")
    print(f"待人工审查: {needs_review} 条")

    # 按领域统计
    domain_stats = Counter()
    for item in results:
        if item.get("_remap_confidence") == "needs_review":
            domain_stats[f"{item.get('domain','')}_待审查"] += 1
    print(f"\n待审查按领域分布:")
    for k, v in domain_stats.most_common():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
