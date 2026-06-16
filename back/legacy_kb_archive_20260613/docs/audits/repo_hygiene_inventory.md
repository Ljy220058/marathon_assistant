# 仓库卫生检查清单

日期：2026-05-21
工作目录：`C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手`
分支：`codex/5/20`

## 迁移前状态

- 工作区已有大量未提交修改与未跟踪研究产物，目录重构必须采用“移动并保留”的策略，不做删除式清理。
- 根目录混合了承载产品运行的 Python 包、Astro 前端、论文项目、知识库 PDF、向量索引、实验输出、历史归档和本地缓存。
- 当前最大目录体量：
  - `.git`：约 586 MB
  - `docs`：约 307 MB
  - `lib`：约 138 MB，疑似误落入仓库根的 Python site-packages，本轮不迁入 Monorepo 正式结构
  - `frontend`：约 134 MB，主要包含 `node_modules`、`.astro`、`dist` 等可再生成内容
  - `knowledge_base`：约 73 MB
  - `uploaded_docs`：约 29 MB
  - `artifacts`：约 22 MB

## 需要治理的目录类型

| 类型 | 当前位置 | 目标位置 | 处理方式 |
|---|---|---|---|
| 后端源码 | `marathon_qa_assistant/` | `apps/backend/src/marathon_qa_assistant/` | 移动，保留公开 import |
| Astro 前端 | `frontend/` | `apps/web/` | 移动，后续再拆大文件 |
| 前端静态资源 | `public/` | `apps/web/public/` | 移动 |
| 默认向量库 | `vector_kb/` | `data/vector_kb/default/` | 移动并保留旧路径 fallback |
| 用户向量库 | `vector_kb_user/` | `data/vector_kb/user/` | 移动并保留旧路径 fallback |
| 上传资料 | `uploaded_docs/` | `data/uploads/seed/` | 移动 |
| 知识库源材料 | `knowledge_base/` | `data/knowledge/` | 按 raw/curated/packs 归类 |
| STAI 论文与 benchmark | 迁移前论文项目目录 | `research/stai2026/` | 按 manuscript/benchmark/analysis 归类 |
| M-EXRxBench | 迁移前论文项目下的 RuleML 子目录 | `research/mexrxbench/` | 移动为独立研究子项目 |
| STAI runs | 迁移前论文项目下的 runs 目录 | `artifacts/research_runs/stai2026/` | 移动 |
| UI 审计截图 | `artifacts/ui_audit_*` | `artifacts/ui_audits/` | 归类 |
| Chainlit 遗留配置 | `.chainlit/`、包内 `.chainlit/` | `archive/legacy_chainlit/` | 归档 |
| 本地依赖/缓存 | `lib/`、`frontend/node_modules/`、`.pytest_cache/` | 不进入正式结构 | `.gitignore` 明确忽略 |

## 风险点

- 多个脚本曾硬编码迁移前论文项目目录、`vector_kb`、`uploaded_docs`，迁移时必须同步更新默认路径。
- 现有测试直接读取 `frontend/src/pages/index.astro`，迁移到 `apps/web` 后必须更新测试路径。
- `app_state.py` 是所有运行时路径的统一入口，需保留 `PROJECT_ROOT`、`MARATHON_DATA_DIR`、旧根路径 fallback。
- 迁移前论文项目目录中包含论文源码、输出 PDF、zip 包、benchmark、runs 和人工审计记录，不能整体当作普通 docs 移走。

## 验收口径

- 根目录不再承担产品源码、前端源码、知识库、论文项目的直接承载职责。
- 可再生成缓存继续被忽略，不作为研究或产品资产迁移。
- 旧入口在一个过渡周期内通过 wrapper 或文档说明可定位到新入口。
- `pytest` 的路径契约、API 基础测试、RAG 检索单元测试、前端源码契约测试可以运行。

## Migration Landing Record

- Backend package: `apps/backend/src/marathon_qa_assistant/`
- Frontend: `apps/web/`
- Default vector KB: `data/vector_kb/default/`
- User vector KB: `data/vector_kb/user/`
- Seed uploads: `data/uploads/seed/`
- STAI: `research/stai2026/` and `artifacts/research_runs/stai2026/`
- M-EXRxBench: `research/mexrxbench/` and `artifacts/research_runs/mexrxbench/`
- Tools: `tools/kb/`, `tools/research/stai/`, `tools/dev/`
- Legacy `scripts/*.py`: compatibility wrappers for one transition round.
- Chainlit legacy files: `archive/legacy_chainlit/`
- Local caches: `archive/local_caches/`, ignored by `.gitignore`.
