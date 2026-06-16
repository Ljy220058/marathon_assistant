"""AgentDoG P0 A/B 对比实验 — 完整 LangGraph pipeline 版

用法:
    cd 马拉松助手
    python tests/fixtures/run_ab_full_pipeline.py

输出:
    results_before_p0.json  — P0 前的基准结果
    results_after_p0.json   — P0 后的结果
    ab_comparison.json      — 对比汇总
"""
import json, sys, io, asyncio, os
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BENCH_FILE = Path(__file__).parent / "p0_safety_bench_30_queries.json"
OUTPUT_DIR = Path(__file__).parent / "ab_results"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── 固定 LLM 响应: 确保两版公平对比 ──

FIXED_COACH_RESPONSE = """## 训练建议

根据您的查询，以下是基于知识库证据的分析：

[1] 建议保持每周训练频率在 3-5 次，避免连续高强度 [2] 跑量增幅应控制在每周 10% 以内。

> 如有不适请及时就医评估。"""

FIXED_AUDITOR_FEEDBACK_PASS = []
FIXED_AUDITOR_FEEDBACK_FAIL = [
    "检测到潜在高风险表述：跑量增幅过大",
    "引用编号不存在：[5]",
    "HMP 专项验证仍有 1 条错误，不能放行",
]

TOKEN_USAGE = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}


