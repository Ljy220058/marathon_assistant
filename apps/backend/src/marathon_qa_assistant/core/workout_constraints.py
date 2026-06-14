"""训练课文献约束表——替代硬编码的分钟值。

每种训练课类型定义一个约束范围 (min, max, typical)，
LLM 在范围内根据跑者画像自主生成具体课时参数。
Audit 层负责验证 LLM 输出是否在约束范围内。

来源标注：A 级 (教材), B 级 (论文), C 级 (教练实践)
"""

from dataclasses import dataclass
from typing import Dict, Optional

@dataclass(frozen=True)
class WorkoutConstraint:
    workout_type: str          # 训练课类型中文名
    min_minutes: int           # 该类型训练课的最短持续时间 (分钟)
    max_minutes: int           # 该类型训练课的最长持续时间 (分钟)
    typical_minutes: int       # 该类型训练课的典型持续时间 (分钟)
    zone_range: str            # 强度区间
    stimulus_type: str         # intensity / volume_only / mixed
    source: str                # 文献来源
    source_grade: str          # A / B / C
    notes: str = ""            # 补充约束说明


WORKOUT_CONSTRAINTS: Dict[str, WorkoutConstraint] = {
    # ── 有氧耐力类 (volume_only) ──
    "轻松跑": WorkoutConstraint(
        workout_type="轻松跑", min_minutes=20, max_minutes=90, typical_minutes=45,
        zone_range="Z1-Z2", stimulus_type="volume_only",
        source="Daniels E 跑, Pfitzinger Recovery/GA", source_grade="A",
        notes="上限受 max_session_minutes 约束；恢复日取 20-30min"),
    "恢复跑": WorkoutConstraint(
        workout_type="恢复跑", min_minutes=15, max_minutes=45, typical_minutes=30,
        zone_range="Z1", stimulus_type="volume_only",
        source="Daniels E 跑 (recovery), Pfitzinger Recovery", source_grade="A",
        notes="心率 <72% LTHR；高强度课后次日使用"),
    "一般有氧跑": WorkoutConstraint(
        workout_type="一般有氧跑", min_minutes=30, max_minutes=90, typical_minutes=50,
        zone_range="Z2-Z3", stimulus_type="volume_only",
        source="Pfitzinger General Aerobic, Daniels E (extended)", source_grade="A",
        notes="工作日最常见的训练课类型"),
    "长距离": WorkoutConstraint(
        workout_type="长距离", min_minutes=60, max_minutes=210, typical_minutes=100,
        zone_range="Z2-Z3", stimulus_type="volume_only",
        source="Pfitzinger Long Run, Daniels Long Run", source_grade="A",
        notes="上限由全马/半马分型决定；半马 ≤150min，全马 ≤210min"),
    "跑走结合": WorkoutConstraint(
        workout_type="跑走结合", min_minutes=20, max_minutes=60, typical_minutes=40,
        zone_range="Z1-Z2", stimulus_type="volume_only",
        source="教练实践 (恢复期/伤病期), Galloway run-walk 方法 (教练实践, 无同行评审文献)", source_grade="C",
        notes="极端疲劳或伤病恢复期使用。2026-06 PubMed 检索: 跑走结合方法无 B 级及以上文献可用——Galloway 方法为教练协议，未在同行评审期刊发表对照研究。保留 C 级。"),
    # ── 阈值/节奏类 (intensity) ──
    "节奏跑": WorkoutConstraint(
        workout_type="节奏跑", min_minutes=20, max_minutes=30, typical_minutes=25,
        zone_range="Z5-Z6", stimulus_type="intensity",
        source="Daniels T 跑 (20-30min, 88-92% HRmax)", source_grade="A",
        notes="关键约束: 不可超过 30min；不到 20min 说明配速太快"),
    "连续节奏跑": WorkoutConstraint(
        workout_type="连续节奏跑", min_minutes=20, max_minutes=30, typical_minutes=25,
        zone_range="Z5-Z6", stimulus_type="intensity",
        source="Daniels T 跑, Pfitzinger LT 跑", source_grade="A",
        notes="阈值连续跑，与节奏跑约束相同"),
    "有氧阈值训练": WorkoutConstraint(
        workout_type="有氧阈值训练", min_minutes=30, max_minutes=60, typical_minutes=40,
        zone_range="Z3-Z4", stimulus_type="intensity",
        source="Daniels E 区上沿 + Pfitzinger 有氧功率训练", source_grade="A",
        notes="在最大脂肪氧化强度附近做稳态巡航"),
    "无氧阈跑": WorkoutConstraint(
        workout_type="无氧阈跑", min_minutes=25, max_minutes=45, typical_minutes=35,
        zone_range="Z4-Z6", stimulus_type="intensity",
        source="Daniels T (巡航间歇), Pfitzinger Cruise Intervals", source_grade="A",
        notes="通常以分段间歇形式执行（而非连续）"),
    # ── 间歇/摄氧量类 (intensity) ──
    "间歇跑": WorkoutConstraint(
        workout_type="间歇跑", min_minutes=15, max_minutes=35, typical_minutes=25,
        zone_range="Z5-Z7", stimulus_type="intensity",
        source="Daniels I 跑, Billat 2001 有氧间歇", source_grade="A",
        notes="总高强度工作时间 ≤8min (Daniels)；组数 ≤10 (Billat)；工休比 ≥1:1"),
    "摄氧量训练": WorkoutConstraint(
        workout_type="摄氧量训练", min_minutes=20, max_minutes=40, typical_minutes=30,
        zone_range="Z6-Z8", stimulus_type="intensity",
        source="Daniels I 跑 (VO2max), Billat 2001", source_grade="A",
        notes="总高强度时间 ≤8min；业余跑者 vVO2max 总量 ≤5km/节"),
    "重复跑": WorkoutConstraint(
        workout_type="重复跑", min_minutes=10, max_minutes=25, typical_minutes=15,
        zone_range="Z7-Z9", stimulus_type="intensity",
        source="Daniels R 跑", source_grade="A",
        notes="总 R 跑距离 ≤5km/节；工休比 ≥1:2"),
    # ── 混合/专项类 (mixed 或 intensity) ──
    "马拉松配速跑": WorkoutConstraint(
        workout_type="马拉松配速跑", min_minutes=25, max_minutes=80, typical_minutes=50,
        zone_range="Z4-Z5", stimulus_type="intensity",
        source="Daniels M 跑, Pfitzinger MP 跑", source_grade="A",
        notes="比赛专项期核心课；可嵌入长距离或独立执行"),
    "渐进跑": WorkoutConstraint(
        workout_type="渐进跑", min_minutes=35, max_minutes=80, typical_minutes=55,
        zone_range="Z2-Z5", stimulus_type="mixed",
        source="Pfitzinger Progression Run", source_grade="A",
        notes="从轻松区间渐进至比赛配速区；不可在中途停顿"),
    "法特莱克": WorkoutConstraint(
        workout_type="法特莱克", min_minutes=25, max_minutes=55, typical_minutes=40,
        zone_range="Z3-Z6", stimulus_type="intensity",
        source="Seiler 2010 (极化训练), Stoggl 2014", source_grade="B",
        notes="速度游戏——快段和慢段交替；快段配速不超 Z6 上限"),
    "坡道训练": WorkoutConstraint(
        workout_type="坡道训练", min_minutes=15, max_minutes=35, typical_minutes=25,
        zone_range="Z5-Z7", stimulus_type="intensity",
        source="Pfitzinger Hill Repeats, Daniels 坡道间歇", source_grade="A",
        notes="≥300m 长坡用于力量耐力；<100m 短坡用于速度和跑姿"),
    "MP混合长距离": WorkoutConstraint(
        workout_type="MP混合长距离", min_minutes=70, max_minutes=160, typical_minutes=110,
        zone_range="Z2-Z5", stimulus_type="mixed",
        source="Pfitzinger Long/MP, Daniels M+E 混编", source_grade="A",
        notes="长距离巡航 (Z2-Z3) + 比赛配速段 (Z4-Z5)；MP 段可 2-6km"),
    # ── 速度/冲刺类 (intensity) ──
    "短冲": WorkoutConstraint(
        workout_type="短冲", min_minutes=10, max_minutes=25, typical_minutes=15,
        zone_range="Z7-Z9", stimulus_type="intensity",
        source="Daniels R (Strides), Pfitzinger Strides", source_grade="A",
        notes="短距离快速重复 (80-200m)；充分恢复 (2-3min)；不在疲劳时做"),
    "跨步跑": WorkoutConstraint(
        workout_type="跨步跑", min_minutes=10, max_minutes=20, typical_minutes=15,
        zone_range="Z7-Z9", stimulus_type="intensity",
        source="Daniels R (Strides), Pfitzinger Strides", source_grade="A",
        notes="6-8 × 100m 或 8 × 20s 加速跑；通常附加在轻松跑末尾"),
    # ── 专项/模拟类 ──
    "比赛模拟跑": WorkoutConstraint(
        workout_type="比赛模拟跑", min_minutes=40, max_minutes=90, typical_minutes=60,
        zone_range="Z5-Z7", stimulus_type="intensity",
        source="Pfitzinger Tune-up Race, Daniels Race Simulation", source_grade="A",
        notes="含完整赛前热身和赛后冷身；比赛前 3-6 周执行"),
    "半马专项配速": WorkoutConstraint(
        workout_type="半马专项配速", min_minutes=50, max_minutes=100, typical_minutes=70,
        zone_range="Z4-Z5", stimulus_type="intensity",
        source="Daniels M (HM adapted), Pfitzinger HM-specific", source_grade="A",
        notes="100% HMP 巡航恢复间歇；总比赛配速段 8-15km"),
    # ── 补充/恢复类 ──
    "热身": WorkoutConstraint(
        workout_type="热身", min_minutes=10, max_minutes=25, typical_minutes=15,
        zone_range="Z1-Z2", stimulus_type="volume_only",
        source="Wang et al. 2022 荟萃分析 (损伤风险降低 15.7%)", source_grade="A",
        notes=(
            "强度课 (间歇/节奏/重复跑/摄氧量) 前: 含 3-4 组渐进加速跑 strides, 总时长 15-25min；"
            "轻松跑/长距离前: 慢跑+动态拉伸, 总时长 10-15min；"
            "恢复跑前: 5-8min 轻量动态拉伸即可。"
            "来源: Wang et al. 2022 荟萃分析 (A 级)"
        )),
    "泡沫轴放松": WorkoutConstraint(
        workout_type="泡沫轴放松", min_minutes=5, max_minutes=20, typical_minutes=10,
        zone_range="Z1", stimulus_type="volume_only",
        source="Zhou et al. 2024 荟萃分析 (DOMS 缓解)", source_grade="B"),
    "核心训练": WorkoutConstraint(
        workout_type="核心训练", min_minutes=10, max_minutes=25, typical_minutes=15,
        zone_range="Z1-Z2", stimulus_type="volume_only",
        source="Bompa 周期化理论 (辅助训练)", source_grade="B"),
}


