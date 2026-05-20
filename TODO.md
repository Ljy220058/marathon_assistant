# TODO 总索引

> 角色：根目录 `TODO.md` 只做长期维护总索引，不再承载完整产品 backlog、论文投稿清单或实验运行任务。
>
> 工作目录：`C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手`

## 长期维护目标

- 可运行：`apps/backend`、`apps/web`、核心工具脚本有明确启动命令和 smoke 验证。
- 可复现：研究 benchmark、运行产物、release package 有固定入口和来源说明。
- 可发布：产品、研究、数据、归档和产物分层清楚，发布前能排除缓存和本地依赖。
- 可审计：路径、证据链、技术使用状态、仓库卫生检查都有文档记录。
- 可迁移：旧入口保留过渡说明，新入口作为唯一长期维护目标。

## 任务分流规则

| 任务类型 | 维护入口 | 规则 |
|---|---|---|
| 产品体验、UI 组件、用户可感知能力 | [docs/product/backlog.md](docs/product/backlog.md) | 只放产品能力，不混入论文和仓库治理。 |
| 后端架构、API 契约、测试门禁、前端拆分 | [docs/architecture/maintenance_roadmap.md](docs/architecture/maintenance_roadmap.md) | 记录长期工程债和演进方向。 |
| 仓库协作、PR 规范、代码归属、验证矩阵 | [docs/architecture/repository_governance.md](docs/architecture/repository_governance.md) | 所有长期协作规则先进入治理文档，再进入自动化脚本。 |
| 命名、检索边界、manifest 入口 | [docs/architecture/naming_and_discovery.md](docs/architecture/naming_and_discovery.md) | 先查命名规范和 manifest，再打开长题名资料或历史产物。 |
| 缓存、归档、大文件、artifacts、发布包治理 | [docs/audits/repo_hygiene_roadmap.md](docs/audits/repo_hygiene_roadmap.md) | 记录仓库卫生规则和验收口径。 |
| STAI 2026 论文和 benchmark | [research/stai2026/TODO.md](research/stai2026/TODO.md) | 只维护 STAI 项目剩余任务和历史索引。 |
| M-EXRxBench / RuleML 研究线 | [research/mexrxbench/TODO.md](research/mexrxbench/TODO.md) | 保留独立研究项目 TODO，不重复搬运。 |
| 知识库质量、证据包、RAG 资料治理 | [docs/knowledge_base/implementation_slices.md](docs/knowledge_base/implementation_slices.md) | 与产品功能和研究实验分开管理。 |

## 当前维护轨道

- [产品体验](docs/product/backlog.md)：训练计划、画像、反馈、证据、进度和日历体验。
- [后端架构](docs/architecture/maintenance_roadmap.md)：路径契约、API 契约、测试门禁、兼容 wrapper 退役。
- [仓库治理](docs/architecture/repository_governance.md)：贡献指南、PR 模板、CODEOWNERS、验证矩阵和自动检查入口。
- [命名与检索治理](docs/architecture/naming_and_discovery.md)：路径命名规则、`.rgignore` 边界和 manifest 契约。
- [前端维护](docs/architecture/maintenance_roadmap.md)：拆分 `apps/web/src/pages/index.astro` 和 `global.css`，形成组件边界。
- [数据与知识库](docs/knowledge_base/implementation_slices.md)：知识库资料分层、证据质量、检索评测。
- [研究复现](research/stai2026/TODO.md)：STAI 复现包、claim boundary、artifact index。
- [发布治理](docs/audits/repo_hygiene_roadmap.md)：release package、artifacts、缓存、大文件策略。
- [仓库卫生](docs/audits/repo_hygiene_roadmap.md)：根目录清洁、忽略规则、归档规则。

## Manifest 入口

- [M-EXRxBench 运动健康交叉研究 manifest](research/mexrxbench/analysis/exercise_health_cross_research_2026/manifest.md)：长题名论文 notes、PDF 和主题索引。
- [上传种子资料 manifest](data/uploads/seed/manifest.md)：上传资料、隔离资料、中文名和特殊字符文件入口。
- [Artifacts manifest](artifacts/MANIFEST.md)：研究运行、发布包、UI 审计和历史产物入口。

## P0 总控 TODO

- [ ] [repo-hygiene][P0] 保持根目录只出现 `README.md`、`requirements.txt`、`TODO.md`、配置文件和一级功能目录。完成定义：`Get-ChildItem -Force -Name` 不出现产品源码、前端源码、知识库或运行缓存旧根目录。
- [ ] [repo-governance][P0] 维护 `CONTRIBUTING.md`、`.github/PULL_REQUEST_TEMPLATE.md`、`.github/CODEOWNERS` 和 [仓库治理规范](docs/architecture/repository_governance.md)。完成定义：新 PR 可按模板说明改动类型、验证、风险和 data/artifacts impact。
- [ ] [architecture][P0] 确认所有长期文档入口使用新路径，不再指向迁移前论文项目路径。完成定义：对 TODO 和 roadmap 文档运行旧路径字面量搜索无输出。
- [ ] [discovery][P0] 维护命名规范、`.rgignore` 和高噪声资料 manifest。完成定义：`rg --files` 缓存噪声检查无输出，新增 manifest 中的本地路径均可 `Test-Path`。
- [ ] [quality-gate][P0] 使用 `python tools/dev/check_repo.py` 作为仓库治理默认检查入口。完成定义：docs/hygiene/large-files scope 能分别覆盖文档链接、缓存噪声、大文件候选和 `git diff --check`。
- [ ] [architecture][P1] 逐步退役 `scripts/*.py` 兼容 wrapper。完成定义：README 和 CI/本地命令全部改用 `tools/` 后，移除对应 wrapper 或改为明确迁移提示。
- [ ] [frontend][P1] 拆分 `apps/web/src/pages/index.astro` 和 `apps/web/src/styles/global.css`。完成定义：页面入口只负责装配，主要 UI 组件和样式进入清晰子目录，并通过 `npm run build`。
- [ ] [contracts][P2] 决定 `packages/shared-contracts/` 是否正式承载前后端共享契约。完成定义：要么放入版本化 schema/type，要么移除空壳并在架构文档记录决策。

## 维护约定

- 新增 TODO 必须写明轨道、优先级和完成定义。
- 产品、研究、仓库治理任务不得混在同一个 backlog 中。
- 已完成的历史任务应转入对应项目的 Done/Archive 或引用既有记录，不继续堆在根目录。
- 执行任何目录迁移前先更新 [docs/audits/repo_hygiene_inventory.md](docs/audits/repo_hygiene_inventory.md) 或对应 roadmap。
