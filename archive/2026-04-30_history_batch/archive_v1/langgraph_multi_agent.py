import os
from typing import TypedDict, Literal, Annotated
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
import operator
from pathlib import Path
from build_vector_kb import load_vector_kb, retrieve

# ==========================================
# 1. 定义状态 (State)
# ==========================================
class PrepState(TypedDict):
    query: str                   # 跑者的原始问题
    category: str                # 意图分类结果 (coach/nutritionist/therapist)
    draft_plan: str              # 专业Agent生成的草案
    review_feedback: str         # 医疗总监的审核意见
    is_approved: bool            # 是否通过审核
    iteration_count: int         # 当前修改轮次
    final_report: str            # 最终输出报告

# 初始化 LLM
llm = ChatOllama(model="qwen2.5:latest", temperature=0.5, base_url="http://localhost:11434")

# 加载知识库
print("正在加载本地知识库 (TF-IDF)...")
try:
    vector_dir = Path(__file__).parent / "vector_kb"
    KB_CHUNKS, KB_VECTORIZER, KB_MATRIX = load_vector_kb(vector_dir)
    print("知识库加载成功！")
except Exception as e:
    print(f"知识库加载失败: {e}")
    KB_CHUNKS, KB_VECTORIZER, KB_MATRIX = [], None, None

def _get_rag_context(query: str, top_k: int = 3) -> str:
    if not KB_CHUNKS:
        return "（无可用知识库）"
    hits = retrieve(query, KB_CHUNKS, KB_VECTORIZER, KB_MATRIX, top_k=top_k)
    if not hits:
        return "（未检索到相关知识）"
    snippets = [hit["text"].replace("\n", " ").strip() for hit in hits]
    return "\n".join(snippets)

# ==========================================
# 2. 定义各个 Agent 节点
# ==========================================

def classifier_agent(state: PrepState) -> dict:
    """分类Agent：识别跑者意图"""
    print("\n[分类Agent] 正在分析跑者意图...")
    query = state["query"]
    prompt = f"""请分析以下跑者的问题，将其分类到以下三个类别之一，只输出类别英文名称：
    - coach: 涉及跑步训练计划、配速、跑量等
    - nutritionist: 涉及饮食、补剂、赛前补碳等
    - therapist: 涉及疼痛、伤病、赛后恢复等
    
    跑者问题：{query}
    类别："""
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        cat = response.content.strip().lower()
        if "coach" in cat:
            category = "coach"
        elif "nutrition" in cat:
            category = "nutritionist"
        elif "therapist" in cat:
            category = "therapist"
        else:
            category = "coach" # 默认 fallback
    except Exception as e:
        print(f"   [警告] LLM 调用失败，使用基于规则的分类...")
        if "吃" in query or "补剂" in query or "水" in query:
            category = "nutritionist"
        elif "痛" in query or "伤" in query or "恢复" in query:
            category = "therapist"
        else:
            category = "coach"
            
    print(f"[分类Agent] 分配给: {category.upper()}")
    return {"category": category, "iteration_count": 0}


def coach_agent(state: PrepState) -> dict:
    """主教练Agent：处理训练计划"""
    print("\n[主教练Agent] 正在基于 RAG 制定/修改训练方案...")
    query = state["query"]
    feedback = state.get("review_feedback", "")
    previous_draft = state.get("draft_plan", "")
    
    context = _get_rag_context(query + " 训练 配速 LSD 跑量 计划", top_k=3)
    
    prompt = f"""你是专业的马拉松主教练。请根据以下参考知识和跑者的问题，提供专业、科学的训练指导。
如果存在之前的审核反馈，请务必针对反馈中的每一条意见，对【上一版草案】进行彻底修改，绝对不要重复被驳回的错误！

【参考知识】：
{context}

【跑者问题】：
{query}

【上一版草案（如有）】：
{previous_draft}

【医疗总监的审核驳回意见（如有）】：
{feedback}

请直接输出你修改后的最新训练方案，保持专业和严谨："""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        draft = response.content.strip()
    except Exception as e:
        print(f"   [警告] LLM 调用失败 ({e})，使用规则生成...")
        draft = "【模拟训练方案】基于 RAG 检索的训练计划：" + context[:50]

    print(f"  -> 生成草案完毕 (字数: {len(draft)})")
    return {"draft_plan": draft}


