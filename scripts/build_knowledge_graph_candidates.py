"""
从 v2_sharded 分片批量抽取候选知识图谱三元组，写入 knowledge_graph_candidates.jsonl。

用法:
  python scripts/build_knowledge_graph_candidates.py [--dry-run] [--domain nutrition] \
      [--max-per-domain 50] [--target-nodes 120]
"""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "backend" / "src"))

from marathon_qa_assistant.services.kb.kg_extraction import (
    ALLOWED_RELATIONS,
    EXTRACTION_SYSTEM_PROMPT,
    _entity_in_text,
    _build_candidate_id,
    _normalize_relation,
    _validate_triple,
)

V2_SHARDED_DIR = ROOT / "data" / "vector_kb" / "v2_sharded"
CANDIDATES_PATH = ROOT / "data" / "knowledge" / "governance" / "knowledge_graph_candidates.jsonl"

SHARD_NAMES = ["training_protocol", "nutrition", "injury_safety", "medical_safety", "sport_psychology"]
DEFAULT_MAX_PER_DOMAIN = 50
DEFAULT_TARGET_NODES = 120
OLLAMA_MODEL = "qwen2.5:latest"
OLLAMA_URL = "http://localhost:11434/api/generate"


def _is_not_reference(chunk: dict[str, Any]) -> bool:
    text = str(chunk.get("text", ""))
    if re.match(r'^\d{1,4}\.\s+[A-Z]', text.strip()):
        return False
    if "PMID:" in text or "doi:" in text or "doi.org" in text:
        return False
    if text.count(";") > 5:
        return False
    if text.strip().lower().startswith(("review", "open access", "abstract", "received:")):
        return False
    return True


def _is_substantive(text: str) -> bool:
    t = text.strip()
    if len(t) < 80:
        return False
    log_patterns = [
        r'^\d{1,2}/\d{1,2}[\s/]',
        r'^\d{1,2}\.\d{1,2}\s',
        r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun|周一|周二|周三|周四|周五|周六|周日)',
        r'^\d{1,2}:\d{2}[\s-]',
        r'^\d{1,2}[kK]\s',
    ]
    for pat in log_patterns:
        if re.match(pat, t) and len(t) < 200:
            return False
    alpha_ratio = sum(1 for c in t if c.isalpha()) / max(len(t), 1)
    if alpha_ratio < 0.35:
        return False
    words = t.lower().split()
    if len(words) > 20:
        from collections import Counter
        top = Counter(words).most_common(1)[0][1]
        if top > 8 and top / len(words) > 0.3:
            return False
    sentences = [s for s in re.split(r"[.!?\n]{1,2}", t) if len(s.strip()) > 10]
    if len(sentences) < 2:
        return False
    return True


def _sample_chunks(chunks: list[dict[str, Any]], domain: str, max_n: int) -> list[dict[str, Any]]:
    domain_chunks = [c for c in chunks if c.get("domain_pack") == domain]
    body_chunks = [c for c in domain_chunks if _is_not_reference(c)]
    body_chunks = [c for c in body_chunks if _is_substantive(str(c.get("text", "")))]
    if not body_chunks:
        body_chunks = [c for c in domain_chunks if _is_not_reference(c)]

    def _quality_key(c: dict[str, Any]) -> tuple:
        text = str(c.get("text", ""))
        return (
            1 if c.get("page") else 0,
            1 if 300 < len(text) < 1500 else 0,
            len(text),
        )

    body_chunks.sort(key=_quality_key, reverse=True)

    by_source: dict[str, list] = defaultdict(list)
    for c in body_chunks:
        by_source[str(c.get("source_file", ""))].append(c)

    sampled: list[dict[str, Any]] = []
    for sf, clist in by_source.items():
        body_pages = [c for c in clist if int(c.get("page") or 1) > 2]
        picks = body_pages[:3] if body_pages else clist[:3]
        sampled.extend(picks)

    already = {c["chunk_id"] for c in sampled}
    for c in body_chunks:
        if len(sampled) >= max_n:
            break
        if c["chunk_id"] not in already:
            sampled.append(c)
            already.add(c["chunk_id"])
    return sampled[:max_n]


