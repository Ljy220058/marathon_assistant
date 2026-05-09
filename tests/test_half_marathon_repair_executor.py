from marathon_qa_assistant.core.half_marathon_repair_executor import apply_half_marathon_repairs
from marathon_qa_assistant.core.half_marathon_validator import validate_half_marathon_protocol_plan


def _day(day, training_type="轻松跑", main_set="40分钟轻松跑", notes=""):
    return {
        "day": day,
        "training_type": training_type,
        "main_set": main_set,
        "notes": notes,
        "warmup_km": 1.5,
        "main_km": 8.0,
        "cooldown_km": 1.0,
    }


def _week(index, days, phase="基础阶段"):
    return {
        "week_index": index,
        "phase": phase,
        "week_goal": f"第 {index} 周",
        "days": days,
        "key_workouts": [],
        "action_suggestions": [],
        "repeat_guard_signature": {"weekly_volume_km": 50},
    }


def _plan(weeks, recent_marathon=False):
    return {
        "half_marathon_protocol": {
            "active": True,
            "recent_marathon": recent_marathon,
            "input_weekly_mileage_km": 50,
        },
        "week_plans": weeks,
    }


def test_repair_executor_downgrades_recent_marathon_intro_hard_session():
    plan = _plan(
        [
            _week(
                1,
                [
                    _day("周一", "休息", "休息"),
                    _day("周二", "半马专项", "20km @95% HMP 长距离快速跑"),
                    _day("周三"),
                ],
            )
        ],
        recent_marathon=True,
    )

    validation = validate_half_marathon_protocol_plan(plan)
    repaired = apply_half_marathon_repairs(plan, validation)
    repaired_validation = validate_half_marathon_protocol_plan(repaired)
    repaired_day = repaired["week_plans"][0]["days"][1]

    assert validation["passed"] is False
    assert repaired_validation["passed"] is True
    assert repaired_day["training_type"] == "法特莱克"
    assert "hm_intro_fartlek_hills" in repaired_day["main_set"]
    assert repaired["half_marathon_protocol_repair_log"][0]["constraint_id"] == "marathon_recovery_intro"


def test_repair_executor_delays_early_100_hmp_core_session():
    plan = _plan(
        [
            _week(
                1,
                [
                    _day("周一"),
                    _day("周二", "半马专项", "5 x 3 公里 @100% HMP + 1公里巡航恢复"),
                    _day("周三"),
                ],
                phase="基础阶段",
            )
        ]
    )

    validation = validate_half_marathon_protocol_plan(plan)
    repaired = apply_half_marathon_repairs(plan, validation)
    repaired_validation = validate_half_marathon_protocol_plan(repaired)
    repaired_day = repaired["week_plans"][0]["days"][1]

    assert any(issue["constraint_id"] == "race_specific_timing" for issue in validation["issues"])
    assert repaired_validation["passed"] is True
    assert "hm_90_support_endurance" in repaired_day["main_set"]
    assert "100% HMP" not in repaired_day["main_set"]


def test_repair_executor_adds_speed_calibration_and_environment_downgrade():
    plan = _plan(
        [
            _week(
                1,
                [
                    _day("周一"),
                    _day("周二", "半马专项速度", "8 x 1公里 @105% HMP", notes="高温湿热"),
                    _day("周三"),
                ],
                phase="专项能力构建阶段",
            )
        ]
    )

    validation = validate_half_marathon_protocol_plan(plan)
    repaired = apply_half_marathon_repairs(plan, validation)
    repaired_validation = validate_half_marathon_protocol_plan(repaired)
    repaired_day = repaired["week_plans"][0]["days"][1]
    log_ids = {item["constraint_id"] for item in repaired["half_marathon_protocol_repair_log"]}

    assert {"dynamic_hmp_calibration", "environment_or_fatigue_downgrade"}.issubset(log_ids)
    assert repaired_validation["passed"] is True
    assert not repaired_validation["warnings"]
    assert "当前5K/8K/10K能力校准" in repaired_day["main_set"]
    assert "降级" in repaired_day["main_set"]


def test_repair_executor_downgrades_capacity_budget_excess():
    plan = _plan(
        [
            _week(
                1,
                [
                    _day("周一"),
                    _day("周二", "半马专项", "3km@100% HMP / 1km巡航恢复 × 3，累计HMP约9km"),
                    _day("周三"),
                ],
                phase="比赛专项阶段",
            )
        ]
    )
    plan["half_marathon_protocol"]["weekly_decisions"] = [
        {
            "week_index": 1,
            "capacity_budget": {
                "quality_sessions_max": 1,
                "hmp_100_total_max_km": 4,
                "hmp_105_total_max_km": 4,
                "hmp_95_max_km": 10,
            },
        }
    ]

    validation = validate_half_marathon_protocol_plan(plan)
    repaired = apply_half_marathon_repairs(plan, validation)
    repaired_validation = validate_half_marathon_protocol_plan(repaired)
    repaired_day = repaired["week_plans"][0]["days"][1]

    assert any(issue["constraint_id"] == "capacity_budget_exceeded" for issue in validation["issues"])
    assert "hm_90_support_endurance" in repaired_day["main_set"]
    assert not any(issue["constraint_id"] == "capacity_budget_exceeded" for issue in repaired_validation["issues"])
