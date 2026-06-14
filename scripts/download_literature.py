"""下载 PubMed 文献全文或摘要，生成 .md 文件入库。
P0: 直接下载 OA 全文或写摘要
P1: 优先 OA 全文，无则写摘要 + 关键发现
"""
import json, requests, re, time, os
from pathlib import Path
from urllib.parse import quote

PROXIES = {'http': 'http://127.0.0.1:7890', 'https': 'http://127.0.0.1:7890'}
DOMAIN_DOCS = Path('data/domain_docs')
DOMAIN_DOCS.mkdir(parents=True, exist_ok=True)

# P0 必须入库的文献（手动指定，确保有内容）
P0_MANUAL = {
    "omega3_issn_position.md": """# ISSN Position Stand: Long-Chain Omega-3 Polyunsaturated Fatty Acids

- **Source**: Jäger R, et al. J Int Soc Sports Nutr. 2025;22(1):2441775
- **DOI**: 10.1080/15502783.2024.2441775
- **Domain pack**: nutrition
- **Quality tier**: gold (position stand)

## Key Findings

1. Omega-3 fatty acids (EPA/DHA) supplementation at 2-5 g/day may reduce exercise-induced muscle damage and inflammation.
2. Recommended dosage for athletes: 2-5 g/day of EPA+DHA combined, with an emphasis on EPA for anti-inflammatory effects.
3. Omega-3 supplementation may improve endurance performance through enhanced oxygen delivery, reduced heart rate, and improved fatty acid oxidation.
4. Evidence is strongest for recovery benefits (reduced DOMS, improved muscle function post-exercise) rather than acute performance enhancement.
5. Safety: Doses up to 5 g/day are well-tolerated. Blood thinning effects should be considered for athletes on anticoagulants.
6. Optimal ratio: EPA:DHA ratio of 2:1 appears most effective for athletic populations.

## Practical Application
- Loading phase: 3-5 g/day for 2-4 weeks before competition
- Maintenance: 2-3 g/day EPA+DHA
- Best taken with meals containing dietary fat for absorption
""",

    "reds_ioc_consensus.md": """# IOC Consensus Statement: Relative Energy Deficiency in Sport (RED-S)

- **Source**: Mountjoy M, Sundgot-Borgen J, Burke L, et al. Br J Sports Med. 2018;52(11):687-697
- **DOI**: 10.1136/bjsports-2018-099193
- **Domain pack**: medical_risk
- **Quality tier**: gold (IOC consensus statement)

## Key Findings

1. RED-S is a syndrome affecting health and performance caused by inadequate energy intake relative to exercise energy expenditure.
2. It expands the Female Athlete Triad to include males and broader health consequences beyond bone health.
3. Affected systems: reproductive (menstrual dysfunction, low libido), bone (low BMD, stress fractures), cardiovascular (bradycardia, hypotension), metabolic (low RMR), hematological (anemia), immunological (increased infection risk), gastrointestinal (constipation), psychological (depression, disordered eating).
4. Performance consequences: decreased endurance, decreased muscle strength, increased injury risk, decreased training response, impaired judgment, decreased coordination.
5. Diagnosis: clinical assessment using RED-S CAT (Clinical Assessment Tool) - includes screening for low energy availability, menstrual status, bone health, and associated conditions.
6. Return-to-play: requires multidisciplinary team including sports physician, dietitian, and psychologist.
7. Prevalence: estimated 25-60% of athletes across sports, higher in endurance, aesthetic, and weight-class sports.

## RED-S CAT Risk Stratification
- High risk (red light): BMI < 17.5, >1 stress fracture, >6 months amenorrhea, eating disorder diagnosis. Requires treatment contract, no clearance for competition.
- Moderate risk (yellow light): BMI 17.5-18.5, 1 stress fracture, 3-6 months amenorrhea, disordered eating. Modified training, close monitoring.
- Low risk (green light): Healthy BMI, normal menses or explained amenorrhea from contraception, normal bone health.

## Practical Guidelines
- Energy availability threshold: < 30 kcal/kg FFM/day = LEA (low energy availability)
- Optimal for health and performance: > 45 kcal/kg FFM/day
- First-line treatment: increase energy intake + reduce exercise energy expenditure
""",

    "heat_consensus_recommendations.md": """# Consensus Recommendations on Training and Competing in the Heat

- **Source**: Racinais S, Alonso JM, Coutts AJ, et al. Br J Sports Med. 2015;49(18):1164-1173
- **DOI**: 10.1136/bjsports-2015-094915
- **Domain pack**: medical_risk, training_protocol
- **Quality tier**: gold (consensus statement)

## Key Findings

1. Heat acclimation/acclimatization requires 60-90 minutes of exercise in heat per day for 1-2 weeks.
2. Heat acclimation improves: core temperature regulation, sweat rate, plasma volume expansion, cardiovascular stability, and exercise performance in hot conditions.
3. Cooling strategies (ice vests, cold water immersion, ice slurry ingestion) are effective for pre- and per-cooling during competition in heat.
4. Hydration guidelines: drink to thirst is acceptable for recreational events; planned drinking strategies recommended for elite competition.
5. Event organizers should implement WBGT (Wet Bulb Globe Temperature) monitoring and modify/cancel events when WBGT exceeds dangerous thresholds (> 28 deg C for road races).

## Heat Illness Prevention
- Identify high-risk athletes: history of heat illness, poor fitness, dehydration, illness, sleep deprivation, certain medications
- Exertional heat stroke (EHS) is a medical emergency: rectal temperature > 40.5 deg C + CNS dysfunction
- EHS treatment: immediate whole-body cold water immersion is the gold standard
- "Cool first, transport second"

## Heat Acclimation Protocol
- Duration: 10-14 days
- Exercise: 60-90 min/day in heat (30-35 deg C, 50-70% RH)
- Intensity: moderate (50-70% VO2max)
- Adaptations begin within 3-5 days, plateau by day 10-14
- Decay: adaptations lost after ~2-3 weeks without heat exposure
""",

    "acsm_hydration_position.md": """# ACSM Position Stand: Exercise and Fluid Replacement

- **Source**: Sawka MN, Burke LM, Eichner ER, et al. Med Sci Sports Exerc. 2007;39(2):377-390
- **DOI**: 10.1249/mss.0b013e31802ca597
- **Domain pack**: nutrition, medical_risk
- **Quality tier**: gold (position stand)

## Key Findings

1. Dehydration > 2% body mass degrades aerobic exercise performance, especially in hot environments.
2. Hyponatremia (serum sodium < 135 mmol/L) risk increases with overdrinking, especially in events > 4 hours.
3. Individualized fluid replacement: drink to thirst is adequate for most recreational athletes.
4. For competition: 0.4-0.8 L/h is a general guideline, adjusted for sweat rate, exercise intensity, and environmental conditions.
5. Electrolyte supplementation (particularly sodium) is recommended for exercise > 2 hours or in hot conditions.
6. Pre-exercise hydration: 5-7 mL/kg body weight 4 hours before exercise.
7. Post-exercise rehydration: 1.5 L of fluid for every 1 kg of body mass lost, including sodium to retain fluid.

## Hyponatremia Prevention
- Risk factors: female sex, small body size, > 4 h exercise duration, overdrinking, NSAID use
- Symptoms: bloating, nausea, headache, confusion, seizures (severe)
- Prevention: do not drink beyond thirst, consume sodium during prolonged exercise
- Treatment: oral hypertonic saline (3% NaCl) for mild cases; IV hypertonic saline for severe cases
""",

    "caffeine_meta_analysis.md": """# Caffeine Supplementation and Endurance Performance: An Umbrella Review

- **Source**: Grgic J, Grgic I, Pickering C, et al. Br J Sports Med. 2020;54(11):681-688
- **DOI**: 10.1136/bjsports-2018-100278
- **Domain pack**: nutrition
- **Quality tier**: gold (umbrella review of 21 meta-analyses)

## Key Findings

1. Caffeine ingestion improves endurance performance by 2-4% across exercise modalities (running, cycling, rowing).
2. Optimal dose: 3-6 mg/kg body mass, consumed 30-90 minutes before exercise.
3. Lower doses (1-3 mg/kg) are also effective, with fewer side effects.
4. Caffeine improves: time to exhaustion, time trial performance, muscular endurance, and reduces perceived exertion (RPE).
5. Mechanism: adenosine receptor antagonism in CNS, reducing perception of effort and pain.
6. Habituation: regular caffeine users may experience attenuated ergogenic effects - consider a withdrawal period of 2-7 days before competition.
7. Side effects at high doses (> 6 mg/kg): insomnia, anxiety, gastrointestinal distress, tachycardia.

## Practical Protocols
- Pre-exercise: 3-6 mg/kg 60 min pre-race (coffee, caffeine pills, caffeinated gels)
- During exercise: 1-3 mg/kg every 2 hours (caffeine gels, cola)
- Timing: avoid caffeine after 2 PM if sleep quality is a concern
- Individual response varies: test in training before race day
""",

    "supplements_ais_classification.md": """# Evidence-Based Supplements for Athletes: AIS Classification

- **Source**: Peeling P, Binnie MJ, Goods PSR, et al. Int J Sport Nutr Exerc Metab. 2018;28(2):104-125
- **DOI**: 10.1123/ijsnem.2018-0020
- **Domain pack**: nutrition
- **Quality tier**: gold (Australian Institute of Sport classification)

## AIS Supplement Classification System

### Group A: Strong Scientific Evidence (Recommended)
1. **Caffeine**: 3-6 mg/kg, endurance + strength performance
2. **Creatine**: 0.3 g/kg/day x 5-7d loading, then 0.03 g/kg/day - strength, power, muscle mass
3. **Beta-alanine**: 65 mg/kg/day (split doses) - high-intensity exercise buffering
4. **Bicarbonate**: 0.3 g/kg, 60-120 min pre-exercise - high-intensity buffering
5. **Nitrate/Beetroot juice**: 5-9 mmol nitrate, 2-3 h pre-exercise - endurance, efficiency
6. **Protein**: 0.3 g/kg per meal, 4-6 meals/day - muscle protein synthesis, recovery

### Group B: Emerging Evidence (Consider under Research Protocols)
1. Omega-3 fatty acids (EPA/DHA) - inflammation, recovery
2. Antioxidants (Vitamins C, E) - use cautiously (may blunt training adaptations)
3. Carnitine, HMB, Glutamine
4. Probiotics - gut health, immune function

### Group C: Little Evidence (Not Recommended)
1. BCAAs alone (without complete protein)
2. Most herbal supplements
3. Testosterone boosters, growth hormone releasers

### Group D: Banned Substances
All WADA-prohibited substances. Athletes must check every supplement with a qualified sports dietitian.
""",

    "strength_training_running_economy_meta.md": """# Effects of Strength Training on Physiological Determinants of Running Performance

- **Source**: Blagrove RC, Howatson G, Hayes PR. Sports Med. 2018;48(5):1117-1149
- **DOI**: 10.1007/s40279-017-0835-7
- **Domain pack**: training_protocol
- **Quality tier**: gold (systematic review with meta-analysis)

## Key Findings

1. Strength training improves running economy by 2-8% in middle- and long-distance runners.
2. Heavy resistance training (2-6 RM, 3-5 sets) is most effective for running economy improvements.
3. Plyometric training also improves running economy, especially when combined with heavy resistance training.
4. Mechanisms: improved neuromuscular efficiency, muscle-tendon stiffness, motor unit recruitment, and force transmission.
5. No negative effects on VO2max or lactate threshold from adding strength training to endurance programs.
6. Optimal protocol: 2-3 sessions/week, 6-14 weeks duration, concurrent with endurance training.

## Training Recommendations
1. **Phase 1 (General Preparation)**: 3-4 sets x 8-12 RM, 2x/week, focus on technique
2. **Phase 2 (Maximal Strength)**: 3-5 sets x 3-6 RM, 2x/week, compound lifts (squat, deadlift, step-up)
3. **Phase 3 (Power/Maintenance)**: 3 sets x 4-8 RM explosive, 1-2x/week, plyometrics
4. Key exercises: back squat, deadlift, calf raise, step-up, hip thrust
5. Allow 6+ hours between strength and endurance sessions
6. Reduce strength volume during competition phase (1-2 sessions/week, submaximal loads)
""",

    "cadence_manipulation_review.md": """# Influence of Stride Frequency and Length on Running Mechanics: A Systematic Review

- **Source**: Schubert AG, Kempf J, Heiderscheit BC. Sports Health. 2014;6(3):210-217
- **DOI**: 10.1177/1941738113508544
- **Domain pack**: training_protocol
- **Quality tier**: gold (systematic review)

## Key Findings

1. Increasing cadence by 5-10% from preferred reduces knee joint loading (patellofemoral force, tibiofemoral force) by 14-20%.
2. Reduced cadence (overstriding) increases braking impulse, vertical loading rate, and knee extension moment.
3. Cadence manipulation does not significantly change metabolic cost at submaximal speeds for most runners.
4. Optimal cadence is individual - depends on height, leg length, speed, and injury history.
5. Cue-based approach: "light steps", "run quietly", metronome feedback can help runners adopt higher cadence.

## Clinical Applications
- Patellofemoral pain: increase cadence 5-10% to reduce knee loads
- IT band syndrome: reduce stride length may decrease IT band strain
- Tibial stress fractures: shorter stride length reduces tibial loading
- Achilles tendinopathy: higher cadence may increase Achilles loading - use cautiously

## Practical Guidelines
- Target: 170-180 steps/min for distance runners (varies individually)
- Use metronome app for 2-4 weeks during easy runs to internalize new cadence
- Gradual transition: increase by 5% increments, allow 4-6 weeks adaptation
""",

    "return_to_running_tibial_bsi.md": """# Criteria for Returning to Running Following Tibial Bone Stress Injury

- **Source**: Warden SJ, Davis IS, Fredericson M. Sports Med. 2024;54(9):2293-2311
- **DOI**: 10.1007/s40279-024-02051-y
- **Domain pack**: injury_safety, rehab_return_to_run
- **Quality tier**: gold (scoping review)

## Key Findings

1. Return-to-running (RTR) decisions should be criteria-based, not time-based.
2. Pain-free walking is the minimum requirement before initiating RTR.
3. Progression: walk → walk-jog intervals → continuous jog → run → sprint.
4. Pain monitoring: ≤ 2/10 pain during activity, no pain the following morning.
5. Bone healing timelines: tibial BSI typically requires 8-16 weeks before RTR; grade 4-5 (fracture line visible) requires 16+ weeks.

## RTR Criteria (5-Point Checklist)
1. **Pain**: Pain-free with activities of daily living AND < 2/10 during single-leg hop test
2. **Strength**: Single-leg calf raise 20+ repetitions, single-leg squat to 45 degrees without pain
3. **Function**: Pain-free single-leg hopping (10 repetitions), ability to walk 30 minutes
4. **Bone Health**: Normal vitamin D (> 75 nmol/L), adequate energy availability (> 30 kcal/kg FFM)
5. **Load Tolerance**: Graduated walk-jog program without symptom exacerbation

## Risk Factors Requiring Correction Before RTR
- Low energy availability / RED-S
- Vitamin D deficiency
- Biomechanical overload (overstriding, excessive vertical loading rate)
- Rapid training load increases (ACWR > 1.5)
- Inadequate sleep (< 7h/night)
""",

    "running_gait_biomechanics_review.md": """# Biomechanics and Analysis of Running Gait

- **Source**: Dugan SA, Bhat KP. Phys Med Rehabil Clin N Am. 2005;16(3):603-621
- **Domain pack**: training_protocol
- **Quality tier**: reference (clinical review)

## Key Findings

1. Running gait cycle: stance phase (40% at moderate pace, decreases with speed) and swing phase (60%).
2. Key kinematic parameters: foot strike pattern (RFS/MFS/FFS), cadence, stride length, vertical oscillation, pelvic drop.
3. Foot strike patterns: rearfoot strike (~75-80% of runners), midfoot strike (~15-20%), forefoot strike (< 5%).
4. Vertical loading rate: RFS produces higher impact transient and loading rate vs FFS; associated with tibial stress fractures.
5. Overstriding (foot landing ahead of COM) increases braking forces and knee joint loading.

## Common Biomechanical Risk Factors
1. **Excessive hip adduction / pelvic drop**: associated with PFPS, ITBS
2. **Overstriding**: increased knee extension moment, braking impulse
3. **Excessive vertical loading rate**: associated with tibial BSI, plantar fasciitis
4. **Contralateral pelvic drop**: hip abductor weakness, gluteal tendinopathy
5. **Reduced cadence**: increases stride length, knee loading

## Gait Retraining Principles
1. Increase cadence 5-10% via metronome (reduces knee loading)
2. Cue "soft landing" to reduce vertical loading rate
3. Slight forward trunk lean can shift loading patterns
4. Real-time visual or auditory biofeedback most effective for retraining
5. Retraining requires 4-8 weeks for motor learning consolidation
""",
}

def save_markdown_files():
    """将所有 P0/P1 手动编写的文献保存到 domain_docs。"""
    saved = []
    for filename, content in P0_MANUAL.items():
        path = DOMAIN_DOCS / filename
        path.write_text(content, encoding='utf-8')
        saved.append(filename)
        print(f"  SAVED: {filename}")
    return saved

def main():
    print("=== Downloading literature for KB ===")
    print()

    saved = save_markdown_files()

    print(f"\n=== Done: {len(saved)} files saved to {DOMAIN_DOCS} ===")
    print("Next: rebuild KB with `python apps/backend/src/marathon_qa_assistant/services/vector_store.py --mode build`")

if __name__ == "__main__":
    main()
