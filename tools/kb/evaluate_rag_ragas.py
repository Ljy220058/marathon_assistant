import asyncio
import argparse
import json
import os
import sys
import types
from pathlib import Path
from typing import Dict, Iterable

import pandas as pd
from dotenv import load_dotenv
from langchain_ollama import ChatOllama, OllamaEmbeddings

try:
    from ragas.run_config import RunConfig
except ImportError:
    RunConfig = None

def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (candidate / ".git").exists() and (candidate / "apps").exists():
            return candidate
    return Path.cwd().resolve()


PROJECT_ROOT = _find_project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_SRC = PROJECT_ROOT / "apps" / "backend" / "src"
if BACKEND_SRC.exists() and str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from marathon_qa_assistant.services.vector_store import load_vector_kb, retrieve

# 加载配置
base_dir = PROJECT_ROOT
env_path = base_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:latest")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", OLLAMA_MODEL)

# 初始化 LLM
llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)
embeddings = OllamaEmbeddings(model=OLLAMA_EMBED_MODEL, base_url=OLLAMA_BASE_URL)
DEFAULT_VECTOR_DIR = base_dir / "data" / "vector_kb" / "v2"


def _install_ragas_legacy_import_shims() -> None:
    """Keep ragas 0.2.x importable with the current LangChain packages."""

    module_name = "langchain_community.chat_models.vertexai"
    if module_name in sys.modules:
        return

    try:
        __import__(module_name)
        return
    except ModuleNotFoundError:
        pass

    module = types.ModuleType(module_name)

    class ChatVertexAI:  # pragma: no cover - compatibility placeholder only
        pass

    module.ChatVertexAI = ChatVertexAI
    sys.modules[module_name] = module


def build_ragas_metrics():
    _install_ragas_legacy_import_shims()
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics._answer_relevance import answer_relevancy
        from ragas.metrics._context_precision import context_precision
        from ragas.metrics._context_recall import context_recall
        from ragas.metrics._faithfulness import faithfulness
    except ImportError as exc:
        raise RuntimeError(
            "运行 RAG 评测前请先安装额外依赖：pip install datasets ragas"
        ) from exc

    # ragas 0.4.x 的 evaluate() 仍要求 legacy Metric 实例。
    metrics = [context_precision, faithfulness, answer_relevancy, context_recall]
    return Dataset, evaluate, metrics


def _metric_names(metrics: Iterable[object]) -> list[str]:
    return [metric.name for metric in metrics]


def _summarize_scores(result, allowed_metrics: Iterable[str]) -> Dict[str, float]:
    allowed_metric_names = set(allowed_metrics)
    if hasattr(result, "to_pandas"):
        df = result.to_pandas()
        summary: Dict[str, float] = {}
        for column in df.columns:
            if column not in allowed_metric_names:
                continue
            series = pd.to_numeric(df[column], errors="coerce").dropna()
            if not series.empty:
                summary[column] = float(series.mean())
        return summary
    return {
        key: float(value)
        for key, value in result.items()
        if key in allowed_metric_names
    }


def _build_chunk_lookup(chunks: list[dict]) -> Dict[str, dict]:
    return {chunk["chunk_id"]: chunk for chunk in chunks if chunk.get("chunk_id")}


def _find_match_rank(
    target_id: str,
    retrieved_ids: list[str],
    chunk_lookup: Dict[str, dict],
    mode: str,
) -> int | None:
    if mode == "exact_chunk":
        return retrieved_ids.index(target_id) + 1 if target_id in retrieved_ids else None

    target_chunk = chunk_lookup.get(target_id)
    if not target_chunk:
        return None

    target_source = target_chunk.get("source_file")
    target_page = target_chunk.get("page")

    for rank, candidate_id in enumerate(retrieved_ids, start=1):
        candidate_chunk = chunk_lookup.get(candidate_id)
        if not candidate_chunk:
            continue

        same_source = candidate_chunk.get("source_file") == target_source
        same_page = same_source and candidate_chunk.get("page") == target_page

        if mode == "same_page" and same_page:
            return rank
        if mode == "same_source" and same_source:
            return rank
    return None


def _compute_retrieval_metrics(
    retrieval_results: list[dict],
    chunk_lookup: Dict[str, dict],
) -> Dict[str, Dict[str, float]]:
    metric_defs = {
        "exact_chunk": "精确块命中",
        "same_page": "同页命中",
        "same_source": "同文档命中",
    }
    totals = {
        key: {"label": label, "recall_sum": 0.0, "mrr_sum": 0.0, "map_sum": 0.0}
        for key, label in metric_defs.items()
    }

    evaluated_results = [
        res
        for res in retrieval_results
        if str(res.get("sample_type") or "positive") not in {"negative", "out_of_domain"}
    ]

    for res in evaluated_results:
        target = res.get("ref_id") or ""
        retrieved = list(res.get("retrieved_ids") or [])

        for mode, bucket in totals.items():
            rank = _find_match_rank(target, retrieved, chunk_lookup, mode)
            if rank is None:
                continue
            bucket["recall_sum"] += 1.0
            bucket["mrr_sum"] += 1.0 / rank
            bucket["map_sum"] += 1.0 / rank

    count = len(evaluated_results) or 1
    return {
        mode: {
            "label": bucket["label"],
            "recall": bucket["recall_sum"] / count,
            "mrr": bucket["mrr_sum"] / count,
            "map": bucket["map_sum"] / count,
        }
        for mode, bucket in totals.items()
    }


