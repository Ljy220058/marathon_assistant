import json
from pathlib import Path

import pytest

from marathon_qa_assistant.services.kb.runtime_v2 import build_v2_runtime_index
from tools.kb.build_commercial_libraries import build_commercial_libraries
from tools.kb.build_commercial_readiness_report import build_commercial_readiness_report
from tools.kb.extract_expert_evidence import extract_expert_evidence
from tools.kb.register_expert_source_batch import register_expert_source_batch
from tools.kb.review_expert_sources_for_commercial_staging import review_expert_sources_for_commercial_staging


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _source(**overrides) -> dict:
    payload = {
        "source_registry_id": "src_protocol_taper_guideline",
        "title": "Marathon Taper Guidance",
        "source_type": "official_guideline",
        "authors_or_owner": "Example Running Medicine Association",
        "year": "2026",
        "source_url": "https://example.org/guidelines/marathon-taper",
        "source_file": "marathon_taper.url",
        "license_status": "link_only",
        "download_status": "metadata_only",
        "evidence_domain": "protocol",
        "knowledge_layer": "source_registry",
        "domain_pack": "training_protocols",
        "allowed_use": "core_prescription",
        "prescription_permission": "can_write_core",
        "quality_tier": "candidate",
        "freshness_status": "current",
        "needs_review": True,
        "review_status": "candidate",
        "metadata": {
            "accessed_at": "2026-05-28",
            "date_basis": "page_date",
            "canonical_url": "https://example.org/guidelines/marathon-taper",
            "authority_tier": "official_guideline",
            "selection_reason": "Specific marathon taper prescription boundary source.",
            "gap_target": "training_protocols",
            "commercial_risks": ["stale_evidence_risk"],
            "claim": "Reduce training volume during the taper while preserving some intensity.",
            "section": "Tapering",
            "quote_or_snippet": "Reduce volume while maintaining race-specific intensity during taper weeks.",
            "applicable_to": ["marathon runners"],
            "not_applicable_to": ["acute injury"],
            "contraindications": ["chest pain", "syncope"],
        },
    }
    payload.update(overrides)
    return payload


def _review(source_id: str, actor: str, **overrides) -> dict:
    payload = {
        "review_report_id": f"review_{source_id}_{actor}",
        "source_registry_id": source_id,
        "review_actor": actor,
        "decision": "pass_for_core_prescription",
        "allowed_use": "core_prescription",
        "blocked_use": ["diagnosis"],
        "reasons": ["Source is specific and bounded for training prescription."],
        "confidence": "high",
        "evidence_ids": [f"ev_{source_id}_001"],
        "red_flag": False,
    }
    payload.update(overrides)
    return payload


def test_register_commercial_source_batch_rejects_invalid_enum_before_normalization(tmp_path):
    batch = tmp_path / "sources.jsonl"
    _write_jsonl(batch, [_source(evidence_domain="training_protocols")])

    with pytest.raises(ValueError, match="invalid_enum"):
        register_expert_source_batch(
            registry_path=tmp_path / "empty.jsonl",
            batch_files=[batch],
            registry_out=tmp_path / "commercial_source_library.jsonl",
            queue_out=tmp_path / "queue.jsonl",
            summary_out=tmp_path / "summary.json",
            audit_out=tmp_path / "source_audit.json",
        )


def test_register_commercial_source_batch_reports_duplicate_canonical_url_and_required_audit_metadata(tmp_path):
    batch_a = tmp_path / "sources_a.jsonl"
    batch_b = tmp_path / "sources_b.jsonl"
    _write_jsonl(batch_a, [_source(source_registry_id="src_a")])
    _write_jsonl(
        batch_b,
        [
            _source(
                source_registry_id="src_b",
                title="Duplicate Taper Guidance",
                metadata={
                    "accessed_at": "2026-05-28",
                    "canonical_url": "https://example.org/guidelines/marathon-taper",
                    "authority_tier": "official_guideline",
                    "selection_reason": "Duplicate deep link should be reported.",
                    "gap_target": "training_protocols",
                },
            )
        ],
    )

    report = register_expert_source_batch(
        registry_path=tmp_path / "empty.jsonl",
        batch_files=[batch_a, batch_b],
        registry_out=tmp_path / "commercial_source_library.jsonl",
        queue_out=tmp_path / "queue.jsonl",
        summary_out=tmp_path / "summary.json",
        audit_out=tmp_path / "source_audit.json",
    )

    audit = json.loads((tmp_path / "source_audit.json").read_text(encoding="utf-8"))
    assert report["batch_records"] == 2
    assert audit["duplicate_canonical_urls"][0]["canonical_url"] == "https://example.org/guidelines/marathon-taper"
    assert audit["missing_required_audit_metadata"]["src_b"] == ["date_basis"]
    assert audit["candidate_permission_boundary_counts"]["candidate"] == 2


