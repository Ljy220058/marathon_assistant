"""周期化训练引擎：基于比赛日期倒推，自动生成 Macrocycle / Mesocycle 结构化阶段，支持最高 26 周。"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import re as _re

logger = logging.getLogger("workflow_engine")


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
    ) -> "Macrocycle":
        if total_weeks is None:
            total_weeks = int((profile or {}).get("plan_duration_weeks", 12) or 12)
        total_weeks = max(1, min(total_weeks, 26))
        mesocycles = cls._compute_mesocycles(total_weeks)
        return cls(race_date=race_date, total_weeks=total_weeks, mesocycles=mesocycles)

    @classmethod
    def from_profile(cls, profile: Dict) -> Optional["Macrocycle"]:
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
        return cls.from_race_date(race_date=parsed, total_weeks=total_weeks, profile=profile)

    @staticmethod
    def _compute_mesocycles(total_weeks: int) -> List[Mesocycle]:
        if total_weeks <= 4:
            return Macrocycle._phases_short(total_weeks)
        elif total_weeks <= 8:
            return Macrocycle._phases_medium(total_weeks)
        elif total_weeks <= 16:
            return Macrocycle._phases_standard(total_weeks)
        else:
            return Macrocycle._phases_long(total_weeks)

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
