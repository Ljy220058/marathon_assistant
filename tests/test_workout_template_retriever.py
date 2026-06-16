from marathon_qa_assistant.core.training_plan_skeleton import build_structured_training_plan_skeleton
from marathon_qa_assistant.nodes.output_nodes import _build_structured_report
from marathon_qa_assistant.services.workout_template_retriever import (
    WORKOUT_TEMPLATE_REGISTRY,
    WORKOUT_TYPE_KEYWORD_MAP,
    build_daily_workout_template_card_from_hits,
    build_workout_template_query,
    get_action_library_foundation_hits,
    normalize_workout_type_for_template,
)
from marathon_qa_assistant.ui.report_ui import UIHelper


def test_build_workout_template_query_expands_aerobic_threshold_aliases():
    query = build_workout_template_query("aerobic_threshold")

    assert "有氧阈值训练" in query
    assert "最大脂肪氧化训练" in query
    assert "3-4*3000" in query
    assert "动作库.pdf" in query


def test_build_daily_workout_template_card_from_action_library_hits():
    hits = [
        {
            "source_file": "动作库.pdf",
            "page": 6,
            "chunk_id": "动作库_p0006_c0001",
            "score": 0.9,
            "text": """
            【Aerobic Endurance（有氧耐力）】
            2. name：有氧阈值训练（最大脂肪氧化训练）
            categories： Aerobic , Steady-State , Endurance
            content：
            a. 3-4*3000/2min
            b. 5-6*2000/2min
            c. 3*3000+3+2000(配速比3000快10s)
            d. 上下坡交替跑15km
            """,
        },
        {
            "source_file": "动作库.pdf",
            "page": 7,
            "chunk_id": "动作库_p0007_c0001",
            "score": 0.88,
            "text": """
            e. 5000+3*2000
            f. （3min有氧阈+2min慢跑+2min有氧阈+1min慢跑）*6
            objective：在75–85%HRmax区间提升脂代谢效率与有氧耐力，提升最大脂肪氧化率
            """,
        },
        {
            "source_file": "动作库.pdf",
            "page": 3,
            "chunk_id": "动作库_p0003_c0003",
            "score": 0.7,
            "text": """
            5. 热身
            categories：激活，有氧
            content：15分钟慢跑+动态拉伸+马克操+3.2-4.8km加速跑（有氧跑加速到有氧阈值上限）
            """,
        },
    ]

    card = build_daily_workout_template_card_from_hits("aerobic_threshold", day="周二", hits=hits)

    assert card["title"] == "周二｜有氧阈值训练课"
    assert card["training_type"] == "有氧阈值训练（最大脂肪氧化训练）"
    assert "动作库.pdf，第 6 页" in card["source"]
    assert len(card["main_set_candidates"]) >= 4
    assert card["intensity_target"] == "Z3-Z4 稳态有氧区至有氧阈值区"
    assert "最大脂肪氧化率" in card["training_objective"]
    assert "15分钟慢跑" in card["warmup_suggestion"]
    assert card["evidence_status"]["main_set_candidates"] == "direct"
    assert card["evidence_status"]["cooldown"] == "missing"


def test_action_library_card_rejects_warmup_drill_hit_as_core_main_set():
    hits = [
        {
            "source_file": "动作库.pdf",
            "page": 2,
            "chunk_id": "warmup_drill",
            "score": 0.95,
            "text": """
            Long Run support drill
            categories: Technique, Drills, Warm-up
            content:
            a. A Skip running drill
            b. High knees running drill
            """,
            "tags": {"categories": "Technique, Drills, Warm-up"},
            "source_authority": "C",
        },
        {
            "source_file": "动作库.pdf",
            "page": 12,
            "chunk_id": "long_run_prescription",
            "score": 0.9,
            "text": """
            Long Run
            categories: Long-Run, Endurance, Marathon-Spec
            content:
            a. 21-25km
            b. 21-25km last 3-4km at marathon pace
            objective: aerobic endurance and marathon-specific fatigue resistance
            """,
            "tags": {"categories": "Long-Run, Endurance, Marathon-Spec"},
            "source_authority": "A",
        },
        {
            "source_file": "动作库.pdf",
            "page": 10,
            "chunk_id": "aerobic_threshold_not_long_run",
            "score": 0.88,
            "text": """
            Long Run adjacent aerobic threshold
            categories: Aerobic, Steady-State, Endurance
            content:
            a. 3-4*3000/2min
            """,
            "tags": {"categories": "Aerobic, Steady-State, Endurance"},
            "source_authority": "B",
        },
    ]

    card = build_daily_workout_template_card_from_hits("long_run", day="Sun", hits=hits)

    assert card["evidence_tier"] == "action_library"
    assert card["evidence"][0]["chunk_id"] == "long_run_prescription"
    assert any("21-25km" in item for item in card["main_set_candidates"])
    assert not any("Skip" in item for item in card["main_set_candidates"])


def test_long_run_jsonl_foundation_prefers_long_run_prescription_chunk():
    hits = get_action_library_foundation_hits("long_run")

    card = build_daily_workout_template_card_from_hits("long_run", day="Sun", hits=hits)

    assert card["evidence_tier"] == "action_library"
    assert card["evidence"][0]["chunk_id"] == "动作库_p0012_c0001"
    assert card["main_set_candidates"][0].startswith("21")


