# M-EXRxBench Rule Challenge 论文逻辑审查与中文润色稿

审查对象：`submission_package/paper/main.tex` 与配套 `rule_examples.tex`、基准、规则规范、评测摘要、artifact checklist。

评审视角：RuleML+RR Rule Challenge 赛道资深程序委员。重点检查挑战定义、规则系统、基准构建、可审计性、可复现性和安全边界是否构成自洽论文叙事。

## 1. 整体评价

**整体逻辑评分：8/10。**

论文已经具备 RuleML+RR Rule Challenge 投稿的核心形态：问题定义明确，挑战对象不是“生成更好的跑步计划”，而是“在证据与规则边界内判定是否允许生成个体化运动处方”；基准、规则系统、评测脚本、可复现工件和安全声明也能互相支撑。稿件最强的部分是把 `answered / partial_answer / ask_clarification / refused` 设计成可评测的权限状态，并用 RiskGate、EvidenceGate、PrescriptionContract、Rule Auditor 和 bounded repair 形成可追踪的规则治理链条。

主要问题不在于材料缺失，而在于正文中的若干逻辑连接仍然偏压缩：标签生成与标注一致性说明不足，形式化规则表达仍接近“半形式化接口说明”，默认 500 例结果与 Hard-100 压力集结果之间的解释需要更清楚，基线系统的“deterministic generated ablation controls”容易被误读为真实外部 LLM/RAG 系统，trace completeness=1.000 也可能让评审误以为所有系统都有原生可审计推理轨迹。若补强这些点，论文会更接近一个成熟的 Rule Challenge artifact paper。

## 2. 逻辑问题清单与修改方向

### 2.1 整体结构逻辑

**问题 1：挑战定义与参考解法的双重身份已经成立，但论文早段没有足够早地解释“hybrid Challenge Proposal + Challenge Solution”的评价边界。**

修改方向：在引言贡献列表或 Challenge Definition 第一段中明确说明：M-EXRxBench 是 challenge proposal，rule-governed M-EXRx 是 reference solution；论文评价的核心是接口、基准、规则合规性和可复现 artifact，而不是声称系统已经具备真实临床安全性或训练效果。

**问题 2：章节递进基本清楚，但“Benchmark Construction”放在“Rule Reasoning Interface”之前，会让读者先看到标签分布，再看到状态空间和规则语义。**

修改方向：当前顺序可保留，但应在 Challenge Definition 中提前给出最小形式化状态空间，例如 `state = <profile, query, risk_signals, evidence_set, action_set, constraints>`，并说明后续基准只是这个状态空间的实例化。

**问题 3：默认 500 例高分与 Hard-100 失败之间的论文叙事需要更平衡。**

修改方向：摘要、结果和讨论中统一表述：默认 500 例是规则合规性与可复现性检查，Hard-100 是边界失败暴露工具。不要让 1.000 的默认分数成为核心可信度声明；应强调 stress set 揭示当前参考解法仍有 9% unsafe leakage。

### 2.2 摘要

**优点：** 已包含问题、方法、贡献和关键结果四个要素。

**问题 1：`1.000 rule-compliance scores` 表述过宽。**

修改方向：改为“在默认 500 例合成基准上，状态准确率、风险准确率、trace completeness 和 repair success 均为 1.000，unsafe/unsupported 为 0.000”。这样比“rule-compliance scores”更可核查。

**问题 2：Hard-100 的负面结果只在末尾一句出现，权重偏弱。**

修改方向：摘要中直接说明 Hard-100 的 status accuracy=0.670、unsafe advice rate=0.090，定位为边界分析，不要只说“remaining boundary failures”。

**问题 3：安全免责声明有，但还可以更靠前。**

修改方向：在结果句之后立即补一句“这些指标仅是 artifact-level deterministic checks”。当前句子已有此意，但建议把“not clinical safety”与“not real-world deployment evidence”并列。

### 2.3 引言

**问题 1：现有工作不足的逻辑链条还可以更明确。**

修改方向：按“RAG/agent 可生成合理文本，但不能决定处方权限；CDSS 有规则边界，但不直接覆盖生成式运动处方；因此需要可评测的 permission benchmark”展开。

**问题 2：贡献列表中“benchmark artifact”与“reference system and evaluator”较清楚，但创新性表述偏保守。**

修改方向：突出三点：以权限状态而非文本质量为主评测对象；把证据资格从 retrieval relevance 提升为 prescription authority；把 bounded repair 纳入可审计输出。

**问题 3：领域动机中“half-marathon training”的选择理由充分，但缺少对“为什么不是医疗处方”的边界声明。**

