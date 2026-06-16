# 周期化训练文献清单与入库计划

> 状态：收集进行中。目标：支撑画像→训练周期的 RAG 决策链路。

## 已有文献（在 data/domain_docs/，部分待分块入库）

### 已入库（training_protocol 分片可检索）

| 文件 | 内容 | 块数 | 支撑参数 |
|---|---|---|---|
| `train_tapering_meta_2023.pdf` | 减量期系统综述与荟萃分析 | 329 | 减量时长、跑量削减幅度 |
| `protocol_taper_*` 系列 (9文件) | 初/中/高级跑者减量协议 | 9 | 分水平的减量期建议 |

### 待入库（有 PDF 但未分块到 KB）

| 文件 | 内容 | 应支撑参数 |
|---|---|---|
| `Seiler_2010_TID_Best_Practice.pdf` | 训练强度分布最佳实践 | 基础期/建设期高强度课次上限（80/20 原则） |
| `Stoggl_2014_Polarized_vs_Threshold.pdf` | 极化训练 vs 阈值训练对比 | 业余跑者选极化还是阈值训练 |
| `Midgley_2007_Marathon_Physiology.pdf` | 马拉松训练生理学决定因素 | 长距离递增节奏与 VO2max 关系 |
| `Gabbett_2016_ACWR_Paradox.pdf` | 急慢性负荷比 | 每周跑量递增安全上限（10% 规则） |
| `train_low_intensity_2025.md` | 低强度训练理论与实践 | 基础期轻松跑比例依据 |
| `train_marathon_physiology_2025.md` | 2025 马拉松生理学综述 | 阶段转换的生理依据 |

## 待收集文献

### P0（直接支撑现有硬编码参数）

| 文献 | DOI/URL | 支撑参数 | 状态 |
|---|---|---|---|
| Bosquet et al. (2007) "Effects of tapering on performance: a meta-analysis" | DOI: 10.1249/mss.0b013e31806010e0 | 减量期 2-3 周、跑量削减 41% | 待下载 |
| Muñoz et al. (2014) "Does polarized training improve performance in recreational runners?" | DOI: 10.1123/ijspp.2012-0350 | 业余跑者极化训练效果 | 待下载 |
| Esteve-Lanao et al. (2007) "Impact of training intensity distribution on performance in endurance athletes" | DOI: 10.1519/R-19725.1 | 不同阶段高强度比例对比 | 待下载 |

### P1（完善阶段决策证据链）

| 文献 | 方向 | 状态 |
|---|---|---|
| Pfitzinger & Douglas, Advanced Marathoning (2009) | 分水平跑者的阶段分配模板 | 待收集摘要 |
| Daniels, Running Formula (2022) | VDOT 体系下的阶段分布建议 | 待收集摘要 |
| Bompa & Haff, Periodization (2009) | 周期化理论基础的周数分配原则 | 待收集摘要 |
| Shaw et al. (2022) | 业余跑者减量时长研究 | 待检索 |

### P2（长远补全，不阻塞当前进度）

- Neal et al. (2013) 极化 vs 阈值业余组对照
- Casado et al. (2022) 精英跑者建设期强度分布
- Mujika & Padilla (2003) 减量期生理指标变化

## 入库流程

1. PDF 放 `data/domain_docs/`
2. 用 `tools/kb/build_expert_preview_chunks.py` 分块
3. 用 `python -m marathon_qa_assistant.services.vector_store --mode build` 重建索引
4. 验证：`vector_store --mode test --query "减量期持续时长建议"`
