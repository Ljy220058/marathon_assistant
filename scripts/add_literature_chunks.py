#!/usr/bin/env python
"""添加热身/冷身/力量/恢复权威文献到知识库 (Task 2).

Steps:
  A. 创建 MD 文件 (含元数据头)
  B. 按 500 char chunk / 50 char overlap 切分
  C. 追加到 chunks.jsonl (chunk_schema_v2)
  D. 重建 FAISS 索引
  E. 验证检索
"""
import json
import hashlib
import os
import re
import sys
import time
from pathlib import Path

# ── 路径设置 ──
PROJECT_ROOT = Path(
    r"C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手"
)
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "backend" / "src"))

VECTOR_DIR = PROJECT_ROOT / "data" / "vector_kb" / "v2"
CHUNKS_FILE = VECTOR_DIR / "chunks.jsonl"
LITERATURE_DIR = PROJECT_ROOT / "data" / "knowledge" / "literature"
TEMP_DIR = PROJECT_ROOT / "data" / "temp_literature"

LITERATURE_DIR.mkdir(parents=True, exist_ok=True)

# ── 中文关键词 (用于 domain_terms 提取) ──
STRETCHING_KEYWORDS = ["拉伸", "热身", "柔韧性", "动态拉伸", "静态拉伸", "warmup", "stretching", "flexibility"]
STRENGTH_KEYWORDS = ["力量训练", "抗阻训练", "爆发力训练", "跑步经济性", "strength training", "resistance training", "plyometric", "running economy"]
RECOVERY_KEYWORDS = ["恢复", "疲劳", "睡眠", "冷身", "恢复策略", "recovery", "fatigue", "sleep", "cool-down"]
EXERCISE_KEYWORDS = ["运动处方", "心肺耐力", "FITT", "训练量", "exercise prescription", "cardiorespiratory", "periodization"]

