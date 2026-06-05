"""分析检索分数分布：为什么相关内容得低分？"""
import json, sys
sys.path.insert(0, 'apps/backend/src')
from marathon_qa_assistant.services.vector_store import load_vector_kb, retrieve, _build_query_variants

chunks, vectorizer, matrix, bm25 = load_vector_kb('data/vector_kb/v2')
chunk_lookup = {c['chunk_id']: c for c in chunks if c.get('chunk_id')}

with open('eval_dataset_matched.json', encoding='utf-8') as f:
    dataset = json.load(f)

# 只分析有 ref_id 的正例
positives = [d for d in dataset if d.get('reference_chunk_id')]

print(f'分析 {len(positives)} 条正例的检索分数分布\n')

hits_analyzed = 0
low_score_relevant = 0
missed_relevant = 0

for item in positives:
    ref_id = item['reference_chunk_id']
    question = item['question']
    domain = item.get('domain', '')

    hits = retrieve(question, chunks, vectorizer, matrix, top_k=10, bm25=bm25)
    ids = [h['chunk_id'] for h in hits]

    ref_chunk = chunk_lookup.get(ref_id, {})
    ref_text = (ref_chunk.get('text', '') or '')[:200]
    ref_source = ref_chunk.get('source_file', '')

    # 目标片段在检索结果中的位置和分数
    target_hit = None
    for rank, h in enumerate(hits, 1):
        if h['chunk_id'] == ref_id:
            target_hit = {'rank': rank, 'score': h['score'], 'hits': hits}
            break

    if target_hit:
        rank = target_hit['rank']
        score = target_hit['score']
        hits_analyzed += 1

        # 看目标片段的前后邻居
        if rank > 1:
            neighbors = hits[:rank-1]
            # 检查排在前面的片段是否同源
            same_source_ahead = [h for h in neighbors if h.get('source_file') == ref_source]

            if score < 0.5:
                low_score_relevant += 1
                print(f'[低分] score={score:.4f} rank=#{rank} domain={domain}')
                print(f'  查询: {question[:80]}')
                print(f'  目标: {ref_id[:50]} ({ref_source})')
                print(f'  排在前面的{len(neighbors)}条中{len(same_source_ahead)}条同源')
                if neighbors:
                    top = neighbors[0]
                    print(f'  第一名: score={top["score"]:.4f} {top.get("source_file","")} {top.get("text","")[:100]}')
                print(f'  目标文本: {ref_text[:150]}')
                print()
    else:
        # 目标片段没进前10
        missed_relevant += 1
        if missed_relevant <= 5:
            print(f'[未命中] domain={domain}')
            print(f'  查询: {question[:80]}')
            print(f'  目标: {ref_id[:50]} ({ref_source})')
            if hits:
                top = hits[0]
                print(f'  第一名: score={top["score"]:.4f} {top.get("source_file","")} {top.get("text","")[:120]}')
            else:
                print(f'  检索返回空')
            print(f'  目标文本: {ref_text[:150]}')
            print()

print(f'\n===== 汇总 =====')
print(f'命中正例: {hits_analyzed}/{len(positives)} (进前10)')
print(f'其中低分命中(<0.5): {low_score_relevant} 条')
print(f'完全未命中(前10): {missed_relevant} 条')

# 分数分布
all_scores = []
for item in positives:
    hits = retrieve(item['question'], chunks, vectorizer, matrix, top_k=10, bm25=bm25)
    for h in hits:
        all_scores.append(h['score'])

import statistics
print(f'\n检索分数分布 (全部命中):')
print(f'  均值: {statistics.mean(all_scores):.4f}')
print(f'  中位数: {statistics.median(all_scores):.4f}')
print(f'  25分位: {sorted(all_scores)[len(all_scores)//4]:.4f}')
print(f'  75分位: {sorted(all_scores)[3*len(all_scores)//4]:.4f}')
print(f'  最高: {max(all_scores):.4f}  最低: {min(all_scores):.4f}')

# 按领域看分数
print(f'\n按领域分数分布:')
for domain in ['training_protocol', 'nutrition', 'injury_safety', 'medical_safety']:
    dscores = []
    for item in [d for d in positives if d.get('domain') == domain]:
        hits = retrieve(item['question'], chunks, vectorizer, matrix, top_k=5, bm25=bm25)
        for h in hits:
            dscores.append(h['score'])
    if dscores:
        print(f'  {domain}: 均值={statistics.mean(dscores):.4f} 中位={statistics.median(dscores):.4f} 样本={len(dscores)}')
