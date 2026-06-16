"""
回填 chunks.jsonl 的 evidence_domain 和 expert_domain 字段。
基于 source_file 文件名关键词推断领域，不改动其他字段。
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict

# 扩展关键词映射 — 覆盖所有已知来源文件命名模式
SOURCE_KEYWORD_TO_EVIDENCE_DOMAIN: list[tuple[list[str], str]] = [
    (["nutrition", "fuel", "hydration", "electrolyte", "diet", "carb", "protein",
      "supplement", "creatine", "caffeine", "nitrate", "beetroot", "issn_nutrient",
      "acsm_nutrition", "world_athletics", "distance_runners", "ultramarathon",
      "marathon_running"], "nutrition_race_fueling"),
    (["injury", "rehab", "return_to_run", "pain", "pfps", "achilles", "plantar",
      "overuse", "tibial", "bsi", "msk", "overtraining", "safety_injury",
      "risk_factor", "acwr", "gabbett"], "medical_safety"),
    (["train", "physiology", "strength", "running_economy", "tid", "polarized",
      "threshold", "seiler", "stoggl", "middle_distance",
      "marathon_physiology", "app_data", "best_practice", "periodization",
      "world_class", "jhse"], "protocol"),
    # 赛前策略（减量、配速、比赛日）
    (["taper", "tapering", "pacing", "race_strategy", "race_day", "competition",
      "heat", "weather", "altitude", "environment", "temperature"],
     "environment_race_context"),
    (["competitor", "product", "shoe", "watch", "device", "nike", "garmin"],
     "competitor_product_reference"),
    (["profile", "user_case", "runner_case"], "user_profile_case"),
    (["action", "drill", "exercise", "workout", "strength_training"],
     "action_library"),
]

# evidence_domain → expert_domain 映射
EVIDENCE_TO_EXPERT: Dict[str, str] = {
    "protocol": "training_theory",
    "action_library": "workout_prescription",
    "sports_science_reference": "training_theory",
    "medical_safety": "rehab_safety",
    "rehab_strength_mobility": "rehab_safety",
    "nutrition_race_fueling": "nutrition",
    "environment_race_context": "race_strategy",
    "competitor_product_reference": "training_theory",
    "user_profile_case": "training_theory",
    "llm_general_knowledge": "training_theory",
}

# 兼容旧枚举值
LEGACY_TO_EVIDENCE: Dict[str, str] = {
    "nutrition": "nutrition_race_fueling",
    "race_fueling": "nutrition_race_fueling",
    "hydration": "nutrition_race_fueling",
    "medical_risk": "medical_safety",
    "injury": "medical_safety",
    "rehabilitation": "rehab_strength_mobility",
    "recovery": "rehab_strength_mobility",
    "training": "protocol",
    "training_protocols": "protocol",
    "workout": "action_library",
    "environment": "environment_race_context",
}


def _infer_evidence_domain(source_file: str, existing_domain: str = "") -> str:
    """从 source_file 文件名推断 evidence_domain。"""
    # 优先使用已有有效值
    if existing_domain and existing_domain not in ("?", "", "unknown"):
        norm = LEGACY_TO_EVIDENCE.get(existing_domain.lower(), existing_domain.lower())
        # 验证是否是合法枚举值
        valid = {v for _, v in SOURCE_KEYWORD_TO_EVIDENCE_DOMAIN}
        valid.update(LEGACY_TO_EVIDENCE.values())
        valid.update(EVIDENCE_TO_EXPERT.keys())
        if norm in valid:
            return norm

    lowered = source_file.lower()
    for keywords, domain in SOURCE_KEYWORD_TO_EVIDENCE_DOMAIN:
        if any(kw in lowered for kw in keywords):
            return domain
    return "sports_science_reference"


def _infer_expert_domain_short(evidence_domain: str) -> str:
    """从 evidence_domain 推断 expert_domain。"""
    return EVIDENCE_TO_EXPERT.get(evidence_domain, "training_theory")


def backfill_chunks(chunks_path: str | Path, backup: bool = True) -> dict:
    """回填 chunks 的领域字段，返回统计信息。"""
    chunks_path = Path(chunks_path)
    if backup:
        backup_path = chunks_path.with_suffix(".jsonl.bak")
        import shutil
        shutil.copy2(chunks_path, backup_path)
        print(f"已备份至 {backup_path}")

    chunks: list[Dict[str, Any]] = []
    with open(chunks_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))

    stats = Counter()
    domain_stats: Counter = Counter()

    for chunk in chunks:
        source_file = str(chunk.get("source_file", ""))
        existing_ed = str(chunk.get("evidence_domain", ""))
        existing_xd = str(chunk.get("expert_domain", ""))

        # 推断 evidence_domain
        new_ed = _infer_evidence_domain(source_file, existing_ed)
        if new_ed != (existing_ed if existing_ed not in ("?", "") else new_ed):
            stats["evidence_domain_changed"] += 1
        chunk["evidence_domain"] = new_ed
        domain_stats[new_ed] += 1

        # 推断 expert_domain
        new_xd = _infer_expert_domain_short(new_ed)
        if new_xd != (existing_xd if existing_xd not in ("?", "") else new_xd):
            stats["expert_domain_changed"] += 1
        chunk["expert_domain"] = new_xd

        # 确保 knowledge_layer 有值
        if not chunk.get("knowledge_layer") or chunk["knowledge_layer"] in ("?", ""):
            has_full = chunk.get("section") in ("document_paragraph", "pdf_paragraph_candidate")
            chunk["knowledge_layer"] = "document_index" if has_full else "source_registry"

    # 写回
    with open(chunks_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    stats["total_chunks"] = len(chunks)
    print(f"回填完成: {len(chunks)} chunks")
    print(f"evidence_domain 变更: {stats.get('evidence_domain_changed', 0)}")
    print(f"expert_domain 变更: {stats.get('expert_domain_changed', 0)}")
    print(f"\n证据域分布:")
    for domain, count in domain_stats.most_common():
        print(f"  {domain}: {count}")
    return dict(stats)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/vector_kb/v2/chunks.jsonl"
    backfill_chunks(path)
