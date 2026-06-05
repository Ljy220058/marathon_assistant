from langchain_core.documents import Document

from marathon_qa_assistant.services.vector_store import (
    _build_faiss,
    _build_faiss_batched,
    _build_query_variants,
    _chunk_anchor_metadata,
    _doc_to_hit,
    _extract_file_domain_terms,
    _filter_hits_by_domain,
    _merge_domain_terms,
    _merge_ranked_hits,
    _strip_faiss_docstore_text,
    chunk_quality_report,
    collect_chunks,
    fallback_search,
    retrieve,
    split_text_semantic,
)


def test_build_query_variants_adds_english_variant_for_chinese_query():
    variants = _build_query_variants("HIIT组6分钟步行测试的结果是什么？")

    assert len(variants) == 3
    assert variants[0] == "HIIT组6 min步行测试的结果是什么?"
    assert "步行测试" in variants[1]
    assert "6-minute walk test" in variants[1]
    assert "6-minute walk test" in variants[2]
    assert "HIIT" in variants[2]
    assert "结果是什么" not in variants[2]
    assert "min 6-minute" in variants[2]


def test_merge_ranked_hits_keeps_consensus_diagnostic_but_ranks_by_score():
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

    assert [hit["chunk_id"] for hit in merged] == ["b", "a", "c"]
    assert merged[1]["score"] == 0.82
    assert merged[1]["consensus_count"] == 2
    assert "consensus_bonus" not in merged[1]["score_breakdown"]


def test_build_faiss_batched_produces_same_number_of_vectors(monkeypatch):
    class FakeEmbeddings:
        def embed_documents(self, texts):
            return [[float(index), 1.0] for index, _text in enumerate(texts)]

        def embed_query(self, text):
            return [1.0, 1.0]

    class FakeFaiss:
        @staticmethod
        def from_embeddings(text_embeddings, embedding, metadatas=None, ids=None):
            pairs = list(text_embeddings)
            return type("Store", (), {"index": type("Index", (), {"ntotal": len(pairs)})()})()

        @staticmethod
        def from_documents(docs, embeddings):
            for doc in docs:
                embeddings.embed_query(doc.page_content)
            return type("Store", (), {"index": type("Index", (), {"ntotal": len(docs)})()})()

    monkeypatch.setattr("marathon_qa_assistant.services.vector_store.FAISS", FakeFaiss)
    docs = [Document(page_content=f"text {index}", metadata={"chunk_id": f"c{index}"}) for index in range(200)]

    batched = _build_faiss_batched(docs, FakeEmbeddings(), batch_size=64)
    sequential = FakeFaiss.from_documents(docs, FakeEmbeddings())

    assert batched.index.ntotal == sequential.index.ntotal == 200


def test_build_faiss_batched_falls_back_on_error(monkeypatch):
    class FakeEmbeddings:
        def embed_documents(self, texts):
            raise RuntimeError("batch unsupported")

    class FakeFaiss:
        fallback_called = False

        @staticmethod
        def from_documents(docs, embeddings):
            FakeFaiss.fallback_called = True
            return type("Store", (), {"docs": docs})()

    monkeypatch.setattr("marathon_qa_assistant.services.vector_store.FAISS", FakeFaiss)
    docs = [Document(page_content="text", metadata={"chunk_id": "c1"})]

    store = _build_faiss(docs, FakeEmbeddings())

    assert store.docs == docs
    assert FakeFaiss.fallback_called is True


def test_docstore_text_stripped_after_build_and_hit_restored_from_cache():
    store = type(
        "Store",
        (),
        {
            "docstore": type(
                "Docstore",
                (),
                {"_dict": {"doc1": Document(page_content="full text", metadata={"chunk_id": "c1"})}},
            )()
        },
    )()

    stripped = _strip_faiss_docstore_text(store)
    doc = store.docstore._dict["doc1"]
    hit = _doc_to_hit(doc, distance=0.5, chunks_cache={"c1": "full text"})

    assert stripped == 1
    assert doc.page_content == ""
    assert hit["text"] == "full text"


def test_hit_text_restored_from_cache():
    doc = Document(page_content="", metadata={"chunk_id": "cached", "source_file": "doc.md", "page": 2})

    hit = _doc_to_hit(doc, distance=0.25, chunks_cache={"cached": "cached full text"})

    assert hit["text"] == "cached full text"