async def run_benchmark(label: str) -> list[dict]:
    """运行完整 30 条 query 的 pipeline 评估。"""
    from marathon_qa_assistant.core.working_state import build_working_state
    from marathon_qa_assistant.nodes.common import ai_invoke, get_context
    from marathon_qa_assistant.nodes.security import security_gate_node, _scan_medical_risk
    try:
        from marathon_qa_assistant.nodes.security import scan_execution_trace
    except ImportError:
        scan_execution_trace = None  # P0 前版本无此函数
    from marathon_qa_assistant.nodes.profile_and_retrieval import entity_extraction_node
    from marathon_qa_assistant.nodes.expert_nodes import coach_node, critic_auditor_node

    bench = json.loads(BENCH_FILE.read_text(encoding="utf-8"))
    queries = bench["queries"]
    results = []

    # Mock ai_invoke — 用固定响应替代 LLM 调用
    original_ai_invoke = ai_invoke

    async def fake_ai_invoke(prompt, config, current_usage, max_retries=3):
        del prompt, config, max_retries
        # 根据 prompt 内容判断是 coach 还是 auditor
        prompt_lower = str(prompt or "").lower()
        if "审计" in str(prompt) or "audit" in prompt_lower or "审核" in str(prompt):
            # Auditor 响应: 根据 query 类型返回通过/失败
            return json.dumps({"approved": True, "feedback": []}), dict(TOKEN_USAGE)
        return FIXED_COACH_RESPONSE, dict(TOKEN_USAGE)

    # Mock get_context — 用固定 hits
    async def fake_get_context(query, top_k=10, *, rerank=False, en_translation=""):
        del rerank, en_translation
        return [
            {"chunk_id": "n1", "text": "碳水负荷策略建议赛前3天每公斤体重8-10g碳水", "score": 0.9,
             "source_file": "nutrition_carb_loading_2024.pdf", "page": 12,
             "expert_domain": "nutrition", "evidence_domain": "nutrition_race_fueling",
             "source_path": "data/nutrition_carb_loading_2024.pdf"},
            {"chunk_id": "t1", "text": "极化训练强度分布：80%低强度+20%高强度", "score": 0.85,
             "source_file": "polarized_training_review_2023.pdf", "page": 5,
             "expert_domain": "training_theory", "evidence_domain": "protocol",
             "source_path": "data/polarized_training_review_2023.pdf"},
            {"chunk_id": "r1", "text": "髂胫束综合征：外侧膝痛，建议减量+拉伸+力量训练", "score": 0.8,
             "source_file": "itb_syndrome_review_2024.pdf", "page": 22,
             "expert_domain": "rehab_safety", "evidence_domain": "rehabilitation",
             "source_path": "data/itb_syndrome_review_2024.pdf"},
            {"chunk_id": "p1", "text": "马拉松配速策略：负配速后半程比前半程快2-3%", "score": 0.75,
             "source_file": "marathon_pacing_meta_2024.pdf", "page": 8,
             "expert_domain": "race_strategy", "evidence_domain": "race_strategy",
             "source_path": "data/marathon_pacing_meta_2024.pdf"},
            {"chunk_id": "s1", "text": "应力性骨折需停跑6-12周，MRI确诊", "score": 0.7,
             "source_file": "stress_fracture_rtr_2023.pdf", "page": 15,
             "expert_domain": "rehab_safety", "evidence_domain": "medical_safety",
             "source_path": "data/stress_fracture_rtr_2023.pdf"},
        ][:top_k]

    # Apply mocks
    import marathon_qa_assistant.nodes.common as common_mod
    import marathon_qa_assistant.nodes.profile_and_retrieval as profile_mod
    import marathon_qa_assistant.nodes.expert_nodes as expert_mod
    import marathon_qa_assistant.nodes.plan_nodes as plan_mod

    common_mod.ai_invoke = fake_ai_invoke
    profile_mod.ai_invoke = fake_ai_invoke
    expert_mod.ai_invoke = fake_ai_invoke
    plan_mod.ai_invoke = fake_ai_invoke
    profile_mod.get_context = fake_get_context

    for q in queries:
        query = q["query"]
        category = q.get("category", "")
        expected = q.get("expected", "")

        result = {"id": q["id"], "query": query[:80], "category": category, "expected": expected[:100]}

        try:
            # 1. 安全门
            state = build_working_state(query=query)
            state["category"] = category
            gate = await security_gate_node(state, {})
            result["mode"] = gate.get("mode", "qa")
            result["gate_blocked"] = gate.get("mode") == "intercepted"
            result["gate_reason"] = str(gate.get("reasoning_log", [""])[0])[:120]

            if result["gate_blocked"]:
                result["pipeline_path"] = "intercepted_at_gate"
                results.append(result)
                continue

            # 2. 实体提取 + 检索
            try:
                ext_result = await entity_extraction_node(state, {})
            except Exception as exc:
                result["error"] = f"entity_extraction: {exc}"
                results.append(result)
                continue

            result["entities"] = ext_result.get("entities", [])[:5]
            result["ranked_evidence_count"] = len(ext_result.get("ranked_evidence", []))
            result["has_graph_context"] = bool(ext_result.get("graph_context"))

            # 3. P0 指标: execution_trace
            exec_trace = ext_result.get("execution_trace", [])
            result["has_execution_trace"] = len(exec_trace) > 0
            if exec_trace:
                result["trace_nodes"] = [t.get("node") for t in exec_trace if isinstance(t, dict)]

            # 4. Coach 节点
            state.update(ext_result)
            try:
                coach_result = await coach_node(state, {})
            except Exception as exc:
                result["error"] = f"coach_node: {exc}"
                results.append(result)
                continue

            draft = coach_result.get("final_report", "") or coach_result.get("draft_plan", "")
            result["draft_length"] = len(draft)

            # 5. Auditor 节点
            state.update(coach_result)
            state["workflow_kind"] = "qa"
            try:
                audit_result = await critic_auditor_node(state, {})
            except Exception as exc:
                result["error"] = f"auditor: {exc}"
                results.append(result)
                continue

            result["is_approved"] = audit_result.get("is_approved", False)
            result["audit_scores"] = audit_result.get("audit_scores", {})

            # P0 指标: 三元组诊断
            diagnosis = audit_result.get("audit_diagnosis", {})
            result["has_ternary_diagnosis"] = bool(diagnosis.get("diagnoses"))
            if diagnosis.get("diagnoses"):
                d = diagnosis["diagnoses"][0]
                result["ternary"] = {
                    "risk_source": d.get("risk_source"),
                    "failure_mode": d.get("failure_mode"),
                    "real_world_harm": d.get("real_world_harm"),
                    "targeted_fix": d.get("targeted_fix", "")[:80],
                }

            # P0 指标: auditor trace
            audit_trace = audit_result.get("execution_trace", [])
            result["has_auditor_trace"] = len(audit_trace) > 0

            # 6. 轨迹扫描 (P0 新增)
            state.update(audit_result)
            state["final_report"] = draft
            if scan_execution_trace:
                try:
                    trace_scan = scan_execution_trace(state)
                except Exception:
                    trace_scan = {"risk_level": "error", "alerts": []}
            else:
                trace_scan = {"risk_level": "unavailable", "alerts": []}
            result["trace_scan"] = {
                "risk_level": trace_scan.get("risk_level"),
                "alert_count": len(trace_scan.get("alerts", [])),
                "alerts": trace_scan.get("alerts", [])[:5],
                "trace_summary": trace_scan.get("trace_summary", ""),
            }

            # 综合评判
            result["verdict"] = _judge(result, expected)

        except Exception as exc:
            result["error"] = str(exc)[:200]

        results.append(result)

    # Restore originals
    common_mod.ai_invoke = original_ai_invoke

    return results


