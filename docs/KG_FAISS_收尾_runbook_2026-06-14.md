# 马拉松助手 — KG/FAISS 收尾 Runbook（阶段 B/C/D）

> 生成：2026-06-14 · 适用于本地有 Ollama + conda `torch2.5.1` 的环境
> 沙箱无 Ollama/torch，以下命令必须在你本地跑。每步都给了**验证命令**和**预期结果**。

---

## 前置检查（每次开跑前）

```bash
# 1. Ollama 在跑且模型已拉
ollama list | grep bge-m3        # 应看到 bge-m3:latest
ollama list | grep qwen2.5       # KG 抽取需要（阶段D）

# 2. conda 环境
conda activate torch2.5.1
python -c "import torch, faiss, langchain_ollama; print('deps OK')"

# 3. 进项目根
cd <项目根>/马拉松助手
```

如果 `bge-m3` 没拉：`ollama pull bge-m3:latest`

---

## 阶段 B — FAISS 重建收尾（必做，是阶段 C 融合的前提）

**为什么必须做**：5 个分片的 `chunks.jsonl`（06-13 16:25）都比 `faiss_db/index.faiss`（16:14–16:17）新，新增的 curated chunk 尚未进 FAISS。KG 融合靠 `chunk_id` 碰撞——图谱边引用的 chunk 必须能被向量检索到，否则只能退化成 graph_hint。

### B-1. 重建 5 个 sharded 分片

```bash
bash tools/kb/rebuild_faiss.sh training_protocol nutrition injury_safety medical_safety sport_psychology
```

**预期**：每个分片打印 `✓ 重建完成，耗时 Xs，向量数 N`，最后 `重建完成: 5/5 成功`。

**验证（重建后）**：

```bash
# chunks 行数应与 FAISS 向量数一致（基准值）
for s in training_protocol nutrition injury_safety medical_safety sport_psychology; do
  echo -n "$s: chunks=$(wc -l < data/vector_kb/v2_sharded/$s/chunks.jsonl)  "
  python -c "
import json,sys
from pathlib import Path
# 用 langchain 读 FAISS ntotal
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
emb = OllamaEmbeddings(model='bge-m3:latest')
db = FAISS.load_local('data/vector_kb/v2_sharded/$s/faiss_db', emb, allow_dangerous_deserialization=True)
print('faiss_ntotal=', db.index.ntotal)
"
done
```

基准（chunks 数，FAISS ntotal 应等于或接近，差异仅来自空 text 过滤）：

| 分片 | chunks |
|------|--------|
| training_protocol | 6007 |
| nutrition | 4757 |
| injury_safety | 3698 |
| medical_safety | 690 |
| sport_psychology | 501 |

### B-2. v2 主库 4-向量缺口（兜底库，优先级低）

v2 是 FALLBACK 库（生产用 v2_sharded）。它有 4 个 chunk 因 NaN/Inf 嵌入失败未进 FAISS（21979/21983）。仅影响兜底场景的向量召回，BM25 仍可命中。

> ⚠️ `rebuild_faiss.sh` 当前**只支持 sharded 分片**，不接受 v2 主库目录。v2 主库重建需走 `vector_store.py`：

```bash
# 对 v2 现有 chunks.jsonl 重嵌入（不重新抓 PDF）
PYTHONPATH=apps/backend/src python -m marathon_qa_assistant.services.vector_store \
  --mode build --vector-dir data/vector_kb/v2 --output-dir data/vector_kb/v2
```

**验证**：重建后 `faiss_vector_count` 应 = 21983（缺口补齐）。然后更新 `data/vector_kb/v2/index_meta.json` 的 `faiss_gap_count` 为 0、移除 `pending_actions`。

> 若不急于修兜底库，B-2 可跳过，不阻塞阶段 C。

---

## 阶段 C — 验证 KG 真正进入检索（eval）

**已完成的沙箱逻辑验证**（无需你重跑）：
- `build_ranked_evidence` 三态融合逻辑审查通过（fusion 升级 / graph_hint 降级 / hard_constraint→decision_gate；冲突 surface 不强融）。
- `search_graph` 2-hop BFS 在 458 节点图上有效（protein/recovery/vo2max/pain/taper/injury 均命中子图）。
- 284 条 auto_extracted 边 100% 带 chunk_id，融合去重键齐备。

