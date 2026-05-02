import asyncio
import sys
from pathlib import Path


root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from marathon_qa_assistant.nodes.output_nodes import _build_structured_report
from marathon_qa_assistant.nodes.plan_nodes import _build_plan_prompt
from marathon_qa_assistant.nodes.profile_and_retrieval import build_ranked_evidence


def test_build_plan_prompt_contains_week_plan_constraints_and_evidence_rules():
    state = {
        "query": "请帮我安排下周半马训练计划，训练日固定周二周四周日。",
        "graph_context": "知识图谱关联路径：阈值跑 --(supports)--> 半马专项",
        "rag_sources": [
            {
                "source": "丹尼尔斯训练法.pdf",
                "page": 12,
                "snippet": "阈值跑适合稳定保持乳酸阈附近强度。",
            },
            {
                "source": "马拉松专项指南.pdf",
                "page": 5,
                "snippet": "周计划需要覆盖恢复、质量课与长距离。",
            },
        ],
        "user_profile": {
            "goal": "半马 90 分",
            "weekly_mileage": 60,
            "t_pace": "4:00/km",
            "experience_level": "进阶",
            "available_days": "周二,周四,周日",
            "max_session_minutes": 90,
            "terrain_preference": "田径场,公园",
            "vo2max": 58,
            "pace_preference": "节奏跑 4:00/km",
            "pace_zones": {
                "Z1": "5:40-5:10",
                "Z2": "5:10-4:50",
                "Z3": "4:50-4:30",
                "Z4": "4:30-4:15",
                "Z5": "4:15-4:05",
                "Z6": "4:05-3:55",
                "Z7": "3:55-3:45",
                "Z8": "3:45-3:35",
                "Z9": "3:35-3:20",
            },
        },
    }

    prompt = _build_plan_prompt(state)

    assert "一周 7 天全覆盖" in prompt
    assert "用户指定的训练日必须严格安排" in prompt
    assert "配速必须带单位 /km" in prompt
    assert "凡使用上述证据中的事实信息，必须在对应句末或表格单元格内标注 [1]、[2] 等来源编号" in prompt
    assert "[1] 丹尼尔斯训练法.pdf P.12 - 阈值跑适合稳定保持乳酸阈附近强度。" in prompt
    assert "[2] 马拉松专项指南.pdf P.5 - 周计划需要覆盖恢复、质量课与长距离。" in prompt
    assert "| Z1 |" in prompt
    assert "Profile (9-Zones)" in prompt


def test_build_ranked_evidence_assigns_sequential_citation_labels(monkeypatch):
    from marathon_qa_assistant.nodes import profile_and_retrieval as profile_module

    class _FakeGraphEngine:
        @staticmethod
        def map_edge_to_evidence(edge):
            return {
                "evidence_id": "graph_c1",
                "kind": "graph",
                "source_file": "训练指南.pdf",
                "page": 8,
                "chunk_id": "c1",
                "snippet": "阈值跑可以提升乳酸耐受。",
                "text": "阈值跑可以提升乳酸耐受。",
                "vector_score": 0.0,
                "retrieval_score": 0.0,
                "graph_confidence": 0.9,
                "entity_overlap": 0.0,
                "fusion_bonus": 0.0,
                "hybrid_score": 0.0,
                "citation_label": "",
                "trace": {
                    "vector_hit": False,
                    "vector_score": 0.0,
                    "graph_hit": True,
                    "fusion_bonus": 0.0,
                },
            }

    monkeypatch.setattr(profile_module, "graph_engine", _FakeGraphEngine())

    ranked = build_ranked_evidence(
        query="阈值跑如何安排？",
        vector_hits=[
            {
                "chunk_id": "c1",
                "source_file": "训练指南.pdf",
                "page": 8,
                "text": "阈值跑可以提升乳酸耐受。",
                "score": 0.85,
            },
            {
                "chunk_id": "c2",
                "source_file": "恢复手册.pdf",
                "page": 2,
                "text": "轻松跑帮助恢复。",
                "score": 0.40,
            },
        ],
        graph_edges=[{"relation": "supports"}],
        entities=["阈值跑"],
        top_k=2,
    )

    assert [item["citation_label"] for item in ranked] == ["[1]", "[2]"]
    assert ranked[0]["kind"] == "fusion"
    assert ranked[0]["trace"]["graph_hit"] is True
    assert ranked[0]["trace"]["graph_relation"] == "supports"
    assert ranked[0]["source_file"] == "训练指南.pdf"


