import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Iterable

import pandas as pd
from dotenv import load_dotenv
from langchain_ollama import ChatOllama, OllamaEmbeddings

try:
    from ragas.run_config import RunConfig
except ImportError:
    RunConfig = None

PROJECT_ROOT = Path(__file__).absolute().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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


def build_ragas_metrics():
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

    for res in retrieval_results:
        target = res["ref_id"]
        retrieved = res["retrieved_ids"]

        for mode, bucket in totals.items():
            rank = _find_match_rank(target, retrieved, chunk_lookup, mode)
            if rank is None:
                continue
            bucket["recall_sum"] += 1.0
            bucket["mrr_sum"] += 1.0 / rank
            bucket["map_sum"] += 1.0 / rank

    count = len(retrieval_results) or 1
    return {
        mode: {
            "label": bucket["label"],
            "recall": bucket["recall_sum"] / count,
            "mrr": bucket["mrr_sum"] / count,
            "map": bucket["map_sum"] / count,
        }
        for mode, bucket in totals.items()
    }

async def run_evaluation():
    Dataset, evaluate, metrics = build_ragas_metrics()
    metric_names = _metric_names(metrics)

    # 1. 加载向量库
    vector_dir = base_dir / "vector_kb"
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
            "retrieved_ids": retrieved_ids
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
    for metric_name, score in ragas_scores.items():
        print(f"- {metric_name}: {score:.4f}")
    print("="*30)
    
    # 保存详细报告
    report_path = base_dir / "rag_eval_report.md"
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
        for metric_name, score in ragas_scores.items():
            f.write(f"| Ragas | {metric_name} | {score:.4f} |\n")
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
    asyncio.run(run_evaluation())