def get_constraint(workout_type: str) -> Optional[WorkoutConstraint]:
    """获取训练课类型的文献约束范围。"""
    return WORKOUT_CONSTRAINTS.get(workout_type)


# F1: 减量期课型优先级 (来源: Pfitzinger Advanced Marathoning + Daniels Running Formula, A 级)
TAPER_WORKOUT_PRIORITY = {
    "retain": ["马拉松配速跑", "节奏跑", "半马专项配速"],  # 保持比赛节奏感
    "shorten": ["长距离", "一般有氧跑", "轻松跑", "恢复跑", "跑走结合", "MP混合长距离"],  # 缩短跑量
    "remove": ["摄氧量训练", "间歇跑", "重复跑", "坡道训练", "法特莱克", "无氧阈跑", "短冲", "比赛模拟跑"],  # 砍掉——不产生新刺激
}


def build_constraints_context(phase_family: str, allowed_types: Optional[list] = None) -> str:
    """构建 LLM 生成课时的约束上下文文本。

    Args:
        phase_family: 当前训练阶段 (base_1, build, peak, taper 等)
        allowed_types: 该阶段允许的训练课类型列表。None = 全部可用。

    Returns:
        可注入 LLM prompt 的约束描述文本。
    """
    types_to_show = allowed_types or list(WORKOUT_CONSTRAINTS.keys())
    lines = ["## 训练课类型约束 (你在生成课时必须遵守这些范围)",
             "| 课型 | 时间范围 | 典型时长 | 强度区间 | 类型 | 来源 |",
             "|------|---------|---------|---------|------|------|"]
    for tt in types_to_show:
        c = WORKOUT_CONSTRAINTS.get(tt)
        if not c:
            continue
        lines.append(
            f"| {c.workout_type} | {c.min_minutes}-{c.max_minutes}min | "
            f"{c.typical_minutes}min | {c.zone_range} | {c.stimulus_type} | "
            f"{c.source_grade}级 |"
        )
    lines.append(f"\n当前阶段: {phase_family}")
    return "\n".join(lines)
