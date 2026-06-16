# 仓库卫生维护路线图

> 范围：根目录清洁、缓存忽略、归档策略、artifacts 管理、大文件和 release package 治理。

## P0：根目录与忽略规则

- [ ] [repo-hygiene][P0] 保持根目录只承载一级功能目录和少量入口文件。完成定义：根目录不出现 `frontend/`、`marathon_qa_assistant/`、`vector_kb/`、`uploaded_docs/`、`knowledge_base/`、`node_modules/`。
- [ ] [repo-hygiene][P0] 定期清理本地缓存。完成定义：`.pytest_cache/`、`__pycache__/`、`apps/web/dist/`、`apps/web/node_modules/` 不进入 Git 变更。
- [ ] [repo-hygiene][P0] 保持 `.gitignore` 覆盖可再生成产物。完成定义：测试、前端 build、LaTeX build 后 `git status --short` 不出现缓存或构建目录。
- [ ] [search-noise][P0] 保持 `.rgignore` 覆盖默认检索噪声。完成定义：`rg --files | rg "node_modules|\.npm-cache|\.pytest_cache|__pycache__|archive/local_caches|apps/web/dist"` 无输出；正式 `archive/`、`artifacts/`、`research/` 不被整体排除。

## P1：归档治理

- [ ] [archive][P1] 合并历史批次命名规则。完成定义：`archive/history_batches/` 和日期批次目录有统一命名和索引。
- [ ] [archive][P2] 将本地缓存归档与真实历史资产分离。完成定义：`archive/local_caches/` 始终忽略，历史资产目录保留 manifest。

## P1：artifacts 与 release 包

- [ ] [artifacts][P1] 为 `artifacts/research_runs/` 建立 manifest。完成定义：每个研究运行目录能说明来源脚本、配置、模型和用途。
- [ ] [artifacts][P1] 为 `artifacts/release_packages/` 建立发布清单。完成定义：每个 PDF/zip 能追溯到研究项目、生成命令或提交记录。
- [ ] [artifacts][P2] 统一 UI audit 目录。完成定义：UI 审计产物进入 `artifacts/ui_audits/`，旧命名目录有迁移或归档说明。

## P2：大文件与公开协作

- [ ] [large-files][P2] 评估 Git LFS 是否必要。完成定义：列出 PDF、zip、FAISS index、图片等大文件清单，并决定 Git、LFS 或外部存储策略。
- [ ] [large-files][P2] 为公开仓库准备最小数据包。完成定义：公开分支不包含本地绝对路径、无关缓存、隐私上传文件或不可复现产物。
- [ ] [release][P2] 建立发布前卫生检查脚本。完成定义：`python tools/dev/check_repo.py` 能检查旧路径、缓存目录、大文件候选和 release package manifest。

## P1：持续检查命令

```powershell
git status --short --branch
Get-ChildItem -Force -Name
python tools/dev/check_repo.py
git grep -n --untracked "<old paper project path>" -- TODO.md docs/product docs/architecture docs/audits research/stai2026/TODO.md
rg --files | rg "node_modules|\.npm-cache|\.pytest_cache|__pycache__|archive/local_caches|apps/web/dist"
```

完成定义：状态和根目录检查不会暴露误入根目录的缓存或未说明的大型产物；TODO 与 roadmap 文档不再出现迁移前论文项目路径字面量；默认 `rg` 文件列表不包含本地依赖、缓存或前端构建产物。
