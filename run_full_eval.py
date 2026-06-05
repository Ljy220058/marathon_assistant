"""完整检索评测：正例召回 + 反例检测"""
import json, sys
sys.path.insert(0, 'apps/backend/src')
from marathon_qa_assistant.services.vector_store import load_vector_kb, retrieve

# 加载已有
with open('eval_dataset_matched.json', encoding='utf-8') as f:
    existing = json.load(f)
with open('eval_chunks_extra_15.json', encoding='utf-8') as f:
    extra_chunks = json.load(f)

# 15条新正例 (从MCP生成结果)
new_positive = [
    {'question':'According to tapering studies, what combination of duration, intensity, frequency, and volume reduction is most effective?','ground_truth':'14-day duration with unchanged intensity and frequency but 41-60% volume reduction','domain':'training_protocol','sample_type':'positive'},
    {'question':'What are the four core categories of injury in the Running Injury Continuum?','ground_truth':'Twinge, persisting niggle, non-responding niggle, and short-term injury.','domain':'injury_safety','sample_type':'positive'},
    {'question':'How can runners manage overuse injuries?','ground_truth':'Continue running with altered technique, reduced load, or rest days. Self-management includes stretching. External management includes athletic therapists and physiotherapists.','domain':'injury_safety','sample_type':'positive'},
    {'question':'What is the ISSN position on nutrient timing?','ground_truth':'Nutrient timing involves purposeful ingestion of nutrients at various times throughout the day to favorably impact the adaptive response to exercise including muscle strength, body composition, and performance.','domain':'nutrition','sample_type':'positive'},
    {'question':'Why does the literature not provide clear direction on the most prevalent running injuries?','ground_truth':'Due to heterogeneity in injury definition, runner type, and injury classification across studies.','domain':'injury_safety','sample_type':'positive'},
    {'question':'What acute kidney conditions are observed during marathon training?','ground_truth':'Acute kidney injury (AKI) and acute tubular necrosis are observed, indicating marathon training presents extreme stress on the renal system.','domain':'medical_safety','sample_type':'positive'},
    {'question':'What are the benefits and risks of nutritional supplements for athletes?','ground_truth':'Benefits include assistance meeting sports nutrition goals, preventing deficiencies, placebo effect, and ergogenic effects. Risks include expense, ergolytic effects, and health and legal consequences.','domain':'nutrition','sample_type':'positive'},
    {'question':'What is a key risk factor for overuse injuries in short-distance runners?','ground_truth':'No previous running experience. Novice runners may build up training too quickly without allowing tissue adaptation. Running more than 60 min per week is protective.','domain':'injury_safety','sample_type':'positive'},
    {'question':'What is the objective of the training framework for elite middle-distance runners?','ground_truth':'To integrate scientific and best practice coaching literature into a novel framework for training and development of elite middle-distance performance.','domain':'training_protocol','sample_type':'positive'},
    {'question':'What did fitness app data reveal about training response groups?','ground_truth':'The high response group showed the highest improvement in 10km velocity while slightly decreasing mean heart rate. Effect sizes varied between groups.','domain':'training_protocol','sample_type':'positive'},
    {'question':'What does nutrition periodization involve for athletes?','ground_truth':'Integrating dietary strategies with training cycles. Different phases like base, build, competition, and recovery require different macronutrient ratios and energy availability.','domain':'nutrition','sample_type':'positive'},
    {'question':'What are the safe and risky Acute to Chronic Workload Ratio ranges?','ground_truth':'ACWR above 1.5 is associated with increased injury risk. A ratio between 0.8 and 1.3 is considered a safe training zone.','domain':'training_protocol','sample_type':'positive'},
    {'question':'What is running economy and what factors affect it?','ground_truth':'Running economy is the oxygen cost at a given submaximal running speed. Factors include metabolic, cardiorespiratory, biomechanical efficiency, and neuromuscular characteristics.','domain':'training_protocol','sample_type':'positive'},
    {'question':'What is the female athlete triad and what did it expand into?','ground_truth':'Low energy availability, menstrual dysfunction, and low bone mineral density. It expanded into RED-S which encompasses broader health consequences.','domain':'medical_safety','sample_type':'positive'},
    {'question':'What are the criteria for returning to running after an injury?','ground_truth':'Pain-free walking, pain-free strength testing, and ability to perform sport-specific movements without compensation. Progression is guided by symptom response.','domain':'injury_safety','sample_type':'positive'},
]

