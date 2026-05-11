import json
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).absolute().parents[1]
DEFAULT_BENCHMARK_KB_DIR = PROJECT_ROOT / "docs" / "paper_project" / "benchmark_kb"
DEFAULT_EVIDENCE_ITEMS = DEFAULT_BENCHMARK_KB_DIR / "evidence_items_v0.1.jsonl"
DEFAULT_QID_EVIDENCE_MAP = DEFAULT_BENCHMARK_KB_DIR / "qid_to_gold_evidence_v0.1.json"


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def load_gold_evidence(
    *,
    evidence_items_path: Path = DEFAULT_EVIDENCE_ITEMS,
    qid_evidence_map_path: Path = DEFAULT_QID_EVIDENCE_MAP,
) -> Dict[str, Any]:
    evidence_items_path = resolve_path(evidence_items_path)
    qid_evidence_map_path = resolve_path(qid_evidence_map_path)
    evidence_items = load_jsonl(evidence_items_path)
    qid_to_evidence_ids = json.loads(qid_evidence_map_path.read_text(encoding="utf-8-sig"))
    evidence_by_id = {str(item["evidence_id"]): item for item in evidence_items}

    missing_ids = []
    for qid, evidence_ids in qid_to_evidence_ids.items():
        for evidence_id in evidence_ids:
            if evidence_id not in evidence_by_id:
                missing_ids.append({"qid": qid, "evidence_id": evidence_id})
    if missing_ids:
        raise ValueError(f"qid_to_gold_evidence refers to unknown evidence ids: {missing_ids}")

    return {
        "evidence_by_id": evidence_by_id,
        "qid_to_evidence_ids": qid_to_evidence_ids,
        "evidence_items_path": evidence_items_path,
        "qid_evidence_map_path": qid_evidence_map_path,
    }


def truncate_text(text: str, max_chars: int) -> tuple[str, bool]:
    clean = str(text or "").strip()
    if max_chars <= 0 or len(clean) <= max_chars:
        return clean, False
    return clean[:max_chars].rstrip() + " [...]", True


def build_gold_contexts(
    qid: str,
    gold_bundle: Dict[str, Any],
    *,
    max_chars: int,
) -> List[Dict[str, Any]]:
    evidence_by_id = gold_bundle["evidence_by_id"]
    evidence_ids = gold_bundle["qid_to_evidence_ids"].get(qid, [])
    contexts: List[Dict[str, Any]] = []
    for rank, evidence_id in enumerate(evidence_ids, start=1):
        item = evidence_by_id[evidence_id]
        text_parts = []
        if item.get("quote"):
            text_parts.append(f"quote: {item['quote']}")
        if item.get("paraphrase"):
            text_parts.append(f"paraphrase: {item['paraphrase']}")
        if item.get("section"):
            text_parts.append(f"section: {item['section']}")
        text, truncated = truncate_text("\n".join(text_parts), max_chars)
        contexts.append(
            {
                "rank": rank,
                "chunk_id": str(item["evidence_id"]),
                "source_file": str(item.get("source_title") or "benchmark_kb"),
                "source_path": str(item.get("source_url_or_path") or ""),
                "page": item.get("page"),
                "score": 1.0,
                "text": text,
                "raw_text_char_count": len("\n".join(text_parts)),
                "text_truncated_for_prompt": truncated,
                "evidence_source": "gold",
                "verification_status": item.get("verification_status"),
                "section": item.get("section"),
                "risk_category": item.get("risk_category"),
            }
        )
    return contexts


def rerank_contexts(contexts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    reranked = []
    for rank, context in enumerate(contexts, start=1):
        item = dict(context)
        item["rank"] = rank
        reranked.append(item)
    return reranked