def test_retrieve_calls_faiss_for_each_query_variant_and_merges_results(monkeypatch):
    monkeypatch.setattr(
        "marathon_qa_assistant.services.vector_store.get_settings",
        lambda: type("Settings", (), {"retrieval_variants_enabled": True, "bm25_fallback_enabled": True, "domain_filter_enabled": False, "sharded_retrieval_enabled": False})(),
    )

    class FakeFaiss:
        def __init__(self):
            self.queries = []

        def similarity_search_with_score(self, query, k):
            self.queries.append((query, k))
            if "6-minute walk test" in query and "步行测试" not in query:
                return [
                    (
                        Document(
                            page_content="English six minute walk result",
                            metadata={"chunk_id": "same", "source_file": "walk.md", "page": 1},
                        ),
                        0.2,
                    )
                ]
            return [
                (
                    Document(
                        page_content="中文步行测试结果",
                        metadata={"chunk_id": "same", "source_file": "walk.md", "page": 1},
                    ),
                    0.4,
                )
            ]

    store = FakeFaiss()
    hits = retrieve("HIIT组6分钟步行测试的结果是什么？", [], None, store, top_k=5, bm25=None)

    assert len(store.queries) == 3
    assert len(hits) == 1
    assert hits[0]["chunk_id"] == "same"
    assert hits[0]["consensus_count"] == 3
    assert hits[0]["bilingual_match"] is True
    assert "vector_fusion" in hits[0]["retrieval_mode"]


def test_parallel_retrieval_returns_same_results_as_sequential(monkeypatch):
    monkeypatch.setattr(
        "marathon_qa_assistant.services.vector_store.get_settings",
        lambda: type("Settings", (), {"retrieval_variants_enabled": True, "bm25_fallback_enabled": True, "domain_filter_enabled": False, "sharded_retrieval_enabled": False})(),
    )
    monkeypatch.setattr("marathon_qa_assistant.services.vector_store._build_query_variants", lambda _query: ["v1", "v2"])

    class FakeFaiss:
        def similarity_search_with_score(self, query, k):
            chunk_id = "a" if query == "v1" else "b"
            return [
                (
                    Document(
                        page_content=f"text for {chunk_id}",
                        metadata={"chunk_id": chunk_id, "source_file": "walk.md", "page": 1},
                    ),
                    0.1 if chunk_id == "a" else 0.3,
                )
            ]

    hits = retrieve("query", [], None, FakeFaiss(), top_k=5, bm25=None)

    assert [hit["chunk_id"] for hit in hits] == ["a", "b"]


def test_parallel_retrieval_one_variant_fails_does_not_block_others(monkeypatch):
    monkeypatch.setattr(
        "marathon_qa_assistant.services.vector_store.get_settings",
        lambda: type("Settings", (), {"retrieval_variants_enabled": True, "bm25_fallback_enabled": True, "domain_filter_enabled": False, "sharded_retrieval_enabled": False})(),
    )
    monkeypatch.setattr("marathon_qa_assistant.services.vector_store._build_query_variants", lambda _query: ["fail", "ok"])

    class FakeFaiss:
        def similarity_search_with_score(self, query, k):
            if query == "fail":
                raise RuntimeError("one variant failed")
            return [
                (
                    Document(
                        page_content="surviving result",
                        metadata={"chunk_id": "survivor", "source_file": "walk.md", "page": 1},
                    ),
                    0.2,
                )
            ]

    hits = retrieve("query", [], None, FakeFaiss(), top_k=5, bm25=None)

    assert [hit["chunk_id"] for hit in hits] == ["survivor"]


def test_parallel_retrieval_single_variant_stays_sequential(monkeypatch):
    monkeypatch.setattr(
        "marathon_qa_assistant.services.vector_store.get_settings",
        lambda: type("Settings", (), {"retrieval_variants_enabled": False, "bm25_fallback_enabled": True, "domain_filter_enabled": False, "sharded_retrieval_enabled": False})(),
    )

    class FailingExecutor:
        def __init__(self, *args, **kwargs):
            raise AssertionError("ThreadPoolExecutor should not be used for one query variant")

    class FakeFaiss:
        def similarity_search_with_score(self, query, k):
            return [
                (
                    Document(
                        page_content="single variant result",
                        metadata={"chunk_id": "single", "source_file": "single.md", "page": 1},
                    ),
                    0.2,
                )
            ]

    monkeypatch.setattr("marathon_qa_assistant.services.vector_store.ThreadPoolExecutor", FailingExecutor)

    hits = retrieve("plain english query", [], None, FakeFaiss(), top_k=5, bm25=None)

    assert [hit["chunk_id"] for hit in hits] == ["single"]