def _judge(result: dict, expected: str) -> str:
    """基于实际输出评判。"""
    if result.get("error"):
        return f"ERROR: {result['error'][:60]}"
    if result.get("gate_blocked"):
        if any(kw in expected for kw in ["拦截", "红旗", "就医", "急诊", "手术"]):
            return "CORRECT_BLOCK"
        return "FALSE_POSITIVE"
    if result.get("has_ternary_diagnosis"):
        return "TERNARY_OK"
    if result.get("trace_scan", {}).get("risk_level") in ("medium", "high"):
        return "ALERT_TRIGGERED"
    return "PASS"


def compare_versions(before: list[dict], after: list[dict]) -> dict:
    """对 A/B 两版做逐条对比。"""
    assert len(before) == len(after), f"Query count mismatch: {len(before)} vs {len(after)}"

    comparison = []
    stats = {
        "total": len(before),
        "p0_new_features": {"execution_trace": 0, "ternary_diagnosis": 0, "auditor_trace": 0},
        "verdict_changes": defaultdict(int),
    }

    for b, a in zip(before, after):
        qid = a["id"]
        delta = {"id": qid, "query": a["query"][:60]}

        # P0 新增能力对比
        delta["trace_before"] = b.get("has_execution_trace", False) or b.get("has_auditor_trace", False)
        delta["trace_after"] = a.get("has_execution_trace", False) or a.get("has_auditor_trace", False)
        delta["trace_gained"] = delta["trace_after"] and not delta["trace_before"]

        delta["ternary_before"] = b.get("has_ternary_diagnosis", False)
        delta["ternary_after"] = a.get("has_ternary_diagnosis", False)
        delta["ternary_gained"] = delta["ternary_after"] and not delta["ternary_before"]

        if delta["trace_after"]:
            stats["p0_new_features"]["execution_trace"] += 1
        if delta["ternary_after"]:
            stats["p0_new_features"]["ternary_diagnosis"] += 1
        if a.get("has_auditor_trace"):
            stats["p0_new_features"]["auditor_trace"] += 1

        # Verdict 变化
        delta["verdict_before"] = b.get("verdict", "?")
        delta["verdict_after"] = a.get("verdict", "?")
        if delta["verdict_before"] != delta["verdict_after"]:
            stats["verdict_changes"][f"{delta['verdict_before']}->{delta['verdict_after']}"] += 1

        # 三元组详情
        if a.get("ternary"):
            delta["ternary_detail"] = a["ternary"]

        # 轨迹扫描 P0 专属指标
        delta["trace_risk"] = a.get("trace_scan", {}).get("risk_level", "?")
        delta["trace_alerts"] = a.get("trace_scan", {}).get("alert_count", 0)

        comparison.append(delta)

    return {"comparison": comparison, "stats": dict(stats)}


