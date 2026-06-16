"""完整 RAG 查询：从问题到证据的端到端输出"""
import json, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'apps/backend/src')

from pathlib import Path
from collections import defaultdict
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from marathon_qa_assistant.services.vector_store import load_chunks
from marathon_qa_assistant.services.knowledge_graph import graph_engine as engine
from marathon_qa_assistant.nodes.common import infer_entities
from marathon_qa_assistant.nodes.profile_and_retrieval import (
    _intent_domain_policy, _expert_domain_policy,
    filter_hits_for_intent_domain, _hit_domain_values,
)

# 加载
embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url="http://localhost:11434")
faiss_store = FAISS.load_local("data/vector_kb/v2/faiss_db", embeddings, allow_dangerous_deserialization=True)
chunks = load_chunks(Path("data/vector_kb/v2/chunks.jsonl"))
chunk_map = {c['chunk_id']: c for c in chunks}

REL_CN = {'improves': '改善', 'reduces': '减少', 'risks': '增加风险',
          'requires': '需要', 'supports': '促进', 'adjusts': '调节',
          'constrains': '约束', 'bridges_to': '桥接'}

query = "我膝盖外侧疼，还能继续跑步吗"
category = "therapist"

print(f"提问: {query}")
print(f"分类: {category}")
print()

# 1. 意图域策略
policy_name, policy = _intent_domain_policy(category=category, query=query)
if policy:
    print(f"[意图域策略] {policy_name} → evidence_domains={policy['domains']}")
else:
    print(f"[意图域策略] 默认 coach → {_expert_domain_policy('coach')}")

# 2. 实体抽取（动态加载 KG 标签）
entities = infer_entities(query)
print(f"[实体抽取] {entities}")

# 3. FAISS 向量检索
docs = faiss_store.similarity_search(query, k=15)
raw_hits = []
for d in docs:
    cid = d.metadata.get('chunk_id', '')
    c = chunk_map.get(cid, {})
    raw_hits.append({
        'chunk_id': cid, 'expert_domain': c.get('expert_domain',''),
        'evidence_domain': c.get('evidence_domain',''),
        'source_file': c.get('source_file','')[:45],
        'page': c.get('page',''),
        'text': d.page_content[:120]
    })

# 4. 域过滤
if policy:
    filtered = filter_hits_for_intent_domain(raw_hits, category=category, query=query, top_k=8)
else:
    filtered = raw_hits[:8]

print(f"\n[向量检索] {len(raw_hits)} → 域过滤后 {len(filtered)}:")
hit_domains = defaultdict(int)
for h in filtered:
    ed = h.get('expert_domain', '?')
    hit_domains[ed] += 1
print(f"  域分布: {dict(hit_domains)}")
for i, h in enumerate(filtered[:5]):
    print(f"  [{i+1}] [{h['expert_domain']}] {h['source_file'][:30]} p{h['page']} | {h['text'][:80]}")

# 5. 图搜索
graph_edges = []
seen_eids = set()
for ent in entities[:5]:
    sub = engine.search_graph([ent], max_hops=2)
    for e in sub.get('edges', []):
        eid = f"{e['source']}|{e['target']}|{e['relation']}"
        if eid not in seen_eids:
            seen_eids.add(eid)
            graph_edges.append(e)

by_domain = defaultdict(list)
for e in graph_edges:
    by_domain[e.get('expert_domain', '?')].append(e)

print(f"\n[图搜索] {len(graph_edges)} 条边 / {len(by_domain)} 个域:")
for domain in sorted(by_domain.keys()):
    dom_edges = by_domain[domain]
    print(f"\n  {domain} ({len(dom_edges)} 条):")
    for e in dom_edges[:5]:
        src = engine.nodes.get(e['source'], {}).get('label_zh', e['source'])[:30]
        tgt = engine.nodes.get(e['target'], {}).get('label_zh', e['target'])[:30]
        rel = REL_CN.get(e['relation'], e['relation'])
        ev = e.get('evidence', {})
        sf = (ev.get('source', '')[:25] if isinstance(ev, dict) else '')
        bridge = f' [跨域:{e.get("bridge_type","")}]' if e.get('bridge_type') else ''
        confidence = e.get('confidence', e.get('evidence', {}).get('confidence', '')) if isinstance(e.get('evidence'), dict) else ''
        print(f"    {src} →[{rel}]→ {tgt}{bridge}  ({sf})")
    if len(dom_edges) > 5:
        print(f"    ... 及 {len(dom_edges)-5} 条")

print(f"\n{'='*50}")
print(f"KG: {len(engine.nodes)} 节点 / {len(engine.edges)} 边 / FAISS: {len(chunks)} chunks")
