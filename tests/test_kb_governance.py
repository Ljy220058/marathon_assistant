import json
from dataclasses import replace
from pathlib import Path

from marathon_qa_assistant.services.kb.governance import (
    FIRST_BATCH_DOMAIN_PACKS,
    build_default_coverage_matrix,
    build_default_golden_questions,
    build_default_golden_questions_v2,
    build_evidence_drawer_payload,
    build_kb_release_report,
    build_seed_domain_pack_catalog,
    golden_question_to_v2,
    summarize_source_readiness,
    top_coverage_gaps,
    validate_golden_questions,
    validate_golden_questions_v2,
)


def test_coverage_matrix_tracks_all_first_batch_domain_packs_and_top_gaps():
    rows = build_default_coverage_matrix()
    domains = {row.domain_pack for row in rows}

    assert set(FIRST_BATCH_DOMAIN_PACKS).issubset(domains)
    assert all(row.target_question_count >= 10 for row in rows)
    assert top_coverage_gaps(rows, limit=10)
    assert any(row.domain_pack == "user_profile_cases" and row.gap_status == "gap" for row in rows)


def test_golden_questions_cover_100_plus_questions_and_required_fields():
    questions = build_default_golden_questions()
    result = validate_golden_questions(questions)

    assert len(questions) >= 100
    assert result["ready"] is True
    assert result["invalid"] == []
    assert all(result["domain_counts"][domain] >= 10 for domain in FIRST_BATCH_DOMAIN_PACKS)


def test_golden_question_fixture_is_expanded_to_100_plus_items():
    questions = json.loads(Path("tests/fixtures/kb_golden_questions.json").read_text(encoding="utf-8"))
    result = validate_golden_questions(questions)

    assert result["question_count"] >= 100
    assert result["ready"] is True


def test_golden_questions_v2_add_judge_rubric_and_safety_behavior():
    questions = build_default_golden_questions_v2()
    result = validate_golden_questions_v2(questions)

    assert len(questions) >= 100
    assert result["ready"] is True
    assert result["invalid"] == []
    assert "citation_faithfulness" in result["rubric_dimensions"]
    assert result["safety_behavior_counts"]["needs_evidence_when_protocol_or_action_library_missing"] >= 10
    assert result["safety_behavior_counts"]["medical_referral_or_risk_refused"] >= 1


def test_golden_question_v2_blocks_core_without_expected_evidence_ids():
    item = golden_question_to_v2(build_default_golden_questions()[0])
    item["expected_evidence_ids"] = []

    result = validate_golden_questions_v2([item])

    assert result["ready"] is False
    assert "core_prescription_requires_expected_evidence_ids" in result["invalid"][0]["errors"]


def test_golden_question_v2_fixture_is_judge_ready():
    questions = json.loads(Path("tests/fixtures/kb_golden_questions_v2.json").read_text(encoding="utf-8"))
    result = validate_golden_questions_v2(questions)

    assert result["question_count"] >= 100
    assert result["ready"] is True


def test_domain_pack_catalog_has_required_seed_volume_and_boundaries():
    catalog = build_seed_domain_pack_catalog()

    assert len(catalog["training_protocols"]) >= 50
    assert len(catalog["action_library"]) >= 100
    assert len(catalog["training_load"]) >= 30
    assert len(catalog["medical_risk"]) >= 40
    assert len(catalog["rehab_return_to_run"]) >= 40
    assert len(catalog["strength_conditioning"]) >= 60
    assert len(catalog["mobility_recovery"]) >= 40
    assert len(catalog["nutrition_race_fueling"]) >= 40
    assert len(catalog["environment_race_context"]) >= 30
    assert len(catalog["competitor_product_tasks"]) >= 40
    assert len(catalog["user_profile_cases"]) >= 100
    assert all(item["prescription_permission"] == "can_write_core" for item in catalog["action_library"])
    assert all(item["not_device_metric"] is True for item in catalog["training_load"])
    assert all(item["forbidden_response"] == "high_intensity_alternative_training" for item in catalog["medical_risk"])


