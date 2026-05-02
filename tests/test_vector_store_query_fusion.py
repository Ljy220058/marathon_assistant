from marathon_qa_assistant.services.vector_store import _build_query_variants, _merge_ranked_hits


def test_build_query_variants_adds_english_variant_for_chinese_query():
    variants = _build_query_variants("HIIT组6分钟步行测试的结果是什么？")

    assert len(variants) == 2
    assert "步行测试" in variants[0]
    assert "6-minute walk test" in variants[0]
    assert "6-minute walk test" in variants[1]
    assert "HIIT" in variants[1]
    assert "结果是什么" not in variants[1]


def test_merge_ranked_hits_prefers_consensus_across_query_variants():
    search_runs = [
        [
            {"chunk_id": "b", "score": 0.91, "distance": 0.1, "source_file": "doc.pdf", "source_path": "", "page": 1, "text": "b", "rank_score": 0.0},
            {"chunk_id": "a", "score": 0.80, "distance": 0.2, "source_file": "doc.pdf", "source_path": "", "page": 1, "text": "a", "rank_score": 0.0},
        ],
        [
            {"chunk_id": "a", "score": 0.82, "distance": 0.18, "source_file": "doc.pdf", "source_path": "", "page": 1, "text": "a", "rank_score": 0.0},
            {"chunk_id": "c", "score": 0.79, "distance": 0.22, "source_file": "doc.pdf", "source_path": "", "page": 1, "text": "c", "rank_score": 0.0},
        ],
    ]

    merged = _merge_ranked_hits(search_runs, top_k=3)

    assert [hit["chunk_id"] for hit in merged] == ["a", "b", "c"]
    assert merged[0]["score"] == 0.82
