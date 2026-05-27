"""动作库解析器单元测试 — 覆盖 F1-F6 六类损坏修复"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from marathon_qa_assistant.services.exercise_parser import parse_action_library


def _find_entry(entries, name):
    for e in entries:
        if e.get("name") == name:
            return e
    return None


def test_full_valid_exercise():
    text = """动作库
【Technique & Mobility】
1. name：轻松跑
categories：Aerobic , Base , Recovery
content：40-60min，在 60% - 70%HRmax
objective：建立有氧基础，促进血液循环与代谢废物排出。"""

    entries = parse_action_library(text)
    assert len(entries) == 1
    e = entries[0]
    assert e["name"] == "轻松跑"
    assert "Aerobic" in e["categories"]
    assert "Base" in e["categories"]
    assert "40-60min" in e["content"]
    assert "有氧基础" in e["objective"]
    assert e["content_missing"] is False


def test_fix_missing_colon():
    text = """动作库
1. name：重复跑
categories Anaerobic , Speed , Lactate-Tolerance
content：5-6*300（800专项）
objective：提升无氧做功容量。"""

    entries = parse_action_library(text)
    e = _find_entry(entries, "重复跑")
    assert e is not None
    assert "Anaerobic" in e["categories"]
    assert "Speed" in e["categories"]


def test_dedup_by_name():
    text = """动作库
1. name：轻松跑
categories：Aerobic
content：第一份内容
objective：第一份目标。
1. name：轻松跑
categories：Aerobic
content：第二份内容。
objective：重复条目。"""

    entries = parse_action_library(text)
    names = [e["name"] for e in entries]
    assert names.count("轻松跑") == 1


def test_merge_orphan_start():
    text = """动作库
1. name：复合速度训练
categories：Speed , Simulation , Kick
content：4*400+4*250（前50用来渐加速到最大速度）
objective：训练疲劳状态下的冲刺能力。
2. name：拉伸放松
categories：Recovery
content：正常内容。
objective：恢复肌肉。"""

    entries = parse_action_library(text)
    compound = _find_entry(entries, "复合速度训练")
    assert compound is not None
    stretch = _find_entry(entries, "拉伸放松")
    assert stretch is not None
    assert len(stretch["content"]) > 0


def test_empty_content_with_objective():
    text = """动作库
1. name：核心训练
categories：Core , Stability , Strength
content：
objective：增强躯干稳定性，在疲劳状态下维持正确跑姿。"""

    entries = parse_action_library(text)
    e = _find_entry(entries, "核心训练")
    assert e is not None
    assert e["content_missing"] is True
    assert len(e["objective"]) > 0


def test_empty_both_discard():
    text = """动作库
1. name：空动作
categories：Test
content：
objective："""

    entries = parse_action_library(text)
    assert _find_entry(entries, "空动作") is None


def test_merge_truncated_content():
    text = """动作库
1. name：热身
categories：激活，有氧
content：15分钟慢跑+动态拉伸+马克操+3.2-4.8km加速跑（有氧跑加速到有氧阈值上限）力
2. name：下一个
categories：Test
content：量训练应该循序渐进。
objective：测试条目。"""

    entries = parse_action_library(text)
    warmup = _find_entry(entries, "热身")
    assert warmup is not None
    assert "力量训练" in warmup["content"] or "循序渐进" in warmup["content"]


def test_discard_objective_only():
    text = """动作库
objective：这是一个没有名称的孤立目标条目，应该被丢弃。
1. name：有效动作
categories：Test
content：有名称有内容。
objective：有效目标。"""

    entries = parse_action_library(text)
    names = [e["name"] for e in entries]
    assert len(names) == 1
    assert names[0] == "有效动作"


def test_multiple_exercises():
    text = """动作库
【Technique & Mobility】
1. name：灵活度训练
categories：Mobility , Recovery
content：静态拉伸+呼吸配合
objective：松解→改善关节活动度→激活肌肉
2. name：马克操
categories：Technique , Drills
content：A字跳、B字跳、C式等
objective：优化跑姿力学，提升神经协调性"""

    entries = parse_action_library(text)
    assert len(entries) == 2
    assert entries[0]["name"] == "灵活度训练"
    assert entries[1]["name"] == "马克操"
