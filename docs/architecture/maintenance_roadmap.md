# 架构维护路线图

> 范围：长期工程维护、路径契约、API 契约、测试门禁、前端拆分和兼容层退役。

## P0：路径与运行契约

- [ ] [architecture-paths][P0] 固化 `PROJECT_ROOT`、`MARATHON_DATA_DIR`、默认向量库、用户向量库、上传目录、研究运行目录的路径契约。完成定义：`tests/test_monorepo_paths.py` 覆盖这些路径并通过。
- [ ] [architecture-paths][P0] 保留旧路径 fallback 的退役计划。完成定义：每个 fallback 有文档说明、测试覆盖和移除条件。
- [ ] [architecture-docs][P0] 更新所有启动命令为 monorepo 新路径。完成定义：README、架构文档、工具文档不再指导用户从旧根目录启动。

## P1：后端维护

- [ ] [backend-api][P1] 为 FastAPI 关键接口沉淀稳定契约。完成定义：健康检查、画像、计划、日历接口有测试和文档入口。
- [ ] [backend-rag][P1] 明确产品 RAG、研究 RAG、Ragas 评测之间的边界。完成定义：在线链路和评测脚本的输入输出不混用。
- [ ] [backend-workflow][P1] 将 LangGraph 工作流节点责任写入架构文档。完成定义：节点职责、输入输出状态、fallback 行为能从文档定位。

## P1：前端维护

- [ ] [module-boundary][P1] 先完成 [模块边界审计 V1](module_boundary_audit.md) 的拆分 gate，再进入前端和后端大文件拆分。完成定义：每个拆分批次都有 public facade、目标测试和回滚边界。
- [ ] [frontend-structure][P1] 拆分 `apps/web/src/pages/index.astro`。完成定义：页面入口只做数据装配和布局，组件进入 `components/` 或等价目录。
- [ ] [frontend-structure][P1] 拆分 `apps/web/src/styles/global.css`。完成定义：全局样式、组件样式、布局样式边界清楚，`npm run build` 通过。
- [ ] [frontend-contract][P1] 为前端工作区 smoke 保留稳定脚本。完成定义：`npm run smoke:workspace` 能验证主工作台加载。

## P1：工具与兼容层

- [ ] [tools][P1] 将长期脚本入口集中到 `tools/`。完成定义：KB、STAI、dev 工具均有新路径命令示例。
- [ ] [tools][P1] 退役 `scripts/*.py` 兼容 wrapper。完成定义：无 README、测试或自动化引用旧入口后，wrapper 删除或改为迁移提示。
- [ ] [contracts][P2] 决定 `packages/shared-contracts/` 的生命周期。完成定义：共享 schema/type 正式落地，或移除空目录并记录原因。

## P1：命名与检索治理

- [ ] [discovery][P1] 维护 [命名与检索治理](naming_and_discovery.md)。完成定义：新增代码、工具和配置路径遵守 ASCII + `snake_case`；新增产品/架构文档路径使用 ASCII slug，中文放标题中。
- [ ] [discovery][P1] 为长题名资料和高噪声产物补 manifest。完成定义：`research/`、`data/uploads/seed/`、`artifacts/` 中需要索引的资料有 `short_id`、路径、主题、来源、用途和质量状态。
- [ ] [discovery][P2] 分批消化当前命名例外。完成定义：每批迁移前后都运行引用搜索和链接检查，且不破坏既有论文、实验或产品引用链。

## P2：可观测性

- [x] [observability][P2] 建立 [可观测性基线](observability_baseline.md)。覆盖 SLI/SLO 定义、排查顺序、指标端点 (`/ops/metrics`)、request-id 关联和告警分级。
- [x] [observability][P2] 结构化日志与安全脱敏。完成定义：`marathon_qa_assistant.core.observability` 和 `logging_middleware` 覆盖 request_id、path、method、status_code、duration_ms、generation_status 字段，日志不含 API key、token、OAuth secret。

## P1：测试门禁

- [ ] [quality-gate][P1] 建立提交前最小验证组合。完成定义：[仓库治理规范](repository_governance.md) 中的改动类型验证矩阵覆盖 Python targeted tests、前端 build、workspace smoke、研究路径验证。
- [ ] [quality-gate][P1] 维护 `tools/dev/check_repo.py`。完成定义：`python tools/dev/check_repo.py --scope docs` 和 `--scope hygiene` 能独立运行，覆盖链接、旧路径、缓存噪声、大文件候选和 `git diff --check`。
- [ ] [quality-gate][P1] 区分产品测试、前端契约测试、研究脚本 smoke。完成定义：测试目录或文档能说明每组测试保护什么行为。
- [ ] [quality-gate][P2] 为大规模研究产物变更建立轻量验证。完成定义：路径和 manifest 校验可独立运行，不要求重跑完整实验。