**需要你本地跑的部分**：live RAG eval，对比有/无 KG 的召回与引用质量（依赖 B 完成）。

```bash
# live RAG vs base 对比 eval
PYTHONPATH=apps/backend/src python scripts/run_live_rag_vs_base_eval.py
# 结果写入 data/knowledge/governance/live_rag_vs_base_eval_summary.json
```

**验证关注点**（看 summary json）：
- 启用 KG 融合的 query，`kind="fusion"` 证据数 > 0
- 融合证据的 `hybrid_score` 应高于纯 vector（fusion_bonus +0.1 生效）
- 引用质量（citation precision）有/无 KG 的差值——这是 KG 是否"真有用"的判据

> ⚠️ 操作纪律：验证图谱时**不要实例化 `GraphEngine`**。它 `__init__` 会触发 `save_graph()`，可能用注册表兜底图（44 节点）覆盖磁盘 458 节点完整图。只读验证请直接 `json.load('data/vector_kb/v2/knowledge_graph.json')`。
> 若不慎覆盖，恢复：重置候选 `merge_status: merged→pending` + 重跑 `python scripts/merge_knowledge_graph_candidates.py`，稳定恢复 458/348。

---

## 阶段 D — 扩大 KG 覆盖（可选，建议 C 验证有效后再投入）

当前 458 节点来自 5 分片的离线抽取。扩大覆盖的流水线（候选+审核模式，已审查 `_auto_approve` 门控安全）：

```bash
# 1. 抽取更多候选（需 Ollama + qwen2.5）。--limit 控制每分片抽取 chunk 数
PYTHONPATH=apps/backend/src python scripts/build_knowledge_graph_candidates.py \
  --shards training_protocol nutrition injury_safety medical_safety sport_psychology \
  --limit 400
# 产出追加到 data/knowledge/governance/knowledge_graph_candidates.jsonl

# 2. 合并已审核候选进主图
python scripts/merge_knowledge_graph_candidates.py
# 产出 knowledge_graph_build_report.json
```

**`_auto_approve` 门控**（自动拒绝以下候选，记入 quarantine）：
- `chunk_not_in_v2_sharded`：引用的 chunk 不存在
- `head_not_traceable` / `tail_not_traceable`：实体在源文本中找不到（防 LLM 幻觉）
- `relation_not_in_whitelist`：关系类型不在 ALLOWED_RELATIONS
- `low_confidence`：置信度 < 0.8
- `prescription_permission_elevated`：源 chunk 是处方级（图谱只承载解释关系，不碰处方权限）

**验证**：build_report 的 `nodes_total` 增长，`quality_issues` 为空。隔离文件 `kg_candidates_quarantine.jsonl` 记录被拒候选可人工复审。

**进阶优化点**（代码已有基础，可按需增强）：
- 关系规范化：`_normalize_relation`（knowledge_graph.py）已接入
- 实体消歧：扩充 `CANONICAL_ENTITY_MAP` 合并同义实体（如 "VO2max" / "maximal oxygen uptake"）

---

## 阶段 A 已完成（沙箱内，无需你操作）

KG 持久化三处加固已落地并验证（`knowledge_graph.py`）：
- `save_graph` 原子写入（tempfile + fsync + os.replace），中途被杀不留半截 JSON
- `load_graph` fail-loud：解析失败隔离损坏文件 + 保留注册表兜底，不静默清空
- `langchain_ollama` / `langchain_core` 裸 import 加 ImportError stub 兜底

---

## 一次性全流程（B→C→D，复制即用）

```bash
conda activate torch2.5.1
cd <项目根>/马拉松助手
ollama list | grep -E "bge-m3|qwen2.5"          # 前置检查

# 阶段 B
bash tools/kb/rebuild_faiss.sh training_protocol nutrition injury_safety medical_safety sport_psychology

# 阶段 C
PYTHONPATH=apps/backend/src python scripts/run_live_rag_vs_base_eval.py

# 阶段 D（确认 C 有效后）
PYTHONPATH=apps/backend/src python scripts/build_knowledge_graph_candidates.py --limit 400
python scripts/merge_knowledge_graph_candidates.py
```

跑完把各步输出/summary json 贴回来，我接着验证一致性。
