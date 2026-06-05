"""周期化训练引擎：基于比赛日期倒推，自动生成 Macrocycle / Mesocycle 结构化阶段，支持最高 26 周。"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import logging
import re as _re

logger = logging.getLogger("workflow_engine")

# ── LLM advisor 约束：每个周数范围允许的模型层级 ──
_HM_VALID_TIER_MAP: Dict[Tuple[int, int], Tuple[str, ...]] = {
    (1, 4): ("short",),
    (5, 8): ("short", "compact"),
    (9, 14): ("short", "compact", "medium"),
    (15, 20): ("compact", "medium", "standard"),
    (21, 26): ("medium", "standard", "long"),
}
_FM_VALID_TIER_MAP: Dict[Tuple[int, int], Tuple[str, ...]] = {
    (1, 6): ("short",),
    (7, 12): ("short", "medium"),
    (13, 26): ("medium", "long"),
}


def _is_valid_hm_tier(tier: str, total_weeks: int) -> bool:
    for (lo, hi), valid in _HM_VALID_TIER_MAP.items():
        if lo <= total_weeks <= hi:
            return tier in valid
    return False


def _is_valid_fm_tier(tier: str, total_weeks: int) -> bool:
    for (lo, hi), valid in _FM_VALID_TIER_MAP.items():
        if lo <= total_weeks <= hi:
            return tier in valid
    return False


@dataclass
class Mesocycle:
    """中周期：一个连续的训练阶段"""
    name: str
    weeks: int
    start_week: int
    goal: str
    max_high_intensity_per_week: int
    min_easy_days: int
    long_run_zone: str
    weekly_mileage_ratio: float = 1.0

    @property
    def end_week(self) -> int:
        return self.start_week + self.weeks - 1

    @property
    def week_range_label(self) -> str:
        return f"{self.start_week}-{self.end_week}周"


@dataclass
class Macrocycle:
    """大周期：完整的训练周期规划，从比赛日倒推"""
    race_date: date
    total_weeks: int
    mesocycles: List[Mesocycle]
    start_date: date = field(init=False)

    def __post_init__(self):
        self.start_date = self.race_date - timedelta(weeks=self.total_weeks)

    @classmethod
    def from_race_date(
        cls,
        race_date: date,
        total_weeks: Optional[int] = None,
        profile: Optional[Dict] = None,
        advisory: Optional[Any] = None,
    ) -> "Macrocycle":
        if total_weeks is None:
            total_weeks = int((profile or {}).get("plan_duration_weeks", 12) or 12)
        total_weeks = max(1, min(total_weeks, 26))
        race_type = _resolve_race_type(profile) if profile else "general"
        mesocycles = cls._compute_mesocycles(total_weeks, race_type=race_type, advisory=advisory)
        return cls(race_date=race_date, total_weeks=total_weeks, mesocycles=mesocycles)

    @classmethod
    def from_profile(cls, profile: Dict, advisory: Optional[Any] = None) -> Optional["Macrocycle"]:
        target_str = str(profile.get("target_race_date", "") or "").strip()
        if not target_str or target_str.lower() in ("none", "null", "未设置", ""):
            return None

        parsed = None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%d/%m/%Y"):
            try:
                parsed = datetime.strptime(target_str, fmt).date()
                break
            except ValueError:
                continue

        if parsed is None:
            m_month = _re.search(r'(\d+)\s*个?\s*月', target_str)
            m_week = _re.search(r'(\d+)\s*个?\s*周', target_str)
            today = date.today()
            if m_month:
                parsed = today + timedelta(days=int(m_month.group(1)) * 30)
            elif m_week:
                parsed = today + timedelta(weeks=int(m_week.group(1)))
            else:
                return None

        total_weeks = int(profile.get("plan_duration_weeks", 12) or 12)
        return cls.from_race_date(race_date=parsed, total_weeks=total_weeks, profile=profile, advisory=advisory)

    @staticmethod
    def _compute_mesocycles(
        total_weeks: int,
        race_type: str = "general",
        advisory: Optional[Any] = None,
    ) -> List[Mesocycle]:
        """根据总周数和赛事类型选择对应的阶段模型。

        advisory 为可选 LLM 顾问建议，可覆写模型层级、导入期需求、
        阶段权重调整。不可用时走确定性规则。
        """
        if race_type == "marathon":
            return Macrocycle._marathon_phases(total_weeks, advisory=advisory)
        if race_type == "half_marathon":
            return Macrocycle._half_marathon_phases(total_weeks, advisory=advisory)
        if total_weeks <= 4:
            return Macrocycle._phases_short(total_weeks)
        elif total_weeks <= 8:
            return Macrocycle._phases_medium(total_weeks)
        elif total_weeks <= 16:
            return Macrocycle._phases_standard(total_weeks)
        else:
            return Macrocycle._phases_long(total_weeks)

    # ------------------------------------------------------------------
    # 半马专属阶段模型，对齐 HMP 协议（基础→专项构建→比赛专项）
    # Phase family 映射：基础→"general", 专项构建→"race_supportive", 比赛专项→"race_specific"
    # ------------------------------------------------------------------

    @staticmethod
    def _half_marathon_phases(
        total_weeks: int,
        advisory: Optional[Any] = None,
    ) -> List[Mesocycle]:
        total_weeks = max(1, total_weeks)

        # LLM 可覆写模型层级
        tier = ""
        if advisory is not None and getattr(advisory, "llm_generated", False):
            tier = str(getattr(advisory, "model_tier", "") or "").strip().lower()
            # 验证 LLM 选择的层级不超出总周数约束
            if not _is_valid_hm_tier(tier, total_weeks):
                logger.warning(
                    "HMP periodization: LLM model_tier=%s 对 %dw 无效，降级到确定性规则",
                    tier, total_weeks,
                )
                tier = ""
            else:
                logger.info(
                    "HMP periodization: LLM advisory model_tier=%s intro=%s adjustments=%s",
                    tier,
                    getattr(advisory, "needs_introductory", False),
                    getattr(advisory, "phase_adjustments", {}),
                )

        # ── tier → phase generator 映射 ──
        _generators = {
            "short": Macrocycle._hm_short,
            "compact": Macrocycle._hm_compact,
            "medium": Macrocycle._hm_medium,
            "standard": Macrocycle._hm_standard,
            "long": Macrocycle._hm_long,
        }
        if tier in _generators:
            mesos = _generators[tier](total_weeks)
        else:
            # 确定性 fallback
            if total_weeks <= 4:
                mesos = Macrocycle._hm_short(total_weeks)
            elif total_weeks <= 8:
                mesos = Macrocycle._hm_compact(total_weeks)
            elif total_weeks <= 14:
                mesos = Macrocycle._hm_medium(total_weeks)
            elif total_weeks <= 20:
                mesos = Macrocycle._hm_standard(total_weeks)
            else:
                mesos = Macrocycle._hm_long(total_weeks)

        # ── 导入期注入 ──
        if advisory is not None and getattr(advisory, "needs_introductory", False):
            intro_weeks = max(1, min(4, int(getattr(advisory, "intro_weeks", 0) or 2)))
            intro = Mesocycle(
                name="导入期 (Introductory Phase)",
                weeks=intro_weeks,
                start_week=1,
                goal="恢复身体和精神能量，重新引入上个周期缺失的训练元素，以体感训练为主，避免高负荷专项课。",
                max_high_intensity_per_week=0,
                min_easy_days=6,
                long_run_zone="Z1-Z2",
                weekly_mileage_ratio=0.65,
            )
            # 后续阶段起止周顺延，总周数不变：从各非减量阶段各减一周
            shifted: List[Mesocycle] = []
            remaining = intro_weeks
            for m in mesos:
                if remaining <= 0 or "减量" in m.name or "Taper" in m.name:
                    shifted.append(m)
                else:
                    shrink = min(m.weeks - 2, remaining)
                    if shrink > 0:
                        shifted.append(Mesocycle(
                            name=m.name,
                            weeks=m.weeks - shrink,
                            start_week=-1,  # 后续重算
                            goal=m.goal,
                            max_high_intensity_per_week=m.max_high_intensity_per_week,
                            min_easy_days=m.min_easy_days,
                            long_run_zone=m.long_run_zone,
                            weekly_mileage_ratio=m.weekly_mileage_ratio,
                        ))
                        remaining -= shrink
                    else:
                        shifted.append(m)
            mesos = [intro] + shifted

        # ── 阶段权重微调 ──
        if advisory is not None:
            adjustments = getattr(advisory, "phase_adjustments", {}) or {}
            if adjustments and len(mesos) >= 2:
                mesos = Macrocycle._apply_phase_adjustments(mesos, adjustments)

        # 重算 start_week
        start = 1
        for m in mesos:
            m.start_week = start
            start += m.weeks

        return mesos

    @staticmethod
    def _hm_short(total_weeks: int) -> List[Mesocycle]:
        """≤4 周半马：直奔比赛专项，保证赛前体感适应。"""
        return [Mesocycle(
            name="比赛专项阶段 (Race-Specific Phase)",
            weeks=total_weeks, start_week=1,
            goal="短期内最大化比赛配速体感适应，以 100% HMP 核心课和巡航恢复为主，避免大跑量冲击。",
            max_high_intensity_per_week=1, min_easy_days=4, long_run_zone="Z2-Z3",
            weekly_mileage_ratio=0.85,
        )]

    @staticmethod
    def _hm_compact(total_weeks: int) -> List[Mesocycle]:
        """5-8 周半马：压缩专项构建 + 比赛专项，不设独立基础阶段。"""
        race_w = max(3, int(total_weeks * 0.55))
        support_w = total_weeks - race_w
        mesos = []
        start = 1
        if support_w > 0:
            mesos.append(Mesocycle(
                name="专项构建阶段 (Race-Supportive Phase)", weeks=support_w, start_week=start,
                goal="建立 90-95% HMP 耐力支撑与 105-110% HMP 速度支撑，为比赛专项大课做铺垫。",
                max_high_intensity_per_week=2, min_easy_days=3, long_run_zone="Z2-Z3",
                weekly_mileage_ratio=0.95,
            ))
            start += support_w
        mesos.append(Mesocycle(
            name="比赛专项阶段 (Race-Specific Phase)", weeks=race_w, start_week=start,
            goal="最大化 95-105% HMP 区间能力，100% HMP 长间歇+巡航恢复，95% HMP 长距离快速跑。",
            max_high_intensity_per_week=2, min_easy_days=2, long_run_zone="Z3",
            weekly_mileage_ratio=1.00,
        ))
        return mesos

    @staticmethod
    def _hm_medium(total_weeks: int) -> List[Mesocycle]:
        """9-14 周半马：基础阶段 + 专项构建 + 比赛专项 三段式。"""
        race_w = max(3, int(total_weeks * 0.35))
        support_w = max(3, int(total_weeks * 0.30))
        base_w = total_weeks - support_w - race_w
        mesos = []
        start = 1
        if base_w > 0:
            mesos.append(Mesocycle(
                name="基础阶段 (General Phase)", weeks=base_w, start_week=start,
                goal="稳步提升总跑量，建立覆盖多配速区间的宽厚体能基础，发展阈值、有氧功率和基础耐力。长距离递增至 16-20km。",
                max_high_intensity_per_week=1, min_easy_days=5, long_run_zone="Z1-Z2",
                weekly_mileage_ratio=0.85,
            ))
            start += base_w
        if support_w > 0:
            mesos.append(Mesocycle(
                name="专项构建阶段 (Race-Supportive Phase)", weeks=support_w, start_week=start,
                goal="建立 90-95% HMP 耐力支撑与 105-110% HMP 速度支撑，为比赛专项阶段大课做铺垫。",
                max_high_intensity_per_week=2, min_easy_days=3, long_run_zone="Z2-Z3",
                weekly_mileage_ratio=1.00,
            ))
            start += support_w
        mesos.append(Mesocycle(
            name="比赛专项阶段 (Race-Specific Phase)", weeks=race_w, start_week=start,
            goal="最大化 95-105% HMP 区间能力，100% HMP 长间歇+巡航恢复，95% HMP 长距离快速跑至 20-25km。",
            max_high_intensity_per_week=2, min_easy_days=2, long_run_zone="Z3",
            weekly_mileage_ratio=0.95,
        ))
        return mesos

    @staticmethod
    def _hm_standard(total_weeks: int) -> List[Mesocycle]:
        """15-20 周半马：基础阶段 + 专项构建 + 比赛专项 + 赛前减量。"""
        taper_w = max(2, int(total_weeks * 0.12))
        race_w = max(4, int(total_weeks * 0.30))
        support_w = max(4, int(total_weeks * 0.28))
        base_w = total_weeks - taper_w - race_w - support_w
        mesos = []
        start = 1
        if base_w > 0:
            mesos.append(Mesocycle(
                name="基础阶段 (General Phase)", weeks=base_w, start_week=start,
                goal="稳步提升总跑量，建立覆盖多配速区间的宽厚体能基础，发展阈值、有氧功率、跑步经济性和基础耐力。长距离递增至 18-22km。",
                max_high_intensity_per_week=1, min_easy_days=5, long_run_zone="Z1-Z2",
                weekly_mileage_ratio=0.82,
            ))
            start += base_w
        if support_w > 0:
            mesos.append(Mesocycle(
                name="专项构建阶段 (Race-Supportive Phase)", weeks=support_w, start_week=start,
                goal="建立 90-95% HMP 耐力支撑与 105-110% HMP 速度支撑，为比赛专项阶段大课做铺垫。",
                max_high_intensity_per_week=2, min_easy_days=3, long_run_zone="Z2-Z3",
                weekly_mileage_ratio=1.00,
            ))
            start += support_w
        if race_w > 0:
            mesos.append(Mesocycle(
                name="比赛专项阶段 (Race-Specific Phase)", weeks=race_w, start_week=start,
                goal="最大化 95-105% HMP 区间能力，100% HMP 长间歇+巡航恢复（累计约 15km 目标配速），95% HMP 长距离快速跑至 20-25km。",
                max_high_intensity_per_week=2, min_easy_days=2, long_run_zone="Z3-Z4",
                weekly_mileage_ratio=1.00,
            ))
            start += race_w
        if taper_w > 0:
            mesos.append(Mesocycle(
                name="赛前减量 (Taper)", weeks=taper_w, start_week=start,
                goal="大幅降低训练负荷与跑量（至巅峰期 50-60%），消除累积疲劳，维持配速感，储备体能迎接半马比赛。",
                max_high_intensity_per_week=1, min_easy_days=6, long_run_zone="Z1-Z2",
                weekly_mileage_ratio=0.55,
            ))
        return mesos

    @staticmethod
    def _hm_long(total_weeks: int) -> List[Mesocycle]:
        """21-26 周半马：基础阶段-1/-2 + 专项构建 + 比赛专项 + 赛前减量。"""
        taper_w = max(2, int(total_weeks * 0.12))
        race_w = max(4, int(total_weeks * 0.26))
        support_w = max(4, int(total_weeks * 0.22))
        remaining = total_weeks - taper_w - race_w - support_w
        base2_w = max(3, int(remaining * 0.45))
        base1_w = remaining - base2_w
        mesos = []
        start = 1
        if base1_w > 0:
            mesos.append(Mesocycle(
                name="基础阶段-1 (General Phase 1)", weeks=base1_w, start_week=start,
                goal="建立有氧基础，以轻松跑和渐进长距离为核心，逐步增加跑量，长距离递增至 16-18km。引入法特莱克。",
                max_high_intensity_per_week=1, min_easy_days=5, long_run_zone="Z1-Z2",
                weekly_mileage_ratio=0.78,
            ))
            start += base1_w
        if base2_w > 0:
            mesos.append(Mesocycle(
                name="基础阶段-2 (General Phase 2)", weeks=base2_w, start_week=start,
                goal="巩固有氧能力，引入节奏跑和阈值训练，逐步提升训练强度，长距离递增至 20-22km。",
                max_high_intensity_per_week=1, min_easy_days=4, long_run_zone="Z2",
                weekly_mileage_ratio=0.92,
            ))
            start += base2_w
        if support_w > 0:
            mesos.append(Mesocycle(
                name="专项构建阶段 (Race-Supportive Phase)", weeks=support_w, start_week=start,
                goal="建立 90-95% HMP 耐力支撑与 105-110% HMP 速度支撑，为比赛专项阶段大课做铺垫。",
                max_high_intensity_per_week=2, min_easy_days=3, long_run_zone="Z2-Z3",
                weekly_mileage_ratio=1.02,
            ))
            start += support_w
        if race_w > 0:
            mesos.append(Mesocycle(
                name="比赛专项阶段 (Race-Specific Phase)", weeks=race_w, start_week=start,
                goal="最大化 95-105% HMP 区间能力，100% HMP 长间歇+巡航恢复（累计约 15km 目标配速），95% HMP 长距离快速跑至 20-25km。",
                max_high_intensity_per_week=2, min_easy_days=2, long_run_zone="Z3-Z4",
                weekly_mileage_ratio=1.00,
            ))
            start += race_w
        if taper_w > 0:
            mesos.append(Mesocycle(
                name="赛前减量 (Taper)", weeks=taper_w, start_week=start,
                goal="大幅降低训练负荷与跑量（至巅峰期 50-60%），消除累积疲劳，维持配速感，储备体能迎接半马比赛。",
                max_high_intensity_per_week=1, min_easy_days=6, long_run_zone="Z1-Z2",
                weekly_mileage_ratio=0.55,
            ))
        return mesos

    # ------------------------------------------------------------------
    # 全马专属阶段模型 (Base / Build / Peak / Taper)
    # ------------------------------------------------------------------

    @staticmethod
    def _marathon_phases(
        total_weeks: int,
        advisory: Optional[Any] = None,
    ) -> List[Mesocycle]:
        """全马专属四阶段模型，长距离每周递增到 30-35km。"""
        tier = ""
        if advisory is not None and getattr(advisory, "llm_generated", False):
            tier = str(getattr(advisory, "model_tier", "") or "").strip().lower()
        _generators = {
            "short": Macrocycle._marathon_phases_short,
            "medium": Macrocycle._marathon_phases_medium,
            "long": Macrocycle._marathon_phases_long,
        }
        if tier in _generators:
            return _generators[tier](total_weeks)
        if total_weeks <= 6:
            return Macrocycle._marathon_phases_short(total_weeks)
        elif total_weeks <= 12:
            return Macrocycle._marathon_phases_medium(total_weeks)
        else:
            return Macrocycle._marathon_phases_long(total_weeks)

    @staticmethod
    def _marathon_phases_short(total_weeks: int) -> List[Mesocycle]:
        """短周期全马 (< 7 周)：压缩为 Build + Taper。"""
        taper_w = max(2, int(total_weeks * 0.25))
        build_w = total_weeks - taper_w
        mesos = []
        start = 1
        if build_w > 0:
            mesos.append(Mesocycle(
                name="强化期 (Build Phase)", weeks=build_w, start_week=start,
                goal="提升有氧耐力与长距离能力，每周长距离递增至25-30km，引入马拉松配速专项",
                max_high_intensity_per_week=1, min_easy_days=4, long_run_zone="Z2-Z3",
                weekly_mileage_ratio=0.95,
            ))
            start += build_w
        if taper_w > 0:
            mesos.append(Mesocycle(
                name="减量期 (Taper Phase)", weeks=taper_w, start_week=start,
                goal="大幅降低训练负荷，消除累积疲劳，储备体能迎接全马比赛",
                max_high_intensity_per_week=1, min_easy_days=6, long_run_zone="Z1-Z2",
                weekly_mileage_ratio=0.55,
            ))
        return mesos

    @staticmethod
    def _marathon_phases_medium(total_weeks: int) -> List[Mesocycle]:
        """中周期全马 (7-12 周)：Base + Build + Taper。"""
        taper_w = max(2, int(total_weeks * 0.22))
        build_w = max(4, int(total_weeks * 0.45))
        base_w = total_weeks - build_w - taper_w
        if base_w < 2:
            base_w = 2
            build_w = total_weeks - base_w - taper_w
        mesos = []
        start = 1
        if base_w > 0:
            mesos.append(Mesocycle(
                name="基础期 (Base Phase)", weeks=base_w, start_week=start,
                goal="建立有氧基础，以轻松跑和渐进长距离为核心，逐步增加跑量，长距离递增至20-25km",
                max_high_intensity_per_week=1, min_easy_days=5, long_run_zone="Z1-Z2",
                weekly_mileage_ratio=0.82,
            ))
            start += base_w
        if build_w > 0:
            mesos.append(Mesocycle(
                name="强化期 (Build Phase)", weeks=build_w, start_week=start,
                goal="增加长距离距离至25-30km，引入马拉松配速跑、节奏跑和无氧阈间歇，强化专项耐力",
                max_high_intensity_per_week=2, min_easy_days=3, long_run_zone="Z2-Z3",
                weekly_mileage_ratio=1.03,
            ))
            start += build_w
        if taper_w > 0:
            mesos.append(Mesocycle(
                name="减量期 (Taper Phase)", weeks=taper_w, start_week=start,
                goal="大幅降低负荷，消除累积疲劳，心理与体能准备迎接全马比赛",
                max_high_intensity_per_week=1, min_easy_days=6, long_run_zone="Z1-Z2",
                weekly_mileage_ratio=0.55,
            ))
        return mesos

    @staticmethod
    def _marathon_phases_long(total_weeks: int) -> List[Mesocycle]:
        """长周期全马 (>=13 周)：Base + Build + Peak + Taper 标准四阶段。"""
        taper_w = max(2, int(total_weeks * 0.17))
        peak_w = max(3, int(total_weeks * 0.22))
        build_w = max(4, int(total_weeks * 0.35))
        base_w = total_weeks - taper_w - peak_w - build_w
        if base_w < 3:
            base_w = 3
            remaining = total_weeks - taper_w - peak_w - base_w
            build_w = max(3, int(remaining * 0.6))
            peak_w = remaining - build_w

        mesos = []
        start = 1
        if base_w > 0:
            mesos.append(Mesocycle(
                name="基础期 (Base Phase)", weeks=base_w, start_week=start,
                goal="有氧基础建设：以轻松跑和渐进长距离为核心，长距离每周递增至20-25km，引入法特莱克",
                max_high_intensity_per_week=1, min_easy_days=5, long_run_zone="Z1-Z2",
                weekly_mileage_ratio=0.78,
            ))
            start += base_w
        if build_w > 0:
            mesos.append(Mesocycle(
                name="强化期 (Build Phase)", weeks=build_w, start_week=start,
                goal="增加长距离至28-32km，引入马拉松配速跑、节奏跑和无氧阈间歇，提升专项耐力与乳酸阈值",
                max_high_intensity_per_week=2, min_easy_days=3, long_run_zone="Z2-Z3",
                weekly_mileage_ratio=1.00,
            ))
            start += build_w
        if peak_w > 0:
            mesos.append(Mesocycle(
                name="巅峰期 (Peak Phase)", weeks=peak_w, start_week=start,
                goal="马拉松配速专项：长距离含比赛配速段落，模拟比赛节奏与补给策略，长距离峰值30-35km",
                max_high_intensity_per_week=2, min_easy_days=2, long_run_zone="Z3",
                weekly_mileage_ratio=1.05,
            ))
            start += peak_w
        if taper_w > 0:
            mesos.append(Mesocycle(
                name="减量期 (Taper Phase)", weeks=taper_w, start_week=start,
                goal="赛前减量：大幅降低训练负荷与跑量（至巅峰期50-60%），消除累积疲劳，配速感维持",
                max_high_intensity_per_week=1, min_easy_days=6, long_run_zone="Z1-Z2",
                weekly_mileage_ratio=0.55,
            ))
        return mesos

    @staticmethod
    def _phases_short(total_weeks: int) -> List[Mesocycle]:
        if total_weeks == 1:
            return [
                Mesocycle(name="赛前调整期", weeks=1, start_week=1,
                          goal="赛前减量调整，保持轻松运动",
                          max_high_intensity_per_week=0, min_easy_days=6, long_run_zone="Z1",
                          weekly_mileage_ratio=0.5),
            ]
        build_w = total_weeks - 1
        return [
            Mesocycle(name="基础适应期", weeks=build_w, start_week=1,
                      goal="建立常规跑量，适应训练节奏",
                      max_high_intensity_per_week=1, min_easy_days=4, long_run_zone="Z1-Z2",
                      weekly_mileage_ratio=0.9),
            Mesocycle(name="减量恢复期", weeks=1, start_week=total_weeks,
                      goal="恢复减量，为比赛储备体能",
                      max_high_intensity_per_week=1, min_easy_days=6, long_run_zone="Z1-Z2",
                      weekly_mileage_ratio=0.6),
        ]

    @staticmethod
    def _phases_medium(total_weeks: int) -> List[Mesocycle]:
        base_w = max(3, int(total_weeks * 0.5))
        build_w = total_weeks - base_w - 1
        if build_w < 2:
            build_w = 2
            base_w = total_weeks - build_w - 1
        taper_w = total_weeks - base_w - build_w
        if taper_w < 1:
            taper_w = 1
            build_w = total_weeks - base_w - taper_w

        mesos = []
        start = 1
        if base_w > 0:
            mesos.append(Mesocycle(
                name="基础期", weeks=base_w, start_week=start,
                goal="建立有氧基础，逐步增加跑量，以轻松跑和长距离有氧为核心",
                max_high_intensity_per_week=1, min_easy_days=5, long_run_zone="Z1-Z2",
                weekly_mileage_ratio=0.85,
            ))
            start += base_w
        if build_w > 0:
            mesos.append(Mesocycle(
                name="建设期", weeks=build_w, start_week=start,
                goal="提升乳酸阈值与专项耐力，引入间歇和节奏训练",
                max_high_intensity_per_week=2, min_easy_days=3, long_run_zone="Z2-Z3",
                weekly_mileage_ratio=1.05,
            ))
            start += build_w
        if taper_w > 0:
            mesos.append(Mesocycle(
                name="减量期", weeks=taper_w, start_week=start,
                goal="大幅降低训练负荷，消除累积疲劳，储备体能迎接比赛",
                max_high_intensity_per_week=1, min_easy_days=6, long_run_zone="Z1-Z2",
                weekly_mileage_ratio=0.6,
            ))
        return mesos

    @staticmethod
    def _phases_standard(total_weeks: int) -> List[Mesocycle]:
        base1_w = max(3, int(total_weeks * 0.30))
        base2_w = max(3, int(total_weeks * 0.25))
        build_w = max(3, int(total_weeks * 0.28))
        taper_w = total_weeks - base1_w - base2_w - build_w
        if taper_w < 1:
            taper_w = 1
            rem = total_weeks - taper_w
            base1_w = int(rem * 0.33)
            base2_w = int(rem * 0.28)
            build_w = rem - base1_w - base2_w

        mesos = []
        start = 1
        for name, wks, goal, max_hi, min_easy, lr_z, rt in [
            ("基础期-1", base1_w, "建立有氧基础，逐步增加跑量，以轻松跑和长距离有氧为核心", 1, 5, "Z1-Z2", 0.80),
            ("基础期-2", base2_w, "巩固有氧能力，引入节奏跑和法特莱克，逐步提升训练强度", 1, 4, "Z2", 0.95),
            ("建设期", build_w, "强化专项耐力与比赛配速能力，引入无氧阈间歇和高强度训练", 2, 3, "Z2-Z3", 1.05),
            ("减量期", taper_w, "大幅降低训练负荷，消除累积疲劳，储备体能迎接比赛", 1, 6, "Z1-Z2", 0.60),
        ]:
            if wks > 0:
                mesos.append(Mesocycle(name=name, weeks=wks, start_week=start,
                                       goal=goal, max_high_intensity_per_week=max_hi,
                                       min_easy_days=min_easy, long_run_zone=lr_z,
                                       weekly_mileage_ratio=rt))
                start += wks
        return mesos

    @staticmethod
    def _phases_long(total_weeks: int) -> List[Mesocycle]:
        base1_w = max(3, int(total_weeks * 0.22))
        base2_w = max(3, int(total_weeks * 0.20))
        build1_w = max(2, int(total_weeks * 0.18))
        build2_w = max(2, int(total_weeks * 0.18))
        peak_w = max(2, int(total_weeks * 0.14))
        taper_w = total_weeks - base1_w - base2_w - build1_w - build2_w - peak_w
        if taper_w < 2:
            taper_w = 2
            rem = total_weeks - taper_w
            base1_w = int(rem * 0.23)
            base2_w = int(rem * 0.20)
            build1_w = int(rem * 0.19)
            build2_w = int(rem * 0.19)
            peak_w = rem - base1_w - base2_w - build1_w - build2_w

        mesos = []
        start = 1
        for name, wks, goal, max_hi, min_easy, lr_z, rt in [
            ("基础期-1", base1_w, "建立有氧基础，以轻松跑和长距离有氧为主，逐步增加跑量", 1, 5, "Z1-Z2", 0.75),
            ("基础期-2", base2_w, "巩固有氧能力，引入节奏跑和法特莱克，适当增加强度", 1, 4, "Z2", 0.90),
            ("建设期-1", build1_w, "提升乳酸阈值，引入无氧阈间歇训练，强化专项耐力", 2, 3, "Z2-Z3", 1.00),
            ("建设期-2", build2_w, "强化比赛配速能力，长距离加入渐进配速，增加训练复杂度", 2, 3, "Z3", 1.05),
            ("巅峰期", peak_w, "冲刺专项能力，训练高度针对目标比赛距离，模拟比赛节奏", 2, 2, "Z3-Z4", 1.00),
            ("减量期", taper_w, "大幅降低负荷，消除累积疲劳，储备体能与心理状态迎接比赛", 1, 6, "Z1-Z2", 0.55),
        ]:
            if wks > 0:
                mesos.append(Mesocycle(name=name, weeks=wks, start_week=start,
                                       goal=goal, max_high_intensity_per_week=max_hi,
                                       min_easy_days=min_easy, long_run_zone=lr_z,
                                       weekly_mileage_ratio=rt))
                start += wks
        return mesos

    @staticmethod
    def _apply_phase_adjustments(mesos: List[Mesocycle], adjustments: Dict[str, int]) -> List[Mesocycle]:
        """按 LLM 建议微调阶段周数，保持总周数不变。

        adjustments: {"base": 1, "specific": -1} 表示基础阶段+1周、专项-1周。
        调整仅作用于非减量/Taper 阶段，且每阶段保留至少 2 周。
        """
        if not adjustments or len(mesos) < 2:
            return mesos

        # 建立阶段名 → 索引映射
        _phase_keys = {
            "base": ("基础", "Base", "base"),
            "base_1": ("基础阶段-1", "基础期-1", "General Phase 1"),
            "base_2": ("基础阶段-2", "基础期-2", "General Phase 2"),
            "build": ("建设", "Build", "build", "专项构建"),
            "support": ("专项构建", "Supportive"),
            "specific": ("比赛专项", "Race-Specific", "Specific"),
            "peak": ("巅峰", "Peak", "peak"),
            "taper": ("减量", "Taper", "taper"),
        }

        def _match_phase(name: str, keys: Tuple[str,...]) -> bool:
            return any(k in name for k in keys)

        # 应用调整
        for adj_key, delta in adjustments.items():
            if delta == 0:
                continue
            keys = _phase_keys.get(adj_key, (adj_key,))
            for i, m in enumerate(mesos):
                if _match_phase(m.name, keys):
                    # 找一个反方向的非 tapert 阶段平衡
                    for j, other in enumerate(mesos):
                        if j == i:
                            continue
                        if _match_phase(other.name, _phase_keys.get("taper", ())):
                            continue
                        if delta > 0 and other.weeks - abs(delta) >= 2:
                            m.weeks += delta
                            other.weeks -= delta
                            logger.info(
                                "[periodization advisor] 阶段调整：%s %+d周 → %s %+d周",
                                m.name, delta, other.name, -delta,
                            )
                            break
                    break

        return mesos

    # ── LLM advisor 约束（模块级常量，避免 dataclass field 误解析）──

    def get_phase_for_week(self, week_num: int) -> Optional[Mesocycle]:
        for meso in self.mesocycles:
            if meso.start_week <= week_num <= meso.end_week:
                return meso
        return None

    def get_week_in_phase(self, week_num: int) -> Optional[int]:
        phase = self.get_phase_for_week(week_num)
        if phase is None:
            return None
        return week_num - phase.start_week + 1

    def build_phase_summary_text(self, week_num: int) -> str:
        phase = self.get_phase_for_week(week_num)
        if phase is None:
            return ""
        return (
            f"当前处于 **{phase.name}**（第{phase.week_range_label}，共 {phase.weeks} 周）\n"
            f"- 阶段目标：{phase.goal}\n"
            f"- 每周最多 {phase.max_high_intensity_per_week} 次高强度课\n"
            f"- 长距离配速区间：{phase.long_run_zone}\n"
            f"- 跑量系数：{phase.weekly_mileage_ratio:.0%}（相对于基准跑量）"
        )

    def build_skeleton_prompt_phase_rules(self) -> str:
        lines = ["【周期化阶段规则 —— 必须严格遵守】", ""]
        for i, meso in enumerate(self.mesocycles, 1):
            lines.append(f"{i}. {meso.name}（第{meso.week_range_label}，{meso.weeks} 周）：")
            lines.append(f"   目标：{meso.goal}")
            lines.append(f"   每周高强度上限：{meso.max_high_intensity_per_week} 次")
            lines.append(f"   长距离配速区：{meso.long_run_zone}")
            lines.append(f"   跑量系数：{meso.weekly_mileage_ratio:.0%}")
            lines.append("")
        return "\n".join(lines)

    def countdown_days(self) -> Optional[int]:
        try:
            return (self.race_date - date.today()).days
        except Exception:
            return None


@dataclass
class BlockParams:
    """四周板块参数：用于跑量约束引擎"""
    block_index: int
    start_week: int
    end_week: int
    weeks: int
    block_coeff: float
    block_peak_km: float


WITHIN_BLOCK_FACTORS = {1: 1.00, 2: 1.06, 3: 1.10, 4: 0.90}


def _baseline_block_coeff(block_index: int, meso_ratio: float) -> float:
    if meso_ratio <= 0.65:
        return meso_ratio
    return max(1.0, 1.0 + 0.04 * (block_index - 1), meso_ratio)


def resolve_4week_blocks(total_weeks: int, base_weekly_mileage: float) -> List[BlockParams]:
    """将总周数拆分为 4 周板块，返回每块的峰值参数"""
    num_blocks = (total_weeks + 3) // 4
    macrocycle = Macrocycle._compute_mesocycles(total_weeks)

    def _meso_for_week(w: int):
        for m in macrocycle:
            if m.start_week <= w <= m.end_week:
                return m
        return macrocycle[-1]

    block_coeffs = []
    for b in range(num_blocks):
        mid_week = b * 4 + 2.5
        meso = _meso_for_week(int(mid_week))
        block_coeffs.append(_baseline_block_coeff(b + 1, float(meso.weekly_mileage_ratio)))

    blocks = []
    for b in range(num_blocks):
        start = b * 4 + 1
        end = min(start + 3, total_weeks)
        ws = end - start + 1
        coeff = block_coeffs[b]
        blocks.append(BlockParams(
            block_index=b + 1,
            start_week=start,
            end_week=end,
            weeks=ws,
            block_coeff=round(coeff, 3),
            block_peak_km=round(base_weekly_mileage * coeff, 1),
        ))
    return blocks


def compute_week_volume_factor(week_index: int, blocks: List[BlockParams]) -> float:
    """根据板块和周内位置返回跑量缩放因子"""
    for blk in blocks:
        if blk.start_week <= week_index <= blk.end_week:
            wib = week_index - blk.start_week + 1
            if blk.block_coeff <= 0.65:
                return round(blk.block_coeff * max(0.85, 1.0 - 0.04 * (wib - 1)), 4)
            factor = WITHIN_BLOCK_FACTORS.get(wib, 1.0)
            if blk.weeks < 4:
                factor = max(1.0, factor - 0.02 * (4 - blk.weeks))
            return round(blk.block_coeff * factor, 4)
    return 1.0


def _resolve_race_type(profile: Dict) -> str:
    """从用户画像中检测目标赛事类型。

    检测来源（按优先级）：
    1. profile['race_type'] 显式字段（"half_marathon" / "marathon"）
    2. profile['goal'] 文本关键词（全马/半马/全程/半程/marathon）
    3. profile['target_pace'] 文本关键词
    4. 默认返回 "general"
    """
    race_type = str(profile.get("race_type") or "").strip().lower()
    if race_type in ("marathon", "half_marathon"):
        return race_type

    goal = str(profile.get("goal") or "").strip()
    target_pace = str(profile.get("target_pace") or "").strip()
    combined = f"{goal} {target_pace}".lower()

    if any(kw in combined for kw in ("全马", "全程", "马拉松", "marathon", "42k", "42.2")):
        return "marathon"
    if any(kw in combined for kw in ("半马", "半程", "half marathon", "half", "21k", "21.1")):
        return "half_marathon"

    return "general"