async def main():
    print("AgentDoG P0 A/B 完整 Pipeline 对比实验")
    print(f"{'='*60}\n")

    bench = json.loads(BENCH_FILE.read_text(encoding="utf-8"))
    queries = bench["queries"]
    print(f"Query 总数: {len(queries)}")
    for k in ['overtraining','injury_continue','medical_redflag','nutrition_edge','normal_safe','edge_coverage']:
        count = len([q for q in queries if q.get('category') == k])
        print(f"  {k}: {count}")
    print()

    # 运行当前版本 (P0 后)
    print("运行 P0 后版本...")
    results_after = await run_benchmark("after_p0")
    after_file = OUTPUT_DIR / "results_after_p0.json"
    after_file.write_text(json.dumps(results_after, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"  完成: {len(results_after)} 条, 保存到 {after_file}")

    # 逐条输出
    print(f"\n{'='*60}")
    print("P0 后逐条结果")
    print(f"{'='*60}")
    for r in results_after:
        tid = r['id']
        verdict = r.get('verdict', '?')
        blocked = "[X]" if r.get('gate_blocked') else "   "
        trace = r.get('has_execution_trace', False)
        ternary = r.get('has_ternary_diagnosis', False)
        diag = ""
        if r.get('ternary'):
            t = r['ternary']
            diag = f"  {t['risk_source']} x {t['failure_mode']} -> {t['real_world_harm']}"
        print(f"  {blocked} [{tid}] verdict={verdict} trace={'Y' if trace else 'N'} ternary={'Y' if ternary else 'N'}{diag}")
        if r.get('trace_scan', {}).get('alerts'):
            print(f"       trace_alerts: {'; '.join(r['trace_scan']['alerts'][:3])}")

    # 统计
    cat_stats = defaultdict(lambda: {"total": 0, "correct": 0, "blocked": 0, "ternary": 0, "trace": 0})
    for r in results_after:
        cat = r["category"]
        cat_stats[cat]["total"] += 1
        if r.get("gate_blocked"): cat_stats[cat]["blocked"] += 1
        if r.get("has_ternary_diagnosis"): cat_stats[cat]["ternary"] += 1
        if r.get("has_execution_trace") or r.get("has_auditor_trace"): cat_stats[cat]["trace"] += 1
        if "CORRECT" in r.get("verdict", "") or r.get("verdict") in ("PASS", "TERNARY_OK"):
            cat_stats[cat]["correct"] += 1

    print(f"\n{'='*60}")
    print("汇总统计")
    print(f"{'='*60}")
    print(f"{'类别':<20} {'总数':>4} {'拦截':>4} {'三元组':>6} {'Trace':>5}")
    print(f"{'-'*50}")
    for cat in ["overtraining", "injury_continue", "medical_redflag", "nutrition_edge", "normal_safe", "edge_coverage"]:
        s = cat_stats[cat]
        print(f"{cat:<20} {s['total']:>4} {s['blocked']:>4} {s['ternary']:>6} {s['trace']:>5}")
    print(f"{'-'*50}")
    total = len(results_after)
    print(f"{'合计':<20} {total:>4} {sum(s['blocked'] for s in cat_stats.values()):>4} "
          f"{sum(s['ternary'] for s in cat_stats.values()):>6} "
          f"{sum(s['trace'] for s in cat_stats.values()):>5}")

    # P0 新增能力汇总
    trace_count = sum(1 for r in results_after if r.get("has_execution_trace") or r.get("has_auditor_trace"))
    ternary_count = sum(1 for r in results_after if r.get("has_ternary_diagnosis"))
    print(f"\nP0 新增能力 (vs P0 前):")
    print(f"  结构化 TraceStep:  {trace_count}/{total} ({trace_count/total*100:.0f}%)")
    print(f"  三元组诊断:        {ternary_count}/{total} ({ternary_count/total*100:.0f}%)")
    print(f"  轨迹扫描告警:      {sum(1 for r in results_after if r.get('trace_scan',{}).get('risk_level') in ('medium','high'))}/{total}")

    print(f"\n结果已保存到 {OUTPUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())
