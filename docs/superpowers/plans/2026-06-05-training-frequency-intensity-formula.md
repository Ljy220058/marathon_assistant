# 训练频次→强度课约束公式 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `quality_sessions_max` 从硬编码 2 节替换为文献约束驱动范围（基于 Seiler/Pfitzinger/Gabbett），按训练频次和阶段动态计算。

**Architecture:** 在 `half_marathon_capacity_budget.py` 中新增 `_compute_intensity_bounds()` 函数，按频次范围表返回 (lower, upper)，再由阶段和画像修正。`training_plan_skeleton.py::_build_week_days()` 改为从该函数获取 `quality_sessions_max` 并透传 `phase_family`。

**Tech Stack:** Python 3.11+, 现有 `marathon_qa_assistant` 模块体系

---

## 文件结构

| 文件 | 角色 | 改动类型 |
|------|------|:--:|
| `core/half_marathon_capacity_budget.py` | 新增 `_compute_intensity_bounds()` + `_frequency_bounds()`，修改 `build_half_marathon_capacity_budget()` 签名 | 中 |
| `core/training_plan_skeleton.py` | `_build_week_days()` 传递 `phase_family`；低频长距离约束判断 | 小 |
| `core/periodization_advisor.py` | 提示词添加强度课约束范围上下文 | 小 |
| `tests/test_half_marathon_capacity_budget.py` | 新增强度课范围的参数化测试 | 中（新建测试类） |

---

### Task 1: 新增 `_frequency_bounds()` 和 `_compute_intensity_bounds()`

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/core/half_marathon_capacity_budget.py`

- [ ] **Step 1: 在文件末尾添加两个新函数**

在 `half_marathon_capacity_budget.py` 末尾（`_safe_float` 辅助函数之后）追加：

```python
# ── 训练频次→强度课约束范围（Seiler 2010 + Pfitzinger + Gabbett 2016）──

def _frequency_bounds(total_sessions: int) -> Tuple[int, int]:
    """训练总课次 → 强度课范围 (lower, upper)。

    来源标注：
    - 上限: Seiler 2010 (20% sessions), Stoggl 2014 POL 验证 (B 级)
    - 下限: Pfitzinger Advanced Marathoning, Daniels Running Formula (A 级)
    - 6-7 练区间: 组合外推, 非直接实验证据
    """
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


def _compute_intensity_bounds(
    total_sessions: int,
    phase_family: str,
    profile: Optional[Dict[str, Any]] = None,
) -> Tuple[int, int]:
    """根据训练频次、阶段、画像返回强度课范围 (lower, upper)。

    Args:
        total_sessions: 一周训练总课次 (当前 = len(available_days))
        phase_family: _phase_family() 返回值 (base_1/base_2/build/peak/taper/intro)
        profile: 跑者画像, 可选。用于伤病/中断修正。

    Returns:
        (lower, upper) — 强度课数量约束范围, 两端均为闭区间。
        代码层安全边界: 1 ≤ lower ≤ upper ≤ 3。
    """
    profile = profile or {}

    # 1. 文献约束表 → 基础范围
    lower, upper = _frequency_bounds(total_sessions)

    # 2. 阶段修正 (来源: Bompa 周期化理论 + Pfitzinger 阶段模板)
    if phase_family in ("base_1", "base_2", "intro"):
        upper = lower  # 基础期: 只用下限
    elif phase_family == "build":
        upper = max(lower, upper - 1)  # 建设期: 取中间值
    elif phase_family == "peak":
        lower = upper  # 比赛专项期: 用上限
    elif phase_family == "taper":
        return 1, 1  # 减量期: 强制 1 节

    # 3. 画像修正: 伤病/近全马 → 强制 1 节
    #    (来源: Gabbett 2016 ACWR + 教练实践 A/B 级)
    if profile.get("injury_or_fatigue") or profile.get("recent_marathon"):
        return 1, 1

    # 4. 安全裁剪
    return max(1, lower), min(3, upper)