修改方向：在引言末尾或脚注中说明该任务是规则治理研究 artifact，不提供诊断、治疗、康复或急救建议。

### 2.4 挑战定义

**问题 1：输入输出规范已有，但状态空间定义仍分散。**

修改方向：增加一个简短公式或定义块：`x = (q, p, g, c, R_s, E, A)`，其中 `q` 为请求、`p` 为 profile、`g` 为目标、`c` 为约束、`R_s` 为风险信号、`E` 为证据集合、`A` 为动作库。输出 `y = (status, answer, trace)`。

**问题 2：评估协议的“系统可见 / 评估器专用”逻辑清楚，但应明确禁止 solver 读取 gold labels。**

修改方向：正文中加入“solver contract”：solver only reads `system_visible_cases.jsonl`; evaluator alone reads `gold_labels.jsonl`; any access to gold fields invalidates the run。

**问题 3：`partial_answer` 的权限边界定义偏窄。**

修改方向：表格中写成“limited to approved low-risk/recovery/educational content under the contract”，避免被误解为所有 partial answer 都只能是 recovery and low-intensity activities。

### 2.5 基准构建

**问题 1：案例设计原则已列出，但“标签生成方法”不足。**

修改方向：补充一段说明 gold labels 的生成流程：基于 category seed、risk rule、evidence/action availability、profile completeness、adversarial pressure 生成候选标签，再通过 schema validation 和 rule consistency audit 校验。若当前为单作者生成，应明确写为 single-author generated and self-audited synthetic labels。

**问题 2：标注一致性没有实证结果。**

修改方向：不要暗示已有多人标注一致性。可写“external annotation agreement is future work”，并把 R3/refused cases 的人工复核作为 camera-ready 或 artifact release 的计划。

**问题 3：synthetic benchmark 的外部有效性边界应更早出现。**

修改方向：在 Benchmark Construction 末尾加一句：该分布用于覆盖规则边界，不代表真实跑者风险分布或真实训练需求分布。

### 2.6 规则系统

**问题 1：规则形式化表达准确性基本可接受，但更像规则接口，不是完整 RuleML 序列化。**

修改方向：把“follows the shape of a RuleML implication”改为“uses a RuleML-style implication interface”，避免评审要求看到完整 RuleML XML/PSOA/RuleML syntax。

**问题 2：优先级机制有形式化关系，但 priority layer 与实现文件之间的映射不够明确。**

修改方向：增加一张小表或补充说明，将 `red_flags > injury/fatigue/environment > scope > evidence > protocol > capacity > progression > user_preference` 映射到具体 rule IDs 或 rule_spec 文件。

**问题 3：PrescriptionContract 定义完整，但缺少 contract construction 的时序图或伪代码。**

修改方向：在系统架构段加入 5 步流程：RiskGate classify -> EvidenceGate authorize -> contract assemble -> Coach draft -> Auditor/repair/finalize。

**问题 4：Rule Auditor 与 bounded repair 很强，但要明确 repair 的不可变约束。**

修改方向：把“repair must not introduce new evidence/actions or lower risk”放入正文主段，而不仅出现在补充材料。

### 2.7 实验评估

**问题 1：基线系统名容易被误读。**

修改方向：在表格标题和正文中反复说明：这些是 deterministic ablation controls，不是外部调用的真实 LLM/RAG 系统。`naked_llm` 只是模拟自由生成失败模式。

**问题 2：结果表没有列出 rule violation rate 和 repair success rate。**

修改方向：如果版面允许，增加两列；如果不允许，表下注明完整 metrics 包括这两个值，并指向 artifact summary。

**问题 3：Trace=1.000 对所有系统可能引起评审质疑。**

修改方向：把列名改成 `Schema Trace` 或 `Required-field Trace`，并在正文强调 baseline traces 是 evaluator-normalized schema outputs，不代表原生 reasoning trace。

**问题 4：Hard-100 中 unsafe_advice_rate=0.090 但 rule_violation_rate=0.000，需要解释。**

修改方向：说明 unsafe advice 与 forbidden-output/rule violation 的检测口径不同：unsafe leakage 可由状态/风险边界错误触发，而 rule violation rate 只统计 evaluator 中显式 forbidden-output/rule checks 命中。

### 2.8 相关工作

**问题 1：相关工作覆盖面较好，但创新点对比还可更锋利。**

修改方向：每个小节结尾加入一句“therefore gap”：RAG 解决 grounding，不解决 prescription permission；CDSS 解决规则边界，但不测试生成式代理的答复权限；agent/tool use 解决调用流程，不保证 fail-closed governance。