def nutritionist_agent(state: PrepState) -> dict:
    """营养师Agent：处理饮食补给"""
    print("\n[营养师Agent] 正在基于 RAG 制定/修改饮食方案...")
    query = state["query"]
    feedback = state.get("review_feedback", "")
    previous_draft = state.get("draft_plan", "")
    
    context = _get_rag_context(query + " 饮食 补给 碳水 营养 牛奶 赛前", top_k=3)
    
    prompt = f"""你是专业的马拉松运动营养师。请根据以下参考知识和跑者的问题，提供专业、科学的饮食和补给指导。
如果存在之前的审核反馈，请务必针对反馈中的每一条意见，对【上一版草案】进行彻底修改，绝对不要重复被驳回的错误！

【参考知识】：
{context}

【跑者问题】：
{query}

【上一版草案（如有）】：
{previous_draft}

【医疗总监的审核驳回意见（如有）】：
{feedback}

请直接输出你修改后的最新饮食补给方案，保持专业和严谨："""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        draft = response.content.strip()
    except Exception as e:
        print(f"   [警告] LLM 调用失败 ({e})，使用规则生成...")
        draft = "【模拟饮食方案】基于 RAG 检索的饮食计划：" + context[:50]

    print(f"  -> 生成草案完毕 (字数: {len(draft)})")
    return {"draft_plan": draft}


def therapist_agent(state: PrepState) -> dict:
    """康复师Agent：处理伤病恢复"""
    print("\n[康复师Agent] 正在基于 RAG 制定/修改康复方案...")
    query = state["query"]
    feedback = state.get("review_feedback", "")
    previous_draft = state.get("draft_plan", "")
    
    context = _get_rag_context(query + " 疼痛 伤病 恢复 膝盖 治疗", top_k=3)
    
    prompt = f"""你是专业的马拉松运动康复师。请根据以下参考知识和跑者的问题，提供专业、科学的康复和防伤指导。
如果存在之前的审核反馈，请务必针对反馈中的每一条意见，对【上一版草案】进行彻底修改，绝对不要重复被驳回的错误！

【参考知识】：
{context}

【跑者问题】：
{query}

【上一版草案（如有）】：
{previous_draft}

【医疗总监的审核驳回意见（如有）】：
{feedback}

请直接输出你修改后的最新康复指导方案，保持专业和严谨："""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        draft = response.content.strip()
    except Exception as e:
        print(f"   [警告] LLM 调用失败 ({e})，使用规则生成...")
        draft = "【模拟康复方案】基于 RAG 检索的康复计划：" + context[:50]

    print(f"  -> 生成草案完毕 (字数: {len(draft)})")
    return {"draft_plan": draft}


