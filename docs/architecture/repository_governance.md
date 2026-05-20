# 仓库治理规范

> 目标：让马拉松助手长期保持可运行、可复现、可发布、可审计、可迁移。

## 治理模型

本仓库不是单一应用仓库，而是产品 + 前端 + 后端 + 研究 + 数据 + 产物的 monorepo。长期管理重点不是继续搬目录，而是建立稳定的协作入口、验证门禁和产物边界。

参考模式：

- FastAPI full-stack template：前后端、脚本、文档和部署说明分层。
- PyPA sampleproject：Python 包使用 `src/`、`tests/`、`pyproject.toml`。
- Astro 官方结构：前端围绕 `src/pages`、`src/components`、`src/layouts`、`src/styles`、`public`。
- Cookiecutter Data Science：研究项目区分 raw data、可复用代码、notebooks/reports 和模型/产物。
- GitHub 官方协作规范：README、CONTRIBUTING、PR template、CODEOWNERS、large-file policy。

## 长期目录职责

| 目录 | 职责 | 规则 |
|---|---|---|
| `apps/backend/` | FastAPI、RAG、训练计划后端 | 保留 `marathon_qa_assistant.*` import；领域规则不放入 API router |
| `apps/web/` | Astro 前端 | 页面入口只做装配，组件、脚本、样式分域 |
| `tools/` | 可复用开发、KB、研究工具 | 新脚本优先放这里，旧 `scripts/` 只保留过渡 wrapper |
| `research/` | 论文、benchmark、分析材料 | 论文源码和 benchmark 定义留在 research，不放运行输出 |
| `data/` | 知识库资料、上传种子、向量库入口 | raw、curated、uploads、vector_kb 分层并维护 manifest |
| `artifacts/` | 研究运行、release package、UI audit | 产物必须能追溯项目、来源和用途 |
| `archive/` | 历史资产 | 真实历史资产保留 manifest，本地缓存进入 `archive/local_caches/` 并忽略 |
| `.github/` | 协作与 PR 规则 | CODEOWNERS、PR template 和后续 CI 放这里 |

## 改动类型与验证矩阵

| 改动类型 | 必跑命令 | 通过标准 |
|---|---|---|
| 仓库治理 / 文档 | `python tools/dev/check_repo.py --scope docs`、`git diff --check` | 链接存在，无旧路径污染，无空白错误 |
| 后端 API | `pytest tests/test_api_app.py tests/test_api_cli_startup_contract.py -q` | API 契约和启动入口不变 |
| 训练计划骨架 | `pytest tests/test_training_plan_skeleton.py tests/test_volume_allocation.py -q` | 结构化计划和跑量约束不回归 |
| 日程生成 | `pytest tests/test_daily_schedule_generator.py -q` | 月历、证据、风险门输出稳定 |
| 前端 | `cd apps/web; npm run build; npm run smoke:workspace` | Astro build 和 workspace smoke 通过 |
| 研究 / 数据 | `python tools/dev/check_repo.py --scope hygiene` + 项目 smoke | manifest、路径和大文件状态可审计 |

## PR 管理

- 每个 PR 使用 `.github/PULL_REQUEST_TEMPLATE.md`。
- 大文件、数据、artifacts 影响必须在 PR 中显式说明。
- 涉及 public facade 的重构必须说明兼容入口是否保留。
- 不建议一个 PR 同时包含前端大拆、后端规则改动和研究产物整理。
- 当前 `CODEOWNERS` 先使用 `@Ljy220058` 作为默认 owner；多人协作时再拆成团队 owner。

## 模块拆分 Gate

进入大文件拆分前必须满足：

- 已阅读 [模块边界审计 V1](module_boundary_audit.md)。
- 已确认本批只拆一个模块族。
- 已保留 public facade 一轮。
- 已跑拆分前 targeted tests，拆分后跑同一组。
- 如果测试绑定私有 helper，先把测试提升为输入输出契约。

## 大文件和产物策略

- GitHub 普通仓库不适合长期堆积大型 PDF、zip、FAISS index 和 release 包。
- 小型、必要、可复现的资料可版本化，但必须有 manifest。
- release package 优先进入 `artifacts/release_packages/<project>/` 并维护来源、用途和生成命令。
- 后续公开协作前，应单独评估 Git LFS、GitHub Releases 或外部存储。

## 自动检查入口

默认运行：

```powershell
python tools/dev/check_repo.py
```

常用 scope：

```powershell
python tools/dev/check_repo.py --scope docs
python tools/dev/check_repo.py --scope hygiene
python tools/dev/check_repo.py --scope large-files
```
