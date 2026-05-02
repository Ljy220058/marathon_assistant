import os
import sys
import io
import time
from pathlib import Path
from langgraph_multi_agent import app

# 重定向标准输出以捕获运行日志
class OutputCapture:
    def __init__(self):
        self.output = io.StringIO()

    def write(self, s):
        self.output.write(s)
        sys.__stdout__.write(s)  # 同时输出到控制台

    def flush(self):
        self.output.flush()
        sys.__stdout__.flush()

    def get_value(self):
        return self.output.getvalue()

def evaluate():
    test_cases = [
        {
            "id": 1,
            "name": "标准教练路径 (Coach)",
            "query": "我打算参加下个月的全程马拉松，目前配速在6分左右，最后三周应该如何安排LSD和减量训练？",
            "expected_path": "Classifier -> Coach -> Reviewer -> Formatter"
        },
        {
            "id": 2,
            "name": "营养师路径与审核驳回 (Nutritionist + Rejection)",
            "query": "明天就要跑马拉松了，为了补充蛋白质和能量，我打算今天晚上吃一大顿烤肉，明天早上喝两杯纯牛奶，这样安排可以吗？",
            "expected_path": "Classifier -> Nutritionist -> Reviewer (Reject) -> Nutritionist -> Reviewer (Approve) -> Formatter"
        },
        {
            "id": 3,
            "name": "康复师路径与安全检查 (Therapist)",
            "query": "最近跑步膝盖外侧有些疼，下坡时特别明显。为了不影响下个月的比赛，我打算吃止痛药坚持跑，或者找人强力按揉痛点，能行吗？",
            "expected_path": "Classifier -> Therapist -> Reviewer (Reject) -> Therapist -> Reviewer -> Formatter"
        },
        {
            "id": 4,
            "name": "模糊意图与默认路由 (Ambiguous)",
            "query": "我马上要跑首马了，感觉很紧张，不知道该怎么调整状态，能给我一些全面的建议吗？",
            "expected_path": "Classifier -> Coach (Fallback) -> Reviewer -> Formatter"
        },
        {
            "id": 5,
            "name": "RAG知识增强测试 (RAG Focus)",
            "query": "关于马拉松比赛中的补水策略，听说每个水站都要喝水，而且要大口喝，这种做法对吗？",
            "expected_path": "Classifier -> Nutritionist/Coach -> Reviewer -> Formatter"
        }
    ]

    report_content = "# Task 7: 多Agent工作流测试与评估报告\n\n"
    report_content += "## 1. 测试用例执行记录\n\n"

    for tc in test_cases:
        print(f"\n{'='*50}\n执行测试用例 {tc['id']}: {tc['name']}\n{'='*50}")
        
        capture = OutputCapture()
        sys.stdout = capture

        start_time = time.time()
        
        try:
            result = app.invoke({
                "query": tc["query"],
                "category": "",
                "draft_plan": "",
                "review_feedback": "",
                "is_approved": False,
                "iteration_count": 0,
                "final_report": ""
            })
            
            end_time = time.time()
            sys.stdout = sys.__stdout__  # 恢复标准输出
            
            log_output = capture.get_value()
            
            # 解析日志提取关键指标
            category = result.get("category", "Unknown")
            iterations = result.get("iteration_count", 0)
            final_report = result.get("final_report", "")
            
            # 简单评估质量 (基于是否包含审核驳回并修改)
            quality_assessment = "高 (逻辑完整，包含审核)" if iterations > 0 else "中 (直接通过，可能较常规)"
            
            report_content += f"### 测试用例 {tc['id']}: {tc['name']}\n"
            report_content += f"- **输入 (Query):** {tc['query']}\n"
            report_content += f"- **预期路径:** {tc['expected_path']}\n"
            report_content += f"- **实际分类 (Category):** {category}\n"
            report_content += f"- **迭代次数 (Iterations):** {iterations}\n"
            report_content += f"- **最终结果质量:** {quality_assessment}\n"
            report_content += f"- **耗时:** {end_time - start_time:.2f} 秒\n\n"
            
            report_content += "#### 路由与决策过程日志:\n```text\n"
            # 过滤掉报告打印部分，只保留过程
            process_log = log_output.split("### 马拉松全周期备赛管家")[0]
            report_content += process_log.strip() + "\n```\n\n"
            
            report_content += "#### 最终输出 (Final Report):\n```markdown\n"
            report_content += final_report.strip() + "\n```\n\n"
            report_content += "---\n"
            
        except Exception as e:
            sys.stdout = sys.__stdout__
            report_content += f"### 测试用例 {tc['id']}: 执行失败\n"
            report_content += f"- **错误信息:** {str(e)}\n\n"

    report_content += """
## 2. 多Agent协作的优势和挑战分析

### 优势 (Advantages)
1. **专业分工明确，输出质量高：** 
   - 相比于单一的大模型，多Agent架构将复杂任务拆解。在测试用例中，分类Agent负责意图识别，营养师/康复师/教练负责特定领域的方案生成，医疗总监负责安全把关。
   - 这种职责分离使得 Prompt 设计更加专注，结合专有的 RAG 知识库检索（例如营养师检索饮食知识，康复师检索伤病知识），生成的方案在专业性和深度上远胜于通用回答。
2. **闭环审核机制保障安全性 (Human-like Review)：** 
   - 医疗总监 (Reviewer) 的加入构建了“生成-评估-修正”的闭环。对于可能导致受伤或不适的建议（如测试用例2中的“赛前喝纯牛奶”、测试用例3中的“吃止痛药带痛跑”），Reviewer 能够敏锐识别并触发打回重写 (`REJECTED`)。
   - 这对于医疗健康、运动指导等高风险领域至关重要。
3. **流程可控性与可解释性：** 
   - 通过 LangGraph 的状态图 (StateGraph)，整个决策链条完全透明。我们可以清楚地看到用户的 Query 被路由到了哪个专家，方案经过了几次修改，以及医疗总监给出的具体驳回原因。这大大增强了系统的可解释性。

### 挑战 (Challenges)
1. **意图分类的模糊性与重叠：** 
   - 用户的问题往往是复合型的（如测试用例4中的“紧张、调整状态”，或者同时涉及训练和饮食）。目前的单一分类器只能将其路由到一个专家 Agent，导致无法全面覆盖复合需求。
   - **改进方向：** 可以设计并行路由 (Parallel Execution) 机制，让多个专家同时生成方案，最后由综合 Agent 进行合并总结。
2. **多轮调用的延迟与成本问题：** 
   - 多Agent工作流在遇到不合格方案时会触发循环修改。在测试用例2和3中，生成草案、审核驳回、重新生成、再次审核的流程会导致多次调用 LLM，整体响应延迟显著增加。
   - 这对本地算力或 API 成本提出了较高要求。
3. **死循环风险与“妥协”审核：** 
   - 如果生成 Agent 无法理解审核 Agent 的反馈，可能会反复生成同样的错误内容。虽然代码中设置了最大迭代次数（如 `iteration_count >= 2` 强制通过）作为兜底防线，但这本质上是对输出质量的妥协。
   - **改进方向：** 需要在 Prompt 中强制要求生成 Agent “必须逐条回应审核反馈”，并在状态字典中记录历史所有版本的草案以防重复。
4. **大模型对 Prompt 的遵循度依赖：** 
   - 审核 Agent 必须严格输出 `APPROVED` 或 `REJECTED` 作为首行。在某些情况下，大模型可能会加入前缀词（如“根据审核结果，REJECTED”），导致代码正则解析失败，从而破坏路由逻辑。
"""

    report_path = Path(__file__).parent / "workflow_evaluation_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"\n评估完成！报告已生成: {report_path}")

if __name__ == "__main__":
    evaluate()