```

- [ ] **Step 2: 验证导入可用**

```bash
cd apps/backend/src && python -c "from marathon_qa_assistant.core.half_marathon_capacity_budget import _frequency_bounds, _compute_intensity_bounds; print(_frequency_bounds(5)); print(_compute_intensity_bounds(7, 'peak'))"
```

预期: (1, 1) 和 (2, 2)

- [ ] **Step 3: Commit**

```bash
git add apps/backend/src/marathon_qa_assistant/core/half_marathon_capacity_budget.py
git commit -m "feat: add intensity bounds functions (Seiler/Pfitzinger/Gabbett constraints)"
```

---

### Task 2: 修改 `build_half_marathon_capacity_budget()` 接入新函数

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/core/half_marathon_capacity_budget.py:8-33`

- [ ] **Step 1: 修改函数签名和 quality_sessions_max 计算**

```python
def build_half_marathon_capacity_budget(
    *,
    weekly_volume_km: Optional[float],
    phase_id: str,
    available_days_count: Optional[int] = None,
    recent_four_week_mileage_km: Optional[float] = None,
    recent_marathon: bool = False,
    fatigue_or_injury: bool = False,
    speed_calibration_available: bool = True,
    phase_family: str = "general",          # 新增
    total_training_sessions: Optional[int] = None,  # 新增
) -> Dict[str, Any]:
```

**修改 `quality_sessions_max` 计算逻辑**（替换原来的 line 31-33）：

```python
    # 强度课约束: 文献约束范围取上限作为 quality_sessions_max
    # 实际 downgrade 逻辑在下游 _build_week_days() 中
    total_sessions = int(total_training_sessions or available_days_count or 0) or len(available_days) if 'available_days' in dir() else 3
    intensity_lower, intensity_upper = _compute_intensity_bounds(
        total_sessions=total_sessions,
        phase_family=phase_family,
        profile={
            "injury_or_fatigue": fatigue_or_injury,
            "recent_marathon": recent_marathon,
        },
    )
    quality_sessions_max = intensity_upper

    # 保留原有的降级逻辑作为附加安全阀
    if low_volume or constrained_days or recovery_risk or phase_id == "introductory":
        quality_sessions_max = min(quality_sessions_max, intensity_lower)
```

- [ ] **Step 2: 验证函数仍然返回合理值**

```bash
cd apps/backend/src && python -c "
from marathon_qa_assistant.core.half_marathon_capacity_budget import build_half_marathon_capacity_budget
result = build_half_marathon_capacity_budget(
    weekly_volume_km=40, phase_id='general', available_days_count=5,
    phase_family='base_1', total_training_sessions=5
)
print('quality_sessions_max:', result['quality_sessions_max'])
"
```

预期: `quality_sessions_max: 1`（5 练 + 基础期 → 上限 = 下限 = 1）

- [ ] **Step 3: Commit**

```bash
git add apps/backend/src/marathon_qa_assistant/core/half_marathon_capacity_budget.py
git commit -m "feat: wire intensity bounds into capacity budget with phase_family/total_sessions"
```

---

