import json
from pathlib import Path

from tools.kb.build_eval_dataset import (
    GOLDEN_QUESTIONS,
    build_eval_dataset,
    summarize_dataset,
)


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_golden_question_set_has_required_size_and_sample_types():
    assert len(GOLDEN_QUESTIONS) >= 50
    sample_types = {row["sample_type"] for row in GOLDEN_QUESTIONS}
    assert {"positive", "negative", "out_of_domain", "near_miss"} <= sample_types


def test_build_eval_dataset_binds_real_v2_chunks():
    chunks = _load_jsonl(Path("data/vector_kb/v2/chunks.jsonl"))

    dataset = build_eval_dataset(chunks)
    summary = summarize_dataset(dataset)

    assert summary["count"] >= 50
    assert summary["missing_required_reference_ids"] == []
    assert summary["by_sample_type"]["positive"] >= 40
    assert summary["by_sample_type"]["negative"] >= 1
    assert summary["by_sample_type"]["out_of_domain"] >= 1
    for domain in ("training_protocol", "nutrition", "injury_safety", "medical_safety"):
        assert summary["by_domain"][domain] >= 10


def test_eval_dataset_rows_include_retrieval_quality_fields():
    chunks = _load_jsonl(Path("data/vector_kb/v2/chunks.jsonl"))
    dataset = build_eval_dataset(chunks)
    row = dataset[0]

    assert row["question"]
    assert row["ground_truth"]
    assert row["reference_chunk_id"]
    assert row["relevant_ids"]
    assert row["expected_domain"]
    assert row["sample_type"]
