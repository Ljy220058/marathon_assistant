# Exercise Health Cross Research 2026 Manifest

> 项目：M-EXRxBench / exercise-health cross research
>
> 目的：为长题名论文 notes、PDF 和分段索引提供短入口。完整 90 篇论文清单仍以 [INDEX.md](INDEX.md) 为准。

## 入口

| short_id | path | topic | source | purpose | quality_state | next_action |
|---|---|---|---|---|---|---|
| `main_index` | [INDEX.md](INDEX.md) | all topics | generated from review source noted inside index | 90 篇论文总索引、题名、DOI、PDF 状态 | active | 更新论文条目时同步维护 |
| `index_001_030` | [index_fragments/index_001_030.md](index_fragments/index_001_030.md) | clinical, biology, biomechanics | split index | 轻量检索 001-030 | active | 与 `main_index` 保持一致 |
| `index_031_060` | [index_fragments/index_031_060.md](index_fragments/index_031_060.md) | injury, nutrition, policy | split index | 轻量检索 031-060 | active | 与 `main_index` 保持一致 |
| `index_061_090` | [index_fragments/index_061_090.md](index_fragments/index_061_090.md) | equity, technology, urban design | split index | 轻量检索 061-090 | active | 与 `main_index` 保持一致 |
| `paper_notes` | [papers/001_relative-efficacy-of-prehabilitation-interventions-and-their-components.md](papers/001_relative-efficacy-of-prehabilitation-interventions-and-their-components.md) | paper notes | generated notes | 单篇 Markdown notes，文件名使用编号 + slug | active | 通过 `INDEX.md` 查具体编号 |
| `pdf_cache` | [pdfs/004_effects-of-different-doses-of-exercise-and-diet-induced-weight-loss-on-beta-cell-funct.pdf](pdfs/004_effects-of-different-doses-of-exercise-and-diet-induced-weight-loss-on-beta-cell-funct.pdf) | downloaded PDFs | public/OA PDF where available | 公开可访问 PDF 缓存 | active | PDF 来源以 `INDEX.md` 的 PDF 状态为准 |

## 主题短名

| short_id | topic | paper range | primary entry |
|---|---|---:|---|
| `clinical_exercise_medicine` | Clinical Exercise Medicine | 001-010 | [INDEX.md](INDEX.md) |
| `exercise_biology` | Exercise Biology & Physiology | 011-020 | [INDEX.md](INDEX.md) |
| `exercise_biomechanics` | Exercise Biomechanics | 021-030 | [INDEX.md](INDEX.md) |
| `injury_prevention` | Injury Prevention | 031-040 | [INDEX.md](INDEX.md) |
| `nutrition` | Nutrition | 041-050 | [INDEX.md](INDEX.md) |
| `policy` | Policy | 051-060 | [INDEX.md](INDEX.md) |
| `equity` | Social Determinants & Equity | 061-070 | [INDEX.md](INDEX.md) |
| `technology_engineering` | Technology & Engineering | 071-080 | [INDEX.md](INDEX.md) |
| `urban_design_pa` | Urban Design and Physical Activity | 081-090 | [INDEX.md](INDEX.md) |

## 检索方式

```powershell
rg "heart rate|wearable|injury" research/mexrxbench/analysis/exercise_health_cross_research_2026/INDEX.md
rg "beta-cell|running step rate" research/mexrxbench/analysis/exercise_health_cross_research_2026/papers
rg --files research/mexrxbench/analysis/exercise_health_cross_research_2026/pdfs
```

## 命名规则

- 单篇 Markdown 使用 `NN_topic_slug.md`。
- PDF 使用 `NN_topic_slug.pdf`，保留较长 slug 以便与 `INDEX.md` 对齐。
- 新增论文先写入 `INDEX.md`，再落 `papers/` 或 `pdfs/`。
- 不直接用长题名猜路径；先按编号或 DOI 在 `INDEX.md` 中定位。