# 10条反例/边界
negatives = [
    {'question':'How do I write a for loop in Python?','ground_truth':'','domain':'','sample_type':'out_of_domain'},
    {'question':'What is the weather forecast for Tokyo tomorrow?','ground_truth':'','domain':'','sample_type':'out_of_domain'},
    {'question':'What are the best restaurants in Paris?','ground_truth':'','domain':'','sample_type':'out_of_domain'},
    {'question':'Explain quantum computing in simple terms','ground_truth':'','domain':'','sample_type':'out_of_domain'},
    {'question':'How do I fix a leaking kitchen faucet?','ground_truth':'','domain':'','sample_type':'out_of_domain'},
    {'question':'What is the plot of the movie Inception?','ground_truth':'','domain':'','sample_type':'out_of_domain'},
    {'question':'Can swimming help with my running performance?','ground_truth':'','domain':'','sample_type':'near_miss'},
    {'question':'I have a headache after my morning run, should I take ibuprofen?','ground_truth':'','domain':'','sample_type':'near_miss'},
    {'question':'How many calories are in a banana?','ground_truth':'','domain':'','sample_type':'near_miss'},
    {'question':'Is it safe to run if I have a cold?','ground_truth':'','domain':'medical_safety','sample_type':'near_miss'},
]

# 匹配新正例到extra_chunks
used = set(item.get('reference_chunk_id','') for item in existing if item.get('reference_chunk_id'))
for qa in new_positive:
    gt = qa['ground_truth'].lower()
    best_score = 0
    best = None
    for c in extra_chunks:
        if c['chunk_id'] in used:
            continue
        text = c['text'].lower()
        score = sum(1 for w in gt.split() if w in text) / max(1, len(gt.split()))
        if score > best_score:
            best_score = score
            best = c
    if best and best_score > 0.03:
        used.add(best['chunk_id'])
        qa['reference_chunk_id'] = best['chunk_id']
        qa['source_file'] = best['source_file']

# 合并
full = existing + new_positive + negatives
positives = [d for d in full if d.get('reference_chunk_id')]
neg_items = [d for d in full if d['sample_type'] in ('out_of_domain','near_miss') and not d.get('reference_chunk_id')]

# 加载向量库
chunks, vectorizer, matrix, bm25 = load_vector_kb('data/vector_kb/v2')
chunk_lookup = {c['chunk_id']: c for c in chunks if c.get('chunk_id')}

# 正例评测
exact = same_page = same_source = 0
for item in positives:
    ref_id = item['reference_chunk_id']
    hits = retrieve(item['question'], chunks, vectorizer, matrix, top_k=5, bm25=bm25)
    ids = [h['chunk_id'] for h in hits]
    ref = chunk_lookup.get(ref_id, {})
    ref_src = ref.get('source_file','')
    ref_page = ref.get('page',0)

    if ref_id in ids:
        exact += 1
    for h in hits:
        if h.get('source_file') == ref_src and h.get('page') == ref_page:
            same_page += 1
            break
    for h in hits:
        if h.get('source_file') == ref_src:
            same_source += 1
            break

n_pos = len(positives)
print('====== 检索质量评测报告 (v2, 最终版) ======')
print(f'正例数: {n_pos}  反例/边界: {len(neg_items)}  总计: {len(full)}')
print()
print(f'指标                  | 命中    | 得分')
print(f'精确片段召回@5        | {exact:3d}/{n_pos} | {exact/n_pos:.1%}')
print(f'同页召回@5            | {same_page:3d}/{n_pos} | {same_page/n_pos:.1%}')
print(f'同文档召回@5          | {same_source:3d}/{n_pos} | {same_source/n_pos:.1%}')

# 反例评测
neg_hit = 0
out_hits = 0
near_hits = 0
for item in neg_items:
    hits = retrieve(item['question'], chunks, vectorizer, matrix, top_k=5, bm25=bm25)
    if hits:
        neg_hit += 1
        if item['sample_type'] == 'out_of_domain':
            out_hits += 1
        else:
            near_hits += 1

n_neg = len(neg_items)
print(f'反例命中率            | {neg_hit:3d}/{n_neg} | {neg_hit/n_neg:.1%} (越低越好)')
print(f'  领域外查询命中      | {out_hits}/6 (纯不相干问题)')
print(f'  边界查询命中         | {near_hits}/4 (擦边问题)')
print()

# 按领域细分
for domain in ['training_protocol', 'nutrition', 'injury_safety', 'medical_safety']:
    items = [d for d in positives if d.get('domain') == domain]
    if not items: continue
    d_exact = sum(1 for item in items if item['reference_chunk_id'] in
        [h['chunk_id'] for h in retrieve(item['question'], chunks, vectorizer, matrix, top_k=5, bm25=bm25)])
    print(f'  {domain}: {d_exact}/{len(items)} = {d_exact/len(items):.1%}')

# 保存
with open('eval_dataset_final.json', 'w', encoding='utf-8') as f:
    json.dump(full, f, ensure_ascii=False, indent=2)
print(f'\n已保存 eval_dataset_final.json ({len(full)} 条)')
