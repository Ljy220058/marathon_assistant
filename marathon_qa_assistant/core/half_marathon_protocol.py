from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Literal, Optional, Tuple


HMPZoneId = Literal[
    "recovery_55",
    "easy_60_70",
    "moderate_75_85",
    "support_endurance_90",
    "specific_endurance_95",
    "race_specific_100",
    "specific_speed_105",
    "support_speed_107_110",
]

HMPhaseId = Literal[
    "introductory",
    "general",
    "race_supportive",
    "race_specific",
]

RunnerArchetypeId = Literal[
    "endurance_speed_rebuild",
    "marathoner_aerobic_power_gap",
    "short_build_after_marathon",
    "speed_based_endurance_gap",
    "general_half_marathon",
]


@dataclass(frozen=True)
class HMPZone:
    id: HMPZoneId
    label: str
    min_percent: Optional[float]
    max_percent: Optional[float]
    purpose: str
    typical_workouts: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class HMPhaseRule:
    id: HMPhaseId
    label: str
    objective: str
    preferred_zones: Tuple[HMPZoneId, ...]
    typical_workouts: Tuple[str, ...]
    safety_notes: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RunnerArchetypeRule:
    id: RunnerArchetypeId
    label: str
    indicators: Tuple[str, ...]
    primary_risk: str
    plan_bias: str
    preferred_workout_ids: Tuple[str, ...]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class HMWorkoutRule:
    id: str
    label: str
    primary_zone: HMPZoneId
    objective: str
    progression: Tuple[str, ...]
    ideal_cap: str
    caution: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class HMSafetyConstraint:
    id: str
    label: str
    rule: str
    rationale: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class RunnerArchetypeInput:
    recent_marathon: bool = False
    build_weeks: Optional[int] = None
    endurance_background: bool = False
    marathon_background: bool = False
    long_training_gap: bool = False
    middle_distance_background: bool = False
    speed_strength: bool = False
    half_marathon_experience_low: bool = False
    weekly_mileage_km: Optional[float] = None
    injury_or_fatigue: bool = False


@dataclass
class RunnerArchetypeDecision:
    archetype_id: RunnerArchetypeId
    label: str
    score: int
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


HMP_ZONES: Dict[HMPZoneId, HMPZone] = {
    "recovery_55": HMPZone(
        id="recovery_55",
        label="极轻松恢复",
        min_percent=None,
        max_percent=55.0,
        purpose="恢复、赛后导入、低压力补跑量。",
        typical_workouts=("恢复跑", "极轻松跑"),
    ),
    "easy_60_70": HMPZone(
        id="easy_60_70",
        label="轻松跑",
        min_percent=60.0,
        max_percent=70.0,
        purpose="日常有氧和跑量积累。",
        typical_workouts=("轻松跑", "普通有氧跑"),
    ),
    "moderate_75_85": HMPZone(
        id="moderate_75_85",
        label="中等强度",
        min_percent=75.0,
        max_percent=85.0,
        purpose="构建有氧基础、稳定跑和渐速跑前段。",
        typical_workouts=("中等跑", "稳定跑", "渐速跑"),
    ),
    "support_endurance_90": HMPZone(
        id="support_endurance_90",
        label="辅助耐力",
        min_percent=90.0,
        max_percent=90.0,
        purpose="支撑 95% HMP 长距离快速跑。",
        typical_workouts=("稳定长跑", "分段递进跑"),
    ),
    "specific_endurance_95": HMPZone(
        id="specific_endurance_95",
        label="专项耐力",
        min_percent=95.0,
        max_percent=95.0,
        purpose="提升半马后程抗疲劳和接近全马配速的持续能力。",
        typical_workouts=("长距离快速跑", "分段递进长跑"),
    ),
    "race_specific_100": HMPZone(
        id="race_specific_100",
        label="核心专项",
        min_percent=100.0,
        max_percent=100.0,
        purpose="提升半马目标配速下的代谢效率和乳酸转运。",
        typical_workouts=("长间歇", "巡航恢复交替跑"),
    ),
    "specific_speed_105": HMPZone(
        id="specific_speed_105",
        label="专项速度",
        min_percent=105.0,
        max_percent=105.0,
        purpose="建立 8K/10K 速度储备，让 HMP 感觉更轻松。",
        typical_workouts=("中长间歇", "快速持续跑", "8K/10K 比赛"),
    ),
    "support_speed_107_110": HMPZone(
        id="support_speed_107_110",
        label="辅助速度",
        min_percent=107.0,
        max_percent=110.0,
        purpose="发展 VO2max、速度上限、乳酸转运和乳酸氧化能力。",
        typical_workouts=("法特莱克", "短间歇", "短坡跑", "5K 比赛"),
    ),
}


