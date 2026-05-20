import json
import logging
from typing import Any, Dict, Tuple

try:
    from langchain_core.runnables import RunnableConfig
except ImportError:
    RunnableConfig = Any

from marathon_qa_assistant.core.profile_store import load_user_profile, save_user_profile
from marathon_qa_assistant.core.state_models import IntegratedState
from marathon_qa_assistant.nodes.common import ai_invoke, ensure_usage

logger = logging.getLogger("workflow_engine")

PROFILE_UPDATE_SYSTEM = """你是一个训练画像智能管家。分析用户消息，判断他们是想**更新**自己的训练数据，还是仅仅在**询问概念**。

你可以更新的字段及示例：

| 字段 | 说明 | 示例表达 |
|------|------|---------|
| lthr | 乳酸阈心率 (bpm, 纯数字) | "乳酸阈心率180"、"LTHR是175"、"我心率阈值172" |
| t_pace | 阈值/目标配速 | "配速3:30/km"、"T配速是4:00" |
| weekly_mileage | 周跑量 (km, 纯数字) | "周跑量80"、"每周跑60公里" |
| vo2max | 最大摄氧量 (纯数字) | "VO2max是55"、"最大摄氧量60" |
| pb_5k | 5公里最好成绩 | "5K PB 19:30"、"5000米跑进20分"、"五公里19分半" |
| pb_10k | 10公里最好成绩 | "10K 42分"、"万米PB了 40:00" |
| pb_half | 半马最好成绩 | "半马135"、"半马PB 1:30:00" |
| pb_full | 全马最好成绩 | "全马330"、"马拉松破三" |
| experience_level | 经验水平 | "我现在算进阶了"、"水平是精英" |
| goal | 目标赛事/成绩 | "目标全马330"、"想跑进半马130" |
| target_race_date | 比赛日期 | "比赛在6月15号"、"距比赛2个月" |
| available_days | 可用训练日 | "我周一三五训练" |
| max_session_minutes | 单次最长训练分钟 | "最多跑90分钟" |

返回 JSON（严格只输出 JSON，不要 Markdown 代码块包裹）：
{
  "action": "update" 或 "question",
  "confidence": 0.0 到 1.0,
  "fields": {"字段名": "新值"},
  "message": "面向用户的简短确认语"
}

判断规则：
- "action": "update"：用户在陈述自己的数据，不论是否显式用了"更新/改为/设为"等动词
  例："乳酸阈心率为180" → update、"我5K PB了 19分半" → update
- "action": "question"：用户明显在问概念或寻求评估
  例："什么是乳酸阈"、"PB怎么算"、"乳酸阈180算高吗"、"配速怎么提高"
- 如果用户既提供了数据又问了问题（如"乳酸阈180正常吗"），action 用 "question" 但 fields 仍可提取
- confidence 低于 0.6 时即使 action=update 也会被系统当作非更新处理
- 若用户只说了"我PB了"但没给具体成绩，不要填 fields，confidence 设低"""


_FIELD_LABEL_MAP = {
    "lthr": "乳酸阈心率",
    "t_pace": "阈值配速",
    "weekly_mileage": "周跑量",
    "vo2max": "VO₂max",
    "pb_5k": "5K PB",
    "pb_10k": "10K PB",
    "pb_half": "半马 PB",
    "pb_full": "全马 PB",
    "experience_level": "经验水平",
    "goal": "目标赛事",
    "target_race_date": "比赛日期",
    "available_days": "可用训练日",
    "max_session_minutes": "单次最长训练",
}

NUMERIC_FIELDS = {"lthr", "weekly_mileage", "vo2max", "max_session_minutes"}


def _field_label(key: str) -> str:
    return _FIELD_LABEL_MAP.get(key, key)


def _normalize_value(field_key: str, value: Any) -> Any:
    if value is None:
        return None
    if field_key in NUMERIC_FIELDS:
        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError:
                try:
                    return float(value.strip())
                except ValueError:
                    return value.strip()
        return int(value) if isinstance(value, float) else value
    if isinstance(value, str):
        return value.strip()
    return value