def test_commercial_review_requires_two_passes_and_blocks_red_flags(tmp_path):
    sources = tmp_path / "commercial_source_library.jsonl"
    reports = tmp_path / "agent_review_reports.jsonl"
    _write_jsonl(sources, [_source(), _source(source_registry_id="src_heat", evidence_domain="medical_safety", domain_pack="medical_risk", allowed_use="risk_gate", prescription_permission="explanation_only")])
    _write_jsonl(
        reports,
        [
            _review("src_protocol_taper_guideline", "authority_reviewer"),
            _review("src_protocol_taper_guideline", "sports_science_reviewer"),
            _review("src_protocol_taper_guideline", "release_auditor"),
            _review("src_heat", "authority_reviewer", decision="red_flag", red_flag=True),
            _review("src_heat", "medical_safety_reviewer", decision="pass_for_risk_gate_only", allowed_use="risk_gate"),
        ],
    )

    result = review_expert_sources_for_commercial_staging(
        source_library_path=sources,
        review_reports_path=reports,
        reviewed_sources_out=tmp_path / "reviewed_sources.jsonl",
        audit_out=tmp_path / "review_audit.json",
    )
    reviewed = {row["source_registry_id"]: row for row in _read_jsonl(tmp_path / "reviewed_sources.jsonl")}

    assert result["commercial_staging_eligible_count"] == 1
    assert reviewed["src_protocol_taper_guideline"]["commercial_status"] == "commercial_staging_eligible"
    assert reviewed["src_protocol_taper_guideline"]["human_reviewed"] is False
    assert reviewed["src_heat"]["commercial_status"] == "candidate"


def test_extract_evidence_and_split_commercial_libraries_enforce_usage_boundaries(tmp_path):
    reviewed_sources = tmp_path / "reviewed_sources.jsonl"
    review_reports = tmp_path / "agent_review_reports.jsonl"
    _write_jsonl(
        reviewed_sources,
        [
            _source(commercial_status="commercial_staging_eligible", human_reviewed=False, review_report_ids=["r1", "r2"]),
            _source(
                source_registry_id="src_heat",
                title="Heat Illness Warning Signs",
                evidence_domain="medical_safety",
                domain_pack="medical_risk",
                allowed_use="risk_gate",
                prescription_permission="explanation_only",
                commercial_status="commercial_staging_eligible",
                review_report_ids=["r3", "r4"],
                metadata={
                    **_source()["metadata"],
                    "canonical_url": "https://example.org/health/heat-illness",
                    "claim": "Stop activity and seek help for heat illness red flags.",
                    "section": "Warning signs",
                    "quote_or_snippet": "Confusion, fainting, or persistent symptoms require urgent help.",
                    "gap_target": "medical_risk",
                },
            ),
        ],
    )
    _write_jsonl(review_reports, [_review("src_protocol_taper_guideline", "sports_science_reviewer"), _review("src_protocol_taper_guideline", "release_auditor"), _review("src_heat", "authority_reviewer", decision="pass_for_risk_gate_only", allowed_use="risk_gate"), _review("src_heat", "medical_safety_reviewer", decision="pass_for_risk_gate_only", allowed_use="risk_gate")])

    extract_expert_evidence(
        reviewed_sources_path=reviewed_sources,
        review_reports_path=review_reports,
        evidence_out=tmp_path / "expert_evidence.jsonl",
        audit_out=tmp_path / "evidence_audit.json",
    )
    report = build_commercial_libraries(
        evidence_path=tmp_path / "expert_evidence.jsonl",
        output_dir=tmp_path,
        staging_chunks_out=tmp_path / "commercial_staging_chunks.jsonl",
    )

    core = _read_jsonl(tmp_path / "commercial_core_prescription_library_20260528.jsonl")
    risk = _read_jsonl(tmp_path / "commercial_risk_gate_library_20260528.jsonl")
    chunks = _read_jsonl(tmp_path / "commercial_staging_chunks.jsonl")
    assert report["library_counts"]["commercial_core_prescription_library"] == 1
    assert report["library_counts"]["commercial_risk_gate_library"] == 1
    assert core[0]["prescription_permission"] == "can_write_core"
    assert risk[0]["allowed_use"] == "risk_gate"
    assert {chunk["source_registry_id"] for chunk in chunks} == {"src_protocol_taper_guideline", "src_heat"}


def test_build_commercial_readiness_report_blocks_candidate_fake_human_review_and_runtime_replacement(tmp_path):
    source_audit = tmp_path / "source_audit.json"
    reviews = tmp_path / "reviews.jsonl"
    evidence = tmp_path / "evidence.jsonl"
    gold = tmp_path / "gold.json"
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "readiness.json"
    source_audit.write_text(json.dumps({"missing_required_audit_metadata": {}, "duplicate_canonical_urls": []}), encoding="utf-8")
    _write_jsonl(reviews, [_review("src_protocol_taper_guideline", "authority_reviewer"), _review("src_protocol_taper_guideline", "sports_science_reviewer")])
    _write_jsonl(evidence, [{"evidence_id": "ev1", "source_registry_id": "src_protocol_taper_guideline", "commercial_status": "candidate", "human_reviewed": True, "evidence_domain": "protocol", "allowed_use": "core_prescription", "prescription_permission": "can_write_core", "claim": "claim", "canonical_url": "https://example.org", "section": "s", "applicable_to": ["runner"], "contraindications": ["red flag"]}])
    gold.write_text(json.dumps({"passed": False, "red_flag_failures": ["knee pain"]}), encoding="utf-8")
    manifest.write_text(json.dumps({"can_replace_runtime": True}), encoding="utf-8")

    report = build_commercial_readiness_report(
        source_audit_path=source_audit,
        review_reports_path=reviews,
        evidence_path=evidence,
        gold_qa_report_path=gold,
        manifest_path=manifest,
        output_path=output,
    )

    assert report["commercial_staging_ready"] is False
    assert "candidate_evidence_in_commercial_staging" in report["release_blockers"]
    assert "fake_human_review_flag" in report["release_blockers"]
    assert "staging_manifest_can_replace_runtime_true" in report["release_blockers"]


