# 论文 RAG 文献分组

## 分组概览

| 分组 | 数量 | 本地 PDF | 用途 |
|---|---:|---:|---|
| `endurance_training_protocols` | 7 | 6 | 运动处方、周期化、强度分布、赛前减量 |
| `load_injury_safety` | 7 | 4 | 损伤风险、负荷监控、疼痛/疲劳反馈、安全降级 |
| `nutrition_hydration_race_fueling` | 7 | 6 | 马拉松补给、水合、营养时机、补剂安全 |
| `ai_rag_evidence_explanation` | 6 | 6 | RAG、引用生成、事实性评估、健康 RAG 风险 |
| `hci_health_recommender_systems` | 6 | 5 | Human-AI interaction、健康推荐、用户建模、过度依赖 |

## 使用建议

`endurance_training_protocols` 用于论文方法的运动训练背景，但进入产品前要抽成规则，不直接以 chunk 覆盖计划。

`load_injury_safety` 用于安全约束和反馈闭环，例如疼痛、疲劳、主观负荷、训练突增。

`nutrition_hydration_race_fueling` 用于非核心处方解释和比赛补给建议，补剂相关内容必须加保守提示。

`ai_rag_evidence_explanation` 用于论文 related work、系统方法和评测章节。

`hci_health_recommender_systems` 用于交互设计、用户画像、AI 辅助决策与解释边界。

## 入口文件

- `knowledge_base/canonical/academic_literature/source_registry.md`
- `knowledge_base/canonical/academic_literature/paper_cards.jsonl`
- `knowledge_base/packs/literature_pack/*/manifest.json`