def _compute_retrieval_quality_metrics(
    retrieval_results: list[dict],
    chunk_lookup: Dict[str, dict],
    *,
    k: int = 5,
) -> Dict[str, float]:
    positives = [res for res in retrieval_results if str(res.get("sample_type") or "positive") in {"positive", "near_miss"}]
    negatives = [res for res in retrieval_results if str(res.get("sample_type") or "") in {"negative", "out_of_domain"}]
    positive_count = len(positives) or 1
    negative_count = len(negatives) or 1

    recall_hits = 0
    precision_sum = 0.0
    mrr_sum = 0.0
    domain_mismatch_hits = 0
    unsafe_hits = 0

    for res in positives:
        target = str(res.get("ref_id") or "")
        retrieved = list(res.get("retrieved_ids") or [])[:k]
        expected_domain = str(res.get("expected_domain") or "").strip()
        relevant_ids = set(str(item) for item in (res.get("relevant_ids") or []) if str(item).strip())
        if target:
            relevant_ids.add(target)

        relevant_ranks = [rank for rank, item_id in enumerate(retrieved, start=1) if item_id in relevant_ids]
        if relevant_ranks:
            recall_hits += 1
            mrr_sum += 1.0 / relevant_ranks[0]
        precision_sum += len(relevant_ranks) / max(1, min(k, len(retrieved) or k))

        if expected_domain:
            for item_id in retrieved:
                chunk = chunk_lookup.get(item_id) or {}
                domains = {
                    str(chunk.get(key) or "").strip()
                    for key in ("domain_pack", "evidence_domain", "knowledge_layer")
                    if str(chunk.get(key) or "").strip()
                }
                domains.update(str(item).strip() for item in (chunk.get("domain_terms") or []) if str(item).strip())
                if domains and expected_domain not in domains:
                    domain_mismatch_hits += 1
                    break

    for res in negatives:
        retrieved = list(res.get("retrieved_ids") or [])[:k]
        if retrieved:
            unsafe_or_core = False
            for item_id in retrieved:
                chunk = chunk_lookup.get(item_id) or {}
                permission = str(chunk.get("prescription_permission") or "")
                allowed_use = str(chunk.get("allowed_use") or "")
                domain = str(chunk.get("evidence_domain") or chunk.get("domain_pack") or "")
                if permission == "can_write_core" or allowed_use == "core_prescription" or domain in {"medical_safety", "medical_risk"}:
                    unsafe_or_core = True
                    break
            if unsafe_or_core:
                unsafe_hits += 1

    negative_hit_count = sum(1 for res in negatives if list(res.get("retrieved_ids") or [])[:k])
    return {
        f"recall@{k}": recall_hits / positive_count,
        f"precision@{k}": precision_sum / positive_count,
        "mrr": mrr_sum / positive_count,
        "negative_hit_rate": negative_hit_count / negative_count if negatives else 0.0,
        "domain_mismatch_rate": domain_mismatch_hits / positive_count,
        "unsafe_retrieval_rate": unsafe_hits / negative_count if negatives else 0.0,
    }