HM_PHASE_RULES: Dict[HMPhaseId, HMPhaseRule] = {
    "introductory": HMPhaseRule(
        id="introductory",
        label="导入期",
        objective="恢复身体和精神能量，重新引入上个周期缺失的训练元素。",
        preferred_zones=("recovery_55", "easy_60_70", "moderate_75_85"),
        typical_workouts=("极轻松跑", "短法特莱克", "坡冲", "肯尼亚式渐速跑"),
        safety_notes=("刚比完全马或近期疲劳时，避免立刻安排长距离 95% HMP 快跑。",),
    ),
    "general": HMPhaseRule(
        id="general",
        label="基础阶段",
        objective="提升跑量和多配速综合能力，建立宽厚体能基础。",
        preferred_zones=("easy_60_70", "moderate_75_85", "support_endurance_90", "support_speed_107_110"),
        typical_workouts=("轻松跑", "长距离轻松跑", "阈值训练", "渐速跑", "法特莱克", "坡地训练"),
        safety_notes=("基础阶段应优先发展支撑能力，不宜频繁安排极限专项大课。",),
    ),
    "race_supportive": HMPhaseRule(
        id="race_supportive",
        label="专项能力构建阶段",
        objective="构建 90-95% HMP 的耐力支撑和 105-110% HMP 的速度支撑。",
        preferred_zones=("support_endurance_90", "specific_endurance_95", "specific_speed_105", "support_speed_107_110"),
        typical_workouts=("90% HMP 稳定长跑", "95% HMP 较短快速跑", "105% HMP 中长间歇", "混合法特莱克"),
        safety_notes=("关键课表容量应根据当前完成度递进，不能只按目标成绩倒推。",),
    ),
    "race_specific": HMPhaseRule(
        id="race_specific",
        label="比赛专项阶段",
        objective="最大化 95-105% HMP 区间能力，并在赛前完成关键 100% HMP 核心课。",
        preferred_zones=("specific_endurance_95", "race_specific_100", "specific_speed_105"),
        typical_workouts=("95% HMP 长距离快速跑", "100% HMP 巡航恢复间歇", "105% HMP 中长间歇"),
        safety_notes=("100% HMP 大课通常安排在支撑能力建立之后，且需要充分恢复。",),
    ),
}


RUNNER_ARCHETYPE_RULES: Dict[RunnerArchetypeId, RunnerArchetypeRule] = {
    "endurance_speed_rebuild": RunnerArchetypeRule(
        id="endurance_speed_rebuild",
        label="A 型：耐力强、速度需重建",
        indicators=("越野/超马/全马背景", "长距离耐力扎实", "速度训练近期不足"),
        primary_risk="过度依赖耐力，忽视速度和有氧功率。",
        plan_bias="从短距离快速跑、坡跑和法特莱克入手，逐步回到半马专项速度。",
        preferred_workout_ids=("hm_intro_fartlek_hills", "hm_105_specific_speed", "hm_100_float_intervals"),
    ),
    "marathoner_aerobic_power_gap": RunnerArchetypeRule(
        id="marathoner_aerobic_power_gap",
        label="B 型：全马经验强但久疏战阵",
        indicators=("路跑经验丰富", "近期缺少系统训练", "有氧功率或短距离速度不足"),
        primary_risk="专项速度和有氧功率跟不上半马目标。",
        plan_bias="拉长基础期，补阈值、短间歇和 105-110% HMP 能力。",
        preferred_workout_ids=("hm_base_threshold_progression", "hm_110_support_speed", "hm_105_specific_speed"),
    ),
    "short_build_after_marathon": RunnerArchetypeRule(
        id="short_build_after_marathon",
        label="C 型：备战期短且刚比完全马",
        indicators=("刚比完全马", "备战期 8 周左右或更短", "已有全马体能"),
        primary_risk="恢复不足时过早安排高消耗专项课。",
        plan_bias="先恢复和导入，后期集中安排少量关键专项课。",
        preferred_workout_ids=("hm_intro_fartlek_hills", "hm_95_long_fast_run", "hm_100_float_intervals"),
    ),
    "speed_based_endurance_gap": RunnerArchetypeRule(
        id="speed_based_endurance_gap",
        label="D 型：速度强、半马耐力不足",
        indicators=("1500 米/5K 背景", "速度是优势", "半马经验少"),
        primary_risk="无法长时间维持高速，巡航恢复和长距离快跑经验不足。",
        plan_bias="逐步加长快速跑距离，把速度转化为持久力。",
        preferred_workout_ids=("hm_90_support_endurance", "hm_95_long_fast_run", "hm_100_float_intervals"),
    ),
    "general_half_marathon": RunnerArchetypeRule(
        id="general_half_marathon",
        label="通用半马跑者",
        indicators=("背景不足以归入 A/B/C/D",),
        primary_risk="计划缺少明确个性化侧重点。",
        plan_bias="按阶段均衡建设 90/95/100/105/110% HMP 能力，并根据反馈调整。",
        preferred_workout_ids=("hm_base_threshold_progression", "hm_95_long_fast_run", "hm_100_float_intervals"),
    ),
}