def test_workout_template_card_exposes_layered_kb_metadata():
    card = build_daily_workout_template_card_from_hits(
        "easy_run",
        day="周三",
        hits=[
            {
                "source_file": "动作库.pdf",
                "page": 4,
                "chunk_id": "动作库_p0004_c0001",
                "score": 0.91,
                "text": """
                【轻松跑】
                name：轻松跑
                content：30-60分钟 Z1-Z2 轻松跑
                objective：促进恢复并维持有氧基础
                热身：10分钟慢跑+动态活动
                """,
            }
        ],
    )

    assert card["kb_metadata"]["knowledge_layer"] == "prescription_library"
    assert card["kb_metadata"]["evidence_domain"] == "action_library"
    assert card["kb_metadata"]["prescription_permission"] == "can_write_core"
    assert card["kb_metadata"]["retrieval_mode"] == "action_library"
    assert card["kb_metadata"]["source_registry_id"].startswith("src_")


def test_build_daily_workout_template_card_does_not_fabricate_when_evidence_missing():
    card = build_daily_workout_template_card_from_hits(
        "aerobic_threshold",
        day="周二",
        hits=[
            {
                "source_file": "其他.pdf",
                "page": 1,
                "chunk_id": "other_c1",
                "score": 0.6,
                "text": "普通轻松跑建议。",
            }
        ],
    )

    assert card["title"] == "周二｜课表证据不足"
    assert card["main_set_candidates"] == []
    assert card["training_objective"] == ""
    assert card["evidence_status"]["main_set_candidates"] == "missing"
    assert "未检索到动作库" in card["evidence_status"]["reason"]


def test_structured_report_exposes_and_renders_daily_workout_cards():
    report = _build_structured_report(
        {
            "query": "给我生成一周训练计划",
            "category": "coach",
            "mode": "team",
            "audit_scores": {"consistency": 90, "safety": 95, "roi": 80},
            "rag_sources": [
                {
                    "source": "动作库.pdf",
                    "source_file": "动作库.pdf",
                    "page": 6,
                    "chunk_id": "动作库_p0006_c0001",
                    "score": 0.9,
                    "text": """
                    2. name：有氧阈值训练（最大脂肪氧化训练）
                    content：a. 3-4*3000/2min b. 5-6*2000/2min
                    objective：在75–85%HRmax区间提升脂代谢效率与有氧耐力，提升最大脂肪氧化率
                    """,
                },
                {
                    "source": "动作库.pdf",
                    "source_file": "动作库.pdf",
                    "page": 3,
                    "chunk_id": "动作库_p0003_c0003",
                    "score": 0.7,
                    "text": "content：15分钟慢跑+动态拉伸+马克操+3.2-4.8km加速跑（有氧跑加速到有氧阈值上限）",
                },
            ],
            "structured_training_plan": {
                "plan_meta": {
                    "requested_weeks": 1,
                    "actual_weeks": 1,
                    "goal": "半马训练",
                    "experience_level": "进阶",
                    "target_race_date": "4周后",
                    "plan_type": "multi_week",
                    "render_version": "v1",
                },
                "week_plans": [
                    {
                        "week_index": 1,
                        "phase": "基础期",
                        "week_goal": "建立有氧基础",
                        "load_level": "medium",
                        "days": [
                            {
                                "day": "周二",
                                "training_type": "有氧阈值训练",
                                "warmup": "慢跑15分钟",
                                "main_set": "有氧阈值主课",
                                "cooldown": "慢跑10分钟",
                                "venue": "田径场",
                            }
                        ],
                    }
                ],
            },
        },
        "已生成训练计划。",
    )

    cards = report["daily_workout_cards"]
    assert len(cards) == 1
    assert cards[0]["title"] == "周二｜有氧阈值训练课"
    assert cards[0]["week_index"] == 1
    assert cards[0]["evidence_tier"] == "action_library"
    assert cards[0]["evidence_status"]["main_set_candidates"] == "direct"

    rendered = UIHelper.render_structured_report(report, "已生成训练计划。")
    assert "#### 📌 每日课表卡" in rendered
    assert "周二｜有氧阈值训练课" in rendered
    assert "动作库.pdf，第 6 页" in rendered
    assert "冷身、替代训练还需要补充课表库" in rendered


def test_normalize_workout_type_for_all_registered_types():
    test_cases = [
        ("有氧阈值训练", "有氧阈值主课", "aerobic_threshold"),
        ("长距离", "120分钟稳定跑", "long_run"),
        ("轻松跑", "40分钟低强度", "easy_run"),
        ("恢复跑", "30分钟恢复", "easy_run"),
        ("节奏跑", "25分钟阈值", "tempo_run"),
        ("摄氧量训练", "5×3分钟摄氧量间歇", "vo2max_interval"),
        ("最大摄氧量", "VO2max", "vo2max_interval"),
        ("间歇跑", "5×800m", "interval_run"),
        ("间歇", "6×400m", "interval_run"),
        ("无氧阈跑", "3×1600m", "anaerobic_threshold"),
        ("无氧阈", "巡航间歇", "anaerobic_threshold"),
        ("马拉松配速跑", "2×15分钟", "marathon_pace"),
        ("马拉松配速", "专项配速", "marathon_pace"),
        ("渐进跑", "渐进加速", "progression_run"),
        ("休息", "休息日", ""),
        ("未知类型", "未知课表", ""),
    ]
    for training_type, main_set, expected_key in test_cases:
        result = normalize_workout_type_for_template(training_type, main_set)
        assert result == expected_key, f"{training_type}/{main_set} → expected {expected_key!r}, got {result!r}"



