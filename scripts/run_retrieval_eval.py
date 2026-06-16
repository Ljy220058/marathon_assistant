"""
完整检索评测脚本。

输入：eval_dataset_golden.json（或 eval_dataset_final.json）
输出：六项指标 + 按领域细分 + 分数分布分析

指标：
- recall@5（精确片段、同页、同文档三档）
- precision@5
- mrr（平均倒数排名）
- negative_hit_rate（反例命中率）
- domain_mismatch_rate（领域错配率）
- unsafe_retrieval_rate（不安全检索率）
"""

import json
import sys
import os
import statistics
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / "src"))

from marathon_qa_assistant.services.vector_store import (
    load_vector_kb,
    load_sharded_kb,
    retrieve,
    extract_semantic_terms,
)

# 领域过滤开关（分库模式下自动生效）
os.environ["MARATHON_DOMAIN_FILTER_ENABLED"] = os.environ.get(
    "MARATHON_DOMAIN_FILTER_ENABLED", "1"
)


def compute_metrics(dataset: list[dict], chunks, vectorizer, matrix, bm25, top_k: int = 5) -> dict:
    """计算六项检索指标。chunks 可以是 list[dict]（统一索引）或 dict[str, list[dict]]（分库索引）。"""
    positives = [d for d in dataset if d.get("reference_chunk_id")]
    negatives = [d for d in dataset if d.get("sample_type") in ("out_of_domain", "near_miss") and not d.get("reference_chunk_id")]

    # 统一 chunks 格式构建 lookup
    if isinstance(chunks, dict):
        flat_chunks = [c for clist in chunks.values() for c in clist]
    else:
        flat_chunks = chunks
    chunk_lookup = {c["chunk_id"]: c for c in flat_chunks if c.get("chunk_id")}

    # --- 正例评测 ---
    exact_matches = 0        # relevant_ids 宽松命中
    strict_exact_matches = 0 # ref_id 严格命中
    same_page_matches = 0
    same_source_matches = 0
    reciprocal_ranks = []
    precision_scores = []
    domain_mismatches = 0
    total_domain_hits = 0

    per_domain_exact = defaultdict(lambda: {"hits": 0, "total": 0})
    per_domain_recall = defaultdict(lambda: {"hits": 0, "total": 0})

    for item in positives:
        question = item.get("question", "")
        ref_id = item.get("reference_chunk_id", "")
        query_domain = item.get("domain", "")
        relevant_ids = item.get("relevant_ids", [ref_id] if ref_id else [])

        hits = retrieve(question, chunks, vectorizer, matrix, top_k=top_k, bm25=bm25)
        hit_ids = [h["chunk_id"] for h in hits]

        ref_chunk = chunk_lookup.get(ref_id, {})
        ref_source = ref_chunk.get("source_file", "")
        ref_page = ref_chunk.get("page", 0)

        # 精确片段召回（relevant_ids：多 chunk 至少命中一个即算成功）
        if any(rid in hit_ids for rid in relevant_ids if rid):
            exact_matches += 1
        # 严格精确召回（只认 reference_chunk_id，保持向后兼容）
        if ref_id and ref_id in hit_ids:
            strict_exact_matches += 1

        # 同页召回
        for h in hits:
            hc = chunk_lookup.get(h["chunk_id"], {})
            if hc.get("source_file") == ref_source and hc.get("page") == ref_page:
                same_page_matches += 1
                break

        # 同文档召回（旧方式：top-5 中任意 hit 的 source_file 与参考片段相同即算命中）
        source_match = False
        for h in hits:
            if h.get("source_file") == ref_source:
                source_match = True
                break
        if source_match:
            same_source_matches += 1

        # 同文档召回（relevant_ids 方式：精确命中 relevant_ids 中的任意一个）
        relevant_match = any(rid in hit_ids for rid in relevant_ids if rid)

        # MRR：第一个 relevant 的排名倒数
        rr = 0.0
        for rank, hid in enumerate(hit_ids, 1):
            if hid in relevant_ids or hid == ref_id:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)

        # Precision@K：hits 中有多少是 relevant 的
        relevant_hit_count = sum(1 for hid in hit_ids if hid in relevant_ids or hid == ref_id)
        precision_scores.append(relevant_hit_count / max(1, len(hit_ids)))

        # 领域错配：统计 top-K 中有领域标签但与 query domain 不匹配的 hit 占比
        if query_domain:
            total_labeled = 0
            mismatched = 0
            for h in hits:
                hit_domain_raw = h.get("domain_terms") or []
                if isinstance(hit_domain_raw, list):
                    hit_domains = set(hit_domain_raw)
                else:
                    hit_domains = set(str(hit_domain_raw).replace("[", "").replace("]", "").replace("'", "").replace('"', "").split(","))
                if hit_domains:
                    total_labeled += 1
                    if not any(d.strip() in query_domain for d in hit_domains if d.strip()):
                        mismatched += 1
            domain_mismatches += mismatched
            total_domain_hits += total_labeled

        # 按领域统计（relevant_ids 宽松命中）
        if query_domain:
            per_domain_exact[query_domain]["total"] += 1
            if any(rid in hit_ids for rid in relevant_ids if rid):
                per_domain_exact[query_domain]["hits"] += 1
            per_domain_recall[query_domain]["total"] += 1
            # 宽松召回：同源文件命中
            if source_match:
                per_domain_recall[query_domain]["hits"] += 1

    n_pos = len(positives)
    n_neg = len(negatives)

    # --- 反例评测 ---
    neg_hit_count = 0
    out_of_domain_hits = 0
    near_miss_hits = 0
    unsafe_hits = 0

    for item in negatives:
        question = item.get("question", "")
        sample_type = item.get("sample_type", "")
        hits = retrieve(question, chunks, vectorizer, matrix, top_k=top_k, bm25=bm25)

        if hits:
            neg_hit_count += 1
            if sample_type == "out_of_domain":
                out_of_domain_hits += 1
            else:
                near_miss_hits += 1

            # 安全检查：医疗类查询命中的片段是否包含处方级内容
            if sample_type == "near_miss":
                query_terms = extract_semantic_terms(question)
                query_domains = set(query_terms.get("domain_terms") or [])
                if "medical_safety" in query_domains:
                    for h in hits:
                        if h.get("prescription_permission") == "core_prescription" or h.get("allowed_use") == "core_prescription":
                            unsafe_hits += 1
                            break

    # --- 分数分布 ---
    all_scores = []
    for item in positives:
        hits = retrieve(item["question"], chunks, vectorizer, matrix, top_k=top_k, bm25=bm25)
        for h in hits:
            all_scores.append(float(h.get("score") or 0))

    all_neg_scores = []
    for item in negatives:
        hits = retrieve(item["question"], chunks, vectorizer, matrix, top_k=top_k, bm25=bm25)
        for h in hits:
            all_neg_scores.append(float(h.get("score") or 0))

    return {
        "eval_config": {
            "top_k": top_k,
            "domain_filter_enabled": os.environ.get("MARATHON_DOMAIN_FILTER_ENABLED", "1") == "1",
            "positive_count": n_pos,
            "negative_count": n_neg,
        },
        "metrics": {
            "exact_chunk_recall": {"hits": exact_matches, "total": n_pos, "rate": round(exact_matches / max(1, n_pos), 4)},
            "exact_chunk_recall_strict": {"hits": strict_exact_matches, "total": n_pos, "rate": round(strict_exact_matches / max(1, n_pos), 4), "note": "仅 ref_id 命中，旧指标（向后兼容）"},
            "same_page_recall": {"hits": same_page_matches, "total": n_pos, "rate": round(same_page_matches / max(1, n_pos), 4)},
            "same_source_recall": {"hits": same_source_matches, "total": n_pos, "rate": round(same_source_matches / max(1, n_pos), 4)},
            "mrr": round(statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0.0, 4),
            "mrr_values": reciprocal_ranks,
            "precision_at_k": round(statistics.mean(precision_scores) if precision_scores else 0.0, 4),
            "precision_values": precision_scores,
            "negative_hit_rate": {
                "hits": neg_hit_count,
                "total": n_neg,
                "rate": round(neg_hit_count / max(1, n_neg), 4),
                "out_of_domain_hits": out_of_domain_hits,
                "near_miss_hits": near_miss_hits,
            },
            "domain_mismatch_rate": {
                "mismatched_hits": domain_mismatches,
                "total_labeled_hits": total_domain_hits,
                "rate": round(domain_mismatches / max(1, total_domain_hits), 4),
            },
            "unsafe_retrieval_rate": {
                "unsafe": unsafe_hits,
                "total_medical_near_miss": sum(1 for d in negatives if d.get("sample_type") == "near_miss"),
                "rate": round(unsafe_hits / max(1, sum(1 for d in negatives if d.get("sample_type") == "near_miss")), 4),
            },
        },
        "score_distribution": {
            "positive": {
                "mean": round(statistics.mean(all_scores), 4) if all_scores else 0,
                "median": round(statistics.median(all_scores), 4) if all_scores else 0,
                "stdev": round(statistics.stdev(all_scores), 4) if len(all_scores) >= 2 else 0,
                "min": round(min(all_scores), 4) if all_scores else 0,
                "max": round(max(all_scores), 4) if all_scores else 0,
                "bandwidth": round(max(all_scores) - min(all_scores), 4) if len(all_scores) >= 2 else 0,
            },
            "negative": {
                "mean": round(statistics.mean(all_neg_scores), 4) if all_neg_scores else 0,
                "median": round(statistics.median(all_neg_scores), 4) if all_neg_scores else 0,
                "stdev": round(statistics.stdev(all_neg_scores), 4) if len(all_neg_scores) >= 2 else 0,
                "min": round(min(all_neg_scores), 4) if all_neg_scores else 0,
                "max": round(max(all_neg_scores), 4) if all_neg_scores else 0,
            },
        },
        "per_domain_exact_recall": {
            domain: {"hits": stats["hits"], "total": stats["total"], "rate": round(stats["hits"] / max(1, stats["total"]), 4)}
            for domain, stats in per_domain_exact.items()
        },
        "per_domain_loose_recall": {
            domain: {"hits": stats["hits"], "total": stats["total"], "rate": round(stats["hits"] / max(1, stats["total"]), 4)}
            for domain, stats in per_domain_recall.items()
        },
    }


