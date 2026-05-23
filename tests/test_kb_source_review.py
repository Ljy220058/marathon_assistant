import json
from pathlib import Path

from marathon_qa_assistant.services.kb.source_review import (
    build_source_review_queue,
    review_source_record,
    summarize_source_review_queue,
)


def test_source_review_blocks_seed_records_from_runtime_index():
    item = review_source_record(
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
    )

    assert item["review_status"] == "seed_only"
    assert item["can_enter_runtime_index"] is False
    assert "seed_only_not_runtime_source" in item["blocking_reasons"]
    assert "not_approved" in item["blocking_reasons"]


def test_source_review_requires_external_checks_before_approved_web_source_enters_runtime():
    payload = {
        "title": "Approved Web Guideline",
        "source_file": "approved-guideline.url",
        "source_url": "https://example.com/guideline",
        "source_type": "official_guideline",
        "authors_or_owner": "Example Guideline Owner",
        "year": "2026",
        "license_status": "link_only_reviewed",
        "evidence_domain": "protocol",
        "knowledge_layer": "source_registry",
        "allowed_use": "core_prescription",
        "prescription_permission": "can_write_core",
        "needs_review": False,
        "review_status": "approved",
    }

    unchecked = review_source_record(payload)
    checked = review_source_record(
        payload,
        external_checks={
            unchecked["source_registry_id"]: {
                "url_reachable": True,
                "web_canonical_checked": True,
            }
        },
    )

    assert unchecked["can_enter_runtime_index"] is False
    assert "url_reachability_not_verified" in unchecked["blocking_reasons"]
    assert "web_canonical_not_verified" in unchecked["blocking_reasons"]
    assert checked["can_enter_runtime_index"] is True


def test_source_review_queue_flags_duplicate_sources():
    records = [
        {
            "title": "Duplicate Source",
            "source_file": "a.md",
            "evidence_domain": "sports_science_reference",
            "knowledge_layer": "source_registry",
            "metadata": {"doi": "10.1000/example"},
        },
        {
            "title": "Duplicate Source",
            "source_file": "b.md",
            "evidence_domain": "sports_science_reference",
            "knowledge_layer": "source_registry",
            "metadata": {"doi": "10.1000/example"},
        },
    ]

    queue = build_source_review_queue(records)
    summary = summarize_source_review_queue(queue)

    assert all("duplicate_doi" in item["blocking_reasons"] for item in queue)
    assert all("duplicate_title" in item["blocking_reasons"] for item in queue)
    assert summary["total"] == 2
    assert summary["can_enter_runtime_index"] == 0


def test_generated_source_review_queue_records_current_registry_as_not_runtime_ready():
    queue_path = Path("data/knowledge/governance/source_review_queue.jsonl")
    summary_path = Path("data/knowledge/governance/source_review_summary.json")
    items = [json.loads(line) for line in queue_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert len(items) == 750
    assert summary["total"] == 750
    assert summary["can_enter_runtime_index"] == 0
    assert summary["status_counts"]["seed_only"] == 707
    assert "needs_review" in summary["top_blocking_reasons"]