def test_build_structured_report_contains_required_contract_fields():
    report = _build_structured_report(
        {
            "query": "帮我解释阈值训练安排",
            "category": "coach",
            "entities": ["阈值训练", "半马"],
            "graph_context": "知识图谱关联路径：阈值训练 --(supports)--> 半马",
            "mode": "team",
            "subtasks": [
                {
                    "task_id": "TASK-1",
                    "objective": "明确训练目标与约束",
                    "focus": "验证周计划与恢复安排",
                }
            ],
            "rag_sources": [
                {
                    "source": "训练指南.pdf",
                    "source_path": r"C:\docs\训练指南.pdf",
                    "source_file": "训练指南.pdf",
                    "page": 3,
                    "text": "阈值训练建议每周安排一次。",
                }
            ],
            "audit_scores": {"consistency": 88, "safety": 92, "roi": 75},
            "review_feedback": "结构化输出完整",
            "risk_alert": "注意恢复不足风险",
        },
        "本周建议保留一次阈值跑并加强恢复。",
    )

    assert report["title"] == "马拉松专业分析报告"
    assert report["summary"] == "本周建议保留一次阈值跑并加强恢复。"
    assert set(report).issuperset(
        {
            "summary",
            "findings",
            "recommendations",
            "report_metadata",
            "analysis_framework",
            "execution_steps",
            "audit_block",
            "evidence_base",
        }
    )
    assert report["execution_steps"][0]["task_id"] == "TASK-1"
    assert report["audit_block"]["scores"]["consistency"] == 88
    assert report["evidence_base"][0]["source_path"] == r"C:\docs\训练指南.pdf"
    assert report["evidence_base"][0]["path"] == r"C:\docs\训练指南.pdf"
    assert any("风险提示" in item for item in report["recommendations"])


def test_update_sidebar_renders_nine_zone_table_in_coach_mode(monkeypatch):
    from marathon_qa_assistant.apps import chainlit_app

    class _FakeSession:
        def __init__(self):
            self._data = {
                "chat_profile": "Coach Mode",
                "sidebar_visible": True,
                "sidebar_msg": type("SidebarRef", (), {"id": "sidebar-1"})(),
            }

        def get(self, key, default=None):
            return self._data.get(key, default)

        def set(self, key, value):
            self._data[key] = value

    class _FakeText:
        sent_payloads = []

        def __init__(self, name, content, display, for_id):
            self.name = name
            self.content = content
            self.display = display
            self.for_id = for_id

        async def send(self, for_id=None):
            self.__class__.sent_payloads.append(
                {
                    "name": self.name,
                    "content": self.content,
                    "display": self.display,
                    "for_id": for_id,
                }
            )
            return self

    monkeypatch.setattr(chainlit_app.cl, "user_session", _FakeSession())
    monkeypatch.setattr(chainlit_app.cl, "Text", _FakeText)

    profile = {
        "weekly_mileage": 80,
        "lthr": 168,
        "t_pace": "3:50/km",
        "goal": "半马 80 分",
        "target_race_date": "",
        "hr_zones": {f"Z{i}": f"{110 + i} bpm" for i in range(1, 10)},
        "pace_zones": {f"Z{i}": f"{i}:00/km" for i in range(1, 10)},
    }

    asyncio.run(chainlit_app.update_sidebar(profile_override=profile))

    payload = _FakeText.sent_payloads[-1]
    assert payload["name"] == "Athlete Stats"
    assert payload["display"] == "side"
    assert payload["for_id"] == "sidebar-1"
    assert "**区间映射 (Z1-Z9)**" in payload["content"]
    assert "| **Z9** |" in payload["content"]
    assert "Z1-Z5" not in payload["content"]
