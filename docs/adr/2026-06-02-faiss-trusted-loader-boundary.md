# ADR 2026-06-02: FAISS Trusted Loader Boundary

## Status

Accepted

## Context

本项目运行时会从本地向量库目录加载 FAISS 索引，而 `FAISS.load_local(..., allow_dangerous_deserialization=True)` 本身就带有反序列化风险。

2026-06-02 审计明确要求：

- 运行时不能从任意外部目录反序列化索引
- basename 看起来像 `v2` 也不等于可信目录
- trusted loader 必须收口到统一路径判断

当前实现位于 `apps/backend/src/marathon_qa_assistant/services/vector_store.py`。

## Decision

1. 只允许配置中的受信向量目录进入 FAISS 反序列化路径。
2. `_is_trusted_faiss_dir()` 以绝对路径比对受信目录，而不是只看目录名。
3. `_load_faiss_store()` 作为统一 trusted loader 入口：
   - 非受信目录：直接拒绝
   - 受信目录：允许 `load_local`
   - 常规加载失败：才允许进入文件级内存反序列化兜底
4. 外部目录即使包含 `chunks.jsonl` 和 `faiss_db`，也只能按非 FAISS 运行时降级处理，不能做危险反序列化。

## Consequences

### Positive

- 避免运行时误加载任意外部或历史索引目录中的 pickle 内容。
- `v2` runtime、legacy compatibility、trusted loader 三者边界更清晰。
- 安全测试可以稳定验证“拒绝未受信目录”这一行为。

### Negative

- 临时调试外部索引时，不能直接复用生产运行时加载函数。
- 需要显式区分“构建索引工具”和“运行时加载索引”。

## Non-Goals

- 不在本 ADR 中设计通用远程向量库服务。
- 不把“可构建索引”误写成“可进入运行时 trusted set”。

## Verification

相关契约由以下测试覆盖：

- `tests/test_vector_kb_runtime_contract.py`
- `tests/test_security_guards.py`
