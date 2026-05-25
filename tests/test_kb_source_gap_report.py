from marathon_qa_assistant.services.kb.source_gap_report import build_source_gap_report


def test_source_gap_report_groups_readiness_candidates_and_domain_needs_without_paths():
    source_review_queue = [
        {
            "source_registry_id": "src_action_approved",
            "title": "Approved Action",
            "domain_pack": "action_library",
            "evidence_domain": "action_library",
            "prescription_permission": "can_write_core",
            "review_status": "approved",
            "can_enter_runtime_index": True,
            "blocking_reasons": [],
            "registry_snapshot": {"local_path": "C:/Users/private/action.json"},
        },
        {
            "source_registry_id": "src_medical_candidate",
            "title": "Medical Candidate",
            "domain_pack": "medical_risk",
            "evidence_domain": "medical_safety",
            "prescription_permission": "explanation_only",
            "review_status": "candidate",
            "can_enter_runtime_index": False,
            "blocking_reasons": ["license_not_checked", "url_reachability_not_verified"],
            "registry_snapshot": {"local_path": "C:/Users/private/medical.pdf"},
        },
    ]
    release_report = {
        "coverage_matrix_delta": [
            {
                "domain_pack": "action_library",
                "subdomain": "warmup/main/cooldown",
                "current_source_count": 1,
                "target_source_count": 20,
                "current_rule_count": 5,
                "target_rule_count": 20,
                "gap_status": "partial",
                "can_write_core": True,
            },
            {
                "domain_pack": "medical_risk",
                "subdomain": "red flags/pain/sleep",
                "current_source_count": 0,
                "target_source_count": 12,
                "current_rule_count": 0,
                "target_rule_count": 12,
                "gap_status": "gap",
                "can_write_core": False,
            },
        ]
    }

    report = build_source_gap_report(
        source_review_queue=source_review_queue,
        release_report=release_report,
    )

    assert report["report_schema_version"] == "source_gap_report_v1"
    assert report["domain_pack_readiness"]["action_library"]["approved_records"] == 1
    assert report["domain_pack_readiness"]["action_library"]["runtime_ready_records"] == 1
    assert report["domain_pack_readiness"]["action_library"]["ready_core_records"] == 1
    assert report["candidate_blocker_groups"]["license_not_checked"][0]["source_registry_id"] == "src_medical_candidate"
    assert report["candidate_blocker_groups"]["url_reachability_not_verified"][0]["domain_pack"] == "medical_risk"
    assert report["domain_pack_external_source_needs"][0]["domain_pack"] == "medical_risk"
    assert report["domain_pack_external_source_needs"][0]["needed_source_count"] == 12
    assert "C:/Users" not in str(report)
    assert "local_path" not in str(report)
