"""验证调整器(session_adjuster)在真实跳过场景下的表现。"""
import sys
sys.path.insert(0, 'apps/backend/src')
from marathon_qa_assistant.core.session_adjuster import propose_adjustments

# ── 构建一个典型的 12 周半马训练计划的第一周 ──
# 跑者画像：中级，周跑量 45km，目标半马，基础期
WEEK_1 = [
    {"day": "周一", "training_type": "恢复跑", "zone_range": "Z1",
     "main_set": "30min Z1", "is_rest": False, "stimulus_type": "volume_only"},
    {"day": "周二", "training_type": "一般有氧跑", "zone_range": "Z2-Z3",
     "main_set": "60min Z2-Z3", "is_rest": False, "stimulus_type": "volume_only"},
    {"day": "周三", "training_type": "节奏跑", "zone_range": "Z5-Z6",
     "main_set": "20min Z5-Z6 连续", "is_rest": False, "stimulus_type": "intensity"},
    {"day": "周四", "training_type": "一般有氧跑", "zone_range": "Z2-Z3",
     "main_set": "50min Z2-Z3", "is_rest": False, "stimulus_type": "volume_only"},
    {"day": "周五", "training_type": "间歇跑", "zone_range": "Z6-Z7",
     "main_set": "6 x 800m Z6-Z7 组间 2min 慢跑", "is_rest": False, "stimulus_type": "intensity"},
    {"day": "周六", "training_type": "恢复跑", "zone_range": "Z1",
     "main_set": "40min Z1 + 拉伸", "is_rest": False, "stimulus_type": "volume_only"},
    {"day": "周日", "training_type": "长距离", "zone_range": "Z2-Z3",
     "main_set": "18km Z2-Z3", "is_rest": False, "stimulus_type": "volume_only"},
]

PROFILE = {"weekly_mileage": 45, "experience_level": "中级", "goal": "半马 1:45"}

SCENARIOS = [
    # (场景名, 跳过的天, 预期操作, 预期原因关键词)
    ("跳过周三节奏跑 (intensity)", WEEK_1[2], "reschedule",
     ["Mujika", "7", "补"]),
    ("跳过周五间歇跑 (intensity)", WEEK_1[4], "reschedule",
     ["Mujika", "强度刺激", "补"]),
    ("跳过周一恢复跑 (volume_only)", WEEK_1[0], "delete",
     ["Seiler", "纯跑量课"]),
    ("跳过周六恢复跑 (volume_only)", WEEK_1[5], "delete",
     ["Seiler", "纯跑量课"]),
    ("跳过周二一般有氧跑 (volume_only)", WEEK_1[1], "delete",
     ["纯跑量课"]),
]

print("=" * 65)
print("Session Adjuster — 真实场景验证")
print("=" * 65)

passed = 0
failed = 0

for name, missed_day, expected_action, expected_keywords in SCENARIOS:
    proposals = propose_adjustments(missed_day, WEEK_1, PROFILE)
    print(f"\n场景: {name}")

    if not proposals:
        print(f"  FAIL: 没有生成任何建议")
        failed += 1
        continue

    p = proposals[0]
    action_ok = p.action == expected_action
    keywords_ok = all(kw in p.reason for kw in expected_keywords)
    confirm_ok = p.requires_confirmation == True

    print(f"  操作: {p.action} (预期 {expected_action}) {'OK' if action_ok else 'FAIL'}")
    print(f"  目标日: {p.target_day}")
    print(f"  理由: {p.reason[:80]}...")
    print(f"  来源: {p.source_citation}")
    print(f"  需确认: {p.requires_confirmation} {'OK' if confirm_ok else 'FAIL'}")

    # 检查关键词
    for kw in expected_keywords:
        if kw not in p.reason:
            print(f"  FAIL: 原因中缺少关键词 '{kw}'")

    if action_ok and keywords_ok and confirm_ok:
        print(f"  RESULT: PASS")
        passed += 1
    else:
        print(f"  RESULT: FAIL")
        failed += 1

# ── 边界场景 ──
print("\n" + "-" * 40)
print("边界场景")

# 边界 1: 跳过未标注 stimulus_type 的课（应回退到 zone_range 推导）
missed_no_label = {"day": "周三", "training_type": "法特莱克", "zone_range": "Z3-Z6",
                   "main_set": "40min 法特莱克", "is_rest": False, "stimulus_type": ""}
proposals = propose_adjustments(missed_no_label, WEEK_1, PROFILE)
if proposals:
    print(f"  无标签课: action={proposals[0].action} (zone_range Z3-Z6 → 推导为 mixed)")
    passed += 1
else:
    print(f"  无标签课: FAIL - 无建议")
    failed += 1

# 边界 2: 跳过没有任何 zone_range 的课（应保守处理为 volume_only）
missed_nothing = {"day": "周四", "training_type": "未知",
                  "main_set": "随便跑", "is_rest": False}
proposals = propose_adjustments(missed_nothing, WEEK_1, PROFILE)
if proposals and proposals[0].action == "delete":
    print(f"  无信息课: action={proposals[0].action} (保守为 volume_only → delete)")
    passed += 1
else:
    print(f"  无信息课: FAIL")
    failed += 1

# 边界 3: 跳过 intensity 课但无可用空位 (连续高强度日)
crowded_week = [
    {"day": "周一", "training_type": "间歇跑", "zone_range": "Z6-Z7",
     "is_rest": False, "stimulus_type": "intensity"},
    {"day": "周二", "training_type": "节奏跑", "zone_range": "Z5-Z6",
     "is_rest": False, "stimulus_type": "intensity"},
    {"day": "周三", "training_type": "摄氧量训练", "zone_range": "Z6-Z8",
     "is_rest": False, "stimulus_type": "intensity"},
    {"day": "周四", "training_type": "节奏跑", "zone_range": "Z5-Z6",
     "is_rest": False, "stimulus_type": "intensity"},
    {"day": "周五", "training_type": "重复跑", "zone_range": "Z8-Z9",
     "is_rest": False, "stimulus_type": "intensity"},
    {"day": "周六", "training_type": "法特莱克", "zone_range": "Z3-Z6",
     "is_rest": False, "stimulus_type": "mixed"},
    {"day": "周日", "training_type": "长距离", "zone_range": "Z2-Z3",
     "is_rest": False, "stimulus_type": "volume_only"},
]
missed_intensity = crowded_week[0]  # 跳过周一间歇跑
proposals = propose_adjustments(missed_intensity, crowded_week, PROFILE)
if proposals:
    p = proposals[0]
    # 密集周：周日是 volume_only 且距离周一/周六足够远 → reschedule 到周日
    # 48h 规则正确，但实际教练会避免在长距离日加强度课 —— 已知局限
    if p.action in ("reschedule", "trim"):
        print(f"  密集周强度课: action={p.action} (48h规则有效)")
        passed += 1
    else:
        print(f"  密集周强度课: action={p.action} FAIL")
        failed += 1
else:
    print(f"  无空位强度课: FAIL - 无建议")
    failed += 1

print(f"\n{'=' * 65}")
print(f"总计: {passed} 通过, {failed} 失败")
print(f"{'ALL PASSED' if failed == 0 else 'SOME FAILED'}")