HM_WORKOUT_RULES: Dict[str, HMWorkoutRule] = {
    "hm_90_support_endurance": HMWorkoutRule(
        id="hm_90_support_endurance",
        label="半马辅助耐力跑",
        primary_zone="support_endurance_90",
        objective="为 95% HMP 长距离快速跑提供耐力支撑。",
        progression=("中等强度长跑", "90% HMP 稳定跑", "分段递进跑"),
        ideal_cap="15-18 英里（25-30 公里）@90% HMP，或 86-88-92% HMP 分段递进。",
        caution="低跑量或短备战期用户需要显著缩放距离。",
    ),
    "hm_95_long_fast_run": HMWorkoutRule(
        id="hm_95_long_fast_run",
        label="半马专项耐力长距离快速跑",
        primary_zone="specific_endurance_95",
        objective="建立半马后程抗疲劳和接近全马配速的持续能力。",
        progression=("较短 95% HMP 快速跑", "90% HMP 辅助耐力", "分段递进跑", "长距离 95% HMP 快速跑"),
        ideal_cap="13-15 英里（20-25 公里）@95% HMP。",
        caution="刚比完全马、伤病恢复或跑量不足时不应直接安排上限课表。",
    ),
    "hm_100_float_intervals": HMWorkoutRule(
        id="hm_100_float_intervals",
        label="半马核心专项巡航恢复间歇",
        primary_zone="race_specific_100",
        objective="提升目标配速代谢效率，并用巡航恢复训练乳酸转运。",
        progression=("1km/1km 交替跑", "2km/1km 交替跑", "3km/1km 交替跑", "3-2-1km 组合间歇"),
        ideal_cap="累计 14-15 公里 HMP 跑量，总训练约 20 公里。",
        caution="应建立在 90/95/105% HMP 支撑能力之上，并配置充分恢复。",
    ),
    "hm_105_specific_speed": HMWorkoutRule(
        id="hm_105_specific_speed",
        label="半马专项速度间歇",
        primary_zone="specific_speed_105",
        objective="建立 8K/10K 速度储备，让目标 HMP 更轻松。",
        progression=("500-1000m 间歇", "1200m-2km 间歇", "2-3km 中长间歇", "6-8km 快速持续跑或 8K/10K 比赛"),
        ideal_cap="累计 8-10 公里，单次间歇 1-3 公里。",
        caution="慢肌优势跑者可能需要更长构建期，不宜过早上长间歇。",
    ),
    "hm_110_support_speed": HMWorkoutRule(
        id="hm_110_support_speed",
        label="半马辅助速度训练",
        primary_zone="support_speed_107_110",
        objective="发展 VO2max、速度上限、乳酸转运和乳酸氧化能力。",
        progression=("短坡冲刺", "1-2 分钟短法特莱克", "混合法特莱克", "400-1000m 间歇"),
        ideal_cap="35-45 分钟混合法特莱克，或累计 6-7 公里 400-1000m 间歇。",
        caution="名义 110% HMP 需根据当前 5K 能力校准，耐力型跑者常需下调。",
    ),
    "hm_intro_fartlek_hills": HMWorkoutRule(
        id="hm_intro_fartlek_hills",
        label="导入期法特莱克/坡跑",
        primary_zone="moderate_75_85",
        objective="低压力恢复训练热情，并重新引入速度、力量和跑姿刺激。",
        progression=("极轻松跑", "短法特莱克", "坡冲", "越野渐速跑"),
        ideal_cap="以体感控制为主，不追求固定上限。",
        caution="导入期重点是恢复和重新适应，不能演变为隐藏高强度比赛。",
    ),
    "hm_base_threshold_progression": HMWorkoutRule(
        id="hm_base_threshold_progression",
        label="基础期阈值/渐速跑",
        primary_zone="moderate_75_85",
        objective="构建 SSmax、有氧功率、跑步经济性和多配速基础。",
        progression=("中等跑", "阈值间歇", "肯尼亚式渐速跑", "双阈值训练日"),
        ideal_cap="依据训练年限和恢复能力动态设置。",
        caution="基础期不等于无上限堆强度，需要保护后续专项阶段的可持续性。",
    ),
}