def test_single_day_daily_workout_card_matrix_for_all_training_types():
    test_cases = [
        {
            "training_type": "节奏跑",
            "main_set": "25分钟阈值",
            "expected_key": "tempo_run",
            "day": "周二",
            "expected_title": "周二｜节奏跑训练课",
            "expected_label": "节奏跑（乳酸阈值训练）",
            "expected_intensity": "Z4 有氧阈值区",
            "expected_objective_keyword": "乳酸阈值",
            "hit": {
                "source_file": "动作库.pdf",
                "page": 8,
                "chunk_id": "动作库_p0008_c0003",
                "score": 0.91,
                "text": """
                【节奏跑（乳酸阈值训练）】
                name：节奏跑（Tempo Run）
                content：
                a. 20分钟阈值跑（Z4）
                b. 3×8min/Z4，组间慢跑3min
                c. 25分钟持续Z4配速
                objective：在Z4区间提升乳酸阈值附近的持续输出能力
                热身：15分钟慢跑+动态拉伸
                """,
            },
        },
        {
            "training_type": "长距离",
            "main_set": "120分钟长距离",
            "expected_key": "long_run",
            "day": "周日",
            "expected_title": "周日｜长距离训练课",
            "expected_label": "长距离训练",
            "expected_intensity": "Z2-Z3 轻松有氧区至稳态有氧区",
            "expected_objective_keyword": "有氧耐力",
            "hit": {
                "source_file": "动作库.pdf",
                "page": 10,
                "chunk_id": "动作库_p0010_c0005",
                "score": 0.92,
                "text": """
                【长距离训练】
                name：长距离（有氧耐力跑）
                content：
                a. 90分钟稳定有氧跑（Z2-Z3）
                b. 120分钟长距离+补给练习
                c. 3×20分钟稳定有氧
                objective：在Z2-Z3区间提升有氧耐力与脂肪代谢能力
                热身：20分钟慢跑+动态拉伸
                """,
            },
        },
        {
            "training_type": "轻松跑",
            "main_set": "40分钟低强度",
            "expected_key": "easy_run",
            "day": "周三",
            "expected_title": "周三｜轻松跑训练课",
            "expected_label": "轻松跑",
            "expected_intensity": "Z1-Z2 恢复放松区至轻松有氧区",
            "expected_objective_keyword": "恢复",
            "hit": {
                "source_file": "动作库.pdf",
                "page": 15,
                "chunk_id": "动作库_p0015_c0002",
                "score": 0.85,
                "text": """
                【轻松跑】
                name：轻松跑（Easy Run）
                content：
                a. 30分钟Z1轻松跑
                b. 45分钟Z2轻松连续跑
                c. 恢复跑20分钟
                objective：在Z1-Z2区间促进恢复，保持有氧容量
                热身：10分钟慢跑+动态拉伸
                """,
            },
        },
        {
            "training_type": "摄氧量训练",
            "main_set": "5×3分钟摄氧量间歇",
            "expected_key": "vo2max_interval",
            "day": "周四",
            "expected_title": "周四｜摄氧量训练课",
            "expected_label": "摄氧量训练（最大摄氧量间歇）",
            "expected_intensity": "Z6-Z7 乳酸阈值区至高强度耐受区",
            "expected_objective_keyword": "最大摄氧量",
            "hit": {
                "source_file": "动作库.pdf",
                "page": 18,
                "chunk_id": "动作库_p0018_c0001",
                "score": 0.9,
                "text": """
                【摄氧量训练】
                name：摄氧量训练（VO2max Interval）
                content：
                a. 5×3分钟/Z6-Z7，组间慢跑3min
                b. 6×2分钟最大摄氧量间歇，组间慢跑2min
                c. 4×4分钟摄氧量训练
                objective：在Z6-Z7区间提升最大摄氧量与高强度有氧输出能力
                热身：15分钟慢跑+动态拉伸+加速跑
                """,
            },
        },
        {
            "training_type": "间歇跑",
            "main_set": "5×800m间歇",
            "expected_key": "interval_run",
            "day": "周四",
            "expected_title": "周四｜间歇训练课",
            "expected_label": "间歇跑（高强度间歇训练）",
            "expected_intensity": "Z5-Z6 马拉松专项区至乳酸阈值区",
            "expected_objective_keyword": "速度耐力",
            "hit": {
                "source_file": "动作库.pdf",
                "page": 12,
                "chunk_id": "动作库_p0012_c0004",
                "score": 0.9,
                "text": """
                【间歇训练】
                name：间歇跑（Interval）
                content：
                a. 4×800m/Z5，组间慢跑2min
                b. 6×400m/Z6，组间慢跑90s
                c. 3×1000m/200m慢跑
                objective：在Z5-Z6区间提升速度耐力与最大摄氧量
                热身：15分钟慢跑+动态拉伸+加速跑
                """,
            },
        },
        {
            "training_type": "无氧阈跑",
            "main_set": "巡航间歇",
            "expected_key": "anaerobic_threshold",
            "day": "周五",
            "expected_title": "周五｜无氧阈训练课",
            "expected_label": "无氧阈跑（巡航间歇训练）",
            "expected_intensity": "Z4-Z5 有氧阈值区至马拉松专项区",
            "expected_objective_keyword": "无氧",
            "hit": {
                "source_file": "动作库.pdf",
                "page": 13,
                "chunk_id": "动作库_p0013_c0002",
                "score": 0.88,
                "text": """
                【无氧阈跑】
                name：无氧阈跑（巡航间歇训练）
                content：
                a. 3×1600m/Z4，组间慢跑2min
                b. 4×1200m/Z5，组间慢跑2min
                c. 巡航间歇20分钟
                objective：在Z4-Z5区间提升无氧阈附近的稳定输出能力
                热身：15分钟慢跑+动态拉伸
                """,
            },
        },
        {
            "training_type": "马拉松配速跑",
            "main_set": "专项配速",
            "expected_key": "marathon_pace",
            "day": "周六",
            "expected_title": "周六｜马拉松配速训练课",
            "expected_label": "马拉松配速跑（专项配速训练）",
            "expected_intensity": "Z4-Z5 比赛配速区（100% HMP），配合 85-90% HMP 巡航恢复",
            "expected_objective_keyword": "配速",
            "hit": {
                "source_file": "动作库.pdf",
                "page": 14,
                "chunk_id": "动作库_p0014_c0001",
                "score": 0.87,
                "text": """
                【马拉松配速跑】
                name：马拉松配速跑（Marathon Pace）
                content：
                a. 2×15分钟Z3-Z4专项配速
                b. 40分钟马拉松配速跑
                c. 3×5km配速跑
                objective：在Z3-Z4区间稳定目标马拉松配速控制能力
                热身：15分钟慢跑+动态拉伸
                """,
            },
        },
        {
            "training_type": "渐进跑",
            "main_set": "渐进加速",
            "expected_key": "progression_run",
            "day": "周一",
            "expected_title": "周一｜渐进跑训练课",
            "expected_label": "渐进跑",
            "expected_intensity": "Z1→Z4 恢复放松区渐进至有氧阈值区",
            "expected_objective_keyword": "渐进",
            "hit": {
                "source_file": "动作库.pdf",
                "page": 16,
                "chunk_id": "动作库_p0016_c0001",
                "score": 0.84,
                "text": """
                【渐进跑】
                name：渐进跑（Progression Run）
                content：
                a. 45分钟从Z1渐进到Z4
                b. 60分钟后半程渐加速
                c. 3×10分钟渐进跑
                objective：通过渐进加速提升配速控制与后程输出能力
                热身：10分钟慢跑+动态拉伸
                """,
            },
        },
        {
            "training_type": "有氧阈值训练",
            "main_set": "有氧阈值主课",
            "expected_key": "aerobic_threshold",
            "day": "周二",
            "expected_title": "周二｜有氧阈值训练课",
            "expected_label": "有氧阈值训练（最大脂肪氧化训练）",
            "expected_intensity": "Z3-Z4 稳态有氧区至有氧阈值区",
            "expected_objective_keyword": "最大脂肪氧化",
            "hit": {
                "source_file": "动作库.pdf",
                "page": 6,
                "chunk_id": "动作库_p0006_c0001",
                "score": 0.9,
                "text": """
                【Aerobic Endurance（有氧耐力）】
                name：有氧阈值训练（最大脂肪氧化训练）
                content：
                a. 3-4*3000/2min
                b. 5-6*2000/2min
                c. 5000+3*2000
                objective：在75–85%HRmax区间提升脂代谢效率与有氧耐力，提升最大脂肪氧化率
                热身：15分钟慢跑+动态拉伸+马克操+3.2-4.8km加速跑（有氧跑加速到有氧阈值上限）
                """,
            },
        },
    ]
    for case in test_cases:
        workout_type = normalize_workout_type_for_template(case["training_type"], case["main_set"])
        assert workout_type == case["expected_key"]

        card = build_daily_workout_template_card_from_hits(workout_type, day=case["day"], hits=[case["hit"]])

        assert card["title"] == case["expected_title"]
        assert card["workout_type"] == case["expected_key"]
        assert card["training_type"] == case["expected_label"]
        assert card["source"]
        assert card["main_set_candidates"]
        assert card["intensity_target"] == case["expected_intensity"]
        assert case["expected_objective_keyword"] in card["training_objective"]
        assert card["warmup_suggestion"]
        assert card["evidence_status"]["main_set_candidates"] == "direct"
        assert card["evidence_status"]["intensity_target"] == "direct"
        assert card["evidence_status"]["training_objective"] == "direct"
        assert card["evidence_status"]["warmup_suggestion"] == "direct"