**问题 2：Rule Challenge 前作对比较密集，但缺少一两句总结差异维度。**

修改方向：用“evaluated object”概念区分：现有工作评估规则建模、合规、临床规则或法律推理；本文评估生成式运动处方 agent 的 permission trace。

### 2.9 结论

**问题：结论过短。**

修改方向：结论应至少重申三件事：M-EXRxBench 的 challenge status 设计、参考系统的规则治理链条、默认基准与 Hard-100 的不同意义。未来工作可点到专家标注、多域运动处方、真实用户前瞻验证和语义 trace audit。

### 2.10 规则论文特有规范

**规则形式化表达：** 半形式化表达清楚，但还不是严格 RuleML 编码。建议将“RuleML-style interface”与“full executable rule specification in artifact”分开表述。

**权限边界与安全机制：** 清楚。RiskGate、EvidenceGate、Contract、Auditor、Repair 的职责完整。建议把 fail-closed 逻辑放在正文更显眼位置。

**可审计追踪机制：** 字段完整，但 trace soundness 与 trace completeness 的差异需要反复强调。当前正文已经说明 completeness 不是语义保证，建议在结果表列名中体现。

**可复现性声明：** 基本符合 Rule Challenge artifact 要求。建议增加 release tag、commit hash、文件 hash 或一条 fresh-clone 命令输出摘要。

**安全免责声明：** 已充分。建议摘要、引言、Discussion 中使用同一套术语，统一写为“not clinical validation, not deployment safety evidence, not medical diagnosis/treatment/rehabilitation advice”。

### 2.11 内容质量规范

**术语一致性：** `reference solution` 与 `reference system` 混用，建议统一为 `reference system`，在首次出现处说明它是 reference solution artifact。

**潜在矛盾：** “does not call an external model during evaluation” 与“LLM may draft”并不矛盾，但容易误读。建议说明 reference runner uses deterministic components to instantiate the contract, while the challenge interface allows LLM-based solvers。

**引用准确性：** 引用整体相关。Rule Challenge 官方要求引用合理。建议减少“医疗有效性”暗示，保留为 vocabulary and governance motivation。

**未定义概念或缩写：** R0--R3、FITT-VP、Hard-100、M-EXRx 在首次出现时应确保定义完整。正文中 R0--R3 在系统段定义较晚，建议前移到 Challenge Definition。

## 3. 润色后的完整论文（中文学术润色稿）

> 说明：以下是面向中文审阅和逻辑回改的完整润色稿。正式提交 RuleML+RR 仍应使用英文 CEURART 稿件；建议将此稿作为逐段改写英文版的语义底稿。

# M-EXRxBench：面向证据边界内运动处方代理的可追踪规则挑战

## 摘要

大型语言模型能够生成流畅的耐力训练计划，但文本流畅性不能构成运动处方的安全边界。本文将“证据边界内的运动处方”定义为 RuleML+RR Rule Challenge 任务，并提出 M-EXRxBench：一个包含 500 个合成案例的规则合规性基准，用于评估代理系统在不同风险与证据条件下应当回答、降级回答、请求澄清还是拒绝生成处方。该基准覆盖半程马拉松训练计划、疲劳与过载、疼痛与损伤、医学红旗信号、环境风险、营养边界、可穿戴设备不确定性、证据缺口和提示注入等场景。

同时，本文发布一个规则治理的 M-EXRx 参考系统。系统将处方权限交由 RiskGate、EvidenceGate、PrescriptionContract、规则优先级、Rule Auditor 和 bounded repair 共同控制，而不是让语言模型自行决定是否有权给出处方。参考实现会输出可审计轨迹，包括 profile version、risk level、fired rules、evidence identifiers、action identifiers、audit result、repair log 和 final status。在当前参考运行中，规则治理系统在默认 500 例合成基准上取得 1.000 的状态准确率与风险准确率，并在确定性评估器下达到 0.000 unsafe advice rate 和 0.000 unsupported prescription rate；单独报告的 Hard-100 压力集则暴露了剩余边界失败。这些指标是 artifact 层面的确定性检查，不代表真实世界临床安全性、训练效果或部署安全性。

**关键词：** Rule Challenge；trace-governed systems；evidence-bounded reasoning；exercise prescription；safety rules；benchmark

## 1. 引言

大型语言模型、检索增强生成和工具调用代理已经能够生成看似合理的耐力训练建议。然而，对运动处方而言，“看似合理”并不等于“允许生成”。当用户报告胸痛、晕厥、疼痛加重、异常疲劳、关键资料缺失或证据不足时，系统需要执行可检查的工作流和安全边界，而不能仅依赖模型生成文本时的自我约束。

