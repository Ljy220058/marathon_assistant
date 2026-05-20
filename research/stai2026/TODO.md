# STAI 2026 TODO

> 范围：`research/stai2026/` 下的 STAI 论文、benchmark、claim-evidence audit、复现包和投稿材料。
>
> 已完成的大量历史打磨任务不再堆在根目录；历史证据见 `research/stai2026/analysis/`、`artifacts/research_runs/stai2026/` 和 `artifacts/release_packages/stai2026/`。

## P0：Claim 与证据边界

- [ ] [stai-claims][P0] 增加 claim boundary 表。完成定义：主稿或补充材料明确区分 supported claims、diagnostic claims、unsupported/forbidden claims。
- [ ] [stai-claims][P0] 增加“实验结果支持哪个 claim”的映射表。完成定义：每个核心数字都能对应到一个论文 claim 和 artifact 来源。
- [ ] [stai-claims][P0] 更新 claim-evidence audit 主依据。完成定义：`research/stai2026/analysis/55_STAI_claim_evidence_audit_v0.1.md` 或后续版本覆盖最终投稿版本。

## P1：复现与 artifact

- [ ] [stai-repro][P1] 更新 STAI artifact index。完成定义：benchmark、run outputs、paper source、release package 均能从一个索引定位。
- [ ] [stai-repro][P1] 校验 release package 与当前 manuscript 是否一致。完成定义：`artifacts/release_packages/stai2026/` 中 PDF/zip 与当前主稿、图表、参考文献版本匹配。
- [ ] [stai-repro][P1] 保留文本完整性检查。完成定义：`python tools/research/stai/check_stai_text_integrity.py --max-rows 1` 通过。

## P2：扩展实验评估

- [ ] [stai-experiments][P2] 评估是否补跑 v0.3 100q full ablation。完成定义：给出是否补跑 no_gate、no_audit、no_repair 的决策和时间成本。
- [ ] [stai-experiments][P2] 评估是否扩展 safety stress 到 multi-turn stress prompts。完成定义：形成设计说明或明确暂不扩展。
- [ ] [stai-experiments][P2] 评估 retrieval-only 与 retrieval_plus_gold 对比是否需要进入正文或补充材料。完成定义：区分检索失败和 workflow gate 失败的叙事边界。
- [ ] [stai-experiments][P2] 评估小规模 external runner/coach spot-check。完成定义：如果执行，必须先定义标注流程和不能声称专家验证的边界。

## P2：投稿材料

- [ ] [stai-submission][P2] 准备 final PDF。完成定义：页数、匿名性、引用、图表和模板检查通过。
- [ ] [stai-submission][P2] 准备 anonymized source zip。完成定义：不包含本地绝对路径、无关工程文件或隐私材料。
- [ ] [stai-submission][P2] 准备 abstract 和 keywords。完成定义：与最终标题、贡献边界和 workshop 主题一致。
- [ ] [stai-submission][P2] 准备 data/code availability statement。完成定义：复现材料位置和不可公开内容边界清楚。
- [ ] [stai-submission][P2] 准备 ethics、conflict of interest、funding、AI usage disclosure。完成定义：符合目标 venue 要求，不扩大系统安全性声明。
- [ ] [stai-submission][P2] 准备投稿前自查表。完成定义：覆盖 claim boundary、citation integrity、template compliance、artifact reproducibility。

## Done / Archive

- STAI 历史分析记录：`research/stai2026/analysis/`
- STAI benchmark：`research/stai2026/benchmark/`
- STAI manuscript：`research/stai2026/manuscript/`
- STAI run artifacts：`artifacts/research_runs/stai2026/`
- STAI release packages：`artifacts/release_packages/stai2026/`
