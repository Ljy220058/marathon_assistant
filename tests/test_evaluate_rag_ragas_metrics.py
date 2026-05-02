from scripts.evaluate_rag_ragas import _build_chunk_lookup, _compute_retrieval_metrics


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
