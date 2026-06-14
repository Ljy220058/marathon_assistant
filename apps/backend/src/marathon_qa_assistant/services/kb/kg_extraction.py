"""
从领域已标注 chunk 中抽取候选知识图谱三元组，写入审核队列。

流程：
1. 按 expert_domain 分组加载 chunk
2. 用 LLM 从 chunk 文本中抽取 (head, relation, tail) 三元组
3. 规则校验：relation 在白名单、实体可回溯到原文
4. 写入 kg_candidate_triples.jsonl（不直接污染主图）
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("kg_extraction")

# 第一版关系白名单
ALLOWED_RELATIONS = {
    "supports",       # A 支持/促进 B
    "constrains",     # A 约束/限制 B
    "requires",       # A 需要/依赖 B
    "adjusts",        # A 调整/修改 B
    "risks",          # A 增加 B 的风险
    "improves",       # A 改善/提升 B
    "reduces",        # A 减少/降低 B
    "bridges_to",     # 跨领域桥接边
}

# 中文关系名 → 英文规范名
RELATION_ALIASES: Dict[str, str] = {
    "support": "supports", "促进": "supports", "增强": "supports",
    "constrain": "constrains", "限制": "constrains", "约束": "constrains",
    "require": "requires", "需要": "requires", "依赖": "requires",
    "adjust": "adjusts", "调整": "adjusts", "修改": "adjusts",
    "risk": "risks", "增加风险": "risks", "风险": "risks",
    "improve": "improves", "改善": "improves", "提升": "improves",
    "reduce": "reduces", "减少": "reduces", "降低": "reduces",
    "bridge": "bridges_to", "桥接": "bridges_to", "跨域": "bridges_to",
}

EXTRACTION_SYSTEM_PROMPT = """你是运动科学知识图谱三元组抽取器。从给定的运动科学文本片段中提取知识三元组。

每条三元组格式: {head_entity, relation, tail_entity, confidence}

规则：
1. head_entity 和 tail_entity 必须是文本中明确出现的概念、动作、生理指标或训练参数，≤20 字。
2. relation 只能从以下选择：
   - supports (A支持B): A有利于B的发生或增强
   - constrains (A约束B): A是B的限制条件
   - requires (A需要B): A依赖于B才能成立
   - adjusts (A调整B): A会改变B的值或状态
   - risks (A风险B): A会增加B的风险或发生概率
   - improves (A改善B): A能改善B的质量或效果
   - reduces (A减少B): A能减少B的量或程度
   - bridges_to (A桥接B): A和B属于不同领域但存在因果/依赖关系
3. confidence 用 0.0-1.0 表示你对这条三元组的确信程度。
4. 只抽取有明确文本依据的关系，不要猜测。如果文本没有明确的三元组关系，返回空数组。
5. 最多抽取 3 条三元组。

