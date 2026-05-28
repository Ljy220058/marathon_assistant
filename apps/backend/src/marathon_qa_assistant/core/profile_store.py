import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from .app_state import USER_PROFILE_PATH
from .physiology import calculate_hr_zones, calculate_pace_zones, is_zone_empty

logger = logging.getLogger("workflow_engine")


def _get_user_profile_path(user_id: str = "default_user") -> Path:
    """返回用户级别的画像文件路径。多用户模式下每个用户有独立文件。"""
    if user_id == "default_user":
        return USER_PROFILE_PATH
    user_dir = USER_PROFILE_PATH.parent / "users" / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / "profile.json"


def _encrypt_data(data: str) -> str:
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return data
    key = os.getenv("MARATHON_FERNET_KEY", "").strip()
    if not key:
        return data
    try:
        return Fernet(key.encode("utf-8")).encrypt(data.encode("utf-8")).decode("utf-8")
    except Exception:
        return data


def _decrypt_data(encrypted: str) -> str:
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return encrypted
    key = os.getenv("MARATHON_FERNET_KEY", "").strip()
    if not key:
        return encrypted
    try:
        return Fernet(key.encode("utf-8")).decrypt(encrypted.encode("utf-8")).decode("utf-8")
    except Exception:
        return encrypted


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


def load_user_profile(user_id: str = "default_user") -> Dict[str, Any]:
    """从磁盘加载用户画像，并在 schema 演进后自动补默认值。"""
    profile = DEFAULT_PROFILE.copy()
    profile_path = _get_user_profile_path(user_id)
    if profile_path.exists():
        try:
            raw = profile_path.read_text(encoding="utf-8")
            saved = json.loads(_decrypt_data(raw))
            for key, value in DEFAULT_PROFILE.items():
                saved.setdefault(key, value)
            profile = saved
        except Exception as exc:
            logger.warning(f"加载用户画像失败 (user={user_id}): {exc}")

    # 清理旧的带括号的 key (历史遗留)
    has_legacy = False
    for zone_type in ["hr_zones", "pace_zones"]:
        zones = profile.get(zone_type, {})
        if any("(" in str(key) for key in zones.keys()):
            profile[zone_type] = {}
            has_legacy = True

    # 执行同步逻辑
    changed = sync_user_zones(profile)

    # 如果是因为版本演进导致的数据变动，主动写回磁盘
    if changed or has_legacy:
        save_user_profile(profile, user_id)

    return profile


def save_user_profile(profile: Dict[str, Any], user_id: str = "default_user") -> None:
    """持久化用户画像。保存前会自动同步区间数据。"""
    try:
        lthr = _coerce_number(profile.get("lthr", 0))
        if lthr > 40:
            profile["hr_zones"] = calculate_hr_zones(lthr)
        if profile.get("t_pace"):
            profile["pace_zones"] = calculate_pace_zones(profile["t_pace"])

        profile_path = _get_user_profile_path(user_id)
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(profile, ensure_ascii=False, indent=2)
        profile_path.write_text(_encrypt_data(payload), encoding="utf-8")
        logger.info(f"用户画像已保存并同步区间数据 (user={user_id})。")
    except Exception as exc:
        logger.error(f"保存用户画像失败 (user={user_id}): {exc}")
