import json
import logging
from typing import Any, Dict

from .app_state import USER_PROFILE_PATH
from .physiology import calculate_hr_zones, calculate_pace_zones, is_zone_empty

logger = logging.getLogger("workflow_engine")


DEFAULT_PROFILE: Dict[str, Any] = {
    "experience_level": "进阶",
    "weekly_mileage": 30.0,
    "goal": "维持健康",
    "injury_history": ["无"],
    "long_term_memory": [],
    "verified_facts": {},
    "last_race_time": "未知",
    "pb_800m": "",
    "pb_1500m": "",
    "pb_5k": "",
    "pb_10k": "",
    "pb_half": "",
    "pb_full": "",
    "lthr": 0,
    "t_pace": "",
    "hr_zones": {},
    "pace_zones": {},
    "nutrition_profile": {
        "weight_kg": 65.0,
        "diet_preference": "无偏好",
        "allergies": [],
        "daily_calories": 2500,
        "hydration_strategy": "运动中每 20 分钟饮水 150-250ml",
    },
    "target_race_date": "",
    "plan_duration_weeks": 12,
}


def _coerce_number(value: Any, default: float = 0) -> float:
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = value.strip().replace("+", "")
        try:
            return float(text)
        except ValueError:
            return default
    return default


def sync_user_zones(profile: Dict[str, Any]) -> bool:
    """
    根据 LTHR 和 T-Pace 同步心率和配速区间。
    如果数据有变动，返回 True。
    """
    changed = False
    
    # 1. 同步心率区间 (强制 9 区)
    lthr = _coerce_number(profile.get("lthr", 0))
    if lthr > 40:
        hr_zones = profile.get("hr_zones", {})
        # 如果是空的，或者不是 9 区，或者需要根据最新逻辑重算
        if is_zone_empty(hr_zones, expected_count=9):
            profile["hr_zones"] = calculate_hr_zones(lthr)
            changed = True
            logger.info(f"已自动计算 9区心率区间 (LTHR: {lthr})")
            
    # 2. 同步配速区间 (强制 9 区)
    t_pace = profile.get("t_pace", "")
    if t_pace:
        pace_zones = profile.get("pace_zones", {})
        if is_zone_empty(pace_zones, expected_count=9):
            profile["pace_zones"] = calculate_pace_zones(t_pace)
            changed = True
            logger.info(f"已自动计算 9区配速区间 (T-Pace: {t_pace})")
            
    return changed


def load_user_profile() -> Dict[str, Any]:
    """从磁盘加载用户画像，并在 schema 演进后自动补默认值。"""
    profile = DEFAULT_PROFILE.copy()
    if USER_PROFILE_PATH.exists():
        try:
            with open(USER_PROFILE_PATH, "r", encoding="utf-8") as file:
                saved = json.load(file)
            for key, value in DEFAULT_PROFILE.items():
                saved.setdefault(key, value)
            profile = saved
        except Exception as exc:
            logger.warning(f"加载用户画像失败: {exc}")

    # 清理旧的带括号的 key (历史遗留)
    has_legacy = False
    for zone_type in ["hr_zones", "pace_zones"]:
        zones = profile.get(zone_type, {})
        if any("(" in str(key) for key in zones.keys()):
            profile[zone_type] = {}
            has_legacy = True

    # 执行同步逻辑
    changed = sync_user_zones(profile)
    
    # 如果是因为版本演进（补全 9区或清理旧数据）导致的数据变动，主动写回磁盘
    if changed or has_legacy:
        save_user_profile(profile)

    return profile


def save_user_profile(profile: Dict[str, Any]) -> None:
    """持久化用户画像。保存前会自动同步区间数据。"""
    try:
        # 保存前强制触发一次同步，确保修改了 lthr/t_pace 后区间随之更新
        # 注意：这里我们放宽 sync_user_zones 的触发条件，或者直接在这里强制重算
        lthr = _coerce_number(profile.get("lthr", 0))
        if lthr > 40:
            profile["hr_zones"] = calculate_hr_zones(lthr)
        if profile.get("t_pace"):
            profile["pace_zones"] = calculate_pace_zones(profile["t_pace"])

        USER_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(USER_PROFILE_PATH, "w", encoding="utf-8") as file:
            json.dump(profile, file, ensure_ascii=False, indent=2)
        logger.info("用户画像已保存并同步区间数据。")
    except Exception as exc:
        logger.error(f"保存用户画像失败: {exc}")
