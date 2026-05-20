# NPJ Exercise Medicine 投稿导向 Workflow 方案 v0.1

生成日期：2026-05-14

## 1. 当前判断

最初的 STAI/RAG 安全 workflow 不适合直接投 `npj Exercise Medicine and Health`。三轮模拟审稿后的共同意见是：如果把论文写成“更安全的 RAG/LLM 运动建议系统”，很容易被认为偏 AI 工程、RAG guardrail 或 npj Digital Medicine，而不是 exercise medicine Article。

更可行的方向是：

**Expert-validated safety boundaries for digital exercise prescription advice**

核心不是证明“我们做了一个安全 AI 系统”，而是建立并验证一套数字运动处方安全边界体系，再用 AI 生成建议作为压力测试，识别数字运动建议中最容易失守的运动处方风险。

## 2. 研究对象重构

- 主对象：数字健康环境中的运动处方安全边界。
- AI/LLM/RAG：仅作为 stress-test 工具，不作为论文主贡献。
- 目标期刊叙事：exercise prescription safety science，而不是 AI benchmark。
- 推荐题目：
  - `Expert-validated safety boundaries for digital exercise prescription advice`
  - `Exercise prescription safety boundaries in digital health advice`

## 3. 核心产物

论文需要把以下内容作为主要产物，而不是把模型性能表作为主结果：

- Exercise-prescription-specific safety boundary taxonomy。
- Annotation manual。
- FITT-VP acceptable range decision table。
- Red-flag disposition map。
- Condition-specific prescription boundary matrix。
- Evidence hierarchy rules。

## 4. Case Benchmark 设计

目标规模：`500` 个 case。

来源要求：

- 至少 `40%` 来自真实或外部半真实来源，例如匿名运动咨询、公开运动论坛/FAQ 改写、App/可穿戴用户问题模板、教练/学生常见咨询、训练日志异常情境。
- 其余来自 ACSM/WHO/运动处方指南、现有 90 篇运动健康交叉文献矩阵和运动处方安全场景派生。

每个 case 至少标注：

- case source level：真实匿名、公开真实改写、外部半真实、指南派生、文献派生。
- condition domain：心血管、代谢、肌骨、心理健康、热病/环境、睡眠/疲劳、初学者/低体能、疼痛/损伤等。
- risk category：红旗症状、禁忌/相对禁忌、FITT-VP 剂量边界、进阶负荷、过度个体化、证据冲突、转诊/拒答/补问边界等。
- expected disposition：具体处方、保守一般建议、补问风险信息、监测/停止规则、转诊/急诊、拒答。

数据划分：

- development set：用于 taxonomy、manual 和 prompt refinement。
- internal locked test：最终一次评估，不能调参污染。
- external validation set：最好来自独立机构、独立专家、不同平台或不同时间窗口。

## 5. 专家验证设计

目标专家数：`5-7` 名。

专家构成应尽量覆盖：

- 运动医学或康复医学医师。
- 临床运动生理或 ACSM-CEP/EP 背景专家。
- 物理治疗/康复专家。
- 心肺康复或慢病运动管理专家。
- 运动训练/运动科学专家。

关键设计：

- Taxonomy 开发组和 locked/external set 盲评组分离。
- 至少双标或多标，争议项通过预设仲裁流程处理。
- 报告 inter-rater agreement，例如 weighted kappa、Krippendorff alpha 或 Gwet AC1。
- 单独报告 severe unsafe advice、correct escalation/referral/refusal 等关键标签的一致性。
- 报告专家置信度、争议项比例、修订前后变化、外部盲评表现。

## 6. AI Stress-test 设计

AI 不是主角，只是诱发和暴露错误的压力测试工具。

可比较系统：

- 通用 LLM。
- Domain-prompt LLM。
- Vanilla RAG。
- RAG + safety prompt。
- Rule-based red-flag triage。
- Evidence-risk gated system。

标准化要求：

- 固定 prompt、模型版本、temperature、retrieval corpus、run count 和输出格式。
- 所有系统共享同一评估任务和同一专家金标准。
- 输出分析重点不是模型排名，而是哪些运动处方边界最容易被破坏。

## 7. 主要终点与统计

Primary endpoints：

- Severe unsafe advice rate。
- Correct escalation/referral/refusal rate。

Secondary endpoints：

- FITT-VP appropriateness。
- Unsupported evidence/citation。
- False refusal。
- Over-personalization。
- Answer utility under safe boundaries。
- Expert editing burden。

统计要求：

