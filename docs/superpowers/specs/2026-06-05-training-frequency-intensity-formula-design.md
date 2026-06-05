# 训练频次→强度课数量约束公式设计

> 状态：已批准。来源标注规则：A 级（教材）、B 级（论文）、⚠️（组合外推）。
> 审核修正：2026-06-05（补充 total_sessions 定义、长距离归类、阶段 ID 对齐）。

## Context

当前系统将每周强度课数量硬编码为 2 节（`half_marathon_capacity_budget.py` line 33: `quality_sessions_max = 2`），不管跑者一周练 3 天还是 14 练。设计目标是让系统能区分不同训练频次的跑者，给他们生成不同的强度课分配。

经过文献审计发现：没有任何一篇实验论文直接给出"训练频次→强度课数量"的连续映射公式。但有三组独立的文献来源给出了约束：

- **Seiler 2010 + Stoggl 2014**（B 级）：80/20 按课次计，精英人群，提供**上限**（总次数 × 20%，cap 3 节/周）
- **Pfitzinger Advanced Marathoning + Daniels Running Formula**（A 级）：业余训练模板，强度课 1-2 节/周，提供**下限**（≥1 节）
- **Gabbett 2016**（B 级）：ACWR 急慢性负荷比，提供**过渡约束**（每周增量 ≤10%，强度课数跨度不超过 1 节）

本设计的核心原则：**不下全局公式，而是给出一套有文献来源的约束范围，让 LLM 在范围内基于跑者画像做选择。**

## 关键定义（审核补丁）

### 1. `total_sessions` 的计算方式

```python
# 当前：单练模式，每天最多一节训练课
total_sessions = len(available_days)  # e.g., ["周二","周四","周日"] → 3

# 未来：双练模式（DayPlan 改造后），每天可设上午/下午槽位
# total_sessions = len(available_days) * slots_per_day
# 其中 slots_per_day 默认 1，双练跑者为 2（由画像字段控制）
```

**当前实现仅支持单练模式。** `available_days` 是从用户画像提取的可训练日期列表。`total_sessions` 等于 `len(available_days)`。代码中留有 `slots_per_day` 注释接口，供未来双练改造时接入。

### 2. 长距离跑的归类

**长距离跑（Long Run）不属于 Seiler 定义的"高强度课"**——长距离大部分在 Z2-Z3，是专项耐力训练而非高强度刺激。但长距离跑对低频训练者（≤4 练/周）仍然是显著的周负荷。

处理方式：
- 长距离跑不纳入强度课计数——强度课仅含：节奏跑（Z5-Z6）、间歇跑（Z5-Z8）、法特莱克（Z3-Z6）、坡道训练（Z5-Z7）
- **低频训练者附加约束**：当 `total_sessions ≤ 4` 且包含长距离课时，强度课上限强制为 1。因为 1 节长距离 + 1 节强度课 = 2/4 = 50% 的课次为高负荷，已接近业余跑者的安全边界。
- 该约束标注为 ⚠️ 组合外推（Pfitzinger 低频计划模板 + Gabbett ACWR 安全区间取交集）。

### 3. 阶段 ID 对齐

以下阶段 ID 与 `training_plan_skeleton.py::_phase_family()` 实际返回值一致（已验证代码）：

| 阶段中文名 | `_phase_family()` 返回值 | 本 spec 使用 |
|-----------|------------------------|------------|
| 导入期（Introductory） | —（暂未实现，由 advisory 控制） | `intro` |
| 基础阶段-1（General Phase 1） | `base_1` | `base_1` |
| 基础阶段-2（General Phase 2） | `base_2` | `base_2` |
| 专项构建阶段（Build/Supportive） | `build` / `build_1` / `build_2` | `build` |
| 比赛专项阶段（Race-Specific/Peak） | `peak` | `peak` |
| 赛前减量（Taper） | `taper` | `taper` |

## 约束规则表

```python
# 训练总课次 → (强度课下限, 强度课上限)
FREQUENCY_INTENSITY_BOUNDS = {
    (1, 3):   (1, 1),   # Seiler 20%×3=0.6 → 1, Pfitzinger 保底 1
    (4, 5):   (1, 1),   # Seiler 20%×5=1.0, Pfitzinger 保底 1
    (6, 7):   (1, 2),   # Seiler 20%×7=1.4→2, Pfitzinger 保底 1
    (8, 10):  (1, 2),   # Stoggl POL: 2/10 直接适用
    (11, 14): (2, 3),   # Seiler 精英: 14练→2-3节高强度
}
```

### 来源逐行标注

| 总次数范围 | 下限 | 下限来源 | 上限 | 上限来源 | 备注 |
|:---:|:---:|---|:---:|---|:---|
| 1-3 | 1 | Pfitzinger/Daniels (A 级) | 1 | Seiler 80/20 (B 级) | 三练中一练是长距离，天然占去强度负荷 |
| 4-5 | 1 | Pfitzinger (A 级) | 1 | Seiler 80/20 (B 级) | 五一训练者的经典结构：2 高强度 + 3 轻松 |
| 6-7 | 1 | Pfitzinger (A 级) | 2 | Seiler 80/20 (B 级) | **⚠️ 组合外推，非直接实验证据** |
| 8-10 | 1 | Pfitzinger (A 级) | 2 | Stoggl 2014 POL (B 级) | Stoggl 的 10 练方案直接验证了 2 节 |
| 11-14 | 2 | Daniels/Pfitzinger (A 级) | 3 | Seiler 精英 (B 级) | Seiler 精英数据直接适用此范围 |

### 低频训练者长距离负荷约束

