from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set


PROFILE_FIELD_LABELS = {
    "goal": "目标",
    "weekly_mileage": "周跑量",
    "experience_level": "经验水平",
    "weight_kg": "体重",
    "sex": "性别",
    "diet_type": "饮食类型",
    "sweat_rate": "出汗率",
    "gi_sensitivity": "胃肠敏感度",
    "lthr": "LTHR",
    "t_pace": "T-Pace",
}

NUTRITION_FIELD_ALIASES = {
    "weight_kg",
    "sex",
    "diet_preference",
    "sweat_rate",
    "gi_sensitivity",
}


def _confirmed_field_names(profile: Dict[str, Any]) -> Set[str]:
    raw = profile.get("_confirmed_fields") or profile.get("confirmed_fields") or []
    if isinstance(raw, str):
        return {item.strip() for item in raw.split(",") if item.strip()}
    if isinstance(raw, Iterable):
        return {str(item).strip() for item in raw if str(item).strip()}
    return set()


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def filter_confirmed_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """只保留用户明确确认过的画像字段，避免默认值进入模型上下文。"""

    if not isinstance(profile, dict):
        return {}
    confirmed = _confirmed_field_names(profile)
    filtered: Dict[str, Any] = {}
    used_fields: List[str] = []

    for field in PROFILE_FIELD_LABELS:
        if field not in confirmed:
            continue
        value = profile.get(field)
        if _has_value(value):
            filtered[field] = value
            used_fields.append(field)

    nutrition = profile.get("nutrition_profile") if isinstance(profile.get("nutrition_profile"), dict) else {}
    filtered_nutrition: Dict[str, Any] = {}
    for field in NUTRITION_FIELD_ALIASES:
        if field not in confirmed:
            continue
        value = nutrition.get(field)
        if _has_value(value):
            filtered_nutrition[field] = value
            if field not in used_fields:
                used_fields.append(field)
    if filtered_nutrition:
        filtered["nutrition_profile"] = filtered_nutrition

    filtered["_profile_context"] = {
        "used_profile_fields": used_fields,
        "missing_fields": [],
        "assumptions": [],
    }
    if not used_fields:
        filtered.pop("_profile_context")
    return filtered


def profile_context_metadata(profile: Dict[str, Any]) -> Dict[str, Any]:
    filtered = filter_confirmed_profile(profile)
    return filtered.get("_profile_context", {"used_profile_fields": [], "missing_fields": [], "assumptions": []})


def build_prompt_profile_summary(profile: Dict[str, Any]) -> str:
    filtered = filter_confirmed_profile(profile)
    if not filtered:
        return "本轮无已确认画像字段；不要假设体重、目标成绩、经验等级、配速或训练背景。"

    nutrition = filtered.get("nutrition_profile") if isinstance(filtered.get("nutrition_profile"), dict) else {}
    lines: List[str] = []
    for field, label in PROFILE_FIELD_LABELS.items():
        value = filtered.get(field)
        if not _has_value(value) and field in nutrition:
            value = nutrition.get(field)
        if not _has_value(value):
            continue
        if field == "weekly_mileage":
            lines.append(f"{label}: {value} km")
        elif field == "weight_kg":
            lines.append(f"{label}: {value} kg")
        else:
            lines.append(f"{label}: {value}")
    return "\n".join(lines) if lines else "本轮无已确认画像字段；不要假设体重、目标成绩、经验等级、配速或训练背景。"
