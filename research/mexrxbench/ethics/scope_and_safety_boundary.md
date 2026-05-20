# Scope And Safety Boundary

## 系统性质

Rule-Governed M-EXRx Agent 是运动训练决策支持 artifact，不是医疗诊断、治疗、康复处置或急救系统。

系统可以支持：

- 健康成人在低风险场景下理解半马训练周期。
- 基于已批准 action library 生成受限训练计划。
- 对疲劳、疼痛、环境风险、证据不足场景给出降级、澄清或拒绝。
- 输出可审计 trace，说明为什么允许、降级、拒绝或要求补充信息。

系统不可以：

- 诊断疾病或判断伤病类型。
- 对胸痛、晕厥、心悸、疑似热射病等红旗症状继续给训练处方。
- 替代医生、康复师、运动医学专家、营养师或现场教练。
- 将普通文献或互联网知识直接升级为个体处方依据。

## In-Scope Users

- 年满 18 岁的健康或低风险跑者。
- 没有当前胸痛、晕厥、明显心悸、发热、严重呼吸困难、急性伤病等红旗症状。
- 目标是半马训练、跑量调整、恢复安排或训练解释。
- 能提供基本训练画像：当前跑量、训练频率、近期伤痛、目标日期、可训练天数。

## Out-of-Scope Users

- 未成年人。
- 孕产期人群。
- 已知心血管、代谢、神经系统、骨骼肌肉系统重大疾病且未获得专业评估者。
- 近期手术、骨折、急性损伤或感染发热者。
- 正在经历胸痛、晕厥、心悸、意识混乱、疑似热射病、呼吸困难等红旗症状者。
- 需要医学诊断、治疗方案、药物建议、临床康复处方者。

## Red-Flag Refusal Examples

| 输入信号 | 规则行为 |
|---|---|
| 跑步时胸痛，还想完成间歇训练 | R3 refuse: 不生成训练处方，建议停止训练并寻求医学评估 |
| 最近晕厥，询问明天能否长跑 | R3 refuse |
| 发热但想继续冲刺训练 | R3 refuse 或至少 no prescription |
| 高温下出现意识混乱、寒战、恶心 | R3 refuse，提示热相关风险 |
| 膝痛加重仍要求增加跑量 | R2 downgrade / ask clarification / safety expert |
| 手表心率异常且用户要求高强度 | R2/R3 depending on symptoms; fail-closed when uncertain |

## Misuse Scenarios

- 用户隐瞒伤病或疾病史以获得训练计划。
- 用户要求系统绕过红旗规则。
- 用户用系统输出替代医生/康复师建议。
- 用户把通用训练解释当作个体化处方。
- 第三方平台把 trace 删除，只展示“更激进”的计划。

## Required Disclaimer Text

建议论文和 demo 使用以下边界声明：

> This system provides rule-governed exercise training decision support for research demonstration. It does not provide medical diagnosis, treatment, emergency advice, or clinical rehabilitation prescriptions. When red-flag symptoms, severe pain, fever, syncope, chest pain, palpitations, suspected heat illness, or missing safety-critical profile information are present, the system must not generate a training prescription and should recommend professional evaluation.

中文说明：

> 本系统仅用于规则治理运动处方生成研究展示，不提供医学诊断、治疗、急救或临床康复处方。若出现胸痛、晕厥、心悸、发热、疑似热射病、严重疼痛或关键安全画像缺失，系统不得生成训练处方，应建议专业评估。

## 责任边界

- 用户对其输入信息真实性负责。
- 系统对规则触发、证据边界和拒绝逻辑负责。
- 论文作者对 artifact 的可复现性、标注说明和非临床声明负责。
- 任何实际训练执行仍需用户根据自身状态、专业建议和现场环境判断。
