import hashlib
import logging
from typing import Any, Dict, List

try:
    from langchain_core.runnables import RunnableConfig
except ImportError:
    RunnableConfig = Any

from marathon_qa_assistant.core.physiology import calculate_hr_zones, calculate_pace_zones
from marathon_qa_assistant.core.profile_store import load_user_profile, save_user_profile
from marathon_qa_assistant.core.state_models import Evidence, IntegratedState
from marathon_qa_assistant.nodes.common import (
    ai_invoke,
    build_rag_sources,
    ensure_usage,
    get_context,
    get_graph_context,
    graph_engine,
    infer_entities,
)
from marathon_qa_assistant.nodes.routing import evaluate_plan_evidence

logger = logging.getLogger("workflow_engine")


EXTRACT_PROFILE_SYSTEM = """你是一个训练画像提取器。从用户的自然语言输入中提取以下字段（仅提取明确出现的信息，不要猜测）：

- goal: 目标赛事或目标成绩（如"半马69分""全马3小时"）
- experience_level: 经验水平（新手/中级/进阶/精英）
- weekly_mileage: 当前周跑量（数字，单位 km）
- lthr: 乳酸阈心率（数字）
- t_pace: 阈值配速（如"3:30/km"）
- vo2max: 最大摄氧量（数字）
- target_race_date: 比赛日期或距比赛还有多久（如"2个月后"）
- available_days: 可用训练日（如"周一,周三,周五"）
- max_session_minutes: 单次训练最长分钟数（数字）
- pace_preference: 配速偏好（用户指定的任何配速信息）
- terrain_preference: 场地偏好（田径场/公园/跑步机等）
- training_types: 用户要求的训练类型列表
- notes: 其他值得记录的信息

返回一个 JSON 对象，只包含从输入中提取到的字段。不要编造任何未提及的值。"""


def _normalize_profile(raw_profile: Dict[str, Any]) -> Dict[str, Any]:
    profile = load_user_profile()
    profile.update(raw_profile or {})

    lthr = int(profile.get("lthr", 0) or 0)
    if lthr > 40:
        profile["hr_zones"] = calculate_hr_zones(lthr)

    t_pace = str(profile.get("t_pace", "") or "").strip()
    if t_pace:
        profile["pace_zones"] = calculate_pace_zones(t_pace)

    if not isinstance(profile.get("long_term_memory"), list):
        profile["long_term_memory"] = []
    if not isinstance(profile.get("verified_facts"), dict):
        profile["verified_facts"] = {}
    return profile


FIELD_LABELS = {
    "goal": "目标赛事或目标成绩",
    "weekly_mileage": "当前周跑量",
    "vo2max": "最大摄氧量 VO₂max",
    "lthr": "乳酸阈心率 (LTHR)",
    "t_pace": "阈值配速 (T-Pace)",
    "available_days": "可用训练日",
    "max_session_minutes": "单次最长训练时长",
    "pace_preference": "配速偏好",
    "terrain_preference": "场地偏好",
    "experience_level": "经验水平",
    "target_race_date": "距比赛还有",
    "training_types": "课表类型偏好",
}

FIELD_HINTS = {
    "goal": "如：半马69分、全马3小时",
    "weekly_mileage": "如：80",
    "vo2max": "如：66",
    "lthr": "如：168 (bpm)",
    "t_pace": "如：3:50/km",
    "available_days": "如：周一,周三,周五,周日",
    "max_session_minutes": "如：90",
    "pace_preference": "如：强度课2:50-3:00/km，轻松跑4:30/km",
    "terrain_preference": "如：田径场,公园",
    "experience_level": "如：进阶",
    "target_race_date": "如：2个月后",
    "training_types": "如：有氧阈,无氧阈,节奏跑,重复跑,长距离",
}


