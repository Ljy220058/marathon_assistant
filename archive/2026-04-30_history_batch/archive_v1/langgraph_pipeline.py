from typing import TypedDict, Annotated
from operator import add
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

class ArticleState(TypedDict):
    topic: str
    research_notes: Annotated[list, add]  # 使用add操作符累积列表
    outline: str
    draft: str
    review_feedback: str
    final_article: str

# 初始化模型，使用已验证的 qwen2.5 模型名称
llm = ChatOllama(model="qwen2.5", base_url="http://localhost:11434", temperature=0.7)

def research_agent(state: ArticleState) -> dict:
    """研究Agent：收集主题相关信息"""
    print("[运动科学研究员] 正在收集资料...")
    try:
        response = llm.invoke([
            HumanMessage(
                content=f"你是一个运动科学研究员。请就'{state['topic']}'这个主题，"
                        f"基于丹尼尔斯经典训练法，列出5个核心训练原则或关键点，每个用2-3句话说明。"
            )
        ])
        content = response.content
    except Exception as e:
        print(f"  [Error] {e} - 使用回退数据")
        content = "1. 减量期通常在赛前3-4周开始，逐步减少周跑量。\n2. 保持训练频率，但降低单次训练的距离。\n3. 维持甚至略微提升强度，以保持肌肉的神经募集能力。\n4. 注重碳水化合物的补充，为比赛储备糖原。\n5. 增加睡眠和休息时间，促进身体全面恢复。"
    return {"research_notes": [content]}

def writing_agent(state: ArticleState) -> dict:
    """写作Agent：基于研究结果撰写文章"""
    print("[马拉松主教练] 正在基于文献撰写训练计划...")
    notes = "\n".join(state["research_notes"])
    try:
        response = llm.invoke([
            HumanMessage(
                content=f"你是一个资深马拉松教练。基于以下运动科学研究资料，撰写一篇关于"
                        f"'{state['topic']}'的指导文章（300-500字），提供给业余跑者。\n\n"
                        f"研究资料：\n{notes}"
            )
        ])
        content = response.content
    except Exception as e:
        print(f"  [Error] {e} - 使用回退数据")
        content = "马拉松赛前减量训练（Tapering）是决定比赛表现的关键阶段。根据丹尼尔斯训练法，赛前3-4周跑者应开始逐步减少跑量，但必须保持原有的训练频率和部分高强度训练（如节奏跑或间歇跑），以维持身体的竞技状态和神经肌肉的活跃度。在此期间，跑者需要特别注意增加碳水化合物的摄入，并保证充足的睡眠，让身体从前期的疲劳中彻底恢复，以最佳状态迎接比赛。"
    return {"draft": content}

def review_agent(state: ArticleState) -> dict:
    """审核Agent：评审文章质量与安全性"""
    print("[运动康复专家] 正在审核计划的安全性与科学性...")
    try:
        response = llm.invoke([
            HumanMessage(
                content=f"你是一个严谨的运动康复师。请审核以下马拉松训练指导文章，指出可能存在的伤病隐患或不够严谨的地方，"
                        f"并提出具体修改建议（至少3条）。\n\n"
                        f"文章：\n{state['draft']}"
            )
        ])
        content = response.content
    except Exception as e:
        print(f"  [Error] {e} - 使用回退数据")
        content = "1. 建议明确指出跑量减少的具体比例（例如每周递减20%左右），避免跑者减量过度或不足。\n2. 提到高强度训练时，应强调必须做好充分的热身和冷身，赛前一周应避免力竭性间歇。\n3. 关于碳水补充，建议提醒跑者避免尝试平时未吃过的新食物，防止肠胃不适。"
    return {"review_feedback": content}

def revision_agent(state: ArticleState) -> dict:
    """修改Agent：根据反馈修改文章"""
    print("[马拉松主教练] 正在根据专家反馈修改最终计划...")
    try:
        response = llm.invoke([
            HumanMessage(
                content=f"你是一个资深马拉松教练。请根据运动康复专家的审核反馈，修改并完善以下指导文章。\n\n"
                        f"原文：\n{state['draft']}\n\n"
                        f"审核反馈：\n{state['review_feedback']}\n\n"
                        f"请输出修改后的完整指导文章（排版清晰，适合跑者阅读）。"
            )
        ])
        content = response.content
    except Exception as e:
        print(f"  [Error] {e} - 使用回退数据")
        content = "### 马拉松赛前四周减量（Tapering）科学指南\n\n马拉松赛前减量训练（Tapering）是决定比赛表现的关键阶段。根据丹尼尔斯训练法，赛前3-4周跑者应开始逐步减少跑量（建议每周递减20%左右），但必须保持原有的训练频率。\n\n**核心要点：**\n1. **维持强度，防伤防病**：保留部分高强度训练（如节奏跑），以维持神经肌肉活跃度。但切记，赛前一周应避免力竭性间歇，且所有高强度课表前后必须进行充分的热身与冷身。\n2. **科学补碳，肠胃安全**：增加碳水化合物摄入以储备糖原，但切忌在赛前尝试任何平时未吃过的新食物或补剂，以防肠胃不适。\n3. **全面恢复**：保证充足的睡眠，让身体从漫长的备战疲劳中彻底恢复，以最佳状态站上起跑线！"
    return {"final_article": content}

# 构建流水线
graph = StateGraph(ArticleState)

graph.add_node("research", research_agent)
graph.add_node("write", writing_agent)
graph.add_node("review", review_agent)
graph.add_node("revise", revision_agent)

graph.add_edge(START, "research")
graph.add_edge("research", "write")
graph.add_edge("write", "review")
graph.add_edge("review", "revise")
graph.add_edge("revise", END)

app = graph.compile()

# 运行流水线
print("\n" + "=" * 60)
print("启动马拉松科研与写作 Agent 流水线")
print("=" * 60)

result = app.invoke({
    "topic": "马拉松赛前四周减量（Tapering）与状态调整策略",
    "research_notes": [],
    "outline": "",
    "draft": "",
    "review_feedback": "",
    "final_article": ""
})

print("\n" + "=" * 60)
print("最终文章：")
print(result["final_article"])
