"""跑者原型判断顾问：LLM 读取画像 → 输出结构化 RunnerArchetypeInput。

替代 _build_hm_archetype_input 的关键词匹配，LLM 不可用时静默降级到原有关键词路径。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("archetype_advisor")

from marathon_qa_assistant.core.half_marathon_protocol import RunnerArchetypeInput

# ── 字段定义（给 LLM 看的字段说明） ──────────────────────────────────────

_ARCHETYPE_FIELD_DESCRIPTIONS = {
    "recent_marathon": "跑者近期（1个月内）是否完成过全马比赛",
    "build_weeks": "可用训练周数（即 total_weeks 参数，强制使用输入值）",
    "endurance_background": "是否有长距离耐力背景（越野/超马 trail/ultra 等）",
    "marathon_background": "是否有全马或马拉松训练经历",
    "long_training_gap": "是否长期中断系统训练或久疏战阵",
    "middle_distance_background": "是否有中距离田径背景（1500m/3K/5K）",
    "speed_strength": "是否以速度能力见长（短距离速度突出）",
    "half_marathon_experience_low": "是否半马参赛经验不足",
    "weekly_mileage_km": "当前每周总跑量（公里），取自画像的 weekly_mileage 字段",
    "injury_or_fatigue": "近期是否有伤病、慢性疲劳、过度训练迹象",
}


# ── LLM 提示词 ────────────────────────────────────────────────────────────


def _build_archetype_prompt(profile: Dict[str, Any], total_weeks: int) -> str:
    profile_text = json.dumps(profile, ensure_ascii=False, default=str)
    fields_desc = "\n".join(
        f"  - `{name}` ({descr})"
        for name, descr in _ARCHETYPE_FIELD_DESCRIPTIONS.items()
    )
    parts = [
        "你是一位运动训练学专家，负责从跑者画像中提取结构化判断字段，用于跑者原型匹配。",
        "",
        "## 画像原始数据",
        profile_text[:2500],
        "",
        "## 需输出的字段（及含义）",
        fields_desc,
        "",
        "## 输出规则",
        f"1. `build_weeks` 必须设为 {total_weeks}（不可以修改）",
        "2. `weekly_mileage_km` 从 profile 的 `weekly_mileage` 字段取值，为 None 则不填",
        "3. 布尔字段仅当有明确证据支撑时才设为 true",
        "4. evidence 字段解释每个字段判断的理由，引用 profile 中的关键词语",
        "",
        "## 输出格式（严格 JSON，不要有其他文字）",
        "{",
        '  "fields": {',
        '    "recent_marathon": false,',
        '    "build_weeks": 12,',
        '    "endurance_background": false,',
        '    "marathon_background": true,',
        '    "long_training_gap": false,',
        '    "middle_distance_background": false,',
        '    "speed_strength": false,',
        '    "half_marathon_experience_low": false,',
        '    "weekly_mileage_km": 58.0,',
        '    "injury_or_fatigue": false',
        "  },",
        '  "evidence": {',
        '    "marathon_background": "profile.training_background 中含「全马」",',
        '    "weekly_mileage_km": "profile.weekly_mileage = 58"',
        "  }",
        "}",
        "",
        "JSON:",
    ]
    return "\n".join(parts)


# ── 解析 ──────────────────────────────────────────────────────────────────


def _parse_archetype_response(
    raw: str,
    total_weeks: int,
) -> Optional[Tuple[RunnerArchetypeInput, Dict[str, str]]]:
    if not raw:
        return None
    text = raw.strip()
    if "```" in text:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start:end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("archetype advisor: LLM 响应不是有效 JSON")
        return None

    fields = data.get("fields") or {}
    evidence = {
        str(k): str(v)
        for k, v in (data.get("evidence") or {}).items()
    }

    def _bool(key: str) -> bool:
        v = fields.get(key)
        return bool(v) if isinstance(v, bool) else False

    def _float_or_none(key: str) -> Optional[float]:
        v = fields.get(key)
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    return (
        RunnerArchetypeInput(
            recent_marathon=_bool("recent_marathon"),
            build_weeks=total_weeks,
            endurance_background=_bool("endurance_background"),
            marathon_background=_bool("marathon_background"),
            long_training_gap=_bool("long_training_gap"),
            middle_distance_background=_bool("middle_distance_background"),
            speed_strength=_bool("speed_strength"),
            half_marathon_experience_low=_bool("half_marathon_experience_low"),
            weekly_mileage_km=_float_or_none("weekly_mileage_km"),
            injury_or_fatigue=_bool("injury_or_fatigue"),
        ),
        evidence,
    )


# ── 主入口 ────────────────────────────────────────────────────────────────


def get_archetype_advisory(
    profile: Dict[str, Any],
    total_weeks: int,
    enable_llm: bool = True,
) -> Tuple[Optional[RunnerArchetypeInput], Dict[str, str]]:
    """从跑者画像构建 RunnerArchetypeInput，LLM 不可用时返回 None。

    返回：
        (RunnerArchetypeInput | None, field_evidence)
        - 返回 None → 调用方走 _build_hm_archetype_input 关键词 fallback
    """
    if not enable_llm:
        return None, {}

    try:
        from marathon_qa_assistant.core.periodization_advisor import _call_llm_sync  # noqa: E402
    except ImportError:
        logger.debug("archetype advisor: 无法导入 _call_llm_sync")
        return None, {}

    prompt = _build_archetype_prompt(profile, total_weeks)
    raw = _call_llm_sync(prompt, timeout_sec=45.0)
    if not raw:
        return None, {}

    result = _parse_archetype_response(raw, total_weeks)
    if result is None:
        return None, {}

    runner_input, evidence = result
    logger.info(
        "archetype advisor: LLM 解析成功 marathon=%s endurance=%s speed=%s",
        runner_input.marathon_background,
        runner_input.endurance_background,
        runner_input.speed_strength,
    )
    return runner_input, evidence
