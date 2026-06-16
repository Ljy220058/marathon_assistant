"""第二轮清洗：消除残留英文"""
import json, re

with open('data/vector_kb/v2/knowledge_graph.json', 'r', encoding='utf-8') as f:
    kg = json.load(f)
nodes = kg['nodes']

# 扩展翻译
MORE = {
    # 英文残留词
    'of the': '', ' of ': '', ' the ': ' ', ' a ': ' ', ' an ': '',
    ' for ': '用于', ' with ': '配合', ' without ': '无',
    'in ': '在', ' on ': '在', ' to ': '到', ' and ': '和',
    ' or ': '或', ' by ': '通过', ' per ': '每', ' from ': '来自',
    ' at ': '在', ' into ': '进入', ' within ': '在',
    # 后缀修正
    'ation': '', 's Supplement': '补充剂', ' addition': '', ' and comparison': '',
    # 具体词的翻译
    'older individuals': '老年人群',
    'increases': '增加', 'increase': '增加',
    'Incidence': '发生率', 'upper respiratory': '上呼吸道',
    'tract': '道', 'infections': '感染',
    'PA Supplement': '磷脂酸补充', 'supplementation': '补充',
    'Placebo': '安慰剂', 'placebo': '安慰剂',
    'group': '组', 'Group': '组',
    'whole-body': '全身', 'resistance': '抗阻', 'training': '训练',
    'doses': '剂量', 'Doses': '剂量',
    'exercise': '运动', 'Exercise': '运动',
    'core temperature': '核心温度', 'regulation': '调节',
    'sweat rate': '出汗率', 'sweat': '出汗',
    'heat': '热', 'Heat': '热',
    'middle-distance': '中距离', 'running events': '跑步项目',
    'intensity': '强度', 'Intensity': '强度',
    'setting HIT': '设置高强度训练', 'match race pace': '匹配比赛配速',
    'pre-competition': '赛前', 'Competition': '比赛',
    'Step': '阶梯式', 'step': '阶梯式',
    'Progressive': '渐进式', 'progressive': '渐进式',
    'fast-decay': '快速衰减', 'decay': '衰减', 'pattern': '模式',
    'pre-taper overload': '减量前超负荷',
    'Training load reduction': '训练负荷减少', 'range': '范围',
    'reduction': '减少', 'Reduction': '减少',
    'duration': '持续时间', 'Duration': '持续时间',
    'Carbohydrate delivery': '碳水化合物输送',
    'dependence on carbohydrates for athletes': '运动员对碳水化合物的依赖',
    "athletes' dependence on carbohydrates": '运动员对碳水化合物的依赖',
    'carbohydrate type': '碳水化合物类型', 'carbohydrate': '碳水化合物',
    'Carbohydrate': '碳水化合物', 'athletes': '运动员',
    'Athletes': '运动员', 'consideration': '考虑',
    'precedence over other strategies': '优先于其他策略',
    'resistance training': '抗阻训练',
    'Running': '跑步', 'Economy': '经济性', 'economy': '经济性',
    'Biomechanics': '生物力学', 'biomechanics': '生物力学',
    'Interval': '间歇', 'Prescription': '处方', 'Dose-Response': '剂量反应',
    'Time-Trial': '计时赛', 'Performance': '表现', 'Improvement': '改善',
    'Periodization': '周期化', 'Elite': '精英', 'Reverse': '逆向',
    'Factors': '因素', 'Affecting': '影响', 'Recreational': '业余',
    'Endurance': '耐力', 'Runners': '跑者', 'Runners.': '跑者',
    'high': '高', 'higher': '更高', 'Higher': '更高',
    'muscle protein synthesis': '肌肉蛋白质合成',
    'daily': '每日', 'Daily': '每日',
    'fat-free mass': '去脂体重', 'Lean Body': '瘦体重',
    'Mass': '量', 'mass': '量',
    'older': '老年', 'individuals': '人群',
    'g/kg/day': '克/公斤/天',
    'vitamin C': '维生素C', 'Vitamin C': '维生素C',
    'immunity': '免疫力', 'Immunity': '免疫力',
    'Likelihood': '可能性', 'of Injury': '受伤',
    'classification into': '分类为', 'subcategory': '子类',
    'subgroup': '子组', 'subcategory': '子类',
    'PFP IMPAIRMENT': '髌股疼痛损伤', 'FUNCTION-BASED': '功能导向',
    'CLASSIFICATION': '分类', 'IMPAIRMENT': '损伤',
    'Function-based': '功能导向',
    'history of increased': '有增加的历史', 'PFJ loading': '髌股关节负荷',
    'loading': '负荷', 'Loading': '负荷',
    'Total': '总', 'weekly': '每周', 'distance': '距离',
    'rapid change': '快速变化', 'in weekly': '每周内',
    'GPS variables': 'GPS变量', 'GPS': 'GPS',
    'variables': '变量', 'Internal': '内部', 'external': '外部',
    'load metrics': '负荷指标', 'metrics': '指标',
    'High-intensity': '高强度', 'Moderate-intensity': '中等强度',
    'Low-intensity': '低强度',
    'Body Mass': '体重', 'Body mass': '体重',
    'Index': '指数', 'index': '指数',
    'Score': '评分', 'score': '评分',
    'Rate': '率', 'rate': '率',
    'Time': '时间', 'time': '时间',
    'Total time': '总时间',
    'Session': '课次', 'session': '课次',
    'Week': '周', 'week': '周', 'Week.': '周',
    'Study': '研究', 'study': '研究',
    'Control': '对照', 'control': '对照',
    'Group': '组', 'group': '组',
    'Model': '模型', 'model': '模型',
    'Type': '类型', 'type': '类型',
    'Level': '水平', 'level': '水平',
    'Phase': '阶段', 'phase': '阶段',
    'Cycle': '周期', 'cycle': '周期',
    'Block': '板块', 'block': '板块',
    'Workload': '工作量', 'workload': '工作量',
    'Specific': '专项', 'specific': '专项',
    'General': '一般', 'general': '一般',
    'Preparation': '准备期', 'preparation': '准备期',
    'Competitive': '比赛期', 'competitive': '比赛期',
    'Transition': '过渡期', 'transition': '过渡期',
    'Additional': '额外的',
    'Active': '主动', 'active': '主动',
    'Passive': '被动', 'passive': '被动',
    'Dynamic': '动态', 'static': '静态',
    'Maximal': '最大', 'maximal': '最大',
    'Submaximal': '次最大', 'submaximal': '次最大',
    'Peak': '峰值', 'peak': '峰值',
    'Mean': '平均', 'mean': '平均',
    'Minimum': '最小', 'minimum': '最小',
    'Maximum': '最大', 'maximum': '最大',
    'Average': '平均', 'average': '平均',
    'Absolute': '绝对', 'absolute': '绝对',
    'Relative': '相对', 'relative': '相对',
    'Individual': '个体', 'individual': '个体',
    'Total training time': '总训练时间',
    'Endurance training interventions': '耐力训练干预',
    'Achieving peak performance': '达到峰值表现',
    'performance.': '表现',
}

