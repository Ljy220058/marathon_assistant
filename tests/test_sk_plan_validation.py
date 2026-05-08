import sys, json
sys.path.insert(0, r'c:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手')
from marathon_qa_assistant.core.training_plan_skeleton import build_structured_training_plan_skeleton

FORBIDDEN = {"间歇跑", "摄氧量训练", "无氧阈"}

profile_4w = {
    "experience_level": "进阶", "weekly_mileage": 80, "goal": "半马 90 分",
    "injury_history": ["无"], "lthr": 170, "t_pace": "400",
    "target_race_date": "3个月", "plan_duration_weeks": 12,
    "available_days": "周二,周四,周六,周日", "max_session_minutes": 100, "vo2max": 55,
}

def get_type(day):
    return day.get("training_type", "")

print("=" * 70)
print("TEST 1: 4周短计划 - 基础期安全约束")
print("=" * 70)
data = build_structured_training_plan_skeleton(
    query="请给我制定4周训练计划，每周训练4天",
    profile=profile_4w, requested_weeks=4
)
weeks = data.get("week_plans", data.get("training_plan_weeks", []))
print(f"共 {len(weeks)} 周\n")

violations = []
base_count = 0
for w in weeks:
    ph = w.get("phase", "?")
    wn = w.get("week_index", "?")
    is_base = any(bp in str(ph) for bp in ("基础", "适应"))
    for d in w.get("days", []):
        dl = d.get("day", "")
        t = get_type(d)
        if t == "休息":
            continue
        if is_base:
            base_count += 1
            warmup = d.get("warmup", "")
            main = d.get("main_set", "")
            print(f"  W{wn} {dl} [{ph}] {t}: warm={warmup[:30]} | main={main[:40]}")
        for fb in FORBIDDEN:
            if fb in t:
                if is_base:
                    violations.append(f"  [FAIL] W{wn} {dl} [{ph}] {fb}")
                else:
                    print(f"  [INFO] W{wn} {dl} [{ph}] {fb} (非基础期，允许)")

print(f"\n基础期训练日数: {base_count}")
print(f"基础期安全: {'PASS' if not violations else 'FAIL'}")
for v in violations:
    print(v)

all_text = json.dumps(weeks, ensure_ascii=False)
for nt in ["法特莱克", "坡道训练", "短冲"]:
    count = all_text.count(nt)
    print(f"  {nt}: {count} 次")

# === 8 周 ===
profile_8w = {
    **profile_4w,
    "goal": "全马 330", "weekly_mileage": 70, "t_pace": "430",
    "target_race_date": "5个月", "plan_duration_weeks": 20,
}

print()
print("=" * 70)
print("TEST 2: 8周中计划 - 阶段感知")
print("=" * 70)
data8 = build_structured_training_plan_skeleton(
    query="请给我制定8周训练计划，每周训练4天",
    profile=profile_8w, requested_weeks=8
)
weeks8 = data8.get("week_plans", data8.get("training_plan_weeks", []))
print(f"共 {len(weeks8)} 周\n")

for w in weeks8:
    ph = w.get("phase", "?")
    wn = w.get("week_index", "?")
    daily_summary = []
    for d in w.get("days", []):
        dl = d.get("day", "")
        t = get_type(d)
        if t == "休息":
            continue
        daily_summary.append(f"{dl}:{t}")
    print(f"  W{wn} [{ph}] " + " | ".join(daily_summary))

violations8 = []
base_count8 = 0
for w in weeks8:
    ph = w.get("phase", "?")
    is_base = any(bp in str(ph) for bp in ("基础", "适应"))
    if not is_base:
        continue
    wn = w.get("week_index", "?")
    for d in w.get("days", []):
        t = get_type(d)
        if t == "休息":
            continue
        base_count8 += 1
        for fb in FORBIDDEN:
            if fb in t:
                violations8.append(f"  [FAIL] W{wn} {d.get('day','')} [{ph}] {fb}")

print(f"\n基础期训练日数: {base_count8}")
print(f"基础期安全: {'PASS' if not violations8 else 'FAIL'}")
for v in violations8:
    print(v)

all_text8 = json.dumps(weeks8, ensure_ascii=False)
for nt in ["法特莱克", "坡道训练", "短冲"]:
    count = all_text8.count(nt)
    print(f"  {nt}: {count} 次")

print()
print("DONE")