仅返回 JSON 数组，不要任何其他文字。"""


def _normalize_relation(raw: str) -> Optional[str]:
    """将 LLM 输出的关系名归一化到白名单，不合法则返回 None。"""
    key = str(raw or "").strip().lower()
    if key in ALLOWED_RELATIONS:
        return key
    if key in RELATION_ALIASES:
        return RELATION_ALIASES[key]
    return None


def _entity_in_text(entity: str, text: str) -> bool:
    """验证实体能在原文中找到（模糊匹配，允许部分重叠）。"""
    if not entity or not text:
        return False
    entity_clean = entity.strip().lower()
    text_clean = text.lower()
    if entity_clean in text_clean:
        return True
    # 尝试拆分实体为词，逐个检查
    parts = re.split(r"[,，、\s]+", entity_clean)
    parts = [p for p in parts if len(p) >= 2]
    if parts and all(p in text_clean for p in parts):
        return True
    # 允许 80% 以上字符匹配
    if len(entity_clean) >= 3:
        matched = sum(1 for ch in entity_clean if ch in text_clean)
        if matched / len(entity_clean) >= 0.8:
            return True
    return False


def _validate_triple(triple: Dict[str, Any], chunk_text: str) -> List[str]:
    """校验单条三元组，返回错误列表（空列表 = 通过）。"""
    errors: List[str] = []

    head = str(triple.get("head_entity") or triple.get("head") or "").strip()
    tail = str(triple.get("tail_entity") or triple.get("tail") or "").strip()
    relation = str(triple.get("relation") or "").strip()
    confidence = triple.get("confidence", 0.0)

    if not head or len(head) > 60:
        errors.append(f"invalid_head: {head[:40]}")
    if not tail or len(tail) > 60:
        errors.append(f"invalid_tail: {tail[:40]}")
    if head == tail:
        errors.append("self_loop")
    if not _normalize_relation(relation):
        errors.append(f"invalid_relation: {relation}")
    if not _entity_in_text(head, chunk_text):
        errors.append(f"head_not_in_text: {head[:40]}")
    if not _entity_in_text(tail, chunk_text):
        errors.append(f"tail_not_in_text: {tail[:40]}")
    if not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
        errors.append(f"invalid_confidence: {confidence}")

    return errors


def _build_candidate_id(chunk_id: str, head: str, relation: str, tail: str) -> str:
    """为候选三元组生成稳定 ID。"""
    seed = f"{chunk_id}|{head}|{relation}|{tail}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"cand_{digest}"


async def extract_triples_from_chunk(
    chunk: Dict[str, Any],
    llm_call,
    max_retries: int = 2,
) -> List[Dict[str, Any]]:
    """从单个 chunk 抽取候选三元组。llm_call 是异步函数 (prompt, system) -> str。"""
    chunk_id = str(chunk.get("chunk_id", ""))
    text = str(chunk.get("text", ""))
    source_file = str(chunk.get("source_file", ""))
    page = chunk.get("page")
    expert_domain = str(chunk.get("expert_domain", "training_theory"))
    evidence_domain = str(chunk.get("evidence_domain", "sports_science_reference"))
    source_registry_id = str(chunk.get("source_registry_id", ""))

    if len(text) < 60:
        return []  # 太短，跳过

    prompt = f"领域: {expert_domain}\n文本:\n{text[:800]}"
    candidates: List[Dict[str, Any]] = []

    for attempt in range(max_retries + 1):
        try:
            raw = await llm_call(prompt, EXTRACTION_SYSTEM_PROMPT)
            # 解析 JSON
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if 0 <= start < end:
                triples = json.loads(raw[start:end])
            else:
                triples = []

            if not isinstance(triples, list):
                continue

            for triple in triples:
                if not isinstance(triple, dict):
                    continue
                errors = _validate_triple(triple, text)
                if errors:
                    logger.debug(f"triple rejected: {errors}")
                    continue

                head = str(triple.get("head_entity") or triple.get("head") or "").strip()
                tail = str(triple.get("tail_entity") or triple.get("tail") or "").strip()
                relation = _normalize_relation(str(triple.get("relation", "")))

                candidate = {
                    "candidate_id": _build_candidate_id(chunk_id, head, relation, tail),
                    "chunk_id": chunk_id,
                    "source_file": source_file,
                    "source_registry_id": source_registry_id,
                    "page": page,
                    "expert_domain": expert_domain,
                    "evidence_domain": evidence_domain,
                    "head_entity": head,
                    "relation": relation,
                    "tail_entity": tail,
                    "confidence": float(triple.get("confidence", 0.5)),
                    "evidence_span": text[:200],
                    "status": "candidate",  # candidate | validated | rejected | merged
                    "reviewed_by": "",
                    "review_note": "",
                    "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }
                candidates.append(candidate)
            break  # 成功则退出重试
        except Exception as exc:
            logger.warning(f"extraction attempt {attempt + 1} failed: {exc}")
            if attempt == max_retries:
                break

    return candidates


def load_candidate_queue(queue_path: str | Path) -> List[Dict[str, Any]]:
    """加载候选三元组队列。"""
    queue_path = Path(queue_path)
    if not queue_path.exists():
        return []
    candidates: List[Dict[str, Any]] = []
    with open(queue_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                candidates.append(json.loads(line))
    return candidates


def save_candidates(
    candidates: List[Dict[str, Any]],
    queue_path: str | Path,
    *,
    dedup_by: str = "candidate_id",
) -> int:
    """追加候选三元组到队列文件，按 candidate_id 去重。返回新增数量。"""
    queue_path = Path(queue_path)
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    existing_ids: set = set()
    if queue_path.exists():
        with open(queue_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        existing_ids.add(entry.get(dedup_by, ""))
                    except json.JSONDecodeError:
                        pass

    new_count = 0
    with open(queue_path, "a", encoding="utf-8") as f:
        for cand in candidates:
            cid = cand.get(dedup_by, "")
            if cid and cid not in existing_ids:
                f.write(json.dumps(cand, ensure_ascii=False) + "\n")
                existing_ids.add(cid)
                new_count += 1

    return new_count


def queue_stats(queue_path: str | Path) -> Dict[str, Any]:
    """统计候选队列状态。"""
    candidates = load_candidate_queue(queue_path)
    status_counts = Counter(c.get("status", "candidate") for c in candidates)
    domain_counts = Counter(c.get("expert_domain", "?") for c in candidates)
    relation_counts = Counter(c.get("relation", "?") for c in candidates)
    return {
        "total": len(candidates),
        "by_status": dict(status_counts),
        "by_expert_domain": dict(domain_counts),
        "by_relation": dict(relation_counts),
    }


def validate_candidate(
    candidate: Dict[str, Any],
    approved: bool,
    reviewer: str = "",
    note: str = "",
) -> Dict[str, Any]:
    """审核一条候选三元组。返回更新后的记录。"""
    candidate["status"] = "validated" if approved else "rejected"
    candidate["reviewed_by"] = reviewer
    candidate["review_note"] = note
    return candidate