def clean_zh(zh):
    """清洗混合中英文标签"""
    # 去掉首尾空白
    zh = zh.strip()
    # 去掉多余空格
    zh = re.sub(r'\s+', ' ', zh)
    # 替换已知残留词
    for en, cn in sorted(MORE.items(), key=lambda x: -len(x[0])):
        zh = zh.replace(en, cn)
    # 去掉残留的英文括号内容
    zh = re.sub(r'\([A-Z][A-Za-z\s]+\)', '', zh)
    # 单独残留的英文单词（>3字母，不在中文语境中）
    # 如果连续英文超过2个单词且旁边有中文，尝试清理
    zh = re.sub(r'\b(the|of|and|or|in|on|to|by|for|with|from|at|as|an|a|is|are|was|were|be|has|have|had|not|but|if|than|that|this|these|those|it|its|they|their|them)\b', '', zh)
    zh = re.sub(r'\s+', ' ', zh).strip()
    # 去掉首尾残留的标点和空格
    zh = zh.strip(' ,.()[]{}:;')
    return zh

cleaned = 0
for nid, n in nodes.items():
    zh = n.get('label_zh', '')
    if not zh:
        continue
    new_zh = clean_zh(zh)
    if new_zh != zh:
        n['label_zh'] = new_zh
        cleaned += 1

with open('data/vector_kb/v2/knowledge_graph.json', 'w', encoding='utf-8') as f:
    json.dump(kg, f, ensure_ascii=False, indent=2)

# 检查剩余的混合标签
mixed_after = 0
for nid, n in nodes.items():
    zh = n.get('label_zh', '')
    if not zh:
        continue
    has_zh = any('一' <= c <= '鿿' for c in zh)
    has_en = any(c.isalpha() and ord(c) < 128 for c in zh)
    if has_zh and has_en:
        mixed_after += 1

print(f'Cleaned: {cleaned} labels')
print(f'Remaining mixed: {mixed_after}/{len(nodes)}')

# 抽样检查 rehab 和 race 域
for domain in ['rehab_safety', 'race_strategy', 'nutrition']:
    samples = []
    for nid, n in nodes.items():
        if n.get('expert_domain') == domain:
            zh = n.get('label_zh', '')
            if zh:
                samples.append(zh)
    print(f'\n{domain} samples:')
    for s in sorted(set(samples))[:5]:
        has_en = any(c.isalpha() and ord(c) < 128 for c in s)
        flag = ' [EN]' if has_en else ''
        print(f'  {s[:55]}{flag}')