def test_registry_covers_all_keyword_map_entries():
    for key in WORKOUT_TYPE_KEYWORD_MAP:
        assert key in WORKOUT_TEMPLATE_REGISTRY, f"KEYWORD_MAP 中的 {key} 不在 REGISTRY 中"


def test_build_daily_workout_template_card_for_long_run():
    hits = [
        {
            "source_file": "动作库.pdf",
            "page": 10,
            "chunk_id": "动作库_p0010_c0005",
            "score": 0.92,
            "text": """
            【长距离训练】
            name：长距离（有氧耐力跑）
            content：a. 90分钟稳定有氧跑 b. 120分钟长距离+补给练习 c. 3×20分钟渐进
            objective：在Z2-Z3区间提升有氧耐力与脂肪代谢能力
            热身：20分钟慢跑+动态拉伸+4.8km加速跑
            """,
        },
    ]

    card = build_daily_workout_template_card_from_hits("long_run", day="周日", hits=hits)

    assert card["title"] == "周日｜长距离训练课"
    assert card["workout_type"] == "long_run"
    assert card["training_type"] == "长距离训练"
    assert len(card["main_set_candidates"]) >= 1
    assert card["evidence_status"]["main_set_candidates"] == "direct"
    assert "有氧耐力" in card["training_objective"]


