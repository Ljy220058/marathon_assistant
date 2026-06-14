"""给 KG 英文节点添加中文别名 label_zh"""
import json, re

with open('data/vector_kb/v2/knowledge_graph.json', 'r', encoding='utf-8') as f:
    kg = json.load(f)
nodes = kg['nodes']

TRANSLATIONS = {
    # 训练负荷与伤病
    'Training Load': '训练负荷', 'training load': '训练负荷',
    'high absolute training loads': '高绝对训练负荷',
    'Injury risk': '受伤风险', 'Injury': '损伤', 'injury': '损伤',
    'injuries': '损伤', 'injury risk': '受伤风险', 'injury rates': '损伤率',
    'Likelihood of Injury': '受伤概率', 'pain': '疼痛', 'Pain': '疼痛',
    'risk of injury': '受伤风险', 'greater injury risk': '更高受伤风险',
    'risk': '风险', 'Risk': '风险',
    # 跑步力学与康复
    'running mechanics': '跑步力学', 'function': '功能', 'Function': '功能',
    'movement': '运动动作', 'practitioners': '从业者',
    'exercise therapy': '运动疗法', 'rehabilitation': '康复',
    'recovery': '恢复', 'hamstring': '腘绳肌', 'quadriceps': '股四头肌',
    'knee': '膝盖', 'hip': '髋关节', 'ankle': '踝关节',
    'tendon': '肌腱', 'Tendon': '肌腱', 'tendinopathy': '肌腱病',
    'Tendinopathy': '肌腱病', 'achilles': '跟腱', 'Achilles': '跟腱',
    'Achilles tendon': '跟腱', 'plantar': '足底', 'Plantar': '足底',
    'Fasciitis': '筋膜炎', 'fasciitis': '筋膜炎',
    'stress fracture': '应力骨折', 'tibial': '胫骨', 'Tibial': '胫骨',
    'overuse': '过度使用', 'Overuse': '过度使用', 'overload': '超负荷',
    # 训练
    'training': '训练', 'Training': '训练', 'strength training': '力量训练',
    'resistance training': '抗阻训练', 'exercise': '运动', 'Exercise': '运动',
    'Running': '跑步', 'running': '跑步', 'runner': '跑者', 'athlete': '运动员',
    'endurance': '耐力', 'Endurance': '耐力', 'performance': '表现',
    'Performance': '表现', 'adaptation': '适应', 'fatigue': '疲劳',
    # 训练方法
    'HIIT': '高强度间歇训练', 'interval training': '间歇训练',
    'interval': '间歇', 'tempo': '节奏跑', 'sprint': '冲刺',
    'plyometric': '增强式训练', 'warm-up': '热身', 'cool-down': '冷身',
    # 生理
    'VO2max': '最大摄氧量', 'vo2max': '最大摄氧量',
    'lactate': '乳酸', 'Lactate': '乳酸', 'threshold': '阈值',
    'Threshold': '阈值', 'muscle': '肌肉', 'Muscle': '肌肉',
    'strength': '力量', 'Strength': '力量', 'power': '功率',
    'Power': '功率', 'aerobic': '有氧', 'anaerobic': '无氧',
    'heart rate': '心率', 'blood': '血液',
    # 营养
    'protein': '蛋白质', 'Protein': '蛋白质',
    'carbohydrate': '碳水化合物', 'Carbohydrate': '碳水化合物',
    'CHO': '碳水化合物', 'supplement': '补剂', 'Supplement': '补剂',
    'creatine': '肌酸', 'Creatine': '肌酸', 'vitamin': '维生素',
    'Vitamin': '维生素', 'iron': '铁', 'Iron': '铁',
    'nutrition': '营养', 'Nutrition': '营养', 'hydration': '水合',
    'fuel': '补给', 'diet': '饮食', 'intake': '摄入',
    'ingestion': '摄入', 'dose': '剂量', 'dosage': '剂量',
    # 比赛策略
    'taper': '赛前减量', 'Taper': '赛前减量', 'tapering': '赛前减量',
    'Tapering': '赛前减量', 'pacing': '配速策略', 'Pacing': '配速策略',
    'race': '比赛', 'Race': '比赛', 'competition': '比赛',
    'marathon': '马拉松', 'heat acclimation': '热适应',
    'cold': '寒冷', 'weather': '天气', 'hydration strategy': '补水策略',
    # 训练处方
    'polarized training': '极化训练', 'intensity': '强度',
    'Intensity': '强度', 'zone': '区间', 'Zone': '区间',
    'volume': '训练量', 'Volume': '训练量', 'frequency': '频率',
    'Frequency': '频率', 'duration': '持续时间', 'repetition': '重复',
    # 适应与变化
    'improves': '改善', 'reduces': '减少', 'increases': '增加',
    'decreases': '降低', 'change': '变化', 'effect': '效果',
    'response': '反应', 'Improves': '改善', 'Reduces': '减少',
    # 其他常见
    'body mass': '体重', 'body weight': '体重',
    'lean body mass': '瘦体重', 'fat-free mass': '去脂体重',
    'muscle mass': '肌肉量', 'bone': '骨骼', 'bone density': '骨密度',
    'sleep': '睡眠', 'stress': '压力', 'psychology': '心理',
    'immune': '免疫', 'immunity': '免疫力', 'inflammation': '炎症',
    'antioxidant': '抗氧化', 'oxidative': '氧化', 'glycogen': '糖原',
    'glucose': '葡萄糖', 'electrolyte': '电解质', 'sodium': '钠',
    'caffeine': '咖啡因', 'nitrate': '硝酸盐', 'beta-alanine': 'β-丙氨酸',
    'bicarbonate': '碳酸氢盐',
}

def is_english(text):
    chinese = sum(1 for c in text if '一' <= c <= '鿿')
    return chinese == 0 and any(c.isalpha() for c in text)

def translate(label):
    if label in TRANSLATIONS:
        return TRANSLATIONS[label]
    ll = label.lower()
    for k, v in sorted(TRANSLATIONS.items(), key=lambda x: -len(x[0])):
        if k.lower() in ll:
            label = label.replace(k, v)
    return label if label != TRANSLATIONS.get(label, '') else label

translated = 0
for nid, n in nodes.items():
    label = n.get('label', '')
    if not label or label == '?':
        continue
    if is_english(label):
        zh = translate(label)
        # 只保留有意义的中文翻译（含中文字符）
        if any('一' <= c <= '鿿' for c in zh):
            n['label_zh'] = zh
            translated += 1
        else:
            n['label_zh'] = label  # 兜底：保留英文
    else:
        n['label_zh'] = label

# 对已翻译的，也确保 label_en
for nid, n in nodes.items():
    label = n.get('label', '')
    if label and not is_english(label):
        # 中文节点设英文（如果已有翻译则跳过）
        n.setdefault('label_en', label)

with open('data/vector_kb/v2/knowledge_graph.json', 'w', encoding='utf-8') as f:
    json.dump(kg, f, ensure_ascii=False, indent=2)

has_zh = sum(1 for n in nodes.values() if n.get('label_zh'))
print(f'Translated: {translated} / Total with label_zh: {has_zh}/{len(nodes)}')