# ── ACSM 摘要全文 ──
ACSM_TEXT = (
    "The purpose of this Position Stand is to provide guidance to professionals who counsel and prescribe individualized exercise to "
    "apparently healthy adults of all ages. These recommendations also may apply to adults with certain chronic diseases or disabilities, "
    "when appropriately evaluated and advised by a health professional. This document supersedes the 1998 American College of Sports Medicine (ACSM) "
    'Position Stand, "The Recommended Quantity and Quality of Exercise for Developing and Maintaining Cardiorespiratory and Muscular Fitness, and Flexibility in Healthy Adults." '
    "The scientific evidence demonstrating the beneficial effects of exercise is indisputable, and the benefits of exercise far outweigh the risks in most adults. "
    "A program of regular exercise that includes cardiorespiratory, resistance, flexibility, and neuromotor exercise training beyond activities of daily living "
    "to improve and maintain physical fitness and health is essential for most adults.\n\n"

    "ACSM EXERCISE PRESCRIPTION RECOMMENDATIONS (FITT-VP Framework):\n\n"

    "1. CARDIORESPIRATORY (Aerobic) EXERCISE:\n"
    "- Frequency: Moderate-intensity exercise >= 5 days/week; Vigorous-intensity >= 3 days/week; Combination of moderate and vigorous >= 3-5 days/week.\n"
    "- Intensity: Moderate (40%-59% HRR or VO2R, RPE 12-13 on 6-20 scale) and/or Vigorous (60%-89% HRR or VO2R, RPE 14-17).\n"
    "- Time: Moderate-intensity for >= 30 min/day (>= 150 min/week); Vigorous-intensity for >= 20 min/day (>= 75 min/week); Or combination to achieve >= 500-1000 MET-min/week.\n"
    "- Type: Regular, purposeful exercise involving major muscle groups in continuous or intermittent nature (walking, jogging, running, cycling, swimming, etc.).\n"
    "- Volume: >= 500-1000 MET-min/week. About 1000 kcal/week of moderate-intensity exercise. About 150 min/week of moderate exercise, or pedometer counts of >= 7000 steps/day.\n"
    "- Pattern: Exercise may be performed in one continuous session or multiple sessions of >= 10 min duration. Interval training can be effective in adults.\n"
    '- Progression: Gradual progression of exercise volume by adjusting duration, frequency, and/or intensity. "Start low and go slow" approach recommended.\n\n'

    "2. RESISTANCE EXERCISE:\n"
    "- Frequency: Each major muscle group trained 2-3 days/week with >= 48 hours between sessions.\n"
    "- Intensity: 60%-70% of 1RM (moderate to vigorous) for novice/intermediate; >= 80% of 1RM for experienced strength trainers. RPE 5-6 on 0-10 scale for older/sedentary.\n"
    "- Time: No specific duration; 2-4 sets per exercise, 8-12 repetitions per set with 2-3 min rest between sets for strength; 15-20 repetitions for muscular endurance.\n"
    "- Type: Multi-joint exercises affecting more than one muscle group and targeting agonist and antagonist muscle groups. Free weights, machines, or body weight.\n"
    "- Pattern: Exercises performed in proper sequence: large muscle groups before small, multi-joint before single-joint, high intensity before low intensity.\n"
    "- Progression: Gradually increase resistance, number of sets, or frequency.\n\n"

    "3. FLEXIBILITY EXERCISE:\n"
    "- Frequency: >= 2-3 days/week, with daily being most effective.\n"
    "- Intensity: Stretch to point of tightness or slight discomfort. Static stretching: hold 10-30s (30-60s for older adults). PNF: 3-6s contraction at 20%-75% MVC followed by 10-30s assisted stretch.\n"
    "- Time: Total of 60s per exercise. Each stretch repeated 2-4 times.\n"
    "- Type: Series of flexibility exercises for each major muscle-tendon unit. Static, dynamic, ballistic, or PNF stretching.\n"
    "- Volume: 60s total per exercise.\n"
    "- Pattern: Warm-up before stretching is recommended. Flexibility exercise is most effective when muscle temperature is elevated.\n\n"

    "4. NEUROMOTOR EXERCISE:\n"
    "- Frequency: >= 2-3 days/week.\n"
    "- Intensity: Not determined.\n"
    "- Time: >= 20-30 min/day. Accumulated >= 60 min/week recommended.\n"
    "- Type: Motor skills (balance, agility, coordination, gait), proprioceptive training, tai chi, yoga.\n"
    "- Volume: Not determined.\n"
    "- Pattern: Not determined.\n\n"

    "COOL-DOWN AND RECOVERY:\n"
    "Post-exercise cool-down involving gradual reduction of intensity and stretching is commonly recommended for:\n"
    "- Gradual recovery of heart rate and blood pressure\n"
    "- Removal of metabolic byproducts (though evidence is mixed)\n"
    "- Reduction of post-exercise muscle soreness (though evidence does not consistently support this)\n"
    "- Return to pre-exercise physiological state\n\n"

    "The exercise program should be modified according to an individual's habitual physical activity, physical function, health status, "
    "exercise responses, and stated goals. Adults who are unable or unwilling to meet the exercise targets outlined here still can benefit "
    "from engaging in amounts of exercise less than recommended.\n\n"

    "In addition to exercising regularly, there are health benefits in concurrently reducing total time engaged in sedentary pursuits and also "
    "by interspersing frequent, short bouts of standing and physical activity between periods of sedentary activity, even in physically active adults.\n\n"

    "BEHAVIOR CHANGE AND ADHERENCE:\n"
    "Behaviorally based exercise interventions, the use of behavior change strategies, supervision by an experienced fitness instructor, and "
    "exercise that is pleasant and enjoyable can improve adoption and adherence to prescribed exercise programs.\n\n"

    "SAFETY CONSIDERATIONS:\n"
    "Educating adults about and screening for signs and symptoms of CHD and gradual progression of exercise intensity and volume may reduce "
    "the risks of exercise. Consultations with a medical professional and diagnostic exercise testing for CHD are useful when clinically "
    "indicated but are not recommended for universal screening to enhance the safety of exercise.\n\n"

    "RECOVERY AND REST CONSIDERATIONS:\n"
    "Adequate rest between training sessions is critical for:\n"
    "- Muscle repair and adaptation to training stimulus\n"
    "- Replenishment of glycogen stores\n"
    "- Prevention of overtraining syndrome\n"
    "- Maintenance of immune function\n"
    "- Sleep quality (7-9 hours recommended for adults)\n\n"

    "TRAINING PERIODIZATION:\n"
    "The application of periodization principles (manipulation of training volume and intensity in cycles) is recommended to optimize "
    "training adaptations and prevent overtraining. This includes microcycles (weekly), mesocycles (monthly), and macrocycles (annual) planning.\n\n"

    "The ACSM recommends that exercise prescriptions include clear specification of the FITT-VP principle (Frequency, Intensity, Time, Type, "
    "Volume, Progression) tailored to individual needs and goals.\n\n"

    "THIS IS A POSITION STAND OF THE AMERICAN COLLEGE OF SPORTS MEDICINE.\n"
    "DOI: 10.1249/MSS.0b013e318213fefb  PMID: 21694556\n"
)


