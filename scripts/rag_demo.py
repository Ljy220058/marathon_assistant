"""完整 RAG 管线：意图分类 → 领域策略 → 域过滤 → 向量检索 → 图搜索"""
import json, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'apps/backend/src')

from pathlib import Path
from collections import defaultdict
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from marathon_qa_assistant.services.vector_store import load_chunks
from marathon_qa_assistant.services.knowledge_graph import GraphEngine

# 真实管线核心函数
from marathon_qa_assistant.nodes.profile_and_retrieval import (
    INTENT_DOMAIN_POLICIES, EXPERT_DOMAIN_POLICIES,
    _intent_domain_policy, _expert_domain_policy,
    filter_hits_for_intent_domain, _hit_domain_values, _infer_expert_domain,
)

# 加载
print("Loading FAISS...")
embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url="http://localhost:11434")
faiss_store = FAISS.load_local("data/vector_kb/v2/faiss_db", embeddings, allow_dangerous_deserialization=True)
chunks = load_chunks(Path("data/vector_kb/v2/chunks.jsonl"))
chunk_map = {c['chunk_id']: c for c in chunks}
print(f"Loaded: {len(chunks)} chunks")

engine = GraphEngine.__new__(GraphEngine)
engine.nodes = {}; engine.edges = []; engine.processed_chunks = {}
engine.GRAPH_DATA_PATH = Path('data/vector_kb/v2/knowledge_graph.json')
engine._mermaid_cache = None; engine._cache_key = None; engine.STRICT_MODE = True
engine.load_graph()
print(f"Loaded KG: {len(engine.nodes)}n {len(engine.edges)}e\n")

REL_CN = {
    'improves': '改善', 'reduces': '减少', 'risks': '增加风险',
    'requires': '需要', 'supports': '促进', 'adjusts': '调节',
    'constrains': '约束', 'bridges_to': '桥接',
}

def rag_pipeline(query, category=""):
    print(f"Q: {query}")
    print(f"   Category: {category or '(auto-detect)'}")

    # 1. 意图域策略
    policy_name, policy = _intent_domain_policy(category=category, query=query)
    if policy:
        print(f"   Intent policy: {policy_name} → evidence_domains={policy['domains']}")
    else:
        # 缺省 coach
        default_domains = EXPERT_DOMAIN_POLICIES.get('coach', set())
        print(f"   Intent policy: (default coach) → expert_domains={default_domains}")

    # 2. FAISS 向量检索
    docs = faiss_store.similarity_search(query, k=15)
    hits = []
    for d in docs:
        cid = d.metadata.get('chunk_id', '')
        c = chunk_map.get(cid, {})
        hits.append({
            'chunk_id': cid,
            'expert_domain': c.get('expert_domain', ''),
            'evidence_domain': c.get('evidence_domain', ''),
            'text': d.page_content[:100],
            'source_file': d.metadata.get('source_file', '')[:40],
        })

    # 3. 域过滤
    if policy:
        filtered = []
        fallback = []
        allowed = set(policy['domains'])
        for h in hits:
            if _hit_domain_values(h) & allowed:
                filtered.append(h)
            else:
                fallback.append(h)
        primary_hits = filtered[:8] + fallback[:4]
    else:
        primary_hits = hits[:8]

    # 统计命中域
    hit_domains = defaultdict(int)
    for h in primary_hits:
        ed = h.get('expert_domain', '?')
        hit_domains[ed] += 1
    print(f"   Filtered hits ({len(primary_hits)}): {dict(hit_domains)}")

    # 4. 实体抽取 + 图搜索
    entities = []
    patterns = [
        r"(马拉松|半马|全马|LTHR|T-Pace|VO2\s*max|乳酸阈|配速|心率|力量|恢复|营养|补给|间歇|长距离|比赛|跑步|跑量|跑姿|拉伸|核心|节奏跑|轻松跑|tempo|减量)",
        r"([A-Za-z][A-Za-z0-9\-/]{2,20})",
    ]
    for pat in patterns:
        for m in re.findall(pat, query, re.IGNORECASE):
            if m.strip() not in entities:
                entities.append(m.strip())

    # 也从命中 chunk 中提取 expert_domain 的实体
    for h in primary_hits[:5]:
        ed = h.get('expert_domain', '')
        if ed and ed not in entities:
            entities.append(ed)

    all_labels = []
    for n in engine.nodes.values():
        all_labels.append(n.get('label', ''))
        zh = n.get('label_zh', '')
        if zh: all_labels.append(zh)
    all_labels = sorted(set(l for l in all_labels if len(l)>=2), key=len, reverse=True)
    ql = query.lower()
    for label in all_labels:
        if len(entities) >= 8: break
        if label.lower() in ql and label not in entities:
            entities.append(label)

    # 5. 图 BFS
    graph_edges = []
    seen_eids = set()
    for ent in entities[:8]:
        sub = engine.search_graph([ent], max_hops=2)
        for e in sub.get('edges', []):
            eid = f"{e['source']}|{e['target']}|{e['relation']}"
            if eid not in seen_eids:
                seen_eids.add(eid)
                graph_edges.append(e)

    by_domain = defaultdict(list)
    for e in graph_edges:
        by_domain[e.get('expert_domain', '?')].append(e)

    print(f"   Entities: {entities[:6]}")
    print(f"   Graph edges: {len(graph_edges)} ({len(by_domain)} domains)")

    for domain, dom_edges in sorted(by_domain.items()):
        print(f"    [{domain}] ({len(dom_edges)} edges)")
        for e in dom_edges[:3]:
            src = engine.nodes.get(e['source'], {}).get('label_zh', e['source'])[:25]
            tgt = engine.nodes.get(e['target'], {}).get('label_zh', e['target'])[:25]
            rel = REL_CN.get(e['relation'], e['relation'])
            ev = e.get('evidence', {})
            src_file = (ev.get('source', '')[:20] if isinstance(ev, dict) else '').replace('_', ' ')
            bridge = f' [bridge:{e.get("bridge_type","")}]' if e.get('bridge_type') else ''
            print(f"      {src} ->[{rel}]-> {tgt}{bridge}  {src_file}")
    print()

# ─── 测试 ───
questions = [
    ("我膝盖外侧疼，还能继续跑步吗", "therapist"),
    ("全马想破3小时，赛前两周怎么减量", "coach"),
    ("跑步补剂肌酸有用吗", "nutritionist"),
    ("间歇跑一周安排几次比较好", "planner"),
    ("乳酸阈值跑应该用什么配速", "coach"),
    ("最近跑量增加后小腿前侧疼，是应力骨折吗", "therapist"),
]
for q, cat in questions:
    rag_pipeline(q, category=cat)
