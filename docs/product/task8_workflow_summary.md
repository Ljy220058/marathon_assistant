# 任务8：工作流可视化与总结

## 1. 工作流可视化

为了直观展示马拉松全周期备赛管家多Agent协作系统的执行逻辑，我们通过 `LangGraph` 的 `draw_mermaid_png` 接口导出了工作流的状态图。

- **可视化图片已生成**: [workflow_graph.png](file:///c:/Users/26318/Documents/trae_projects/ollama_pro/实验五_罗锦源_202300203039_代码_v1/workflow_graph.png)
- **Mermaid 源码**：如果图片由于环境原因无法直接查看，可参考对应的 [workflow_graph.mermaid](file:///c:/Users/26318/Documents/trae_projects/ollama_pro/实验五_罗锦源_202300203039_代码_v1/workflow_graph.mermaid)。

该图表清晰地展示了：
1. **START** -> `classifier` (分类意图)
2. `classifier` 条件路由到 `coach` / `nutritionist` / `therapist`
3. 专家节点生成后，统一流转到 `reviewer` (医疗总监)
4. `reviewer` 进行评估，通过则进入 `formatter` 并结束，驳回则返回对应的专家节点重新生成。

---

## 2. Agent 角色定义与系统提示词整理

在本项目中，我们共设计了 5 个核心 Agent 和 1 个格式化 Agent。以下是它们的角色定义与系统提示词 (System Prompt) 汇总：

### 2.1 意图识别：分类Agent (`classifier_agent`)
- **角色定位**：作为系统的入口，负责分析用户的自然语言输入，并将其准确路由到最匹配的领域专家。
- **系统提示词**：
  ```text
  请分析以下跑者的问题，将其分类到以下三个类别之一，只输出类别英文名称：
  - coach: 涉及跑步训练计划、配速、跑量等
  - nutritionist: 涉及饮食、补剂、赛前补碳等
  - therapist: 涉及疼痛、伤病、赛后恢复等
  
  跑者问题：{query}
  类别：
  ```

### 2.2 训练指导：主教练Agent (`coach_agent`)
- **角色定位**：负责制定马拉松训练计划、LSD（长距离慢跑）安排及配速建议。
- **系统提示词**：
  ```text
  你是专业的马拉松主教练。请根据以下参考知识和跑者的问题，提供专业、科学的训练指导。
  如果存在之前的审核反馈，请务必根据反馈修改方案。

  【参考知识】：{context}
  【跑者问题】：{query}
  【审核反馈（如有）】：{feedback}

  请直接输出你的训练方案，保持专业和严谨：
  ```

### 2.3 饮食规划：营养师Agent (`nutritionist_agent`)
- **角色定位**：负责赛前补碳、比赛日补给及日常饮食指导。
- **系统提示词**：
  ```text
  你是专业的马拉松运动营养师。请根据以下参考知识和跑者的问题，提供专业、科学的饮食和补给指导。
  如果存在之前的审核反馈，请务必根据反馈修改方案。

  【参考知识】：{context}
  【跑者问题】：{query}
  【审核反馈（如有）】：{feedback}

  请直接输出你的饮食补给方案，保持专业和严谨：
  ```

### 2.4 伤病防范：康复师Agent (`therapist_agent`)
- **角色定位**：针对跑者的伤病（如膝盖疼痛）、拉伸及赛后恢复提供医学视角的建议。
- **系统提示词**：
  ```text
  你是专业的马拉松运动康复师。请根据以下参考知识和跑者的问题，提供专业、科学的康复和防伤指导。
  如果存在之前的审核反馈，请务必根据反馈修改方案。

  【参考知识】：{context}
  【跑者问题】：{query}
  【审核反馈（如有）】：{feedback}

  请直接输出你的康复指导方案，保持专业和严谨：
  ```

### 2.5 闭环守门人：医疗总监Agent (`reviewer_agent`)
- **角色定位**：负责对专家草案进行严格审查，拦截违背运动医学常识和存在安全隐患的建议。
- **系统提示词**：
  ```text
  你是马拉松团队的医疗总监与总审核员。请基于以下参考知识，严格审查专业Agent给出的方案草案。
  重点关注：是否有安全隐患、是否违背运动医学常识（例如：赛前喝牛奶导致肠胃不适、LSD配速过快导致力竭、受伤期间带痛坚持或暴力按揉等）。

  【参考知识】：{context}
  【跑者原始问题】：{query}
  【待审核方案】：{draft}

  请按以下格式严格输出：
  第一行必须是：APPROVED 或 REJECTED
  从第二行开始：给出具体的审核意见或修改建议（如果 REJECTED，指出哪里有危险并要求修改；如果 APPROVED，给出肯定评价）。
  ```

---

## 3. 多Agent协作的设计要点与改进方向

### 3.1 协作设计要点 (Design Key Points)
基于本项目的实践，构建高效可靠的多 Agent 系统需把握以下几个核心要点：
1. **关注点分离 (Separation of Concerns)**：
   将“理解意图”、“检索知识”、“生成草案”和“安全审核”解耦为独立的 Agent 节点。每个 Agent 的 Prompt 职责单一，这极大地降低了单一 LLM 发生幻觉的概率。
2. **基于图的状态流转 (Stateful Routing)**：
   利用 LangGraph 的 `TypedDict` (如 `PrepState`) 维护全局状态。各个 Agent 只需读取自己关心的字段（如 `query` 和 `review_feedback`），并更新自己的产出（如 `draft_plan`），使得信息传递透明且可追溯。
3. **“生成-对抗-修正”的闭环机制 (Actor-Critic Loop)**：
   引入 Reviewer 角色是高要求场景（如医疗、运动指导）的刚需。它模拟了人类审查机制 (Human-in-the-loop 的自动化延伸)，能拦截诸如“赛前大量吃烤肉”或“吃止痛药坚持跑”的危险言论。
4. **领域专属的 RAG 动态注入**：
   在进入专家节点和审核节点时，分别针对各自领域的关键词（如营养师追加“碳水、补给”，康复师追加“疼痛、恢复”）进行 TF-IDF 检索，这比全局统一检索更能保证上下文的精准度。

### 3.2 基于本项目的改进方向 (Future Improvements)
尽管当前系统能够运行，但暴露出了一些典型的挑战，未来可从以下方面改进：

1. **引入并行路由 (Parallel Execution)**：
   - **痛点**：目前分类器只能选择一条路线（如被归类为 Coach，就无法获得 Nutritionist 的建议）。
   - **改进**：修改 `classifier` 节点，使其能够输出多意图标签（如 `["coach", "nutritionist"]`）。LangGraph 支持条件分支的分叉 (fan-out)，让教练和营养师**并行**生成草案，最后由合并节点 (Merger) 或 Reviewer 整合为一份全面的报告。
2. **结构化输出约束 (Structured Output Framework)**：
   - **痛点**：目前严重依赖大模型输出 `APPROVED` 或 `REJECTED` 字符串，且必须在第一行。若模型啰嗦（如“根据您的要求，结果是 REJECTED”），则正则或字符串匹配会失效，破坏路由逻辑。
   - **改进**：结合 LangChain 的 `with_structured_output` 配合 Pydantic，强制 LLM 返回 JSON 格式（如 `{"decision": "REJECTED", "feedback": "..."}`），保证程序解析的 100% 稳定性。
3. **历史草案的追踪与记忆 (Draft Versioning)**：
   - **痛点**：目前的 `draft_plan` 字段在每次迭代时被直接覆盖，Reviewer 看不到之前的版本，容易造成“反复修改同一错误”的死循环。
   - **改进**：在 State 中将 `draft_plan` 修改为 `draft_history: list[str]`。每次修改都 appending 到列表中，Prompt 中附带“你上一次的回答是... 审核意见是... 请不要再犯同样的错误”，从而提高修正成功率。
4. **多级/分层知识库检索 (Hierarchical RAG)**：
   - **痛点**：目前所有的专家都从同一个全局 `chunks.jsonl` 中检索。
   - **改进**：预先将知识库分库（如 `kb_coach`, `kb_medical`）。通过分类器的意图，直接定向到对应的专属向量库中检索，以进一步降低无关文本对大模型注意力的干扰。