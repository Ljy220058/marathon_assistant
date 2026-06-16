"""将审核所需文献的核心证据写入 training_protocol KB chunk。"""
import json
from pathlib import Path

KB_JSONL = Path(__file__).resolve().parents[2] / "data" / "vector_kb" / "v2_sharded" / "training_protocol" / "chunks.jsonl"

CHUNKS = [
    # ═══ Billat 2001 Part I — 有氧间歇训练 ═══
    {
        "chunk_id": "kb_billat_aerobic_interval_2001_abstract",
        "source_file": "Billat_2001_Interval_Training_Part_I_Aerobic.pdf",
        "source_registry_id": "src_billat_aerobic_interval_2001",
        "local_path": "data/domain_docs/Billat_2001_Interval_Training_Part_I_Aerobic.pdf",
        "page": 1, "paragraph_index": 0, "char_start": 0, "char_end": 2000,
        "text": (
            "【间歇训练理论与实践：有氧间歇训练（Billat 2001 Part I）】\n"
            "期刊：Sports Medicine, 2001, 31(1):13-31。作者：L V Billat。\n\n"
            "核心内容：\n"
            "1. 间歇训练（Interval Training）的定义：重复进行短至长段的高强度运动"
            "（强度≥最大乳酸稳态速度，即 ≥maximal lactate steady-state velocity），"
            "中间穿插恢复期（轻度运动或完全休息）。\n"
            "2. 间歇训练最早由 Reindell 和 Roskamm 提出，1950 年代由奥运冠军 Emil Zatopek 推广。\n"
            "3. 中长跑运动员使用此技术以接近比赛速度的强度训练。教练员历史上使用 "
            "800-5000m 的比赛速度校准间歇训练，而非依靠生理标记。\n"
            "4. 在非比赛季，建议参考与特定生理反应相关的速度范围——"
            "从最大乳酸稳态到绝对最大速度（maximal lactate steady state to absolute maximal velocity）。\n"
            "5. 比赛中的速度范围必须被考虑——即使是世界纪录也不是以恒定配速完成的。\n\n"
            "训练应用：有氧间歇训练以 ≥90% VO2max 的强度执行，"
            "每组工作时长 30 秒至 5 分钟，组间采用不完全恢复。"
            "目标是累积尽可能多的"红区时间"（T@VO2max），单节课应达到数分钟以上的 ≥90% VO2max 时间。"
        ),
        "language": "zh",
        "domain_pack": "endurance_training_protocols",
        "evidence_domain": "sports_science_reference",
        "knowledge_layer": "domain_pack",
        "allowed_use": "explanation",
        "prescription_permission": "explanation_only",
        "quality_tier": "systematic_review",
        "needs_review": False,
        "exclude_from_training_generation": False,
        "source_authority": "B",
        "domain_terms": ["间歇训练", "有氧间歇", "Billat", "vVO2max", "最大乳酸稳态", "红区时间", "有氧能力"],
    },

    # ═══ Billat 2001 Part II — 无氧间歇训练 ═══
    {
        "chunk_id": "kb_billat_anaerobic_interval_2001_abstract",
        "source_file": "Billat_2001_Interval_Training_Part_II_Anaerobic.pdf",
        "source_registry_id": "src_billat_anaerobic_interval_2001",
        "local_path": "data/domain_docs/Billat_2001_Interval_Training_Part_II_Anaerobic.pdf",
        "page": 1, "paragraph_index": 0, "char_start": 0, "char_end": 2000,
        "text": (
            "【间歇训练理论与实践：无氧间歇训练（Billat 2001 Part II）】\n"
            "期刊：Sports Medicine, 2001, 31(2):75-90。作者：L V Billat。\n\n"
            "核心内容：\n"
            "1. 无氧间歇训练研究分为两类：\n"
            "   a) 固定工作速率研究（旧研究）：强度为 130-160% VO2max，工作段 10-15 秒，"
            "休息间隔 15-40 秒。测量个体在给定暂停时长下能完成的重复次数。\n"
            "   b) 最大强度重复研究（新研究）：要求参与者以最大努力重复，暂停时长"
            "30 秒至 4-5 分钟。研究连续运动间的最大动态功率变化及肌肉代谢变化。\n"
            "2. 使用短间歇训练极难激发纯粹的无氧代谢。研究明确表明："
            "同等强度下，间歇形式的糖原分解贡献远低于连续运动形式。\n"
            "3. 第二类间歇训练的关键特征：强度位于增量测试中测定的 VO2max 对应"
            "最小速度（vVO2max）之上。\n"
            "4. 多项关于超最大强度间歇运动长期生理效应的研究表明："
            "VO2max 和跑步经济性（Running Economy）均得到改善。\n\n"
            "训练应用：无氧间歇训练的强度应设定在 vVO2max 之上（即 >100% vVO2max），"
            "工作时间 10-30 秒，组间恢复比 1:3 至 1:6（如 15 秒工作：60 秒恢复）。"
            "单节课总高强度工作时间不超过 5-8 分钟。"
            "每周此类训练不超过 1-2 次，且与有氧间歇训练穿插安排。"
        ),
        "language": "zh",
        "domain_pack": "endurance_training_protocols",
        "evidence_domain": "sports_science_reference",
        "knowledge_layer": "domain_pack",
        "allowed_use": "explanation",
        "prescription_permission": "explanation_only",
        "quality_tier": "systematic_review",
        "needs_review": False,
        "exclude_from_training_generation": False,
        "source_authority": "B",
        "domain_terms": ["无氧间歇", "Billat", "vVO2max", "糖原分解", "跑步经济性", "超最大强度", "短间歇"],
    },

    # ═══ Bosquet 2007 — 减量期荟萃分析 ═══
    {
        "chunk_id": "kb_bosquet_taper_meta_2007_abstract",
        "source_file": "Bosquet_2007_Tapering_MetaAnalysis.pdf",
        "source_registry_id": "src_bosquet_taper_meta_2007",
        "local_path": "data/domain_docs/Bosquet_2007_Tapering_MetaAnalysis.pdf",
        "page": 1, "paragraph_index": 0, "char_start": 0, "char_end": 2500,
        "text": (
            "【减量训练对运动表现的影响：荟萃分析（Bosquet et al. 2007）】\n"
            "期刊：Medicine & Science in Sports & Exercise, 2007, 39(8):1358-1365。\n"
            "作者：Laurent Bosquet, Jonathan Montpetit, Denis Arvisais, Inigo Mujika。\n"
            "设计：荟萃分析（Meta-Analysis），纳入 27 项研究（共 182 篇候选文献）。\n\n"
            "核心发现：\n"
            "1. 最优减量时长：2 周（8-14 天）。总效应量（Effect Size）= 0.59 ± 0.33，P < 0.001。\n"
            "2. 训练量削减幅度：指数式递减 41-60%。效应量 = 0.72 ± 0.36，P < 0.001——"
            "这是所有减量变量中效应量最大的。\n"
            "3. 训练强度：不可修改！维持减量前强度水平的效应量 = 0.33 ± 0.14，P < 0.001。\n"
            "   降低强度会破坏减量效果。\n"
            "4. 训练频次：维持 ≥80% 的减量前频次。维持频次的效应量 = 0.35 ± 0.17，P < 0.001。\n"
            "   降低频次不产生显著的额外收益。\n"
            "5. 平均成绩提升：约 1.96%（范围：-2.28% 至 +8.91%）。"
            "在精英水平，奖牌通常由 <1% 的差距决定，此提升幅度具有实际意义。\n\n"
            "训练应用：比赛前 2 周开始减量。跑量削减至巅峰期的 40-59%（即保留 41-60%）。"
            "强度必须保持——减量期的轻松跑配速不应比减量前更慢。"
            "训练频次可维持原样，每节课缩短而非跳过训练日。"
            "减量模式应为指数式递减（第一周削减幅度大于第二周），而非线性递减。"
        ),
        "language": "zh",
        "domain_pack": "endurance_training_protocols",
        "evidence_domain": "sports_science_reference",
        "knowledge_layer": "domain_pack",
        "allowed_use": "explanation",
        "prescription_permission": "explanation_only",
        "quality_tier": "meta_analysis",
        "needs_review": False,
        "exclude_from_training_generation": False,
        "source_authority": "B",
        "domain_terms": ["减量", "Taper", "Bosquet", "荟萃分析", "跑量削减", "比赛准备", "减量时长", "指数递减"],
    },

    # ═══ Buchheit & Laursen 2013 Part I — HIT 心肺部分 ═══
    {
        "chunk_id": "kb_buchheit_hit_cardio_2013_abstract",
        "source_file": "Buchheit_Laursen_2013_HIT_Part_I_Cardiopulmonary.pdf",
        "source_registry_id": "src_buchheit_hit_cardio_2013",
        "local_path": "data/domain_docs/Buchheit_Laursen_2013_HIT_Part_I_Cardiopulmonary.pdf",
        "page": 1, "paragraph_index": 0, "char_start": 0, "char_end": 2000,
        "text": (
            "【高强度间歇训练的编程方案：第一部分——心肺重点（Buchheit & Laursen 2013）】\n"
            "期刊：Sports Medicine, 2013, 43(5):313-338。\n"
            "作者：Martin Buchheit, Paul B Laursen。\n\n"
            "核心内容：\n"
            "1. HIT（高强度间歇训练）是目前改善心肺和代谢功能、提升运动员体能表现的"
            "最有效手段之一。\n"
            "2. 最佳刺激标准：运动员每节课至少在其"红区"（red zone）中停留数分钟。\n"
            "   "红区"定义为 ≥90% VO2max 的强度区间。\n"
            "3. HIT 训练处方的编程涉及至少九个变量：\n"
            "   - 工作段强度（work interval intensity）\n"
            "   - 工作段时长（work interval duration）\n"
            "   - 恢复段强度（relief interval intensity）\n"
            "   - 恢复段时长（relief interval duration）\n"
            "   - 运动模式（exercise modality）\n"
            "   - 重复次数（number of repetitions）\n"
            "   - 组数/系列数（number of series）\n"
            "   - 组间恢复时长（between-series recovery duration）\n"
            "   - 组间恢复强度（between-series recovery intensity）\n"
            "4. 操纵任何一个变量都会影响急性生理反应。\n"
            "5. 除了 T@VO2max（红区时间），编程时还应考虑：心血管做功、"
            "无氧糖酵解能量贡献、急性神经肌肉负荷和肌肉骨骼应变。\n\n"
            "训练应用：设计 HIT 课时需同时考虑上述九个变量，不能只关注组数和距离。"
            "工作段与恢复段的比例（work:rest ratio）是决定训练刺激性质的关键——"
            "短恢复比（如 1:1）偏向有氧刺激，长恢复比（如 1:4）偏向速度和神经肌肉刺激。"
        ),
        "language": "zh",
        "domain_pack": "endurance_training_protocols",
        "evidence_domain": "sports_science_reference",
        "knowledge_layer": "domain_pack",
        "allowed_use": "explanation",
        "prescription_permission": "explanation_only",
        "quality_tier": "narrative_review",
        "needs_review": False,
        "exclude_from_training_generation": False,
        "source_authority": "B",
        "domain_terms": ["高强度间歇训练", "HIT", "Buchheit", "Laursen", "红区时间", "九变量", "心肺适应"],
    },

    # ═══ Buchheit & Laursen 2013 Part II — HIT 无氧/神经肌肉部分 ═══
    {
        "chunk_id": "kb_buchheit_hit_anaerobic_2013_abstract",
        "source_file": "Buchheit_Laursen_2013_HIT_Part_II_Anaerobic.pdf",
        "source_registry_id": "src_buchheit_hit_anaerobic_2013",
        "local_path": "data/domain_docs/Buchheit_Laursen_2013_HIT_Part_II_Anaerobic.pdf",
        "page": 1, "paragraph_index": 0, "char_start": 0, "char_end": 2500,
        "text": (
            "【高强度间歇训练的编程方案：第二部分——无氧能量、神经肌肉负荷与实践应用（Buchheit & Laursen 2013）】\n"
            "期刊：Sports Medicine, 2013, 43(10):927-954。\n"
            "作者：Martin Buchheit, Paul B Laursen。\n\n"
            "核心内容：\n"
            "1. HIT 的四种主要格式：\n"
            "   a) 长间歇 HIT（Long Intervals）：>2-3 分钟，强度 ≥95% vVO2max。\n"
            "      经典应用：4-5 × 4min @ 90-95% HRmax，组间 3min 主动恢复。\n"
            "   b) 短间歇 HIT（Short Intervals）：≥15 秒，强度 100-120% vVO2max。\n"
            "      经典应用：30s/30s 或 60s/60s，总工作时间 10-20 分钟。\n"
            "   c) 重复冲刺训练（Repeated-Sprint Training, RST）：>4 秒，全力冲刺，含变向/跳跃。\n"
            "   d) 冲刺间歇训练（Sprint Interval Training, SIT）：>20-30 秒，全力冲刺。\n"
            "2. 跑者可以在单节 HIT 课中累积 6-8 km 的 vVO2max 距离。\n"
            "3. 对一天两练的运动员（twice a day training），必须考虑额外的生理应变——\n"
            "   避免过度负荷并优化适应。应在每周微周期中平衡代谢系统和神经肌肉系统的训练。\n"
            "4. 高运动速度/功率要求（≥95% v/pVO2max 至 100% 最大冲刺速度）加上高强度下的大量积累"
            "（单节课可达 6-8 km vVO2max）会造成显著的神经肌肉/骨骼系统负荷。\n"
            "5. 对比产生相似（乃至最大）心肺反应的 HIT 格式——它们可能伴随截然不同的无氧能量贡献。\n\n"
            "训练应用：\n"
            "- 业余跑者单节 HIT 课的 vVO2max 距离上限建议为 4-5 km，而非精英的 6-8 km。\n"
            "- 四种 HIT 格式应轮换使用，避免神经肌肉适应停滞。\n"
            "- 一天两练时，HIT 课应安排在上午，下午为低强度恢复课。\n"
            "- 业余跑者每周 HIT 不超过 2 次，且两次之间间隔 ≥72 小时。"
        ),
        "language": "zh",
        "domain_pack": "endurance_training_protocols",
        "evidence_domain": "sports_science_reference",
        "knowledge_layer": "domain_pack",
        "allowed_use": "explanation",
        "prescription_permission": "explanation_only",
        "quality_tier": "narrative_review",
        "needs_review": False,
        "exclude_from_training_generation": False,
        "source_authority": "B",
        "domain_terms": ["高强度间歇训练", "HIT格式", "Buchheit", "长间歇", "短间歇", "冲刺训练", "神经肌肉负荷", "一天两练"],
    },

    # ═══ Pfitzinger 周课表结构（教材摘要） ═══
    {
        "chunk_id": "kb_pfitzinger_weekly_structure_summary",
        "source_file": "Pfitzinger_Douglas_Advanced_Marathoning_3e.md",
        "source_registry_id": "src_pfitzinger_advanced_marathoning_3e",
        "local_path": "data/domain_docs/Pfitzinger_Douglas_Advanced_Marathoning_3e.md",
        "page": 0, "paragraph_index": 0, "char_start": 0, "char_end": 2500,
        "text": (
            "【Pfitzinger Advanced Marathoning 周课表结构模板（A 级教材来源）】\n"
            "来源：Pfitzinger & Douglas, Advanced Marathoning, 3rd Edition, Human Kinetics。\n\n"
            "Pfitzinger 为不同周跑量（18-55+ 英里/周）提供了完整的训练计划模板，"
            "其周课表结构遵循一致的逻辑：\n\n"
            "## 各阶段典型周课表结构\n\n"
            "### 基础期（Base Phase，约前 1/3 训练周期）\n"
            "- 周二/周三：一般有氧跑（General Aerobic, 8-15km）\n"
            "- 周四：乳酸阈值训练（Lactate Threshold, 13-16km 含 4-6km @LT 配速）\n"
            "- 周六：恢复跑（Recovery, 5-8km）\n"
            "- 周日：长距离跑（Long Run, 20-29km @Z2-Z3）\n"
            "- 其余日：休息或一般有氧跑\n"
            "- 强度课数量：1 节/周（仅 LT 跑）\n\n"
            "### 建设期（Build Phase，约中期 1/3）\n"
            "- 周二：一般有氧跑\n"
            "- 周三：VO2max 间歇（如 5×1000m @5K pace）\n"
            "- 周五：乳酸阈值跑或马拉松配速跑\n"
            "- 周日：长距离跑（可能含 MP 段落）\n"
            "- 强度课数量：2 节/周（VO2max + LT/MP）\n\n"
            "### 巅峰期/比赛专项期（Peak Phase，约后 1/3，最后 6-8 周）\n"
            "- 周二：一般有氧跑\n"
            "- 周三：VO2max 间歇或 LT 跑\n"
            "- 周五/周六：马拉松配速跑或比赛模拟\n"
            "- 周日：含 MP 段落的长距离\n"
            "- 强度课数量：2-3 节/周\n\n"
            "### 减量期（Taper，最后 2-3 周）\n"
            "- 维持强度但缩短每节课的距离\n"
            "- 强度课数量：1 节/周（最后一周可能为 0 节纯强度课）\n"
            "- 长距离缩短至 13-16km\n"
            "- 频次维持，只是每节课缩短\n\n"
            "## 强度课间隔原则\n"
            "- 两节强度课之间至少隔 2 天（如周三 + 周六）\n"
            "- 长距离跑的前一天不应有强度课\n"
            "- 强度课后第二天安排恢复跑或完全休息"
        ),
        "language": "zh",
        "domain_pack": "endurance_training_protocols",
        "evidence_domain": "sports_science_reference",
        "knowledge_layer": "domain_pack",
        "allowed_use": "explanation",
        "prescription_permission": "explanation_only",
        "quality_tier": "textbook",
        "needs_review": False,
        "exclude_from_training_generation": False,
        "source_authority": "A",
        "domain_terms": ["周课表", "Pfitzinger", "阶段结构", "基础期", "建设期", "巅峰期", "减量期", "强度课间隔", "训练周期"],
    },

    # ═══ Daniels 训练类型参数（教材摘要） ═══
    {
        "chunk_id": "kb_daniels_training_types_summary",
        "source_file": "Daniels_Running_Formula_4e.md",
        "source_registry_id": "src_daniels_running_formula_4e",
        "local_path": "data/domain_docs/Daniels_Running_Formula_4e.md",
        "page": 0, "paragraph_index": 0, "char_start": 0, "char_end": 3000,
        "text": (
            "【Daniels Running Formula 训练强度分类与参数（A 级教材来源）】\n"
            "来源：Jack Daniels, Daniels' Running Formula, 4th Edition, Human Kinetics。\n\n"
            "Daniels 将训练分为五个强度区（E/M/T/I/R），每个区有明确的生理依据和处方参数：\n\n"
            "## E 跑（Easy Running，轻松跑）\n"
            "- 强度：59-74% VO2max，65-78% HRmax\n"
            "- 目的：建立有氧基础、促进恢复、积累跑量\n"
            "- 单次时长：20-90 分钟（取决于周跑量和训练阶段）\n"
            "- 每周频次：可每天做，占周总跑量的多数\n"
            "- 恢复需求：不需要特别恢复——E 跑本身就是恢复\n\n"
            "## M 跑（Marathon-Pace Running，马拉松配速跑）\n"
            "- 强度：75-84% VO2max，80-89% HRmax\n"
            "- 目的：适应比赛配速的代谢需求\n"
            "- 单次时长：连续 8-15km @MP，或嵌入在长距离跑中\n"
            "- 每周频次：比赛专项期每周 1 次\n\n"
            "## T 跑（Threshold Running，阈值跑/节奏跑）\n"
            "- 强度：83-88% VO2max，88-92% HRmax\n"
            "- 生理对应：约在乳酸阈值附近\n"
            "- 单次时长：连续 20-30 分钟（不可超过 30 分钟——超过则非 T 区）\n"
            "- 替代形式：巡航间歇（Cruise Intervals）——如 5-6×1km @T 配速，组间 1min 休息\n"
            "- 每周频次：1 次/周\n"
            "- 关键原则：T 跑的关键是「你能不停跑的最快配速，持续 20 分钟」。\n"
            "  如果只能跑 15 分钟，说明配速太快。如果能跑 40 分钟，说明配速太慢。\n\n"
            "## I 跑（Interval Running，间歇跑/摄氧量间歇）\n"
            "- 强度：95-100% VO2max，98-100% HRmax\n"
            "- 目的：最大化 VO2max 刺激\n"
            "- 单段时长：3-5 分钟（≤5 分钟——超过则主要刺激非 VO2max）\n"
            "- 组间恢复：等于或略少于工作时间（如 3min 工作 + 2-3min 慢跑恢复）\n"
            "- 单节课总量：总 I 跑时间 ≤8 分钟或 ≤10km 总量（取较小者）\n"
            "- 每周频次：1 次/周\n\n"
            "## R 跑（Repetition Running，重复跑/速度跑）\n"
            "- 强度：>100% VO2max，全力或接近全力\n"
            "- 目的：改善跑步经济性（Running Economy）和速度\n"
            "- 单段时长：≤2 分钟（通常 200-600m）\n"
            "- 组间恢复：充分恢复（工作:休息 = 1:2 至 1:3）\n"
            "- 单节课总量：总 R 跑距离 ≤5km\n"
            "- 每周频次：1 次/周，通常在 I 跑或 T 跑的不同日\n\n"
            "## 强度课组合原则\n"
            "- 每周最多 2 节高强度课（T/I/R 中选两节）\n"
            "- 两节高强度课之间至少 48 小时\n"
            "- I 跑和 R 跑不在同一天做\n"
            "- 长距离跑（E 和 M 的混合）不和高强度课挤在同一天"
        ),
        "language": "zh",
        "domain_pack": "endurance_training_protocols",
        "evidence_domain": "sports_science_reference",
        "knowledge_layer": "domain_pack",
        "allowed_use": "explanation",
        "prescription_permission": "explanation_only",
        "quality_tier": "textbook",
        "needs_review": False,
        "exclude_from_training_generation": False,
        "source_authority": "A",
        "domain_terms": ["Daniels", "VDOT", "E跑", "M跑", "T跑", "I跑", "R跑", "阈值跑", "间歇跑", "重复跑", "强度分区", "训练参数"],
    },
]


def main():
    existing = []
    existing_ids = set()
    if KB_JSONL.exists():
        for line in KB_JSONL.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            existing.append(stripped)
            try:
                existing_ids.add(json.loads(stripped).get("chunk_id", ""))
            except json.JSONDecodeError:
                pass

    added = 0
    for chunk in CHUNKS:
        if chunk["chunk_id"] not in existing_ids:
            existing.append(json.dumps(chunk, ensure_ascii=False))
            existing_ids.add(chunk["chunk_id"])
            added += 1
            print(f"  + {chunk['chunk_id']}")

    if added:
        KB_JSONL.write_text("\n".join(existing) + "\n", encoding="utf-8")
        print(f"Done: added {added} chunks, total {len(existing)}")
        print(f"Training protocol chunks: {len(existing)}")
    else:
        print("All chunks already exist (noop)")


if __name__ == "__main__":
    main()