def test_build_daily_workout_template_card_for_easy_run():
    hits = [
        {
            "source_file": "动作库.pdf",
            "page": 15,
            "chunk_id": "动作库_p0015_c0002",
            "score": 0.85,
            "text": """
            【轻松跑】
            name：轻松跑（Easy Run）
            content：a. 30分钟Z1轻松跑 b. 45分钟低强度连续跑 c. 恢复跑20分钟
            objective：在Z1-Z2区间促进恢复，保持有氧容量
            """,
        },
    ]

    card = build_daily_workout_template_card_from_hits("easy_run", day="周四", hits=hits)

    assert card["title"] == "周四｜轻松跑训练课"
    assert card["workout_type"] == "easy_run"
    assert card["training_type"] == "轻松跑"
    assert len(card["main_set_candidates"]) >= 1
    assert card["evidence_status"]["main_set_candidates"] == "direct"


def test_build_daily_workout_template_card_for_interval_run():
    hits = [
        {
            "source_file": "动作库.pdf",
            "page": 12,
            "chunk_id": "动作库_p0012_c0004",
            "score": 0.9,
            "text": """
            【间歇训练】
            name：间歇跑（Interval）
            content：a. 4×800m/2min慢跑 b. 6×400m/90s慢跑 c. 3×1000m/200m慢跑
            objective：在Z5区间提升速度耐力与最大摄氧量
            """,
        },
    ]

    card = build_daily_workout_template_card_from_hits("interval_run", day="周二", hits=hits)

    assert card["title"] == "周二｜间歇训练课"
    assert card["workout_type"] == "interval_run"
    assert len(card["main_set_candidates"]) >= 1
    assert card["evidence_status"]["main_set_candidates"] == "direct"


def test_build_daily_workout_template_card_for_unknown_type():
    card = build_daily_workout_template_card_from_hits("unknown_type", day="周一", hits=[])

    assert "证据不足" in card["title"]
    assert "未找到该训练类型" in card["evidence_status"]["reason"]


def test_structured_report_exposes_multi_type_daily_cards():
    report = _build_structured_report(
        {
            "query": "生成一周训练计划",
            "category": "coach",
            "mode": "team",
            "audit_scores": {"consistency": 85, "safety": 90, "roi": 75},
            "rag_sources": [
                {
                    "source": "动作库.pdf",
                    "source_file": "动作库.pdf",
                    "page": 6,
                    "chunk_id": "动作库_p0006_c0001",
                    "score": 0.92,
                    "text": """name：有氧阈值训练（最大脂肪氧化训练）
content：3-4*3000/2min 5-6*2000/2min
objective：在75–85%HRmax区间提升脂代谢效率与有氧耐力，提升最大脂肪氧化率""",
                },
                {
                    "source": "动作库.pdf",
                    "source_file": "动作库.pdf",
                    "page": 10,
                    "chunk_id": "动作库_p0010_c0005",
                    "score": 0.88,
                    "text": """name：长距离（有氧耐力跑）
content：90分钟稳定有氧跑 120分钟长距离+补给练习""",
                },
                {
                    "source": "动作库.pdf",
                    "source_file": "动作库.pdf",
                    "page": 8,
                    "chunk_id": "动作库_p0008_c0003",
                    "score": 0.85,
                    "text": """name：间歇跑（Interval）
content：4×800m/2min慢跑 6×400m/90s慢跑""",
                },
            ],
            "structured_training_plan": {
                "plan_meta": {
                    "requested_weeks": 1,
                    "actual_weeks": 1,
                    "goal": "半马训练",
                    "experience_level": "进阶",
                    "target_race_date": "4周后",
                    "plan_type": "multi_week",
                    "render_version": "v1",
                },
                "week_plans": [
                    {
                        "week_index": 1,
                        "phase": "基础期",
                        "week_goal": "建立有氧基础",
                        "load_level": "medium",
                        "days": [
                            {
                                "day": "周二",
                                "training_type": "有氧阈值训练",
                                "warmup": "慢跑15分钟",
                                "main_set": "有氧阈值主课",
                                "cooldown": "慢跑10分钟",
                                "venue": "田径场",
                            },
                            {
                                "day": "周四",
                                "training_type": "间歇跑",
                                "warmup": "慢跑10分钟",
                                "main_set": "5×800m间歇",
                                "cooldown": "慢跑10分钟",
                                "venue": "田径场",
                            },
                            {
                                "day": "周日",
                                "training_type": "长距离",
                                "warmup": "慢跑15分钟",
                                "main_set": "90分钟长距离",
                                "cooldown": "慢跑10分钟",
                                "venue": "公路",
                            },
                            {
                                "day": "周三",
                                "training_type": "轻松跑",
                                "warmup": "慢跑10分钟",
                                "main_set": "40分钟轻松",
                                "cooldown": "拉伸",
                                "venue": "公园",
                            },
                            {
                                "day": "周一",
                                "training_type": "休息",
                                "warmup": "无",
                                "main_set": "休息",
                                "cooldown": "无",
                                "venue": "居家",
                            },
                        ],
                    }
                ],
            },
        },
        "已生成训练计划。",
    )

    cards = report["daily_workout_cards"]
    assert len(cards) >= 3, f"期望至少3张课表卡（有氧阈、间歇、长距离），实际 {len(cards)}"

    card_types = [c["workout_type"] for c in cards]
    assert "aerobic_threshold" in card_types
    assert "interval_run" in card_types
    assert "long_run" in card_types

    rendered = UIHelper.render_structured_report(report, "已生成训练计划。")
    assert "#### 📌 每日课表卡" in rendered
    assert "有氧阈值训练课" in rendered
    assert "间歇训练课" in rendered
    assert "长距离训练课" in rendered



