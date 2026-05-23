from marathon_qa_assistant.services.training_plan_review import build_training_plan_review


def _review_plan():
    return {
        "plan_meta": {"goal": "half marathon PB", "actual_weeks": 2},
        "phase_summary": [
            {"phase": "base", "start_week": 1, "end_week": 1},
            {"phase": "specific", "start_week": 2, "end_week": 2},
        ],
        "week_plans": [
            {"week_index": 1, "phase": "base", "days": []},
            {"week_index": 2, "phase": "specific", "days": []},
        ],
    }


def _review_days():
    return [
        {
            "week_index": 1,
            "day_index": 1,
            "training_type": "Easy run",
            "workout_type": "easy_run",
            "duration_min": 45,
            "training_load": 45,
            "evidence_tier": "action_library",
            "is_rest": False,
            "warmup": "10 min easy jog",
            "cooldown": "10 min easy jog and stretching",
            "main_set": "35 min Z2",
            "field_sources": {
                "main_set": {"source_type": "action_library"},
                "intensity": {"source_type": "protocol"},
                "duration": {"source_type": "protocol"},
            },
            "kb_metadata": {
                "knowledge_layer": "prescription_library",
                "evidence_domain": "action_library",
                "retrieval_mode": "action_library",
                "prescription_permission": "can_write_core",
            },
        },
        {
            "week_index": 1,
            "day_index": 2,
            "training_type": "Rest",
            "workout_type": "rest",
            "duration_min": 0,
            "training_load": 0,
            "evidence_tier": "protocol_rule",
            "is_rest": True,
            "warmup": "",
            "cooldown": "",
            "main_set": "Rest",
            "field_sources": {},
        },
        {
            "week_index": 1,
            "day_index": 3,
            "training_type": "Threshold",
            "workout_type": "hm_base_threshold_progression",
            "duration_min": 60,
            "training_load": 90,
            "evidence_tier": "protocol_rule",
            "is_rest": False,
            "warmup": "15 min easy jog",
            "cooldown": "10 min easy jog and mobility",
            "main_set": "3 x 8 min HMP effort",
            "field_sources": {
                "main_set": {"source_type": "action_library"},
                "intensity": {"source_type": "protocol"},
                "duration": {"source_type": "protocol"},
            },
        },
        {
            "week_index": 2,
            "day_index": 1,
            "training_type": "Strength",
            "workout_type": "strength_conditioning",
            "duration_min": 35,
            "training_load": 25,
            "evidence_tier": "kb_fallback",
            "is_rest": False,
            "warmup": "dynamic mobility",
            "cooldown": "stretching",
            "main_set": "single-leg strength and core",
            "field_sources": {
                "main_set": {"source_type": "kb_fallback"},
                "intensity": {"source_type": "protocol"},
                "duration": {"source_type": "protocol"},
            },
        },
        {
            "week_index": 2,
            "day_index": 2,
            "training_type": "Recovery",
            "workout_type": "recovery_run",
            "duration_min": 40,
            "training_load": 30,
            "evidence_tier": "llm_general_knowledge",
            "is_rest": False,
            "warmup": "walk and easy jog",
            "cooldown": "walk, stretch, foam roll",
            "main_set": "30 min easy run",
            "alternative": "bike or elliptical if pain returns",
            "field_sources": {
                "main_set": {"source_type": "protocol"},
                "intensity": {"source_type": "protocol"},
                "duration": {"source_type": "protocol"},
            },
        },
    ]


def test_training_plan_review_covers_commercial_quality_dimensions():
    review = build_training_plan_review(
        structured_training_plan=_review_plan(),
        daily_schedule_cards=_review_days(),
        training_load_summary={
            "source_type": "planned_load_proxy",
            "not_device_metric": True,
            "weekly_loads": [
                {"week_index": 1, "training_load": 135, "delta_percent_from_previous": 0, "trend_label": "baseline"},
                {"week_index": 2, "training_load": 55, "delta_percent_from_previous": -59.3, "trend_label": "deload"},
            ],
        },
    )

    assert review["review_version"] == "training_plan_review.v1"
    assert review["summary"]["not_device_metric"] is True
    assert review["summary"]["reviewed_dimensions_count"] >= 10
    assert set(review["dimensions"]) >= {
        "training_load",
        "plan_structure",
        "periodization",
        "injury_recovery",
        "rehabilitation",
        "strength_conditioning",
        "mobility_recovery",
        "injury_prevention",
        "evidence_control",
        "rag_vs_base_model",
    }
    assert review["dimensions"]["training_load"]["source_type"] == "planned_load_proxy"
    assert review["dimensions"]["training_load"]["not_device_metric"] is True
    assert "heart_rate" in review["dimensions"]["training_load"]["missing_inputs"]
    assert review["dimensions"]["evidence_control"]["core_fields_forbid"] == [
        "llm_expression",
        "llm_general_knowledge",
    ]
    assert review["dimensions"]["rag_vs_base_model"]["status"] in {"traceable", "partial_traceable"}
    assert "layered_kb" in review["dimensions"]
    assert review["dimensions"]["layered_kb"]["status"] in {"traceable", "partial_traceable", "gap"}
    assert review["dimensions"]["layered_kb"]["prescription_permission_counts"]["can_write_core"] >= 1


def test_training_plan_review_flags_missing_strength_and_mobility_gaps():
    days = [
        {
            "week_index": 1,
            "day_index": 1,
            "training_type": "Tempo",
            "workout_type": "tempo_run",
            "duration_min": 50,
            "training_load": 75,
            "evidence_tier": "action_library",
            "is_rest": False,
            "warmup": "",
            "cooldown": "",
            "main_set": "20 min tempo",
            "field_sources": {
                "main_set": {"source_type": "action_library"},
                "intensity": {"source_type": "protocol"},
                "duration": {"source_type": "protocol"},
            },
        }
    ]

    review = build_training_plan_review(
        structured_training_plan={"plan_meta": {"actual_weeks": 1}, "week_plans": [{"week_index": 1, "days": []}]},
        daily_schedule_cards=days,
        training_load_summary={"source_type": "planned_load_proxy", "not_device_metric": True},
    )

    assert review["dimensions"]["strength_conditioning"]["status"] == "gap"
    assert review["dimensions"]["mobility_recovery"]["status"] == "gap"
    assert "strength" in review["summary"]["risks"][0].lower() or review["summary"]["risks"]


def test_training_plan_review_distinguishes_v2_preview_from_commercial_core_kb():
    review = build_training_plan_review(
        structured_training_plan=_review_plan(),
        daily_schedule_cards=_review_days(),
        training_load_summary={"source_type": "planned_load_proxy", "not_device_metric": True},
        rag_health={
            "source": "v2",
            "index_schema_version": "chunk_schema_v2",
            "metadata_completeness": 1.0,
            "runtime_core_prescription_enabled": True,
            "commercial_core_prescription_enabled": False,
            "runtime_status": "runtime_preview_ready",
            "can_replace_runtime": False,
        },
    )

    boundary = review["dimensions"]["runtime_kb_boundary"]
    assert boundary["status"] == "runtime_preview_not_commercial"
    assert boundary["runtime_core_prescription_enabled"] is True
    assert boundary["commercial_core_prescription_enabled"] is False
    assert boundary["runtime_status"] == "runtime_preview_ready"
    assert boundary["can_replace_runtime"] is False
