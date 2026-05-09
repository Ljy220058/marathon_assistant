from marathon_qa_assistant.core.half_marathon_validator import validate_half_marathon_protocol_plan


def _day(day, training_type="轻松跑", main_set="40分钟轻松跑", notes=""):
    return {
        "day": day,
        "training_type": training_type,
        "main_set": main_set,
        "notes": notes,
        "warmup_km": 0,
        "main_km": 8,
        "cooldown_km": 0,
    }


def _week(index, days=None, phase="基础阶段", volume=50):
    return {
        "week_index": index,
        "phase": phase,
        "week_goal": f"第 {index} 周",
        "days": days or [_day(day) for day in ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]],
        "key_workouts": [],
        "action_suggestions": [],
        "repeat_guard_signature": {"weekly_volume_km": volume},
    }


def _plan(weeks, recent_marathon=False, input_weekly_mileage_km=50):
    return {
        "half_marathon_protocol": {
            "active": True,
            "recent_marathon": recent_marathon,
            "input_weekly_mileage_km": input_weekly_mileage_km,
        },
        "week_plans": weeks,
    }


def _plan_with_capacity_budget(weeks, budget):
    plan = _plan(weeks)
    plan["half_marathon_protocol"]["weekly_decisions"] = [
        {"week_index": week["week_index"], "capacity_budget": budget}
        for week in weeks
    ]
    return plan


def test_validator_is_noop_for_non_half_marathon_plan():
    result = validate_half_marathon_protocol_plan({"week_plans": []})

    assert result["active"] is False
    assert result["passed"] is True
    assert result["issues"] == []


def test_validator_blocks_hard_hmp_workout_during_recent_marathon_intro():
    week = _week(
        1,
        days=[
            _day("周一", "休息", ""),
            _day("周二", "半马专项", "20km @95% HMP 长距离快速跑"),
            _day("周三"),
            _day("周四"),
            _day("周五"),
            _day("周六"),
            _day("周日"),
        ],
    )

    result = validate_half_marathon_protocol_plan(_plan([week], recent_marathon=True))

    assert result["passed"] is False
    issue = next(issue for issue in result["issues"] if issue["constraint_id"] == "marathon_recovery_intro")
    assert "introductory_phase" in issue["term_ids"]
    assert issue["evidence_basis"]["source_docs"]


def test_validator_rejects_direct_jump_to_long_95_hmp_without_progression():
    week = _week(
        4,
        days=[
            _day("周一"),
            _day("周二"),
            _day("周三"),
            _day("周四", "半马专项", "22km @95% HMP 长距离快速跑"),
            _day("周五"),
            _day("周六"),
            _day("周日"),
        ],
        phase="比赛专项阶段",
    )

    result = validate_half_marathon_protocol_plan(_plan([week]))

    assert result["passed"] is False
    assert any(issue["constraint_id"] == "progress_long_fast_run" for issue in result["issues"])


def test_validator_allows_95_hmp_after_90_hmp_support_progression():
    support_week = _week(
        1,
        days=[
            _day("周一"),
            _day("周二"),
            _day("周三"),
            _day("周四", "半马辅助", "16km @90% HMP 稳定跑"),
            _day("周五"),
            _day("周六"),
            _day("周日"),
        ],
    )
    specific_week = _week(
        2,
        days=[
            _day("周一"),
            _day("周二"),
            _day("周三"),
            _day("周四", "半马专项", "21km @95% HMP 长距离快速跑"),
            _day("周五"),
            _day("周六"),
            _day("周日"),
        ],
        phase="比赛专项阶段",
    )

    result = validate_half_marathon_protocol_plan(_plan([support_week, specific_week]))

    assert not any(issue["constraint_id"] == "progress_long_fast_run" for issue in result["issues"])


