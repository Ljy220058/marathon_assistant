"""Phase 0b: Auditor 可执行性诊断

评估 auditor targeted_fix 的质量: 具体性、可操作性、证据依据、安全性
DeepSeek v4 评分 1-5，输出分维度统计
"""
import json, sys, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
OUTPUT_DIR = Path(__file__).parent / "ab_results"
OUTPUT_DIR.mkdir(exist_ok=True)

# 20 条 simulated targeted_fix 样本 (覆盖 6 类 failure_mode)
SAMPLES = [
    {"failure_mode": "overtraining_rx", "fix": "将周跑量从 55km 降至 33km，增加 2 天恢复日"},
    {"failure_mode": "overtraining_rx", "fix": "在连续高强度课之间插入恢复日或轻松跑，确保周跑量增幅 ≤10%"},
    {"failure_mode": "overtraining_rx", "fix": "建议修改训练计划"},
    {"failure_mode": "pain_misinterpretation", "fix": "立即就医评估，暂停所有跑步训练直至医生确认安全"},
    {"failure_mode": "pain_misinterpretation", "fix": "任何疼痛信号应先建议就医评估，不得生成「坚持一下」类建议"},
    {"failure_mode": "pain_misinterpretation", "fix": "注意安全"},
    {"failure_mode": "hallucinated_claim", "fix": "删除或替换为有本地证据支持的表述，检查引用编号对应关系"},
    {"failure_mode": "hallucinated_claim", "fix": "将 [5] 引用替换为有效的证据来源"},
    {"failure_mode": "hallucinated_claim", "fix": "修改内容"},
    {"failure_mode": "pacing_overly_aggressive", "fix": "降低配速目标至用户当前能力的 80% 区间，增加渐进过渡周"},
    {"failure_mode": "pacing_overly_aggressive", "fix": "配速有问题"},
    {"failure_mode": "recovery_insufficient", "fix": "每周至少安排 2 天完全休息或主动恢复，长距离跑后安排恢复日"},
    {"failure_mode": "recovery_insufficient", "fix": "建议增加休息"},
    {"failure_mode": "evidence_misapplication", "fix": "为每个处方级建议附加明确的 [n] 证据引用，确保引用链可追溯"},
    {"failure_mode": "evidence_misapplication", "fix": "标注「基于通用知识，非本地证据」"},
    {"failure_mode": "evidence_misapplication", "fix": "需要证据"},
    {"failure_mode": "contraindication_missed", "fix": "检查用户画像中的伤病标记，涉及受伤部位的训练应标注风险"},
    {"failure_mode": "contraindication_missed", "fix": "发现用户有膝盖伤病史，建议删除涉及膝关节的高强度训练"},
    {"failure_mode": "contraindication_missed", "fix": "注意安全"},
    {"failure_mode": "individualization_failure", "fix": "根据用户实际周跑量 30km 重新计算训练量，而非使用默认值 60km"},
]


async def score_fixes() -> list[dict]:
    """Use DeepSeek v4 to score each targeted_fix."""
    from marathon_qa_assistant.nodes.common import ai_invoke

    items = []
    for i, s in enumerate(SAMPLES):
        items.append(f"[{i}] failure_mode={s['failure_mode']} | fix=\"{s['fix']}\"")

    prompt = (
        "You are evaluating the quality of AI-generated training plan audit suggestions.\n"
        "For each fix below, rate it on 4 dimensions (1=worst, 5=best):\n\n"
        "  specificity: Is the fix concrete and specific? (1=vague 'fix it', 5=exact numbers and actions)\n"
        "  actionability: Can an executor directly apply this fix? (1=no clue, 5=step-by-step)\n"
        "  evidence_basis: Is the fix grounded in sports science principles? (1=random guess, 5=clearly evidence-backed)\n"
        "  safety: Will following this fix protect the runner? (1=dangerous, 5=conservatively safe)\n\n"
        + "\n".join(items) +
        "\n\nReturn ONLY a JSON array of objects: [{\"specificity\":4,\"actionability\":3,\"evidence_basis\":4,\"safety\":5}, ...]\n"
        "One object per fix, same order. No other text."
    )

    result, usage = await ai_invoke(prompt, {}, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    text = result.strip()
    start = text.find("[")
    end = text.rfind("]") + 1
    if 0 <= start < end:
        scores = json.loads(text[start:end])
        if isinstance(scores, list):
            for s, score in zip(SAMPLES, scores):
                s["scores"] = score
                s["avg"] = round(sum(score.values()) / 4, 2)

    return SAMPLES


async def main():
    print("Phase 0b: Auditor Targeted Fix Quality")
    print(f"{'='*60}\n")

    print("Scoring 20 targeted_fix samples with DeepSeek v4...")
    results = await score_fixes()

    # Statistics
    all_avgs = [r["avg"] for r in results if "avg" in r]
    overall_avg = sum(all_avgs) / max(len(all_avgs), 1)
    dims = ["specificity", "actionability", "evidence_basis", "safety"]
    dim_avgs = {}
    for dim in dims:
        values = [r["scores"][dim] for r in results if "scores" in r and dim in r["scores"]]
        dim_avgs[dim] = round(sum(values) / max(len(values), 1), 2)

    # By failure_mode
    from collections import defaultdict
    mode_avgs = defaultdict(list)
    for r in results:
        if "avg" in r:
            mode_avgs[r["failure_mode"]].append(r["avg"])
    mode_summary = {m: round(sum(vs) / len(vs), 2) for m, vs in mode_avgs.items()}

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"  Overall avg score:    {overall_avg:.2f}/5")
    for dim, val in dim_avgs.items():
        print(f"    {dim:<20}: {val:.2f}")
    print(f"\n  By failure_mode:")
    for mode, avg in sorted(mode_summary.items(), key=lambda x: -x[1]):
        print(f"    {mode:<30}: {avg:.2f}")

    # Sample good vs bad
    good = [r for r in results if r.get("avg", 0) >= 4.0]
    bad = [r for r in results if r.get("avg", 0) < 2.5]
    if good:
        print(f"\n  Best fixes ({len(good)}):")
        for r in good[:3]:
            print(f"    [{r['avg']}] {r['fix'][:80]}")
    if bad:
        print(f"\n  Worst fixes ({len(bad)}):")
        for r in bad[:3]:
            print(f"    [{r['avg']}] {r['fix'][:80]}")

    decision = "START_P2" if overall_avg < 3.5 else "SKIP_P2"
    print(f"\n  [ACTION] Avg {overall_avg:.2f} {'<' if overall_avg < 3.5 else '>='} 3.5 → {decision}")

    out = {
        "results": results,
        "overall_avg": overall_avg,
        "dim_avgs": dim_avgs,
        "mode_avgs": mode_summary,
        "decision": decision,
    }
    out_file = OUTPUT_DIR / "auditor_diagnosis.json"
    out_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nSaved to {out_file}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
