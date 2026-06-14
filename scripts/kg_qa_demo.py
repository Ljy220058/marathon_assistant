"""KG QA demo: search KG with real runner questions"""
import json, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from collections import defaultdict

with open('data/vector_kb/v2/knowledge_graph.json', 'r', encoding='utf-8') as f:
    kg = json.load(f)
nodes = kg['nodes']
edges = kg['edges']

def match_entities(query, top_n=10):
    """用中文关键词匹配 KG 实体——N-gram滑动窗口"""
    q = query.lower()
    scores = []

    # 提取中文 n-gram (2-5字)
    tokens = set()
    for n in range(2, 6):
        for i in range(len(q) - n + 1):
            tok = q[i:i+n]
            # 跳过纯标点/数字
            if re.match(r'^[\x00-\x7f\s\d\.\,\;\:\!\?\(\)\[\]\{\}]+$', tok):
                continue
            tokens.add(tok)
    # 也加英文分词
    tokens.update(w.lower() for w in re.findall(r'[a-zA-Z]+', q) if len(w) >= 2)

    for nid, n in nodes.items():
        label = n.get('label', '')
        label_zh = n.get('label_zh', label)
        combined = f"{label} {label_zh}".lower()
        score = 0
        for tok in tokens:
            if tok in combined:
                score += len(tok)  # 长匹配权重更高
        if score >= 3:
            domain = n.get('expert_domain', '?')
            scores.append((score, label_zh[:50], label[:40], domain, nid))
    scores.sort(key=lambda x: -x[0])
    return scores[:top_n]

def get_connected_edges(entity_nid, max_hops=1):
    """获取实体周围的边"""
    visited = {entity_nid}
    result_edges = []
    result_nodes = {entity_nid}

    for hop in range(max_hops):
        new_edges = []
        for e in edges:
            if e['source'] in visited or e['target'] in visited:
                if e['source'] not in result_nodes or e['target'] not in result_nodes:
                    new_edges.append(e)
                    result_nodes.add(e['source'])
                    result_nodes.add(e['target'])
        result_edges.extend(new_edges)
        visited.update(result_nodes)

    return result_edges, result_nodes

def format_evidence(edges_list, entity_nodes, max_show=8):
    """格式化证据为可读文本"""
    if not edges_list:
        return "（知识图谱中未找到相关证据）"

    lines = []
    for e in edges_list[:max_show]:
        src_zh = nodes.get(e['source'], {}).get('label_zh', nodes.get(e['source'], {}).get('label', '?'))[:30]
        tgt_zh = nodes.get(e['target'], {}).get('label_zh', nodes.get(e['target'], {}).get('label', '?'))[:30]
        rel = e['relation']
        domain = e.get('expert_domain', '?')
        ev = e.get('evidence', {})
        src_file = ev.get('source', '')[:35] if isinstance(ev, dict) else ''
        bridge = e.get('bridge_type', '')

        # 关系中文名
        rel_cn = {'improves': '改善', 'reduces': '减少', 'risks': '增加风险',
                  'requires': '需要', 'supports': '促进', 'adjusts': '调节',
                  'constrains': '约束', 'bridges_to': '桥接'}
        rel_str = rel_cn.get(rel, rel)

        line = f"  {src_zh} →[{rel_str}]→ {tgt_zh}"
        if bridge:
            line += f" [跨域:{bridge}]"
        if src_file and src_file != 'decision_graph_registry':
            line += f" ({src_file})"
        lines.append(line)
    return '\n'.join(lines)

# ─── 问答演示 ───
questions = [
    ("我膝盖外侧疼，还能继续跑步吗？", "康复安全 (rehab_safety)",
     "这是一个典型的外侧膝痛问题，可能涉及ITBS。系统需要检索伤病机制 + 风险证据 + 替代建议。"),
    ("全马想破3小时，赛前两周怎么减量？", "比赛策略 (race_strategy)",
     "减量是比赛策略的核心问题。系统需要命中减量相关的训练证据 + 比赛配速策略。"),
    ("跑步补剂肌酸有用吗？安全吗？", "营养 (nutrition)",
     "补剂问题是营养域常见查询。系统需要检索肌酸的改善效果 + 风险证据。"),
    ("间歇跑一周安排几次比较好？", "训练处方 + 容量管理 (workout_prescription + capacity_management)",
     "训练频率问题涉及处方和容量管理两个域。系统应命中强度课约束 + 间歇训练设计。"),
    ("乳酸阈值跑应该用什么配速和距离？", "训练理论 (training_theory)",
     "阈值训练是训练理论的核心话题。系统需要检索乳酸阈值相关的生理证据 + 训练参数。"),
    ("最近跑量增加后小腿前侧疼，是不是应力骨折？", "康复安全 + 容量管理 (rehab_safety + capacity_management)",
     "这是一个跨域问题：康复域需要应力骨折识别证据，容量域需要负荷-损伤风险证据。"),
]

for q, expected_domain, context in questions:
    print("=" * 70)
    print(f"跑者提问：{q}")
    print(f"期望领域：{expected_domain}")
    print(f"背景：{context}")
    print()

    # 实体匹配
    entities = match_entities(q, top_n=5)
    print("* 命中的知识实体：")
    if not entities:
        print("  （未匹配到实体）")
        print()
        continue

    for score, zh_label, en_label, domain, nid in entities:
        print(f"  [{domain:25}] {zh_label[:45]}")

    # 取前3个实体做图遍历
    all_edges = []
    seen_edge_ids = set()
    for _, _, _, _, nid in entities[:3]:
        sub_edges, _ = get_connected_edges(nid, max_hops=1)
        for e in sub_edges:
            eid = f"{e['source']}|{e['target']}|{e['relation']}"
            if eid not in seen_edge_ids:
                seen_edge_ids.add(eid)
                all_edges.append(e)

    # 按域分组展示
    by_domain = defaultdict(list)
    for e in all_edges:
        by_domain[e.get('expert_domain', '?')].append(e)

    print()
    for domain, dom_edges in sorted(by_domain.items()):
        print(f"* {domain} 证据（{len(dom_edges)}条）：")
        print(format_evidence(dom_edges, set(), max_show=6))
        print()

    print()

# 汇总
print("=" * 70)
print("知识图谱统计：")
print(f"  总节点：{len(nodes)}  总边：{len(edges)}")
from collections import Counter
domains = Counter(n.get('expert_domain', '?') for n in nodes.values())
for d, c in sorted(domains.items()):
    print(f"  {d}: {c} nodes")
rels = Counter(e['relation'] for e in edges)
print(f"  关系类型：{dict(rels)}")
bridges = sum(1 for e in edges if e['relation'] == 'bridges_to')
print(f"  桥接边：{bridges}")
