from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "apps" / "backend" / "src"
for path in (ROOT, BACKEND_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _install_ragas_legacy_import_shims() -> None:
    module_name = "langchain_community.chat_models.vertexai"
    if module_name in sys.modules:
        return

    try:
        __import__(module_name)
        return
    except ModuleNotFoundError:
        pass

    module = types.ModuleType(module_name)

    class ChatVertexAI:  # pragma: no cover - compatibility placeholder only
        pass

    module.ChatVertexAI = ChatVertexAI
    sys.modules[module_name] = module


_install_ragas_legacy_import_shims()

from ragas.run_config import RunConfig

from marathon_qa_assistant.services.vector_store import (
    build_bm25_fallback_index,
    load_chunks,
    load_vector_kb,
    retrieve,
)
from tools.kb.evaluate_rag_ragas import (
    _metric_names,
    _summarize_scores,
    build_ragas_metrics,
    llm,
    embeddings,
)


DEFAULT_VECTOR_DIR = ROOT / "data" / "vector_kb" / "v2"
DEFAULT_OUTPUT = ROOT / "artifacts" / "research_runs" / "ragas_scores_v2.jsonl"


def _load_existing_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        sample_id = str(row.get("id") or "")
        if sample_id and not row.get("error"):
            ids.add(sample_id)
    return ids


def _select_items(
    dataset: list[dict[str, Any]],
    *,
    start: int,
    limit: int | None,
    completed_ids: set[str],
) -> list[dict[str, Any]]:
    sliced = dataset[start:]
    if limit is not None:
        sliced = sliced[:limit]
    return [item for item in sliced if str(item.get("id") or "") not in completed_ids]


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


async def _evaluate_item(
    item: dict[str, Any],
    *,
    chunks: list[dict[str, Any]],
    vectorizer: Any,
    matrix: Any,
    bm25: Any,
    retrieval_backend: str,
    top_k: int,
    dataset_cls: Any,
    evaluate: Any,
    metrics: list[Any],
    metric_names: list[str],
    timeout: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    hits = retrieve(item["question"], chunks, vectorizer, matrix, top_k=top_k, bm25=bm25)
    contexts = [hit["text"] for hit in hits]
    prompt = (
        "请根据以下背景信息回答问题：\n\n"
        f"背景：\n{chr(10).join(contexts)}\n\n"
        f"问题：\n{item['question']}"
    )
    response = await llm.ainvoke(prompt)
    dataset = dataset_cls.from_dict(
        {
            "question": [item["question"]],
            "contexts": [contexts],
            "answer": [response.content],
            "ground_truth": [item["ground_truth"]],
        }
    )
    result = evaluate(
        dataset,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
        run_config=RunConfig(timeout=timeout),
        batch_size=1,
    )
    return {
        "id": item["id"],
        "question": item["question"],
        "sample_type": item.get("sample_type") or "positive",
        "expected_domain": item.get("expected_domain") or "",
        "reference_chunk_id": item.get("reference_chunk_id") or "",
        "retrieved_ids": [hit["chunk_id"] for hit in hits],
        "retrieval_backend": retrieval_backend,
        "scores": _summarize_scores(result, metric_names),
        "answer": response.content,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run resumable per-sample RAGAS evaluation for the v2 eval dataset.")
    parser.add_argument("--vector-dir", default=str(DEFAULT_VECTOR_DIR))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--retrieval-backend", choices=["auto", "bm25"], default="auto")
    parser.add_argument("--rerun", action="store_true", help="Ignore completed sample ids already present in output.")
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    vector_dir = Path(args.vector_dir)
    output = Path(args.output)
    dataset = json.loads((vector_dir / "eval_dataset.json").read_text(encoding="utf-8"))
    completed_ids = set() if args.rerun else _load_existing_ids(output)
    items = _select_items(dataset, start=args.start, limit=args.limit, completed_ids=completed_ids)

    Dataset, evaluate, metrics = build_ragas_metrics()
    metric_names = _metric_names(metrics)
    if args.retrieval_backend == "bm25":
        chunks = load_chunks(vector_dir / "chunks.jsonl")
        vectorizer = "bm25_only"
        matrix = None
        bm25 = build_bm25_fallback_index(chunks)
        retrieval_backend = "bm25"
    else:
        chunks, vectorizer, matrix, bm25 = load_vector_kb(vector_dir)
        retrieval_backend = "faiss" if matrix is not None else "bm25_fallback"

    print(
        json.dumps(
            {
                "dataset_rows": len(dataset),
                "selected_rows": len(items),
                "already_completed": len(completed_ids),
                "output": str(output),
            },
            ensure_ascii=False,
        )
    )

    for index, item in enumerate(items, start=1):
        try:
            row = await _evaluate_item(
                item,
                chunks=chunks,
                vectorizer=vectorizer,
                matrix=matrix,
                bm25=bm25,
                retrieval_backend=retrieval_backend,
                top_k=args.top_k,
                dataset_cls=Dataset,
                evaluate=evaluate,
                metrics=metrics,
                metric_names=metric_names,
                timeout=args.timeout,
            )
        except Exception as exc:
            row = {
                "id": item.get("id"),
                "question": item.get("question"),
                "error": repr(exc),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            _append_jsonl(output, row)
            print(json.dumps({"index": index, "id": item.get("id"), "error": repr(exc)}, ensure_ascii=False))
            if not args.continue_on_error:
                raise
        else:
            _append_jsonl(output, row)
            print(
                json.dumps(
                    {
                        "index": index,
                        "id": row["id"],
                        "duration_seconds": row["duration_seconds"],
                        "scores": row["scores"],
                    },
                    ensure_ascii=False,
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
