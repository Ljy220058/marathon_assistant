from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "data" / "vector_kb" / "v2" / "eval_dataset.json"
DEFAULT_RAGAS = ROOT / "artifacts" / "research_runs" / "ragas_scores_v2.jsonl"
DEFAULT_RETRIEVAL = ROOT / "artifacts" / "research_runs" / "rag_eval_retrieval_only_baseline.json"
DEFAULT_REPORT = ROOT / "artifacts" / "research_runs" / "rag_eval_report.md"

METRIC_NAMES = ["context_precision", "faithfulness", "answer_relevancy", "context_recall"]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def summarize_scores(dataset_path: Path, ragas_path: Path) -> dict[str, Any]:
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    rows = _load_jsonl(ragas_path)
    latest_success: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []
    for row in rows:
        sample_id = str(row.get("id") or "")
        if row.get("error"):
            errors.append(row)
            continue
        if sample_id:
            latest_success[sample_id] = row

    missing_samples = [row["id"] for row in dataset if row["id"] not in latest_success]
    missing_metrics = []
    metric_values: dict[str, list[float]] = {name: [] for name in METRIC_NAMES}
    for sample_id, row in latest_success.items():
        scores = row.get("scores") or {}
        missing = [name for name in METRIC_NAMES if name not in scores]
        if missing:
            missing_metrics.append({"id": sample_id, "missing": missing})
        for name in METRIC_NAMES:
            if name in scores and scores[name] is not None:
                metric_values[name].append(float(scores[name]))

    metric_means = {
        name: mean(values) if values else None
        for name, values in metric_values.items()
    }
    metric_counts = {name: len(values) for name, values in metric_values.items()}
    backend_counts = Counter(str(row.get("retrieval_backend") or "unknown") for row in latest_success.values())

    return {
        "dataset_rows": len(dataset),
        "raw_rows": len(rows),
        "completed_rows": len(latest_success),
        "missing_samples": missing_samples,
        "error_rows": errors,
        "missing_metric_rows": missing_metrics,
        "metric_means": metric_means,
        "metric_counts": metric_counts,
        "retrieval_backend_counts": dict(sorted(backend_counts.items())),
    }


