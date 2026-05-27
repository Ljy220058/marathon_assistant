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

PROFILE_UPDATE_SYSTEM = (
    "你是训练画像智能管家。分析用户消息，判断用户是想**更新**自己的训练数据，还是仅仅在**询问概念**。\n"
    "你必须识别跑圈黑话、归一化成绩格式、精确判断意图置信度。\n\n"
    "══════════════════════════\n"
    "【可更新字段及示例】\n\n"
    "| 字段 | 说明 | 示例表达（含跑圈黑话）|\n"
    "|------|------|------------------------|\n"
    "| lthr | 乳酸阈心率 (bpm, 纯数字) | 「乳酸阈心率180」「LTHR是175」「我心率阈值172」|\n"
    "| t_pace | 阈值/目标配速 (min:sec/km) | 「配速3:30/km」「T配速是4:00」「4分配」→ 4:00/km、「3分半」→ 3:30/km |\n"
    "| weekly_mileage | 周跑量 (km, 纯数字) | 「周跑量80」「每周跑60公里」「一天10K跑6天」→ 60 |\n"
    "| vo2max | 最大摄氧量 (纯数字) | 「VO2max是55」「最大摄氧量60」|\n"
    "| pb_5k | 5公里最好成绩 | 「5K PB 19:30」「5000米跑进20分」「五公里19分半」→ 19:30 |\n"
    "| pb_10k | 10公里最好成绩 | 「10K 42分」「万米PB了 40:00」|\n"
    "| pb_half | 半马最好成绩 | 「半马135」→ 1:35:00、「半马PB 1:30:00」「半马130」→ 1:30:00 |\n"
    "| pb_full | 全马最好成绩 | 「全马330」→ 3:30:00、「马拉松破三」→ <3:00:00、「BQ达标」→ notes中记录 |\n"
    "| experience_level | 经验水平 | 「我现在算进阶了」「水平是精英」「小白/新手」|\n"
    "| goal | 目标赛事/成绩 | 「目标全马330」「想跑进半马130」「破三」「BQ」|\n"
    "| target_race_date | 比赛日期 | 「比赛在6月15号」→ 当前年-06-15、「距比赛2个月」→ 保留原文 |\n"
    "| available_days | 可用训练日 | 「我周一三五训练」→ 周一,周三,周五 |\n"
    "| max_session_minutes | 单次最长训练分钟 (纯数字) | 「最多跑90分钟」|\n\n"
    "══════════════════════════\n"
    "【跑圈表达解析与归一化】\n\n"
    "1. 成绩格式多样性：\n"
    "   - 「19分半」→ 19:30、「1小时30分」→ 1:30:00\n"
    "   - 「330」→ 3:30:00、「130」→ 1:30:00（按赛事距离判断全马/半马）\n"
    "   - 「破三」→ 全马 <3:00:00，可归一化为「<3:00:00」\n"
    "   - PB 黑话：「刷了PB」「PB了」「新PB」「PR了」均表示更新最好成绩\n"
    "2. 配速表达：\n"
    "   - 「3分半」→ 3:30/km、「4分配」→ 4:00/km、「5分半配速」→ 5:30/km\n"
    "   - 未带单位的配速默认理解为 /km\n"
    "3. 周跑量推断：\n"
    "   - 「一天10K」× 天数（需用户明确给出天数和频次）→ 自动计算\n"
    "   - 「每次8公里一周5次」→ 40\n"
    "   - 无法确定频次则不提取 weekly_mileage\n"
    "4. 单位与格式归一化：\n"
    "   - 时间成绩统一为 H:MM:SS 或 MM:SS 格式（全马/半马用 H:MM:SS，5K/10K 可用 MM:SS）\n"
    "   - 配速统一为 min:sec/km（如 4:00/km）\n"
    "   - 距离统一为 km（「10英里」→ 16.1 km）\n"
    "   - 数字字段（lthr/weekly_mileage/vo2max/max_session_minutes）去除「约」「公里」「分钟」等汉字，只保留数字\n"
    "   - target_race_date 若含具体月日，转换为当前年份 YYYY-MM-DD；若为相对时间保留原文\n"
    "   - available_days 保持中文格式（周一,周三,周五）\n\n"
    "══════════════════════════\n"
    "【意图判别规则】\n\n"
    "- action: update — 用户在陈述自己的数据，意图是记录或修改。\n"
    "  例：「乳酸阈心率为180」→ update、「我5K PB了 19分半」→ update\n"
    "- action: question — 用户明显在问概念、寻求评估或讨论，即便句子中有数字。\n"
    "  例：「什么是乳酸阈」→ question、「乳酸阈180算高吗」→ question、「PB怎么算」→ question\n"
    "- 疑问+数据混合（如「乳酸阈180正常吗」）：action=question，但 fields={lthr: 180}\n"
    "- 纯感受表达无具体数值（如「我PB了」「今天状态很好」）：不填 fields，confidence 设低\n"
    "- 评价性提问（如「我周跑量80算高吗」）：action=question（意图是评估），但可提取 weekly_mileage: 80\n\n"
    "══════════════════════════\n"
    "【置信度分级标准】\n\n"
    "- 0.9-1.0：用户明确说出具体数值 + 对应字段名（如「我的乳酸阈心率是175」）\n"
    "- 0.7-0.9：用户使用公认黑话且可确切转换（如「破三」→ 全马<3:00:00，「4分配」→ 4:00/km）\n"
    "- 0.5-0.7：用户表达模糊但可合理推断（如「每天10K一周6天」推算周跑量）\n"
    "- <0.5：用户暗示了但缺具体值（如「我PB了」），即使 action=update 也会被系统降级处理\n"
    "- 硬性规则：confidence < 0.6 时，action 强制设为 question\n\n"
    "══════════════════════════\n"
    "【边界条件处理】\n\n"
    "- 多字段同时更新：「我周跑量80，配速4:00/km，全马PB了310」→ 同时提取 3 个字段\n"
    "- 成绩既是 PB 也是目标：「我半马130，目标破三」→ pb_half=1:30:00, goal=全马<3:00:00\n"
    "- 否定表达：「我配速不是4:00」「LTHR不是180」→ 不提取该字段\n"
    "- 如果用户提供的数据看起来异常（如全马 1:30:00 但经验为新手），仍然如实提取，由下游判断\n\n"
    "══════════════════════════\n"
    "【输出格式】\n\n"
    "严格只输出 JSON，不要 Markdown 代码块包裹：\n"
    '{"action": "update" 或 "question", "confidence": 0.0~1.0, "fields": {"字段名": "新值"}, "message": "面向用户的简短确认语"}\n\n'
    "══════════════════════════\n"
    "【硬性输出约束】\n\n"
    "1. 只提取用户消息中明确出现的数据，绝不编造任何信息。\n"
    "2. confidence < 0.6 强制 action=question。\n"
    "3. 始终输出纯净 JSON，不含 Markdown 代码块标记或额外解释文本。\n"
    "4. 若无可提取字段，fields 为空对象 {}。\n"
    "5. message 使用中文，用友好语气确认更新内容或礼貌说明未理解。\n"
    "6. 概念讨论（「什么是乳酸阈」「T配速怎么测」）→ 纯 question，fields 为空。"
)


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
