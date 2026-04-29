import os
import json
import random
import asyncio
from pathlib import Path
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

# 加载配置
base_dir = Path(__file__).parent.resolve()
env_path = base_dir / "graphrag_project" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:latest")

llm = ChatOllama(
    model=OLLAMA_MODEL,
    temperature=0.3,
    base_url=OLLAMA_BASE_URL
)

def load_chunks(chunks_file: Path) -> list[dict]:
    chunks = []
    with chunks_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            chunks.append(json.loads(line))
    return chunks

async def generate_qa_pair(chunk: dict):
    """为给定的文本块生成问题和标准答案"""
    text = chunk["text"]
    prompt = f"""你是一个专业的运动科学专家。请根据以下提供的文本片段，生成一个对应的问题和该问题的标准回答。

【文本片段】:
{text}

要求:
1. 问题必须能直接从文本中找到答案。
2. 问题应该是具体的，不要太宽泛。
3. 回答应该是准确且简洁的。
4. 请务必以 JSON 格式输出，包含 "question" 和 "ground_truth" 两个字段。不要有其他解释。

输出示例:
{{"question": "什么是VO2Max？", "ground_truth": "VO2Max是最大摄氧量，衡量人体在剧烈运动中利用氧气的能力。"}}
"""
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        # 尝试提取 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "{" in content:
            content = content[content.find("{"):content.rfind("}")+1]
        
        data = json.loads(content)
        return {
            "question": data["question"],
            "ground_truth": data["ground_truth"],
            "reference_chunk_id": chunk["chunk_id"],
            "reference_context": text
        }
    except Exception as e:
        print(f"生成失败 (Chunk ID: {chunk['chunk_id']}): {e}")
        return None

async def main():
    chunks_path = base_dir / "vector_kb" / "chunks.jsonl"
    if not chunks_path.exists():
        print(f"未找到 chunks 文件: {chunks_path}")
        return

    all_chunks = load_chunks(chunks_path)
    # 随机选择 10 个长度适中的块 (避免太短的无意义内容)
    valid_chunks = [c for c in all_chunks if len(c["text"]) > 100]
    selected_chunks = random.sample(valid_chunks, min(10, len(valid_chunks)))

    print(f"正在为 {len(selected_chunks)} 个文本块生成评估数据...")
    
    tasks = [generate_qa_pair(c) for c in selected_chunks]
    results = await asyncio.gather(*tasks)
    
    eval_dataset = [r for r in results if r is not None]
    
    output_path = base_dir / "vector_kb" / "eval_dataset.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(eval_dataset, f, ensure_ascii=False, indent=2)
    
    print(f"评估数据集已保存至: {output_path} (共 {len(eval_dataset)} 条)")

if __name__ == "__main__":
    asyncio.run(main())
