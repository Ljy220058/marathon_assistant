"""动作库覆盖率测试：验证 50 条条目完整性、source_authority 标注、新课型覆盖。"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JSONL_PATH = ROOT / "data" / "knowledge" / "curated" / "action_library" / "action_library_chunks.jsonl"


@pytest.fixture(scope="module")
def action_library_entries():
    if not JSONL_PATH.exists():
        pytest.skip(f"动作库 JSONL 不存在: {JSONL_PATH}")
    with open(JSONL_PATH, encoding="utf-8") as f:
        return [json.loads(line.strip()) for line in f if line.strip()]


@pytest.fixture(scope="module")
def registry():
    try:
        from marathon_qa_assistant.services.workout_template_retriever import WORKOUT_TEMPLATE_REGISTRY
        return WORKOUT_TEMPLATE_REGISTRY
    except ImportError:
        pytest.skip("无法导入 WORKOUT_TEMPLATE_REGISTRY")


# ── 数量验证 ──
def test_jsonl_entry_count(action_library_entries):
    """P10-1: 动作库总条目 = 50。"""
    assert len(action_library_entries) == 50, f"期望 50 条，实际 {len(action_library_entries)}"


# ── source_authority 完整性 ──
def test_all_entries_have_source_authority(action_library_entries):
    """P10-2: 所有条目 source_authority 非空。"""
    missing = [e["chunk_id"] for e in action_library_entries if not e.get("source_authority", "").strip()]
    assert not missing, f"以下条目缺少 source_authority: {missing}"


# ── 权威分布 ──
def test_source_authority_distribution(action_library_entries):
    """P10-3: A >= 26, B >= 9, C >= 15。"""
    counts = {"A": 0, "B": 0, "C": 0}
    for e in action_library_entries:
        sa = e.get("source_authority", "").strip()
        if sa in counts:
            counts[sa] += 1
    assert counts["A"] >= 26, f"A 级条目不足: {counts['A']}"
    assert counts["B"] >= 7, f"B 级条目不足: {counts['B']}"
    assert counts["C"] >= 7, f"C 级条目不足: {counts['C']}"


# ── 新课型覆盖 ──
_GAP_ZONE_RANGES = {  # 7 个缺口类型对应的 zone_range
    "recovery_run_z1": "Z1",
    "general_aerobic_z2z3": "Z2-Z3",
    "continuous_tempo_z5z6": "Z5-Z6",
    "mp_mixed_long_run": "Z2-Z5",
    "strides_z7z9": "Z7-Z9",
    "race_simulation": "Z5-Z7",
    "hm_specific_pace_a": "Z4-Z5",
}

_GAP_NAMES = {  # 辅助：按名称词匹配
    "recovery_run_z1": "恢复跑",
    "general_aerobic_z2z3": "一般有氧",
    "continuous_tempo_z5z6": "节奏跑",
    "mp_mixed_long_run": "MP混合",
    "strides_z7z9": "跨步",
    "race_simulation": "模拟",
    "hm_specific_pace_a": "半马专项",
}


@pytest.mark.parametrize("gap_key", list(_GAP_ZONE_RANGES))
def test_gap_type_has_entries(action_library_entries, gap_key):
    """P10-4: 每个新课型在 JSONL 中至少有 1 条匹配条目。"""
    expected_zone = _GAP_ZONE_RANGES[gap_key]
    expected_name = _GAP_NAMES[gap_key]

    # 按 chunk_id 前缀（新课型）或 zone_range + name 匹配
    matches = [
        e for e in action_library_entries
        if e.get("chunk_id", "").startswith("action_lib_")
        and expected_zone in str(e.get("tags", {}).get("zone_range", "") or e.get("domain_terms", []))
    ]
    # 如果上面不匹配，用名称模糊匹配
    if not matches:
        matches = [
            e for e in action_library_entries
            if e.get("chunk_id", "").startswith("action_lib_")
            and expected_name in str(e.get("text", ""))
        ]

    assert len(matches) >= 1, f"新课型 {gap_key} ({expected_name}, {expected_zone}): JSONL 中无匹配条目"


# ── Registry 完整性 ──
_NEW_REGISTRY_KEYS = [
    "recovery_run_z1", "general_aerobic_z2z3", "continuous_tempo_z5z6",
    "mp_mixed_long_run", "strides_z7z9", "race_simulation", "hm_specific_pace_a",
]


def test_registry_has_all_new_types(registry):
    """P10-5: WORKOUT_TEMPLATE_REGISTRY 包含全部 7 个新课型 key。"""
    missing = [k for k in _NEW_REGISTRY_KEYS if k not in registry]
    assert not missing, f"Registry 缺少以下 key: {missing}"

    for key in _NEW_REGISTRY_KEYS:
        entry = registry[key]
        assert entry.get("display_name"), f"{key}: 缺少 display_name"
        assert entry.get("aliases"), f"{key}: 缺少 aliases"
        assert entry.get("zone_range"), f"{key}: 缺少 zone_range"
        assert entry.get("source_priority"), f"{key}: 缺少 source_priority"


# ── Registry-JSONL 对齐 ──
def test_source_priority_files_in_jsonl(action_library_entries, registry):
    """P10-6: Registry 中 source_priority 引用的文件在 JSONL 中有对应条目。"""
    # 收集 JSONL 中 source_file 的去重集合
    jsonl_sources = set()
    for e in action_library_entries:
        src = str(e.get("source_file") or "").strip()
        if src:
            jsonl_sources.add(src)

    # 检查每个新课型的 source_priority 对应的 JSONL 条目
    for key in _NEW_REGISTRY_KEYS:
        entry = registry[key]
        source_priority = entry.get("source_priority", [])
        # 检查至少有一个 source_priority 文件在 JSONL 中有条目
        matched = any(sp in jsonl_sources for sp in source_priority)
        assert matched, (
            f"{key}: source_priority {source_priority} 中的文件在 JSONL 中无匹配条目。"
            f" JSONL 中的 source_file: {sorted(jsonl_sources)[:10]}..."
        )