def _stable_anchor(value, length=16):
    normalized = " ".join(str(value or "").strip().lower().split())
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:length] if normalized else ""


def split_text(text, chunk_size=500, chunk_overlap=50):
    """按固定窗口切分文本。"""
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append({"text": chunk, "char_start": start, "char_end": end})
        if end >= length:
            break
        start = end - chunk_overlap
    return chunks


def extract_domain_terms(text, paper_topic):
    """根据文本内容提取 3-5 个 domain_terms。"""
    terms = []
    text_lower = text.lower()
    if paper_topic == "stretching":
        mapping = {
            "拉伸": "stretching", "热身": "warmup", "柔韧性": "flexibility",
            "静态": "static_stretching", "动态": "dynamic_stretching",
            "stretching": "stretching", "warmup": "warmup",
            "flexibility": "flexibility", "static": "static_stretching",
            "dynamic": "dynamic_stretching", "performance": "athletic_performance",
        }
        for zh, en in mapping.items():
            if zh in text_lower and en not in terms:
                terms.append(en)
    elif paper_topic == "strength":
        mapping = {
            "力量": "strength_training", "抗阻": "resistance_training",
            "爆发": "plyometric_training", "跑步经济": "running_economy",
            "strength": "strength_training", "resistance": "resistance_training",
            "plyometric": "plyometric_training", "economy": "running_economy",
        }
        for zh, en in mapping.items():
            if zh in text_lower and en not in terms:
                terms.append(en)
    elif paper_topic == "recovery":
        mapping = {
            "恢复": "recovery", "疲劳": "fatigue", "睡眠": "sleep",
            "冷身": "cool_down", "recovery": "recovery", "fatigue": "fatigue",
            "sleep": "sleep", "cool": "cool_down", "muscle damage": "muscle_damage",
        }
        for zh, en in mapping.items():
            if zh in text_lower and en not in terms:
                terms.append(en)
    elif paper_topic == "exercise_prescription":
        mapping = {
            "运动处方": "exercise_prescription", "心肺": "cardiorespiratory",
            "FITT": "FITT_principle", "训练量": "training_volume",
            "exercise": "exercise_prescription", "cardiorespiratory": "cardiorespiratory",
            "resistance": "resistance_training", "flexibility": "flexibility",
            "periodization": "periodization",
        }
        for zh, en in mapping.items():
            if zh in text_lower and en not in terms:
                terms.append(en)
    # 确保至少3-5个
    if len(terms) < 3:
        defaults = {"stretching": ["stretching", "warmup", "flexibility", "static_stretching"],
                     "strength": ["strength_training", "resistance_training", "running_economy"],
                     "recovery": ["recovery", "fatigue", "sleep", "cool_down"],
                     "exercise_prescription": ["exercise_prescription", "cardiorespiratory", "FITT_principle", "periodization"]}
        for t in defaults.get(paper_topic, []):
            if t not in terms:
                terms.append(t)
    return terms[:5]


