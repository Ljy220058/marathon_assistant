"""流式查询 SSE 端点的核心逻辑测试（节点映射 + SSE 帧格式）。"""
import json
import sys
from pathlib import Path

root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from marathon_qa_assistant.apps.routers.query import _NODE_TO_STEP_ID, _sse_pack


def test_node_to_step_id_covers_all_key_nodes():
    """所有关键工作流节点都有前端进度步骤映射。"""
    key_nodes = [
        "security_gate", "router", "evidence_retriever", "crag_corrector",
        "conditioning_constraints", "supervisor", "planner", "executor",
        "coach", "adaptive_coach", "therapist", "nutritionist", "psychologist",
        "rule_checker", "critic_auditor", "missing_info_handler",
        "safety_out", "formatter", "guided_questions_generator",
    ]
    for node in key_nodes:
        assert node in _NODE_TO_STEP_ID, f"节点 {node} 缺少 stepId 映射"
    # 抽查映射正确性
    assert _NODE_TO_STEP_ID["security_gate"] == "connect"
    assert _NODE_TO_STEP_ID["evidence_retriever"] == "profile"
    assert _NODE_TO_STEP_ID["coach"] == "skeleton"
    assert _NODE_TO_STEP_ID["critic_auditor"] == "validate"
    assert _NODE_TO_STEP_ID["formatter"] == "evidence"


def test_sse_pack_frame_format():
    """SSE 帧格式：data: <json>\n\n，中文不转义。"""
    frame = _sse_pack({"type": "node", "node": "coach", "step": 1, "stepId": "skeleton"})
    assert frame.endswith("\n\n")
    assert frame.startswith("data: ")
    payload = json.loads(frame[len("data: "):].strip())
    assert payload["type"] == "node"
    assert payload["node"] == "coach"
    assert payload["stepId"] == "skeleton"


def test_sse_pack_preserves_chinese():
    """SSE 帧中文不转义（ensure_ascii=False），前端可直接显示。"""
    frame = _sse_pack({"type": "complete", "message": "完整工作流已返回。"})
    assert "完整工作流已返回。" in frame
    assert "\\u" not in frame  # 不含 unicode 转义序列（\\u 表示字面反斜杠+u）