HM_SAFETY_CONSTRAINTS: Dict[str, HMSafetyConstraint] = {
    "no_sub70_volume_copy": HMSafetyConstraint(
        id="no_sub70_volume_copy",
        label="不得照搬 Sub-70 跑量",
        rule="weekly_volume must scale to athlete history, not default to 70-90 miles",
        rationale="70-90 英里/周是高水平案例，不是普通跑者默认目标。",
    ),
    "marathon_recovery_intro": HMSafetyConstraint(
        id="marathon_recovery_intro",
        label="刚比完全马需导入",
        rule="recent_marathon implies introductory phase before hard long fast runs",
        rationale="全马后过早安排长距离 95% HMP 快跑会增加疲劳和伤病风险。",
    ),
    "quality_recovery_gap": HMSafetyConstraint(
        id="quality_recovery_gap",
        label="关键课之间保留恢复",
        rule="quality sessions should generally be separated by at least 48 hours",
        rationale="半马专项大课需要足够恢复，才能吸收训练刺激。",
    ),
    "progress_long_fast_run": HMSafetyConstraint(
        id="progress_long_fast_run",
        label="长距离快速跑必须进阶",
        rule="do not jump directly to 20-25km at 95% HMP without progression",
        rationale="95% HMP 长距离跑是高消耗课表，必须由短到长。",
    ),
    "dynamic_hmp_calibration": HMSafetyConstraint(
        id="dynamic_hmp_calibration",
        label="HMP 配速需动态校准",
        rule="target HMP and current HMP estimates should be distinguished",
        rationale="长周期中运动员即时体能会变化，死守初始目标配速会失真。",
    ),
}


def pace_seconds_at_hmp_percent(hmp_pace_seconds_per_km: int, percent: float) -> int:
    if hmp_pace_seconds_per_km <= 0:
        raise ValueError("hmp_pace_seconds_per_km must be positive")
    if percent <= 0:
        raise ValueError("percent must be positive")
    return round(hmp_pace_seconds_per_km * 100.0 / percent)


def pace_range_for_zone(hmp_pace_seconds_per_km: int, zone_id: HMPZoneId) -> Tuple[Optional[int], Optional[int]]:
    zone = HMP_ZONES[zone_id]
    faster: Optional[int] = None
    slower: Optional[int] = None
    if zone.max_percent is not None:
        faster = pace_seconds_at_hmp_percent(hmp_pace_seconds_per_km, zone.max_percent)
    if zone.min_percent is not None:
        slower = pace_seconds_at_hmp_percent(hmp_pace_seconds_per_km, zone.min_percent)
    return faster, slower


def format_pace(seconds_per_km: Optional[int]) -> str:
    if seconds_per_km is None:
        return ""
    minutes, seconds = divmod(int(seconds_per_km), 60)
    return f"{minutes}:{seconds:02d}/km"


def build_hmp_zone_pace_table(hmp_pace_seconds_per_km: int) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for zone in HMP_ZONES.values():
        faster, slower = pace_range_for_zone(hmp_pace_seconds_per_km, zone.id)
        if faster is None:
            pace_text = f"{format_pace(slower)} 或更慢"
        elif slower is None or faster == slower:
            pace_text = format_pace(faster)
        else:
            pace_text = f"{format_pace(faster)} - {format_pace(slower)}"
        rows.append({
            "zone_id": zone.id,
            "label": zone.label,
            "percent": _format_percent_range(zone.min_percent, zone.max_percent),
            "pace": pace_text,
            "purpose": zone.purpose,
        })
    return rows


