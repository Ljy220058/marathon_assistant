import json
import time
import requests

API_URL = "http://localhost:8000/query"

HIGH_INTENSITY_FORBIDDEN_IN_BASE = {"间歇跑", "摄氧量训练", "无氧阈"}
BASE_PHASE_LABELS = ("基础期-1", "基础期-2")
BUILD_PHASE_LABELS = ("建设期-1", "建设期-2")
NEW_WORKOUT_TYPES = {"法特莱克", "坡道训练", "短冲"}

def send_query(query_text: str, timeout: int = 300) -> dict:
    print(f"\n{'='*60}")
    print(f"发送查询: {query_text[:60]}...")
    print(f"{'='*60}")
    t0 = time.time()
    resp = requests.post(
        API_URL,
        json={"query": query_text, "user_id": "default_user", "mode": "team"},
        timeout=timeout,
    )
    elapsed = time.time() - t0
    print(f"响应状态: {resp.status_code} (耗时 {elapsed:.1f}s)")
    if resp.status_code != 200:
        print(f"错误: {resp.text[:500]}")
        return {}
    return resp.json()


def validate_base_phase_safety(weeks: list, label: str) -> list:
    violations = []
    for week in weeks:
        week_label = week.get("week_label", week.get("phase_name", ""))
        week_num = week.get("week_number", "?")
        for day in week.get("daily_plans", week.get("days", [])):
            day_label = day.get("day_label", "")
            q_type = day.get("quality_session_type", "")
            s_type = day.get("secondary_session_type", "")
            all_types = f"{q_type} {s_type}"
            for forbidden in HIGH_INTENSITY_FORBIDDEN_IN_BASE:
                if forbidden in all_types:
                    violations.append(
                        f"  ❌ W{week_num} {day_label} [{week_label}] 包含禁止类型: {forbidden} (q={q_type}, s={s_type})"
                    )
    return violations


def validate_new_workout_types(weeks: list) -> dict:
    found = {}
    all_weeks_text = json.dumps(weeks, ensure_ascii=False)
    for wt in NEW_WORKOUT_TYPES:
        if wt in all_weeks_text:
            found[wt] = True
        else:
            found[wt] = False
    return found


def validate_cooldown_alternative(weeks: list) -> dict:
    result = {"cooldown_count": 0, "alternative_count": 0, "daily_plans_checked": 0}
    for week in weeks:
        for day in week.get("daily_plans", week.get("days", [])):
            result["daily_plans_checked"] += 1
            if day.get("cooldown_suggestion") and day["cooldown_suggestion"] != "missing":
                result["cooldown_count"] += 1
            if day.get("alternative_workout") and day["alternative_workout"] != "missing":
                result["alternative_count"] += 1
    return result


def print_week_workouts(weeks: list, max_weeks: int = 12):
    for week in weeks[:max_weeks]:
        w = week.get("week_number", "?")
        p = week.get("phase_name", week.get("week_label", "?"))
        print(f"\n  📅 W{w} [{p}]")
        for day in week.get("daily_plans", week.get("days", [])):
            dl = day.get("day_label", "?")
            q = day.get("quality_session_type", "")
            s = day.get("secondary_session_type", "")
            easy = day.get("easy_run_type", "")
            lr = day.get("long_run_type", "")
            ws = day.get("workout_summary", day.get("session_type", ""))
            print(f"    {dl}: q={q} | s={s} | e={easy} | l={lr} | ws={ws[:50]}")


