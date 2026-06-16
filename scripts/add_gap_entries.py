"""一次性生成 27 条新动作库条目 (P2-P8)。"""
import json, sys

jsonl_path = 'data/knowledge/curated/action_library/action_library_chunks.jsonl'
with open(jsonl_path, 'r', encoding='utf-8') as f:
    existing = [json.loads(line.strip()) for line in f if line.strip()]

existing_ids = {e['chunk_id'] for e in existing}

# 辅助函数：创建一条动作库条目模板
def make_entry(cid, src_file, src_reg_id, text, authority, domain_terms, tags, warmup="", cooldown="", page=0):
    return {
        "chunk_id": cid, "source_file": src_file, "source_registry_id": src_reg_id,
        "local_path": src_file, "page": page, "paragraph_index": 0, "char_start": 0, "char_end": 0,
        "text": text, "language": "zh", "domain_pack": "action_library",
        "evidence_domain": "action_library", "knowledge_layer": "domain_pack",
        "allowed_use": "core_prescription", "prescription_permission": "can_write_core",
        "quality_tier": "reviewed", "needs_review": False, "exclude_from_training_generation": False,
        "source_authority": authority, "domain_terms": domain_terms,
        "warmup_suggestion": warmup, "cooldown_suggestion": cooldown, "tags": tags,
    }

REF_D = "references/Daniels_Running_Formula_4e.md"
REG_D = "src_ref_daniels_running_formula_4e"
REF_P = "references/Pfitzinger_Advanced_Marathoning_3e.md"
REG_P = "src_ref_pfitzinger_advanced_marathoning_3e"
REF_B = "references/Bompa_Periodization_6e.md"
REG_B = "src_ref_bompa_periodization_6e"

A = "A"

