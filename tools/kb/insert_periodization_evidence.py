"""将已有 PDF 文献的核心证据写入 training_protocol KB chunk。"""
import json
import sys
from pathlib import Path

KB_JSONL = Path(__file__).resolve().parents[2] / "data" / "vector_kb" / "v2_sharded" / "training_protocol" / "chunks.jsonl"

CHUNKS = [
    {
        "chunk_id": "kb_seiler_tid_2010_abstract",
        "source_file": "Seiler_2010_TID_Best_Practice.pdf",
        "source_registry_id": "src_seiler_tid_2010",
        "local_path": "data/domain_docs/Seiler_2010_TID_Best_Practice.pdf",
        "page": 1, "paragraph_index": 0, "char_start": 0, "char_end": 1500,
        "text": (
            "【训练强度分布最佳实践（Seiler 2010）】\n"
            "期刊：IJSPP, 2010, 5, 276-291。作者：Stephen Seiler。\n\n"
            "核心发现：\n"
            "1. 耐力运动员每次训练周期中，约80%的训练课处于低强度（≤2mmol/L血乳酸），"
            "约20%为高强度（约90%VO2max间歇训练）。即经典80/20强度分布。\n"
            "2. 对已训练有素的运动员增加HIIT比例的研究，"
            "没有提供令人信服的证据表明更高比例的高强度训练能带来长期成绩提升。\n"
            "3. 以低强度长持续时间训练为主，辅以少量高强度课，"
            "在优化适应性信号和技术掌握方面是可互补的。\n\n"
            "训练应用：基础期每周高强度课不超过1-2次（对应80/20原则）。"
            "建设期可增至每周2次高质量课但总比例不超过20%。极化训练优于纯阈值训练。"
        ),
        "language": "zh",
        "domain_pack": "endurance_training_protocols",
        "evidence_domain": "sports_science_reference",
        "knowledge_layer": "domain_pack",
        "allowed_use": "explanation",
        "prescription_permission": "explanation_only",
        "quality_tier": "systematic_review",
        "needs_review": False,
        "exclude_from_training_generation": False,
        "domain_terms": ["训练强度分布", "极化训练", "80/20", "Seiler", "基础期高强度上限"],
    },
    {
        "chunk_id": "kb_stoggl_polarized_2014_results",
        "source_file": "Stoggl_2014_Polarized_vs_Threshold.pdf",
        "source_registry_id": "src_stoggl_polarized_2014",
        "local_path": "data/domain_docs/Stoggl_2014_Polarized_vs_Threshold.pdf",
        "page": 1, "paragraph_index": 0, "char_start": 0, "char_end": 1800,
        "text": (
            "【极化训练 vs 阈值训练的RCT对照研究（Stoggl & Sperlich 2014）】\n"
            "期刊：Frontiers in Physiology, 2014, 5:73。\n"
            "设计：48名训练有素的跑者/自行车手/铁三运动员，随机分4组，训练9周。\n\n"
            "四组对比：POL（极化训练）、THR（阈值训练）、HIIT（高强度间歇）、HVT（高训练量）。\n\n"
            "核心结果：\n"
            "1. POL组VO2peak增幅最大：+11.7%（P<0.001）\n"
            "2. POL组力竭时间增加+17.4%（P<0.001）\n"
            "3. POL组峰值速度/功率+5.1%（P<0.01）\n"
            "4. 4mmol/L阈值速度：POL +8.1%，HIIT +5.6%\n"
            "5. HVT和THR对其他指标无进一步改善（P>0.05）\n\n"
            "结论：极化训练产生最大的关键指标改善。"
            "业余跑者应采用极化训练模式80%低强度+20%高强度。"
            "不建议大量安排中等阈值强度训练。随机对照试验证据（n=48）。"
        ),
        "language": "zh",
        "domain_pack": "endurance_training_protocols",
        "evidence_domain": "sports_science_reference",
        "knowledge_layer": "domain_pack",
        "allowed_use": "explanation",
        "prescription_permission": "explanation_only",
        "quality_tier": "rct",
        "needs_review": False,
        "exclude_from_training_generation": False,
        "domain_terms": ["极化训练", "阈值训练", "Stoggl", "POL vs THR", "业余跑者强度分配"],
    },
    {
        "chunk_id": "kb_gabbett_acwr_2016_abstract",
        "source_file": "Gabbett_2016_ACWR_Paradox.pdf",
        "source_registry_id": "src_gabbett_acwr_2016",
        "local_path": "data/domain_docs/Gabbett_2016_ACWR_Paradox.pdf",
        "page": 1, "paragraph_index": 0, "char_start": 0, "char_end": 1600,
        "text": (
            "【训练-损伤预防悖论与急慢性负荷比（Gabbett 2016）】\n"
            "期刊：BJSM, 2016。作者：Tim J Gabbett。\n\n"
            "核心发现：\n"
            "1. 长期保持较高训练负荷的运动员比低负荷训练的伤病更少。\n"
            "2. 急慢性负荷比（ACWR）=本周负荷/过去4周均值。安全区间0.8-1.3。\n"
            "3. ACWR>1.5时伤病风险显著增加（2-4倍）。\n"
            "4. 训练负荷快速过度增加是非接触性软组织伤病主因。\n"
            "5. 训练不足同样增加伤病风险。\n\n"
            "训练应用：每周跑量递增不超过10%（与ACWR安全区间一致）。"
            "阶段转换时跑量和强度应阶梯式而非跳跃式变化。"
            "减量期跑量削减至巅峰期41-60%，对应ACWR 0.4-0.6。"
        ),
        "language": "zh",
        "domain_pack": "endurance_training_protocols",
        "evidence_domain": "sports_science_reference",
        "knowledge_layer": "domain_pack",
        "allowed_use": "explanation",
        "prescription_permission": "explanation_only",
        "quality_tier": "systematic_review",
        "needs_review": False,
        "exclude_from_training_generation": False,
        "domain_terms": ["ACWR", "急慢性负荷比", "Gabbett", "跑量递增", "10%规则", "减量幅度"],
    },
]


def main():
    existing = []
    existing_ids = set()
    if KB_JSONL.exists():
        for line in KB_JSONL.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            existing.append(stripped)
            try:
                existing_ids.add(json.loads(stripped).get("chunk_id", ""))
            except json.JSONDecodeError:
                pass

    added = 0
    for chunk in CHUNKS:
        if chunk["chunk_id"] not in existing_ids:
            existing.append(json.dumps(chunk, ensure_ascii=False))
            existing_ids.add(chunk["chunk_id"])
            added += 1
            print(f"  + {chunk['chunk_id']}")

    if added:
        KB_JSONL.write_text("\n".join(existing) + "\n", encoding="utf-8")
        print(f"Done: added {added} chunks, total {len(existing)}")
    else:
        print("All chunks already exist (noop)")


if __name__ == "__main__":
    main()