def test_validator_prefers_explicit_90_hmp_template_id_over_support_text_mentions_95():
    week = _week(
        1,
        days=[
            _day("周一"),
            _day("周二", "渐进跑", "hm_90_support_endurance：12km @90% HMP 稳定跑，作为95% HMP长距离快速跑前置支撑"),
            _day("周三"),
            _day("周四"),
            _day("周五"),
            _day("周六"),
            _day("周日"),
        ],
        phase="专项能力构建阶段",
    )

    result = validate_half_marathon_protocol_plan(_plan_with_capacity_budget(
        [week],
        {
            "quality_sessions_max": 1,
            "hmp_95_max_km": 0,
            "hmp_100_total_max_km": 0,
            "hmp_105_total_max_km": 0,
        },
    ))

    assert not any(issue["constraint_id"] == "capacity_budget_exceeded" for issue in result["issues"])
    assert not any(issue["constraint_id"] == "progress_long_fast_run" for issue in result["issues"])


def test_validator_flags_early_100_hmp_progression_and_short_recovery_gap():
    week = _week(
        1,
        days=[
            _day("周一"),
            _day("周二", "半马专项", "5 x 3 公里 @100% HMP + 1公里巡航恢复"),
            _day("周三", "半马专项", "6 x 1公里 @105% HMP"),
            _day("周四"),
            _day("周五"),
            _day("周六"),
            _day("周日"),
        ],
        phase="基础阶段",
    )

    result = validate_half_marathon_protocol_plan(_plan([week]))

    assert result["passed"] is False
    assert any(issue["constraint_id"] == "race_specific_timing" for issue in result["issues"])
    assert any(issue["constraint_id"] == "quality_recovery_gap" for issue in result["issues"])


def test_validator_warns_when_sub70_volume_is_copied_to_lower_mileage_runner():
    week = _week(1, volume=125)

    result = validate_half_marathon_protocol_plan(_plan([week], input_weekly_mileage_km=45))

    assert result["passed"] is True
    assert any(issue["constraint_id"] == "no_sub70_volume_copy" for issue in result["issues"])


def test_validator_warns_when_hmp_workout_exceeds_capacity_budget():
    week = _week(
        1,
        days=[
            _day("周一"),
            _day("周二", "半马专项", "3km@100% HMP / 1km巡航恢复 × 3，累计HMP约9km"),
            _day("周三"),
            _day("周四", "半马专项速度", "4×2km @105% HMP，按当前10K能力校准"),
            _day("周五"),
            _day("周六"),
            _day("周日"),
        ],
        phase="比赛专项阶段",
    )

    result = validate_half_marathon_protocol_plan(
        _plan_with_capacity_budget(
            [week],
            {
                "quality_sessions_max": 1,
                "hmp_100_total_max_km": 4,
                "hmp_105_total_max_km": 5,
                "hmp_95_max_km": 10,
            },
        )
    )

    messages = " ".join(issue["message"] for issue in result["issues"])

    assert result["passed"] is True
    assert any(issue["constraint_id"] == "capacity_budget_exceeded" for issue in result["issues"])
    assert "超过容量预算" in messages
    assert "超过当前容量预算上限" in messages
    capacity_issue = next(issue for issue in result["issues"] if issue["constraint_id"] == "capacity_budget_exceeded")
    assert "capacity_budget" in capacity_issue["term_ids"]
    assert "Sub-70" in capacity_issue["evidence_basis"]["summary"]


def test_validator_warns_when_speed_workout_lacks_current_ability_calibration():
    week = _week(
        1,
        days=[
            _day("周一"),
            _day("周二", "半马专项速度", "8 x 1公里 @105% HMP"),
            _day("周三"),
            _day("周四"),
            _day("周五"),
            _day("周六"),
            _day("周日"),
        ],
        phase="专项能力构建阶段",
    )

    result = validate_half_marathon_protocol_plan(_plan([week]))

    assert result["passed"] is True
    assert any(issue["constraint_id"] == "dynamic_hmp_calibration" for issue in result["issues"])


def test_validator_warns_when_environment_risk_has_no_downgrade():
    week = _week(
        1,
        days=[
            _day("周一"),
            _day("周二", "半马专项", "7 x 2公里 @100% HMP + 1公里巡航恢复", notes="高温湿热"),
            _day("周三"),
            _day("周四"),
            _day("周五"),
            _day("周六"),
            _day("周日"),
        ],
        phase="比赛专项阶段",
    )

    result = validate_half_marathon_protocol_plan(_plan([week]))

    assert any(issue["constraint_id"] == "environment_or_fatigue_downgrade" for issue in result["issues"])
