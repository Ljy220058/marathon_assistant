# Novelty Gap Review

## Q1: 为什么不是普通 RAG？

普通 RAG 的核心假设是：找到相关证据后，模型可以生成更可靠的答案。但运动处方不是普通知识问答。处方性建议涉及训练量、强度、恢复、禁忌、疼痛、环境风险和医学红旗；一篇文献与用户问题相关，不代表它可以支持对某个用户生成训练安排。

本文的差异：

- EvidenceGate 区分 `protocol_rule`、`action_library`、`curated_guideline`、`academic_literature`、`general_kb`。
- 只有具备处方资格的 evidence layer 才能进入计划生成。
- 普通论文或通用 KB 只能用于 explanation / discussion，不能直接升级为处方依据。
- 证据不足时必须输出 `needs_evidence`、澄清或拒绝，而不是用 LLM 常识补全。

## Q2: 为什么不是普通 multi-agent？

普通多智能体方案常见结构是“多个专家讨论，最后由教练总结”。这容易产生两个问题：一是角色数量多但权责不清；二是专家之间相互背书，不能保证高风险边界。

本文的差异：

- 常驻 agent 只保留 Evidence Steward、Prescription Coach、Rule Auditor。
- Rehab / Nutrition / Wearable / Environment 等专家按 RiskGate 条件触发。
- Rule Auditor 有否决权，Coach 不是最高权力者。
- agent 不能自由生成处方，必须满足 PrescriptionContract。
- 冲突裁决由 rule priority ladder 完成，而不是由自然语言协商完成。

## Q3: 为什么适合 RuleML+RR？

RuleML+RR 关注 rule-based reasoning、rule-based agents、Agentic AI、explainable decision-making、repair strategies、healthcare/life sciences、multi-agent systems、rule and ontology combinations。本文与这些关键词高度贴合。

更重要的是，本文把 LLM 系统转写成 Rule Challenge artifact：

- `M-EXRxBench` 定义任务和评价标准。
- RiskGate / EvidenceGate / PrescriptionContract 是可检查规则对象。
- Rule Auditor 和 bounded repair 展示规则如何裁决输出。
- trace 使每个计划、降级或拒绝都可追踪。

这比“LLM 跑步教练”更接近 RuleML+RR 的规则推理应用和挑战系统传统。

## Q4: 为什么 exercise prescription 是合理挑战？

运动处方介于健康建议和临床干预之间。它不是简单的“今天跑几公里”，而是需要考虑：

- 个体能力和训练史。
- 目标周期和训练阶段。
- FITT-VP 变量。
- 疼痛、疲劳、环境和可穿戴数据不确定性。
- 红旗症状和转诊边界。
- 证据能否支持处方。

这些特征使 exercise prescription 成为一个适合规则治理的挑战问题：低风险场景需要个性化计划，高风险场景需要降级或拒绝，证据不足场景需要 fail-closed。

## 预计审稿人质疑与答辩

| 质疑 | 答辩 |
|---|---|
| 这只是一个运动助手应用 | 本文主贡献是 benchmark + rule-governed reference solution，不是产品功能 |
| 规则只是 prompt checklist | 论文必须展示 rule tuple、priority relation、contract satisfaction、repair operator 和 evaluator |
| benchmark 是 synthetic，真实性不足 | 明确声明 expert-informed synthetic；提供 taxonomy、annotation guideline、gold split、adversarial cases |
| LLM 仍可能绕过规则 | 系统输出必须经 Rule Auditor；repair 后重审计；R3/证据不足 fail-closed |
| 运动处方不如临床处方高风险 | 本文不做临床声明，但训练计划仍涉及伤病、心血管红旗、热风险和过度训练，足以作为 safety-sensitive decision support challenge |
