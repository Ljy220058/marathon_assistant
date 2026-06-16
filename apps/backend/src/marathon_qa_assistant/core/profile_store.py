import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

from .app_state import USER_PROFILE_PATH
from .settings import get_settings
from .physiology import calculate_hr_zones, calculate_pace_zones, is_zone_empty

logger = logging.getLogger("workflow_engine")


def _extract_target_hmp_seconds(profile: Dict[str, Any]) -> int:
    """从画像字段中提取目标半马配速（秒/km）。"""
    # 直接字段 target_hmp（格式如 "4:16"）
    hmp_raw = profile.get("target_hmp", "")
    if hmp_raw:
        sec = _parse_pace_seconds(hmp_raw)
        if sec and sec >= 130:  # P2: 拒绝不合理的快速配速（< 2:10/km）
            return sec

    # target_pace（格式如 "4:16/km" 或 "4:16"）
    target_pace = str(profile.get("target_pace") or "").strip()
    if target_pace:
        sec = _parse_pace_seconds(target_pace)
        # P2: 配速必须 >= 130s/km（2:10/km），否则视为无效/错误数据并回退到后续字段
        if sec and sec >= 130:
            return sec

    # target_half_time（格式如 "1:30:00"），反算配速
    target_half = str(profile.get("target_half_time") or "").strip()
    if target_half:
        total_sec = _parse_duration_seconds(target_half)
        if total_sec and total_sec > 0:
            return round(total_sec / 21.0975)

    # 从 goal 文本推断
    goal = str(profile.get("goal") or "").strip()
    if goal:
        # 尝试匹配 "半马 SUB 1:30"、"半马 1:30" 等（H:MM 格式表示小时:分钟）
        m = re.search(r"半马\s*(?:sub\s*)?(\d{1,2}):(\d{2})", goal)
        if m:
            # P2: H:MM 格式 — group(1) 为小时，group(2) 为分钟
            total_sec = int(m.group(1)) * 3600 + int(m.group(2)) * 60
            return round(total_sec / 21.0975)

    return 0


def _parse_pace_seconds(text: str) -> Optional[int]:
    """解析 'M:SS' 或 'M:SS/km' 格式为秒数。"""
    text = str(text or "").strip().replace("/km", "").replace("/公里", "")
    m = re.search(r"(\d+)\s*[:：]\s*(\d{1,2})", text)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    return None


def _parse_duration_seconds(text: str) -> Optional[int]:
    """解析 'H:MM:SS' 或 'M:SS' 格式为总秒数。"""
    text = str(text or "").strip().replace("：", ":")
    parts = text.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        pass
    return None


def _get_user_profile_path(user_id: str = "default_user") -> Path:
    """返回用户级别的画像文件路径（仅用于迁移兼容）。"""
    if user_id == "default_user":
        return USER_PROFILE_PATH
    user_dir = USER_PROFILE_PATH.parent / "users" / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / "profile.json"


def _get_db():
    """惰性获取数据库实例，避免模块级循环导入。"""
    from marathon_qa_assistant.services.database import get_db
    return get_db()


def _encrypt_data(data: str) -> str:
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return data
    key = get_settings().fernet_key
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
    key = get_settings().fernet_key
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
    如果提供了目标 HMP，Z5（马拉松专项区）以 HMP 为中心排列。
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
        target_hmp = _extract_target_hmp_seconds(profile)
        needs_pace_sync = is_zone_empty(pace_zones, expected_count=9)
        has_target = target_hmp > 0
        # P2: 即使区间非空，若有 HMP 目标或之前无目标时也应重算，确保 Z5 联动更新
        if needs_pace_sync or has_target:
            new_pace_zones = calculate_pace_zones(t_pace, target_hmp_seconds=target_hmp)
            # 仅当计算结果与现有区间不同时才写入，避免 load 时不必要的磁盘写回
            if new_pace_zones != pace_zones:
                profile["pace_zones"] = new_pace_zones
                changed = True
                if target_hmp:
                    logger.info(
                        f"已自动计算 9区配速区间 (T-Pace: {t_pace}, "
                        f"Z5 以目标 HMP 为中心: {target_hmp}s/km)"
                    )
                else:
                    logger.info(f"已自动计算 9区配速区间 (T-Pace: {t_pace}, 暂无目标 HMP)")

    return changed


def load_user_profile(user_id: str = "default_user") -> Dict[str, Any]:
    """从数据库加载用户画像；首次启动时自动迁移 profile.json 文件到 DB。"""
    profile = DEFAULT_PROFILE.copy()

    db = _get_db()
    raw_json = db.load_profile(user_id)

    if raw_json is not None:
        try:
            saved = json.loads(_decrypt_data(raw_json))
            for key, value in DEFAULT_PROFILE.items():
                saved.setdefault(key, value)
            profile = saved
        except Exception as exc:
            logger.warning(f"从 DB 加载用户画像失败 (user={user_id}): {exc}")
    else:
        profile_path = _get_user_profile_path(user_id)
        if profile_path.exists():
            try:
                file_raw = profile_path.read_text(encoding="utf-8")
                saved = json.loads(_decrypt_data(file_raw))
                for key, value in DEFAULT_PROFILE.items():
                    saved.setdefault(key, value)
                profile = saved
                logger.info(f"从文件迁移用户画像到 DB (user={user_id})")
                payload = json.dumps(profile, ensure_ascii=False, indent=2)
                db.save_profile(user_id, _encrypt_data(payload))
                migrated_path = profile_path.with_suffix(".json.migrated")
                try:
                    profile_path.rename(migrated_path)
                except Exception:
                    pass
            except Exception as exc:
                logger.warning(f"迁移用户画像文件失败 (user={user_id}): {exc}")

    has_legacy = False
    for zone_type in ["hr_zones", "pace_zones"]:
        zones = profile.get(zone_type, {})
        if any("(" in str(key) for key in zones.keys()):
            profile[zone_type] = {}
            has_legacy = True

    changed = sync_user_zones(profile)

    if changed or has_legacy:
        save_user_profile(profile, user_id)

    return profile


def save_user_profile(profile: Dict[str, Any], user_id: str = "default_user") -> None:
    """持久化用户画像到数据库。保存前会自动同步区间数据。"""
    try:
        lthr = _coerce_number(profile.get("lthr", 0))
        if lthr > 40:
            profile["hr_zones"] = calculate_hr_zones(lthr)
        if profile.get("t_pace"):
            target_hmp = _extract_target_hmp_seconds(profile)
            profile["pace_zones"] = calculate_pace_zones(
                profile["t_pace"], target_hmp_seconds=target_hmp
            )

        payload = json.dumps(profile, ensure_ascii=False, indent=2)
        db = _get_db()
        db.save_profile(user_id, _encrypt_data(payload))
        logger.info(f"用户画像已保存并同步区间数据 (user={user_id})。")
    except Exception as exc:
        logger.error(f"保存用户画像失败 (user={user_id}): {exc}")
