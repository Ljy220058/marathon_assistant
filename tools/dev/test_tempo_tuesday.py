import sys
from pathlib import Path

def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (candidate / ".git").exists() and (candidate / "apps").exists():
            return candidate
    return Path.cwd().resolve()


PROJECT_ROOT = _find_project_root()
project_root = PROJECT_ROOT
sys.path.insert(0, str(project_root))
backend_src = project_root / "apps" / "backend" / "src"
if backend_src.exists():
    sys.path.insert(0, str(backend_src))

from marathon_qa_assistant.services.workout_template_retriever import (
    build_daily_workout_template_card_from_hits,
    normalize_workout_type_for_template,
)
from marathon_qa_assistant.ui.report_ui import UIHelper
from marathon_qa_assistant.nodes.output_nodes import _build_structured_report

def main():
    # ============ 模拟证据：知识库里关于 节奏跑 的文本 ============
    hits = [
        {
            "source_file": "动作库.pdf",
            "page": 8,
            "chunk_id": "动作库_p0008_c0003",
            "score": 0.91,
            "text": """
【节奏跑（乳酸阈值训练）】
name：节奏跑（Tempo Run）
categories： Tempo, Threshold, Steady-State
content：
a. 20分钟阈值跑（Z4）
b. 3×8min/Z4，组间慢跑3min
c. 25分钟持续Z4配速
d. 2×12min，Z4渐进到Z5
objective：在Z4区间提升乳酸阈值附近的持续输出能力，稳定专项节奏
热身：15分钟慢跑+动态拉伸+马克操+3.2km加速跑
""",
        },
        {
            "source_file": "动作库.pdf",
            "page": 8,
            "chunk_id": "动作库_p0008_c0004",
            "score": 0.85,
            "text": """
节奏跑补充说明：配速应控制在"可说话但费力"的强度；若恢复状态不佳可缩短至15分钟。
cooldown：10分钟慢跑+静态拉伸
""",
        },
    ]

    # ============ 步骤1：类型识别 ============
    training_type = "节奏跑"
    main_set = "25分钟阈值"
    workout_type = normalize_workout_type_for_template(training_type, main_set)
    print(f"[类型识别] training_type='{training_type}', main_set='{main_set}'")
    print(f"  → workout_type = '{workout_type}'")
    print()

    # ============ 步骤2：构建每日课表卡 ============
    card = build_daily_workout_template_card_from_hits(
        workout_type=workout_type,
        day="周二",
        hits=hits,
    )
    print(f"[课表卡]")
    print(f"  title           = {card['title']}")
    print(f"  workout_type     = {card['workout_type']}")
    print(f"  training_type    = {card['training_type']}")
    print(f"  source           = {card['source']}")
    print(f"  main_set_candidates = {card['main_set_candidates']}")
    print(f"  intensity_target = {card['intensity_target']!r}")
    print(f"  training_objective = {card['training_objective'][:60]}...")
    print(f"  warmup_suggestion= {card['warmup_suggestion'][:60]}...")
    print(f"  evidence_status  = {card['evidence_status']}")
    print()

    # ============ 步骤3：构造最小 structured_report 并走 UI 渲染 ============
    structured_training_plan = {
        "plan_meta": {
            "requested_weeks": 1,
            "actual_weeks": 1,
            "goal": "半马训练",
            "experience_level": "进阶",
            "plan_type": "multi_week",
            "render_version": "v1",
        },
        "week_plans": [
            {
                "week_index": 1,
                "phase": "基础期",
                "week_goal": "建立有氧基础与乳酸阈值",
                "load_level": "medium",
                "days": [
                    {
                        "day": "周二",
                        "training_type": training_type,
                        "warmup": "慢跑15分钟+动态拉伸",
                        "main_set": main_set,
                        "cooldown": "慢跑10分钟+拉伸",
                        "venue": "田径场",
                    },
                ],
            }
        ],
    }

    evidence_base = []
    for i, h in enumerate(hits, start=1):
        evidence_base.append({
            "id": i,
            "document": h["source_file"],
            "source": h["source_file"],
            "source_path": h["source_file"],
            "pages": [h["page"]],
            "text": h["text"],
            "chunk_id": h["chunk_id"],
            "score": h["score"],
        })

    report = _build_structured_report(
        {
            "query": "请为我生成周二节奏跑课表",
            "category": "coach",
            "mode": "team",
            "audit_scores": {"consistency": 85, "safety": 90, "roi": 75},
            "rag_sources": [
                {"source": "动作库.pdf", "source_file": "动作库.pdf", "page": 8,
                 "chunk_id": "动作库_p0008_c0003", "score": 0.91, "text": hits[0]["text"]},
                {"source": "动作库.pdf", "source_file": "动作库.pdf", "page": 8,
                 "chunk_id": "动作库_p0008_c0004", "score": 0.85, "text": hits[1]["text"]},
            ],
            "structured_training_plan": structured_training_plan,
        },
        "已生成周二节奏跑训练课表。",
    )

    rendered = UIHelper.render_structured_report(report, "已生成周二节奏跑训练课表。")

    print("=" * 60)
    print("============ 最终 UI 渲染输出 ============")
    print("=" * 60)
    print(rendered)
    print("=" * 60)
    print()

    # ============ 确认关键内容 ============
    assert "周二｜节奏跑训练课" in rendered, "标题缺失"
    assert "节奏跑（乳酸阈值训练）" in rendered, "训练类型标签缺失"
    assert "Z4" in rendered, "强度目标缺失"
    assert "乳酸阈值" in rendered, "训练目标关键词缺失"
    assert "📌 每日课表卡" in rendered, "每日课表卡区块缺失"
    print("✅ 所有关键断言通过！")


if __name__ == "__main__":
    main()