def update_report(report_path: Path, retrieval_path: Path, ragas_summary: dict[str, Any]) -> None:
    retrieval = json.loads(retrieval_path.read_text(encoding="utf-8"))
    rm = retrieval["retrieval_metrics"]
    qm = retrieval["retrieval_quality_metrics"]
    weak = retrieval["weak_recall_queries"]
    negatives = retrieval["negative_or_ood_queries_with_hits"]
    mismatches = retrieval["domain_mismatch_queries"]

    lines = [
        "# RAG 检索质量评测基线报告",
        "",
        "> 本报告基于 `data/vector_kb/v2/eval_dataset.json` 的 60 条标准样本生成。Retrieval-only 指标已全量完成；RAGAS 生成质量指标已完成 60 条样本，但部分早期行未记录检索后端，报告中单独列出该限制。",
        "",
        "## 1. 数据集概况",
        "",
        "- 样本数：60",
        "- 样本类型：49 positive，4 near_miss，4 negative，3 out_of_domain",
        "- 领域覆盖：training_protocol 20，nutrition 10，injury_safety 11，medical_safety 12，none 3（external_reference 已下线）",
        "- 引用完整性：`reference_chunk_id`、`relevant_ids`、`negative_candidate_ids` 均已验证指向真实 v2 chunk",
        "",
        "## 2. 检索指标基线",
        "",
        "| 指标类型 | 指标 | 数值 |",
        "|---|---:|---:|",
    ]
    for key in ("exact_chunk", "same_page", "same_source"):
        bucket = rm[key]
        lines.append(f"| {bucket['label']} | Recall@5 | {bucket['recall']:.4f} |")
        lines.append(f"| {bucket['label']} | MRR@5 | {bucket['mrr']:.4f} |")
        lines.append(f"| {bucket['label']} | MAP@5 | {bucket['map']:.4f} |")
    for name, value in qm.items():
        lines.append(f"| Retrieval-only | {name} | {value:.4f} |")

    lines.extend(
        [
            "",
            "## 3. RAGAS 生成质量基线",
            "",
            f"- 完成样本：{ragas_summary['completed_rows']}/{ragas_summary['dataset_rows']}",
            f"- 原始 JSONL 行数：{ragas_summary['raw_rows']}（包含历史错误行）",
            f"- 检索后端记录：{json.dumps(ragas_summary['retrieval_backend_counts'], ensure_ascii=False)}",
            "",
            "| 指标 | 均值 | 有效样本数 |",
            "|---|---:|---:|",
        ]
    )
    for name in METRIC_NAMES:
        value = ragas_summary["metric_means"][name]
        formatted = "NA" if value is None else f"{value:.4f}"
        lines.append(f"| {name} | {formatted} | {ragas_summary['metric_counts'][name]} |")

    if ragas_summary["missing_metric_rows"]:
        lines.extend(["", "### 3.1 缺失单项指标", ""])
        for row in ragas_summary["missing_metric_rows"]:
            lines.append(f"- `{row['id']}`：缺失 {', '.join(row['missing'])}")
    if ragas_summary["error_rows"]:
        lines.extend(["", "### 3.2 历史错误行", ""])
        for row in ragas_summary["error_rows"]:
            lines.append(f"- `{row.get('id')}`：{row.get('error')}")

    lines.extend(
        [
            "",
            "## 4. 已知问题清单",
            "",
            f"### 4.1 Recall@5 未命中的正例/边界样例（{len(weak)} 条）",
            "",
        ]
    )
    for row in weak[:20]:
        lines.append(
            f"- `{row['id']}`：{row['question']}；期望领域 `{row['expected_domain']}`；"
            f"参考 `{row['reference_chunk_id']}`；Top-5 `{', '.join(row['retrieved_ids'][:5]) or '<empty>'}`"
        )
    if len(weak) > 20:
        lines.append(f"- 其余 {len(weak) - 20} 条见 `rag_eval_retrieval_only_baseline.json`。")

    lines.extend(["", f"### 4.2 负例/领域外查询仍有召回（{len(negatives)} 条）", ""])
    for row in negatives:
        lines.append(
            f"- `{row['id']}`（{row['sample_type']}）：{row['question']}；"
            f"Top-5 `{', '.join(row['retrieved_ids'][:5]) or '<empty>'}`"
        )

    lines.extend(["", f"### 4.3 领域错配查询（{len(mismatches)} 条）", ""])
    for row in mismatches[:20]:
        lines.append(
            f"- `{row['id']}`：期望 `{row['expected_domain']}`；"
            f"错配 `{', '.join(row['domain_mismatch_ids'][:5])}`"
        )
    if len(mismatches) > 20:
        lines.append(f"- 其余 {len(mismatches) - 20} 条见 `rag_eval_retrieval_only_baseline.json`。")

    lines.extend(
        [
            "",
            "## 5. 后续改进方向",
            "",
            "- 优先分析 internal_hmp_protocol_pilot / norway_method 对训练类查询的强召回，以及 out_of_domain 查询未被拒召的问题。",
            "- 修复 FAISS 加载稳定性后，建议用 `tools/kb/run_ragas_eval_batch.py --rerun` 重新生成一版后端一致的 RAGAS 分数。",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize v2 RAGAS JSONL scores and update the baseline report.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--ragas", default=str(DEFAULT_RAGAS))
    parser.add_argument("--retrieval", default=str(DEFAULT_RETRIEVAL))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    summary = summarize_scores(Path(args.dataset), Path(args.ragas))
    update_report(Path(args.report), Path(args.retrieval), summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
