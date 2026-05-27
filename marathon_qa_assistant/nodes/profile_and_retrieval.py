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
    expand_entities_for_kg,
    get_context,
    get_graph_context,
    graph_engine,
    infer_entities,
)
from marathon_qa_assistant.nodes.routing import evaluate_plan_evidence

logger = logging.getLogger("workflow_engine")


EXTRACT_PROFILE_SYSTEM = (
    "你是专业跑步教练 AI 画像提取器。从用户自然语言中提取训练画像字段，"
    "遵循多步推理流程，内置跑圈领域知识、归一化规则和字段反推逻辑。\n\n"
    "══════════════════════════\n"
    "【跑圈黑话词典】\n\n"
    "识别以下术语并映射到对应字段：\n"
    "- 破三 / sub3：全马完赛时间 < 3:00:00 → goal: 全马3小时\n"
    "- BQ：波士顿马拉松报名资格 (Boston Qualifier) → goal: BQ达标，notes 中记录\n"
    "- 330：全马目标 3 小时 30 分钟 → goal: 全马3小时30分\n"
    "- sub130：半马目标 1 小时 30 分钟以内 → goal: 半马1小时30分\n"
    "- 兔子 / pacer：配速员 → notes 中记录角色\n"
    "- 撞墙：比赛中严重体力不支（通常 30-35 km）→ notes 中记录关注点\n"
    "- LSD：长距离慢跑 (Long Slow Distance) → training_types 中加入「长距离」\n"
    "- Tempo / 节奏跑：以乳酸阈值附近配速持续跑 → training_types 中加入「节奏跑」\n"
    "- 间歇：高强度间歇训练 → training_types 中加入「间歇跑」\n"
    "- 阈值跑：乳酸阈值跑 → training_types 中加入「无氧阈」\n"
    "- 法特莱克：变速跑游戏 (Fartlek) → training_types 中加入「法特莱克」\n"
    "- 配速跑：按目标比赛配速训练 → training_types 中加入「配速跑」\n"
    "- 轻松跑 / 恢复跑 / E 跑：低强度有氧跑 → training_types 中加入「轻松跑」\n"
    "- 渐加速 / Progressive：从慢到快逐渐提速 → training_types 中加入「渐加速跑」\n"
    "- 冲坡：专项上坡冲刺训练 → training_types 中加入「坡道训练」\n"
    "- 倒金字塔：间歇距离递减/递增组合（如 1200-1000-800-600-400）→ training_types 中加入，notes 记录结构\n"
    "- 亚索800 / Yasso 800：用 800m 间歇预测全马时间的训练 → training_types 中加入「亚索800」\n"
    "- 跑量：每周总跑步距离 → weekly_mileage\n"
    "- 跑休：跑步休息日 → available_days 反向推导休息日\n"
    "- 步频 / 步幅：每分钟步数 / 每步步长 → notes 中记录\n\n"
    "══════════════════════════\n"
    "【多步推理流程】\n\n"
    "Step 1 — 识别并提取原始字段：从文本中找出所有与训练相关的明确信息"
    "（目标赛事、当前跑量、配速、可用训练日、痛点等），记入对应字段。\n"
    "Step 2 — 标注不确定项与缺失项：若某个字段信息模糊、隐含或缺失，"
    "将其列入 uncertainties 列表，描述模糊原因和可能的解释范围。\n"
    "Step 3 — 自我追问（内部，≤2 条）：对模糊项生成最多 2 条自我追问，"
    "尝试从上下文中推断答案。如「用户提到破三但没有说当前跑量，"
    "能否从训练类型反推经验水平？」\n"
    "Step 4 — 合并输出最终 JSON：将明确字段、推断字段（标注 confidence）、"
    "以及无法确定的项（写入 notes）合并输出。\n\n"
    "══════════════════════════\n"
    "【归一化规则】\n\n"
    "- 距离统一为 km。若原文为英里：1 mile = 1.60934 km，保留 1 位小数。\n"
    "- 配速统一为 min:sec/km（如 5:30/km）。若为 /mile 配速，自动换算"
    "（min/mile ÷ 1.60934）。不接受「分秒」混合汉字格式。\n"
    "- 时间表达归一化：「两个月后」→ 当前日期 +60 天 → YYYY-MM-DD；"
    "「下半年」→ 当年 7 月 1 日；「明年春天」→ 次年 3 月 1 日。"
    "无法精确到日的，标注 confidence: low。\n"
    "- 周跑量如果是范围（如「50-60 km」），提取为数字时取中间值，notes 中记录原始范围。\n\n"
    "══════════════════════════\n"
    "【字段反推规则】\n\n"
    "- t_pace 可从 goal 反推（全马目标成绩 → 估算阈值配速），但必须标注 confidence: inferred。\n"
    "  反推公式：全马目标成绩每公里配速 − 15~20 秒 ≈ 阈值配速。\n"
    "- experience_level 可从 weekly_mileage 推断：\n"
    "  < 30 km → 新手 (confidence: inferred)；30-60 km → 中级 (confidence: inferred)；\n"
    "  > 60 km → 进阶 (confidence: inferred)；> 100 km + 有明确比赛目标 → 精英 (confidence: inferred)。\n"
    "- 任何 confidence: inferred 的字段，请在 notes 中注明「由系统推断，建议确认」。\n"
    "- 若用户同时提到多个目标（如「半马130或全马破三」），"
    "优先提取 target_race_date 更近的目标，备选目标写入 notes。\n\n"
    "══════════════════════════\n"
    "【提取字段定义】\n\n"
    "- goal (string, 可选): 目标赛事或目标成绩。如「半马1小时30分」「全马3小时」「BQ达标」\n"
    "- experience_level (string, 可选): 经验水平。仅接受：新手 / 中级 / 进阶 / 精英。"
    "直接从原文提取；若原文无明确表述，可用反推规则但标注 confidence: inferred\n"
    "- weekly_mileage (number, 可选): 当前周跑量，单位 km。仅接受数字\n"
    "- lthr (number, 可选): 乳酸阈心率 (bpm)。仅接受数字\n"
    "- t_pace (string, 可选): 阈值配速，格式 min:sec/km。如「3:50/km」。"
    "可从 goal 反推但标注 confidence: inferred\n"
    "- vo2max (number, 可选): 最大摄氧量。仅接受数字\n"
    "- target_race_date (string, 可选): 比赛日期或距比赛多久。"
    "优先输出 YYYY-MM-DD，其次保留原文表达\n"
    "- available_days (string, 可选): 可用训练日。如「周一,周三,周五,周日」\n"
    "- max_session_minutes (number, 可选): 单次训练最长分钟数\n"
    "- pace_preference (string, 可选): 用户指定的任何配速偏好\n"
    "- terrain_preference (string, 可选): 场地偏好。如「田径场」「公园」「跑步机」\n"
    "- training_types (array, 可选): 用户要求的训练类型列表。"
    "如 [\"间歇跑\", \"节奏跑\", \"长距离\"]\n"
    "- notes (string, 可选): 其他值得记录的信息、不确定项、推断说明\n"
    "- uncertainties (array, 可选): 模糊或缺失的关键字段列表，"
    "每项格式 {field: 字段名, reason: 模糊原因, possible_values: 可能范围}，最多 2 项\n"
    "- confidence (string, 可选): 整体提取置信度。high（多字段明确）/ medium（部分推断）/ low（信息稀疏）\n\n"
    "══════════════════════════\n"
    "【输出格式】\n\n"
    "严格输出 JSON 对象，只包含有值的字段（缺失字段省略，不输出 null 或空字符串）。\n"
    "格式示例：\n"
    "{\"goal\": \"全马3小时\", \"weekly_mileage\": 60, \"experience_level\": \"进阶\","
    " \"notes\": \"用户提到破三目标，当前周跑量60km，未提供阈值配速\"}\n\n"
    "══════════════════════════\n"
    "【硬性约束】\n\n"
    "1. 只提取明确出现或可通过简单换算得到的信息，不得编造。\n"
    "2. 模糊信息写入 notes 或 uncertainties，不得猜测为确定值。\n"
    "3. uncertainties 最多 2 项，多余的模糊信息直接入 notes。\n"
    "4. 反推字段必须标注 confidence: inferred。\n"
    "5. 不要反问用户，不要输出 JSON 以外的任何文字。"
)


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