def _build_snapshot(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {
        k: profile.get(k, 0 if k in NUMERIC_FIELDS else "")
        for k in _FIELD_LABEL_MAP
    }


async def profile_update_node(state: IntegratedState, config: RunnableConfig) -> dict:
    query = state.get("query", "")
    profile = load_user_profile()
    usage = ensure_usage(state.get("token_usage"))
    current_snapshot = _build_snapshot(profile)

    prompt = (
        f"{PROFILE_UPDATE_SYSTEM}\n\n"
        f"用户当前档案：{json.dumps(current_snapshot, ensure_ascii=False)}\n\n"
        f"用户消息：\"{query}\"\n\n"
        f"请判断意图并返回 JSON。"
    )

    try:
        raw, usage = await ai_invoke(prompt, config, usage)
    except Exception as exc:
        logger.warning(f"[profile_update] LLM 不可用，回退非更新模式: {exc}")
        return {
            "profile_update__is_update": False,
            "token_usage": usage,
            "reasoning_log": ["[profile_update] LLM 不可用，委托给普通 QA"],
        }

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if 0 <= start < end:
            result = json.loads(raw[start:end])
        else:
            raise ValueError("No JSON found")
    except Exception as exc:
        logger.warning(f"[profile_update] JSON 解析失败: raw={raw[:200]}, err={exc}")
        return {
            "profile_update__is_update": False,
            "token_usage": usage,
            "reasoning_log": ["[profile_update] JSON 解析失败，委托给普通 QA"],
        }

    action = str(result.get("action", "question")).strip().lower()
    confidence = float(result.get("confidence", 0) or 0)
    fields = result.get("fields") or {}
    message = str(result.get("message", "") or "").strip()

    if action != "update" or not isinstance(fields, dict) or not fields or confidence < 0.6:
        logger.info(
            f"[profile_update] 判定为非更新意图 "
            f"(action={action}, confidence={confidence}, fields={len(fields) if isinstance(fields, dict) else 0})"
        )
        return {
            "profile_update__is_update": False,
            "intent_type": "qa",
            "token_usage": usage,
            "reasoning_log": [
                f"[profile_update] 非更新意图 (confidence={confidence})，委托给普通 QA"
            ],
        }

    changed: list = []
    for field_key, raw_value in fields.items():
        if field_key not in current_snapshot:
            logger.warning(f"[profile_update] 未知字段: {field_key}")
            continue
        new_value = _normalize_value(field_key, raw_value)
        old_value = current_snapshot[field_key]
        if str(old_value) != str(new_value):
            profile[field_key] = new_value
            changed.append((field_key, old_value, new_value))

    if not changed:
        logger.info("[profile_update] 未检测到实际变更")
        return {
            "profile_update__is_update": True,
            "final_report": "ℹ️ 你提供的信息和当前档案一致，无需更新。",
            "token_usage": usage,
            "reasoning_log": ["[profile_update] 值未变化，跳过"],
        }

    save_user_profile(profile)

    lines = [
        f"- **{_field_label(k)}**: `{v_old}` → `{v_new}`"
        for k, v_old, v_new in changed
    ]
    changes_md = "\n".join(lines)
    note = f"\n> {message}" if message else ""

    final_report = (
        f"### 🏷️ 训练画像已更新\n\n"
        f"{changes_md}\n"
        f"{note}\n\n"
        f"💡 训练计划和心率/配速区间将基于新数据重新计算。"
    )

    logger.info(
        f"[profile_update] 已更新 {len(changed)} 个字段: {[c[0] for c in changed]} "
        f"(confidence={confidence})"
    )

    return {
        "profile_update__is_update": True,
        "user_profile": profile,
        "final_report": final_report,
        "token_usage": usage,
        "reasoning_log": [
            f"[profile_update] 已更新 {len(changed)} 个字段 "
            f"({', '.join(_field_label(c[0]) for c in changed)}) (confidence={confidence})"
        ],
    }
