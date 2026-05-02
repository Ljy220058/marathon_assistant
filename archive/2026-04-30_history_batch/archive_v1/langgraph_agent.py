import os
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

# 1. 定义状态 (State) - 结合实际科研/备赛文档调研的需求
class ResearchState(TypedDict):
    query: str
    documents: list
    draft: str
    messages: list
    current_step: str

# 2. 定义节点函数 (Nodes)

def retrieve_papers(state: ResearchState) -> dict:
    """模拟检索相关文献或本地笔记"""
    print("-> [Node: retrieve_papers] 正在检索相关文献...")
    # 这里可以替换为真实的检索调用，例如从 domain_docs 中检索
    mock_docs = [
        "文献A: 《Nutrition for Marathon Running》，探讨了马拉松跑步的营养补给与策略。",
        "文献B: 《Periodization for Massive Strength Gains》，分析了周期化力量训练对跑步经济性的提升。"
    ]
    return {
        "documents": mock_docs,
        "messages": state.get("messages", []) + ["系统：已成功检索到2篇相关文献。"],
        "current_step": "retrieved"
    }

def analyze_papers(state: ResearchState) -> dict:
    """使用大模型分析检索到的文献"""
    print("-> [Node: analyze_papers] 正在分析文献内容...")
    
    docs_text = "\n".join(state["documents"])
    prompt = f"请根据以下文献进行简要分析：\n{docs_text}\n\n用户调研问题：{state['query']}\n请给出分析总结。"
    
    try:
        # 尝试调用本地 Ollama 模型进行真实分析
        llm = ChatOllama(model="qwen2.5", base_url="http://localhost:11434")
        response = llm.invoke([HumanMessage(content=prompt)])
        analysis = response.content
    except Exception as e:
        # 如果 Ollama 未启动或模型不存在，使用 mock 数据 fallback
        print(f"   [警告] Ollama 调用失败 ({e})，使用默认分析结果。")
        analysis = "基于文献A和B，科学的营养补给策略与周期化的力量训练是提升马拉松表现的核心关键点。"
        
    return {
        "draft": analysis,
        "messages": state["messages"] + ["系统：文献分析完成，已生成草稿。"],
        "current_step": "analyzed"
    }

def generate_report(state: ResearchState) -> dict:
    """生成最终的调研报告"""
    print("-> [Node: generate_report] 正在生成最终调研报告...")
    report = f"### 最终调研报告\n\n**核心问题**: {state['query']}\n\n**分析总结**:\n{state['draft']}"
    return {
        "messages": state["messages"] + [report],
        "current_step": "done"
    }

# 3. 构建图 (Graph)
graph = StateGraph(ResearchState)

# 添加节点
graph.add_node("retrieve", retrieve_papers)
graph.add_node("analyze", analyze_papers)
graph.add_node("report", generate_report)

# 4. 添加边 (Edges) 定义工作流顺序
graph.add_edge(START, "retrieve")
graph.add_edge("retrieve", "analyze")
graph.add_edge("analyze", "report")
graph.add_edge("report", END)

# 5. 编译图
app = graph.compile()

if __name__ == "__main__":
    print("=== 领域文献调研 LangGraph Agent 启动 ===\n")
    
    # 初始化状态
    initial_state = {
        "query": "如何通过营养补给与力量训练提升马拉松表现？",
        "documents": [],
        "draft": "",
        "messages": ["用户：请帮我调研如何提升马拉松表现。"],
        "current_step": "start"
    }
    
    # 运行图
    result = app.invoke(initial_state)
    
    print("\n=== 最终执行结果 ===")
    for msg in result["messages"]:
        print(msg)
