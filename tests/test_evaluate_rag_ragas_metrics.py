import sys

from scripts.evaluate_rag_ragas import (
    _build_chunk_lookup,
    _compute_retrieval_metrics,
    _compute_retrieval_quality_metrics,
    _install_ragas_legacy_import_shims,
)


def test_compute_retrieval_metrics_distinguishes_match_levels():
    chunks = [
        {"chunk_id": "docA_p0001_c0001", "source_file": "docA.pdf", "page": 1},
        {"chunk_id": "docA_p0001_c0002", "source_file": "docA.pdf", "page": 1},
        {"chunk_id": "docA_p0002_c0001", "source_file": "docA.pdf", "page": 2},
        {"chunk_id": "docB_p0001_c0001", "source_file": "docB.pdf", "page": 1},
    ]
    retrieval_results = [
        {"ref_id": "docA_p0001_c0001", "retrieved_ids": ["docA_p0001_c0002", "docB_p0001_c0001"]},
        {"ref_id": "docA_p0002_c0001", "retrieved_ids": ["docA_p0002_c0001", "docB_p0001_c0001"]},
        {"ref_id": "docB_p0001_c0001", "retrieved_ids": ["missing_chunk"]},
    ]

    metrics = _compute_retrieval_metrics(retrieval_results, _build_chunk_lookup(chunks))

    assert metrics["exact_chunk"]["recall"] == 1 / 3
    assert metrics["exact_chunk"]["mrr"] == 1 / 3
    assert metrics["exact_chunk"]["map"] == 1 / 3

    assert metrics["same_page"]["recall"] == 2 / 3
    assert metrics["same_page"]["mrr"] == 2 / 3
    assert metrics["same_page"]["map"] == 2 / 3

    assert metrics["same_source"]["recall"] == 2 / 3
    assert metrics["same_source"]["mrr"] == 2 / 3
    assert metrics["same_source"]["map"] == 2 / 3


def test_compute_retrieval_quality_metrics_includes_negative_and_precision_metrics():
    chunks = [
        {"chunk_id": "protocol", "source_file": "protocol.md", "domain_pack": "training_protocol", "prescription_permission": "can_write_core"},
        {"chunk_id": "nutrition", "source_file": "nutrition.md", "domain_pack": "nutrition", "prescription_permission": "can_write_core"},
        {"chunk_id": "safety", "source_file": "safety.md", "evidence_domain": "medical_risk", "prescription_permission": "explanation_only"},
    ]
    retrieval_results = [
        {
            "sample_type": "positive",
            "ref_id": "protocol",
            "retrieved_ids": ["protocol", "nutrition"],
            "expected_domain": "training_protocol",
        },
        {
            "sample_type": "negative",
            "retrieved_ids": ["safety"],
        },
        {
            "sample_type": "out_of_domain",
            "retrieved_ids": [],
        },
    ]

    metrics = _compute_retrieval_quality_metrics(retrieval_results, _build_chunk_lookup(chunks), k=2)

    assert metrics["recall@2"] == 1.0
    assert metrics["precision@2"] == 0.5
    assert metrics["mrr"] == 1.0
    assert metrics["negative_hit_rate"] == 0.5
    assert metrics["unsafe_retrieval_rate"] == 0.5
    assert "domain_mismatch_rate" in metrics


def test_retrieval_metrics_excludes_negative_samples_from_recall_denominator():
    chunks = [
        {"chunk_id": "protocol", "source_file": "protocol.md", "page": 1},
        {"chunk_id": "other", "source_file": "other.md", "page": 1},
    ]
    retrieval_results = [
        {"sample_type": "positive", "ref_id": "protocol", "retrieved_ids": ["protocol"]},
        {"sample_type": "negative", "ref_id": "", "retrieved_ids": ["other"]},
        {"sample_type": "out_of_domain", "ref_id": "", "retrieved_ids": []},
    ]

    metrics = _compute_retrieval_metrics(retrieval_results, _build_chunk_lookup(chunks))

    assert metrics["exact_chunk"]["recall"] == 1.0


def test_retrieval_quality_domain_match_uses_domain_terms():
    chunks = [
        {"chunk_id": "protocol", "source_file": "protocol.md", "domain_terms": ["training_protocol"]},
    ]
    retrieval_results = [
        {
            "sample_type": "positive",
            "ref_id": "protocol",
            "retrieved_ids": ["protocol"],
            "expected_domain": "training_protocol",
        }
    ]

    metrics = _compute_retrieval_quality_metrics(retrieval_results, _build_chunk_lookup(chunks), k=1)

    assert metrics["domain_mismatch_rate"] == 0.0


def test_ragas_legacy_import_shim_installs_missing_vertexai_module(monkeypatch):
    module_name = "langchain_community.chat_models.vertexai"
    monkeypatch.delitem(sys.modules, module_name, raising=False)

    _install_ragas_legacy_import_shims()

    assert sys.modules[module_name].ChatVertexAI