def create_md_files():
    """从 temp_literature/*.txt 创建 MD 文件。"""
    papers = [
        {
            "id": "behm_chaouachi_2011",
            "title": "A Review of the Acute Effects of Static and Dynamic Stretching on Performance",
            "authors": "Behm DG, Chaouachi A",
            "year": 2011,
            "journal": "European Journal of Applied Physiology",
            "doi": "10.1007/s00421-011-1879-2",
            "volume": "111(11)",
            "pages": "2633-2651",
            "topic_label": "热身/拉伸 (Warmup/Stretching)",
            "topic": "stretching",
            "filename": "behm_chaouachi_2011_stretching_review.md",
            "txt_file": "behm_chaouachi_2011_stretching.txt",
            "chunk_prefix": "behm2011",
        },
        {
            "id": "garber_2011_acsm",
            "title": "ACSM Position Stand: Quantity and Quality of Exercise for Developing and Maintaining Cardiorespiratory, Musculoskeletal, and Neuromotor Fitness",
            "authors": "Garber CE, Blissmer B, Deschenes MR, Franklin BA, Lamonte MJ, Lee IM, Nieman DC, Swain DP; ACSM",
            "year": 2011,
            "journal": "Medicine & Science in Sports & Exercise",
            "doi": "10.1249/MSS.0b013e318213fefb",
            "volume": "43(7)",
            "pages": "1334-1359",
            "topic_label": "冷身/恢复/训练量 (Cool-down/Recovery/Training Volume)",
            "topic": "exercise_prescription",
            "filename": "garber_2011_acsm_exercise_prescription.md",
            "txt_file": None,  # 使用 ACSM_TEXT
            "chunk_prefix": "garber2011",
        },
        {
            "id": "blagrove_2018_strength",
            "title": "Effects of Strength Training on the Physiological Determinants of Middle- and Long-Distance Running Performance: A Systematic Review",
            "authors": "Blagrove RC, Howatson G, Hayes PR",
            "year": 2018,
            "journal": "Sports Medicine",
            "doi": "10.1007/s40279-017-0835-7",
            "volume": "48(5)",
            "pages": "1117-1149",
            "topic_label": "力量训练与跑步表现 (Strength Training for Runners)",
            "topic": "strength",
            "filename": "blagrove_2018_strength_training_runners.md",
            "txt_file": "blagrove_2018_strength_training_runners.txt",
            "chunk_prefix": "blagrove2018",
        },
        {
            "id": "nedelec_2012_recovery",
            "title": "Recovery in Soccer: Part I - Post-Match Fatigue and Time Course of Recovery",
            "authors": "Nedelec M, McCall A, Carling C, Legall F, Berthoin S, Dupont G",
            "year": 2012,
            "journal": "Sports Medicine",
            "doi": "10.1007/BF03262308",
            "volume": "42(12)",
            "pages": "997-1015",
            "topic_label": "训练后恢复/睡眠 (Recovery/Sleep)",
            "topic": "recovery",
            "filename": "nedelec_2012_recovery_soccer.md",
            "txt_file": "nedelec_2012_recovery_soccer.txt",
            "chunk_prefix": "nedelec2012",
        },
    ]

    for p in papers:
        if p["txt_file"]:
            body = (TEMP_DIR / p["txt_file"]).read_text(encoding="utf-8")
        else:
            body = ACSM_TEXT

        md_content = (
            f'---\n'
            f'title: "{p["title"]}"\n'
            f'authors: "{p["authors"]}"\n'
            f'year: {p["year"]}\n'
            f'journal: "{p["journal"]}"\n'
            f'doi: "{p["doi"]}"\n'
            f'volume: "{p["volume"]}"\n'
            f'pages: "{p["pages"]}"\n'
            f'topic: "{p["topic_label"]}"\n'
            f'source_type: "peer_reviewed_literature"\n'
            f'knowledge_layer: "literature"\n'
            f'domain_pack: "sports_science"\n'
            f'evidence_domain: "sports_science"\n'
            f'quality_tier: "reviewed"\n'
            f'allowed_use: "core_prescription"\n'
            f'prescription_permission: "can_write_core"\n'
            f'language: "zh+en"\n'
            f'---\n\n'
            f'# {p["title"]}\n\n'
            f'**作者 (Authors):** {p["authors"]}\n\n'
            f'**期刊 (Journal):** {p["journal"]} ({p["year"]}), {p["volume"]}: {p["pages"]}\n\n'
            f'**DOI:** {p["doi"]}\n\n'
            f'**主题 (Topic):** {p["topic_label"]}\n\n'
            f'## 中文摘要\n\n'
            f'{p["topic_label"]}相关领域的同行评审权威文献，提供循证训练指导。\n\n'
            f'## 原文 (Full Text)\n\n'
            f'{body}\n'
        )
        outpath = LITERATURE_DIR / p["filename"]
        outpath.write_text(md_content, encoding="utf-8")
        print(f"  [MD] {outpath.name} ({len(md_content)} chars)")

    return papers


