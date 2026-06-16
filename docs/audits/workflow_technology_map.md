# 工作流技术使用映射

日期：2026-05-21

本文件用于核对论文/研究材料中提到的关键技术，在当前项目中属于“产品已用”“实验脚本已用”还是“文档或论文声称”。它不是性能结论，只是代码与工作流证据表。

## 技术映射

| 技术/机制 | 当前证据位置 | 使用状态 | 说明 |
|---|---|---|---|
| LangGraph 工作流 | `apps/backend/src/marathon_qa_assistant/core/workflow_graph.py`、`workflow.py` | 产品已用 | 后端工作流入口通过 `StateGraph` 或 fallback app 装配安全、路由、检索、计划、专家、输出节点。 |
| FastAPI 本地 API | `apps/backend/src/marathon_qa_assistant/apps/api_app.py` | 产品已用 | Astro 前端通过本地 API 读取健康状态、画像、计划与日历数据。 |
| Astro 前端 | `apps/web/src/pages/index.astro`、`apps/web/src/styles/global.css` | 产品已用 | 当前主交互入口。 |
| RAG / FAISS 检索 | `apps/backend/src/marathon_qa_assistant/services/vector_store.py` | 产品已用 | 支持文档切块、FAISS 索引、query variant、检索结果合并与证据返回。 |
| 知识库启动健康检查 | `apps/backend/src/marathon_qa_assistant/core/kb_bootstrap.py` | 产品已用 | 启动时按用户库、运行时库、默认库、旧路径 fallback 的顺序加载。 |
| GraphRAG / 知识图谱 | `apps/backend/src/marathon_qa_assistant/services/knowledge_graph.py` | 产品部分使用 | 包含实体/关系抽取、图谱持久化、周级训练草案辅助；GraphRAG 外部 CLI 材料仍主要体现在文档与历史配置。 |
| Evidence gate | `tools/research/stai/run_stai_s3_full_workflow.py`、`research/stai2026/analysis` | 实验脚本已用 | STAI S3 工作流中以 evidence mode、gold evidence、retrieval evidence 组织证据边界。 |
| Risk gate / safety stress | `tools/research/stai/run_stai_s3_full_workflow.py`、`configs/experiments/stai/*safety*` | 实验脚本已用 | 安全压力集与 risk/safety 判断主要在论文实验脚本和配置里体现。 |
| Repair / audit workflow | `tools/research/stai/run_stai_s3_full_workflow.py`、`research/mexrxbench/rule_spec/` | 实验脚本已用 | STAI ablation 与 M-EXRxBench rule spec 中都有 no-repair/no-audit 或 repair contract 对照。 |
| 多专家节点 | `apps/backend/src/marathon_qa_assistant/nodes/expert_nodes.py` | 产品已用 | Coach/Therapist/Nutritionist/Auditor 等专家节点参与结构化报告生成。 |
| 周级训练调度 | `apps/backend/src/marathon_qa_assistant/services/knowledge_graph.py`、`training_plan_skeleton.py` | 产品已用 | 通过周级状态推进与约束传播减少逐日孤立决策。 |
| Ragas 评估 | `tools/kb/evaluate_rag_ragas.py` | 工具脚本已用 | 评测脚本计算 Ragas 指标和传统检索指标；不属于在线产品运行链路。 |

## 判断边界

- “产品已用”表示当前后端或前端运行路径会直接调用。
- “实验脚本已用”表示论文/benchmark 脚本中实现并可复现实验逻辑，但不一定进入日常产品 UI。
- “文档或论文声称”需要在后续论文复盘中继续降调，不能写成产品部署能力或临床安全能力。