def print_report(metrics: dict) -> None:
    """格式化打印评测报告。"""
    cfg = metrics["eval_config"]
    m = metrics["metrics"]
    sd = metrics["score_distribution"]

    print("=" * 60)
    print("检索质量评测报告 (v2, 领域过滤已开启)")
    print("=" * 60)
    print(f"配置: top_k={cfg['top_k']}, domain_filter={cfg['domain_filter_enabled']}")
    print(f"正例: {cfg['positive_count']}, 反例/边界: {cfg['negative_count']}")
    print()

    print(f"{'指标':<24} {'命中':>8}  {'得分':>10}")
    print("-" * 42)
    exact = m['exact_chunk_recall']
    exact_strict = m.get('exact_chunk_recall_strict', {})
    print(f"{'精确片段召回@5 (relevant)':<30} {exact['hits']:>3}/{exact['total']:>3}  {exact['rate']:>9.1%}")
    if exact_strict:
        print(f"{'  其中严格 (ref_id only)':<30} {exact_strict['hits']:>3}/{exact_strict['total']:>3}  {exact_strict['rate']:>9.1%}")
    print(f"{'同页召回@5':<24} {m['same_page_recall']['hits']:>3}/{m['same_page_recall']['total']:>3}  {m['same_page_recall']['rate']:>9.1%}")
    print(f"{'同文档召回@5':<24} {m['same_source_recall']['hits']:>3}/{m['same_source_recall']['total']:>3}  {m['same_source_recall']['rate']:>9.1%}")
    print(f"{'MRR':<24} {'':>8}  {m['mrr']:>10.4f}")
    print(f"{'Precision@5':<24} {'':>8}  {m['precision_at_k']:>10.4f}")

    nhr = m["negative_hit_rate"]
    print(f"{'反例命中率':<24} {nhr['hits']:>3}/{nhr['total']:>3}  {nhr['rate']:>9.1%} (越低越好)")
    print(f"  领域外查询命中: {nhr['out_of_domain_hits']}")
    print(f"  边界查询命中: {nhr['near_miss_hits']}")

    dmr = m["domain_mismatch_rate"]
    print(f"{'领域错配率':<24} {dmr['mismatched_hits']:>3}/{dmr['total_labeled_hits']:>3}  {dmr['rate']:>9.1%} (有标签hit中不匹配占比，越低越好)")

    usr = m["unsafe_retrieval_rate"]
    print(f"{'不安全检索率':<24} {usr['unsafe']:>3}/{usr['total_medical_near_miss']:>3}  {usr['rate']:>9.1%} (越低越好)")

    print()
    print("分数分布:")
    print(f"  正例: 均值={sd['positive']['mean']:.4f} 中位={sd['positive']['median']:.4f} 带宽={sd['positive']['bandwidth']:.4f}")
    print(f"  反例: 均值={sd['negative']['mean']:.4f} 中位={sd['negative']['median']:.4f}")

    print()
    print("按领域精确召回 (relevant_ids):")
    for domain, stats in metrics.get("per_domain_exact_recall", {}).items():
        print(f"  {domain}: {stats['hits']}/{stats['total']} = {stats['rate']:.1%}")

    print()
    print("按领域宽松召回 (relevant_ids):")
    for domain, stats in metrics.get("per_domain_loose_recall", {}).items():
        print(f"  {domain}: {stats['hits']}/{stats['total']} = {stats['rate']:.1%}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="检索质量评测")
    parser.add_argument("--dataset", default="eval_dataset_golden.json",
                        help="评测集文件 (默认: eval_dataset_golden.json)")
    parser.add_argument("--vector-dir", default="data/vector_kb/v2",
                        help="向量库目录 (默认: data/vector_kb/v2)")
    parser.add_argument("--top-k", type=int, default=5,
                        help="检索 top-K (默认: 5)")
    parser.add_argument("--output", default="artifacts/retrieval_baseline_v2.json",
                        help="输出报告路径")
    parser.add_argument("--no-domain-filter", action="store_true",
                        help="关闭领域过滤")
    parser.add_argument("--sharded", action="store_true",
                        help="使用分库检索模式")
    parser.add_argument("--shard-dir", default="data/vector_kb/v2_sharded",
                        help="分库检索的目录 (默认: data/vector_kb/v2_sharded)")
    args = parser.parse_args()

    base = Path(__file__).resolve().parents[1]
    vector_dir = base / args.vector_dir
    dataset_file = base / args.dataset
    output_file = base / args.output

    # 领域过滤
    if args.no_domain_filter:
        os.environ["MARATHON_DOMAIN_FILTER_ENABLED"] = "0"

    # 分库模式
    if args.sharded:
        os.environ["MARATHON_SHARDED_RETRIEVAL_ENABLED"] = "1"
        shard_base = base / args.shard_dir
        print(f"加载分库索引: {shard_base}")
        shard_stores, shard_chunks, all_chunks, shard_bm25, _ = load_sharded_kb(shard_base)
        chunks = shard_chunks  # 分库 chunks dict
        vectorizer = "sharded"
        matrix = shard_stores
        bm25 = shard_bm25  # 分库 BM25 dict
    else:
        print(f"加载 v2 索引: {vector_dir}")
        chunks, vectorizer, matrix, bm25 = load_vector_kb(vector_dir)

    print(f"加载评测集: {dataset_file}")
    if not dataset_file.exists():
        # 回退到 eval_dataset_final.json
        dataset_file = base / "eval_dataset_final.json"
        print(f"  未找到，回退到: {dataset_file}")
    with open(dataset_file, encoding="utf-8") as f:
        dataset = json.load(f)

    mode = "sharded" if args.sharded else "unified"
    print(f"运行评测 (top_k={args.top_k}, mode={mode}, domain_filter={os.environ.get('MARATHON_DOMAIN_FILTER_ENABLED','1')})...")
    metrics = compute_metrics(dataset, chunks, vectorizer, matrix, bm25, top_k=args.top_k)

    print_report(metrics)

    # 保存
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {output_file}")


if __name__ == "__main__":
    main()