### Task 3: 更新 `_build_week_days()` 传递 `phase_family`

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/core/training_plan_skeleton.py:1759-1792`

- [ ] **Step 1: 在 `_build_week_days()` 中计算 phase_family 并传入预算函数**

找到 line 1751 附近的 `hmp_week_decision = compose_hmp_week_sessions(` 调用，在它之前添加：

```python
    # 计算当前阶段的 phase_family，用于强度课约束
    current_phase_family = _phase_family(mesocycle.name)
    total_training_sessions = len(available_days)  # 当前单练模式

    hmp_week_decision = compose_hmp_week_sessions(
        ...
        capacity_budget=build_half_marathon_capacity_budget(
            weekly_volume_km=weekly_volume_km,
            phase_id=phase_id or "general",
            available_days_count=len(available_days),
            recent_four_week_mileage_km=hm_protocol_context.get("input_recent_four_week_mileage_km"),
            recent_marathon=bool(hm_protocol_context.get("recent_marathon")),
            fatigue_or_injury=bool(hm_protocol_context.get("fatigue_or_injury")),
            speed_calibration_available=bool(pace_calibration.get("speed_calibration_available")),
            phase_family=current_phase_family,           # 新增
            total_training_sessions=total_training_sessions,  # 新增
        ),
    )
```

- [ ] **Step 2: 添加低频长距离约束**

在 line 1789 附近（`quality_sessions_max == 1` 判断），添加低频长距离降级：

```python
        # 低频训练者长距离负荷约束 (来源: Pfitzinger 低频计划模板 + Gabbett ACWR)
        if total_training_sessions <= 4 and secondary_quality_day:
            secondary_type = "轻松跑"
            secondary_main_set = _easy_km_text(8.0, _format_pace_range(threshold_pace_seconds + 45, threshold_pace_seconds + 65))
            secondary_note = "周训练≤4天且含长距离课，强度课上限保持1节。本次课降级为轻松跑。"  # 修改原有 note
        elif capacity_budget.get("quality_sessions_max") == 1 and secondary_quality_day:
            secondary_type = "轻松跑"
            secondary_main_set = _easy_km_text(8.0, _format_pace_range(threshold_pace_seconds + 45, threshold_pace_seconds + 65))
            secondary_note = "近4周跑量或恢复约束触发容量预算,本次次课降级为轻松跑。"
```

- [ ] **Step 3: Commit**

```bash
git add apps/backend/src/marathon_qa_assistant/core/training_plan_skeleton.py
git commit -m "feat: pass phase_family and total_sessions to capacity budget; add low-frequency long-run constraint"
```

---

### Task 4: 更新 `periodization_advisor.py` 提示词

**Files:**
- Modify: `apps/backend/src/marathon_qa_assistant/core/periodization_advisor.py:155-199`

- [ ] **Step 1: 在 `_build_advisor_prompt()` 添加约束范围上下文**

在提示词的 `## 决策任务` 段落之后、`## 输出格式` 之前插入：

```python
        "",
        "## 强度课数量约束（不可超出）",
        f"- 当前训练总课次: {total_sessions} 次/周",
        f"- 允许强度课范围: {intensity_lower}-{intensity_upper} 节/周",
        f"- 上限来源: Seiler 2010 (20% sessions), Stoggl 2014 (B 级)",
        f"- 下限来源: Pfitzinger Advanced Marathoning, Daniels Running Formula (A 级)",
        "- 注意: 基础期(base_1/base_2)必须取下限, 比赛专项期(peak)取上限, 减量期(taper)强制1节",
        "- 伤病/近全马: 强制1节",
        f"- 当前阶段: {phase_family}",
```

需要在 `_build_advisor_prompt()` 签名中新增 `total_sessions` 和 `phase_family` 参数，并在 `get_periodization_advisory()` 调用处传入。

- [ ] **Step 2: 更新 `get_periodization_advisory()` 签名和调用**

```python
def get_periodization_advisory(
    profile: Dict[str, Any],
    total_weeks: int,
    race_type: str = "general",
    enable_llm: bool = True,
    total_sessions: int = 5,        # 新增
    phase_family: str = "general",  # 新增
) -> PeriodizationAdvisory:
```

在构建提示词时传入新参数：

```python
    prompt = _build_advisor_prompt(
        profile, total_weeks, race_type, evidence_text,
        total_sessions=total_sessions, phase_family=phase_family,
    )
```

- [ ] **Step 3: Commit**

```bash
git add apps/backend/src/marathon_qa_assistant/core/periodization_advisor.py
git commit -m "feat: add intensity bounds context to periodization advisor prompt"
```

---

### Task 5: 编写单元测试

**Files:**
- Modify: `tests/test_half_marathon_capacity_budget.py`（新建测试类）

- [ ] **Step 1: 添加 `_frequency_bounds` 参数化测试**

```python
import pytest
from marathon_qa_assistant.core.half_marathon_capacity_budget import (
    _frequency_bounds, _compute_intensity_bounds,
)

@pytest.mark.parametrize("total_sessions, expected", [
    (3, (1, 1)),
    (5, (1, 1)),
    (7, (1, 2)),
    (10, (1, 2)),
    (14, (2, 3)),
])
def test_frequency_bounds_by_session_count(total_sessions, expected):
    assert _frequency_bounds(total_sessions) == expected


@pytest.mark.parametrize("total_sessions, phase, expected", [
    # 基础期: 上限 = 下限
    (5, "base_1", (1, 1)),
    (7, "base_2", (1, 1)),
    # 建设期: 中间值
    (7, "build", (1, 1)),   # (1,2) → build → (1, max(1,2-1)) = (1,1)
    (10, "build", (1, 1)),  # (1,2) → build → (1,1)
    (14, "build", (2, 2)),  # (2,3) → build → (2, max(2,3-1)) = (2,2)
    # 比赛专项期: 取上限
    (7, "peak", (2, 2)),
    (10, "peak", (2, 2)),
    (14, "peak", (3, 3)),
    # 减量期: 强制 1
    (7, "taper", (1, 1)),
    (14, "taper", (1, 1)),
    # 导入期: 取下限
    (5, "intro", (1, 1)),
])
def test_compute_intensity_bounds_by_phase(total_sessions, phase, expected):
    assert _compute_intensity_bounds(total_sessions, phase) == expected


def test_compute_intensity_bounds_injury_forces_one():
    result = _compute_intensity_bounds(10, "peak", {"injury_or_fatigue": True})
    assert result == (1, 1)


def test_compute_intensity_bounds_recent_marathon_forces_one():
    result = _compute_intensity_bounds(14, "peak", {"recent_marathon": True})
    assert result == (1, 1)


def test_capacity_budget_respects_intensity_bounds():
    """集成验证: build_half_marathon_capacity_budget 使用新的 bounds 逻辑。"""
    from marathon_qa_assistant.core.half_marathon_capacity_budget import (
        build_half_marathon_capacity_budget,
    )
    result = build_half_marathon_capacity_budget(
        weekly_volume_km=50,
        phase_id="general",
        available_days_count=7,
        phase_family="base_1",
        total_training_sessions=7,
    )
    assert result["quality_sessions_max"] == 1  # 7练+基础期 → 上限=下限=1
```

- [ ] **Step 2: 运行测试验证通过**

```bash
python -m pytest tests/test_half_marathon_capacity_budget.py -v -k "frequency_bounds or intensity_bounds or capacity_budget"
```

预期: 全部 PASS

- [ ] **Step 3: 运行回归测试**

```bash
python -m pytest tests/test_workout_template_retriever.py tests/test_training_plan_skeleton.py -v --tb=line
```

预期: 现有测试全过（30+ 项）

- [ ] **Step 4: Commit**

```bash
git add tests/test_half_marathon_capacity_budget.py
git commit -m "test: add parametric intensity bounds tests with phase/injury coverage"
```

---

## 依赖关系

```
Task 1 (新函数) → Task 2 (接入预算) → Task 3 (骨架层接入) → Task 5 (测试)
Task 4 (LLM 提示词) ← 可并行于 Task 2/3
```

## 验证方案

```bash
# 1. 单元测试
python -m pytest tests/test_half_marathon_capacity_budget.py -v

# 2. 回归测试 (不破坏现有功能)
python -m pytest tests/test_workout_template_retriever.py tests/test_training_plan_skeleton.py -v

# 3. 对照验证: Pfitzinger 18/35/55 英里计划 (手动检查)
# 预期: 18mpw (3-4 练) → quality_sessions_max = 1
#       35mpw (5-6 练) → quality_sessions_max = 1-2 (看阶段)
#       55mpw (6-7 练) → quality_sessions_max = 1-2 (看阶段)

# 4. 安全边界验证
python -c "
from marathon_qa_assistant.core.half_marathon_capacity_budget import _compute_intensity_bounds
# 伤病强制 1
assert _compute_intensity_bounds(14, 'peak', {'injury_or_fatigue': True}) == (1, 1)
# 基础期不可超过 1
assert _compute_intensity_bounds(14, 'base_1') == (1, 1)
# cap 不超过 3
assert _compute_intensity_bounds(20, 'peak')[1] <= 3
print('All safety checks passed')
"
```