运动处方与一般训练科普之间的区别在于，处方式回答会改变用户的实际行动空间。一般回答可以解释节奏跑、减量周或碳水摄入原则；处方式回答则会告诉某个具体跑者跑多远、跑多快、何时恢复训练、是否可以带痛继续训练，或如何在疲劳状态下安排强度。此时，证据不足不是引用质量较弱的问题，而是系统应当降级、澄清或拒绝的理由。同样，红旗症状和损伤信号应当优先于成绩目标，即使用户明确要求更激进的计划。

本文将“证据边界内的运动处方”定义为一个 RuleML+RR Rule Challenge 任务。给定用户请求、训练画像、目标、约束、风险信号、证据集合和动作库，系统必须输出四种状态之一：`answered`、`partial_answer`、`ask_clarification` 或 `refused`。合法输出还必须包含可审计轨迹，记录画像版本、风险等级、触发规则、证据标识符、动作标识符、专家调用、审计结果、修复日志和最终状态。本文的目标不是构建一个更会说话的跑步教练，而是让个体化处方的权限判定能够被检查、复现和比较。

本文选择半程马拉松训练作为案例域。该领域足够复杂，涉及周期化、跑量、强度、恢复、补给、损伤信号、环境条件和可穿戴设备不确定性；同时又足够收敛，便于定义规则、动作库和可控基准案例。公共运动处方指南提供了频率、强度、时间、类型、总量和进阶等基本概念。本文遵循一个核心原则：语言模型可以起草候选回答，但规则层才是最终的权限判定者。

本文贡献如下。

1. **挑战定义。** 本文将证据边界内的运动处方形式化为 RuleML+RR 任务，把回答、降级、澄清、拒绝和轨迹字段作为可评测结果。
2. **基准 artifact。** 本文发布 M-EXRxBench：一个包含 500 个平衡合成案例的基准，采用系统可见输入与评估器专用标签分离的设计，并附带 100 个 Hard-100 压力测试案例。
3. **参考系统与评估器。** 本文提供规则治理的 M-EXRx 参考系统、确定性消融基线、数据 schema、轨迹、bounded repair 机制和可复现评估器。

## 2. 挑战定义

RuleML+RR Rule Challenge 允许提交挑战提案与挑战解法。本文将两者放在同一 artifact 中：M-EXRxBench 定义挑战，规则治理的 M-EXRx 系统作为参考解法。该任务并不是普通答案生成。求解器必须判断请求的运动处方是否被允许、是否信息不足、是否可以修复，或是否因安全边界而必须拒绝。

形式上，一个案例可表示为：

`x = <query, profile, goal, constraints, risk_signals, evidence_set, action_library>`。

求解器输出：

`y = <status, answer_text, trace>`。

其中 `status` 属于 `{answered, partial_answer, ask_clarification, refused}`，`trace` 必须记录 profile version、risk level、rules fired、evidence ids、action ids、expert calls、audit result、repair log 和 final status。求解器只能读取系统可见案例文件，不能访问 gold labels、期望行为、gold risk level、required rules、forbidden outputs 或 rationale。评估器是唯一读取 evaluator-only gold fields 的组件。

### 2.1 系统可见输入

每个案例包含自然语言请求、画像对象、可用证据标识符、可用动作标识符和约束条件。求解器可以在生成时检查这些字段，但不能查看预期行为、gold risk level、必触发规则、禁止输出或标签理由。这一分离使 M-EXRxBench 更接近规则合规性测试，而不是普通答案评分：成功不取决于文本是否流畅，而取决于系统是否遵守隐藏权限、风险优先级、证据资格、禁止动作和修复范围。

### 2.2 输出契约与状态空间

输出 schema 要求包含 case identifier、system name、status、answer text 和轨迹字段。状态不是格式选择，而是挑战的核心结果，决定系统是否允许给出处方、是否只能给出受限回答、是否必须先请求澄清，或是否必须拒绝。

| 状态 | 含义 | 处方权限 |
|---|---|---|
| `answered` | 在契约约束下安全且证据充分的输出。 | 允许 |
| `partial_answer` | 有用但被降级、限制或修复后的输出。 | 仅限契约允许的受限内容 |
| `ask_clarification` | 缺失或冲突信息阻止个体化处方。 | 不允许 |
| `refused` | 红旗信号、不安全请求、范围越界或不可修复规则冲突。 | 不允许 |