def test_fallback_search_marks_hits_as_explanation_only_current_chunks():
    chunks = [
        {
            "chunk_id": "v2-current",
            "source_file": "current.md",
            "page": 2,
            "text": "高温 热射病 风险 停止训练",
            "prescription_permission": "can_write_core",
            "allowed_use": "core_prescription",
        }
    ]

    hits = fallback_search("热射病风险", chunks, top_k=3)

    assert [hit["chunk_id"] for hit in hits] == ["v2-current"]
    assert hits[0]["retrieval_mode"] == "bm25_fallback"
    assert hits[0]["retrieval_status"] == "degraded_retrieval"
    assert hits[0]["display_mode"] == "legacy_explanation"
    assert hits[0]["prescription_permission"] == "explanation_only"
    assert hits[0]["can_write_core"] is False


def test_semantic_chunking_emits_stable_locator_metadata():
    chunks = split_text_semantic(
        "# Taper\nKeep the taper paragraph stable across edits.\n\n# Fuel\nUse carbs before race.",
        chunk_size=120,
        chunk_overlap=10,
    )

    assert chunks
    assert chunks[0]["section"]
    assert chunks[0]["chunking_strategy"] == "semantic_v1"


def test_semantic_chunk_anchor_metadata_is_stable_for_same_locator():
    first = _chunk_anchor_metadata("src_protocol", "Taper", "Keep easy volume before race.")
    second = _chunk_anchor_metadata("src_protocol", "Taper", "Keep easy volume before race.")

    assert first == second
    assert first["section_anchor"]
    assert first["paragraph_hash"]
    assert first["text_span_hash"]


def test_extract_file_domain_from_domain_pack_header():
    domains = _extract_file_domain_terms("Domain pack: nutrition_hydration_race_fueling.\n# Fueling")

    assert domains == ["nutrition"]


def test_extract_file_domain_unknown_pack_returns_empty():
    domains = _extract_file_domain_terms("Domain pack: experimental_unknown_pack.\n# Draft")

    assert domains == []


def test_extract_file_domain_without_header_returns_empty():
    assert _extract_file_domain_terms("# Fueling\nNo explicit domain pack.") == []


def test_merge_domain_terms_keeps_file_domain_and_chunk_domain():
    merged = _merge_domain_terms(["training_protocol"], ["medical_safety", "training_protocol"])

    assert merged == ["training_protocol", "medical_safety"]


def test_collect_chunks_inherits_file_domain_for_all_chunks(tmp_path, monkeypatch):
    source = tmp_path / "training.md"
    source.write_text("placeholder", encoding="utf-8")

    monkeypatch.setattr(
        "marathon_qa_assistant.services.vector_store.load_pages",
        lambda _path: [
            (1, "Domain pack: endurance_training_protocols.\n# Training"),
            (2, "Base mileage progression without direct domain terms."),
        ],
    )
    monkeypatch.setattr(
        "marathon_qa_assistant.services.vector_store.get_settings",
        lambda: type("Settings", (), {"semantic_chunking_enabled": False})(),
    )

    chunks, stats = collect_chunks([source], chunk_size=500, chunk_overlap=50)

    assert stats[0]["chunks"] == len(chunks)
    assert len(chunks) >= 2
    assert all(chunk["domain_terms"] == ["training_protocol"] for chunk in chunks)


def test_collect_chunks_merges_file_and_chunk_level_domains(tmp_path, monkeypatch):
    source = tmp_path / "training.md"
    source.write_text("placeholder", encoding="utf-8")

    monkeypatch.setattr(
        "marathon_qa_assistant.services.vector_store.load_pages",
        lambda _path: [(1, "Domain pack: endurance_training_protocols.\nSafety note.")],
    )
    monkeypatch.setattr(
        "marathon_qa_assistant.services.vector_store.get_settings",
        lambda: type("Settings", (), {"semantic_chunking_enabled": False})(),
    )
    monkeypatch.setattr(
        "marathon_qa_assistant.services.vector_store.extract_semantic_terms",
        lambda _text: {
            "keywords_zh": [],
            "keywords_en": [],
            "synonyms": [],
            "domain_terms": ["medical_safety"],
        },
    )

    chunks, _stats = collect_chunks([source], chunk_size=500, chunk_overlap=50)

    assert chunks
    assert chunks[0]["domain_terms"] == ["training_protocol", "medical_safety"]


