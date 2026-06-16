from marathon_qa_assistant.services.kb.expert_coverage import build_expert_coverage_report


def test_expert_coverage_marks_action_library_as_blocker_when_source_coverage_is_low():
    coverage_rows = [
        {
            "domain_pack": "training_protocols",
            "target_source_count": 20,
            "current_source_count": 7,
            "target_rule_count": 50,
            "current_rule_count": 63,
            "target_question_count": 10,
            "current_question_count": 10,
            "can_write_core": True,
            "gap_status": "partial",
        },
        {
            "domain_pack": "action_library",
            "target_source_count": 20,
            "current_source_count": 1,
            "target_rule_count": 100,
            "current_rule_count": 120,
            "target_question_count": 10,
            "current_question_count": 10,
            "can_write_core": True,
            "gap_status": "partial",
        },
    ]
    chunks = [
        {"domain_pack": "training_protocols", "prescription_permission": "can_write_core", "quality_tier": "internal_seed_needs_domain_review"},
        {"domain_pack": "action_library", "prescription_permission": "can_write_core", "quality_tier": "internal_seed_needs_domain_review"},
    ]

    report = build_expert_coverage_report(coverage_rows, chunks)
    coach = report["experts"]["coach_node"]

    assert coach["status"] == "blocked"
    assert "action_library" in coach["blocking_domains"]
    assert coach["domain_packs"]["action_library"]["source_coverage_ratio"] == 0.05


def test_expert_coverage_allows_nutritionist_as_partial_not_blocked():
    coverage_rows = [
        {
            "domain_pack": "nutrition_race_fueling",
            "target_source_count": 12,
            "current_source_count": 7,
            "target_rule_count": 40,
            "current_rule_count": 48,
            "target_question_count": 10,
            "current_question_count": 10,
            "can_write_core": False,
            "gap_status": "partial",
        }
    ]
    chunks = [
        {"domain_pack": "nutrition_race_fueling", "prescription_permission": "explanation_only", "quality_tier": "internal_seed_needs_domain_review"}
        for _ in range(48)
    ]

    report = build_expert_coverage_report(coverage_rows, chunks)
    nutritionist = report["experts"]["nutritionist_node"]

    assert nutritionist["status"] == "partial"
    assert nutritionist["blocking_domains"] == []
    assert nutritionist["chunk_count"] == 48


def test_expert_coverage_flags_user_profile_cases_gap():
    coverage_rows = [
        {
            "domain_pack": "user_profile_cases",
            "target_source_count": 100,
            "current_source_count": 0,
            "target_rule_count": 100,
            "current_rule_count": 0,
            "target_question_count": 10,
            "current_question_count": 10,
            "can_write_core": False,
            "gap_status": "gap",
        }
    ]

    report = build_expert_coverage_report(coverage_rows, [])

    assert "user_profile_cases" in report["global_blockers"]
    assert report["domain_packs"]["user_profile_cases"]["status"] == "gap"
