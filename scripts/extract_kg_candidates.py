"""
从领域已标注 chunk 批量抽取候选知识图谱三元组。

用法:
  python scripts/extract_kg_candidates.py [--domain nutrition] [--max-per-domain 50] [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

# 项目路径
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "backend" / "src"))

from marathon_qa_assistant.services.kb.kg_extraction import (
    extract_triples_from_chunk,
    load_candidate_queue,
    queue_stats,
    save_candidates,
)

CHUNKS_PATH = ROOT / "data" / "vector_kb" / "v2" / "chunks.jsonl"
QUEUE_PATH = ROOT / "data" / "knowledge" / "governance" / "kg_candidate_triples.jsonl"

# 每域默认抽取上限
DEFAULT_MAX_PER_DOMAIN = 50

# 优先抽取的域顺序
DOMAIN_PRIORITY = [
    "nutrition",
    "rehab_safety",
    "training_theory",
    "race_strategy",
    "workout_prescription",
    "capacity_management",
]


def _load_chunks(path: str | Path) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    return chunks


def _is_not_reference(chunk: Dict[str, Any]) -> bool:
    """过滤参考文献条目：含 PMID/DOI、数字编号开头、多分号作者列表。"""
    text = str(chunk.get("text", ""))
    if re.match(r'^\d{1,4}\.\s+[A-Z]', text.strip()):
        return False
    if 'PMID:' in text or 'doi:' in text or 'doi.org' in text:
        return False
    if text.count(';') > 5:
        return False
    if text.strip().lower().startswith(('review', 'open access', 'abstract', 'received:')):
        return False
    return True


def _is_substantive(text: str) -> bool:
    """检查文本是否包含实质性运动科学内容（非日历、表格、纯数字、训练日志）。"""
    t = text.strip()
    if len(t) < 80:
        return False
    # 纯训练日志：日期 + 配速 + 距离 + 心率 的组合
    log_patterns = [
        r'^\d{1,2}/\d{1,2}[\s/]',          # 日期行: "5/15 rest" / "06/01 配速跑"
        r'^\d{1,2}\.\d{1,2}\s',              # "5.15 easy run"
        r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun|周一|周二|周三|周四|周五|周六|周日)',
        r'^\d{1,2}:\d{2}[\s-]',             # 时间行: "6:00 晨跑"
        r'^\d{1,2}[kK]\s',                   # "10k easy run"
    ]
    for pat in log_patterns:
        if re.match(pat, t):
            # 如果带实质性说明（>200 字），仍可能有用
            if len(t) < 200:
                return False
    # 纯数字/符号占比 > 60%
    alpha_ratio = sum(1 for c in t if c.isalpha()) / max(len(t), 1)
    if alpha_ratio < 0.35:
        return False
    # 重复模式：同一短语出现 > 8 次（表格数据特征）
    words = t.lower().split()
    if len(words) > 20:
        from collections import Counter as _C
        top = _C(words).most_common(1)[0][1]
        if top > 8 and top / len(words) > 0.3:
            return False
    # 没有主谓结构的短列表/元数据
    sentences = [s for s in re.split(r'[.!?\n]{1,2}', t) if len(s.strip()) > 10]
    if len(sentences) < 2:
        return False
    return True


def _sample_chunks(chunks: List[Dict[str, Any]], domain: str, max_n: int) -> List[Dict[str, Any]]:
    """从指定领域采样高质量 chunk：过滤参考文献+非实质性内容，优先正文长段落。"""
    domain_chunks = [c for c in chunks if c.get("expert_domain") == domain]
    # 两道过滤
    body_chunks = [c for c in domain_chunks if _is_not_reference(c)]
    body_chunks = [c for c in body_chunks if _is_substantive(str(c.get("text", "")))]
    if not body_chunks:
        body_chunks = [c for c in domain_chunks if _is_not_reference(c)]
    # 排序：正文标注优先，有页码优先，文本长度优先
    def _quality_key(c: Dict[str, Any]) -> tuple:
        text = str(c.get("text", ""))
        text_len = len(text)
        has_page = 1 if c.get("page") else 0
        is_body = 1 if str(c.get("section", "")) in ("document_paragraph", "pdf_paragraph_candidate") else 0
        length_bonus = 1 if 300 < text_len < 1500 else 0
        return (is_body, has_page, length_bonus, text_len)
    body_chunks.sort(key=_quality_key, reverse=True)
    # 按源文件分散采样：每源至少 3 个，优先正文（跳过标题页），避免 CPG 挤占全部名额
    by_source: dict = {}
    for c in body_chunks:
        sf = str(c.get("source_file", ""))
        by_source.setdefault(sf, []).append(c)
    sampled = []
    for sf, clist in by_source.items():
        # 优先取 page > 2 的 chunk（跳过标题/作者/版权页）
        body_pages = [c for c in clist if int(c.get("page", 1)) > 2]
        picks = body_pages[:3] if body_pages else clist[:3]
        sampled.extend(picks)
    # 第二轮：从剩余中按质量补满
    already = {c["chunk_id"] for c in sampled}
    for c in body_chunks:
        if len(sampled) >= max_n:
            break
        if c["chunk_id"] not in already:
            sampled.append(c)
            already.add(c["chunk_id"])
    return sampled[:max_n]


async def _ollama_chat(prompt: str, system: str, model: str = "qwen2.5:latest") -> str:
    """通过 Ollama 调用 LLM。"""
    import aiohttp
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 512},
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            data = await resp.json()
            return data.get("response", "")


async def run_extraction(
    chunks_path: str | Path,
    queue_path: str | Path,
    *,
    domain_filter: str = "",
    max_per_domain: int = DEFAULT_MAX_PER_DOMAIN,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """执行批量三元组抽取。"""
    chunks = _load_chunks(chunks_path)
    domains = sorted(set(c.get("expert_domain", "?") for c in chunks))

    if domain_filter:
        if domain_filter not in domains:
            print(f"域 '{domain_filter}' 不存在，可用域: {domains}")
            return {"error": f"unknown domain: {domain_filter}"}
        domains = [domain_filter]

    # 按优先级排序
    domains.sort(key=lambda d: DOMAIN_PRIORITY.index(d) if d in DOMAIN_PRIORITY else 99)

    print(f"chunk 总数: {len(chunks)}")
    print(f"目标领域: {domains}")
    print(f"每域上限: {max_per_domain}")
    print(f"模式: {'dry-run (不写入)' if dry_run else '正式抽取'}")
    print()

    all_candidates: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {"domains": {}}

    for domain in domains:
        sampled = _sample_chunks(chunks, domain, max_per_domain)
        print(f"[{domain}] 采样 {len(sampled)} 个 chunk, 开始抽取...")

        domain_candidates: List[Dict[str, Any]] = []
        for i, chunk in enumerate(sampled):
            text_preview = str(chunk.get("text", ""))[:80].replace("\n", " ")
            text_preview = text_preview.encode("ascii", errors="replace").decode("ascii")
            print(f"  [{i+1}/{len(sampled)}] {chunk.get('chunk_id','?')[:40]} | {text_preview}...", end=" ", flush=True)

            if dry_run:
                print("(dry-run skip)")
                continue

            try:
                triples = await extract_triples_from_chunk(chunk, _ollama_chat)
                if triples:
                    print(f"+{len(triples)} triples")
                    domain_candidates.extend(triples)
                else:
                    print("0 triples")
            except Exception as exc:
                print(f"ERR: {exc}")

            # 每 10 个 chunk 休息一下
            if (i + 1) % 10 == 0:
                await asyncio.sleep(0.5)

        stats["domains"][domain] = {
            "sampled": len(sampled),
            "candidates": len(domain_candidates),
        }
        all_candidates.extend(domain_candidates)
        print(f"[{domain}] 完成: {len(domain_candidates)} 条候选三元组\n")

    if not dry_run and all_candidates:
        new_count = save_candidates(all_candidates, queue_path)
        print(f"写入队列: {new_count} 条新增 (总候选: {len(load_candidate_queue(queue_path))})")
    elif dry_run:
        print(f"[dry-run] 共抽取 {len(all_candidates)} 条候选三元组，未写入")

    stats["total_candidates"] = len(all_candidates)
    return stats


def main():
    parser = argparse.ArgumentParser(description="从标注 chunk 抽取 KG 候选三元组")
    parser.add_argument("--domain", type=str, default="", help="限定领域 (nutrition/rehab_safety/...)")
    parser.add_argument("--max-per-domain", type=int, default=DEFAULT_MAX_PER_DOMAIN)
    parser.add_argument("--dry-run", action="store_true", help="不写入队列，仅预览")
    parser.add_argument("--stats", action="store_true", help="仅显示当前队列统计")
    args = parser.parse_args()

    if args.stats:
        s = queue_stats(QUEUE_PATH)
        print(f"队列统计: {s['total']} 条")
        print(f"  状态: {s['by_status']}")
        print(f"  领域: {s['by_expert_domain']}")
        print(f"  关系: {s['by_relation']}")
        return

    result = asyncio.run(
        run_extraction(
            CHUNKS_PATH,
            QUEUE_PATH,
            domain_filter=args.domain,
            max_per_domain=args.max_per_domain,
            dry_run=args.dry_run,
        )
    )
    print(f"\n总候选: {result.get('total_candidates', 0)}")


if __name__ == "__main__":
    main()