PROFILE_OPTIONS = {
    "experience_level": {
        "label": "经验水平",
        "hint": "根据训练年限、比赛经验和配速选择 (每项有明确定义)",
        "type": "single",
        "options": [
            {"key": "新手", "display": "🌱 新手",
             "desc": "刚开始跑步 | 单次≤5km/≤30min | 配速≥7:00/km | 未参赛"},
            {"key": "初级", "display": "🌿 初级",
             "desc": "规律跑3-6个月 | 可跑5-10km | 配速6:00-7:00/km | 完成过1-2场5K/10K"},
            {"key": "中级", "display": "🌳 中级",
             "desc": "系统训练1年+ | 半马完赛 | 周跑量30-60km | 配速5:00-6:30/km"},
            {"key": "进阶", "display": "🏆 进阶",
             "desc": "系统训练2年+ | 全马完赛 | 周跑量60-100km | 配速4:00-5:30/km"},
            {"key": "精英", "display": "👑 精英",
             "desc": "竞技型跑者 | 全马 sub3 / 冲击资格 | 周跑量≥100km | 有成熟训练体系"},
        ],
    },
    "goal": {
        "label": "目标赛事 / 成绩",
        "hint": "选择比赛类型或自定义 (可多选后合并)",
        "type": "single_custom",
        "options": [
            {"key": "5K sub20", "display": "🏁 5K sub20", "desc": "5公里跑进 20 分钟"},
            {"key": "10K sub40", "display": "🏁 10K sub40", "desc": "10公里跑进 40 分钟"},
            {"key": "半马 sub90", "display": "🏅 半马 sub90", "desc": "半马跑进 1 小时 30 分"},
            {"key": "半马 sub80", "display": "🏅 半马 sub80", "desc": "半马跑进 1 小时 20 分"},
            {"key": "全马 sub330", "display": "🎖 全马 sub330", "desc": "全马跑进 3 小时 30 分"},
            {"key": "全马 sub300", "display": "🎖 全马 sub300", "desc": "全马跑进 3 小时 (破三)"},
            {"key": "全马 sub245", "display": "🎖 全马 sub245", "desc": "全马跑进 2 小时 45 分 (精英)"},
        ],
    },
    "target_race_date": {
        "label": "距比赛还有",
        "hint": "选择比赛倒计时",
        "type": "single",
        "options": [
            {"key": "1个月", "display": "📅 1个月", "desc": "4周内比赛，赛前调整期"},
            {"key": "2个月", "display": "📅 2个月", "desc": "8周，可完成一个完整训练周期"},
            {"key": "3个月", "display": "📅 3个月", "desc": "12周，经典马拉松备战周期"},
            {"key": "半年", "display": "📅 半年", "desc": "24周，两个完整周期"},
            {"key": "无比赛", "display": "🏃 无近期比赛", "desc": "以维持/提升能力为目标"},
        ],
    },
    "vo2max": {
        "label": "最大摄氧量 VO₂max",
        "hint": "如有手表测量值选最接近的，否则根据年龄估算",
        "type": "single_custom",
        "options": [
            {"key": "40", "display": "40", "desc": "一般人群水平"},
            {"key": "45", "display": "45", "desc": "规律跑者入门"},
            {"key": "50", "display": "50", "desc": "训练有素的业余跑者"},
            {"key": "55", "display": "55", "desc": "优秀业余跑者"},
            {"key": "60", "display": "60", "desc": "接近竞技水平"},
            {"key": "65", "display": "65", "desc": "竞技水平"},
            {"key": "70+", "display": "70+", "desc": "精英竞技水平"},
        ],
    },
    "weekly_mileage": {
        "label": "当前周跑量 (km)",
        "hint": "最近4周平均每周跑量",
        "type": "single_custom",
        "options": [
            {"key": "20", "display": "🏃 20 km/周", "desc": "入门跑者，每周2-3次"},
            {"key": "40", "display": "🏃 40 km/周", "desc": "规律跑者，每周3-4次"},
            {"key": "60", "display": "🏃 60 km/周", "desc": "半马训练量，每周4-5次"},
            {"key": "80", "display": "🏃 80 km/周", "desc": "全马训练量，每周5-6次"},
            {"key": "100", "display": "🏃 100 km/周", "desc": "进阶全马，每周6-7次"},
            {"key": "120+", "display": "🏃 120+ km/周", "desc": "精英选手训练量"},
        ],
    },
    "lthr": {
        "label": "乳酸阈心率 (LTHR)",
        "hint": "反映耐力水平的关键心率指标，用于划分九区心率",
        "type": "single_custom",
        "options": [
            {"key": "150", "display": "150 bpm", "desc": "较低强度阈值"},
            {"key": "160", "display": "160 bpm", "desc": "常规业余跑者"},
            {"key": "170", "display": "170 bpm", "desc": "训练有素跑者"},
            {"key": "180", "display": "180 bpm", "desc": "高心率型/精英跑者"},
        ],
    },
    "t_pace": {
        "label": "阈值配速 (T-Pace)",
        "hint": "你能维持 50-60 分钟的最快配速，用于划分九区配速",
        "type": "single_custom",
        "options": [
            {"key": "3:30/km", "display": "⚡ 3:30/km", "desc": "精英级阈值"},
            {"key": "4:00/km", "display": "⚡ 4:00/km", "desc": "进阶级阈值"},
            {"key": "4:30/km", "display": "🏃 4:30/km", "desc": "中级阈值"},
            {"key": "5:00/km", "display": "🏃 5:00/km", "desc": "初级阈值"},
            {"key": "5:30/km", "display": "🚶 5:30/km", "desc": "入门级阈值"},
        ],
    },
    "pace_preference": {
        "label": "配速偏好",
        "hint": "选择训练配速范围 (强度课配速 / 轻松跑配速)",
        "type": "single_custom",
        "options": [
            {"key": "4:00/km", "display": "⚡ 4:00/km", "desc": "强度课 ≈3:40-4:10 | 轻松跑 ≈4:30-5:00"},
            {"key": "4:30/km", "display": "⚡ 4:30/km", "desc": "强度课 ≈4:10-4:40 | 轻松跑 ≈5:00-5:30"},
            {"key": "5:00/km", "display": "🏃 5:00/km", "desc": "强度课 ≈4:40-5:10 | 轻松跑 ≈5:30-6:00"},
            {"key": "5:30/km", "display": "🏃 5:30/km", "desc": "强度课 ≈5:10-5:40 | 轻松跑 ≈6:00-6:30"},
            {"key": "6:00/km", "display": "🚶 6:00/km", "desc": "强度课 ≈5:40-6:10 | 轻松跑 ≈6:30-7:00"},
            {"key": "6:30/km+", "display": "🚶 6:30/km+", "desc": "强度课 ≈6:10-6:40 | 轻松跑 ≈7:00+"},
        ],
    },
    "available_days": {
        "label": "可用训练日",
        "hint": "点击切换选择 (可多选)，选完点 ✓确认",
        "type": "multi",
        "options": [
            {"key": "周一", "display": "周一"},
            {"key": "周二", "display": "周二"},
            {"key": "周三", "display": "周三"},
            {"key": "周四", "display": "周四"},
            {"key": "周五", "display": "周五"},
            {"key": "周六", "display": "周六"},
            {"key": "周日", "display": "周日"},
        ],
    },
    "max_session_minutes": {
        "label": "单次最长训练时长",
        "hint": "你一次训练能投入的最长时间",
        "type": "single",
        "options": [
            {"key": "30", "display": "⏱ 30 分钟", "desc": "适合短课、恢复跑"},
            {"key": "45", "display": "⏱ 45 分钟", "desc": "适合常规轻松跑"},
            {"key": "60", "display": "⏱ 60 分钟", "desc": "标准训练课"},
            {"key": "90", "display": "⏱ 90 分钟", "desc": "可容纳节奏跑+间歇"},
            {"key": "120", "display": "⏱ 120 分钟", "desc": "半马长距离训练"},
            {"key": "150+", "display": "⏱ 150+ 分钟", "desc": "全马长距离训练"},
        ],
    },
    "terrain_preference": {
        "label": "场地偏好",
        "hint": "点击切换选择 (可多选)，选完点 ✓确认",
        "type": "multi",
        "options": [
            {"key": "田径场", "display": "🏟 田径场", "desc": "适合速度课、间歇训练"},
            {"key": "公园", "display": "🌳 公园", "desc": "适合轻松跑、节奏跑"},
            {"key": "公路", "display": "🛣 公路", "desc": "适合长距离、马拉松模拟"},
            {"key": "跑步机", "display": "🏋 跑步机", "desc": "雨天/室内训练"},
            {"key": "山路", "display": "⛰ 山路", "desc": "适合力量耐力、爬升训练"},
        ],
    },
    "training_types": {
        "label": "课表类型偏好",
        "hint": "点击切换选择 (可多选)，选完点 ✓确认",
        "type": "multi",
        "options": [
            {"key": "轻松跑", "display": "🟢 轻松跑", "desc": "有氧基础，低强度"},
            {"key": "节奏跑", "display": "🔵 节奏跑", "desc": "乳酸阈训练，中高强度持续跑"},
            {"key": "间歇跑", "display": "🟠 间歇跑", "desc": "VO₂max 刺激，短距离快跑+休息"},
            {"key": "重复跑", "display": "🔴 重复跑", "desc": "无氧能力，极快配速+充分休息"},
            {"key": "长距离", "display": "🟣 长距离", "desc": "耐力基础，周末 LSD"},
            {"key": "法特莱克", "display": "🟡 法特莱克", "desc": "变速跑，自由切换快慢"},
            {"key": "坡度跑", "display": "⛰ 坡度跑", "desc": "上坡力量+下坡技巧"},
        ],
    },
    "notes": {
        "label": "补充说明",
        "hint": "其他需要教练知道的 (可跳过)",
        "type": "custom",
        "options": [],
    },
}