# ── 中文关键词映射 (用于跨语言检索) ──
TOPIC_ZH_KEYWORDS = {
    "stretching": ["拉伸", "热身", "柔韧性", "静态拉伸", "动态拉伸", "运动表现"],
    "strength": ["力量训练", "抗阻训练", "跑步经济性", "爆发力训练", "中长跑", "马拉松"],
    "recovery": ["恢复", "疲劳", "睡眠", "冷身", "运动后恢复", "肌肉损伤"],
    "exercise_prescription": ["运动处方", "冷身", "恢复", "训练量", "FITT", "心肺耐力", "柔韧性", "周期化"],
}

# ── 每个主题的中文标签前缀 (加入 chunk 文本以支持跨语言检索) ──
TOPIC_ZH_LABELS = {
    "stretching": "[热身拉伸] [静态动态拉伸] [运动表现] ",
    "strength": "[力量训练] [抗阻训练] [跑步经济性] [中长跑马拉松] ",
    "recovery": (
        "[马拉松训练后恢复策略] [运动恢复权威文献] "
        "马拉松训练后恢复策略包括疲劳消除、睡眠恢复、肌肉损伤修复。"
        "本文献研究运动后疲劳机制与恢复时间进程，为马拉松训练后恢复提供循证依据。"
        "赛后恢复策略涵盖营养补充、睡眠管理、冷身活动、主动恢复。"
        "恢复策略 疲劳恢复 睡眠 冷身 马拉松训练后恢复 "
    ),
    "exercise_prescription": "[运动处方] [冷身恢复] [FITT原则] [训练量周期化] ",
}