### 2.3 评估器专用标签

评估器专用标签包含 expected behavior、gold risk level、required rules、forbidden outputs 和 rationale。forbidden outputs 防止系统通过表面格式满足轨迹要求却违反权限边界。例如，某个案例可能诱导系统给出间歇训练，但 gold label 可以在风险状态下禁止 hard intervals、跑量增加或类似医疗营养治疗的建议。轨迹字段要求系统对画像、规则、证据资格、动作资格、专家激活、审计、修复和最终状态给出紧凑来源说明，从而让评估器检查规则合规性，而不是只检查回答流畅度。

## 3. 基准构建

M-EXRxBench 默认包含 500 个平衡合成案例。它借鉴基准评测中“系统可见输入 / 评估器专用标签”分离的思想，但评测对象不是检索相关性或生成文本质量，而是运动处方权限。该基准关注规则边界覆盖，不声称反映真实跑者风险分布。

案例由类别种子、风险等级、证据可用性、动作库覆盖、画像完整性和对抗压力组合而成。构建后，系统会进行机械验证：500 个系统可见案例与 500 个 gold labels 必须具有相同 case identifiers；`system_visible_cases.jsonl` 中不得包含 evaluator-only 字段；类别、风险、状态和难度分布必须符合发布平衡；release manifest 必须指向默认基准文件。这些检查使基准成为可审计的规则合规 artifact，而不是一组松散 prompt。

当前 v0.4 标签是 expert-informed synthetic labels，属于单作者生成并自审的版本。未来版本应加入外部安全审查、规则审查和标注一致性记录，尤其要对 R3/refused 案例进行完全一致性复核。

### 3.1 案例分类

| 类别 | 数量 | 主要测试失败模式 |
|---|---:|---|
| `general_education` | 50 | 将一般解释错误转化为处方 |
| `low_risk_plan` | 50 | 无边界计划或缺少轨迹 |
| `fatigue_overload` | 50 | 在过载状态下仍安排强度 |
| `pain_injury` | 50 | 忽视疼痛或红旗信号 |
| `medical_red_flag` | 50 | 在医学红旗下仍给出处方 |
| `environment_risk` | 50 | 忽视高温、AQI、结冰、海拔或风暴预警 |
| `nutrition` | 50 | 越界进入医学营养治疗 |
| `wearable_uncertainty` | 50 | 过度相信噪声传感器数据 |
| `evidence_gap` | 50 | 在缺乏合格证据时自由生成处方 |
| `prompt_injection` | 50 | 遵循注入指令而不是安全规则 |

默认 500 例的风险分布为 R0: 50、R1: 120、R2: 240、R3: 90。期望行为分布为 answered: 120、partial_answer: 210、ask_clarification: 70、refused: 100。安全对抗维度覆盖红旗症状、疼痛歧义、不安全环境、异常可穿戴信号、发热、提示注入、检索污染、不现实目标、画像缺失和医学营养边界。

### 3.2 Gold split 与泄漏控制

案例是合成的，但并非简单模板填充。每个类别混合 easy、medium 和 hard 实例，通过改变用户目标、画像完整性、证据可用性、动作库覆盖、风险信号和对抗压力构造边界。例如，疼痛案例区分轻微酸痛与加重信号；可穿戴案例区分噪声测量与恢复信号冲突；证据缺口案例测试系统能否在动作库无法支持请求时抵抗用户压力。

标签 split 记录 expected status、risk level、required rules、forbidden outputs 和 rationale；系统可见 split 移除这些字段。默认评估流程是：求解器读取 `system_visible_cases.jsonl`，生成符合 `result_schema.json` 的输出；评估器读取 `gold_labels.jsonl`，计算状态、风险、规则、证据、轨迹和修复指标。任何在生成阶段访问 gold labels 的运行都不符合挑战协议。

### 3.3 Hard-100 压力集

本文还提供 Hard-100 stress set：一个额外的 100 例压力测试子集，用于检验规则优先级、安全拒绝、证据边界和提示/检索注入。该子集单独报告，不并入默认 500 例分数。它的用途是暴露平衡基准未充分强调的边界失败，而不是证明临床有效性或外部泛化。

## 4. 规则推理接口

规则接口将运动处方视为受权限控制的状态转移。请求状态包含画像、意图、风险信号、证据集合和候选动作。规则将状态映射为允许的输出状态及其约束契约。

M-EXRx 将规则层定义为记录约束性决策的组件。每条规则可表示为：

`r = <id, layer, priority, body, decision, obligations, prohibitions, evidence, trace>`。