def test_structured_report_renders_daily_cards_for_all_training_types():
    cases = [
        {
            "day": "周一",
            "training_type": "渐进跑",
            "main_set": "渐进加速",
            "expected_key": "progression_run",
            "expected_title": "周一｜渐进跑训练课",
            "text": """
            【渐进跑】
            name：渐进跑（Progression Run）
            content：
            a. 45分钟从Z1渐进到Z4
            b. 60分钟后半程渐加速
            objective：通过渐进加速提升配速控制与后程输出能力
            热身：10分钟慢跑+动态拉伸
            """,
        },
        {
            "day": "周二",
            "training_type": "有氧阈值训练",
            "main_set": "有氧阈值主课",
            "expected_key": "aerobic_threshold",
            "expected_title": "周二｜有氧阈值训练课",
            "text": """
            【Aerobic Endurance（有氧耐力）】
            name：有氧阈值训练（最大脂肪氧化训练）
            content：
            a. 3-4*3000/2min
            b. 5-6*2000/2min
            c. 5000+3*2000
            objective：在75–85%HRmax区间提升脂代谢效率与有氧耐力，提升最大脂肪氧化率
            热身：15分钟慢跑+动态拉伸+马克操+3.2-4.8km加速跑（有氧跑加速到有氧阈值上限）
            """,
        },
        {
            "day": "周三",
            "training_type": "轻松跑",
            "main_set": "40分钟低强度",
            "expected_key": "easy_run",
            "expected_title": "周三｜轻松跑训练课",
            "text": """
            【轻松跑】
            name：轻松跑（Easy Run）
            content：
            a. 30分钟Z1轻松跑
            b. 45分钟Z2轻松连续跑
            objective：在Z1-Z2区间促进恢复，保持有氧容量
            热身：10分钟慢跑+动态拉伸
            """,
        },
        {
            "day": "周四",
            "training_type": "摄氧量训练",
            "main_set": "5×3分钟摄氧量间歇",
            "expected_key": "vo2max_interval",
            "expected_title": "周四｜摄氧量训练课",
            "text": """
            【摄氧量训练】
            name：摄氧量训练（VO2max Interval）
            content：
            a. 5×3分钟/Z6-Z7，组间慢跑3min
            b. 6×2分钟最大摄氧量间歇，组间慢跑2min
            objective：在Z6-Z7区间提升最大摄氧量与高强度有氧输出能力
            热身：15分钟慢跑+动态拉伸+加速跑
            """,
        },
        {
            "day": "周四",
            "training_type": "间歇跑",
            "main_set": "5×800m间歇",
            "expected_key": "interval_run",
            "expected_title": "周四｜间歇训练课",
            "text": """
            【间歇训练】
            name：间歇跑（Interval）
            content：
            a. 4×800m/Z5，组间慢跑2min
            b. 6×400m/Z6，组间慢跑90s
            objective：在Z5-Z6区间提升速度耐力与最大摄氧量
            热身：15分钟慢跑+动态拉伸+加速跑
            """,
        },
        {
            "day": "周五",
            "training_type": "无氧阈跑",
            "main_set": "巡航间歇",
            "expected_key": "anaerobic_threshold",
            "expected_title": "周五｜无氧阈训练课",
            "text": """
            【无氧阈跑】
            name：无氧阈跑（巡航间歇训练）
            content：
            a. 3×1600m/Z4，组间慢跑2min
            b. 4×1200m/Z5，组间慢跑2min
            objective：在Z4-Z5区间提升无氧阈附近的稳定输出能力
            热身：15分钟慢跑+动态拉伸
            """,
        },
        {
            "day": "周六",
            "training_type": "马拉松配速跑",
            "main_set": "专项配速",
            "expected_key": "marathon_pace",
            "expected_title": "周六｜马拉松配速训练课",
            "text": """
            【马拉松配速跑】
            name：马拉松配速跑（Marathon Pace）
            content：
            a. 2×15分钟Z3-Z4专项配速
            b. 40分钟马拉松配速跑
            objective：在Z3-Z4区间稳定目标马拉松配速控制能力
            热身：15分钟慢跑+动态拉伸
            """,
        },
        {
            "day": "周日",
            "training_type": "长距离",
            "main_set": "120分钟长距离",
            "expected_key": "long_run",
            "expected_title": "周日｜长距离训练课",
            "text": """
            【长距离训练】
            name：长距离（有氧耐力跑）
            content：
            a. 90分钟稳定有氧跑（Z2-Z3）
            b. 120分钟长距离+补给练习
            objective：在Z2-Z3区间提升有氧耐力与脂肪代谢能力
            热身：20分钟慢跑+动态拉伸
            """,
        },
        {
            "day": "周八",
            "training_type": "节奏跑",
            "main_set": "25分钟阈值",
            "expected_key": "tempo_run",
            "expected_title": "周八｜节奏跑训练课",
            "text": """
            【节奏跑（乳酸阈值训练）】
            name：节奏跑（Tempo Run）
            content：
            a. 20分钟阈值跑（Z4）
            b. 25分钟持续Z4配速
            objective：在Z4区间提升乳酸阈值附近的持续输出能力
            热身：15分钟慢跑+动态拉伸
            """,
        },
    ]

    rag_sources = [
        {
            "source": "动作库.pdf",
            "source_file": "动作库.pdf",
            "page": index,
            "chunk_id": f"动作库_all_types_{case['expected_key']}",
            "score": 0.9,
            "text": case["text"],
        }
        for index, case in enumerate(cases, start=1)
    ]
    days = [
        {
            "day": case["day"],
            "training_type": case["training_type"],
            "warmup": "慢跑10分钟+动态拉伸",
            "main_set": case["main_set"],
            "cooldown": "慢跑10分钟+拉伸",
            "venue": "田径场",
        }
        for case in cases
    ]

    report = _build_structured_report(
        {
            "query": "生成覆盖全部训练类型的一周训练计划",
            "category": "coach",
            "mode": "team",
            "audit_scores": {"consistency": 85, "safety": 90, "roi": 75},
            "rag_sources": rag_sources,
            "structured_training_plan": {
                "plan_meta": {
                    "requested_weeks": 1,
                    "actual_weeks": 1,
                    "goal": "全类型课表卡验证",
                    "experience_level": "进阶",
                    "plan_type": "multi_week",
                    "render_version": "v1",
                },
                "week_plans": [
                    {
                        "week_index": 1,
                        "phase": "验证期",
                        "week_goal": "覆盖全部训练类型",
                        "load_level": "medium",
                        "days": days,
                    }
                ],
            },
        },
        "已生成覆盖全部训练类型的训练计划。",
    )

    cards = report["daily_workout_cards"]
    assert len(cards) == len(cases)

    card_by_type = {card["workout_type"]: card for card in cards}
    assert set(card_by_type) == {case["expected_key"] for case in cases}
    for case in cases:
        assert card_by_type[case["expected_key"]]["title"] == case["expected_title"]

    rendered = UIHelper.render_structured_report(report, "已生成覆盖全部训练类型的训练计划。")
    assert "#### 📌 每日课表卡" in rendered
    for case in cases:
        card = card_by_type[case["expected_key"]]
        if card["source"]:
            assert case["expected_title"] in rendered
        else:
            assert card["evidence_status"].get("reason") in rendered


