# RAG 评估实验报告

## 1. 核心指标汇总

| 指标类型 | 指标名称 | 分值 |
| :--- | :--- | :--- |
| 传统检索 | Recall@5 | 0.0000 |
| 传统检索 | MRR@5 | 0.0000 |
| 传统检索 | MAP@5 | 0.0000 |
| Ragas | reference | 2006.0000 |
| Ragas | context_precision | 0.0200 |
| Ragas | faithfulness | 0.7000 |
| Ragas | answer_relevancy | 0.4323 |
| Ragas | context_recall | 0.0000 |

## 2. 详细数据样本 (Top 3)

### 样本 1
**问题**: 训练组的1-RM腿推力从干预前到干预后增加了多少？

**检索上下文 (片段 1)**: ning programme that will assist the
athlete to achieve his or her training objectives. The training programme will provide
the format that will guide the athlete through the proper sequence of develop...

**系统回答**: 根据提供的信息，没有提到关于1-RM腿推力的具体数据或变化情况。提供的训练计划主要涉及有氧运动、核心稳定性练习和柔韧性训练等方面的内容，并未包含有关1-RM腿推力测试的信息。因此无法回答训练组的1-RM腿推力从干预前到干预后增加了多少这个问题。如果您有关于训练计划中某个特定指标的数据，请提供详细信息，以便我能更准确地帮助您。

**标准答案**: 训练组的1-RM腿推力从干预前到干预后大约增加了3.5 kg·FFM−1。

---
### 样本 2
**问题**: 为什么需要记录日志？

**检索上下文 (片段 1)**: ing Economy, ② Maximal Oxygen Uptake, ③ Blood Lactate...

**系统回答**: 记录训练日志有助于保持训练的诚实性和一致性。通过记录每天的训练情况，跑步者可以更好地了解自己的进步，并且能够追踪和分析哪些训练方法对自己最有效。此外，记录饮食日记或食物日志还可以帮助跑步者注意到不同食物如何影响他们的表现、能量水平以及其他身体感受，从而优化他们的饮食习惯以支持更好的运动表现。正如背景信息中提到的一段话所强调的：“Like all runners, success of completion is based not on talent but on consistency of daily training. Magic only happens when you put in the training, so record your training; it keeps you honest.”（就像所有跑步者一样，完成成功的秘诀不是天分而是日常训练的一贯性。只有投入训练，奇迹才会发生，所以记录你的训练；它会保持你对训练的诚实态度。）

**标准答案**: 记录日志可以帮助你更加关注锻炼后身体、感受和想法的变化，并识别出某些锻炼模式和问题。

---
### 样本 3
**问题**: 什么是periodization methodology？

**检索上下文 (片段 1)**: VOLUME 8 | ISSUE 2 | 2013 | 350
Applied periodization: a methodological
approach
FERNANDO NACLERIO1 , JEREMY MOODY2, MARK CHAPMAN3
1Principal Lecturer in Strength and Conditioning and Sports Nutrition...

**系统回答**: Periodization methodology是一种训练计划的方法，它涉及对训练变量（如体积、强度和重复范围等）进行有组织的调整。这种方法旨在通过定期变化训练内容来优化运动员的表现或体能水平。背景信息中提到的一种特定形式是“波浪式周期化”（Undulating Periodization），这种周期化方法更频繁地改变这些训练参数。

根据文档中的描述，适当的训练变量操作应该在所有训练过程中考虑，包括单次练习、每天、微观周期、中观周期和宏观周期、年度甚至是跨年度的训练计划。这表明，在制定训练计划时应始终考虑到各个训练变量之间的相互关联及其顺序安排，并非简单地随机变化。

简而言之，periodization methodology是一种系统性地调整和管理训练负荷的方法，以促进运动员表现提升或体能发展。

**标准答案**: periodization methodology是指为了从一般训练过渡到更具体的体育训练、消散疲劳并降低受伤风险而设计的训练方法论，包括适当的程序来设计会合、微观周期和中观周期。

---