def recommend_archetypes(profile: RunnerArchetypeInput) -> List[RunnerArchetypeDecision]:
    scored: List[RunnerArchetypeDecision] = []

    def add(archetype_id: RunnerArchetypeId, score: int, reasons: List[str]) -> None:
        rule = RUNNER_ARCHETYPE_RULES[archetype_id]
        scored.append(RunnerArchetypeDecision(archetype_id, rule.label, score, reasons))

    if profile.recent_marathon:
        score = 3
        reasons = ["近期刚比完全马"]
        if profile.build_weeks is not None and profile.build_weeks <= 8:
            score += 3
            reasons.append("备战期不超过 8 周")
        if profile.injury_or_fatigue:
            score += 1
            reasons.append("存在疲劳或伤病风险")
        add("short_build_after_marathon", score, reasons)

    if profile.endurance_background or profile.marathon_background:
        score = 2
        reasons = []
        if profile.endurance_background:
            score += 2
            reasons.append("具备越野/超马/长距离耐力背景")
        if profile.marathon_background:
            score += 1
            reasons.append("具备全马训练背景")
        if not profile.speed_strength:
            score += 1
            reasons.append("速度能力不是明确优势")
        add("endurance_speed_rebuild", score, reasons or ["耐力背景较强"])

    if profile.marathon_background or profile.long_training_gap:
        score = 1
        reasons = []
        if profile.marathon_background:
            score += 2
            reasons.append("全马或长距离路跑经验较强")
        if profile.long_training_gap:
            score += 3
            reasons.append("近期缺少系统训练")
        add("marathoner_aerobic_power_gap", score, reasons or ["需要补有氧功率"])

    if profile.middle_distance_background or profile.speed_strength or profile.half_marathon_experience_low:
        score = 1
        reasons = []
        if profile.middle_distance_background:
            score += 3
            reasons.append("中距离或 5K 背景")
        if profile.speed_strength:
            score += 2
            reasons.append("速度能力是优势")
        if profile.half_marathon_experience_low:
            score += 2
            reasons.append("半马经验较少")
        add("speed_based_endurance_gap", score, reasons or ["速度强于耐力"])

    if not scored:
        add("general_half_marathon", 1, ["画像信息不足，采用通用半马规则"])

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored


def select_phase_sequence(total_weeks: int, recent_marathon: bool = False) -> List[HMPhaseId]:
    if total_weeks <= 0:
        return []
    if total_weeks <= 6:
        return ["introductory", "race_supportive", "race_specific"] if recent_marathon else ["general", "race_supportive", "race_specific"]
    if total_weeks <= 10:
        return ["introductory", "race_supportive", "race_specific"] if recent_marathon else ["general", "race_supportive", "race_specific"]
    if total_weeks <= 14:
        return ["introductory", "general", "race_supportive", "race_specific"] if recent_marathon else ["general", "race_supportive", "race_specific"]
    return ["introductory", "general", "race_supportive", "race_specific"] if recent_marathon else ["general", "race_supportive", "race_specific"]


def workout_rules_for_archetype(archetype_id: RunnerArchetypeId) -> List[HMWorkoutRule]:
    archetype = RUNNER_ARCHETYPE_RULES[archetype_id]
    return [HM_WORKOUT_RULES[workout_id] for workout_id in archetype.preferred_workout_ids]


def protocol_summary() -> Dict[str, object]:
    return {
        "zones": [zone.to_dict() for zone in HMP_ZONES.values()],
        "phases": [phase.to_dict() for phase in HM_PHASE_RULES.values()],
        "archetypes": [archetype.to_dict() for archetype in RUNNER_ARCHETYPE_RULES.values()],
        "workouts": [workout.to_dict() for workout in HM_WORKOUT_RULES.values()],
        "safety_constraints": [constraint.to_dict() for constraint in HM_SAFETY_CONSTRAINTS.values()],
    }


def _format_percent_range(min_percent: Optional[float], max_percent: Optional[float]) -> str:
    if min_percent is None and max_percent is None:
        return ""
    if min_percent is None:
        return f"<={_format_percent(max_percent)}"
    if max_percent is None:
        return f">={_format_percent(min_percent)}"
    if min_percent == max_percent:
        return _format_percent(min_percent)
    return f"{_format_percent(min_percent)}-{_format_percent(max_percent)}"


def _format_percent(value: Optional[float]) -> str:
    if value is None:
        return ""
    if float(value).is_integer():
        return f"{int(value)}%"
    return f"{value}%"
