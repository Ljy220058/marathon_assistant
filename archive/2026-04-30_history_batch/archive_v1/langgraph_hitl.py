print("--- SCRIPT STARTING ---", flush=True)
import os
import builtins
print("Imported os, builtins", flush=True)
from typing import TypedDict, Literal
print("Imported typing", flush=True)
from langgraph.graph import StateGraph, START, END
print("Imported langgraph.graph", flush=True)
from langgraph.checkpoint.memory import MemorySaver
print("Imported langgraph.checkpoint.memory", flush=True)
from langchain_ollama import ChatOllama
print("Imported langchain_ollama", flush=True)
from langchain_core.messages import HumanMessage
print("Imported langchain_core", flush=True)

class HumanLoopState(TypedDict):
    request: str
    ai_response: str
    human_approved: bool
    final_output: str

# ==========================================
# 加载知识库
# ==========================================
from pathlib import Path
from build_vector_kb import load_vector_kb, retrieve

print("正在加载本地知识库 (TF-IDF)...", flush=True)
try:
    vector_dir = Path(__file__).parent / "vector_kb"
    KB_CHUNKS, KB_VECTORIZER, KB_MATRIX = load_vector_kb(vector_dir)
    print("知识库加载成功！", flush=True)
except Exception as e:
    print(f"知识库加载失败: {e}", flush=True)
    KB_CHUNKS, KB_VECTORIZER, KB_MATRIX = [], None, None

def _get_rag_context(query: str, top_k: int = 3) -> str:
    if not KB_CHUNKS:
        return "（无可用知识库）"
    hits = retrieve(query, KB_CHUNKS, KB_VECTORIZER, KB_MATRIX, top_k=top_k)
    if not hits:
        return "（未检索到相关知识）"
    snippets = [hit["text"].replace("\n", " ").strip() for hit in hits]
    return "\n".join(snippets)

# 初始化LLM (与之前的任务保持一致)
llm = ChatOllama(model="qwen2.5:latest",  temperature=0.7, base_url="http://localhost:11434")

def ai_generate(state: HumanLoopState) -> dict:
    """AI教练生成或修改训练计划"""
    context = _get_rag_context(state['request'] + " 训练计划 冲刺 马拉松 配速", top_k=3)
    
    prompt = f"""你是一位专业马拉松教练。请结合以下【参考知识】，并根据运动员的要求制定或修改训练计划：

【参考知识】：
{context}

【运动员要求】：
{state['request']}

请简明扼要地输出专业且科学的计划内容（限200字以内）。"""
    print("\n[AI教练] 正在基于 RAG 思考并生成计划...")
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
    except Exception as e:
        print(f"   [警告] LLM 调用失败 ({e})，使用默认生成的计划草案。")
        if "修改意见" in state["request"]:
            content = "【修改后的计划】\n1. 周一：休息\n2. 周二：5km轻松跑 + 下肢力量训练（深蹲、硬拉）\n3. 周三：休息\n4. 周四：8km节奏跑\n5. 周五：休息\n6. 周六：15km长距离跑\n7. 周日：核心力量训练"
        else:
            content = "【初版计划】\n1. 周一：休息\n2. 周二：5km轻松跑\n3. 周三：休息\n4. 周四：8km节奏跑\n5. 周五：休息\n6. 周六：15km长距离跑\n7. 周日：休息"
    
    print(f"[AI教练] 输出草案:\n{content}")
    return {"ai_response": content}


def human_review(state: HumanLoopState) -> dict:
    """人工审核节点（运动员反馈）"""
    print("\n" + "=" * 40)
    print("请审核AI教练生成的训练计划：")
    print(state["ai_response"])
    print("=" * 40)

    # 真实的人机交互：等待终端用户输入
    approval = input("\n运动员：是否批准该计划？(y/n): ").strip().lower()
    
    if approval == "y":
        print("[系统] 计划已批准，流程结束。")
        return {"human_approved": True, "final_output": state["ai_response"]}
    else:
        feedback = input("运动员：请输入修改意见: ")
        print(f"[系统] 计划被打回，修改意见：{feedback}")
        return {
            "human_approved": False,
            "request": f"{state['request']}\n\n运动员修改意见：{feedback}"
        }

def route_after_review(state: HumanLoopState) -> Literal["generate", "end"]:
    if state["human_approved"]:
        return "end"
    return "generate"

# 构建图
graph = StateGraph(HumanLoopState)

graph.add_node("generate", ai_generate)
graph.add_node("review", human_review)

graph.add_edge(START, "generate")
graph.add_edge("generate", "review")
graph.add_conditional_edges("review", route_after_review, {
    "generate": "generate",
    "end": END
})

# 使用 MemorySaver 支持检查点（状态持久化，这是HITL的关键）
memory = MemorySaver()
app = graph.compile(checkpointer=memory)

if __name__ == "__main__":
    print("=== 马拉松备赛：Human-in-the-Loop 人机协同工作流启动 ===\n")
    
    # 运行（带线程ID以支持状态持久化）
    config = {"configurable": {"thread_id": "marathon-athlete-001"}}
    
    initial_request = "请为我制定一份针对半马破112的赛前一个月冲刺训练计划（每周跑7次）。"
    print(f"[初始需求] {initial_request}")
    
    result = app.invoke(
        {"request": initial_request,
         "ai_response": "", 
         "human_approved": False, 
         "final_output": ""},
        config=config
    )
    
    print("\n============================================================")
    print("【最终确定的训练计划】")
    print(result["final_output"])
    print("============================================================")
