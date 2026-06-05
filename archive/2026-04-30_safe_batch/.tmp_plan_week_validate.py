from marathon_qa_assistant.services.knowledge_graph import plan_week_drafts, graph_engine

week = [
    {"day": "周一", "type": "节奏跑"},
    {"day": "周二", "type": "摄氧量"},
    {"day": "周三", "type": "轻松跑"},
    {"day": "周四", "type": "无氧阈"},
    {"day": "周五", "type": "长距离"},
    {"day": "周六", "type": "长距离"},
    {"day": "周日", "type": "重复跑"},
]
profile = {
    "weekly_mileage": 60,
    "max_session_minutes": 120,
    "terrain_preference": "跑道",
    "experience_level": "进阶",
}
result = plan_week_drafts(week, profile, graph_engine)
summary = [(item["day"], item["requested_type"], item["type"], item["status"]) for item in result]
print(summary)
quality_count = sum(1 for item in result if item["type"] in {"节奏跑", "阈值节奏跑", "无氧阈", "摄氧量", "高强度间歇", "重复跑", "极限间歇"})
assert quality_count <= 2, summary
for idx in range(1, len(result)):
    prev_type = result[idx - 1]["type"]
    curr_type = result[idx]["type"]
    prev_quality = prev_type in {"节奏跑", "阈值节奏跑", "无氧阈", "摄氧量", "高强度间歇", "重复跑", "极限间歇"}
    curr_quality = curr_type in {"节奏跑", "阈值节奏跑", "无氧阈", "摄氧量", "高强度间歇", "重复跑", "极限间歇"}
    assert not (prev_quality and curr_quality), summary
long_runs = [item for item in result if "长距离" in item["type"]]
assert len(long_runs) <= 1, summary
print("PLAN_WEEK_DRAFTS_OK")