def test_generated_governance_artifacts_satisfy_p0_to_p10_minimums():
    base = Path("data/knowledge/governance")
    registry = [
        json.loads(line)
        for line in (base / "source_registry_v2.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    coverage = json.loads((base / "coverage_matrix.json").read_text(encoding="utf-8"))
    catalog = json.loads((base / "domain_pack_seed_catalog.json").read_text(encoding="utf-8"))
    summary = json.loads((base / "golden_questions_summary.json").read_text(encoding="utf-8"))
    chunk_health = json.loads((base / "chunk_schema_v2_health.json").read_text(encoding="utf-8"))
    legacy_chunk_health = json.loads((base / "legacy_chunk_health.json").read_text(encoding="utf-8"))
    release_report = json.loads((base / "kb_release_report.json").read_text(encoding="utf-8"))
    v2_summary = json.loads((base / "golden_questions_v2_summary.json").read_text(encoding="utf-8"))

    assert len(registry) >= 150
    assert all(item.get("review_status") for item in registry)
    assert len(coverage) >= len(FIRST_BATCH_DOMAIN_PACKS)
    assert sum(len(items) for items in catalog.values()) >= 500
    assert summary["ready"] is True
    assert chunk_health["metadata_completeness"] == 1.0
    assert legacy_chunk_health["total"] >= 1000
    assert legacy_chunk_health["is_legacy_index"] is True
    assert not any(
        item["prescription_permission"] == "can_write_core"
        and item["evidence_domain"] not in {"protocol", "action_library"}
        for item in registry
    )
    assert not any("????" in item.get("metadata", {}).get("purpose", "") and item["needs_review"] is False for item in registry)
    assert release_report["approved_records"] == 0
    assert release_report["ready_records"] == 0
    assert release_report["ready_for_next_batch"] is False
    assert "no_approved_sources" in release_report["readiness_blockers"]
    assert v2_summary["ready"] is True
    assert "citation_faithfulness" in v2_summary["rubric_dimensions"]


def test_evidence_drawer_payload_never_fakes_citations():
    general = build_evidence_drawer_payload(None, field_is_core=False)
    blocked_core = build_evidence_drawer_payload(None, field_is_core=True)
    verified = build_evidence_drawer_payload(
        {
            "source_registry_id": "src_example",
            "source_file": "example.pdf",
            "source_url": "https://example.com/example.pdf",
            "page": 7,
            "section": "protocol",
            "evidence_domain": "protocol",
            "prescription_permission": "can_write_core",
            "retrieval_mode": "protocol_rule",
            "score": 1.0,
        },
        field_is_core=True,
    )
    missing_position = build_evidence_drawer_payload(
        {
            "source_registry_id": "src_example",
            "source_file": "example.pdf",
            "evidence_domain": "sports_science_reference",
            "prescription_permission": "explanation_only",
        },
        field_is_core=False,
    )

    assert general["display_mode"] == "model_general_knowledge"
    assert general["source_url"] == ""
    assert blocked_core["display_mode"] == "needs_evidence"
    assert verified["display_mode"] == "verified_source"
    assert verified["page"] == 7
    assert missing_position["display_mode"] == "needs_evidence"
    assert missing_position["source_url"] == ""


def test_source_readiness_counts_seed_reviewed_approved_and_ready_records():
    records = [
        {
            "title": "Seed Action",
            "source_file": "seed-action.json",
            "source_type": "internal_structured_rule_seed",
            "evidence_domain": "action_library",
            "knowledge_layer": "domain_pack",
            "allowed_use": "core_prescription",
            "prescription_permission": "can_write_core",
            "needs_review": False,
            "review_status": "approved",
        },
        {
            "title": "Reviewed Protocol",
            "source_file": "reviewed-protocol.md",
            "evidence_domain": "protocol",
            "knowledge_layer": "source_registry",
            "allowed_use": "core_prescription",
            "prescription_permission": "can_write_core",
            "needs_review": False,
            "review_status": "reviewed",
        },
        {
            "title": "Approved Protocol",
            "source_file": "approved-protocol.md",
            "evidence_domain": "protocol",
            "knowledge_layer": "source_registry",
            "allowed_use": "core_prescription",
            "prescription_permission": "can_write_core",
            "needs_review": False,
            "review_status": "approved",
        },
    ]

    summary = summarize_source_readiness(records)

    assert summary["seed_records"] == 1
    assert summary["reviewed_records"] == 1
    assert summary["approved_records"] == 1
    assert summary["ready_records"] == 1
    assert summary["ready_core_records"] == 1
    assert summary["needs_review_records"] == 2


def test_release_report_blocks_next_batch_when_registry_has_only_seed_records():
    questions = validate_golden_questions(build_default_golden_questions())
    rows = build_default_coverage_matrix()
    report = build_kb_release_report(
        sources_added=750,
        chunks_added=750,
        coverage_rows=rows,
        golden_question_summary=questions,
        registry_records=[
            {
                "title": "Seed Action",
                "source_file": "seed-action.json",
                "source_type": "internal_structured_rule_seed",
                "evidence_domain": "action_library",
                "knowledge_layer": "domain_pack",
                "allowed_use": "core_prescription",
                "prescription_permission": "can_write_core",
                "needs_review": False,
                "review_status": "approved",
            }
        ],
    )

    assert report["seed_records"] == 1
    assert report["approved_records"] == 0
    assert report["ready_records"] == 0
    assert report["ready_for_next_batch"] is False
    assert "no_approved_sources" in report["readiness_blockers"]
    assert "all_domain_packs_still_have_gaps" in report["readiness_blockers"]


def test_release_report_blocks_next_batch_on_safety_or_citation_violations():
    questions = validate_golden_questions(build_default_golden_questions())
    rows = build_default_coverage_matrix()
    covered_rows = [
        replace(
            row,
            current_source_count=row.target_source_count,
            current_rule_count=row.target_rule_count,
            current_question_count=row.target_question_count,
            gap_status="covered",
        )
        for row in rows
    ]
    approved_registry = [
        {
            "title": "Approved Protocol",
            "source_file": "approved-protocol.md",
            "evidence_domain": "protocol",
            "knowledge_layer": "source_registry",
            "allowed_use": "core_prescription",
            "prescription_permission": "can_write_core",
            "needs_review": False,
            "review_status": "approved",
        }
    ]
    clean = build_kb_release_report(
        sources_added=150,
        chunks_added=300,
        coverage_rows=covered_rows,
        golden_question_summary=questions,
        registry_records=approved_registry,
        violations={
            "fake_citation_violations": 0,
            "core_permission_violations": 0,
            "medical_safety_violations": 0,
            "metadata_completeness_violations": 0,
            "evaluation_regression_without_explanation": 0,
        },
    )
    blocked = build_kb_release_report(
        sources_added=20,
        chunks_added=50,
        coverage_rows=covered_rows,
        golden_question_summary=questions,
        registry_records=approved_registry,
        violations={"fake_citation_violations": 1},
    )

    assert clean["ready_for_next_batch"] is True
    assert clean["commercial_release_ready"] is True
    assert clean["still_worth_fixing"] == []
    assert blocked["ready_for_next_batch"] is False
    assert blocked["fake_citation_violations"] == 1