def test_personalized_week_structure_constraints_are_applied_and_rendered():
    plan = build_structured_training_plan_skeleton(
        "这周我想要安排一节有氧阈，一节节奏跑一节摄氧量",
        {
            "goal": "半马训练",
            "experience_level": "进阶",
            "available_days": ["周二", "周四", "周六", "周日"],
        },
        requested_weeks=1,
    )

    constraints = plan["weekly_structure_constraints"]
    validation = plan["weekly_structure_validation"]
    required_types = {item["workout_type"] for item in constraints["required_workouts"]}

    assert {"aerobic_threshold", "tempo_run", "vo2max_interval"}.issubset(required_types)
    assert validation["status"] == "satisfied"
    assert not validation["violations"]

    days = plan["week_plans"][0]["days"]
    normalized_types = {
        normalize_workout_type_for_template(day["training_type"], day["main_set"])
        for day in days
    }
    assert "aerobic_threshold" in normalized_types
    assert "tempo_run" in normalized_types
    assert "vo2max_interval" in normalized_types

    report = _build_structured_report(
        {
            "query": "这周我想要安排一节有氧阈，一节节奏跑一节摄氧量",
            "category": "coach",
            "mode": "team",
            "audit_scores": {"consistency": 85, "safety": 90, "roi": 75},
            "rag_sources": [],
            "structured_training_plan": plan,
        },
        "已生成个性化周结构训练计划。",
    )
    rendered = UIHelper.render_structured_report(report, "已生成个性化周结构训练计划。")

    assert "#### 🧩 个性化周结构要求" in rendered
    assert "#### ✅ 周结构满足情况" in rendered
    assert "有氧阈值训练" in rendered
    assert "节奏跑" in rendered
    assert "摄氧量训练" in rendered
    assert "状态：已满足" in rendered


