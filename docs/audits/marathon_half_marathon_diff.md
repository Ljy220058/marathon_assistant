# 全马/半马训练计划差异清单

> 日期: 2026-06-06 | 目的: 集中梳理 backbone 中 marathon vs half_marathon 的所有分叉点，降低新跑者画像接入时的遗漏风险

## 差异维度总览

| 维度 | 全马 | 半马 |
|------|------|------|
| 距离上限 | 长距离 ≤210min, MP 段 4-6km | 长距离 ≤150min, 100% HMP 8-15km |
| 配速区间 | MP = threshold × 1.06 | HMP 含 90%/95%/100%/105%/110% 五档 |
| 阶段比例 | peak=25%, taper=15% | peak=22%, taper=17% (原值, 已修正为文献值) |
| 训练课类型 | MP混合长距离, 比赛模拟跑 | 100% HMP 配速课 (半马特有), HMP 专项配速 |
| 容量预算 | N/A (全马容量预算独立模块) | `half_marathon_capacity_budget.py` (HMP 五档配速容量上限) |

## 逐文件差异点

### 1. `workout_constraints.py` — 训练课约束表

| 课型 | 差异 |
|------|------|
| 长距离 | `max_minutes=210` (全马), `≤150min` (半马, notes 标注) |
| 马拉松配速跑 | `max_minutes=80`, `zone_range=Z4-Z5` — 全马专用 |
| 半马专项配速 | `max_minutes=100`, `zone_range=Z4-Z5` — 半马专用, 100% HMP 巡航 |
| MP混合长距离 | `max_minutes=160`, `zone_range=Z2-Z5` — 全马专用 |

### 2. `training_plan_skeleton.py` — 骨架生成器

- **`_build_quality_session()`**: `race_type` 参数控制 `options_by_phase` 分支
  - `race_type == "half_marathon"` + 长周期 → 半马专用 quality session 选项
  - 默认分支 → 全马/通用选项
- **`_build_long_run_main_set()`**: MP 段仅在 `race_type == "marathon"` 或通用模式下生成
- **`_build_secondary_session()`**: 半马模式下优先 `半马专项配速`
- **距离上限**: 长距离 min(volume × 0.35, 24km)，半马由 capacity budget 单独限制
- **配速计算** (line 1068): `marathon_pace = int(threshold_pace_seconds * 1.06)` — 全马专用

### 3. `half_marathon_capacity_budget.py` — 半马容量预算

- 半马专用模块，按 HMP 五档配速 (90%/95%/100%/105%/110%) 设置容量上限
- 全马无对应模块（容量由 workout_constraints + training_plan_skeleton 直接控制）

### 4. `half_marathon_validator.py` — 半马验证器

- HMP 协议专用验证：100% HMP 课时序 (H6)、Sub-70 跑量缩放 (H2)
- 全马计划走通用 critic_auditor 路径

### 5. `half_marathon_pace_calibration.py` — 半马配速校准

- 半马五档配速校准 (90%-110% HMP)
- 全马仅需 MP 单一配速偏移 (threshold × 1.06)

### 6. `periodization.py` — 周期化阶段

- 阶段周数分配公式对全马/半马使用同一逻辑
- 差异仅在 `race_type` 参数传递到上层选择模型层级时生效

### 7. `physiology.py` — 生理区模型

- 9 区模型通用，全马/半马无差异
- 差异体现在上层 pace calibration 如何映射到 zone_range

### 8. `half_marathon_protocol.py` — HMP 协议规则

- 半马专用：RunnerArchetypeInput、HM_PHASE_RULES、phase_sequence 选择
- 全马走 `periodization_advisor.py` (RAG + LLM)

### 9. `half_marathon_schedule_composer.py` — 半马周课表编排

- 半马专用：`compose_hmp_week_sessions()`

### 10. `half_marathon_repair_executor.py` — 半马修复执行器

- 半马专用：`apply_half_marathon_repairs()`

### 11. `periodization_advisor.py` — 周期化顾问

- `race_type` 参数传递，但决策逻辑通用
- Norway 过滤对全马/半马无差异（均基于 experience_level）

### 12. `profile_store.py` — 画像存储

- 全马和半马共享同一画像结构
- `goal` 字段区分赛事类型

### 13. `archetype_advisor.py` — 原型顾问

- `recent_marathon` 字段仅标注"全马"（`"跑者近期（1个月内）是否完成过全马比赛"`）
- 半马完赛无专用字段

### 14. `evidence_bundle.py` — 证据包

- 协议来源文档列表包含 `half_marathon_hmp_protocol.md`
- 全马证据依赖 RAG 检索

### 15. `half_marathon_glossary.py` — HMP 术语表

- 半马专用术语定义

### 16. `training_plan_context.py` — 计划上下文

- 通用模块，全马/半马无差异

## 接入新赛事类型的检查清单

当接入新赛事类型（如 10K、越野跑）时，按以下顺序检查：

1. `workout_constraints.py` — 是否有专项课型需新增？
2. `periodization.py` — 阶段比例和总周数需调整吗？
3. 容量预算 — 需要新建 `_capacity_budget.py` 还是复用现有？
4. 配速校准 — 需要新建 `_pace_calibration.py` 吗？
5. 验证器 — 需要新建 `_validator.py` 吗？
6. `training_plan_skeleton.py` — `_build_quality_session()` 需追加新 `race_type` 分支