def test_commercial_staging_runtime_forces_can_replace_runtime_false(tmp_path):
    preview = tmp_path / "commercial_staging_chunks.jsonl"
    manifest = tmp_path / "manifest.json"
    release_report = tmp_path / "kb_release_report.json"
    _write_jsonl(
        preview,
        [
            {
                "chunk_id": "commercial_ev1",
                "source_registry_id": "src_protocol_taper_guideline",
                "source_file": "marathon_taper.url",
                "source_url": "https://example.org/guidelines/marathon-taper",
                "local_path": "data/knowledge/governance/expert_evidence_20260528_b.jsonl",
                "page": 1,
                "section": "Tapering",
                "text": "Reduce training volume during the taper while preserving some intensity.",
                "language": "en",
                "evidence_domain": "protocol",
                "knowledge_layer": "document_index",
                "domain_pack": "training_protocols",
                "allowed_use": "core_prescription",
                "prescription_permission": "can_write_core",
                "quality_tier": "commercial_staging_eligible",
            }
        ],
    )
    release_report.write_text(json.dumps({"commercial_release_ready": True, "approved_records": 99, "ready_records": 99}), encoding="utf-8")

    report = build_v2_runtime_index(
        preview_path=preview,
        output_dir=tmp_path / "expert_approved_staging_20260528",
        manifest_path=manifest,
        release_report_path=release_report,
        commercial_staging=True,
        save_func=lambda out_dir, chunks, vectorizer, matrix, bm25: {"chunks_file": str(out_dir / "chunks.jsonl"), "faiss_dir": str(out_dir / "faiss_db")},
    )

    assert report["commercial_staging"] is True
    assert report["can_replace_runtime"] is False
    assert report["release_ready"] is False


def test_commercial_source_audit_reports_authority_license_risk_and_domain_gaps(tmp_path):
    batch = tmp_path / "sources.jsonl"
    _write_jsonl(
        batch,
        [
            _source(source_registry_id="src_protocol", metadata={**_source()["metadata"], "authority_tier": "official_guideline"}),
            _source(
                source_registry_id="src_heat",
                evidence_domain="environment_race_context",
                domain_pack="environment_race_context",
                allowed_use="risk_gate",
                prescription_permission="explanation_only",
                license_status="summary_allowed",
                metadata={
                    **_source()["metadata"],
                    "canonical_url": "https://example.org/heat/athletes",
                    "authority_tier": "public_health_agency",
                    "gap_target": "environment_race_context",
                    "commercial_risks": ["medical_advice_risk", "geographic_applicability_risk"],
                },
            ),
        ],
    )

    report = register_expert_source_batch(
        registry_path=tmp_path / "empty.jsonl",
        batch_files=[batch],
        registry_out=tmp_path / "commercial_source_library.jsonl",
        audit_out=tmp_path / "source_audit.json",
    )
    audit = report["source_audit"]

    assert audit["candidate_source_count"] == 2
    assert audit["unique_canonical_url_count"] == 2
    assert audit["authority_tier_counts"] == {"official_guideline": 1, "public_health_agency": 1}
    assert audit["license_status_counts"] == {"link_only": 1, "summary_allowed": 1}
    assert audit["commercial_risk_counts"] == {
        "geographic_applicability_risk": 1,
        "medical_advice_risk": 1,
        "stale_evidence_risk": 1,
    }
    assert audit["deep_link_issue_source_ids"] == []
    assert "medical_risk" in audit["domain_gaps"]
    assert audit["coverage_ready"] is False


def test_commercial_source_audit_flags_homepage_like_candidate(tmp_path):
    batch = tmp_path / "sources.jsonl"
    _write_jsonl(
        batch,
        [
            _source(
                source_registry_id="src_homepage",
                source_url="https://example.org/",
                metadata={**_source()["metadata"], "canonical_url": "https://example.org/"},
            )
        ],
    )

    report = register_expert_source_batch(
        registry_path=tmp_path / "empty.jsonl",
        batch_files=[batch],
        registry_out=tmp_path / "commercial_source_library.jsonl",
        audit_out=tmp_path / "source_audit.json",
    )

    assert report["source_audit"]["deep_link_issue_source_ids"] == ["src_homepage"]