NEW = [
    # ═══ P2: Z1 恢复跑 (3条) ═══
    make_entry("action_lib_recovery_z1_v1", REF_D, REG_D,
        "name：30min 极松恢复跑\ncategories：Recovery , Easy , Active-Rest\n"
        "content：30min Z1，心率 <72% LTHR，可聊天配速。全程不做加速，不冲坡。步频轻松自然，步幅小。\n"
        "zone_range：Z1\n"
        "objective：主动恢复（Active Recovery），促进血流带走代谢废物，不产生额外训练负荷。适合在高质量强度课之间次日执行。\n"
        "warmup_suggestion：无需专门热身，直接慢跑开始\n"
        "cooldown_suggestion：无需冷身，停下来直接进入补水与放松\n"
        "alternative_workout：如果疲劳感极强，可改为 30min 饭后散步或完全休息",
        A, ["恢复跑","Recovery Run","Z1","Daniels E","主动恢复"],
        {"workout_name":"30min 极松恢复跑","categories":"Recovery, Easy, Active-Rest","zone_range":"Z1","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "无需专门热身","无需冷身", 87),

    make_entry("action_lib_recovery_z1_v2", REF_P, REG_P,
        "name：45min 恢复跑 + 跨步练习\ncategories：Recovery , Strides , Active-Rest\n"
        "content：45min Z1，心率 <75% LTHR。最后 4-6 次 × 20 秒轻柔跨步（不冲刺，控制在 Z5-Z6 上限），感受快速步频而不产生乳酸堆积。\n"
        "zone_range：Z1, Z5-Z6\n"
        "objective：综合恢复 + 神经肌肉激活（Neural Activation）。Pfitzinger 强调恢复跑不仅是代谢恢复，还包括在低强度下保持正确跑姿的神经模式。\n"
        "warmup_suggestion：前 10min 特别慢，逐渐放松到 Z1 稳定节奏\n"
        "cooldown_suggestion：跨步后 5min 慢走 + 小腿和腘绳肌放松\n"
        "alternative_workout：如果疲劳过高，取消跨步跑，只做 45min Z1",
        A, ["恢复跑","Recovery Run","Strides","Z1","Pfitzinger","主动恢复"],
        {"workout_name":"45min 恢复跑 + 跨步练习","categories":"Recovery, Strides, Active-Rest","zone_range":"Z1, Z5-Z6","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "前 10min 特别慢，逐渐放松到 Z1 稳定节奏","跨步后 5min 慢走"),

    make_entry("action_lib_recovery_z1_v3", REF_B, REG_B,
        "name：20min 最短恢复跑\ncategories：Recovery , Minimal-Dose\n"
        "content：20min Z1，极高疲劳日的最低有效剂量（Minimal Effective Dose）。"
        "不过度（不触发进一步疲劳），但也不完全不活动（避免僵硬和血液循环停滞）。\n"
        "zone_range：Z1\n"
        "objective：Bompa 主动恢复原则——最低训练量产生恢复刺激，不产生额外训练负荷。"
        "适用场景：前一天有高强度比赛/测试/极高强度训练课。\n"
        "warmup_suggestion：无需热身\n"
        "cooldown_suggestion：5min 静态拉伸即可\n"
        "alternative_workout：完全休息 + 饭后轻度散步替代",
        A, ["恢复跑","Recovery Run","Minimum Effective Dose","Z1","Bompa","主动恢复"],
        {"workout_name":"20min 最短恢复跑","categories":"Recovery, Minimal-Dose","zone_range":"Z1","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "无需热身","5min 静态拉伸即可"),

    # ═══ P3: Z2-Z3 一般有氧跑 (5条) ═══
    make_entry("action_lib_general_aerobic_z2z3_v1", REF_P, REG_P,
        "name：40min 稳定有氧跑（GA Base）\ncategories：Aerobic , Base , Endurance\n"
        "content：40min Z2 稳态，心率 72-78% LTHR，匀速巡航。新手或恢复期中课量，不追求配速，关注呼吸节奏。\n"
        "zone_range：Z2-Z3\n"
        "objective：线粒体增生基础（Mitochondrial Biogenesis），有氧基础构建。适合作为工作日早晨或下午的常规有氧课。\n"
        "warmup_suggestion：前 5min 从走过渡到轻松慢跑\n"
        "cooldown_suggestion：慢走 5min\n"
        "alternative_workout：若时间不够，可改为 30min Z2",
        A, ["一般有氧跑","General Aerobic","Z2-Z3","Pfitzinger","线粒体增生","有氧基础"],
        {"workout_name":"40min 稳定有氧跑（GA Base）","categories":"Aerobic, Base, Endurance","zone_range":"Z2-Z3","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "前 5min 从走过渡到轻松慢跑","慢走 5min"),

    make_entry("action_lib_general_aerobic_z2z3_v2", REF_P, REG_P,
        "name：60min 标准一般有氧跑（GA Standard）\ncategories：Aerobic , Endurance\n"
        "content：60min Z2-Z3，心率 72-84% LTHR。Pfitzinger 计划中最常见的周中训练课，占周跑量主体的低强度积累。\n"
        "zone_range：Z2-Z3\n"
        "objective：有氧容量维护（Aerobic Maintenance）。毛细血管密度提升、慢肌纤维氧化酶上调。每周 2-3 次执行。\n"
        "warmup_suggestion：前 10min 逐渐从 Z1 过渡到 Z2\n"
        "cooldown_suggestion：慢走 5min + 简单放松拉伸\n"
        "alternative_workout：若当周已有长距离课，可缩短至 45min；若疲劳高，降为 Z1-Z2 轻松跑",
        A, ["一般有氧跑","General Aerobic","Z2-Z3","Pfitzinger","有氧容量","日常训练"],
        {"workout_name":"60min 标准一般有氧跑（GA Standard）","categories":"Aerobic, Endurance","zone_range":"Z2-Z3","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "前 10min 逐渐从 Z1 过渡到 Z2","慢走 5min + 简单放松拉伸"),

    make_entry("action_lib_general_aerobic_z2z3_v3", REF_D, REG_D,
        "name：75min 有氧耐力跑（Daniels E Extended）\ncategories：Aerobic , Endurance , Fat-Oxidation\n"
        "content：75min Z2，心率 <78% LTHR，配速稳定。Daniels 强调 E 跑的核心是足够慢才能跑得足够多。\n"
        "zone_range：Z2-Z3\n"
        "objective：毛细血管密度提升（Capillarization）和脂肪氧化能力建设。长时 E 跑比短时 E 跑更能刺激线粒体网络扩展。适合作为次要长距离课。\n"
        "warmup_suggestion：前 15min 心率逐步爬升到 Z2\n"
        "cooldown_suggestion：5min 慢走 + 补水 + 能量补充\n"
        "alternative_workout：可拆为 40min AM + 35min PM 双跑（仅进阶跑者）",
        A, ["有氧耐力","Daniels E","Z2-Z3","脂肪氧化","毛细血管密度","长时间低强度"],
        {"workout_name":"75min 有氧耐力跑（Daniels E Extended）","categories":"Aerobic, Endurance, Fat-Oxidation","zone_range":"Z2-Z3","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "前 15min 心率逐步爬升到 Z2","5min 慢走 + 补水 + 能量补充"),

    make_entry("action_lib_general_aerobic_z2z3_v4", REF_P, REG_P,
        "name：90min 中等长距离有氧跑（Medium-Long Run）\ncategories：Aerobic , Medium-Long , Endurance\n"
        "content：90min Z2-Z3。介于日常有氧跑和真正 LSD 之间的中长距离有氧课。Pfitzinger 计划中周中第二长课，为周末长距离提供耐受基础。\n"
        "zone_range：Z2-Z3\n"
        "objective：糖原节约适应（Glycogen Sparing），使身体在有氧范围内更高效地使用脂肪而非糖原。同时提升肌肉和结缔组织对持续负荷的耐受性。\n"
        "warmup_suggestion：前 15min Z1→Z2 逐渐过渡\n"
        "cooldown_suggestion：10min 慢走 + 拉伸 + 补水，注意补充糖原\n"
        "alternative_workout：可拆为 50min AM + 40min PM，或缩短至 75min",
        A, ["中等长距离","Medium-Long Run","Z2-Z3","Pfitzinger","糖原节约","有氧耐力"],
        {"workout_name":"90min 中等长距离有氧跑（Medium-Long Run）","categories":"Aerobic, Medium-Long, Endurance","zone_range":"Z2-Z3","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "前 15min Z1→Z2 逐渐过渡","10min 慢走 + 拉伸 + 补水，注意补充糖原"),

    make_entry("action_lib_general_aerobic_z2z3_v5", REF_P, REG_P,
        "name：50min 有氧跑 + 跨步跑收尾（GA + Strides）\ncategories：Aerobic , Strides , Neuromuscular\n"
        "content：50min Z2-Z3 有氧稳定跑 + 收尾 4 × 100m 跨步跑（Z7-Z9），跨步间充分走回休息 2-3min。\n"
        "zone_range：Z2-Z3, Z7-Z9\n"
        "objective：有氧基础 + 神经肌肉经济性（Running Economy）兼顾的优化课。Pfitzinger 将跨步跑嵌入 GA 课末尾而非单独设课，减少训练天数占用。\n"
        "warmup_suggestion：前 10min Z1→Z2 过渡\n"
        "cooldown_suggestion：跨步后 5min 慢走 + 小腿动态放松\n"
        "alternative_workout：如果跨步段感觉过紧，可改为 2 次跨步 + 更充分的慢走恢复",
        A, ["一般有氧跑","跨步跑","GA+Strides","Z2-Z3","Pfitzinger","跑步经济性"],
        {"workout_name":"50min 有氧跑 + 跨步跑收尾（GA + Strides）","categories":"Aerobic, Strides, Neuromuscular","zone_range":"Z2-Z3, Z7-Z9","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "前 10min Z1→Z2 过渡","跨步后 5min 慢走 + 小腿动态放松"),

    # ═══ P4: Z5-Z6 连续节奏跑 (4条) ═══
    make_entry("action_lib_continuous_tempo_z5z6_v1", REF_D, REG_D,
        "name：20min 经典节奏跑（Daniels T Run）\ncategories：Threshold , Tempo , Lactate-Clearance\n"
        "content：充分热身→20min 连续 Z5-Z6（90-97% LTHR，约 83-88% VO2max 速度）→充分冷身。不要停顿、不走、不间歇。\n"
        "zone_range：Z5-Z6\n"
        "objective：乳酸清除效率（Lactate Clearance）训练。Daniels T 的核心是你能不停跑的最快配速持续 20min。产生并同时清除乳酸，提高身体在阈值边界的巡航能力。\n"
        "warmup_suggestion：15min 轻松跑 + 4 × 100m 渐加速 + 动态拉伸\n"
        "cooldown_suggestion：10min 慢跑冷身，帮助乳酸代谢\n"
        "alternative_workout：若感觉 20min 过长，拆为 2 × 10min T，组间 3min 慢跑恢复",
        A, ["连续节奏跑","Continuous Tempo","Z5-Z6","Daniels T","乳酸清除","阈值训练"],
        {"workout_name":"20min 经典节奏跑（Daniels T Run）","categories":"Threshold, Tempo, Lactate-Clearance","zone_range":"Z5-Z6","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "15min 轻松跑 + 4 × 100m 渐加速 + 动态拉伸","10min 慢跑冷身，帮助乳酸代谢"),

    make_entry("action_lib_continuous_tempo_z5z6_v2", REF_P, REG_P,
        "name：30min 延长节奏跑（Pfitzinger LT Run）\ncategories：Threshold , Tempo , Sustained-LT\n"
        "content：30min 连续 Z5-Z6（LT 配速），全程不降速。Pfitzinger 的 LT 跑比 Daniels 长 50%，强调在乳酸阈值长时间巡航的纯适应。\n"
        "zone_range：Z5-Z6\n"
        "objective：延长乳酸阈值巡航时间（Sustained LT）。Pfitzinger 认为 20min T 对全马/半马选手而言刺激时长不足，30min 能更充分触发线粒体琥珀酸脱氢酶上调。\n"
        "warmup_suggestion：15-20min 轻松跑 + 动态拉伸 + 5 × 60m 渐加速\n"
        "cooldown_suggestion：10-15min 慢跑冷身\n"
        "alternative_workout：能力不足者可分两段：2 × 15min T 配速，3min 慢跑恢复",
        A, ["连续节奏跑","Pfitzinger LT","Z5-Z6","阈值巡航","乳酸阈值","琥珀酸脱氢酶"],
        {"workout_name":"30min 延长节奏跑（Pfitzinger LT Run）","categories":"Threshold, Tempo, Sustained-LT","zone_range":"Z5-Z6","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "15-20min 轻松跑 + 动态拉伸 + 5 × 60m 渐加速","10-15min 慢跑冷身"),

    make_entry("action_lib_continuous_tempo_z5z6_v3", REF_P, REG_P,
        "name：2 × 15min 分段节奏跑（Pfitzinger LT Intervals）\ncategories：Threshold , Tempo , Cruise-Intervals\n"
        "content：2 × 15min Z5-Z6，组间 3min 慢跑恢复。总 T 时间 30min，分段降低心理耐受压力。\n"
        "zone_range：Z5-Z6\n"
        "objective：与 30min 连续 T 跑相同的总刺激量，但心理负荷更低。适合初次接触节奏跑的跑者，或心理疲劳较高的训练阶段。\n"
        "warmup_suggestion：15min 轻松跑 + 4 × 80m 渐加速\n"
        "cooldown_suggestion：10min 慢跑冷身\n"
        "alternative_workout：可变为 3 × 10min T 配速，组间 2min 慢跑",
        A, ["分段节奏跑","Pfitzinger LT Intervals","Z5-Z6","巡航间歇","阈值训练"],
        {"workout_name":"2 × 15min 分段节奏跑（Pfitzinger LT Intervals）","categories":"Threshold, Tempo, Cruise-Intervals","zone_range":"Z5-Z6","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "15min 轻松跑 + 4 × 80m 渐加速","10min 慢跑冷身"),

    make_entry("action_lib_continuous_tempo_z5z6_v4", REF_D, REG_D,
        "name：25min 渐进节奏跑（Tempo Progression）\ncategories：Threshold , Progression , Lactate-Accumulation\n"
        "content：充分热身→5min Z4（有氧阈值上沿）→10min Z5→5min Z5 上沿靠近 Z6→5min Z6 乳酸积聚段→冷身。全程不中断，速度阶梯式上升。\n"
        "zone_range：Z4-Z6\n"
        "objective：渐进式 T 跑从有氧阈平滑过渡到乳酸阈上限，训练身体逐步处理乳酸堆积而非突然进入高乳酸状态。模拟比赛中后程配速逐渐提升的场景。\n"
        "warmup_suggestion：15min 轻松跑 + 动态拉伸 + 4 × 60m 加速\n"
        "cooldown_suggestion：10-15min 慢跑冷身，特别注意排酸\n"
        "alternative_workout：如果后段感觉吃力，最后一档从 Z6 降为 Z5，总长仍为 25min",
        A, ["渐进节奏跑","Tempo Progression","Z4-Z6","Daniels T","乳酸渐进","比赛模拟"],
        {"workout_name":"25min 渐进节奏跑（Tempo Progression）","categories":"Threshold, Progression, Lactate-Accumulation","zone_range":"Z4-Z6","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "15min 轻松跑 + 动态拉伸 + 4 × 60m 加速","10-15min 慢跑冷身，特别注意排酸"),

    # ═══ P5: MP 混合长距离 (5条) ═══
    make_entry("action_lib_mp_mixed_long_v1", REF_P, REG_P,
        "name：21km 后段比赛配速长距离（Long/MP 17+4）\ncategories：Long-Run , Marathon-Pace , Race-Simulation\n"
        "content：17km Z2-Z3（巡航段）+ 4km Z4-Z5（100% MP/HMP 比赛配速），总 21km。注意：MP 段放在跑量累积后执行，而非体能充沛时。\n"
        "zone_range：Z2-Z3, Z4-Z5\n"
        "objective：模拟比赛后半程的代谢状态——在糖原已部分消耗的情况下维持目标配速。Pfitzinger 称此为最重要的长距离课，比赛日 3-4 周前执行。\n"
        "warmup_suggestion：前 2km 逐渐从 Z1→Z2 过渡进入巡航状态\n"
        "cooldown_suggestion：10min 慢走 + 拉伸 + 补水补糖\n"
        "alternative_workout：若疲劳明显，将 MP 段从 4km 减至 3km 或 2km",
        A, ["MP混合长距离","Long/MP","Z2-Z5","Pfitzinger","比赛模拟","配速长距离"],
        {"workout_name":"21km 后段比赛配速长距离（Long/MP 17+4）","categories":"Long-Run, Marathon-Pace, Race-Simulation","zone_range":"Z2-Z3, Z4-Z5","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "前 2km 逐渐从 Z1→Z2 过渡进入巡航状态","10min 慢走 + 拉伸 + 补水补糖"),

    make_entry("action_lib_mp_mixed_long_v2", REF_D, REG_D,
        "name：24km 中段比赛配速嵌入长距离（2×4km@MP）\ncategories：Long-Run , Marathon-Pace , Embedded-MP\n"
        "content：24km 总，巡航段 Z2-Z3→4km MP(Z4-Z5)→Z2 恢复巡航 2km→4km MP(Z4-Z5)→剩余巡航至 24km。两个 MP 段不连做，中间有 2km 低强度缓冲。\n"
        "zone_range：Z2-Z3, Z4-Z5\n"
        "objective：代谢振荡训练（Metabolic Oscillation）——在高-低-高配速间切换，训练身体在巡航状态和比赛状态之间高效转换代谢路径。Daniels M+E 混编思路。\n"
        "warmup_suggestion：前 3km Z1→Z2 过渡\n"
        "cooldown_suggestion：10min 慢走 + 补水补糖 + 拉伸\n"
        "alternative_workout：如果第二组 MP 段吃力，将 4km 缩短至 3km",
        A, ["MP混合长距离","代谢振荡","Z2-Z5","Daniels M+E","配速长距离","巡航恢复"],
        {"workout_name":"24km 中段比赛配速嵌入长距离（2×4km@MP）","categories":"Long-Run, Marathon-Pace, Embedded-MP","zone_range":"Z2-Z3, Z4-Z5","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "前 3km Z1→Z2 过渡","10min 慢走 + 补水补糖 + 拉伸"),

    make_entry("action_lib_mp_mixed_long_v3", REF_P, REG_P,
        "name：18km 后段强比赛配速长距离（Long/MP 12+6）\ncategories：Long-Run , Marathon-Pace , Aggressive-MP\n"
        "content：12km Z2-Z3→6km Z4-Z5 连续比赛配速，总 18km。比赛配速段更长（6km），适合进阶跑者在比赛前 3-4 周执行。\n"
        "zone_range：Z2-Z3, Z4-Z5\n"
        "objective：高级比赛代谢模拟——在 12km 巡航后执行 6km 连续的比赛配速，模拟比赛中后段体能被消耗但必须维持配速的生理和心理状态。\n"
        "warmup_suggestion：前 2km Z1→Z2 渐入\n"
        "cooldown_suggestion：10min 慢走 + 补水补糖 + 放松拉伸\n"
        "alternative_workout：配速段无法全程维持时，最后 1-2 km 可降为巡航恢复（85-90% HMP）",
        A, ["MP混合长距离","进阶配速","Z2-Z5","Pfitzinger","Long/MP aggressive","比赛模拟"],
        {"workout_name":"18km 后段强比赛配速长距离（Long/MP 12+6）","categories":"Long-Run, Marathon-Pace, Aggressive-MP","zone_range":"Z2-Z3, Z4-Z5","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "前 2km Z1→Z2 渐入","10min 慢走 + 补水补糖 + 放松拉伸"),

    make_entry("action_lib_mp_mixed_long_v4", REF_D, REG_D,
        "name：25km 巡航/配速交替长距离（3km/3km 交替）\ncategories：Long-Run , Marathon-Pace , Alternating-MP\n"
        "content：25km 总，分段：3km Z2 巡航→3km Z4-Z5 比赛配速→3km Z2 巡航→3km Z4-Z5 比赛配速→3km Z2 巡航→3km Z4-Z5 比赛配速→剩余巡航至 25km。共 3 组 MP 段，每组间 Z2 缓冲。\n"
        "zone_range：Z2-Z3, Z4-Z5\n"
        "objective：代谢振荡训练进阶版——多轮有氧/比赛配速交替，总配速段累计 9km。Daniels M+E 混编，训练身体在高/低配速间反复切换的代谢灵活性。\n"
        "warmup_suggestion：前 2km Z1→Z2 过渡\n"
        "cooldown_suggestion：10min 慢走 + 充分补水补糖 + 拉伸\n"
        "alternative_workout：配速段无法满负荷完成时，将 3km MP 段均减为 2km，总配速段降为 6km",
        A, ["MP混合长距离","交替配速","Z2-Z5","Daniels M+E","代谢灵活性","巡航恢复"],
        {"workout_name":"25km 巡航/配速交替长距离（3km/3km 交替）","categories":"Long-Run, Marathon-Pace, Alternating-MP","zone_range":"Z2-Z3, Z4-Z5","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "前 2km Z1→Z2 过渡","10min 慢走 + 充分补水补糖 + 拉伸"),

    make_entry("action_lib_mp_mixed_long_v5", REF_P, REG_P,
        "name：20km 渐进至比赛配速长距离（Progression Long to MP）\ncategories：Long-Run , Progression , Marathon-Pace\n"
        "content：20km 总，全程渐进：前 5km Z2→中 10km Z3 渐升至 Z4 上沿→最后 5km 渐升至 Z5 比赛配速并保持。不做分段式配速切换，而是一个梯度上升的连续过程。\n"
        "zone_range：Z2-Z5\n"
        "objective：平滑代谢过渡训练——Pfitzinger 的渐进长距离不设硬性 MP 段，而是让跑者自然找到体能允许的最高巡航速度，避免分段配速带来的心理压力和代谢冲击。\n"
        "warmup_suggestion：前 2km 非常轻松，不可强迫加速\n"
        "cooldown_suggestion：10min 慢走 + 补水补糖 + 充分拉伸\n"
        "alternative_workout：如果最后 5km 无法渐进至 Z5，停在 Z4 上沿即可，不做强制配速",
        A, ["渐进长距离","Progression Long","Z2-Z5","Pfitzinger","代谢平滑过渡","比赛配速"],
        {"workout_name":"20km 渐进至比赛配速长距离（Progression Long to MP）","categories":"Long-Run, Progression, Marathon-Pace","zone_range":"Z2-Z5","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "前 2km 非常轻松，不可强迫加速","10min 慢走 + 补水补糖 + 充分拉伸"),

    # ═══ P6: 跨步跑 Strides (2条) ═══
    make_entry("action_lib_strides_z7z9_v1", REF_D, REG_D,
        "name：6 × 100m 跨步跑（Daniels R Strides）\ncategories：Strides , Speed , Running-Economy\n"
        "content：6 × 100m Z7-Z9（80-90% 最大速度），充分间隔 2-3min 走回恢复。不在疲劳时做，通常在轻松跑后或独立进行。关注轻快步频和舒展跑姿，不求极限速度。\n"
        "zone_range：Z7-Z9\n"
        "objective：跑步经济性（Running Economy）——快肌纤维温和招募 + 神经协调模式优化。不产生有意义的乳酸积累。\n"
        "warmup_suggestion：10-15min 轻松慢跑 + 动态拉伸后开始\n"
        "cooldown_suggestion：跨步结束后 5min 慢走 + 轻度拉伸\n"
        "alternative_workout：若在非跑步日做，前需充分热身 10min 慢跑",
        A, ["跨步跑","Strides","Z7-Z9","Daniels R","跑步经济性","神经肌肉"],
        {"workout_name":"6 × 100m 跨步跑（Daniels R Strides）","categories":"Strides, Speed, Running-Economy","zone_range":"Z7-Z9","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "10-15min 轻松慢跑 + 动态拉伸后开始","跨步结束后 5min 慢走 + 轻度拉伸", 110),

    make_entry("action_lib_strides_z7z9_v2", REF_P, REG_P,
        "name：8 × 20 秒加速跑（Pfitzinger Strides）\ncategories：Strides , Acceleration , Neuromuscular\n"
        "content：8 × 20 秒渐加速至 Z8（约 90% 最大速度的一档），充分恢复（60-90s 慢走或原地恢复）。从慢跑开始→加速 5 秒→达 Z8→减速慢跑结束。Pfitzinger 强调 Strides 是加速跑不是冲刺跑。\n"
        "zone_range：Z7-Z9\n"
        "objective：神经肌肉效率——在不产生明显乳酸的情况下，训练快速肌纤维和神经系统在高速跑姿下的协调性。与 Daniels 的核心区别：按时间（20s）而非距离（100m）设计。\n"
        "warmup_suggestion：10-15min 轻松慢跑\n"
        "cooldown_suggestion：5min 慢走\n"
        "alternative_workout：可嵌入在轻松跑或 GA 跑末尾执行，节省独立训练日",
        A, ["跨步跑","Strides","Z7-Z9","Pfitzinger","加速跑","神经肌肉效率"],
        {"workout_name":"8 × 20 秒加速跑（Pfitzinger Strides）","categories":"Strides, Acceleration, Neuromuscular","zone_range":"Z7-Z9","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "10-15min 轻松慢跑","5min 慢走"),

    # ═══ P7: 比赛模拟跑 (4条) ═══
    make_entry("action_lib_race_simulation_v1", REF_P, REG_P,
        "name：10km 模拟赛（Pfitzinger Tune-up Race）\ncategories：Race-Simulation , Tune-up , Tempo\n"
        "content：10km 比赛配速 Z5-Z7。模拟赛前完整流程：前晚碳水补充→赛前热身 2km 慢跑 + 动态拉伸 + 4 × 80m 加速→10km 目标配速→赛后冷身 2km 慢跑 + 拉伸。穿比赛日鞋子和服装。\n"
        "zone_range：Z5-Z7\n"
        "objective：比赛心理演练 + 生理确认。Pfitzinger 建议比赛前 4-6 周和 2-3 周分别安排一次模拟赛，用于配速策略验证、补给方案测试和赛前紧张感管理。\n"
        "warmup_suggestion：2km 轻松慢跑 + 动态拉伸 + 4 × 80m 渐加速\n"
        "cooldown_suggestion：2km 慢跑冷身 + 补水 + 静态拉伸\n"
        "alternative_workout：若体质不佳或天气原因，改为 8km 非比赛状态轻松跑",
        A, ["比赛模拟跑","Tune-up Race","Z5-Z7","Pfitzinger","心理演练","补给测试"],
        {"workout_name":"10km 模拟赛（Pfitzinger Tune-up Race）","categories":"Race-Simulation, Tune-up, Tempo","zone_range":"Z5-Z7","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "2km 轻松慢跑 + 动态拉伸 + 4 × 80m 渐加速","2km 慢跑冷身 + 补水 + 静态拉伸"),

    make_entry("action_lib_race_simulation_v2", REF_P, REG_P,
        "name：16km 半马距离渐进模拟跑（Dress Rehearsal）\ncategories：Race-Simulation , Dress-Rehearsal , HM-Specific\n"
        "content：16km 总：4km Z2 轻松→8km Z4-Z5（100% HMP 比赛配速）→4km Z5-Z6（105% HMP 冲刺模拟）。模拟比赛前慢后快的配速策略。\n"
        "zone_range：Z2-Z6\n"
        "objective：半马彩排——从小到大渐进至比赛配速并超速收尾，模拟比赛日开局稳、中局巡航、末段提速的典型配速曲线。同时验证比赛补给方案在中等距离下的耐受性。\n"
        "warmup_suggestion：15min 轻松慢跑 + 动态拉伸 + 4 × 60m 加速\n"
        "cooldown_suggestion：10-15min 慢跑冷身 + 补水 + 拉伸\n"
        "alternative_workout：如果无法完成 105% HMP 段，改为 8km@100% HMP 连续，不做冲刺段",
        A, ["比赛模拟跑","半马彩排","Z2-Z6","Pfitzinger","Dress Rehearsal","配速策略"],
        {"workout_name":"16km 半马距离渐进模拟跑（Dress Rehearsal）","categories":"Race-Simulation, Dress-Rehearsal, HM-Specific","zone_range":"Z2-Z6","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "15min 轻松慢跑 + 动态拉伸 + 4 × 60m 加速","10-15min 慢跑冷身 + 补水 + 拉伸"),

    make_entry("action_lib_race_simulation_v3", REF_D, REG_D,
        "name：8km 减量期模拟跑（Taper Simulation）\ncategories：Race-Simulation , Taper , Confidence-Builder\n"
        "content：8km Z5 目标比赛配速。减量周内（比赛前 7-10 天）执行，目的是建立信心而非产生适应。全程不过度用力，重要的是把比赛配速跑舒服。\n"
        "zone_range：Z5\n"
        "objective：信心建设——在减量期内用比赛配速短距离跑，让身体和心理记住目标配速的感觉而不产生疲劳。Daniels 赛前减量原则：量降质不降。\n"
        "warmup_suggestion：10min 轻松慢跑 + 动态拉伸 + 3 × 50m 加速\n"
        "cooldown_suggestion：10min 慢跑冷身，不可过度拉伸\n"
        "alternative_workout：如果比赛前感觉过度紧张或睡眠不足，改为 5km 轻松跑 + 心理演练",
        A, ["比赛模拟跑","减量模拟","Z5","Daniels","减量期","信心建设"],
        {"workout_name":"8km 减量期模拟跑（Taper Simulation）","categories":"Race-Simulation, Taper, Confidence-Builder","zone_range":"Z5","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "10min 轻松慢跑 + 动态拉伸 + 3 × 50m 加速","10min 慢跑冷身，不可过度拉伸"),

    make_entry("action_lib_race_simulation_v4", REF_P, REG_P,
        "name：2 × 5km 比赛配速块（Pfitzinger MP Blocks）\ncategories：Race-Simulation , Pace-Blocks , Tempo\n"
        "content：2 × 5km Z4-Z5（100% HMP），组间 1km Z2 浮动恢复。不做完整比赛距离，而是分两段配速块模拟比赛节奏，降低单次课的心理负荷。\n"
        "zone_range：Z4-Z5\n"
        "objective：配速纪律训练——在分段配速块中练习控制节奏不超速、组间恢复不降级。Pfitzinger 认为配速控制是非精英跑者最常犯的错误（开赛过快），这个训练专治此问题。\n"
        "warmup_suggestion：15min 轻松慢跑 + 动态拉伸 + 4 × 60m 加速\n"
        "cooldown_suggestion：10min 慢跑冷身\n"
        "alternative_workout：如果第一组配速块过快完成，第二组应刻意控制在目标配速 ±3s 内",
        A, ["比赛模拟跑","配速纪律","Z4-Z5","Pfitzinger","MP Blocks","节奏控制"],
        {"workout_name":"2 × 5km 比赛配速块（Pfitzinger MP Blocks）","categories":"Race-Simulation, Pace-Blocks, Tempo","zone_range":"Z4-Z5","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "15min 轻松慢跑 + 动态拉伸 + 4 × 60m 加速","10min 慢跑冷身"),

    # ═══ P8: 半马专项配速跑 A 级 (4条) ═══
    make_entry("action_lib_hm_specific_pace_v1", REF_D, REG_D,
        "name：10 × 1km HMP 巡航恢复间歇（Daniels M-HM v1）\ncategories：HM-Specific , Marathon-Pace , Cruise-Recovery\n"
        "content：10 × 1km @ 100% HMP（Z4-Z5）/ 1km @ 85% HMP 巡航恢复，交替。总计 10km 比赛配速 + 10km 巡航恢复 = 20km 总。不中断，巡航恢复段保持可控而非慢走。\n"
        "zone_range：Z4-Z5\n"
        "objective：高密度比赛配速代谢效率。Daniels M 配速框架在半马中的应用——通过巡航恢复段维持总体心输出量（不降到恢复区间），同时让比赛配速段的总暴露时长达到 10km。\n"
        "warmup_suggestion：20min 轻松跑 + 动态拉伸 + 4 × 80m 加速\n"
        "cooldown_suggestion：10-15min 慢跑冷身 + 补水\n"
        "alternative_workout：若每组巡航恢复段掉出 85% HMP 下限，减为 8 组",
        A, ["半马专项配速","HM Pace","Z4-Z5","Daniels M","巡航恢复","代谢效率"],
        {"workout_name":"10 × 1km HMP 巡航恢复间歇（Daniels M-HM v1）","categories":"HM-Specific, Marathon-Pace, Cruise-Recovery","zone_range":"Z4-Z5","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "20min 轻松跑 + 动态拉伸 + 4 × 80m 加速","10-15min 慢跑冷身 + 补水"),

    make_entry("action_lib_hm_specific_pace_v2", REF_D, REG_D,
        "name：7 × 2km HMP 巡航恢复间歇（Daniels M-HM v2）\ncategories：HM-Specific , Marathon-Pace , Longer-Reps\n"
        "content：7 × 2km @ 100% HMP（Z4-Z5）/ 1km @ 85% HMP 巡航恢复，交替。每段配速更长（2km），对配速纪律要求更高。总计 14km 比赛配速 + 7km 巡航 = 21km 总。\n"
        "zone_range：Z4-Z5\n"
        "objective：长段落比赛配速巡航能力——2km 段更接近比赛实际距离感知。每段的最后 500m 需要维持配速纪律不降速，训练比赛后程抗疲劳能力。\n"
        "warmup_suggestion：20min 轻松跑 + 动态拉伸 + 4 × 80m 加速\n"
        "cooldown_suggestion：10-15min 慢跑冷身 + 补水\n"
        "alternative_workout：如果 2km 段无法全程维持，减为 5 组 2km 或改用 v1（1km 段）",
        A, ["半马专项配速","HM Pace","Z4-Z5","Daniels M","长段落巡航","抗疲劳"],
        {"workout_name":"7 × 2km HMP 巡航恢复间歇（Daniels M-HM v2）","categories":"HM-Specific, Marathon-Pace, Longer-Reps","zone_range":"Z4-Z5","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "20min 轻松跑 + 动态拉伸 + 4 × 80m 加速","10-15min 慢跑冷身 + 补水"),

    make_entry("action_lib_hm_specific_pace_v3", REF_P, REG_P,
        "name：3km + 2km + 1km 半马比赛配速递减组合（Pfitzinger HM Pyramid）\ncategories：HM-Specific , Marathon-Pace , Descending-Pyramid\n"
        "content：3km @ 100% HMP→1km @ 85% HMP 巡航恢复→2km @ 100% HMP→1km @ 85% HMP 巡航恢复→1km @ 100% HMP。总比赛配速段 6km，心理负荷递减（3→2→1），最后一段只需 1km。\n"
        "zone_range：Z4-Z5\n"
        "objective：递减金字塔配速训练——心理负荷随配速段递减但代谢需求不降。最后 1km 段是纯粹的质量检查：在已疲劳的状态下，能不能把比赛配速再跑 1km？\n"
        "warmup_suggestion：15-20min 轻松跑 + 动态拉伸 + 3 × 80m 加速\n"
        "cooldown_suggestion：10min 慢跑冷身 + 补水\n"
        "alternative_workout：如果 3km 首段过高，可变成 2+2+1+1 km 的替代金字塔",
        A, ["半马专项配速","HM Pace","Z4-Z5","Pfitzinger","递减金字塔","配速纪律"],
        {"workout_name":"3km + 2km + 1km 半马比赛配速递减组合（Pfitzinger HM Pyramid）","categories":"HM-Specific, Marathon-Pace, Descending-Pyramid","zone_range":"Z4-Z5","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "15-20min 轻松跑 + 动态拉伸 + 3 × 80m 加速","10min 慢跑冷身 + 补水"),

    make_entry("action_lib_hm_specific_pace_v4", REF_D, REG_D,
        "name：8km 连续比赛配速跑（Daniels M-HM Continuous）\ncategories：HM-Specific , Marathon-Pace , Continuous-MP\n"
        "content：16km 总：8km 轻松跑 Z2-Z3→8km @ 100% HMP（Z4-Z5）连续配速段。不设巡航恢复，纯粹的 8km 比赛配速耐力测试。\n"
        "zone_range：Z2-Z5\n"
        "objective：半马比赛配速连续巡航能力——不做间歇+恢复组合，而是测试能不能在 8km 配速跑中维持稳定的节奏和心率。比赛日 2-3 周前执行以确认比赛配速目标。\n"
        "warmup_suggestion：8km 轻松跑 Z2-Z3 即为热身\n"
        "cooldown_suggestion：10min 慢跑冷身 + 补水 + 拉伸\n"
        "alternative_workout：如果连续 8km @ HMP 无法完成，改为 5km @ HMP 连续",
        A, ["半马专项配速","HM Pace","Z2-Z5","Daniels M","连续配速","比赛确认"],
        {"workout_name":"8km 连续比赛配速跑（Daniels M-HM Continuous）","categories":"HM-Specific, Marathon-Pace, Continuous-MP","zone_range":"Z2-Z5","has_content":True,"has_objective":True,"has_warmup":True,"has_cooldown":True},
        "8km 轻松跑 Z2-Z3 即为热身","10min 慢跑冷身 + 补水 + 拉伸"),
]

new_entries = [e for e in NEW if e['chunk_id'] not in existing_ids]
skipped = len(NEW) - len(new_entries)
if skipped:
    print(f'Skipped {skipped} duplicates')

all_lines = [json.dumps(e, ensure_ascii=False) for e in existing] + [json.dumps(e, ensure_ascii=False) for e in new_entries]
with open(jsonl_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(all_lines) + '\n')

print(f'Total: {len(all_lines)} ({len(existing)} existing + {len(new_entries)} new)')
counts = {'A': 0, 'B': 0, 'C': 0}
for line in all_lines:
    obj = json.loads(line)
    sa = obj.get('source_authority', '')
    counts[sa] = counts.get(sa, 0) + 1
print(f'A={counts["A"]}, B={counts["B"]}, C={counts["C"]}')