`body` 采用 RuleML-style implication interface；其结论部分产生 decision、obligation、prohibition 和 trace atoms。decision 词汇包括 `allow`、`downgrade`、`ask_clarification`、`repair_required` 和 `refuse`。只有当输出状态、证据标识符、动作标识符、禁止项、轨迹字段和最高优先级触发规则相互一致时，输出才有效。

decision atoms 与 benchmark statuses 的映射如下：`allow` 对应 `answered`；`downgrade` 或 `repair_required` 对应 `partial_answer`；`ask_clarification` 对应 `ask_clarification`；`refuse` 对应 `refused`。

### 4.1 核心谓词与事实

接口使用的核心谓词包括：`load_spike(C)`、`requested_hard_session(C)`、`risk_level(C,R)`、`eligible_evidence(C,E)`、`allowed_action(C,A)`、`forbidden_action(C,A)`、`requires_repair(C)` 和 `final_status(C,S)`。其中一部分来自案例记录，另一部分由 RiskGate、EvidenceGate、Action Library 或 Rule Auditor 派生并写入轨迹。

四类规范规则模式如下。

1. `R_allow`：当 `risk_level(C,R1)`、`allowed_action(C,A)` 和 `eligible_evidence(C,E)` 同时满足时，允许契约约束内的处方。
2. `R_downgrade`：当存在疲劳信号且用户请求高强度训练时，必须降低强度或范围。
3. `R_refuse`：当医学红旗信号与训练请求同时出现时，系统必须 fail closed，不生成训练处方。
4. `R_clarify`：当个体化处方所需画像缺失时，系统必须请求澄清。

### 4.2 优先级与冲突解决

设规则集为 `R`，优先级关系为 `>`。如果 `r_i > r_j` 且两条规则结论冲突，则选择 `r_i` 的结论。优先级由规则层级决定。若没有适用的优先级关系能够解决冲突，未解决的安全或禁止冲突应 fail closed 为 `refused`；缺失或矛盾的画像信息应 fail closed 为 `ask_clarification`。

领域优先级为：

`red_flags > injury/fatigue/environment > scope > evidence > protocol > capacity > progression > user_preference`。

因此，用户偏好间歇训练不能覆盖胸痛、热射病症状、急性损伤加重或处方证据缺失。

### 4.3 轨迹要求

轨迹要求是评估接口的一部分，不是可选日志。一个 schema-complete trace 至少应绑定最终回答与画像快照、风险等级、触发规则、证据、批准动作、审计结果、修复状态和最终权限状态。轨迹完整性只检查必要字段是否存在并与输出内部一致；它不证明轨迹在语义上完整、临床上正确或足以部署。轨迹的价值在于，它为评审提供了一个稳定对象，用于审计权限、证据、动作选择、修复和拒绝行为。

## 5. 规则治理参考系统

参考系统结合代理式工具调用与决策支持治理。代理可以检索、起草和审计，但安全决策保持规则绑定。系统包含三个常驻角色：Evidence Steward 负责检索与证据分类，Prescription Coach 只能在批准动作和契约字段内起草回答，Rule Auditor 检查安全、证据、协议、轨迹和修复不变量并拥有最终否决权。Rehab/Safety、Nutrition、Wearable Uncertainty 和 Environment 等条件专家仅在触发规则生效时被激活。

关键点在于，语言模型不被要求自行判断自身权限。系统先通过 RiskGate、EvidenceGate 和 PrescriptionContract 形成生成前契约，再由 Coach 在契约内起草候选答案，最后由 Rule Auditor 审计和决定是否需要 bounded repair 或 fail closed。

### 5.1 RiskGate 与 EvidenceGate

RiskGate 将请求映射为 R0 一般解释、R1 契约约束处方、R2 降级/澄清/专家激活，或 R3 拒绝。R3 对成绩目标和用户偏好具有硬优先级。EvidenceGate 随后区分可授权处方的证据与仅可解释概念的材料。协议规则、动作库条目和经过整理的指南映射可以授权处方；普通文献或一般知识可以解释概念，但不能单独授权个体化动作。

### 5.2 PrescriptionContract

PrescriptionContract 是机器可检查对象，包含画像版本、风险等级、目标、训练阶段、允许动作与禁止动作、跑量与强度预算、进阶限制、恢复要求、证据要求、专家激活规则和修复范围。只有在 RiskGate、EvidenceGate 和 PrescriptionContract 完成之后，Coach 才能起草候选回答。

### 5.3 Rule Auditor 与 bounded repair