async def _ollama_chat(prompt: str, system: str, model: str = OLLAMA_MODEL) -> str:
    import aiohttp
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 512},
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(OLLAMA_URL, json=payload,
                                timeout=aiohttp.ClientTimeout(total=120)) as resp:
            data = await resp.json()
            return data.get("response", "")


def _auto_approve(cand: dict[str, Any], by_id: dict[str, Any]) -> tuple[bool, list[str]]:
    """严格自动审核门控。"""
    reasons: list[str] = []
    chunk_id = cand.get("source_chunk_id", "")
    chunk = by_id.get(chunk_id)

    if not chunk:
        reasons.append("chunk_not_in_v2_sharded")
    else:
        text = (chunk.get("text") or "") + " " + (chunk.get("parent_text") or "")
        if not _entity_in_text(cand.get("head_entity", ""), text):
            reasons.append("head_not_traceable")
        if not _entity_in_text(cand.get("tail_entity", ""), text):
            reasons.append("tail_not_traceable")
        pp = chunk.get("prescription_permission", "explanation_only")
        if pp in ("write_core", "prescription_direct"):
            reasons.append(f"prescription_permission_elevated:{pp}")

    if cand.get("relation", "") not in ALLOWED_RELATIONS:
        reasons.append(f"relation_not_in_whitelist:{cand.get('relation')}")

    if float(cand.get("confidence_score", 0.0)) < 0.8:
        reasons.append(f"low_confidence:{cand.get('confidence_score')}")

    return len(reasons) == 0, reasons


