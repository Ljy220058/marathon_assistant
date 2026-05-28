from typing import Any

try:
    from langchain_core.runnables import RunnableConfig
except ImportError:
    RunnableConfig = Any

from marathon_qa_assistant.core.state_models import IntegratedState
from marathon_qa_assistant.nodes.common import ensure_usage

PLAN_TIME_KEYWORDS = ["本周", "下周", "这周", "明天", "后天", "接下来", "第一周", "第1周", "周期"]
PLAN_ACTION_KEYWORDS = ["计划", "制定", "安排", "生成", "怎么练", "练什么", "课表", "schedule", "plan"]
# P1-1: 添加 "比较" 关键词，使对比类查询能正确触发 research 模式
RESEARCH_KEYWORDS = ["研究", "文献", "对比", "比较", "机制", "原理", "graph", "图谱", "cross-document"]
# P0-4: 扩展营养关键词，覆盖补给/恢复/饮食等常见营养查询
NUTRITION_KEYWORDS = [
    "营养", "补给", "吃", "喝", "补水", "蛋白", "碳水", "恢复餐",
    "能量胶", "电解质", "饮食", "素食", "生酮", "空腹", "低血糖",
    "hydration", "fuel", "nutrition", "diet",
]
THERAPY_KEYWORDS = ["伤", "恢复", "疼", "疲劳", "拉伸", "康复", "injury", "recovery"]
ADAPTIVE_KEYWORDS = ["【自适应调整】", "adaptive"]
PROFILE_UPDATE_KEYWORDS = [
    "乳酸阈", "lthr", "阈值心率", "心率阈值", "心率是", "心率为", "心率:",
    "pb", "pr", "最好成绩", "个人最佳", "个人记录", "新纪录",
    "配速是", "配速为", "配速:", "t配速", "t-pace", "t_pace",
    "周跑量", "跑量是", "跑量为",
    "vo2max", "最大摄氧",
    "经验水平", "我现在是", "我算",
    "目标赛事", "目标成绩",
    "比赛日期", "比赛在",
    "可用训练日", "训练日是",
    "最长训练", "最多跑",
    "心率改为", "心率设为", "心率更新", "心率调整",
    "配速改为", "配速设为",
    "跑量改为", "跑量调整",
    "更新", "改为", "设为",
]


async def router_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    query = state.get("query", "")
    lower_query = query.lower()

    if any(keyword in lower_query for keyword in [k.lower() for k in RESEARCH_KEYWORDS]):
        workflow_kind = "research"
        intent_type = "qa"
    elif any(keyword in lower_query for keyword in [k.lower() for k in ADAPTIVE_KEYWORDS]):
        workflow_kind = "adaptive"
        intent_type = "plan"
    else:
        has_time = any(keyword in lower_query for keyword in [k.lower() for k in PLAN_TIME_KEYWORDS])
        has_action = any(keyword in lower_query for keyword in [k.lower() for k in PLAN_ACTION_KEYWORDS])
        if has_time and has_action:
            workflow_kind = "plan"
            intent_type = "plan"
        elif "计划" in query or "训练安排" in query:
            workflow_kind = "plan"
            intent_type = "plan"
        elif any(keyword in lower_query for keyword in [k.lower() for k in PROFILE_UPDATE_KEYWORDS]):
            workflow_kind = "profile_update"
            intent_type = "profile_update"
        else:
            workflow_kind = "qa"
            intent_type = "qa"

    mode = {
        "plan": "subagent",
        "research": "research",
        "adaptive": "adaptive",
        "profile_update": "team",
        "qa": "team",
    }.get(workflow_kind, "team")

    category = "coach"
    if any(keyword in lower_query for keyword in [k.lower() for k in NUTRITION_KEYWORDS]):
        category = "nutritionist"
    elif any(keyword in lower_query for keyword in [k.lower() for k in THERAPY_KEYWORDS]):
        category = "therapist"
    elif workflow_kind == "research":
        category = "research"

    return {
        "mode": mode,
        "workflow_kind": workflow_kind,
        "category": category,
        "intent_type": intent_type,
        "iteration_count": 0,
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": [f"[router] workflow_kind={workflow_kind}, intent={intent_type}, category={category}"],
        "rag_sources": [],
    }
