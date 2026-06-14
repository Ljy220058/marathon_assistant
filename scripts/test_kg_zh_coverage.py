"""中文 KG 完备性测试"""
import json
from collections import Counter, defaultdict

with open('data/vector_kb/v2/knowledge_graph.json', 'r', encoding='utf-8') as f:
    kg = json.load(f)
nodes = kg['nodes']
edges = kg['edges']

# 按域收集 label_zh
by_domain_zh = defaultdict(list)
for nid, n in nodes.items():
    zh = n.get('label_zh', n.get('label', ''))
    if zh and zh != '?':
        d = n.get('expert_domain', '?')
        by_domain_zh[d].append(zh)

tests = {
    'rehab_safety': {
        'keywords': ['膝', '疼', '损伤', '炎', '跟腱', '应力', '足底', '筋膜',
                     '肌肉', '恢复', '负荷', '风险', '受伤', '过度使用', '肌腱',
                     '疼痛', '胫骨', '筋膜炎', '髋', '踝'],
        'scenarios': ['膝盖外侧疼', '跟腱炎恢复', '足底筋膜炎跑步', '应力骨折判断',
                     '肌肉拉伤怎么办', 'ITBS还能跑吗'],
    },
    'race_strategy': {
        'keywords': ['配速', '减量', '赛前', '热适应', '寒冷', '补给', '比赛',
                     '策略', 'taper', '碳水', '补水', '马拉松', '天气'],
        'scenarios': ['全马配速策略', '赛前两周减量', '热天比赛准备', '比赛补给时机'],
    },
    'nutrition': {
        'keywords': ['碳水', '蛋白质', '补剂', '肌酸', '维生素', '铁', '营养',
                     '补给', '水合', '摄入', '剂量', '饮食'],
        'scenarios': ['赛前碳水加载', '蛋白质每天吃多少', '肌酸对跑步有用吗',
                     '铁补充剂', '比赛怎么补给'],
    },
    'training_theory': {
        'keywords': ['乳酸', '阈值', '间歇', '最大摄氧量', '极化', '周期',
                     '强度', '跑步', '训练', '恢复', '高强度', '耐力'],
        'scenarios': ['乳酸阈值训练', '间歇跑怎么设计', 'VO2max怎么提高',
                     '极化训练是什么', '周期化训练安排'],
    },
    'workout_prescription': {
        'keywords': ['课', '模板', '跑步', '恢复', '长距离', '间歇', '节奏',
                     '训练', '计划', '配速', '区间', '强度'],
        'scenarios': ['周课表怎么排', '强度课设计', '恢复跑配速'],
    },
    'capacity_management': {
        'keywords': ['周', '容量', '上限', '限制', '恢复', '间隔', '强度'],
        'scenarios': ['每周几个强度课', '跑量上限', '恢复间隔'],
    },
}

def fuzzy(label, kws):
    for kw in kws:
        if kw in label:
            return True
    return False

results = {}
for domain, info in tests.items():
    labels = by_domain_zh.get(domain, [])
    matched = [l for l in labels if fuzzy(l, info['keywords'])]
    dom_edges = [e for e in edges if e.get('expert_domain') == domain]
    rels = set(e['relation'] for e in dom_edges)

    # 场景覆盖率：看每个场景是否能找到相关实体
    scenario_hits = 0
    for s in info['scenarios']:
        if any(fuzzy(l, s) for l in labels):
            scenario_hits += 1

    sc_total = len(info['scenarios'])
    sc_pct = scenario_hits * 100 // sc_total if sc_total else 0

    results[domain] = {
        'nodes': len(labels),
        'matched': len(matched),
        'edges': len(dom_edges),
        'rels': len(rels),
        'scenarios': f'{scenario_hits}/{sc_total} ({sc_pct}%)',
    }

print(f"{'Domain':25s} {'Nodes':>5s} {'Matched':>7s} {'Edges':>5s} {'Rels':>4s} {'Scenarios':>12s} {'Grade'}")
print('-' * 75)
grades = {}
for domain, r in results.items():
    m = r['matched']
    s = int(r['scenarios'].split('/')[0])
    st = int(r['scenarios'].split('/')[1].split()[0])

    if m >= 15 and s >= st - 1:
        grade = 'A'
    elif m >= 10 and s >= st // 2:
        grade = 'B'
    elif m >= 5:
        grade = 'C'
    else:
        grade = 'D'
    grades[domain] = grade

    print(f"{domain:25s} {r['nodes']:5d} {r['matched']:7d} {r['edges']:5d} {r['rels']:4d} {r['scenarios']:>12s}     {grade}")

# 按域展示命中的实体
for domain, info in tests.items():
    labels = by_domain_zh.get(domain, [])
    matched = [l for l in labels if fuzzy(l, info['keywords'])]
    print(f"\n{domain} ({len(matched)}/{len(labels)}):")
    for l in matched[:6]:
        print(f"  {l[:55]}")

print(f"\n=== Overall ===")
print(f"A: {sum(1 for g in grades.values() if g=='A')}  B: {sum(1 for g in grades.values() if g=='B')}  C: {sum(1 for g in grades.values() if g=='C')}  D: {sum(1 for g in grades.values() if g=='D')}")
