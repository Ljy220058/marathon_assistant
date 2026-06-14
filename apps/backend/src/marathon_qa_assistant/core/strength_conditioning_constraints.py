from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Dict, Iterable, List, Optional

from marathon_qa_assistant.core.training_plan_context import coerce_float_from_unit_text


def _profile_text(profile: Dict[str, Any], *keys: str) -> str:
    values: List[str] = []
    for key in keys:
        raw = profile.get(key)
        if isinstance(raw, (list, tuple, set)):
            values.extend(str(item) for item in raw)
        elif isinstance(raw, dict):
            values.extend(str(item) for item in raw.values())
        else:
            values.append(str(raw or ""))
    return " ".join(values).lower()


def _has_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _strip_negated_status_phrases(text: str) -> str:
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


def _safe_float(value: Any, default: float) -> float:
    parsed = coerce_float_from_unit_text(value)
    if parsed is None:
        return float(default)
    return float(parsed)


def _evidence_refs(ranked_evidence: Iterable[Any], limit: int = 5) -> List[str]:
    refs: List[str] = []
    for item in ranked_evidence or []:
        if not isinstance(item, dict):
            continue
        ref = str(item.get("citation_label") or item.get("source_registry_id") or item.get("source_file") or "").strip()
        if ref and ref not in refs:
            refs.append(ref)
        if len(refs) >= limit:
            break
    return refs


def build_training_capacity_envelope(
    *,
    profile: Optional[Dict[str, Any]] = None,
    query: str = "",
    ranked_evidence: Optional[Iterable[Any]] = None,
    medical_constraints: Optional[Dict[str, Any]] = None,
    current_plan: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the deterministic S&C capacity boundary consumed by planning nodes.

    The envelope is not a medical diagnosis. It translates normal training
    capacity signals into constraints that planner/executor/auditor can read.
    """

    del current_plan
    profile = dict(profile or {})
    medical = dict(medical_constraints or {})
    weekly_mileage = _safe_float(
        profile.get("weekly_mileage") or profile.get("current_weekly_km") or profile.get("current_weekly_mileage"),
        40.0,
    )
    typical_days = int(_safe_float(profile.get("typical_training_days") or len(profile.get("available_days") or []) or 4, 4.0))
    combined_text = " ".join(
        [
            str(query or ""),
            _profile_text(
                profile,
                "injury_history",
                "active_injuries",
                "body_status",
                "subjective_fatigue",
                "fatigue",
                "sleep_quality",
                "notes",
            ),
        ]
    ).lower()
    combined_text = _strip_negated_status_phrases(combined_text)

    has_fatigue = _has_any(combined_text, ["疲劳", "累", "heavy legs", "poor sleep", "睡眠差", "乏力"])
    has_pain_or_injury = _has_any(combined_text, ["疼", "痛", "伤", "injury", "pain", "膝", "跟腱", "足底"])
    medical_limited = str(medical.get("can_run") or "").strip() in {"limited", "no"}
    can_strength = str(medical.get("can_strength_train") or "").strip()

    progression_multiplier = 1.10
    if weekly_mileage < 35:
        progression_multiplier = min(progression_multiplier, 1.08)
    if typical_days <= 3:
        progression_multiplier = min(progression_multiplier, 1.06)
    if has_fatigue:
        progression_multiplier = min(progression_multiplier, 0.90)
    if has_pain_or_injury or medical_limited:
        progression_multiplier = min(progression_multiplier, 0.75)

    weekly_cap = round(max(15.0, weekly_mileage * progression_multiplier), 1)
    weekly_floor = round(max(0.0, weekly_mileage * 0.75), 1)
    long_run_cap = round(min(32.0, max(8.0, weekly_cap * 0.34)), 1)
    quality_max = 1 if (weekly_cap < 45 or has_fatigue or has_pain_or_injury or typical_days <= 4) else 2

    strength_frequency = 1 if (has_fatigue or has_pain_or_injury or typical_days <= 3) else 2
    strength_intensity = "limited" if (has_fatigue or has_pain_or_injury or can_strength == "limited") else "normal"
    if can_strength == "no":
        strength_frequency = 0
        strength_intensity = "blocked_by_medical_constraint"

    capacity_risk_flags: List[Dict[str, Any]] = []
    if has_fatigue:
        capacity_risk_flags.append(
            {
                "severity": "yellow",
                "code": "fatigue_load_sensitivity",
                "route_to": ["executor", "critic_auditor"],
                "meaning": "capacity constraint only",
            }
        )
    if has_pain_or_injury:
        capacity_risk_flags.append(
            {
                "severity": "red",
                "code": "requires_therapist_review",
                "route_to": ["critic_auditor", "therapist"],
                "meaning": "medical or injury signal is outside S&C authority",
            }
        )

    return {
        "schema_version": "training_capacity_envelope.v1",
        "source_role": "s_and_c",
        "status": "ready",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "load_ceiling": {
            "weekly_load_cap_km": weekly_cap,
            "weekly_load_floor_km": weekly_floor,
            "max_long_run_km": long_run_cap,
            "quality_sessions_max": quality_max,
            "progression_multiplier": progression_multiplier,
        },
        "strength_rules": {
            "max_strength_sessions_per_week": strength_frequency,
            "intensity_permission": strength_intensity,
            "heavy_lower_body_spacing_hours": 48,
            "race_week_mode": "activation_only",
        },
        "recovery_windows": {
            "post_long_run_hours": 48,
            "post_quality_hours": 24,
            "post_heavy_strength_hours": 48,
        },
        "capacity_risk_flags": capacity_risk_flags,
        "downstream_targets": {
            "planner": ["load_ceiling"],
            "executor": ["load_ceiling", "strength_rules", "recovery_windows", "yellow_capacity_flags"],
            "critic_auditor": ["load_ceiling", "recovery_windows", "capacity_risk_flags"],
            "therapist": ["requires_therapist_review"],
        },
        "evidence_refs": _evidence_refs(ranked_evidence or []),
        "boundary": "S&C constrains normal training capacity; medical pain or injury decisions belong to therapist.",
    }


__all__ = ["build_training_capacity_envelope"]