async def run_evaluation(vector_dir: Path | None = None):
    Dataset, evaluate, metrics = build_ragas_metrics()
    metric_names = _metric_names(metrics)

    # 1. 加载向量库
    vector_dir = Path(vector_dir or DEFAULT_VECTOR_DIR)
    chunks, vectorizer, matrix, bm25 = load_vector_kb(vector_dir)
    chunk_lookup = _build_chunk_lookup(chunks)
    
    # 2. 加载评估数据集
    eval_file = vector_dir / "eval_dataset.json"
    if not eval_file.exists():
        print("请先运行 generate_eval_dataset.py 生成数据集")
        return
    
    with open(eval_file, "r", encoding="utf-8") as f:
        dataset_raw = json.load(f)

    # 3. 收集 RAG 运行结果
    print(f"开始运行 RAG 管道评估，共 {len(dataset_raw)} 条数据...")
    
    data = {
        "question": [],
        "contexts": [],
        "answer": [],
        "ground_truth": [],
        "reference_chunk_id": []
    }
    
    retrieval_results = [] # 用于计算 MRR/MAP

    for item in dataset_raw:
        question = item["question"]
        ground_truth = item["ground_truth"]
        ref_id = item["reference_chunk_id"]
        
        # 检索
        hits = retrieve(question, chunks, vectorizer, matrix, top_k=5, bm25=bm25)
        contexts = [h["text"] for h in hits]
        retrieved_ids = [h["chunk_id"] for h in hits]
        
        # 生成回答
        context_str = "\n".join(contexts)
        prompt = f"请根据以下背景信息回答问题：\n\n背景：\n{context_str}\n\n问题：\n{question}"
        response = await llm.ainvoke(prompt)
        answer = response.content
        
        data["question"].append(question)
        data["contexts"].append(contexts)
        data["answer"].append(answer)
        data["ground_truth"].append(ground_truth)
        data["reference_chunk_id"].append(ref_id)
        
        retrieval_results.append({
            "ref_id": ref_id,
            "retrieved_ids": retrieved_ids,
            "relevant_ids": list(item.get("relevant_ids") or []),
            "expected_domain": str(item.get("expected_domain") or ""),
            "sample_type": str(item.get("sample_type") or "positive"),
        })

    # 4. 计算 Ragas 指标
    print("正在使用 Ragas 计算指标 (LLM-as-a-judge)...")
    if RunConfig is None:
        raise RuntimeError("运行 RAGAS 指标前请先安装额外依赖：pip install ragas")
    dataset = Dataset.from_dict({
        "question": data["question"],
        "contexts": data["contexts"],
        "answer": data["answer"],
        "ground_truth": data["ground_truth"]
    })
    
    result = evaluate(
        dataset,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
        run_config=RunConfig(timeout=120),
        batch_size=1,
    )
    
    df_ragas = result.to_pandas()
    ragas_scores = _summarize_scores(result, metric_names)
    
    # 5. 计算传统检索指标 (Recall@K, MRR, MAP)
    print("正在计算传统检索指标...")
    retrieval_metrics = _compute_retrieval_metrics(retrieval_results, chunk_lookup)
    retrieval_quality_metrics = _compute_retrieval_quality_metrics(retrieval_results, chunk_lookup, k=5)
    
    # 6. 生成报告
    print("\n" + "="*30)
    print("RAG 评估报告 (MarathonCoach)")
    print("="*30)
    print(f"传统检索指标 (Top-5):")
    for metrics_key in ("exact_chunk", "same_page", "same_source"):
        bucket = retrieval_metrics[metrics_key]
        print(f"- {bucket['label']}:")
        print(f"  Recall@5: {bucket['recall']:.4f}")
        print(f"  MRR@5:    {bucket['mrr']:.4f}")
        print(f"  MAP@5:    {bucket['map']:.4f}")
    print("-" * 20)
    print(f"Ragas 自动评估指标:")
    print("Retrieval-only quality metrics:")
    for metric_name, score in retrieval_quality_metrics.items():
        print(f"- {metric_name}: {score:.4f}")
    print("-" * 20)
    for metric_name, score in ragas_scores.items():
        print(f"- {metric_name}: {score:.4f}")
    print("="*30)
    
    # 保存详细报告
    report_path = base_dir / "artifacts" / "research_runs" / "rag_eval_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# RAG 评估实验报告\n\n")
        f.write("## 1. 核心指标汇总\n\n")
        f.write("| 指标类型 | 指标名称 | 分值 |\n")
        f.write("| :--- | :--- | :--- |\n")
        for metrics_key in ("exact_chunk", "same_page", "same_source"):
            bucket = retrieval_metrics[metrics_key]
            f.write(f"| 传统检索 | {bucket['label']} Recall@5 | {bucket['recall']:.4f} |\n")
            f.write(f"| 传统检索 | {bucket['label']} MRR@5 | {bucket['mrr']:.4f} |\n")
            f.write(f"| 传统检索 | {bucket['label']} MAP@5 | {bucket['map']:.4f} |\n")
        for metric_name, score in retrieval_quality_metrics.items():
            f.write(f"| Retrieval-only | {metric_name} | {score:.4f} |\n")
        for metric_name, score in ragas_scores.items():
            f.write(f"| Generation/Ragas | {metric_name} | {score:.4f} |\n")
        f.write("\n传统检索指标口径说明：`精确块命中` 要求命中同一 `chunk_id`；`同页命中` 允许命中同一文档同一页的相邻块；`同文档命中` 只要求命中同一 `source_file`。\n")
        
        f.write("\n## 2. 详细数据样本 (Top 3)\n\n")
        for i in range(min(3, len(dataset_raw), len(df_ragas))):
            f.write(f"### 样本 {i+1}\n")
            f.write(f"**问题**: {data['question'][i]}\n\n")
            first_context = data["contexts"][i][0][:200] + "..." if data["contexts"][i] else "无检索上下文"
            f.write(f"**检索上下文 (片段 1)**: {first_context}\n\n")
            f.write(f"**系统回答**: {data['answer'][i]}\n\n")
            f.write(f"**标准答案**: {data['ground_truth'][i]}\n\n")
            f.write("---\n")
            
    print(f"详细报告已生成至: {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Marathon Assistant RAG evaluation.")
    parser.add_argument("--vector-dir", default=str(DEFAULT_VECTOR_DIR))
    args = parser.parse_args()
    asyncio.run(run_evaluation(Path(args.vector_dir)))