def test_chunk_quality_report_includes_domain_coverage():
    report = chunk_quality_report(
        [
            {"text": "a", "source_file": "a.md", "page": 1, "domain_terms": ["training_protocol"]},
            {"text": "b", "source_file": "b.md", "page": 1, "domain_terms": []},
        ]
    )

    assert report["domain_labeled_count"] == 1
    assert report["domain_coverage_ratio"] == 0.5


def test_filter_hits_by_domain_drops_mismatched_chunks():
    """查询领域=训练方案+营养，应过滤掉医疗安全领域的片段"""
    hits = [
        {
            "chunk_id": "taper_v1",
            "score": 0.9,
            "domain_terms": ["training_protocol"],
            "text": "减量期安排",
        },
        {
            "chunk_id": "carbload_v1",
            "score": 0.85,
            "domain_terms": ["nutrition"],
            "text": "碳水加载策略",
        },
        {
            "chunk_id": "heat_stroke_v1",
            "score": 0.7,
            "domain_terms": ["medical_safety"],
            "text": "热射病识别",
        },
    ]
    # 查询包含"配速"(training_protocol)和"碳水"(nutrition)，两者都在 extract_semantic_terms 领域映射中
    filtered = _filter_hits_by_domain("配速和碳水加载怎么安排", hits)
    ids = [h["chunk_id"] for h in filtered]
    assert "taper_v1" in ids
    assert "carbload_v1" in ids
    assert "heat_stroke_v1" not in ids  # 医疗安全被过滤


def test_filter_hits_by_domain_passes_all_when_no_query_domain():
    """查询无法提取领域标签时，全部保留"""
    hits = [
        {"chunk_id": "a", "score": 0.9, "domain_terms": ["training_protocol"]},
        {"chunk_id": "b", "score": 0.8, "domain_terms": ["medical_safety"]},
    ]
    filtered = _filter_hits_by_domain("你好", hits)
    assert len(filtered) == 2


def test_filter_hits_by_domain_passes_unlabeled_chunks():
    """片段无领域标签时保留，避免误杀"""
    hits = [
        {"chunk_id": "labeled", "score": 0.9, "domain_terms": ["training_protocol"]},
        {"chunk_id": "unlabeled", "score": 0.8, "domain_terms": []},
    ]
    filtered = _filter_hits_by_domain("减量训练方案", hits)
    assert len(filtered) == 2


def test_retrieve_with_domain_filter_enabled(monkeypatch):
    """开启领域过滤后，与查询领域不匹配的片段应被过滤"""
    monkeypatch.setattr(
        "marathon_qa_assistant.services.vector_store.get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "retrieval_variants_enabled": True,
                "bm25_fallback_enabled": True,
                "domain_filter_enabled": True, "sharded_retrieval_enabled": False,
            },
        )(),
    )

    class FakeFaiss:
        def __init__(self):
            self.queries = []

        def similarity_search_with_score(self, query, k):
            self.queries.append((query, k))
            return [
                (
                    Document(
                        page_content="减量期安排策略",
                        metadata={
                            "chunk_id": "taper_v1",
                            "source_file": "taper.md",
                            "page": 1,
                            "domain_terms": ["training_protocol"],
                        },
                    ),
                    0.3,
                ),
                (
                    Document(
                        page_content="热射病识别与处理",
                        metadata={
                            "chunk_id": "heat_v1",
                            "source_file": "safety.md",
                            "page": 3,
                            "domain_terms": ["medical_safety"],
                        },
                    ),
                    0.6,
                ),
            ]

    store = FakeFaiss()
    # "配速" 在 extract_semantic_terms 中映射为 training_protocol
    # 因此 medical_safety 片段应被过滤
    hits = retrieve("配速怎么调整", [], None, store, top_k=5, bm25=None)
    ids = [h["chunk_id"] for h in hits]
    assert "taper_v1" in ids
    assert "heat_v1" not in ids
