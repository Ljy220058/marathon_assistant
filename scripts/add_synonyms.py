"""给实体添加跑者常用同义词别名"""
import json

with open('data/vector_kb/v2/knowledge_graph.json', 'r', encoding='utf-8') as f:
    kg = json.load(f)
nodes = kg['nodes']

# 同义词映射：跑者常用说法 → KG 实体关键词
SYNONYMS = {
    # 膝盖/腿痛
    'pain': ['疼', '痛', '酸痛', '不适'],
    '疼痛': ['疼', '痛', '酸痛', '不适'],
    '膝盖': ['膝', '膝关节', '膝部', '髌骨'],
    '外侧': ['外侧膝', '侧面', 'ITBS', 'ITB', '髂胫束'],
    '小腿': ['胫骨', '胫', '小腿前侧', '小腿后侧'],
    '腿': ['腿部', '下肢'],
    # 应力骨折
    'stress fracture': ['应力骨折', '应力性骨折', '疲劳骨折', '骨裂'],
    '应力骨折': ['应力性骨折', '疲劳骨折'],
    '胫骨': ['小腿骨', '胫骨前侧', 'shin'],
    # 间歇训练
    '间歇': ['间歇跑', '间歇训练', '短间歇', '长间歇', '跑道间歇'],
    'interval': ['间歇跑', '间歇训练', '短间歇', '长间歇'],
    'HIIT': ['高强度间歇', '高强度间歇跑', '高强度训练'],
    '高强度间歇训练': ['高强度间歇跑', 'HIIT跑', '间歇冲刺'],
    # 跑量
    '跑量': ['周跑量', '训练量', '里程', '跑量增加', '加量'],
    '周跑量': ['周跑量', '每周跑量', '周里程'],
    '训练量': ['训练负荷', '训练容量'],
    # 休息/恢复
    '恢复': ['休息', '恢复日', '轻松跑', '恢复跑'],
    '休息': ['恢复日', '休息日', '休跑'],
    # 频率
    '频率': ['几次', '每周几次', '一周几次', '安排', '每周安排'],
    '几次': ['多少次', '频率', '每周几次'],
    # 跑步通用
    '跑步': ['跑', '跑步', '慢跑', '长跑', '训练'],
    '跑': ['跑步', '训练', '慢跑'],
    '继续': ['能不能', '可以吗', '还能继续'],
    # 负荷
    '负荷': ['训练负荷', '跑量', '强度', '训练量'],
    '训练负荷': ['训练量', '负荷', '训练压力'],
    # 损伤风险
    '受伤风险': ['受伤', '损伤风险', '受伤可能', '伤病风险'],
    '损伤': ['受伤', '伤病', '伤害'],
    # 肌酸
    '肌酸': ['肌酸补剂', '肌酸补充', 'creatine补剂'],
    # 减量
    '减量': ['减量期', '赛前减量', '减少训练', '削减跑量'],
    # 配速
    '配速': ['配速策略', 'pace', '目标配速'],
    # 碳水和营养
    '碳水': ['碳水化合物', '糖原', '碳', 'CHO'],
    '蛋白质': ['蛋白', 'protein', '蛋白质摄入'],
}

# 为每个节点添加同义词别名
# 把同义词追加到 label_zh 后面
added = 0
for nid, n in nodes.items():
    zh = n.get('label_zh', '')
    en = n.get('label', '')
    if not zh:
        continue

    # 检查 label_zh 包含哪些关键词，添加对应的同义词
    extra_terms = set()
    for keyword, synonyms in SYNONYMS.items():
        # 如果 label_zh 或 label 包含该关键词
        if keyword.lower() in zh.lower() or keyword.lower() in en.lower():
            for syn in synonyms:
                if syn not in zh and syn not in en.lower():
                    extra_terms.add(syn)

    if extra_terms:
        # 追加到 label_zh（用空格分隔）
        n['label_zh'] = zh + ' ' + ' '.join(extra_terms)
        added += 1

with open('data/vector_kb/v2/knowledge_graph.json', 'w', encoding='utf-8') as f:
    json.dump(kg, f, ensure_ascii=False, indent=2)

print(f'Added synonyms to {added} nodes')

# 验证
tests = ['膝盖', '外侧', '疼', '腿', '小腿', '应力骨折', '间歇跑', '休息', '几次', '跑量']
for t in tests:
    hits = sum(1 for n in nodes.values()
               if t in (n.get('label','') + ' ' + n.get('label_zh','')).lower())
    print(f'  "{t}": {hits} hits')
