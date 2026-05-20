# STAI Text Integrity Diagnostics

## 1. 结论

本轮检查显示：当前主要 STAI 数据和实验输出文件在 Python UTF-8 读取路径下是可读中文，未检测到明显 mojibake 标记。

此前在 PowerShell `Get-Content` 中看到的乱码，更可能是**终端显示编码问题**，不是 JSONL 文件本体损坏。

## 2. 检查工具

新增脚本：

- `scripts/check_stai_text_integrity.py`
- `scripts/export_stai_spotcheck_pack.py`

检查命令：

```bat
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe scripts\check_stai_text_integrity.py --json-out docs\paper_project\31_STAI_text_integrity_report.json
```

输出：

- `docs/paper_project/31_STAI_text_integrity_report.json`

## 3. 检查范围

已扫描：

| file | rows | suspicious markers |
|---|---:|---:|
| `docs/paper_project/stai2026_pilot_benchmark_v0.1.jsonl` | 15 | 0 |
| `docs/paper_project/stai_benchmark_v0.2_50_question_draft.jsonl` | 50 | 0 |
| `docs/paper_project/runs/stai_s0_norag_qwen2_5_20260510_run01/outputs.jsonl` | 15 | 0 |
| `docs/paper_project/runs/stai_s1_vanilla_rag_qwen2_5_after_reboot_full01/outputs.jsonl` | 15 | 0 |
| `docs/paper_project/runs/stai_s3_gold_only_50q_v02_run01/outputs.jsonl` | 50 | 0 |
| `docs/paper_project/runs/stai_s3_retrieval_only_50q_v02_run01/outputs.jsonl` | 50 | 0 |
| `docs/paper_project/runs/stai_s3_retrieval_plus_gold_50q_v02_run01/outputs.jsonl` | 50 | 0 |

示例：`first_question` 均能以正常中文读取：

> 优秀耐力运动员的训练强度分布通常有什么特点？

## 4. Spot-check clean pack

已导出清洁人审包：

- `docs/paper_project/spotcheck/stai_s3_retrieval_plus_gold_50q_v02_spotcheck.md`
- `docs/paper_project/spotcheck/stai_s3_retrieval_plus_gold_50q_v02_spotcheck.jsonl`

导出命令：

```bat
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe scripts\export_stai_spotcheck_pack.py
```

该人审包从 `stai_s3_retrieval_plus_gold_50q_v02_run01` 中抽取 15 条样本，包含：

- question
- final_status / gate / audit / repair
- gold evidence
- retrieved evidence preview
- final answer
- human review fields

## 5. 论文使用规则

可以使用：

- Python 脚本读取的 UTF-8 JSONL 内容。
- `spotcheck` 目录下导出的 Markdown / JSONL 人审包。
- `summary_auto.json` 与 `summary_auto.md` 中的结构化指标。

谨慎使用：

- PowerShell `Get-Content` 直接显示的中文片段。
- 终端中复制出的中文答案。

不建议使用：

- 未经过 `check_stai_text_integrity.py` 扫描的旧实验文本。
- 没有人审过的 final answer 作为论文案例。

## 6. 剩余风险

当前检查只能说明“文件文本可被 UTF-8 正常读取，未命中常见 mojibake 标记”，不能替代人工语义审查。

投稿前仍需继续完成：

- 更大范围的人审或专家审查。
- citation 是否真实对应 evidence chunk 的人工核验。
