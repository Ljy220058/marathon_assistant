"""
演示 FAISS 检索链路的每一步：
1. 查询标准化 (normalize_query_text)
2. 查询变体生成 (_build_query_variants) — 中文 + 术语增强 + 英文翻译
3. FAISS 向量检索 (similarity_search_with_score)
4. 多路命中合并 (_merge_ranked_hits)
5. BM25 降级 fallback (fallback_search)
6. 语义切分 (split_text_semantic)
"""

import json
import sys
sys.path.insert(0, "src")

from marathon_qa_assistant.services.vector_store import (
    normalize_query_text,
    _build_query_variants,
    _enhance_query_with_hints,
    _merge_ranked_hits,
    build_bm25_fallback_index,
    fallback_search,
    split_text_semantic,
    split_text_sentence_aware,
    chunk_quality_report,
    _doc_to_hit,
)

SEP = "=" * 80

def demo():
    # ── 示例知识库 chunks (模拟 v2 FAISS 索引里的文档) ──
    sample_chunks = [
        {
            "chunk_id": "taper_v1_p1_c1",
            "source_file": "taper_and_peaking.md",
            "source_path": "/domain_docs/taper_and_peaking.md",
            "page": 12,
            "section": "Taper 减量",
            "text": "减量期 (taper) 是赛前 2-4 周逐步降低训练负荷的策略。研究表明，减量 50-70% 的跑量可以在不损失 VO2max 的情况下提升肌肉糖原储备。关键原则：强度不变、频率不变、容量大幅下降。",
            "keywords_zh": ["减量", "训练负荷", "VO2max"],
            "keywords_en": ["taper", "training load", "glycogen"],
            "domain_terms": ["training_protocol"],
        },
        {
            "chunk_id": "carbload_p1_c2",
            "source_file": "nutrition_race_day.md",
            "source_path": "/domain_docs/nutrition_race_day.md",
            "page": 8,
            "section": "碳水加载",
            "text": "碳水加载 (carbohydrate loading) 可以在赛前 36-48 小时内将肌糖原储备提升至正常水平的 1.5-2 倍。推荐采用改良方案：赛前三天逐步提高碳水占比至 70-80%，同时减少纤维摄入以避免肠胃不适。",
            "keywords_zh": ["碳水加载", "糖原", "赛前"],
            "keywords_en": ["carb loading", "glycogen", "pre-race"],
            "domain_terms": ["nutrition"],
        },
        {
            "chunk_id": "heat_stroke_p3_c1",
            "source_file": "heat_safety.md",
            "source_path": "/domain_docs/heat_safety.md",
            "page": 3,
            "section": "热射病识别",
            "text": "热射病 (exertional heat stroke) 是马拉松训练中最危险的热相关疾病，核心体温超过 40°C 且伴随中枢神经系统功能障碍。一旦出现意识模糊、步态不稳、皮肤干热，必须立即停止训练并紧急降温。冷水浸泡是首选降温方式。",
            "keywords_zh": ["热射病", "核心体温", "降温"],
            "keywords_en": ["heat stroke", "core temperature", "cooling"],
            "domain_terms": ["medical_safety"],
        },
        {
            "chunk_id": "easy_run_p2_c3",
            "source_file": "training_zones.md",
            "source_path": "/domain_docs/training_zones.md",
            "page": 5,
            "section": "轻松跑",
            "text": "轻松跑 (easy run) 应占总跑量的 70-80%，心率控制在最大心率的 60-75% 或储备心率的 59-74%。轻松跑的核心作用是建立有氧基础、促进毛细血管密度增长、加速训练后的恢复过程。",
            "keywords_zh": ["轻松跑", "有氧基础", "心率"],
            "keywords_en": ["easy run", "aerobic base", "heart rate"],
            "domain_terms": ["training_protocol"],
        },
        {
            "chunk_id": "interval_p4_c1",
            "source_file": "training_zones.md",
            "source_path": "/domain_docs/training_zones.md",
            "page": 7,
            "section": "间歇训练",
            "text": "间歇训练 (interval training) 以 VO2max 配速进行 3-5 分钟重复跑，组间等时长或略短的慢跑恢复。每周不超过 8% 的总跑量为间歇训练，以降低过度训练和受伤风险。",
            "keywords_zh": ["间歇", "VO2max", "过度训练"],
            "keywords_en": ["interval", "repetition", "overtraining"],
            "domain_terms": ["training_protocol"],
        },
        {
            "chunk_id": "knee_pain_p2_c1",
            "source_file": "injury_management.md",
            "source_path": "/domain_docs/injury_management.md",
            "page": 11,
            "section": "跑者膝",
            "text": "跑者膝 (runner's knee / PFPS) 是髌股疼痛综合征的俗称，表现为膝前疼痛，在下坡跑和下楼梯时加重。主要病因包括髋外展肌无力、股四头肌失衡和训练负荷过快增长。康复重点在臀中肌强化和逐步恢复跑量。",
            "keywords_zh": ["跑者膝", "髌股疼痛", "康复"],
            "keywords_en": ["runner knee", "PFPS", "rehabilitation"],
            "domain_terms": ["injury_safety"],
        },
    ]

    # ── 查询文本 ──
    query = "马拉松比赛前如何安排减量周和碳水加载？"

    # ================================================================
    # 步骤 1: 查询标准化
    # ================================================================
    print(f"\n{SEP}")
    print("步骤 1: normalize_query_text — 查询标准化")
    print(f"{SEP}")
    print(f"原始查询: {query}")
    normalized = normalize_query_text(query)
    print(f"标准化后: {normalized}")
    print("  → 全角标点→半角, 单位统一 (公里→km, 分钟→min), 多余空格合并")

    # ================================================================
    # 步骤 2: 查询变体生成 (核心双语策略)
    # ================================================================
    print(f"\n{SEP}")
    print("步骤 2: _build_query_variants — 生成多路查询变体")
    print(f"{SEP}")
    variants = _build_query_variants(query)
    for i, v in enumerate(variants):
        label = ["原始中文", "术语注入 (annotated)", "hints 增强", "纯英文术语"][i] if i < 4 else f"变体 {i+1}"
        print(f"  变体 {i+1} [{label}]: {v[:120]}")
    print(f"\n  共生成 {len(variants)} 路查询变体")

    # 解释变体
    print(f"\n  变体 1: 标准化后的原始中文查询 — 保持用户原意")
    print(f"  变体 2: annotated — 中文术语后注入英文对应词 (如 减量(taper))")
    print(f"  变体 3: hints 增强 — 拼接 QUERY_HINTS 中的英文关键词到查询末尾")
    print(f"  变体 4: 纯英文 — 用术语表把中文词替换为英文, 去掉中文部分")

    # ================================================================
    # 步骤 3: 模拟 FAISS 向量检索 (用 BM25 近似)
    # ================================================================
    print(f"\n{SEP}")
    print("步骤 3: FAISS similarity_search_with_score — 每路查询分别检索")
    print(f"{SEP}")
    print("(注: 实际生产调用 OllamaEmbeddings + FAISS.search, 这里用 BM25 模拟)")
    print(f"     实际链路: query → embed_query() → FAISS.index.search() → 返回 (Document, distance)\n")

    bm25_index = build_bm25_fallback_index(sample_chunks)
    all_hit_groups = []
    for i, variant in enumerate(variants):
        hits = fallback_search(variant, sample_chunks, bm25=bm25_index, top_k=5)
        hit_ids = [h["chunk_id"] for h in hits]
        hit_scores = [f"{h['score']:.4f}" for h in hits]
        print(f"  变体 {i+1}: \"{variant[:60]}...\"")
        print(f"    → 命中: {hit_ids}")
        print(f"    → 分数: {hit_scores}")
        # 模拟 FAISS 返回格式
        langchain_docs = []
        for h in hits:
            from langchain_core.documents import Document
            doc = Document(page_content=h["text"], metadata={
                "chunk_id": h["chunk_id"],
                "source_file": h["source_file"],
                "page": h["page"],
                "query_variant": variant,
            })
            # 把 BM25 分数转为距离 (FAISS 用 L2 distance, 越小越好)
            distance = 1.0 - h["score"]
            langchain_docs.append((doc, distance))
        # 转成 _doc_to_hit 格式
        vector_hits = []
        for doc, dist in langchain_docs:
            hit = _doc_to_hit(doc, distance=dist)
            hit["retrieval_mode"] = "vector_fusion" if len(variants) > 1 else "vector"
            hit["query_variant"] = variant
            vector_hits.append(hit)
        all_hit_groups.append(vector_hits)

    # ================================================================
    # 步骤 4: 合并去重排序 (_merge_ranked_hits)
    # ================================================================
    print(f"\n{SEP}")
    print("步骤 4: _merge_ranked_hits — 按 chunk_id 合并去重, 保留最高分")
    print(f"{SEP}")
    merged = _merge_ranked_hits(all_hit_groups, top_k=5)
    for rank, hit in enumerate(merged, 1):
        variants_hit = hit.get("query_variants", [])
        cons = hit.get("consensus_count", 1)
        bl = hit.get("bilingual_match", False)
        print(f"  #{rank} chunk_id={hit['chunk_id']}  score={hit['score']:.4f}")
        print(f"      被 {cons} 路查询命中 | bilingual_match={bl}")
        print(f"      命中变体: {[v[:50] for v in variants_hit]}")
        print(f"      来源: {hit['source_file']} p{hit['page']}")
        print(f"      text: {str(hit.get('text',''))[:100]}...")
        score_bd = hit.get("score_breakdown", {})
        if score_bd:
            print(f"      score_breakdown: {json.dumps(score_bd, ensure_ascii=False)}")
        print()

    # ================================================================
    # 步骤 5: BM25 fallback 演示
    # ================================================================
    print(f"\n{SEP}")
    print("步骤 5: fallback_search — FAISS 不可用时的 BM25 降级")
    print(f"{SEP}")
    print("场景: FAISS 索引损坏或缺失, 系统自动切换到关键词匹配")
    fallback_hits = fallback_search("跑者膝怎么康复", sample_chunks, top_k=3)
    for rank, hit in enumerate(fallback_hits, 1):
        print(f"  #{rank} chunk_id={hit['chunk_id']}  score={hit['score']:.4f}")
        print(f"      retrieval_mode={hit['retrieval_mode']}")
        print(f"      retrieval_status={hit['retrieval_status']}")
        print(f"      can_write_core={hit['can_write_core']}")
        print(f"      display_mode={hit['display_mode']}")
        print(f"      text: {str(hit.get('text',''))[:120]}...")
        print()

    # ================================================================
    # 步骤 6: 语义切分演示
    # ================================================================
    print(f"\n{SEP}")
    print("步骤 6: split_text_semantic — 语义切分 (按标题/段落边界)")
    print(f"{SEP}")
    doc_text = """# 减量期安排
减量期是赛前 2-4 周逐步降低训练负荷的过程。核心原则是保持训练强度、减少训练容量。

## 减量节奏
第一周减量 20-30%，第二周减量 40-50%，最后一周减量 60-70%。
注意: 高强度的间歇训练仍需保留，但组数减半。

## 碳水加载配合
减量期同时开始碳水加载，肌糖原水平可在 48 小时内显著提升。
禁忌: 减量期不应尝试新的补给策略或训练动作。"""
    semantic_chunks = split_text_semantic(doc_text, chunk_size=500, chunk_overlap=50)
    print(f"  输入文本: {len(doc_text)} 字符")
    print(f"  切分数: {len(semantic_chunks)} chunks\n")
    for i, c in enumerate(semantic_chunks, 1):
        print(f"  chunk {i}: section=\"{c['section']}\"  len={len(c['text'])}")
        print(f"    paragraph_index={c['paragraph_index']}  char_start={c['char_start']}  char_end={c['char_end']}")
        print(f"    text: {c['text'][:150]}...")
        print()

    # 对比: 固定窗口切分
    fixed_chunks = split_text_sentence_aware(doc_text, chunk_size=500, chunk_overlap=50)
    print(f"  对比固定窗口 (sentence-aware): {len(fixed_chunks)} chunks")
    for i, c in enumerate(fixed_chunks, 1):
        print(f"    fixed-chunk {i}: len={len(c)}  text: {c[:120]}...")

    # ================================================================
    # 汇总: 检索链路总览
    # ================================================================
    print(f"\n\n{SEP}")
    print("检索链路总览")
    print(f"{SEP}")
    print("""
   用户查询: "马拉松比赛前如何安排减量周和碳水加载？"
       │
       ▼
  [1] normalize_query_text()         ← 全角→半角, 千米→km, 分钟→min
       │
       ▼
  [2] _build_query_variants()        ← 生成 4 路查询变体
       │                                 ① 中文原文
       │                                 ② 术语注入 (减量→减量(taper))
       │                                 ③ hints 增强 (+英文关键词)
       │                                 ④ 纯英文术语翻译
       │
       ▼
  [3] 每路 variant 独立调用          ← FAISS.similarity_search_with_score()
      FAISS 向量检索                    实际: OllamaEmbeddings.embed_query()
       │                                 → FAISS.index.search()
       │                                 → 返回 (Document, L2_distance)
       │
       ▼
  [4] _merge_ranked_hits()           ← 按 chunk_id 去重
       │                                保留最高分 + 最完整 metadata
       │                                consensus_count 仅诊断, 不加分
       │
       ▼
  [5] 输出 ranked evidence           ← → profile_and_retrieval.py
       │                                → build_ranked_evidence()
       │                                → KG 融合 (decision_gate 独立)
       │
       ▼
  [6] evidence chain                 ← → 回答生成 / 前端展示
""")


if __name__ == "__main__":
    demo()
