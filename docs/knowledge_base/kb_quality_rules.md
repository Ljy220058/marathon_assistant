# 知识库质量规则

## 收录规则

1. 优先官方期刊、PMC、arXiv、出版社开放页、学会/组织官网和高校机构库。
2. 不收 ResearchGate、Scribd、网盘、随机镜像站或来源不明 PDF。
3. PDF 下载后必须验证文件头为 `%PDF`，不能把 HTML 错误页当作论文。
4. 每条记录必须有 `id`、`group`、`title`、`authors`、`year`、`url`、`tags`、`purpose` 和 `download.status`。
5. 未下载全文的条目可以保留为 metadata，但不得进入本地 chunk 索引。

## RAG 使用规则

1. 文献层默认服务论文 RAG，不直接进入产品默认训练计划生成。
2. 训练核心字段，如主课、强度、训练量、恢复日安排，必须优先来自 HMP 协议或动作库。
3. 文献层可以补充解释、风险背景、营养建议、术语说明和论文 related work。
4. 健康、疼痛、损伤、补剂相关建议必须保守表达，并提示必要时咨询专业人士。
5. 后续 chunk 时要保留 `paper_id`、`group`、`source_url`、`local_pdf`、页码和段落定位。

## 后续清洗规则

- 对同一 DOI 或同一标题去重。
- 对扫描质量差或 OCR 噪声高的文献打 `needs_review`。
- 对可能包含产品无关内容的 chunk 打 `exclude_from_training_generation`。
- 对可转成规则的内容单独抽入 protocol/action/risk rule，不长期依赖自由文本检索。