# 每个字段对训练计划的价值解释，用于 missing_info_handler 追问生成
FIELD_VALUE_WHY = {
    "goal": "确定训练周期长度、专项强度与比赛配速目标",
    "weekly_mileage": "评估当前负荷基础，决定训练量起点和增幅上限",
    "vo2max": "衡量有氧能力上限，辅助确定间歇跑配速区间",
    "lthr": "乳酸阈心率是划分训练强度区的基准，影响所有心率导向训练",
    "t_pace": "阈值配速是节奏跑、间歇跑、长距离配速的核心参照",
    "available_days": "决定周训练频率和强度课分布（硬-易-硬交替）",
    "max_session_minutes": "限制单次训练时长，影响长距离和双练日规划",
    "pace_preference": "用户主观配速偏好优先于公式推导",
    "terrain_preference": "场地类型影响训练手段选择（田径场间歇 vs 公园长距离）",
    "experience_level": "决定训练进阶节奏、恢复需求和伤病风险管控策略",
    "target_race_date": "倒推训练周期各阶段时间节点和 taper 起点",
    "training_types": "了解用户偏好或教练要求的训练手段，确保课表覆盖",
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


async def _extract_profile_from_query(query: str, config: RunnableConfig, current_usage: dict, max_turns: int = 2) -> dict:
    if not query or len(query) < 20:
        return {}
    import json

    def _parse_json(text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}") + 1
        if 0 <= start < end:
            return json.loads(text[start:end])
        return {}

    try:
        # Turn 1: 初步提取
        result, _ = await ai_invoke(
            f"{EXTRACT_PROFILE_SYSTEM}\n\n用户输入：\n{query}\n\n仅返回 JSON 对象。",
            config, current_usage,
        )
        parsed = _parse_json(result)
    except Exception:
        return {}

    if not parsed:
        return {}

    uncertainties = parsed.get("uncertainties", [])
    confidence = parsed.get("confidence", "high")

    # Turn 2: 如果有不确定项且置信度非 high，发起自我纠错
    if uncertainties and max_turns > 1 and confidence != "high":
        uncertainty_fields = [u.get("field", "") for u in uncertainties if u.get("field")]
        try:
            followup_prompt = (
                f"{EXTRACT_PROFILE_SYSTEM}\n\n"
                f"上一轮提取结果中以下字段不确定：{', '.join(uncertainty_fields)}。\n"
                f"请仔细重新分析用户输入，尝试从上下文推断这些字段的值。"
                f"如果仍无法确定，保持原值并将不确定性写入 notes。\n\n"
                f"用户输入：\n{query}\n\n仅返回 JSON 对象。"
            )
            result2, _ = await ai_invoke(followup_prompt, config, current_usage)
            parsed2 = _parse_json(result2)
            if parsed2:
                # 合并：第二轮结果优先，但保留第一轮中第二轮缺失的字段
                for key, value in parsed.items():
                    if key not in parsed2 and key not in ("uncertainties", "confidence"):
                        parsed2[key] = value
                parsed = parsed2
        except Exception:
            pass

    # 清理内部字段，只保留用户画像字段
    parsed.pop("uncertainties", None)
    parsed.pop("confidence", None)
    return parsed


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
    
    # 获取图谱上下文（展开“动作库”等通用实体为具体标签）
    kg_entities = expand_entities_for_kg(entities)
    try:
        graph_res = graph_engine.search_graph(kg_entities, max_hops=2)
        graph_edges = graph_res.get("edges", [])
        graph_context, mermaid_graph = get_graph_context(kg_entities)
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
    profile = state.get("user_profile", {})
    experience_level = profile.get("experience_level", "")

    # 指标价值速查（取缺失字段的价值解释）
    value_lines = "\n".join(
        f"- {FIELD_LABELS.get(f, f)}：{FIELD_VALUE_WHY.get(f, '')}"
        for f in missing
    ) if missing else ""

    # 分层语气与侧重点
    if experience_level in ("精英",):
        level_context = (
            "你正在与一位精英跑者对话。请围绕「强度分布与恢复管理」追问，"
            "语气果断、简洁，直接切入核心指标。可以适当使用专业术语。"
        )
    elif experience_level in ("进阶",):
        level_context = (
            "你正在与一位进阶跑者对话。请围绕「周期化结构与训练负荷」追问，"
            "语气专业但平易，可以提及 Tempo、LSD 等常见术语。"
        )
    elif experience_level in ("新手", "初级",):
        level_context = (
            "你正在与一位新手跑者对话。请围绕「目标设定与时间保护」追问，"
            "语气积极、鼓励，避免使用专业术语，降低用户心理门槛。"
        )
    else:
        level_context = (
            "请用专业但亲和的语气帮助用户补充关键信息。"
        )

    if missing:
        prompt = (
            f"用户提问：「{query}」\n"
            f"用户经验水平：{experience_level or '未知'}\n"
            f"当前缺失的画像指标：{', '.join(missing)}\n\n"
            f"这些指标的价值：\n{value_lines}\n\n"
            f"{level_context}\n\n"
            f"请生成 2-3 条追问，每条以 • 开头，≤30 字，直接可回答。"
            f"语气专业但亲和，可加入「哪怕只补充 1-2 项我也能给出更好的建议」降低压力。"
            f"控制在 150 字以内。不要反问与缺失指标无关的问题。"
        )
    elif not rag_sources:
        available_entities = "、".join(entities[:3]) if entities else "无特定实体"
        prompt = (
            f"用户提问：「{query}」\n"
            f"已识别实体：{available_entities}\n"
            f"用户经验水平：{experience_level or '未知'}\n"
            f"当前知识库中没有检索到相关证据。\n\n"
            f"{level_context}\n\n"
            f"请生成 2-3 个具体的追问，引导用户补充更详细的目标、周期或限制条件。"
            f"每条追问以 • 开头，≤30 字，指向用户可以立即回答的具体数据。"
            f"控制在 100 字以内。"
        )
    else:
        available_entities = "、".join(entities[:3]) if entities else "无特定实体"
        prompt = (
            f"用户提问：「{query}」\n"
            f"已识别实体：{available_entities}\n"
            f"意图分类：{category}\n"
            f"用户经验水平：{experience_level or '未知'}\n"
            f"当前证据不足以生成处方级建议。\n\n"
            f"{level_context}\n\n"
            f"请生成 2-3 个有具体指向的追问，帮助用户补充训练目标、当前能力、可用时间等关键信息。"
            f"每条追问以 • 开头，≤30 字，尽可能结合已识别实体（{available_entities}）来追问。"
            f"控制在 120 字以内。"
        )

    try:
        result, usage = await ai_invoke(prompt, config, state.get("token_usage"))
        content = f"## 需要更多信息\n{result}" if result else _static_fallback(missing, rag_sources, experience_level)
        return {
            "final_report": content,
            "reasoning_log": ["[missing_info] 已通过 LLM 生成缺失信息引导"],
            "token_usage": usage,
        }
    except Exception:
        content = _static_fallback(missing, rag_sources, experience_level)
        return {
            "final_report": content,
            "reasoning_log": ["[missing_info] 已生成缺失信息引导 (LLM 回退到静态模板)"],
            "token_usage": ensure_usage(state.get("token_usage")),
        }


def _static_fallback(missing: list, rag_sources: list, experience_level: str = "") -> str:
    # 分层语气
    if experience_level in ("精英",):
        tone_hint = "简洁直接"
    elif experience_level in ("进阶",):
        tone_hint = "专业平易"
    elif experience_level in ("新手", "初级",):
        tone_hint = "鼓励亲和"
    else:
        tone_hint = "专业但亲和"

    if missing:
        value_lines = "\n".join(
            f"- **{FIELD_LABELS.get(f, f)}**：{FIELD_VALUE_WHY.get(f, '训练计划的关键参考指标')}"
            for f in missing
        )
        return (
            f"## 需要补充一些关键信息\n\n"
            f"为了给你生成更科学的训练处方（{tone_hint}），还需要了解：\n\n"
            f"{value_lines}\n\n"
            f"> 哪怕只补充 1-2 项，我也能给出比现在更贴合你的建议。\n\n"
            f"直接回复这些指标的数值即可，我会据此重新生成计划。"
        )
    elif not rag_sources:
        return (
            "## 知识库证据不足\n\n"
            "当前本地知识库中没有检索到足够的训练科学证据，"
            "系统不会在缺乏依据的情况下猜测处方级建议。\n\n"
            "**你可以尝试：**\n"
            "- 上传相关的 PDF 训练指南、动作库或研究资料后再试\n"
            "- 补充更详细的训练目标、当前能力或可用时间（帮助系统更精准检索）\n"
            "- 换一种方式描述你的问题（更具体的关键词能命中更多资料）"
        )
    return (
        "## 信息不足\n\n"
        "当前问题缺少足够的上下文来生成可靠建议。\n\n"
        "请尝试补充：\n"
        "- 你的训练目标（如备赛什么项目、目标成绩）\n"
        "- 当前训练状态（如周跑量、配速范围）\n"
        "- 具体限制或关注点（如可用训练日、伤病顾虑）"
    )
