import os
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

class IterativeState(TypedDict):
    task: str
    draft: str
    feedback: str
    iteration: int
    max_iterations: int
    is_approved: bool

# 初始化模型
llm = ChatOllama(model="qwen2.5", temperature=0.7, base_url="http://localhost:11434")

def generate(state: IterativeState) -> dict:
    """生成或修改马拉松四周训练计划"""
    iteration = state["iteration"]
    if iteration == 0:
        prompt = (
            f"你是一个资深马拉松教练。请根据跑者的需求制定一份赛前四周减量期（Tapering）的训练计划：\n"
            f"需求：{state['task']}\n"
            f"请基于丹尼尔斯经典训练法，给出每周总跑量建议以及长距离跑的具体安排。"
        )
    else:
        prompt = (
            f"你是一个资深马拉松教练。请根据审核专家的反馈，修改你的四周训练计划。\n\n"
            f"原计划：\n{state['draft']}\n\n"
            f"专家反馈：\n{state['feedback']}\n\n"
            f"请输出修改后的完整四周训练计划，确保解决专家的担忧。"
        )

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content
    except Exception as e:
        print(f"   [警告] LLM 调用失败 ({e})，使用回退数据。")
        if iteration == 0:
            content = "四周减量计划初稿：每周跑量分别为 60km, 50km, 40km, 20km。每个周末都安排一次30km的长距离跑。"
        else:
            content = "修改后的四周减量计划：每周跑量分别为 60km, 48km, 35km, 15km。赛前最后两周取消30km长距离跑，改为15km轻松跑和赛前热身。"
            
    print(f"\n[第{iteration+1}轮] 主教练已生成计划草案")
    return {"draft": content, "iteration": iteration + 1}

def evaluate(state: IterativeState) -> dict:
    """运动康复专家评估计划的科学性与安全性"""
    print("[专家审核] 正在评估计划的伤病风险与恢复科学性...")
    prompt = (
        f"你是一个严格的运动科学与康复专家。请评估以下马拉松四周训练计划的质量（满分10分），并给出改进建议。\n"
        f"评估重点：减量比例是否科学（通常每周递减20%左右）、赛前1-2周是否避免了过度的长距离或高强度力竭训练。\n"
        f"如果计划足够安全且科学（评分>=8分），请务必在回答的最开头写上大写的 'APPROVED'。\n\n"
        f"计划内容：\n{state['draft']}"
    )
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        feedback = response.content
    except Exception as e:
        print(f"   [警告] LLM 调用失败 ({e})，使用回退数据。")
        if state["iteration"] == 1:
            feedback = "评分：6分。建议：第一周到第二周的跑量递减不够平滑，且初稿中赛前四周每周末都安排了30km长距离跑，这是极度危险的，会导致赛前疲劳堆积。必须修改。"
        else:
            feedback = "APPROVED。评分：9分。修改后的计划跑量递减合理，赛前取消超长距离跑的安排非常科学，有利于身体糖原储备和肌肉全面恢复。"
            
    is_approved = "APPROVED" in feedback or state["iteration"] >= state["max_iterations"]
    print(f"[专家审核] 结果: {'通过 (APPROVED)' if is_approved else '需修改 (REJECTED)'}")
    return {"feedback": feedback, "is_approved": is_approved}

def should_continue(state: IterativeState) -> Literal["generate", "end"]:
    """判断是否需要继续迭代优化"""
    if state["is_approved"]:
        return "end"
    return "generate"

# 构建循环图
graph = StateGraph(IterativeState)

graph.add_node("generate", generate)
graph.add_node("evaluate", evaluate)

graph.add_edge(START, "generate")
graph.add_edge("generate", "evaluate")
graph.add_conditional_edges("evaluate", should_continue, {
    "generate": "generate",
    "end": END
})

app = graph.compile()

if __name__ == "__main__":
    print("=== 马拉松备赛：循环优化 Agent 流水线启动 ===\n")
    
    # 设定任务：制定四周训练计划
    result = app.invoke({
        "task": "目标全马破4（3小时59分），目前月跑量约200km，周末长距离配速5分40秒。",
        "draft": "",
        "feedback": "",
        "iteration": 0,
        "max_iterations": 3,
        "is_approved": False
    })
    
    print(f"\n============================================================")
    print(f"最终计划（经过 {result['iteration']} 轮迭代与优化）：")
    print(result["draft"])
    print(f"============================================================")
    print(f"专家最终评语：\n{result['feedback']}")