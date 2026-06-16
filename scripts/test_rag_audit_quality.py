"""RAG 审核检索质量测试: 8 个典型审核查询 → KB 检索 → 人工判断相关性。"""
import json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'backend', 'src'))

AUDIT_QUERIES = [
    ("节奏跑最佳时长", "节奏跑 20-30分钟 业余跑者 阈值训练 持续时间"),
    ("间歇跑组数限制", "间歇跑 组数 上限 重复段 恢复时间 最大组数"),
    ("强度课周组合", "半马 比赛专项期 周课表 强度课 节奏跑 间歇跑 组合 结构"),
    ("新手跑量递增", "长距离跑 每周递增幅度 不超过 10% 新手 跑量递增"),
    ("减量期安排", "减量期 比赛前一周 训练课 强度 跑量 削减 安排"),
    ("强度课间隔", "强度课 间隔 最佳 至少 48小时 高强度训练 之间"),
    ("VO2max间歇设计", "最大摄氧量 间歇训练 组间恢复 时间 业余跑者 设计"),
    ("赛后恢复限制", "全马赛后 恢复期 导入期 高强度 限制 几周"),
]

RELEVANCE_CRITERIA = {
    "节奏跑最佳时长": ["tempo", "threshold", "T跑", "节奏", "阈值", "lactate", "20-30", "Daniels"],
    "间歇跑组数限制": ["interval", "间歇", "组", "rep", "摄氧量", "HIT", "Buchheit", "Billat", "工作段"],
    "强度课周组合": ["phase", "阶段", "week", "周期", "课表结构", "Pfitzinger", "基础期", "建设期", "巅峰期", "减量期", "microcycle"],
    "新手跑量递增": ["递增", "10%", "ACWR", "Gabbett", "progression", "增", "负荷比"],
    "减量期安排": ["taper", "减量", "赛前", "Bosquet", "削减", "41-60", "指数", "Taper"],
    "强度课间隔": ["间隔", "48", "高强度.*之间", "Pfitzinger", "恢复跑", "至少.*天", "recovery.*day", "强度课.*隔"],
    "VO2max间歇设计": ["VO2max", "摄氧量", "intermittent", "HIT", "Buchheit", "Billat", "work.*rest", "红区", "组间", "I跑"],
    "赛后恢复限制": ["recovery", "恢复", "introductory", "导入", "marathon", "全马"],
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSONL_SOURCES = [
    ("training_protocol", os.path.join(ROOT, "data", "vector_kb", "v2_sharded", "training_protocol", "chunks.jsonl")),
    ("action_library", os.path.join(ROOT, "data", "knowledge", "curated", "action_library", "action_library_chunks.jsonl")),
]

def search_jsonl(query_text):
    results = []
    keywords = query_text.lower().split()
    for cat, path in JSONL_SOURCES:
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8') as f:
            for line in f:
                obj = json.loads(line.strip())
                text = str(obj.get("text", ""))
                domain = str(obj.get("domain_terms", ""))
                combined = (text + " " + domain).lower()
                score = sum(1 for kw in keywords if kw in combined)
                if score >= 1:
                    results.append({
                        "source": cat,
                        "chunk_id": obj.get("chunk_id", ""),
                        "text_preview": text[:150],
                        "score": score,
                        "source_file": str(obj.get("source_file", "")),
                    })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:5]

def is_relevant(hit, criteria):
    text_lower = hit["text_preview"].lower()
    return any(c.lower() in text_lower for c in criteria)

output_lines = []
output_lines.append("=" * 70)
output_lines.append("RAG Audit Retrieval Quality Test")
output_lines.append("=" * 70)

total_hits = 0
total_relevant = 0
detail = []

for short_name, query_text in AUDIT_QUERIES:
    output_lines.append(f"\nQuery: {short_name}")
    output_lines.append(f"  Terms: {query_text[:80]}...")

    hits = search_jsonl(query_text)
    criteria = RELEVANCE_CRITERIA.get(short_name, [])

    relevant_count = 0
    for i, hit in enumerate(hits):
        rel = is_relevant(hit, criteria)
        if rel:
            relevant_count += 1
        marker = "OK" if rel else "XX"
        preview = hit["text_preview"][:100].replace('\n', ' ')
        output_lines.append(f"  [{i+1}] [{marker}] [{hit['source']}] {preview}...")

    count = min(len(hits), 5)
    total_hits += count
    total_relevant += relevant_count
    detail.append(f"{short_name}: {relevant_count}/{count} relevant")

output_lines.append("\n" + "=" * 70)
output_lines.append("Summary")
output_lines.append("=" * 70)
for d in detail:
    output_lines.append(f"  {d}")

rate = total_relevant / max(total_hits, 1) * 100
output_lines.append(f"\nTotal: {total_relevant}/{total_hits} relevant ({rate:.1f}%)")

if rate >= 60:
    output_lines.append("Conclusion: KB quality SUFFICIENT for RAG audit (>=60%)")
elif rate >= 30:
    output_lines.append("Conclusion: KB quality MARGINAL (30-60%), recommend supplementing literature")
else:
    output_lines.append("Conclusion: KB quality INSUFFICIENT (<30%), must add literature first")

output_path = os.path.join(ROOT, "artifacts", "rag_audit_quality_test.txt")
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))

print(f"Results written to: {output_path}")
print(f"Hit rate: {rate:.1f}%")
print(f"Relevant: {total_relevant}/{total_hits}")