def test_personalized_week_structure_parses_weekday_bindings_without_count_leakage():
    plan = build_structured_training_plan_skeleton(
        "这周周二节奏跑，周四摄氧量，周日长距离",
        {
            "goal": "全马训练",
            "experience_level": "进阶",
            "available_days": ["周二", "周四", "周日"],
        },
        requested_weeks=1,
    )

    requirements = {
        item["workout_type"]: item
        for item in plan["weekly_structure_constraints"]["required_workouts"]
    }
    validation = plan["weekly_structure_validation"]
    days = {day["day"]: day for day in plan["week_plans"][0]["days"]}

    assert requirements["tempo_run"]["count"] == 1
    assert requirements["tempo_run"]["day"] == "周二"
    assert requirements["vo2max_interval"]["count"] == 1
    assert requirements["vo2max_interval"]["day"] == "周四"
    assert requirements["long_run"]["count"] == 1
    assert requirements["long_run"]["day"] == "周日"
    assert validation["status"] == "satisfied"
    assert not validation["violations"]
    assert normalize_workout_type_for_template(days["周二"]["training_type"], days["周二"]["main_set"]) == "tempo_run"
    assert normalize_workout_type_for_template(days["周四"]["training_type"], days["周四"]["main_set"]) == "vo2max_interval"
    assert normalize_workout_type_for_template(days["周日"]["training_type"], days["周日"]["main_set"]) == "long_run"


def test_personalized_week_structure_isolates_rest_day_segment_from_later_workouts():
    plan = build_structured_training_plan_skeleton(
        "这周周一休息，安排一节马拉松配速跑，一节渐进跑",
        {
            "goal": "全马破四",
            "experience_level": "中级",
            "available_days": ["周二", "周四", "周日"],
        },
        requested_weeks=1,
    )

    requirements = {
        item["workout_type"]: item
        for item in plan["weekly_structure_constraints"]["required_workouts"]
    }
    validation = plan["weekly_structure_validation"]
    days = {day["day"]: day for day in plan["week_plans"][0]["days"]}
    normalized_types = {
        normalize_workout_type_for_template(day["training_type"], day["main_set"])
        for day in days.values()
    }

    assert plan["weekly_structure_constraints"]["required_rest_days"] == ["周一"]
    assert requirements["marathon_pace"]["day"] is None
    assert requirements["progression_run"]["day"] is None
    assert days["周一"]["training_type"] == "休息"
    assert validation["status"] == "satisfied"
    assert not validation["violations"]
    assert "marathon_pace" in normalized_types
    assert "progression_run" in normalized_types



def test_personalized_week_structure_combination_matrix_for_common_user_demands():
    cases = [
        {
            "query": "这周两节轻松跑，一节长距离",
            "profile": {
                "goal": "基础有氧恢复",
                "experience_level": "初级",
                "available_days": ["周二", "周四", "周日"],
            },
            "expected_counts": {"easy_run": 2, "long_run": 1},
            "expected_days": {},
            "forbidden": [],
            "required_rest_days": [],
        },
        {
            "query": "这周不安排间歇跑，安排一节无氧阈跑一节轻松跑",
            "profile": {
                "goal": "半马提升",
                "experience_level": "进阶",
                "available_days": ["周二", "周四", "周日"],
            },
            "expected_counts": {"anaerobic_threshold": 1, "easy_run": 1},
            "expected_days": {},
            "forbidden": ["interval_run"],
            "required_rest_days": [],
        },
        {
            "query": "这周周二有氧阈，周四节奏跑，周六轻松跑，周日长距离",
            "profile": {
                "goal": "半马训练",
                "experience_level": "进阶",
                "available_days": ["周二", "周四", "周六", "周日"],
            },
            "expected_counts": {"aerobic_threshold": 1, "tempo_run": 1, "easy_run": 1, "long_run": 1},
            "expected_days": {
                "aerobic_threshold": "周二",
                "tempo_run": "周四",
                "easy_run": "周六",
                "long_run": "周日",
            },
            "forbidden": [],
            "required_rest_days": [],
        },
    ]

    for case in cases:
        plan = build_structured_training_plan_skeleton(case["query"], case["profile"], requested_weeks=1)
        constraints = plan["weekly_structure_constraints"]
        validation = plan["weekly_structure_validation"]
        requirements = {item["workout_type"]: item for item in constraints["required_workouts"]}
        normalized_types = [
            normalize_workout_type_for_template(day["training_type"], day["main_set"])
            for day in plan["week_plans"][0]["days"]
        ]

        assert validation["status"] == "satisfied", case["query"]
        assert not validation["violations"], case["query"]
        assert constraints["forbidden_workouts"] == case["forbidden"]
        assert constraints["required_rest_days"] == case["required_rest_days"]
        for workout_type, expected_count in case["expected_counts"].items():
            assert requirements[workout_type]["count"] == expected_count, case["query"]
            assert normalized_types.count(workout_type) >= expected_count, case["query"]
        for workout_type, expected_day in case["expected_days"].items():
            assert requirements[workout_type]["day"] == expected_day, case["query"]
