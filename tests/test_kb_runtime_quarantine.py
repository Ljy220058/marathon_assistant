import json
from pathlib import Path

from marathon_qa_assistant.core.app_state import DATA_DIR
from marathon_qa_assistant.services import vector_store
from marathon_qa_assistant.services.kb.runtime_quarantine import (
    build_legacy_runtime_quarantine_report,
    filter_quarantined_chunks,
)


def test_legacy_runtime_quarantine_report_flags_book_review_sources():
    chunks = [
        {
            "chunk_id": "book-review-1",
            "source_file": "10078-60-2017-v60-2017-28.pdf",
            "page": 1,
            "text": "Section IV - Book Review. This is not a training prescription source.",
        },
        {
            "chunk_id": "training-1",
            "source_file": "training.pdf",
            "page": 1,
            "text": "Marathon training guidance.",
        },
    ]

    report = build_legacy_runtime_quarantine_report(chunks)

    assert "10078-60-2017-v60-2017-28.pdf" in report["quarantined_sources"]
    quarantined = next(item for item in report["sources"] if item["source_file"] == "10078-60-2017-v60-2017-28.pdf")
    assert quarantined["decision"] == "quarantine"
    assert "book_review_not_training_evidence" in quarantined["reasons"]
    fallback = next(item for item in report["sources"] if item["source_file"] == "training.pdf")
    assert fallback["decision"] == "explanation_only_legacy"
    assert "legacy_chunk_missing_v2_metadata" in fallback["reasons"]


def test_filter_quarantined_chunks_removes_blocked_sources(tmp_path):
    report_path = tmp_path / "legacy_runtime_quarantine_report.json"
    report_path.write_text(
        json.dumps({"quarantined_sources": ["blocked.pdf"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    chunks = [
        {"chunk_id": "a", "source_file": "blocked.pdf"},
        {"chunk_id": "b", "source_file": "allowed.pdf"},
    ]

    filtered = filter_quarantined_chunks(chunks, report_path)

    assert [chunk["chunk_id"] for chunk in filtered] == ["b"]


def test_vector_store_load_chunks_applies_legacy_quarantine_report(monkeypatch, tmp_path):
    chunks_path = tmp_path / "chunks.jsonl"
    chunks_path.write_text(
        "\n".join(
            [
                json.dumps({"chunk_id": "a", "source_file": "blocked.pdf", "page": 1, "text": "blocked"}),
                json.dumps({"chunk_id": "b", "source_file": "allowed.pdf", "page": 1, "text": "allowed"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report_path = tmp_path / "legacy_runtime_quarantine_report.json"
    report_path.write_text(json.dumps({"quarantined_sources": ["blocked.pdf"]}), encoding="utf-8")
    monkeypatch.setattr(vector_store, "LEGACY_RUNTIME_QUARANTINE_REPORT", report_path)

    chunks = vector_store.load_chunks(chunks_path)

    assert [chunk["chunk_id"] for chunk in chunks] == ["b"]


def test_generated_legacy_runtime_quarantine_report_blocks_known_book_review():
    report_path = DATA_DIR / "knowledge" / "governance" / "legacy_runtime_quarantine_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert "10078-60-2017-v60-2017-28.pdf" in report["quarantined_sources"]
    assert report["decision_counts"]["quarantine"] >= 1
    assert report["decision_counts"]["explanation_only_legacy"] >= 1
