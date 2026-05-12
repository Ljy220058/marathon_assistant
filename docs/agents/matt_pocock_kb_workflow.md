# Matt Pocock Style KB Workflow

## Principle

每次知识库工作都拆成一个小而可验收的 implementation slice：先定义契约，再补素材或规则，最后验证 manifest 和边界。

## Slice Template

```markdown
## Title

### Problem

### Contract

- input:
- output:
- forbidden behavior:

### Implementation

- files:
- steps:

### Verification

- command:
- expected:
```

## 当前推荐顺序

1. 文献层分组和 source registry。
2. evidence item schema。
3. 独立 literature index。
4. 从文献抽取 protocol/risk/nutrition rules。
5. 论文评测包和 ablation traces。

## Guardrail

文献 RAG 永远不能绕过 HMP 协议层和动作库层。任何可执行训练建议都必须先转成结构化规则，再进入产品生成链路。