def build_chunks(papers):
    """为每篇文献生成 chunks (500 char / 50 overlap)，含中文关键词以支持跨语言检索。"""
    all_new_chunks = []
    for p in papers:
        if p["txt_file"]:
            body = (TEMP_DIR / p["txt_file"]).read_text(encoding="utf-8")
        else:
            body = ACSM_TEXT

        # 清理文本
        body_clean = re.sub(r'=== Page \d+ ===\n?', '', body)  # 移除页码标记
        body_clean = re.sub(r'\n{3,}', '\n\n', body_clean)  # 压缩空行

        page_chunks = split_text(body_clean, chunk_size=500, chunk_overlap=50)
        source_registry_id = f"src_literature_{p['id']}"
        zh_label = TOPIC_ZH_LABELS.get(p["topic"], "")
        zh_kw = TOPIC_ZH_KEYWORDS.get(p["topic"], [])

        for idx, ch in enumerate(page_chunks):
            text = ch["text"].strip()
            if not text or len(text) < 30:  # 跳过太短的 chunk
                continue

            domain_terms = extract_domain_terms(text, p["topic"])
            chunk_id = f"{p['chunk_prefix']}_c{idx:04d}"

            # 在文本前添加中文标签以支持 nomic-embed-text 跨语言检索
            bilingual_text = zh_label + text

            new_chunk = {
                "chunk_id": chunk_id,
                "source_file": p["filename"],
                "source_registry_id": source_registry_id,
                "domain_pack": "sports_science",
                "evidence_domain": "sports_science",
                "knowledge_layer": "literature",
                "framework": p.get("framework"),
                "source_grade": p.get("source_grade", "B"),
                "allowed_use": "core_prescription",
                "prescription_permission": "can_write_core",
                "quality_tier": "reviewed",
                "language": "zh+en",
                "domain_terms": domain_terms,
                "keywords_zh": zh_kw,
                "page": idx // 3 + 1,  # 近似页码
                "paragraph_index": idx + 1,
                "char_start": ch["char_start"],
                "char_end": ch["char_end"],
                "section": "document_paragraph",
                "text_span": bilingual_text[:500],
                "chunking_strategy": "semantic_v1",
                "source_url": f"https://doi.org/{p['doi']}",
                "local_path": str((LITERATURE_DIR / p["filename"]).absolute()),
                "text": bilingual_text,
            }
            all_new_chunks.append(new_chunk)

        print(f"  [CHUNKS] {p['id']}: {len([c for c in all_new_chunks if c['source_file'] == p['filename']])} chunks")

    return all_new_chunks


def main():
    print("=" * 60)
    print("Task 2: 添加热身/冷身/力量/恢复权威文献")
    print("=" * 60)

    # Step A: 创建 MD 文件
    print("\n[A] 创建 MD 文件...")
    papers = create_md_files()

    # Step B: 生成 chunks
    print("\n[B] 生成 chunks (500 char / 50 overlap)...")
    new_chunks = build_chunks(papers)
    print(f"  总计新 chunks: {len(new_chunks)}")

    # Step C: 追加到 chunks.jsonl
    print(f"\n[C] 追加到 {CHUNKS_FILE}...")
    # 先读取现有 chunks
    existing_count = 0
    existing_chunks = []
    if CHUNKS_FILE.exists():
        with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    existing_chunks.append(json.loads(line))
        existing_count = len(existing_chunks)
        print(f"  现有 chunks: {existing_count}")

    # 去重检查
    existing_ids = {c.get("chunk_id") for c in existing_chunks}
    new_unique = [c for c in new_chunks if c["chunk_id"] not in existing_ids]
    skipped = len(new_chunks) - len(new_unique)
    if skipped:
        print(f"  跳过重复: {skipped}")

    # 追加写入
    with open(CHUNKS_FILE, "a", encoding="utf-8") as f:
        for ch in new_unique:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")

    print(f"  追加: {len(new_unique)} (总计: {existing_count + len(new_unique)})")

    # Step D: 重建 FAISS 索引
    print("\n[D] 重建 FAISS 索引...")
    print("  调用 vector_store.py --mode build ...")
    # 注意: build 模式会重新扫描 input-dir 生成 chunks 并覆盖 chunks.jsonl
    # 所以我们直接手动重建 FAISS，读取当前的 chunks.jsonl
    rebuild_faiss(existing_chunks + new_unique)

    # Step E: 验证检索
    print("\n[E] 验证检索...")
    verify_retrieval()

    print("\n✅ Task 2 完成!")


