import os
import json
import asyncio
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from datasets import Dataset
from openai import AsyncOpenAI

# Ragas imports
from ragas import evaluate
from ragas.metrics.collections import (
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)
from ragas.llms import llm_factory
from ragas.embeddings.base import embedding_factory

# Internal imports
from langchain_ollama import ChatOllama, OllamaEmbeddings
from build_vector_kb import load_vector_kb, retrieve

# 加载配置
base_dir = Path(__file__).parent.resolve()
env_path = base_dir / "graphrag_project" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:latest")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", OLLAMA_MODEL)

# 初始化 LLM 和 Embeddings
llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)
embeddings = OllamaEmbeddings(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)

# Ragas collections 需要 modern 接口，这里改为走 Ollama 的 OpenAI 兼容端点
ragas_client = AsyncOpenAI(
    base_url=f"{OLLAMA_BASE_URL.rstrip('/')}/v1",
    api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
)
ragas_llm = llm_factory(OLLAMA_MODEL, client=ragas_client, provider="openai")
ragas_emb = embedding_factory(
    provider="openai",
    model=OLLAMA_EMBED_MODEL,
    client=ragas_client,
    interface="modern",
)

# 配置 Ragas 指标使用新版 collections
metrics = [
    ContextPrecision(llm=ragas_llm),
    Faithfulness(llm=ragas_llm),
    AnswerRelevancy(llm=ragas_llm, embeddings=ragas_emb),
    ContextRecall(llm=ragas_llm),
]

async def run_evaluation():
    # 1. 加载向量库
    vector_dir = base_dir / "vector_kb"
    chunks, vectorizer, matrix, bm25 = load_vector_kb(vector_dir)
    
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
    dataset = Dataset.from_dict({
        "question": data["question"],
        "contexts": data["contexts"],
        "answer": data["answer"],
        "ground_truth": data["ground_truth"]
    })
    
    result = evaluate(
        dataset,
        metrics=metrics,
    )
    
    df_ragas = result.to_pandas()
    
    # 5. 计算传统检索指标 (Recall@K, MRR, MAP)
    print("正在计算传统检索指标...")
    recalls = []
    mrr_sum = 0
    map_sum = 0
    
    for res in retrieval_results:
        target = res["ref_id"]
        retrieved = res["retrieved_ids"]
        
        # Recall@5
        found = target in retrieved
        recalls.append(1 if found else 0)
        
        # MRR
        if found:
            rank = retrieved.index(target) + 1
            mrr_sum += 1.0 / rank
            
        # AP (Simplified for single relevant doc)
        if found:
            rank = retrieved.index(target) + 1
            map_sum += 1.0 / rank # 因为只有一个 relevant doc，AP 等于 1/rank
            
    avg_recall = sum(recalls) / len(recalls)
    avg_mrr = mrr_sum / len(retrieval_results)
    avg_map = map_sum / len(retrieval_results)
    
    # 6. 生成报告
    print("\n" + "="*30)
    print("RAG 评估报告 (MarathonCoach)")
    print("="*30)
    print(f"传统检索指标 (Top-5):")
    print(f"- Recall@5: {avg_recall:.4f}")
    print(f"- MRR@5:    {avg_mrr:.4f}")
    print(f"- MAP@5:    {avg_map:.4f}")
    print("-" * 20)
    print(f"Ragas 自动评估指标:")
    for metric_name, score in result.items():
        print(f"- {metric_name}: {score:.4f}")
    print("="*30)
    
    # 保存详细报告
    report_path = base_dir / "rag_eval_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# RAG 评估实验报告\n\n")
        f.write("## 1. 核心指标汇总\n\n")
        f.write("| 指标类型 | 指标名称 | 分值 |\n")
        f.write("| :--- | :--- | :--- |\n")
        f.write(f"| 传统检索 | Recall@5 | {avg_recall:.4f} |\n")
        f.write(f"| 传统检索 | MRR@5 | {avg_mrr:.4f} |\n")
        f.write(f"| 传统检索 | MAP@5 | {avg_map:.4f} |\n")
        for metric_name, score in result.items():
            f.write(f"| Ragas | {metric_name} | {score:.4f} |\n")
        
        f.write("\n## 2. 详细数据样本 (Top 3)\n\n")
        for i in range(min(3, len(df_ragas))):
            f.write(f"### 样本 {i+1}\n")
            f.write(f"**问题**: {df_ragas.iloc[i]['question']}\n\n")
            f.write(f"**检索上下文 (片段 1)**: {df_ragas.iloc[i]['contexts'][0][:200]}...\n\n")
            f.write(f"**系统回答**: {df_ragas.iloc[i]['answer']}\n\n")
            f.write(f"**标准答案**: {df_ragas.iloc[i]['ground_truth']}\n\n")
            f.write("---\n")
            
    print(f"详细报告已生成至: {report_path}")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
