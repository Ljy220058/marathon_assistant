import re
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
ADAPTIVE_SIGNAL_KEYWORDS = [
    "疼", "痛", "伤", "受伤", "不适", "膝", "跟腱", "足底", "小腿", "髂胫束",
    "疲劳", "很累", "腿很重", "漏练", "漏训", "没练", "跳过", "出差", "改时间",
    "injury", "pain", "fatigue", "missed", "skip", "schedule change",
]
ADAPTIVE_ADJUSTMENT_KEYWORDS = [
    "调整", "重排", "改计划", "重新安排", "怎么调", "怎么改", "下周怎么练", "接下来怎么练",
    "adjust", "replan", "reschedule",
]
PROFILE_SIGNAL_KEYWORDS = [
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


def _strip_negated_status_phrases(text: str) -> str:
    """Remove common negative injury/fatigue status phrases before risk routing."""

    cleaned = str(text or "").lower()
    negated_patterns = (
        r"\bno\s+(current\s+)?(injury|injuries|pain|fatigue)\b",
        r"\bwithout\s+(current\s+)?(injury|injuries|pain|fatigue)\b",
        r"\b(injury|pain|fatigue)\s*[:：]\s*(none|no)\b",
        r"无当前伤病",
        r"无伤病",
        r"没有伤病",
        r"无疼痛",
        r"没有疼痛",
        r"无疲劳",
        r"没有疲劳",
    )
    for pattern in negated_patterns:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
    return cleaned


def _looks_like_plan_request(query: str) -> bool:
    text = str(query or "").strip().lower()
    if not text:
        return False
    readable_plan_actions = ("计划", "制定", "安排", "生成", "课表", "训练", "plan", "schedule", "training")
    readable_plan_times = ("本周", "下周", "这周", "明天", "后天", "接下来", "周期", "大周期", "week", "weeks", "macrocycle")
    if re.search(r"\d+\s*(周|星期|week|weeks)", text) and any(token in text for token in readable_plan_actions):
        return True
    if any(token in text for token in ("大周期", "训练计划", "周计划", "训练课表", "备赛周期")):
        return True
    if any(action in text for action in readable_plan_actions) and any(time in text for time in readable_plan_times):
        return True
    if re.search(r"\d+\s*周", text) and any(token in text for token in ("计划", "课表", "周期", "训练")):
        return True
    if any(token in text for token in ("大周期", "训练计划", "周计划", "训练课表")):
        return True
    has_action = any(keyword.lower() in text for keyword in PLAN_ACTION_KEYWORDS)
    has_time = any(keyword.lower() in text for keyword in PLAN_TIME_KEYWORDS)
    return has_action and has_time


def _unique_labels(labels: list[str]) -> list[str]:
    return list(dict.fromkeys(label for label in labels if label))


TEMPORAL_PLAN_CONTEXT_KEYWORDS = [
    "本周", "下周", "这周", "上周", "本次", "下次",
    "明天", "后天", "接下来", "周期", "训练计划", "周计划",
]


def _derive_intent_labels(query: str, lower_query: str) -> tuple[list[str], str]:
    labels: list[str] = []
    is_plan = _looks_like_plan_request(query) or "计划" in query or "训练安排" in query
    has_research = any(keyword in lower_query for keyword in [k.lower() for k in RESEARCH_KEYWORDS])
    risk_query = _strip_negated_status_phrases(lower_query)
    has_adaptive_signal = any(keyword in risk_query for keyword in [k.lower() for k in ADAPTIVE_SIGNAL_KEYWORDS])
    has_adaptive_command = any(keyword in lower_query for keyword in [k.lower() for k in ADAPTIVE_ADJUSTMENT_KEYWORDS])
    # Adaptive mode requires explicit plan-adjustment context (temporal ref or plan keyword).
    # Pure injury advisory queries ("膝盖痛怎么调整训练量") route to QA/team mode instead.
    has_temporal_plan_context = is_plan or any(kw in lower_query for kw in TEMPORAL_PLAN_CONTEXT_KEYWORDS)
    has_adaptive = (
        any(keyword in lower_query for keyword in [k.lower() for k in ADAPTIVE_KEYWORDS])
        or (has_adaptive_signal and has_adaptive_command and has_temporal_plan_context)
    )
    has_nutrition = any(keyword in lower_query for keyword in [k.lower() for k in NUTRITION_KEYWORDS])
    has_profile_signal = any(keyword in lower_query for keyword in [k.lower() for k in PROFILE_SIGNAL_KEYWORDS])

    if has_adaptive:
        labels.append("adaptive_adjustment")
    if is_plan:
        labels.append("training_plan")
    if has_research:
        labels.append("general_qa")
    if has_nutrition:
        labels.append("nutrition_query")
    if has_profile_signal and not is_plan and not has_adaptive:
        labels.append("profile_signal")
    if not labels:
        labels.append("general_qa")

    priority_order = [
        "adaptive_adjustment",
        "training_plan",
        "nutrition_query",
        "general_qa",
    ]
    unique = _unique_labels(labels)
    priority = next((label for label in priority_order if label in unique), unique[0])
    return unique, priority


async def router_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    query = state.get("query", "")
    lower_query = query.lower()
    risk_query = _strip_negated_status_phrases(lower_query)
    intent_labels, intent_priority = _derive_intent_labels(query, lower_query)

    if intent_priority == "adaptive_adjustment":
        workflow_kind = "adaptive"
        intent_type = "plan"
    elif any(keyword in lower_query for keyword in [k.lower() for k in RESEARCH_KEYWORDS]):
        workflow_kind = "research"
        intent_type = "qa"
    else:
        if _looks_like_plan_request(query):
            workflow_kind = "plan"
            intent_type = "plan"
        elif "计划" in query or "训练安排" in query:
            workflow_kind = "plan"
            intent_type = "plan"
        else:
            workflow_kind = "qa"
            intent_type = "qa"

    mode = {
        "plan": "subagent",
        "research": "research",
        "adaptive": "adaptive",
        "qa": "team",
    }.get(workflow_kind, "team")

    category = "coach"
    if any(keyword in lower_query for keyword in [k.lower() for k in NUTRITION_KEYWORDS]):
        category = "nutritionist"
    elif any(keyword in risk_query for keyword in [k.lower() for k in THERAPY_KEYWORDS]):
        category = "therapist"
    elif workflow_kind == "research":
        category = "research"

    return {
        "mode": mode,
        "workflow_kind": workflow_kind,
        "intent_labels": intent_labels,
        "intent_priority": intent_priority,
        "category": category,
        "intent_type": intent_type,
        "iteration_count": 0,
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": [
            f"[router] workflow_kind={workflow_kind}, intent={intent_type}, "
            f"category={category}, labels={intent_labels}, priority={intent_priority}"
        ],
        "rag_sources": [],
    }
