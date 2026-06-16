"""Sync curated sport-psychology evidence chunks into the local KB.

The chunks are explanatory references for the psychologist role. They are
explicitly blocked from writing training prescriptions.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[1]
V2_CHUNKS = ROOT / "data" / "vector_kb" / "v2" / "chunks.jsonl"
SHARD_BASE = ROOT / "data" / "vector_kb" / "v2_sharded"
PSYCH_SHARD = SHARD_BASE / "sport_psychology" / "chunks.jsonl"
SHARD_META = SHARD_BASE / "shard_meta.json"


COMMON = {
    "domain_terms": ["sport_psychology"],
    "evidence_domain": "sport_psychology",
    "expert_domain": "sport_psychology",
    "domain_pack": "psychological_skills",
    "knowledge_layer": "document_index",
    "allowed_use": "explanation",
    "prescription_permission": "explanation_only",
    "exclude_from_training_generation": True,
    "display_mode": "verified_source",
    "evidence_source_type": "retrieval_evidence",
    "can_write_core": False,
    "explanation_only": True,
    "review_status": "approved",
    "needs_review": False,
    "language": "en",
    "section": "curated_summary",
    "has_full_text": True,
    "source_status": "ready",
}


CURATED_CHUNKS: List[Dict[str, Any]] = [
    {
        **COMMON,
        "chunk_id": "sport_psychology_psych_interventions_meta_2024_0001",
        "source_registry_id": "src_sport_psychology_psych_interventions_meta_2024",
        "source_file": "psychological_interventions_sport_performance_meta_2024.url",
        "source_path": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10933186/",
        "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10933186/",
        "source_label": "Psychological interventions for sports performance systematic review and meta-analysis",
        "quality_tier": "systematic_review_meta_analysis",
        "page": 1,
        "paragraph_index": 1,
        "keywords_en": ["sport psychology", "psychological intervention", "performance", "mental skills"],
        "text": (
            "Psychological interventions for sport performance should be treated as explanatory mental-skills support. "
            "The review evidence supports using structured psychological techniques to influence performance-related "
            "outcomes, but these techniques do not authorize changes to running volume, intensity, injury decisions, "
            "or nutrition prescriptions. Use for confidence, attention, coping, and preparation notes only."
        ),
    },
    {
        **COMMON,
        "chunk_id": "sport_psychology_self_talk_imagery_goal_setting_2024_0002",
        "source_registry_id": "src_sport_psychology_psych_interventions_meta_2024",
        "source_file": "psychological_interventions_sport_performance_meta_2024.url",
        "source_path": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10933186/",
        "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10933186/",
        "source_label": "Psychological interventions for sports performance systematic review and meta-analysis",
        "quality_tier": "systematic_review_meta_analysis",
        "page": 1,
        "paragraph_index": 2,
        "keywords_en": ["self-talk", "imagery", "goal setting", "mental skills", "visualization"],
        "text": (
            "Common mental-skills categories in sport psychology include self-talk, imagery or visualization, goal setting, "
            "relaxation or arousal regulation, and attentional strategies. In a marathon assistant these can be surfaced "
            "as brief coping scripts, process-goal reminders, or race-preparation prompts, while remaining separate from "
            "planner and executor training prescriptions."
        ),
    },
    {
        **COMMON,
        "chunk_id": "sport_psychology_ioc_mental_health_boundary_2019_0003",
        "source_registry_id": "src_ioc_mental_health_elite_athletes_2019",
        "source_file": "ioc_consensus_mental_health_elite_athletes_2019.url",
        "source_path": "https://bjsm.bmj.com/content/53/11/667",
        "source_url": "https://bjsm.bmj.com/content/53/11/667",
        "source_label": "IOC consensus statement on mental health in elite athletes",
        "quality_tier": "consensus_statement",
        "page": 1,
        "paragraph_index": 1,
        "keywords_en": ["mental health", "athlete", "clinical boundary", "referral", "psychology"],
        "text": (
            "The IOC consensus statement frames athlete mental health as a clinical and safeguarding domain when symptoms "
            "are persistent, severe, or impairing. The psychologist role in this system must not diagnose anxiety, depression, "
            "or other clinical states; it should provide non-clinical sport psychology references and recommend professional "
            "mental-health support when distress is ongoing or outside training-preparation scope."
        ),
    },
    {
        **COMMON,
        "chunk_id": "sport_psychology_goal_setting_oxford_2019_0004",
        "source_registry_id": "src_goal_setting_sport_performance_oxford_2019",
        "source_file": "goal_setting_sport_performance_oxford_2019.url",
        "source_path": "https://oxfordre.com/psychology/display/10.1093/acrefore/9780190236557.001.0001/acrefore-9780190236557-e-152",
        "source_url": "https://oxfordre.com/psychology/display/10.1093/acrefore/9780190236557.001.0001/acrefore-9780190236557-e-152",
        "source_label": "Goal Setting and Performance in Sport and Exercise Settings",
        "quality_tier": "expert_review",
        "page": 1,
        "paragraph_index": 1,
        "keywords_en": ["goal setting", "process goals", "performance goals", "motivation"],
        "text": (
            "Goal-setting literature in sport and exercise distinguishes outcome, performance, and process goals. For running "
            "plans, the psychology role should favor process goals and controllable execution cues because they support adherence "
            "and focus without altering the training prescription generated by planner and executor."
        ),
    },
]


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _upsert(existing: List[Dict[str, Any]], new_rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id = {str(row.get("chunk_id") or ""): row for row in existing}
    order = [str(row.get("chunk_id") or "") for row in existing]
    for row in new_rows:
        chunk_id = str(row.get("chunk_id") or "")
        if not chunk_id:
            continue
        if chunk_id not in by_id:
            order.append(chunk_id)
        by_id[chunk_id] = row
    return [by_id[chunk_id] for chunk_id in order if chunk_id in by_id]


def _update_shard_meta() -> None:
    meta: Dict[str, Any] = {}
    if SHARD_META.exists():
        meta = json.loads(SHARD_META.read_text(encoding="utf-8"))
    shards = dict(meta.get("shards") or {})
    shards["sport_psychology"] = len(_load_jsonl(PSYCH_SHARD))
    meta["shards"] = shards
    meta["total_chunks"] = sum(int(value or 0) for value in shards.values())
    SHARD_META.parent.mkdir(parents=True, exist_ok=True)
    SHARD_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    master_rows = _upsert(_load_jsonl(V2_CHUNKS), CURATED_CHUNKS)
    shard_rows = _upsert(_load_jsonl(PSYCH_SHARD), CURATED_CHUNKS)
    _write_jsonl(V2_CHUNKS, master_rows)
    _write_jsonl(PSYCH_SHARD, shard_rows)
    _update_shard_meta()
    print(f"synced sport psychology chunks: {len(CURATED_CHUNKS)}")
    print(f"master chunks: {len(master_rows)}")
    print(f"sport_psychology shard chunks: {len(shard_rows)}")


if __name__ == "__main__":
    main()
