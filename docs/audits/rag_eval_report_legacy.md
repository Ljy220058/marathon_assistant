# RAG 评估实验报告

## 1. 核心指标汇总

| 指标类型 | 指标名称 | 分值 |
| :--- | :--- | :--- |
| 传统检索 | 精确块命中 Recall@5 | 0.3000 |
| 传统检索 | 精确块命中 MRR@5 | 0.1000 |
| 传统检索 | 精确块命中 MAP@5 | 0.1000 |
| 传统检索 | 同页命中 Recall@5 | 0.6000 |
| 传统检索 | 同页命中 MRR@5 | 0.3250 |
| 传统检索 | 同页命中 MAP@5 | 0.3250 |
| 传统检索 | 同文档命中 Recall@5 | 0.9000 |
| 传统检索 | 同文档命中 MRR@5 | 0.7250 |
| 传统检索 | 同文档命中 MAP@5 | 0.7250 |
| Ragas | context_precision | 0.1700 |
| Ragas | faithfulness | 0.7500 |
| Ragas | answer_relevancy | 0.4635 |
| Ragas | context_recall | 0.4000 |

传统检索指标口径说明：`精确块命中` 要求命中同一 `chunk_id`；`同页命中` 允许命中同一文档同一页的相邻块；`同文档命中` 只要求命中同一 `source_file`。

## 2. 详细数据样本 (Top 3)

### 样本 1
**问题**: 训练组的1-RM腿推力从干预前到干预后增加了多少？

**检索上下文 (片段 1)**: ombined training
HIIT group unilateral knee extension strength was 57.9 (47.6–68.1) and 61.5 (45.7–77.2) kg pre- and post-intervention,
respectively.
Combined training group unilateral knee extension ...

**系统回答**: 根据提供的信息，结合训练组（Combined training group）的数据，在进行干预前后，1-RM腿推力分别增加了约3.5 kg·FFM⁻¹。具体数值为：1-RM腿推力在干预前为50.7 (41.1–60.3) kg，干预后为65.4 (54.8–75.9) kg。

**标准答案**: 训练组的1-RM腿推力从干预前到干预后大约增加了3.5 kg·FFM−1。

---
### 样本 2
**问题**: 为什么需要记录日志？

**检索上下文 (片段 1)**: Three Times Weekly
Flexibility and Strength
Easy calisthenics, Yoga,
light-to-moderate
resistance training
Recreational Exercise
Racket games,
basketball, hiking
Information on the use of the daily lo...

**系统回答**: 记录日志有几个重要的原因：

1. **提高对身体、情感和思想的敏感性**：通过记录锻炼后的感受，你可以更好地了解自己的身体状况，从而调整训练计划。

2. **识别特定模式和问题**：记录可以帮助你发现某些运动习惯或饮食选择是否影响了你的表现或者健康。例如，如果你经常感到疲劳，日志可以帮助你找出可能的原因，并且可以与教练或其他专业人士讨论这些情况。

3. **分享信息以寻求帮助**：你可以把记录的信息与他人分享，以便他们能提供帮助和建议来解决发现的问题。

4. **评估训练计划的有效性并进行调整**：通过回顾整个赛季的日志记录，你和你的教练可以获得宝贵的反馈，从而在赛季中乃至赛季之间对训练计划进行改进，以提高运动员的潜力实现机会。

**标准答案**: 记录日志可以帮助你更加关注锻炼后身体、感受和想法的变化，并识别出某些锻炼模式和问题。

---
### 样本 3
**问题**: 什么是periodization methodology？

**检索上下文 (片段 1)**: VOLUME 8 | ISSUE 2 | 2013 | 350
Applied periodization: a methodological
approach
FERNANDO NACLERIO1 , JEREMY MOODY2, MARK CHAPMAN3
1Principal Lecturer in Strength and Conditioning and Sports Nutrition...

**系统回答**: Periodization methodology是一种训练计划的方法，它通过在不同阶段调整训练的各个方面（如体积、强度和重复范围等）来优化运动员的表现。这种策略可以分为不同的模式，比如传统的周期化和波动性周期化。

根据背景信息中的描述，periodization可以通过更频繁地改变训练量、强度以及重复范围等方式来进行安排。这需要在每个训练过程中（从单次锻炼到日训练、微观周期、中观周期、宏观周期，再到全年乃至多年度的计划）适当地调整所有训练变量，并且这种变化应该是有序和考虑周全的，而不是随机或过度进行的。

波动性周期化是其中一种形式，它强调更频繁地调整训练量、强度及重复范围。参考文献中提到的相关研究对理解这一概念提供了更多细节，但简而言之，这种方法通过在不同阶段内持续变化不同的训练变量来帮助运动员达到最佳表现状态。

**标准答案**: periodization methodology是指为了从一般训练过渡到更具体的体育训练、消散疲劳并降低受伤风险而设计的训练方法论，包括适当的程序来设计会合、微观周期和中观周期。

---