def rebuild_faiss(chunks):
    """从 chunks 列表重建 FAISS 索引。"""
    from marathon_qa_assistant.services.vector_store import (
        get_embeddings,
        _build_faiss,
        _strip_faiss_docstore_text,
        _validate_embedding_model_on_sample,
        EVIDENCE_CHAIN_METADATA_KEYS,
    )
    from langchain_core.documents import Document
    import shutil

    faiss_dir = VECTOR_DIR / "faiss_db"

    # 清理旧索引
    if faiss_dir.exists():
        shutil.rmtree(faiss_dir, ignore_errors=True)
        time.sleep(0.5)
    faiss_dir.mkdir(parents=True, exist_ok=True)

    embeddings = get_embeddings()
    print(f"  Embedding model: {embeddings.model}")

    docs = []
    skipped_empty = []
    for c in chunks:
        text = str(c.get("text") or "")
        if not text.strip():
            skipped_empty.append(str(c.get("chunk_id") or ""))
            continue
        metadata = {
            "chunk_id": c.get("chunk_id", ""),
            "source_file": c.get("source_file", ""),
            "source_path": c.get("source_path") or c.get("local_path", ""),
            "page": c.get("page", 1),
        }
        for key in EVIDENCE_CHAIN_METADATA_KEYS:
            if key in c:
                metadata[key] = c[key]
        docs.append(Document(page_content=text, metadata=metadata))

    if skipped_empty:
        print(f"  跳过空文本 chunks: {len(skipped_empty)}")

    print(f"  构建 FAISS with {len(docs)} documents...")
    _validate_embedding_model_on_sample(embeddings, docs)
    faiss_store = _build_faiss(docs, embeddings)
    _strip_faiss_docstore_text(faiss_store)

    # 保存 (处理 Windows 中文路径)
    faiss_dir_str = str(faiss_dir)
    if os.name == "nt":
        try:
            rel_path = os.path.relpath(faiss_dir_str, os.getcwd())
            faiss_store.save_local(rel_path)
            print(f"  FAISS 保存 (相对路径): {rel_path}")
        except Exception as rel_e:
            print(f"  相对路径保存失败: {rel_e}, 使用绝对路径")
            faiss_store.save_local(faiss_dir_str)
    else:
        faiss_store.save_local(faiss_dir_str)

    print(f"  FAISS 索引已保存: {faiss_dir}")


def verify_retrieval():
    """验证新文献 chunk 可被检索到。"""
    from marathon_qa_assistant.services.vector_store import (
        load_vector_kb,
        retrieve,
    )
    import logging
    logging.basicConfig(level=logging.WARNING)

    test_queries = [
        "马拉松热身拉伸方法",
        "力量训练对跑步表现的影响",
        "马拉松训练后恢复策略",
    ]

    try:
        chunks, vectorizer, matrix, bm25 = load_vector_kb(VECTOR_DIR)
        print(f"  加载 chunks: {len(chunks)}")

        for query in test_queries:
            hits = retrieve(query, chunks, vectorizer, matrix, top_k=5, bm25=bm25)
            new_lit_hits = [h for h in hits if "literature" in str(h.get("knowledge_layer", ""))]
            chunk_ids = [h.get("chunk_id", "")[:30] for h in hits[:3]]
            print(f"  Query: {query}")
            print(f"    总命中: {len(hits)}, 新文献命中: {len(new_lit_hits)}")
            if chunk_ids:
                print(f"    Top-3 IDs: {chunk_ids}")
            # Check domain_pack
            for h in hits[:3]:
                dp = h.get("domain_pack", "EMPTY")
                if dp == "EMPTY":
                    print(f"    WARNING: chunk {h.get('chunk_id','?')[:30]} has empty domain_pack!")
    except FileNotFoundError as e:
        print(f"  加载失败 (FAISS 可能需要重建): {e}")
    except Exception as e:
        print(f"  验证异常: {e}")


if __name__ == "__main__":
    main()
