from fastapi.testclient import TestClient
from marathon_qa_assistant.apps.api_app import app
from marathon_qa_assistant.apps.routers import reference as reference_router
from marathon_qa_assistant.services.kb.source_inventory import (
    classify_source_status,
    load_source_inventory_summary,
    public_source_inventory_summary,
    reset_source_inventory_cache_for_tests,
    summarize_sources_from_chunks,
)


def test_classify_source_ready_when_document_sections_exist():
    chunks = [
        {
            "source_registry_id": "src_strength",
            "source_file": "strength.md",
            "section": "document_paragraph",
            "text": "Strength training improves running economy in distance runners.",
        },
        {
            "source_registry_id": "src_strength",
            "source_file": "strength.md",
            "section": "expert_source_registry",
            "text": "source registry card",
        },
    ]

    result = classify_source_status(chunks)

    assert result["source_status"] == "ready"
    assert result["has_full_text"] is True
    assert result["chunk_count"] == 2
    assert result["body_chunk_count"] == 1
    assert result["registry_chunk_count"] == 1


def test_classify_source_registry_only_when_no_body_sections_exist():
    chunks = [
        {
            "source_registry_id": "src_safety_training_errors_2012",
            "source_file": "safety_training_errors_2012.metadata",
            "section": "registry_preview",
            "text": "Training Errors and Running Related Injuries: A Systematic Review.",
        }
    ]

    result = classify_source_status(chunks)

    assert result["source_status"] == "registry_only"
    assert result["has_full_text"] is False
    assert result["evidence_policy"] == "line_only"


def test_summarize_sources_counts_ready_and_registry_only_sources():
    chunks = [
        {
            "source_registry_id": "src_ready",
            "source_file": "ready.md",
            "domain_pack": "training_load",
            "section": "document_paragraph",
            "text": "body",
        },
        {
            "source_registry_id": "src_registry",
            "source_file": "registry.metadata",
            "domain_pack": "load_injury_safety",
            "section": "registry_preview",
            "text": "registry card",
        },
    ]

    summary = summarize_sources_from_chunks(chunks)

    assert summary["total_sources"] == 2
    assert summary["ready_sources"] == 1
    assert summary["registry_only_sources"] == 1
    assert summary["total_chunks"] == 2
    assert summary["sources"][0]["source_registry_id"] == "src_ready"
    assert summary["sources"][1]["source_registry_id"] == "src_registry"


def test_knowledge_sources_summary_endpoint_returns_source_statuses():
    client = TestClient(app)

    response = client.get("/knowledge/sources/summary")

    assert response.status_code == 200
    payload = response.json()
    assert "total_sources" in payload
    assert "ready_sources" in payload
    assert "registry_only_sources" in payload
    assert "total_chunks" in payload
    assert payload["total_sources"] >= payload["ready_sources"]


def test_knowledge_sources_summary_endpoint_redacts_sources_and_sample_text(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(
        reference_router,
        "public_source_inventory_summary",
        lambda _path: {
            "total_sources": 1,
            "total_chunks": 3,
            "ready_sources": 1,
            "registry_only_sources": 0,
            "missing_text_sources": 0,
            "status_counts": {"ready": 1},
            "domain_pack_counts": {"training_load": 1},
            "sources": [],
        },
    )

    response = client.get("/knowledge/sources/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"] == []


def test_knowledge_sources_endpoint_requires_expert_access(monkeypatch):
    client = TestClient(app)
    monkeypatch.delenv("MARATHON_EXPERT_API_TOKEN", raising=False)
    monkeypatch.delenv("MARATHON_DEV_ALLOW_EXPERT_RESPONSE", raising=False)

    response = client.get("/knowledge/sources")

    assert response.status_code == 403


def test_knowledge_sources_endpoint_returns_sources_array_for_expert(monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("MARATHON_EXPERT_API_TOKEN", "expert-test-token")
    monkeypatch.delenv("MARATHON_DEV_ALLOW_EXPERT_RESPONSE", raising=False)
    monkeypatch.setattr(
        reference_router,
        "load_source_inventory_summary",
        lambda _path: {
            "total_sources": 1,
            "total_chunks": 3,
            "ready_sources": 1,
            "registry_only_sources": 0,
            "missing_text_sources": 0,
            "status_counts": {"ready": 1},
            "domain_pack_counts": {"training_load": 1},
            "sources": [
                {
                    "source_registry_id": "src_ready",
                    "source_file": "ready.md",
                    "source_label": "Ready source",
                    "domain_pack": "training_load",
                    "source_status": "ready",
                    "has_full_text": True,
                    "evidence_policy": "answerable",
                    "chunk_count": 3,
                    "body_chunk_count": 2,
                    "registry_chunk_count": 1,
                    "sections": {"document_paragraph": 2, "registry_preview": 1},
                    "sample_text": "sample",
                }
            ],
        },
    )

    response = client.get(
        "/knowledge/sources",
        headers={
            "X-Marathon-Response-Role": "expert",
            "X-Marathon-Expert-Key": "expert-test-token",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "sources" in payload
    assert isinstance(payload["sources"], list)
    assert payload["sources"][0]["sample_text"] == "sample"


def test_source_inventory_summary_cache_reuses_loaded_chunks(tmp_path, monkeypatch):
    chunks_path = tmp_path / "chunks.jsonl"
    chunks_path.write_text(
        '{"source_registry_id":"src_ready","source_file":"ready.md","section":"document_paragraph","text":"body"}\n',
        encoding="utf-8",
    )
    calls = []

    def fake_load(path):
        calls.append(path)
        return [
            {
                "source_registry_id": "src_ready",
                "source_file": "ready.md",
                "section": "document_paragraph",
                "text": "body",
            }
        ]

    reset_source_inventory_cache_for_tests()
    monkeypatch.setattr("marathon_qa_assistant.services.kb.source_inventory.load_chunks_jsonl", fake_load)

    first = load_source_inventory_summary(chunks_path)
    second = public_source_inventory_summary(chunks_path)

    assert first["total_sources"] == 1
    assert second["sources"] == []
    assert calls == [chunks_path]