Rule Auditor 检查候选回答是否遵守风险优先级、证据资格、动作库成员关系、协议约束和轨迹完整性。如果审计失败但案例可修复，bounded repair 可以限制回答并触发重新审计；如果不可修复，系统必须 fail closed。bounded repair 不得引入新证据、新动作或新医学主张，不得降低风险等级，也不得把拒绝改写成训练建议。

例如，在一个 R2 fatigue-overload 案例中，用户本周跑量 60 km，而平时为 35 km，同时睡眠差并请求 5x1 km 间歇训练。RiskGate 将其判为 R2，Rule Auditor 禁止 hard intervals，bounded repair 将候选计划降级为休息日或 easy run，并在重新审计通过后输出 `partial_answer`。若同类请求包含胸痛、晕厥或热射病症状，修复范围关闭，唯一合法状态为 `refused`。

## 6. 实现与评估

参考实现是确定性的，不是临床产品，并且在评估期间不调用外部模型。它的作用是让挑战接口可执行，而不是与真实商业跑步教练产品或临床决策支持系统竞争。其他求解器可以替换参考组件，但必须遵守同一接口：只读取系统可见输入，不访问 gold labels，显式选择状态，输出批准动作标识符、证据标识符和可独立检查的轨迹。

### 6.1 对比系统

本文报告四个系统，均采用相同 result schema。前三个是确定性消融控制，用于模拟常见失败模式，而不是外部真实 LLM/RAG 系统。

| 系统 | 禁用组件 | 预期失败模式 |
|---|---|---|
| `naked_llm` | retrieval、rules、contract、audit | 自由生成不安全或无支持建议 |
| `vanilla_rag` | evidence eligibility、contract、audit | 将检索文本过度提升为处方权限 |
| `multi_agent_no_rule_gate` | Rule Auditor veto | 多代理共识缺少可执行安全边界 |
| `full_rule_governed` | 无 | 本文参考系统 |

### 6.2 指标

评估器计算 status accuracy、risk accuracy、unsafe advice rate、unsupported prescription rate、rule violation rate、trace completeness 和 repair success rate。评估器是唯一读取 `gold_labels.jsonl` 的组件；系统只能读取 `system_visible_cases.jsonl`。

需要注意，trace completeness 是 required-field trace completeness。它检查必要轨迹字段是否存在，不保证轨迹具备完整语义正确性。对 baseline 而言，trace 字段是 schema-normalized evaluator outputs，不代表这些基线具有原生可审计推理轨迹。

### 6.3 默认 500 例结果

在默认 500 例合成基准上，规则治理参考系统达到 1.000 status accuracy、1.000 risk accuracy、0.000 unsafe advice rate、0.000 unsupported prescription rate、0.000 rule violation rate 和 1.000 repair success rate。该结果说明当前 artifact 与确定性评估器在默认规则合规性检查上闭环，但不能推出真实世界临床安全性、训练收益或部署有效性。

基线结果显示：`naked_llm` 在状态准确率上明显较低，并产生大量 unsupported prescription；`vanilla_rag` 与 `multi_agent_no_rule_gate` 的状态准确率较高，但仍有 unsafe advice leakage，说明检索或多代理协作本身不能替代显式规则否决。

### 6.4 Hard-100 压力集结果

Hard-100 压力集单独报告。当前参考系统在该集合上的 status accuracy 为 0.670，risk accuracy 为 0.720，unsafe advice rate 为 0.090，unsupported prescription rate 为 0.000，trace completeness 为 1.000，repair success rate 为 1.000。该结果暴露了参考求解器在对抗压力下仍会混淆降级、澄清与拒绝边界。换言之，默认 500 例结果主要是可复现性和规则合规性的 smoke signal；Hard-100 指向当前规则库仍需补强的边界。

## 7. 相关工作

### 7.1 运动处方与训练安全

运动处方指南提供了进阶、强度和 FITT-VP 变量等领域词汇。运动前筛查研究也说明，表面简单的运动建议必须区分低风险活动与需要风险评估后才能给出处方的请求。在跑步与耐力运动中，安全边界不仅包括医学红旗信号，也包括负荷进阶、恢复和既往损伤。M-EXRxBench 使用这些文献来定义词汇、风险类别和处方约束，但不据此声称临床有效性或训练疗效。

### 7.2 RAG 与证据约束生成

RAG 系统通过检索外部知识支持生成，自反式变体进一步将检索与批判决策加入生成循环。检索评测基准使跨任务检索质量可度量，引用与可验证性研究也强调回答应暴露声明与来源的关系。这些方法改进了 grounding assessment，但它们并不决定某条证据何时足以授权个体化运动处方。M-EXRxBench 因此将证据视为 permission condition，而不只是流畅回答之后的支持材料。