if __name__ == "__main__":
    print("=" * 70)
    print("马拉松助手 - 训练计划生成质量验证")
    print("=" * 70)

    # ===== Test 1: 4周短计划 - 基础期安全约束验证 =====
    print("\n" + "=" * 70)
    print("TEST 1: 4周短计划 - 基础期安全约束")
    print("=" * 70)

    r1 = send_query("请给我制定4周半马训练计划，每周训练4天（周二、周四、周六、周日），目标提升速度但避免受伤。", timeout=300)

    if r1:
        source = None
        # 优先取 structured_training_plan
        stp = r1.get("structured_training_plan") or {}
        weeks = stp.get("training_plan_weeks") or stp.get("week_plans") or []

        if not weeks:
            sr = r1.get("structured_report") or {}
            weeks = sr.get("training_plan_weeks") or sr.get("week_plans") or []
            source = "structured_report"

        if weeks:
            print(f"\n📊 共 {len(weeks)} 周 (来源: {source or 'structured_training_plan'})")
            print_week_workouts(weeks)

            # 验证基础期安全
            print(f"\n🔍 基础期安全验证:")
            violations = validate_base_phase_safety(weeks, "4周短计划")
            if violations:
                for v in violations:
                    print(v)
                print("  ❌ 基础期出现高强度训练类型!")
            else:
                print("  ✅ 基础期无高强度训练 (间歇跑/摄氧量训练/无氧阈)")

            # 验证新训练类型
            print(f"\n🔍 新训练类型覆盖:")
            new_types = validate_new_workout_types(weeks)
            for wt, found in new_types.items():
                status = "✅" if found else "⚠️ (未出现)"
                print(f"  {status} {wt}")

            # 验证冷身/备选
            cd = validate_cooldown_alternative(weeks)
            print(f"\n🔍 冷身/备选训练:")
            print(f"  冷身建议: {cd['cooldown_count']}/{cd['daily_plans_checked']}")
            print(f"  备选训练: {cd['alternative_count']}/{cd['daily_plans_checked']}")
        else:
            print("  ❌ 未找到 week_plans")
            print(f"  响应 keys: {r1.keys()}")
        # 保存完整响应
        with open("tests/_api_test_4w.json", "w", encoding="utf-8") as f:
            json.dump(r1, f, ensure_ascii=False, indent=2, default=str)
        print("\n  完整响应已保存到 tests/_api_test_4w.json")

    # ===== Test 2: 8周中计划 - 阶段感知验证 =====
    print("\n" + "=" * 70)
    print("TEST 2: 8周中计划 - 阶段感知")
    print("=" * 70)

    r2 = send_query("请给我制定8周全马训练计划，每周训练4天（周二、周四、周六、周日），目标安全完成比赛。", timeout=300)

    if r2:
        stp = r2.get("structured_training_plan") or {}
        weeks = stp.get("training_plan_weeks") or stp.get("week_plans") or []
        if not weeks:
            sr = r2.get("structured_report") or {}
            weeks = sr.get("training_plan_weeks") or sr.get("week_plans") or []

        if weeks:
            print(f"\n📊 共 {len(weeks)} 周")
            print_week_workouts(weeks)

            violations = validate_base_phase_safety(weeks, "8周中计划")
            if violations:
                for v in violations:
                    print(v)
                print("  ❌ 基础期出现高强度训练类型!")
            else:
                print("  ✅ 基础期无高强度训练")

            new_types = validate_new_workout_types(weeks)
            print(f"\n🔍 新训练类型覆盖:")
            for wt, found in new_types.items():
                status = "✅" if found else "⚠️ (未出现)"
                print(f"  {status} {wt}")

            cd = validate_cooldown_alternative(weeks)
            print(f"\n🔍 冷身/备选训练:")
            print(f"  冷身建议: {cd['cooldown_count']}/{cd['daily_plans_checked']}")
            print(f"  备选训练: {cd['alternative_count']}/{cd['daily_plans_checked']}")
        else:
            print("  ❌ 未找到 week_plans")

        with open("tests/_api_test_8w.json", "w", encoding="utf-8") as f:
            json.dump(r2, f, ensure_ascii=False, indent=2, default=str)
        print("  完整响应已保存到 tests/_api_test_8w.json")

    # ===== 汇总 =====
    print("\n" + "=" * 70)
    print("验证完成! 完整响应已保存:")
    print("  - tests/_api_test_4w.json")
    print("  - tests/_api_test_8w.json")
    print("=" * 70)