- 预注册主要终点和统计分析计划。
- 给出样本量或 precision rationale。
- 使用 95% CI、paired bootstrap 或 McNemar test。
- 做 severity-weighted analysis。
- 按 case source、condition domain、risk category 分层。
- 做 expert uncertainty sensitivity。

## 8. 专家工作流价值评估

为了避免论文被看成单纯 AI benchmark，需要加入专家工作流价值指标：

- Expert editing burden。
- Time-to-edit。
- Number/type of edits。
- Unsafe-to-safe conversion。
- 专家可用性评分。
- 处方完整性评分。
- 安全性评分。

这部分用于证明该安全边界体系可服务运动医学、康复、临床运动生理和数字健康团队的运动处方质量控制。

## 9. 报告与开放材料

报告框架：

- 对齐 TRIPOD-LLM、DECIDE-AI、CHART 中适用条目。
- 明确说明不适用 CONSORT-AI 或 SPIRIT-AI 的原因，除非后续真的做干预试验。

建议公开或受控访问：

- Development set。
- Case metadata。
- Annotation rubric。
- Annotation guide。
- Prompt templates。
- 知识库 citation snapshot。
- Model versions、run date、decoding parameters。
- Evaluation scripts。
- Failure cases。
- Locked/external set 的受控访问说明。

## 10. 写作原则

必须守住：

- 题目、摘要、图 1、结果首段都不能让 LLM/RAG 站 C 位。
- Results 的骨架应是 taxonomy 覆盖度和专家一致性、哪些 exercise prescription boundaries 最脆弱、哪些场景最容易产生 severe unsafe advice、专家审计如何降低高危错误和修改负担。
- AI stress-test 只能作为证据，不作为主角。
- 不能声称 clinical validation、deployment-ready、safe system、替代专业人员或改善健康结局。

推荐措辞：

- content-validated safety boundary framework。
- expert-adjudicated safety outcomes。
- benchmark-based stress-test。
- digital exercise prescription quality control。

避免措辞：

- clinically validated。
- deployment-ready。
- safe AI exercise prescription system。
- autonomous exercise prescription。
- improves health outcomes。

## 11. 三轮模拟审稿结果

第 1 轮：

- 原始 workflow 被认为太像 AI guardrail/RAG 工程。
- `npj Exercise Medicine and Health` desk reject 风险高。

第 2 轮：

- 改成专家标注 benchmark 后仍偏 AI evaluation。
- 审稿人要求真实 case、外部验证、5-7 名专家和 condition-specific prescription boundary matrix。

第 3 轮：

- v3 已进入目标期刊 scope。
- 编辑型审稿人判断为：`Send to review if executed`。
- 运动医学和方法学审稿人判断为：`Major revision before submission`。

## 12. 当前现实约束

目前尚未联系到专家。作为本科生，不建议直接以 npj Article 作为第一步执行目标。

建议阶段化：

1. 保留本方案作为高阶投稿路线。
2. 先把 STAI 升级到更现实的数字健康、医学信息学、AI safety 或 workshop/会议论文路线。
3. 用现有 STAI 工作流、90 篇运动健康矩阵和小型 case set 做 pilot artifact。
4. 准备 1 页专家请教材料、20 个样例 case 和初版 taxonomy，用于寻找导师或专家 sanity check。
5. 若获得导师或专家支持，再逐步升级到 500-case、专家验证和 npj Exercise Medicine 路线。

## 13. 中科院一区判断备注

该方案如果完整执行，目标质量可以按中科院一区或 Nature Portfolio 级别方法学研究来设计；但“是否属于中科院一区文章”取决于最终投稿期刊的实际分区，而不是研究计划本身。

截至 2026-05-14，`npj Exercise Medicine and Health` 是 Nature Portfolio 的新刊，公开页面显示期刊已开放投稿，ISSN 为 `3059-331X`。新刊通常需要时间进入 Web of Science/JCR，并获得影响因子和中科院分区。因此当前不能严谨地说它已经是中科院一区。

若转投 `npj Digital Medicine`，该刊已被 SCIE 收录，公开期刊页显示其定位为数字医学高质量研究期刊；第三方数据库普遍标注其为 JCR Q1/中科院一区候选或已列一区。但最终分区仍应以学校认可的最新版中科院期刊分区表和 JCR 为准。

结论：

- `npj Exercise Medicine and Health`：潜在 Nature Portfolio 高水平新刊，但目前不宜直接承诺“中科院一区”。
- `npj Digital Medicine`：更贴 STAI/AI workflow，一区可能性和现实认可度更明确，但竞争更强。
- 当前 STAI 升级路线：更现实的是先冲 digital health / medical informatics / AI safety 相关 Q1 或 workshop，再用专家资源升级 npj Exercise Medicine 方向。