PROFILE_FIELD_ORDER = [
    "experience_level",
    "goal",
    "target_race_date",
    "vo2max",
    "weekly_mileage",
    "lthr",
    "t_pace",
    "available_days",
    "max_session_minutes",
    "terrain_preference",
    "training_types",
    "notes",
    "__confirm__",
]


def _next_field(current_field: str) -> str:
    """返回下一个字段名，若已到末尾返回 None"""
    try:
        idx = PROFILE_FIELD_ORDER.index(current_field)
        if idx + 1 < len(PROFILE_FIELD_ORDER):
            return PROFILE_FIELD_ORDER[idx + 1]
    except ValueError:
        pass
    return None


def _prev_field(current_field: str) -> str:
    """返回上一个字段名"""
    try:
        idx = PROFILE_FIELD_ORDER.index(current_field)
        if idx > 0:
            return PROFILE_FIELD_ORDER[idx - 1]
    except ValueError:
        pass
    return None


def profile_selections_to_save(selections: dict) -> dict:
    """将交互式填写的 selections 转为可保存的 profile 字典"""
    result = {}
    field_map = {
        "experience_level": "experience_level",
        "goal": "goal",
        "target_race_date": "target_race_date",
        "vo2max": "vo2max",
        "weekly_mileage": "weekly_mileage",
        "lthr": "lthr",
        "t_pace": "t_pace",
        "pace_preference": "pace_preference",
        "available_days": "available_days",
        "max_session_minutes": "max_session_minutes",
        "terrain_preference": "terrain_preference",
        "training_types": "training_types",
        "notes": "notes",
    }
    for form_key, profile_key in field_map.items():
        val = selections.get(form_key)
        if val is None:
            continue
        if isinstance(val, list):
            result[profile_key] = ",".join(val)
        else:
            result[profile_key] = str(val)
    return result