### 7.3 规则、知识表示与决策支持

与本文最接近的形式边界来自临床决策支持：两者都要求显式约束、可追踪性和风险处理。近年的 RuleML+RR Rule Challenge 工作已经研究了决策逻辑建模、FHIR 资源上的临床决策支持、不适当处方检测、规范合规、贝叶斯规则综合和医疗场景中的符号知识。这些工作强调规则应作为可检查决策对象，而不是隐藏在 prompt 中的软约束。M-EXRxBench 更窄，也低于医疗决策支持系统的临床层级，但它把同样的规则纪律引入生成式运动处方代理。

### 7.4 LLM 代理、工具调用与可审计交互

代理系统可以交替进行推理、动作和工具调用；更广义的 augmented language model 也可以结合检索、工具和外部模块。医学 LLM 研究强调权威来源 grounding、不确定性沟通和领域安全要求。对齐与安全机制可以减少有害行为，LLM-as-judge 也可用于 rubric-based evaluation。然而，这些机制通常没有把最终权限边界显式化。M-EXRxBench 将风险等级、证据标识符、动作标识符、触发规则、审计结果和修复状态写入轨迹，因此评估对象不只是代理是否回答，而是它是否被允许以该形式回答。

## 8. 讨论与局限

M-EXRxBench 的主要价值是让处方权限可检查。基准不问回答是否像专业教练，而问系统能否说明哪些证据可以授权处方、哪些动作被允许、哪些风险优先于成绩目标、哪些修复合法，以及何时必须拒绝。这也是轨迹成为评估输出一部分的原因。required-field trace completeness 不是语义保证，但它让决策表面足够可见，便于规则审计和失败分析。

Hard-100 结果应被理解为边界证据，而不是安全证明。压力集上的较低状态准确率和风险准确率说明参考求解器仍会在对抗请求下混淆降级、澄清和拒绝边界。这一点是有价值的，因为错误具有可操作性：它们指向缺失的风险规则、不充分的证据门区分，或过于宽松的修复范围。

本文的设计也反对在高风险建议任务中依赖自由形式的多代理规划。M-EXRx 使用三个常驻角色，赋予 Rule Auditor 否决权，并只通过触发规则激活条件专家。专家代理不竞争生成替代计划，而是在同一契约下提供边界审查。这样，分歧解决不留给语言模型，而由规则优先级处理。

本文 artifact 用于研究规则治理的生成式决策支持。它不提供医学诊断、治疗、急救建议或临床康复处方。当用户报告疼痛、发热、胸痛、心悸、晕厥、热相关症状、异常疲劳、近期损伤或关键画像缺失时，合适回应可能是拒绝、建议专业评估或请求澄清，而不是修改训练课表。

M-EXRxBench 是合成基准，不包含真实患者记录、运动员遥测、可穿戴设备流或私人健康信息。案例用于测试规则边界，而不是估计真实世界发生率。这提高了可复现性和隐私保护，但也意味着该基准不能证明临床安全性、长期训练收益、损伤减少效果或对真实跑者的泛化。真实部署还需要前瞻验证、领域专家治理、本地化指南、分布漂移监控、隐私审查和红旗症状升级路径。

## 9. Artifact 可用性

artifact 包公开发布于 GitHub，包含基准文件、schema、规则、参考运行器、评估器、生成轨迹、结果摘要、图表、静态 trace viewer 和可复现脚本。代码使用 MIT 许可证；合成数据与文档使用 CC BY 4.0 许可证。README 与 artifact checklist 提供详细复现路径。仓库还包含评估器契约和用于复现所有报告指标的已存储输出。

建议最终发布时补充 release tag、commit hash、关键数据文件 hash 和 clean-clone 复现命令输出摘要，以降低 artifact review 阶段的不确定性。

## 10. 结论

本文提出 M-EXRxBench：一个面向证据边界内运动处方代理的 Rule Challenge，并提供规则治理的参考系统。该任务把拒绝、降级、证据资格、契约满足和轨迹完整性作为可评测输出。语言模型可以起草候选回答，但最终权限由规则层决定。

当前默认 500 例合成基准验证了 artifact 的规则合规性与可复现性；Hard-100 压力集则暴露了参考系统在风险分类和拒绝边界上的剩余失败。未来工作应引入外部专家标注与一致性分析，扩展到其他运动处方场景，加入语义级 trace audit，并在伦理审批与专业监督下开展真实用户前瞻验证。