def _load_all_chunks() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    all_chunks: list[dict[str, Any]] = []
    by_id: dict[str, Any] = {}
    for shard in SHARD_NAMES:
        chunks_file = V2_SHARDED_DIR / shard / "chunks.jsonl"
        if not chunks_file.exists():
            continue
        with open(chunks_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                chunk = json.loads(line)
                all_chunks.append(chunk)
                cid = chunk.get("chunk_id", "")
                if cid:
                    by_id[cid] = chunk
    return all_chunks, by_id


def _load_existing_candidate_ids() -> set[str]:
    if not CANDIDATES_PATH.exists():
        return set()
    ids: set[str] = set()
    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    ids.add(json.loads(line).get("candidate_id", ""))
                except json.JSONDecodeError:
                    pass
    return ids


async def run_extraction(
    *,
    domain_filter: str = "",
    max_per_domain: int = DEFAULT_MAX_PER_DOMAIN,
    target_nodes: int = DEFAULT_TARGET_NODES,
    dry_run: bool = False,
) -> dict[str, Any]:
    print("加载 v2_sharded chunks...")
    all_chunks, by_id = _load_all_chunks()
    print(f"  共 {len(all_chunks):,} 条 chunks")

    existing_ids = _load_existing_candidate_ids()
    print(f"  已有候选记录: {len(existing_ids)} 条（去重用）")

    domains = sorted(set(c.get("domain_pack", "") for c in all_chunks if c.get("domain_pack")))
    if domain_filter:
        if domain_filter not in domains:
            print(f"域 '{domain_filter}' 不存在，可用: {domains}")
            return {"error": f"unknown domain: {domain_filter}"}
        domains = [domain_filter]

    print(f"目标领域: {domains}")
    print(f"每域上限: {max_per_domain}")
    print(f"目标节点数: {target_nodes}")
    print(f"模式: {'dry-run' if dry_run else '正式抽取'}\n")

    all_new_candidates: list[dict[str, Any]] = []
    domain_stats: dict[str, Any] = {}

    for domain in domains:
        sampled = _sample_chunks(all_chunks, domain, max_per_domain)
        print(f"[{domain}] 采样 {len(sampled)} 个 chunk")

        domain_candidates: list[dict[str, Any]] = []

        for i, chunk in enumerate(sampled):
            chunk_id = chunk.get("chunk_id", "?")
            preview = str(chunk.get("text", ""))[:60].replace("\n", " ")
            preview = preview.encode("ascii", errors="replace").decode("ascii")
            print(f"  [{i+1}/{len(sampled)}] {chunk_id[:40]} | {preview}...", end=" ", flush=True)

            if dry_run:
                print("(dry-run)")
                continue

            try:
                text = str(chunk.get("text", ""))
                if len(text) < 60:
                    print("skip:short")
                    continue

                prompt = f"领域: {domain}\n文本:\n{text[:800]}"
                raw = await _ollama_chat(prompt, EXTRACTION_SYSTEM_PROMPT)

                start = raw.find("[")
                end = raw.rfind("]") + 1
                triples = json.loads(raw[start:end]) if 0 <= start < end else []

                added = 0
                for triple in triples:
                    if not isinstance(triple, dict):
                        continue
                    errs = _validate_triple(triple, text)
                    if errs:
                        continue

                    head = str(triple.get("head_entity") or triple.get("head") or "").strip()
                    tail = str(triple.get("tail_entity") or triple.get("tail") or "").strip()
                    relation = _normalize_relation(str(triple.get("relation", "")))
                    if not relation:
                        continue

                    cand_id = _build_candidate_id(chunk_id, head, relation, tail)
                    if cand_id in existing_ids:
                        continue

                    cand: dict[str, Any] = {
                        "candidate_id": cand_id,
                        "source_chunk_id": chunk_id,
                        "source_registry_id": chunk.get("source_registry_id", ""),
                        "source_file": chunk.get("source_file", ""),
                        "page": chunk.get("page"),
                        "expert_domain": domain,
                        "evidence_domain": f"{domain}_reference",
                        "head_entity": head,
                        "relation": relation,
                        "tail_entity": tail,
                        "confidence_score": float(triple.get("confidence", 0.5)),
                        "extraction_method": "llm_offline",
                        "extraction_model": OLLAMA_MODEL,
                        "evidence_span": text[:300],
                        "review_status": "candidate",
                        "review_reasons": [],
                        "merge_approved": False,
                        "merge_status": "pending",
                    }

                    approved, reasons = _auto_approve(cand, by_id)
                    cand["merge_approved"] = approved
                    cand["review_reasons"] = reasons
                    cand["review_status"] = "auto_approved" if approved else "rejected"
                    if not approved:
                        cand["merge_status"] = "rejected"

                    domain_candidates.append(cand)
                    existing_ids.add(cand_id)
                    added += 1

                print(f"+{added} triples")
            except Exception as exc:
                print(f"ERR: {exc}")

            if (i + 1) % 10 == 0:
                await asyncio.sleep(0.5)

        approved_count = sum(1 for c in domain_candidates if c["merge_approved"])
        domain_stats[domain] = {
            "sampled": len(sampled),
            "candidates": len(domain_candidates),
            "auto_approved": approved_count,
        }
        all_new_candidates.extend(domain_candidates)
        print(f"[{domain}] 完成: {len(domain_candidates)} 条候选（{approved_count} 条通过审核）\n")

    print(f"总计新增候选: {len(all_new_candidates)}")
    approved_total = sum(1 for c in all_new_candidates if c["merge_approved"])
    print(f"自动通过: {approved_total}")

    if dry_run:
        print("[dry-run] 未写入文件。")
    elif all_new_candidates:
        CANDIDATES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CANDIDATES_PATH, "a", encoding="utf-8") as f:
            for rec in all_new_candidates:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"写入: {CANDIDATES_PATH}")

    return {
        "total_new": len(all_new_candidates),
        "auto_approved": approved_total,
        "domain_stats": domain_stats,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="从 v2_sharded 抽取 KG 候选三元组")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--domain", type=str, default="")
    parser.add_argument("--max-per-domain", type=int, default=DEFAULT_MAX_PER_DOMAIN)
    parser.add_argument("--target-nodes", type=int, default=DEFAULT_TARGET_NODES)
    args = parser.parse_args()

    asyncio.run(
        run_extraction(
            domain_filter=args.domain,
            max_per_domain=args.max_per_domain,
            target_nodes=args.target_nodes,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