def _detect_missing_fields(state: IntegratedState, profile: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    intent = state.get("intent_type", "")
    query = (state.get("query", "") or "").lower()

    if intent != "plan":
        return missing

    has_goal = profile.get("goal") or profile.get("target_race")
    has_weekly = profile.get("weekly_mileage")
    has_vo2max = profile.get("vo2max")
    has_lthr = profile.get("lthr")
    has_pace = profile.get("t_pace") or profile.get("pace_preference")

    query_has_goal = any(kw in query for kw in ["半马", "全马", "10k", "5k", "马拉松", "比赛", "目标", "pb", "分钟", "小时"])
    query_has_pace = any(kw in query for kw in ["配速", "分", "/km"])

    if not has_goal:
        missing.append("goal")
    if not has_weekly:
        missing.append("weekly_mileage")
    if not has_vo2max:
        missing.append("vo2max")
    if not has_lthr:
        missing.append("lthr")
    if not has_pace:
        missing.append("t_pace")

    has_days = profile.get("available_days")
    if not has_days:
        missing.append("available_days")

    if missing and query_has_goal and query_has_pace:
        missing = []

    return missing


async def _extract_profile_from_query(query: str, config: RunnableConfig, current_usage: dict) -> dict:
    if not query or len(query) < 20:
        return {}
    try:
        result, _ = await ai_invoke(
            f"{EXTRACT_PROFILE_SYSTEM}\n\n用户输入：\n{query}\n\n仅返回 JSON 对象。",
            config,
            current_usage,
        )
        start = result.find("{")
        end = result.rfind("}") + 1
        if 0 <= start < end:
            import json
            return json.loads(result[start:end])
    except Exception:
        pass
    return {}


def build_ranked_evidence(
    query: str,
    vector_hits: List[Dict[str, Any]],
    graph_edges: List[Dict[str, Any]],
    entities: List[str],
    top_k: int = 5
) -> List[Evidence]:
    """聚合向量与图谱证据，去重合并并打分排序"""
    evidence_map: Dict[str, Evidence] = {}
    pre_sort_stats = {"vector": 0, "graph": 0, "fusion": 0}

    # 1. 处理向量证据
    for hit in vector_hits or []:
        chunk_id = hit.get("chunk_id", "")
        source = hit.get("source_file", "unknown")
        page = int(hit.get("page", 1) or 1)
        text = hit.get("text", "")
        score = float(hit.get("score", 0.0) or 0.0)

        # 构造 ID：优先用 chunk_id
        if chunk_id:
            eid = f"vec_{chunk_id}"
        else:
            stable_hash = hashlib.md5(f"{source}|{page}|{text[:120]}".encode("utf-8")).hexdigest()[:10]
            eid = f"vec_{stable_hash}"

        ev: Evidence = {
            "evidence_id": eid,
            "kind": "vector",
            "source_file": source,
            "page": page,
            "chunk_id": chunk_id,
            "snippet": text[:300],
            "text": text,
            "vector_score": score,
            "retrieval_score": score,
            "graph_confidence": 0.0,
            "entity_overlap": 0.0,
            "fusion_bonus": 0.0,
            "hybrid_score": 0.0,
            "citation_label": "",
            "trace": {
                "vector_hit": True,
                "vector_score": score,
                "graph_hit": False,
                "fusion_bonus": 0.0,
            },
        }
        # 以 chunk_id 为核心去重键
        key = chunk_id if chunk_id else f"{source}_{page}"
        evidence_map[key] = ev
        pre_sort_stats["vector"] += 1

    # 2. 处理图谱证据并融合
    for edge in graph_edges or []:
        g_ev_raw = graph_engine.map_edge_to_evidence(edge)
        chunk_id = g_ev_raw["chunk_id"]
        source = g_ev_raw["source_file"]
        page = g_ev_raw["page"]
        key = chunk_id if chunk_id else f"{source}_{page}"

        if key in evidence_map:
            # 融合逻辑
            existing = evidence_map[key]
            existing["kind"] = "fusion"
            existing["graph_confidence"] = g_ev_raw["graph_confidence"]
            existing["trace"]["graph_hit"] = True
            existing["trace"]["graph_relation"] = edge.get("relation", "")
            existing["trace"]["fusion_bonus"] = 0.1
            pre_sort_stats["fusion"] += 1
        else:
            evidence_map[key] = g_ev_raw
            pre_sort_stats["graph"] += 1

    # 3. 计算 entity_overlap 与 hybrid_score
    ranked_list: List[Evidence] = []
    for ev in evidence_map.values():
        # 计算实体重合度
        overlap_count = 0
        snippet_lower = ev["snippet"].lower()
        for ent in entities:
            if ent.lower() in snippet_lower:
                overlap_count += 1
        ev["entity_overlap"] = min(1.0, overlap_count / max(1, len(entities)))

        # Hybrid Score 公式: 向量分(0.4) + 图分(0.3) + 实体分(0.2) + 融合分(0.1)
        vector_score = float(ev.get("retrieval_score", 0.0) or 0.0)
        graph_conf = float(ev.get("graph_confidence", 0.0) or 0.0)
        v_part = vector_score * 0.4
        g_part = graph_conf * 0.3
        e_part = ev["entity_overlap"] * 0.2
        f_part = 0.1 if ev["kind"] == "fusion" else 0.0
        ev["vector_score"] = vector_score
        ev["fusion_bonus"] = f_part

        # 对无法回溯 source/chunk 的 graph-only 证据降权
        is_graph_only = ev["kind"] == "graph"
        has_trace_anchor = bool(ev.get("chunk_id")) or str(ev.get("source_file", "")).strip().lower() not in {"", "unknown"}
        penalty = 0.25 if (is_graph_only and not has_trace_anchor) else 0.0

        ev["hybrid_score"] = max(0.0, v_part + g_part + e_part + f_part - penalty)
        ev["trace"]["score_breakdown"] = {
            "vector_score": round(v_part, 3),
            "graph_confidence": round(g_part, 3),
            "entity_overlap": round(e_part, 3),
            "fusion_bonus": round(f_part, 3),
            "penalty": round(penalty, 3),
        }
        ev["trace"]["query"] = query[:80]
        ranked_list.append(ev)

    # 4. 排序与截断
    ranked_list.sort(key=lambda x: x["hybrid_score"], reverse=True)
    final_list = ranked_list[:top_k]

    # 5. 固定 Citation Label
    for idx, ev in enumerate(final_list, start=1):
        ev["citation_label"] = f"[{idx}]"

    logger.info(
        "[retrieval:evidence] pre_sort vector=%s graph=%s fusion=%s merged=%s top_k=%s",
        pre_sort_stats["vector"],
        pre_sort_stats["graph"],
        pre_sort_stats["fusion"],
        len(ranked_list),
        len(final_list),
    )
    for ev in final_list[:3]:
        logger.info(
            "[retrieval:evidence] top %s %s kind=%s hybrid=%.3f trace=%s",
            ev.get("citation_label", "[?]"),
            ev.get("evidence_id", ""),
            ev.get("kind", "unknown"),
            float(ev.get("hybrid_score", 0.0) or 0.0),
            ev.get("trace", {}),
        )

    return final_list


async def profiler_node(state: IntegratedState, config: RunnableConfig) -> dict:
    current_profile = _normalize_profile(state.get("user_profile", {}))

    intent = state.get("intent_type", "")
    query = state.get("query", "")
    extracted = {}
    if intent == "plan" and query:
        extracted = await _extract_profile_from_query(query, config, state.get("token_usage"))
        if extracted:
            current_profile.update(extracted)

    save_user_profile(current_profile)
    missing = _detect_missing_fields(state, current_profile)
    status = "画像已同步"
    if missing:
        status = "画像可用，但缺少处方关键指标"
    if extracted:
        status += f" (从对话提取 {len(extracted)} 个字段)"

    return {
        "user_profile": current_profile,
        "missing_fields": missing,
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": [f"[profiler] {status}"],
    }


async def entity_extraction_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del config
    query = state.get("query", "")
    entities = infer_entities(query, state.get("selected_entities"))

    hits = await get_context(query, top_k=6)  # 稍微多取一点以便后续融合排序
    if not hits and entities:
        hits = await get_context(" ".join(entities), top_k=6)

    rag_sources = build_rag_sources(hits)
    
    # 获取图谱上下文
    try:
        graph_res = graph_engine.search_graph(entities, max_hops=2)
        graph_edges = graph_res.get("edges", [])
        graph_context, mermaid_graph = get_graph_context(entities)
    except Exception as exc:
        logger.warning(f"Graph Search failed in extraction node: {exc}")
        graph_edges = []
        graph_context = ""
        mermaid_graph = "flowchart TD\n  Empty[Graph Error]"

    # 构建统一的 Ranked Evidence
    ranked_evidence = build_ranked_evidence(
        query=query,
        vector_hits=hits,
        graph_edges=graph_edges,
        entities=entities,
        top_k=5
    )

    evidence_gate = evaluate_plan_evidence(hits, query, state.get("intent_type", "qa"))

    logs = [f"[entity_extraction] 识别实体: {', '.join(entities)}"]
    if not hits:
        logs.append("[Evidence Gate] 知识库检索为空")
    elif evidence_gate.get("required") and not evidence_gate.get("has_plan_evidence", True):
        logs.append("[Evidence Gate] 命中内容不足以支撑计划型处方")
    else:
        logs.append(f"[Evidence Gate] 命中 {len(hits)} 个原始片段 -> 融合排序后保留 {len(ranked_evidence)} 个证据")

    if graph_context:
        logs.append(f"[graph_traversal] 已生成图谱关联路径 (命中 {len(graph_edges)} 条边)")
    else:
        logs.append("[graph_traversal] 未发现直接图谱路径")
    if ranked_evidence:
        top_trace = ", ".join(
            f"{ev.get('citation_label', '[?]')}:{ev.get('kind', 'unknown')}/{ev.get('hybrid_score', 0):.3f}"
            for ev in ranked_evidence[:3]
        )
        logs.append(f"[evidence_trace] top={top_trace}")

    return {
        "entities": entities,
        "selected_entities": entities,
        "gate_hits": hits,
        "rag_sources": rag_sources,
        "ranked_evidence": ranked_evidence,
        "graph_context": graph_context,
        "mermaid_graph": mermaid_graph,
        "token_usage": ensure_usage(state.get("token_usage")),
        "reasoning_log": logs,
    }


async def wiki_search_node(state: IntegratedState, config: RunnableConfig) -> dict:
    del state, config
    return {"wiki_context": "", "reasoning_log": ["[wiki_search] 当前保持 KB-only，本轮未启用外部知识"]}


TRAINING_PROFILE_FORM = """📋 **训练画像表单** — 请直接编辑并发送（替换 `_____` 为你的数据）

| 字段 | 你的数据 | 说明 |
|------|---------|------|
| 目标赛事/成绩 | _____ | 如：半马69分、全马3小时 |
| 当前最好成绩 | _____ | 如：半马70分 |
| VO₂max | _____ | 如：66 |
| 当前周跑量 (km) | _____ | 如：80 |
| 乳酸阈心率 (LTHR) | _____ | 如：168 |
| 阈值配速 (T-Pace) | _____ | 如：3:50/km |
| 可用训练日 | _____ | 如：周一,周三,周五,周日 |
| 单次最长训练 (分钟) | _____ | 如：90 |
| 配速偏好 | _____ | 如：强度课2:50-3:00/km，轻松跑4:30/km |
| 场地偏好 | _____ | 如：田径场,公园 |
| 经验水平 | _____ | 如：进阶 / 精英 |
| 距比赛还有 | _____ | 如：2个月 |
| 课表类型偏好 | _____ | 如：有氧阈,无氧阈,节奏跑,摄氧量,重复跑,长距离 |
| 其他说明 | _____ | 如：每天训练、135跑强度、周六长距离 |

> 填好后直接发送，我将据此生成你的专属周训练计划。"""
FORM_SENTINEL = "📋__TRAINING_PROFILE_FORM_FILLED__"


def _parse_profile_form(text: str) -> dict:
    import re
    result = {}
    field_map = {
        "目标赛事/成绩": "goal",
        "当前最好成绩": "current_pb",
        "VO₂max": "vo2max",
        "VO2max": "vo2max",
        "当前周跑量": "weekly_mileage",
        "乳酸阈心率": "lthr",
        "LTHR": "lthr",
        "阈值配速": "t_pace",
        "T-Pace": "t_pace",
        "可用训练日": "available_days",
        "单次最长训练": "max_session_minutes",
        "配速偏好": "pace_preference",
        "场地偏好": "terrain_preference",
        "经验水平": "experience_level",
        "距比赛还有": "target_race_date",
        "课表类型偏好": "training_types",
        "其他说明": "notes",
    }
    lines = text.strip().split("\n")
    for line in lines:
        line = line.strip().lstrip("|").strip()
        for label, key in field_map.items():
            if label in line:
                parts = line.split("|")
                if len(parts) >= 2:
                    value = parts[1].strip() if len(parts) > 1 else ""
                else:
                    value = line.split(label, 1)[-1].strip()
                if value and value != "_____" and value != "你的数据":
                    result[key] = value
                break
    return result if len(result) >= 3 else {}


async def missing_info_handler_node(state: IntegratedState, config: RunnableConfig) -> dict:
    intent = state.get("intent_type", "")

    if intent == "plan":
        missing = state.get("missing_fields", [])
        labels = [FIELD_LABELS.get(k, k) for k in missing]
        return {
            "final_report": "__FILL_FIELDS__",
            "missing_fields": missing,
            "reasoning_log": [f"[missing_info] 缺少画像字段: {', '.join(labels)}，已发送逐字段填写入口"],
            "token_usage": ensure_usage(state.get("token_usage")),
        }

    missing = state.get("missing_fields", [])
    rag_sources = state.get("rag_sources", [])
    query = state.get("query", "")
    entities = state.get("entities", [])
    category = state.get("category", "coach")

    if missing:
        prompt = (
            f"用户提问：「{query}」\n"
            f"当前缺失的画像指标：{', '.join(missing)}\n"
            f"请用友好的语气告诉用户需要补充这些指标才能给出更科学的训练处方，"
            f"并简要解释每个指标对训练计划的参考价值。控制在150字以内。"
        )
    elif not rag_sources:
        prompt = (
            f"用户提问：「{query}」\n"
            f"当前知识库中没有检索到相关证据。请生成2-3个具体的追问，"
            f"引导用户补充更详细的目标、周期或限制条件。控制在100字以内。"
        )
    else:
        available_entities = "、".join(entities[:3]) if entities else "无特定实体"
        prompt = (
            f"用户提问：「{query}」\n"
            f"已识别实体：{available_entities}\n"
            f"意图分类：{category}\n"
            f"当前证据不足以生成处方级建议。请生成2-3个有具体指向的追问，"
            f"帮助用户补充训练目标、当前能力、可用时间等关键信息。控制在120字以内。"
        )

    try:
        result, usage = await ai_invoke(prompt, config, state.get("token_usage"))
        content = f"## 需要更多信息\n{result}" if result else _static_fallback(missing, rag_sources)
        return {
            "final_report": content,
            "reasoning_log": ["[missing_info] 已通过 LLM 生成缺失信息引导"],
            "token_usage": usage,
        }
    except Exception:
        content = _static_fallback(missing, rag_sources)
        return {
            "final_report": content,
            "reasoning_log": ["[missing_info] 已生成缺失信息引导 (LLM 回退到静态模板)"],
            "token_usage": ensure_usage(state.get("token_usage")),
        }


def _static_fallback(missing: list, rag_sources: list) -> str:
    if missing:
        return (
            "## 需要补充用户画像\n"
            "为了给出更科学的训练处方，请补充以下信息：\n"
            + "\n".join(f"- {item}" for item in missing)
            + "\n\n直接回复这些指标即可，我会据此重新生成建议。"
        )
    elif not rag_sources:
        return (
            "## 证据不足\n"
            "当前本地知识库没有检索到足够证据，系统不会直接猜测处方级建议。\n\n"
            "你可以上传相关 PDF、训练指南、动作库或研究资料后再试。"
        )
    return "## 信息不足\n当前问题还缺少进一步上下文，请补充更具体的目标、周期或限制条件。"