```python
# 附加约束：低频训练者 + 有长距离课 → 强度课上限强制 1
if total_sessions <= 4 and _has_long_run_session(plan):
    upper = min(upper, 1)
```

### 补充约束

1. **ACWR 过渡约束**：阶段转换时，强度课数量的增量不超过 1 节/周。来源：Gabbett 2016 (B 级)。

2. **阶段修正**：
   - `base_1`, `base_2`, `intro`：按区间下限取值
   - `build`：按区间中间值
   - `peak`：按区间上限取值
   - `taper`：强制 1 节（减量期不追求新的训练刺激）
   来源：Bompa 周期化理论 + Pfitzinger 阶段训练模板。

3. **伤病/中断修正**：如跑者有近期伤病或训练中断超过 2 周，强度课锁定为 1 节，不受频次范围约束。来源：Gabbett ACWR 安全区间 + 教练实践 (A/B 级)。

## LLM 决策框架

`periodization_advisor.py` 在约束范围内做决策：

### 输入
- 跑者总训练课次（`total_sessions = len(available_days)`，未来乘 `slots_per_day`）
- 跑者画像（`weekly_mileage`, `experience_level`, `injury_or_fatigue`, `training_background`, `recent_marathon`）
- 当前训练阶段（`_phase_family()` 返回值：`base_1`, `base_2`, `build`, `peak`, `taper`, `intro`）

### 决策规则
LLM 在 `[lower, upper]` 范围内选择强度课数量，遵循以下优先级：

1. **硬约束（代码层安全边界）**：不可超出 `FREQUENCY_INTENSITY_BOUNDS` 范围
2. **低频长距离约束**：`total_sessions ≤ 4` + 含长距离课 → 上限强制 1
3. **阶段修正**：基础期优先取下限，比赛专项期优先取上限
4. **画像修正**：周跑量 <30km 或伤病/中断 → 取下限；周跑量 >50km + 有间歇经验 → 取上限
5. **LLM 可在 1-2 的范围内根据跑者整体画像微调选择**

### 降级
LLM 不可用时，按最保守值处理：取区间下限。

## 实现方案

### 改动文件

| 文件 | 改动 | 规模 |
|------|------|:--:|
| `core/half_marathon_capacity_budget.py` | 替换硬编码的 `quality_sessions_max = 2`，改为 `_compute_intensity_bounds(total_sessions, phase_family, profile) → (lower, upper)` | 中 |
| `core/periodization_advisor.py` | 提示词中添加强度课约束范围上下文 | 小 |
| `core/training_plan_skeleton.py` | `_build_week_days()` 中 quality_sessions_max 的来源改为从新函数获取；低频长距离约束判断 | 小 |

### 新增函数

```python
# half_marathon_capacity_budget.py

def _compute_intensity_bounds(
    total_sessions: int,
    phase_family: str,
    profile: Dict[str, Any]
) -> Tuple[int, int]:
    """根据训练频次、阶段、画像返回强度课范围 (lower, upper)。
    
    来源：
    - 上限：Seiler 2010, Stoggl 2014 (B 级)
    - 下限：Pfitzinger, Daniels (A 级)  
    - 过渡约束：Gabbett 2016 (B 级)
    """
    # 从文献约束表获取基础范围
    lower, upper = _frequency_bounds(total_sessions)
    
    # 阶段修正（对齐 _phase_family() 实际返回值）
    if phase_family in ("base_1", "base_2", "intro"):
        upper = lower  # 基础期只用下限
    elif phase_family == "build":
        upper = max(lower, upper - 1)  # 建设期取中间值（安全侧）
    elif phase_family == "peak":
        lower = upper  # 比赛专项期用上限
    elif phase_family == "taper":
        return 1, 1  # 减量期强制 1 节
    
    # 画像修正：伤病/近全马 → 强制下限
    if profile.get("injury_or_fatigue") or profile.get("recent_marathon"):
        return 1, 1
    
    return max(1, lower), min(3, upper)


def _frequency_bounds(total_sessions: int) -> Tuple[int, int]:
    """训练总课次 → 强度课范围。来源标注见约束规则表。"""
    if total_sessions <= 3:
        return 1, 1
    elif total_sessions <= 5:
        return 1, 1
    elif total_sessions <= 7:
        return 1, 2
    elif total_sessions <= 10:
        return 1, 2
    else:
        return 2, 3
```

## 验证方案

1. **单元测试**：测试 `_compute_intensity_bounds` 在所有频次×阶段组合下返回正确的范围
2. **对照验证**：取 Pfitzinger 18/35/55 英里三档训练计划，逐周比对系统生成的强度课数量
3. **安全边界测试**：验证伤病/中断场景下强度课强制为 1，不随频次改变
4. **低频长距离测试**：验证 3-4 练跑者有长距离课时强度课上限不超过 1
5. **不回归现有测试**：`test_workout_template_retriever.py`（18 项）+ `test_training_plan_skeleton.py` 全过
6. **代码验证**：`grep` 确认所有 `phase_family` 值在 `_phase_family()` 中有对应路径

## 未解决 / 需要后续追踪

- 业余跑者（3-7 练/周）的强度课比例缺少直接 RCT 证据，当前设计方案中的 6-7 练区间标记为 ⚠️ 组合外推。Munoz 2014 和 Esteve-Lanao 2007 两篇论文入库后可补充"业余跑者适用极化训练"的 B 级背书，但不会改变组合外推的本质。
- "双练"（一天两练）尚未实现，当前 `total_sessions = len(available_days)`。双练支持需等 DayPlan 数据结构改造（`slots_per_day` 字段）。
