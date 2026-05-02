import os
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

class RouterState(TypedDict):
    query: str
    query_type: str
    response: str

llm = ChatOllama(model="qwen2.5", temperature=0.3, base_url="http://localhost:11434")

def classify_query(state: RouterState) -> dict:
    """路由节点：判断查询类型"""
    query = state["query"]
    prompt = (
        f"请判断以下关于跑步的查询属于哪个类别，只回答类别名称：\n"
        f"- 训练生理\n- 训练方法\n- 安全风险\n\n"
        f"查询：{query}\n类别："
    )
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        query_type = response.content.strip()
    except Exception as e:
        print(f"   [警告] LLM 调用失败 ({e})，使用基于规则的 fallback。")
        if "乳酸" in query or "生理" in query:
            query_type = "训练生理"
        elif "计划" in query or "方法" in query or "训练" in query:
            query_type = "训练方法"
        else:
            query_type = "安全风险"
            
    print(f"[路由] 查询分类为: {query_type}")
    return {"query_type": query_type}

def handle_physiology(state: RouterState) -> dict:
    """处理训练生理问题"""
    try:
        response = llm.invoke([HumanMessage(content=f"你是一个运动生理学专家。请回答：\n{state['query']}")])
        ans = response.content
    except Exception:
        ans = "乳酸阈值是指血液中乳酸浓度开始急剧上升的拐点。提高乳酸阈值可以让你在更高配速下维持更长时间，是马拉松成绩的关键生理指标。"
    return {"response": f"[运动生理专家] {ans}"}

def handle_methodology(state: RouterState) -> dict:
    """处理训练方法问题"""
    try:
        response = llm.invoke([HumanMessage(content=f"你是一个马拉松教练。请基于丹尼尔斯训练法回答：\n{state['query']}")])
        ans = response.content
    except Exception:
        ans = "制定16周马拉松计划通常分为：基础期（积累跑量）、进展期（引入阈值跑）、巅峰期（长距离与间歇）和减量期（赛前恢复）。建议参考丹尼尔斯经典训练法。"
    return {"response": f"[马拉松教练] {ans}"}

def handle_safety(state: RouterState) -> dict:
    """处理安全风险问题"""
    try:
        response = llm.invoke([HumanMessage(content=f"你是一个运动康复师。请回答：\n{state['query']}")])
        ans = response.content
    except Exception:
        ans = "膝盖外侧疼痛可能是髂胫束综合征（ITBS）。建议减少跑量，加强臀中肌力量训练，并在跑后充分拉伸和使用泡沫轴放松髂胫束。"
    return {"response": f"[运动康复师] {ans}"}

def route_query(state: RouterState) -> Literal["physiology", "methodology", "safety"]:
    """条件路由函数"""
    qt = state["query_type"]
    if "生理" in qt:
        return "physiology"
    elif "方法" in qt or "计划" in qt or "训练" in qt:
        return "methodology"
    else:
        return "safety"

# 构建路由图
graph = StateGraph(RouterState)

graph.add_node("classify", classify_query)
graph.add_node("physiology", handle_physiology)
graph.add_node("methodology", handle_methodology)
graph.add_node("safety", handle_safety)

graph.add_edge(START, "classify")

graph.add_conditional_edges(
    "classify",
    route_query,
    {
        "physiology": "physiology",
        "methodology": "methodology",
        "safety": "safety"
    }
)

graph.add_edge("physiology", END)
graph.add_edge("methodology", END)
graph.add_edge("safety", END)

app = graph.compile()

if __name__ == "__main__":
    print("=== 马拉松备赛：条件路由 Agent 启动 ===\n")
    
    # 测试不同类型的查询
    test_queries = [
        "什么是乳酸阈值，它对马拉松有什么影响？",
        "如何制定一份16周的马拉松基础期训练计划？",
        "跑步时膝盖外侧疼痛是怎么回事，如何预防？",
    ]
    
    for q in test_queries:
        result = app.invoke({"query": q, "query_type": "", "response": ""})
        print(f"\n问题: {q}")
        print(f"回答: {result['response'][:200]}...")
        print("-" * 50)