def reviewer_agent(state: PrepState) -> dict:
    """综合评估Agent（医疗总监）：审核方案安全性与科学性"""
    print(f"\n[医疗总监] 正在严格审查第 {state['iteration_count'] + 1} 版方案...")
    query = state["query"]
    draft = state["draft_plan"]
    
    context = _get_rag_context(query + " 安全 风险 禁忌 注意事项 误区", top_k=3)
    
    prompt = f"""你是马拉松团队的医疗总监与总审核员。请基于以下参考知识，严格审查专业Agent给出的方案草案。
重点关注：是否有安全隐患、是否违背运动医学常识（例如：赛前喝牛奶导致肠胃不适、LSD配速过快导致力竭、受伤期间带痛坚持或暴力按揉等）。

【参考知识】：
{context}

【跑者原始问题】：
{query}

【待审核方案】：
{draft}

请按以下格式严格输出：
第一行必须仅包含：APPROVED 或 REJECTED
从第二行开始：给出具体的审核意见或修改建议（如果 REJECTED，必须明确指出危险点并要求修改；如果 APPROVED，给出肯定评价）。切勿在第一行添加任何其他词语。"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
    except Exception as e:
        print(f"   [警告] LLM 调用失败 ({e})，使用规则生成...")
        content = "APPROVED\n无大模型响应，默认通过。"

    # 改进解析逻辑：使用正则查找 APPROVED 或 REJECTED
    import re
    is_approved = False
    decision_match = re.search(r'(APPROVED|REJECTED)', content, re.IGNORECASE)
    if decision_match:
        decision = decision_match.group(1).upper()
        is_approved = (decision == "APPROVED")
    else:
        # Fallback to original line[0] logic
        lines = content.split('\n')
        decision = lines[0].strip().upper()
        is_approved = "APPROVED" in decision
        
    feedback = content.replace("APPROVED", "").replace("REJECTED", "").strip()
    if not feedback:
        feedback = "无额外意见"
    
    if is_approved:
        print("  -> 审核结果: 通过 (APPROVED)")
    else:
        print("  -> 审核结果: 驳回 (REJECTED)")
        
    print(f"  -> 审核意见: {feedback[:100]}...")
    
    # 防止死循环，最多修改 2 次
    if state["iteration_count"] >= 2 and not is_approved:
        print("  -> 达到最大迭代次数，强制通过。")
        is_approved = True
        feedback += "\n\n（注：已达最大修改次数，强制放行，请跑者自行甄别潜在风险）"

    return {
        "review_feedback": feedback,
        "is_approved": is_approved,
        "iteration_count": state["iteration_count"] + 1
    }


def formatter_agent(state: PrepState) -> dict:
    """格式化Agent：整理最终报告"""
    print("\n[排版Agent] 正在生成最终的 Markdown 报告...")
    report = f"### 马拉松全周期备赛管家 - 专业指导方案\n\n"
    report += f"**跑者需求：** {state['query']}\n"
    report += f"**负责专区：** {state['category'].capitalize()}\n"
    report += f"**历经迭代：** {state['iteration_count']} 轮严格审核\n\n"
    report += f"**最终方案：**\n{state['draft_plan']}\n"
    return {"final_report": report}

# ==========================================
# 3. 定义路由逻辑
# ==========================================
def route_to_specialist(state: PrepState) -> str:
    return state["category"]

def route_after_review(state: PrepState) -> str:
    if state["is_approved"]:
        return "formatter"
    else:
        return state["category"]

# ==========================================
# 4. 构建多Agent状态图
# ==========================================
graph = StateGraph(PrepState)

graph.add_node("classifier", classifier_agent)
graph.add_node("coach", coach_agent)
graph.add_node("nutritionist", nutritionist_agent)
graph.add_node("therapist", therapist_agent)
graph.add_node("reviewer", reviewer_agent)
graph.add_node("formatter", formatter_agent)

graph.add_edge(START, "classifier")
graph.add_conditional_edges("classifier", route_to_specialist, {
    "coach": "coach",
    "nutritionist": "nutritionist",
    "therapist": "therapist"
})

graph.add_edge("coach", "reviewer")
graph.add_edge("nutritionist", "reviewer")
graph.add_edge("therapist", "reviewer")

graph.add_conditional_edges("reviewer", route_after_review, {
    "formatter": "formatter",
    "coach": "coach",
    "nutritionist": "nutritionist",
    "therapist": "therapist"
})

graph.add_edge("formatter", END)
# 编译工作流
app = graph.compile()

# ==========================================
# 5. 执行测试
# ==========================================
if __name__ == "__main__":
    print("="*60)
    print(">>> 欢迎使用 [马拉松全周期备赛管家] 多Agent协作系统 (RAG增强版) <<<")
    print("="*60)
    
    test_cases = [
        "我赛前3周应该怎么跑LSD？配速要不要比比赛配速快一点去刺激心肺？",
        "我听说赛前要大量补碳，比赛当天早上喝2杯牛奶补充蛋白质对不对？",
        "最近跑步膝盖外侧总是疼，我能带痛跑吗？需不需要用力去按揉痛点？"
    ]
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n\n\n>>>>>> 测试案例 {i} <<<<<<")
        print(f"跑者提问：{query}")
        
        try:
            result = app.invoke({
                "query": query,
                "category": "",
                "draft_plan": "",
                "review_feedback": "",
                "is_approved": False,
                "iteration_count": 0,
                "final_report": ""
            })
            
            print("\n" + "="*40)
            print(result["final_report"])
            print("="*40)
        except Exception as e:
            import traceback
            print(f"执行发生异常：{e}")
            traceback.print_exc()
