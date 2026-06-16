import json
import re
import time
import asyncio
import hashlib
import logging
import copy
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
try:
    from langchain_ollama import ChatOllama
except ImportError:  # 运行时缺依赖时降级：仅 STRICT_MODE 离线流水线/检索不需要 LLM
    class ChatOllama:  # type: ignore[no-redef]
        """Stub：langchain_ollama 未安装时的占位。

        生产链路 STRICT_MODE=True，图谱检索与候选合并不调用 LLM；
        仅 LLM 三元组动态抽取需要真实 ChatOllama，缺失时该路径会显式失败。
        """

        def __init__(self, *args, **kwargs):
            self._unavailable = True

        def invoke(self, *args, **kwargs):
            raise RuntimeError(
                "ChatOllama 不可用：langchain_ollama 未安装。"
                "图谱 LLM 抽取需要此依赖；检索与候选合并不受影响。"
            )

try:
    from langchain_core.messages import HumanMessage
except ImportError:  # 同上：仅 LLM 抽取路径用到
    class HumanMessage:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            self.content = kwargs.get("content", args[0] if args else "")
from marathon_qa_assistant.core.app_state import BASE_DIR, DATA_DIR, V2_VECTOR_DIR
from marathon_qa_assistant.core.settings import get_settings, load_project_dotenv
from marathon_qa_assistant.services.kb.graph_evidence import (
    evidence_from_graph_edge,
    graph_binding_to_legacy_evidence,
)

# 配置日志
logger = logging.getLogger("graph_engine")

# 加载配置
load_project_dotenv(BASE_DIR / "graphrag_project" / ".env")
_settings = get_settings()
OLLAMA_BASE_URL = _settings.ollama_base_url
OLLAMA_MODEL = _settings.ollama_model
_raw = _settings.graphrag_api_key
_stripped = (_raw or "").strip()
if _stripped and _stripped != "default_token_for_dev":
    AUTH_TOKEN = _stripped
else:
    logger.warning(
        "GRAPHRAG_API_KEY 未设置或仍为开发默认值，知识图谱将初始化为空图。"
    )
    AUTH_TOKEN = ""

EXACT_RELATION_MAP = {
    "需要": "requires",
    "要求": "requires",
    "需求量": "requires",
    "取决于": "requires",
    "includes": "includes",
    "contains": "includes",
    "包括": "includes",
    "包含": "includes",
    "分为": "includes",
    "安排": "includes",
    "目标": "targets",
    "针对": "targets",
    "提高": "targets",
    "提升": "targets",
    "增强": "targets",
    "改善": "targets",
    "优化": "targets",
    "训练": "targets",
    "处于": "uses_zone",
    "位于": "uses_zone",
    "强度区间": "uses_zone",
    "参数化": "requires",
    "定义为": "requires",
    "设计": "requires",
    "结构化": "requires",
    "限制": "constrained_by",
    "约束": "constrained_by",
    "上限": "constrained_by",
    "不得超过": "constrained_by",
    "至少": "constrained_by",
    "每周安排": "constrained_by",
    "产生": "produces",
    "导致": "produces",
    "引起": "produces",
    "带来": "produces",
    "测量": "measured_by",
    "测定": "measured_by",
    "衡量": "measured_by",
    "评估": "measured_by",
    "leads to": "produces",
    "results in": "produces",
    "improves": "targets",
}

RELATION_KEYWORD_GROUPS = [
    (["需要", "必须", "需求", "要求", "依赖", "取决于", "require", "need", "depend"], "requires"),
    (["包含", "包括", "组成", "构成", "分为", "安排", "集成", "组合", "include", "contain", "comprise"], "includes"),
    (["针对", "目标", "提高", "提升", "增强", "改善", "优化", "刺激", "训练", "improve", "enhance", "increase", "target"], "targets"),
    (["区间", "范围", "强度", "zone", "intensity"], "uses_zone"),
    (["参数", "模板", "格式", "结构化", "定义", "设计", "template", "parameter", "format"], "parameterized_by"),
    (["限制", "约束", "上限", "下限", "不得超过", "不超过", "至少", "最多", "每周", "limit", "constrain", "cap", "maximum", "minimum"], "constrained_by"),
    (["产生", "导致", "引起", "带来", "造成", "结果", "produce", "cause", "result", "lead"], "produces"),
    (["测量", "测定", "测试", "评估", "量化", "衡量", "measure", "evaluate", "quantify", "metric"], "measured_by"),
]

TYPE_RELATION_MAP = {
    ("goal", "phase"): "requires",
    ("phase", "workout"): "includes",
    ("workout", "physiology"): "targets",
    ("workout", "zone"): "uses_zone",
    ("workout", "template"): "requires",
    ("template", "constraint"): "constrained_by",
    ("workout", "adaptation"): "produces",
    ("zone", "metric"): "measured_by",
}

ZONE_PATTERNS = [
    r"\bz[1-9]\b",
    r"zone\s*[1-9]",
    r"心率区间",
    r"lthr",
    r"vo2max区",
]

TEMPLATE_PATTERNS = [
    r"\d+\s*[x×*]\s*\d+\s*(km|m)\b",
    r"\d+\s*组",
    r"@\s*\d+[:：]\d+",
    r"\d+\s*x\s*\d+",
    r"\d+\s*[分钟分]\s*[x×*]\s*\d+",
]

METRIC_PATTERNS = [
    r"\d+[:：]\d+\s*/km",
    r"\d+\s*bpm",
    r"\d+(\.\d+)?\s*km\b",
    r"\d+\s*(min|sec|分钟|秒)\b",
    r"\d+%",
]

WORKOUT_KEYWORDS = [
    "tempo", "threshold", "interval", "long run", "easy run", "recovery",
    "progression", "fartlek", "hill repeat", "节奏跑", "长距离", "间歇",
    "轻松跑", "恢复跑", "摄氧量", "无氧阈", "重复跑",
]

PHYSIOLOGY_KEYWORDS = [
    "lactate threshold", "乳酸阈", "vo2max", "最大摄氧量",
    "aerobic", "anaerobic", "fat oxidation", "脂代谢", "心肺功能",
]

GOAL_KEYWORDS = [
    "5k", "10k", "half marathon", "marathon", "半马", "全马", "配速目标", "pb",
]

PHASE_KEYWORDS = [
    "base", "build", "peak", "taper", "基础期", "强化期", "巅峰期", "减量期",
]

CONSTRAINT_KEYWORDS = [
    "per week", "max", "limit", "每周", "上限", "限制", "不得超过", "至少",
]

ATHLETE_KEYWORDS = [
    "runner", "athlete", "beginner", "advanced", "年龄", "水平", "经验",
]

EQUIPMENT_KEYWORDS = [
    "shoes", "track", "treadmill", "跑鞋", "跑道", "操场",
]

ADAPTATION_KEYWORDS = [
    "improve", "increase", "enhance", "提升", "增强", "改善", "适应",
]

CANONICAL_ENTITY_MAP = {
    "lt": "lactate threshold",
    "vo2": "vo2max",
    "hm": "half marathon",
}

REGISTRY_SOURCE_ID = "decision_graph_registry_v1"
REGISTRY_SOURCE_NAME = "decision_graph_registry"
DECISION_REGISTRY_FILENAME = "decision_registry.json"
QUALITY_WORKOUT_LABELS = {"节奏跑", "阈值节奏跑", "无氧阈", "摄氧量", "高强度间歇", "重复跑", "极限间歇"}
RECOVERY_WORKOUT_LABELS = {"轻松跑", "恢复跑", "休息"}
WEEK_FALLBACK_WORKOUTS = ["轻松跑", "恢复跑", "休息"]

# 注册表 JSON 路径：优先同目录 governance/，其次 GRAPH_DATA_PATH 同级
def _resolve_decision_registry_path() -> Path:
    governance = DATA_DIR / "knowledge" / "governance" / DECISION_REGISTRY_FILENAME
    if governance.exists():
        return governance
    return GRAPH_DATA_PATH.parent / DECISION_REGISTRY_FILENAME

# 兜底硬编码（只在 JSON 不可用时使用）
_FALLBACK_CONSTRAINT_REGISTRY = {
    "c_quality_sessions_weekly_cap": {
        "label": "每周质量课最多 2 次",
        "type": "constraint",
        "rule": "quality_sessions_per_week <= 2",
        "description": "限制节奏跑、无氧阈、摄氧量、重复跑等高质量训练的周频次。",
    },
    "c_quality_gap_48h": {
        "label": "高质量课间隔至少 48 小时",
        "type": "constraint",
        "rule": "hours_between_quality_sessions >= 48",
        "description": "避免连续高强度刺激，保留恢复窗口。",
    },
    "c_long_run_weekly_cap": {
        "label": "每周长距离最多 1 次",
        "type": "constraint",
        "rule": "long_run_sessions_per_week <= 1",
        "description": "防止长距离课过量堆叠。",
    },
    "c_long_run_duration_cap": {
        "label": "长距离时长不得超过单次上限",
        "type": "constraint",
        "rule": "long_run_duration_min <= athlete.max_session_minutes",
        "description": "长距离模板必须受用户单次最长训练时长约束。",
    },
    "c_easy_after_quality": {
        "label": "高质量课后优先恢复或轻松跑",
        "type": "constraint",
        "rule": "day_after_quality in {'easy_run','recovery','rest'}",
        "description": "控制高强度训练后的次日安排。",
    },
}

_FALLBACK_TEMPLATE_REGISTRY = {
    "tpl_easy_run_duration_v1": {
        "label": "轻松跑模板 30-60min",
        "type": "template",
        "workout_labels": ["轻松跑", "恢复跑"],
        "zone_label": "Z1",
        "physiology_targets": ["有氧基础"],
        "adaptation_targets": ["恢复能力", "基础耐力"],
        "fields": {
            "duration_min": "30-60",
            "intensity": "Z1",
            "rest": "无",
            "surface": "公园|公路",
        },
        "constraint_ids": ["c_easy_after_quality"],
    },
    "tpl_long_run_base_v1": {
        "label": "长距离模板 80-120min",
        "type": "template",
        "workout_labels": ["长距离", "长距离有氧"],
        "zone_label": "Z2",
        "physiology_targets": ["脂代谢", "有氧基础"],
        "adaptation_targets": ["耐力提升"],
        "fields": {
            "duration_min": "80-120",
            "intensity": "Z2",
            "progression": "optional_last_20min",
            "surface": "公路|公园",
        },
        "constraint_ids": ["c_long_run_weekly_cap", "c_long_run_duration_cap"],
    },
    "tpl_aerobic_threshold_continuous_v1": {
        "label": "有氧阈模板 30-50min",
        "type": "template",
        "workout_labels": ["有氧阈"],
        "zone_label": "Z3",
        "physiology_targets": ["有氧阈"],
        "adaptation_targets": ["稳态耐力"],
        "fields": {
            "duration_min": "30-50",
            "intensity": "Z3",
            "rest": "无",
            "surface": "公路|跑道",
        },
        "constraint_ids": ["c_quality_gap_48h"],
    },
    "tpl_tempo_continuous_v1": {
        "label": "节奏跑模板 20-40min",
        "type": "template",
        "workout_labels": ["节奏跑", "阈值节奏跑"],
        "zone_label": "Z4",
        "physiology_targets": ["乳酸阈"],
        "adaptation_targets": ["阈值提升"],
        "fields": {
            "duration_min": "20-40",
            "intensity": "Z4",
            "rest": "无",
            "surface": "公路|跑道",
        },
        "constraint_ids": ["c_quality_sessions_weekly_cap", "c_quality_gap_48h"],
    },
    "tpl_threshold_cruise_v1": {
        "label": "无氧阈模板 4x1600m",
        "type": "template",
        "workout_labels": ["无氧阈"],
        "zone_label": "Z5",
        "physiology_targets": ["乳酸阈"],
        "adaptation_targets": ["高阈值耐受"],
        "fields": {
            "reps": "4",
            "distance": "1600m",
            "intensity": "Z5",
            "rest": "2min jog",
        },
        "constraint_ids": ["c_quality_sessions_weekly_cap", "c_quality_gap_48h"],
    },
    "tpl_vo2_1k_v1": {
        "label": "摄氧量模板 6x1km",
        "type": "template",
        "workout_labels": ["摄氧量", "高强度间歇"],
        "zone_label": "Z8",
        "physiology_targets": ["vo2max"],
        "adaptation_targets": ["最大摄氧量提升"],
        "fields": {
            "reps": "5-6",
            "distance": "1km",
            "intensity": "Z8",
            "rest": "90s jog",
        },
        "constraint_ids": ["c_quality_sessions_weekly_cap", "c_quality_gap_48h"],
    },
    "tpl_repetition_400_v1": {
        "label": "重复跑模板 8x400m",
        "type": "template",
        "workout_labels": ["重复跑", "极限间歇"],
        "zone_label": "Z9",
        "physiology_targets": ["跑步经济性"],
        "adaptation_targets": ["神经肌肉刺激"],
        "fields": {
            "reps": "8",
            "distance": "400m",
            "intensity": "Z9",
            "rest": "200m walk",
        },
        "constraint_ids": ["c_quality_sessions_weekly_cap", "c_quality_gap_48h"],
    },
}

# 懒加载 LLM 单例：避免模块 import 时创建 ChatOllama（Ollama 不可用时会阻塞/失败 import），
# 首次实际抽取图谱三元组时才创建。后续如需热更新模型配置可在此扩展。
_llm_instance = None


def _get_llm():
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ChatOllama(
            model=OLLAMA_MODEL,
            temperature=0.1,
            base_url=OLLAMA_BASE_URL,
        )
    return _llm_instance

GRAPH_DATA_PATH = V2_VECTOR_DIR / "knowledge_graph.json"


def _safe_resolve(path: Path) -> Path:
    try:
        return path.resolve()
    except Exception:
        return path.absolute()


def _graph_source_label(graph_dir: Path) -> str:
    resolved = _safe_resolve(graph_dir)
    if resolved == _safe_resolve(V2_VECTOR_DIR):
        return "v2"
    return str(resolved)

class GraphEngine:
    """
    知识图谱引擎：负责从文本中提取三元组、构建图谱、持久化存储以及可视化 (Mermaid)。
    """
    def __init__(self):
        self.GRAPH_DATA_PATH = GRAPH_DATA_PATH
        self.DECISION_REGISTRY_PATH = _resolve_decision_registry_path()
        self.nodes = {} # {id: {label: str, type: str, source_chunks: []}}
        self.edges = [] # [{source: id, target: id, relation: str, canonical_relation: str, evidence: dict}]
        self.processed_chunks = {} # 记录已处理的分片 ID 及其文本哈希 {chunk_id: text_hash}
        self._constraint_registry: Dict[str, Any] = {}
        self._template_registry: Dict[str, Any] = {}
        self._registry_source_id: str = REGISTRY_SOURCE_ID
        self._mermaid_cache = None # 缓存以减少重复生成
        self._cache_key = None
        self.STRICT_MODE = True # [KB-only] 严格模式，生产链路禁用 LLM 动态提取
        self._load_decision_registry()
        self.load_graph()
        if self._ensure_decision_registry():
            self.save_graph()

    def load_graph(self):
        """从磁盘加载图谱数据。

        fail-loud 策略：JSON 解析失败时**不静默清空** self.nodes/self.edges，
        而是保留内存中已有图谱（通常是注册表初始化的兜底图），并把损坏文件
        改名隔离 + 记 error，避免一次截断就让整张抽取图谱无声丢失。
        """
        if not self.GRAPH_DATA_PATH.exists():
            return
        try:
            with open(self.GRAPH_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            # 损坏文件：隔离改名，保留内存现状，明确报错而非静默吞掉
            import time as _t
            quarantine = self.GRAPH_DATA_PATH.with_suffix(
                f".corrupted_{_t.strftime('%Y%m%d_%H%M%S')}.json"
            )
            try:
                self.GRAPH_DATA_PATH.rename(quarantine)
                logger.error(
                    f"[graph_engine] 主图谱 JSON 损坏（{e}），已隔离至 {quarantine.name}；"
                    f"保留内存图谱({len(self.nodes)}节点)，请从候选重建："
                    f"python scripts/merge_knowledge_graph_candidates.py"
                )
            except OSError as rename_err:
                logger.error(
                    f"[graph_engine] 主图谱 JSON 损坏（{e}）且无法隔离（{rename_err}）；"
                    f"保留内存图谱({len(self.nodes)}节点)，请人工修复。"
                )
            return
        except Exception as e:
            logger.error(f"加载图谱失败: {e}")
            return

        # 解析成功才覆盖内存
        self.nodes = data.get("nodes", {})
        self.edges = data.get("edges", [])
        processed = data.get("processed_chunks", {})
        if isinstance(processed, list):
            self.processed_chunks = {cid: "" for cid in processed}
        else:
            self.processed_chunks = processed
        migrated = self._migrate_graph_schema()
        self.clear_cache()
        if migrated:
            self.save_graph()

    def save_graph(self):
        """将图谱数据持久化到磁盘（原子写入，防止中途被杀留下截断文件）。"""
        import os
        import tempfile

        target = self.GRAPH_DATA_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "nodes": self.nodes,
            "edges": self.edges,
            "processed_chunks": self.processed_chunks,
        }
        # 先完整写入同目录临时文件并 fsync，再原子 rename 覆盖正式文件。
        # 这样即使进程在写入中途被杀，正式文件也保持上一份完整版本，不会出现半截 JSON。
        fd, tmp_path = tempfile.mkstemp(
            dir=str(target.parent), prefix=".kg_tmp_", suffix=".json"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, target)  # 原子替换
        except Exception:
            # 写入失败时清理临时文件，不破坏正式文件
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            raise
        self.clear_cache()

    def _load_decision_registry(self):
        """从 JSON 加载决策注册表；JSON 不可用时使用 LLM 知识生成。"""
        if self.DECISION_REGISTRY_PATH and self.DECISION_REGISTRY_PATH.exists():
            try:
                import json as _json
                with open(self.DECISION_REGISTRY_PATH, "r", encoding="utf-8") as f:
                    data = _json.load(f)
                self._constraint_registry = data.get("constraint_registry", {})
                self._template_registry = data.get("template_registry", {})
                self._registry_source_id = data.get("source_id", REGISTRY_SOURCE_ID)
                if self._constraint_registry and self._template_registry:
                    return
            except Exception:
                pass
        # JSON 不可用：异步调用 LLM 生成（通过 asyncio 事件循环）
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                future = concurrent.futures.Future()
                def _build():
                    async def _inner():
                        return await self._build_registry_from_llm()
                    return asyncio.ensure_future(_inner())
                # 无法在同步上下文中等待，使用硬编码兜底并标记为待升级
                logger.warning("无法在同步上下文中调用 LLM 生成注册表，使用空注册表。"
                             "请运行 scripts/build_registry_from_llm.py 生成。")
                self._constraint_registry = {}
                self._template_registry = {}
                self._registry_source_id = REGISTRY_SOURCE_ID
                return
            self._constraint_registry = loop.run_until_complete(
                self._build_registry_from_llm())
            self._template_registry = self._constraint_registry  # LLM 返回完整注册表
        except Exception as exc:
            logger.warning(f"LLM 注册表生成失败: {exc}，使用空注册表。")
            self._constraint_registry = {}
            self._template_registry = {}
        self._registry_source_id = REGISTRY_SOURCE_ID

    async def _build_registry_from_llm(self) -> Dict[str, Any]:
        """使用 LLM 运动科学知识生成训练决策注册表。"""
        prompt = (
            "你是一位马拉松训练专家。请为马拉松训练系统生成训练约束和课表模板的 JSON 配置。"
            "输出严格的 JSON，格式如下：\n"
            '{"constraint_registry": {"c_1": {"label": "约束名", "type": "constraint", '
            '"rule": "逻辑表达式", "description": "说明"}, ...}, '
            '"template_registry": {"tpl_1": {"label": "模板名", "type": "template", '
            '"workout_labels": ["训练课名"], "zone_label": "Z1-Z5", '
            '"physiology_targets": ["生理目标"], "adaptation_targets": ["适应目标"], '
            '"fields": {"duration_min": "区间", "intensity": "区间"}, '
            '"constraint_ids": ["c_1"]}, ...}}\n'
            "规则：\n"
            "1. 约束至少包括：质量课周上限、质量课间隔、长距离周上限、高强度课后恢复、长距离时长上限\n"
            "2. 模板至少包括：轻松跑(Z1,30-60min)、长距离(Z2,80-120min)、有氧阈(Z3,30-50min)、"
            "节奏跑(Z4,20-40min)、无氧阈间歇(Z5,4x1600m)、摄氧量间歇(Z8,6x1km)、重复跑(Z9,8x400m)\n"
            "3. workout_labels 和 zone_label 使用中文\n"
            "4. 每个模板至少引用一个约束\n"
            "仅返回 JSON，不要任何其他文本。"
        )
        try:
            model = ChatOllama(model="qwen2.5:latest", base_url=OLLAMA_BASE_URL, temperature=0.3)
            response = model.invoke([HumanMessage(content=prompt)])
            text = response.content if hasattr(response, 'content') else str(response)
            import json as _json
            start = text.find("{")
            end = text.rfind("}") + 1
            if 0 <= start < end:
                data = _json.loads(text[start:end])
                if "constraint_registry" in data and "template_registry" in data:
                    return data
        except Exception as e:
            logger.error(f"LLM 注册表生成失败: {e}")
        return {"constraint_registry": {}, "template_registry": {}}

    def clear_cache(self):
        """清除可视化缓存"""
        self._mermaid_cache = None
        self._cache_key = None

    def merge_validated_candidates(
        self,
        candidate_queue_path: str | Path,
        *,
        min_confidence: float = 0.5,
    ) -> Dict[str, Any]:
        """从候选队列加载已审核的三元组，合并进主图。

        只合并 status="validated" 且 confidence >= min_confidence 的候选。
        自动创建缺失的节点，保留 expert_domain 和 bridge_type 元数据。
        返回合并统计。
        """
        import json as _json
        from pathlib import Path as _Path

        queue_path = _Path(candidate_queue_path)
        if not queue_path.exists():
            return {"merged": 0, "skipped": 0, "errors": ["queue_not_found"]}

        merged = 0
        skipped = 0
        errors: list[str] = []

        with open(queue_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    cand = _json.loads(line)
                except _json.JSONDecodeError as exc:
                    errors.append(f"json_error: {exc}")
                    continue

                if cand.get("status") != "validated":
                    skipped += 1
                    continue
                if float(cand.get("confidence", 0.0)) < min_confidence:
                    skipped += 1
                    continue

                head = str(cand.get("head_entity", "")).strip()
                tail = str(cand.get("tail_entity", "")).strip()
                relation = str(cand.get("relation", "")).strip()
                expert_domain = str(cand.get("expert_domain", "training_theory"))
                chunk_id = str(cand.get("chunk_id", ""))
                source_file = str(cand.get("source_file", ""))
                page = cand.get("page")

                if not head or not tail or not relation:
                    errors.append(f"incomplete: {cand.get('candidate_id', '?')}")
                    skipped += 1
                    continue

                # 确定节点类型
                head_type = _node_type_for_entity(head, expert_domain)
                tail_type = _node_type_for_entity(tail, expert_domain)

                # 构建证据
                evidence = {
                    "source": source_file or "kg_candidate",
                    "source_path": source_file or "",
                    "chunk_id": chunk_id,
                    "text_span": str(cand.get("evidence_span", ""))[:300],
                    "confidence": float(cand.get("confidence", 0.5)),
                    "evidence_domain": str(cand.get("evidence_domain", "sports_science_reference")),
                }
                if page:
                    evidence["page"] = int(page)

                # 构建跨领域桥接标记
                edge_extra: dict = {}
                if relation == "bridges_to":
                    edge_extra["bridge_type"] = _infer_bridge_type(head, tail, expert_domain)

                changed = self._upsert_edge(
                    head,
                    tail,
                    relation,
                    source_id=str(cand.get("source_registry_id", "")),
                    source_type=head_type,
                    target_type=tail_type,
                    evidence=evidence,
                    edge_extra={"expert_domain": expert_domain, **edge_extra},
                )

                # 标记为已合并
                cand["status"] = "merged"
                merged += 1

        if merged > 0:
            self.save_graph()

        # 回写更新后的状态到队列
        if merged > 0:
            _rewrite_queue_status(queue_path)

        return {"merged": merged, "skipped": skipped, "errors": errors}

    def merge_approved_candidates(
        self,
        candidates_path: str | Path,
    ) -> Dict[str, Any]:
        """合并 merge_approved=True 的新格式候选三元组进主图。

        新候选文件（knowledge_graph_candidates.jsonl）字段：
          source_chunk_id, confidence_score, merge_approved, merge_status

        与旧 merge_validated_candidates() 不同：
          - 门控字段是 merge_approved（布尔），不是 status="validated"
          - 边增加 edge_origin/candidate_id/extraction_method/source_chunk_id/confidence_score 元数据
        """
        import json as _json
        from pathlib import Path as _Path

        queue_path = _Path(candidates_path)
        if not queue_path.exists():
            return {"merged": 0, "skipped": 0, "errors": ["queue_not_found"]}

        records: list[Dict[str, Any]] = []
        with open(queue_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(_json.loads(line))
                except _json.JSONDecodeError as exc:
                    pass

        merged = 0
        skipped = 0
        errors: list[str] = []

        for cand in records:
            if not cand.get("merge_approved"):
                skipped += 1
                continue
            if cand.get("merge_status") == "merged":
                skipped += 1
                continue

            head = str(cand.get("head_entity", "")).strip()
            tail = str(cand.get("tail_entity", "")).strip()
            relation = str(cand.get("relation", "")).strip()
            expert_domain = str(cand.get("expert_domain", "training_protocol"))
            source_chunk_id = str(cand.get("source_chunk_id", ""))
            source_file = str(cand.get("source_file", ""))
            page = cand.get("page")
            confidence_score = float(cand.get("confidence_score", 0.0))
            candidate_id = str(cand.get("candidate_id", ""))
            extraction_method = str(cand.get("extraction_method", "llm_offline"))

            if not head or not tail or not relation:
                errors.append(f"incomplete:{candidate_id}")
                skipped += 1
                continue

            head_type = _node_type_for_entity(head, expert_domain)
            tail_type = _node_type_for_entity(tail, expert_domain)

            evidence = {
                "source": source_file or "kg_candidate",
                "source_path": source_file or "",
                "chunk_id": source_chunk_id,
                "text_span": str(cand.get("evidence_span", ""))[:300],
                "confidence": confidence_score,
                "evidence_domain": str(cand.get("evidence_domain", "sports_science_reference")),
            }
            if page:
                evidence["page"] = int(page)

            self._upsert_edge(
                head,
                tail,
                relation,
                source_id=str(cand.get("source_registry_id", "")),
                source_type=head_type,
                target_type=tail_type,
                evidence=evidence,
                edge_extra={
                    "expert_domain": expert_domain,
                    "edge_origin": "auto_extracted",
                    "candidate_id": candidate_id,
                    "extraction_method": extraction_method,
                    "source_chunk_id": source_chunk_id,
                    "confidence_score": confidence_score,
                },
            )
            cand["merge_status"] = "merged"
            merged += 1

        if merged > 0:
            self.save_graph()
            # 回写 merge_status 到候选文件
            with open(queue_path, "w", encoding="utf-8") as f:
                for rec in records:
                    f.write(_json.dumps(rec, ensure_ascii=False) + "\n")

        return {"merged": merged, "skipped": skipped, "errors": errors}

    def _is_id(self, label: str) -> bool:
        """检查标签是否为无效 ID"""
        if not label: return True
        return bool(re.match(r'^[0-9a-f]{12}$', str(label).lower().strip()))

    def _is_metadata(self, label: str) -> bool:
        """过滤文献元数据噪音"""
        if not label: return True
        label_lower = str(label).lower().strip()
        
        # 1. 机构与学术单位
        edu_keywords = ['university', 'college', 'institute', 'department', 'school', 'academy', 'faculty', 'univ.', 'inst.']
        # 2. 出版相关
        pub_keywords = ['journal', 'proceedings', 'volume', 'issue', 'editor', 'publisher', 'published', 'copyright', 'doi:', 'issn', 'isbn', 'pp.', 'pages']
        # 3. 常见非专业噪音
        noise_entities = ['poland', 'warsaw', 'et al', 'abstract', 'keywords', 'introduction', 'conclusion', 'references', 'table', 'figure']
        
        for kw in edu_keywords + pub_keywords + noise_entities:
            if kw in label_lower:
                return True
                
        # 4. 纯年份或引用标识
        if re.match(r'^\d{4}$', label_lower): return True 
        if re.match(r'^\[\d+\]$', label_lower): return True 
        
        return False

    def _normalize_relation(self, relation: str) -> str:
        text = str(relation or "").strip().lower()
        text = re.sub(r"\s+", " ", text).strip(".,;:!?()[]{}\"'")
        return text

    def _get_node_id(self, label: str) -> str:
        normalized = str(label or "").lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:12]

    def _normalize_entity_text(self, text: str) -> str:
        normalized = str(text or "").lower().strip()
        normalized = re.sub(r"\s+", " ", normalized)
        return CANONICAL_ENTITY_MAP.get(normalized, normalized)

    def _match_any(self, text: str, patterns: List[str]) -> bool:
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)

    def _contains_any(self, text: str, keywords: List[str]) -> bool:
        return any(keyword.lower() in text for keyword in keywords)

    def classify_entity(self, text: str) -> str:
        normalized = self._normalize_entity_text(text)
        if not normalized:
            return "other"
        if self._match_any(normalized, ZONE_PATTERNS):
            return "zone"
        if self._match_any(normalized, TEMPLATE_PATTERNS):
            return "template"
        if self._match_any(normalized, METRIC_PATTERNS):
            return "metric"
        if self._contains_any(normalized, WORKOUT_KEYWORDS):
            return "workout"
        if self._contains_any(normalized, PHYSIOLOGY_KEYWORDS):
            return "physiology"
        if self._contains_any(normalized, GOAL_KEYWORDS):
            return "goal"
        if self._contains_any(normalized, PHASE_KEYWORDS):
            return "phase"
        if self._contains_any(normalized, CONSTRAINT_KEYWORDS):
            return "constraint"
        if self._contains_any(normalized, ATHLETE_KEYWORDS):
            return "athlete"
        if self._contains_any(normalized, EQUIPMENT_KEYWORDS):
            return "equipment"
        if self._contains_any(normalized, ADAPTATION_KEYWORDS):
            return "adaptation"
        return "other"

    def map_relation(self, relation: str, head_type: str = None, tail_type: str = None) -> str:
        normalized = self._normalize_relation(relation)
        if not normalized:
            return "related_to"

        if normalized in EXACT_RELATION_MAP:
            return EXACT_RELATION_MAP[normalized]

        for keywords, canonical in RELATION_KEYWORD_GROUPS:
            if any(keyword in normalized for keyword in keywords):
                return canonical

        if head_type and tail_type:
            inferred = TYPE_RELATION_MAP.get((head_type, tail_type))
            if inferred:
                return inferred

        return "related_to"

    def _build_edge_evidence(
        self,
        source_id: str,
        text_span: str = "",
        source_name: str = "unknown",
        confidence: float = 0.5,
    ) -> Dict[str, Any]:
        span = str(text_span or "").strip()
        if len(span) > 240:
            span = span[:240].rstrip() + "..."
        return {
            "source": source_name or "unknown",
            "chunk_id": source_id or "",
            "text_span": span,
            "confidence": float(confidence),
        }

    def _build_registry_evidence(self, text_span: str) -> Dict[str, Any]:
        return self._build_edge_evidence(
            source_id=self._registry_source_id,
            text_span=text_span,
            source_name=REGISTRY_SOURCE_NAME,
            confidence=0.98,
        )

    def map_edge_to_evidence(self, edge: Dict[str, Any]) -> Dict[str, Any]:
        """将图谱边证据映射为统一 Evidence 结构"""
        return graph_binding_to_legacy_evidence(evidence_from_graph_edge(edge))

    def _ensure_node(
        self,
        label: str,
        node_type: Optional[str],
        source_id: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[str], bool]:
        if not label:
            return None, False
        if self._is_id(label) or self._is_metadata(label):
            return None, False
        if len(str(label).strip()) < 2:
            return None, False

        node_id = self._get_node_id(label)
        changed = False
        if node_id not in self.nodes:
            self.nodes[node_id] = {
                "label": str(label),
                "type": node_type or self.classify_entity(label),
                "source_chunks": [source_id] if source_id else [],
            }
            changed = True
        else:
            if source_id and source_id not in self.nodes[node_id].get("source_chunks", []):
                self.nodes[node_id].setdefault("source_chunks", []).append(source_id)
                changed = True
            if node_type and self.nodes[node_id].get("type") != node_type:
                self.nodes[node_id]["type"] = node_type
                changed = True
            elif not self.nodes[node_id].get("type"):
                self.nodes[node_id]["type"] = self.classify_entity(label)
                changed = True

        for key, value in (extra or {}).items():
            if self.nodes[node_id].get(key) != value:
                self.nodes[node_id][key] = value
                changed = True
        return node_id, changed

    def _upsert_edge(
        self,
        source_label: str,
        target_label: str,
        relation: str,
        source_id: str,
        source_type: Optional[str] = None,
        target_type: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None,
        source_extra: Optional[Dict[str, Any]] = None,
        target_extra: Optional[Dict[str, Any]] = None,
        edge_extra: Optional[Dict[str, Any]] = None,
    ) -> bool:
        source_node_id, source_changed = self._ensure_node(
            source_label,
            node_type=source_type,
            source_id=source_id,
            extra=source_extra,
        )
        target_node_id, target_changed = self._ensure_node(
            target_label,
            node_type=target_type,
            source_id=source_id,
            extra=target_extra,
        )
        if not source_node_id or not target_node_id:
            return source_changed or target_changed

        canonical_relation = self.map_relation(
            relation,
            head_type=self.nodes[source_node_id].get("type"),
            tail_type=self.nodes[target_node_id].get("type"),
        )
        payload = {
            "source": source_node_id,
            "target": target_node_id,
            "relation": str(relation),
            "canonical_relation": canonical_relation,
            "evidence": evidence or self._build_edge_evidence(source_id=source_id),
        }
        payload.update(edge_extra or {})

        for edge in self.edges:
            if (
                edge.get("source") == source_node_id
                and edge.get("target") == target_node_id
                and edge.get("relation") == str(relation)
            ):
                changed = source_changed or target_changed
                for key, value in payload.items():
                    if edge.get(key) != value:
                        edge[key] = value
                        changed = True
                return changed

        self.edges.append(payload)
        return True

    def _ensure_decision_registry(self) -> bool:
        changed = False

        for constraint_id, constraint in self._constraint_registry.items():
            _, node_changed = self._ensure_node(
                constraint["label"],
                node_type=constraint.get("type", "constraint"),
                source_id=self._registry_source_id,
                extra={
                    "registry_id": constraint_id,
                    "registry_kind": "constraint",
                    "node_origin": "registry",
                    "rule": constraint.get("rule", ""),
                    "description": constraint.get("description", ""),
                },
            )
            changed = changed or node_changed

        for template_id, template in self._template_registry.items():
            template_label = template["label"]
            _, node_changed = self._ensure_node(
                template_label,
                node_type=template.get("type", "template"),
                source_id=self._registry_source_id,
                extra={
                    "registry_id": template_id,
                    "registry_kind": "template",
                    "node_origin": "registry",
                    "fields": copy.deepcopy(template.get("fields", {})),
                    "workout_labels": list(template.get("workout_labels", [])),
                    "constraint_ids": list(template.get("constraint_ids", [])),
                },
            )
            changed = changed or node_changed

            for workout_label in template.get("workout_labels", []):
                changed = self._upsert_edge(
                    workout_label,
                    template_label,
                    "requires",
                    source_id=self._registry_source_id,
                    source_type="workout",
                    target_type="template",
                    evidence=self._build_registry_evidence(f"{workout_label} -> {template_label}"),
                ) or changed
                if template.get("zone_label"):
                    changed = self._upsert_edge(
                        workout_label,
                        template["zone_label"],
                        "requires",
                        source_id=self._registry_source_id,
                        source_type="workout",
                        target_type="zone",
                        evidence=self._build_registry_evidence(f"{workout_label} -> {template['zone_label']}"),
                    ) or changed
                for physiology in template.get("physiology_targets", []):
                    changed = self._upsert_edge(
                        workout_label,
                        physiology,
                        "improves",
                        source_id=self._registry_source_id,
                        source_type="workout",
                        target_type="physiology",
                        evidence=self._build_registry_evidence(f"{workout_label} -> {physiology}"),
                    ) or changed
                for adaptation in template.get("adaptation_targets", []):
                    changed = self._upsert_edge(
                        workout_label,
                        adaptation,
                        "supports",
                        source_id=self._registry_source_id,
                        source_type="workout",
                        target_type="adaptation",
                        evidence=self._build_registry_evidence(f"{workout_label} -> {adaptation}"),
                    ) or changed

            for constraint_id in template.get("constraint_ids", []):
                constraint = self._constraint_registry.get(constraint_id)
                if not constraint:
                    continue
                changed = self._upsert_edge(
                    template_label,
                    constraint["label"],
                    "constrains",
                    source_id=self._registry_source_id,
                    source_type="template",
                    target_type="constraint",
                    evidence=self._build_registry_evidence(f"{template_label} -> {constraint['label']}"),
                ) or changed

        return changed

    def get_template_registry(self) -> Dict[str, Any]:
        return copy.deepcopy(self._template_registry)

    def get_constraint_registry(self) -> Dict[str, Any]:
        return copy.deepcopy(self._constraint_registry)

    def get_templates_for_workout(self, workout_label: str) -> List[Dict[str, Any]]:
        normalized = self._normalize_entity_text(workout_label)
        matches = []
        for template_id, template in self._template_registry.items():
            labels = [self._normalize_entity_text(label) for label in template.get("workout_labels", [])]
            if normalized in labels:
                item = copy.deepcopy(template)
                item["template_id"] = template_id
                matches.append(item)
        return matches

    def get_constraints_for_template(self, template_id: str) -> List[Dict[str, Any]]:
        template = self._template_registry.get(template_id, {})
        constraints = []
        for constraint_id in template.get("constraint_ids", []):
            if constraint_id in self._constraint_registry:
                item = copy.deepcopy(self._constraint_registry[constraint_id])
                item["constraint_id"] = constraint_id
                constraints.append(item)
        return constraints

    def _as_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            text = value.replace("，", ",").replace("、", ",")
            return [part.strip() for part in text.split(",") if part.strip()]
        return [str(value).strip()]

    def _safe_float(self, value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _pick_range_value(self, range_text: str, bias: str = "mid") -> str:
        text = str(range_text or "").strip()
        match = re.match(r"^\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*$", text)
        if not match:
            return text
        low = float(match.group(1))
        high = float(match.group(2))
        if bias == "low":
            value = low
        elif bias == "high":
            value = high
        else:
            value = (low + high) / 2.0
        if abs(value - round(value)) < 1e-9:
            return str(int(round(value)))
        return f"{value:.1f}".rstrip("0").rstrip(".")

    def _choose_volume_bias(self, athlete_profile: Dict[str, Any]) -> str:
        weekly = self._safe_float(athlete_profile.get("weekly_mileage"))
        fatigue = str(athlete_profile.get("fatigue_level", "") or athlete_profile.get("fatigue", "")).lower().strip()
        exp = str(athlete_profile.get("experience_level", "")).strip()

        if fatigue in {"high", "高", "heavy", "tired"}:
            return "low"
        if exp in {"新手", "初级"}:
            return "low"
        if weekly is not None and weekly < 40:
            return "low"
        if exp in {"进阶", "精英"} or (weekly is not None and weekly >= 80):
            return "high"
        return "mid"

    def _apply_profile_to_template(self, template: Dict[str, Any], athlete_profile: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        fields = copy.deepcopy(template.get("fields", {}))
        adjustments: List[str] = []
        bias = self._choose_volume_bias(athlete_profile)
        max_session_minutes = self._safe_float(athlete_profile.get("max_session_minutes"))
        terrain_preferences = self._as_list(athlete_profile.get("terrain_preference"))

        if "duration_min" in fields:
            selected_duration = self._pick_range_value(fields["duration_min"], bias=bias)
            fields["duration_min"] = selected_duration
            adjustments.append(f"duration_min 按 {bias} 档位取值为 {selected_duration}")

            duration_value = self._safe_float(selected_duration)
            if duration_value is not None and max_session_minutes is not None and duration_value > max_session_minutes:
                fields["duration_min"] = str(int(max_session_minutes))
                adjustments.append(f"duration_min 受单次时长上限约束，下调到 {int(max_session_minutes)}")

        if "reps" in fields and isinstance(fields["reps"], str) and "-" in fields["reps"]:
            selected_reps = self._pick_range_value(fields["reps"], bias=bias)
            fields["reps"] = selected_reps
            adjustments.append(f"reps 按 {bias} 档位取值为 {selected_reps}")

        if "surface" in fields:
            options = [item.strip() for item in str(fields["surface"]).split("|") if item.strip()]
            if terrain_preferences:
                matched = [item for item in options if item in terrain_preferences]
                if matched:
                    fields["surface"] = matched[0]
                    adjustments.append(f"surface 按场地偏好匹配为 {matched[0]}")
                elif options:
                    fields["surface"] = options[0]
            elif options:
                fields["surface"] = options[0]

        return fields, adjustments

    def _evaluate_constraints(
        self,
        workout_label: str,
        template_id: str,
        parameters: Dict[str, Any],
        athlete_profile: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
        constraint_reports: List[Dict[str, Any]] = []
        warnings: List[str] = []
        adjustments: List[str] = []
        is_quality = workout_label in QUALITY_WORKOUT_LABELS

        for constraint in self.get_constraints_for_template(template_id):
            constraint_id = constraint["constraint_id"]
            status = "ok"
            message = "约束满足或当前上下文不足以触发。"

            if constraint_id == "c_quality_sessions_weekly_cap":
                current = int(context.get("quality_sessions_this_week", 0) or 0)
                projected = current + (1 if is_quality else 0)
                if projected > 2:
                    status = "violated"
                    message = f"本周质量课预计达到 {projected} 次，超过上限 2 次。"
                    warnings.append(message)
            elif constraint_id == "c_quality_gap_48h":
                hours = self._safe_float(context.get("last_quality_hours_ago"))
                if is_quality and hours is not None and hours < 48:
                    status = "violated"
                    message = f"距离上一次质量课仅 {int(hours)} 小时，未满足至少 48 小时间隔。"
                    warnings.append(message)
            elif constraint_id == "c_long_run_weekly_cap":
                current = int(context.get("long_runs_this_week", 0) or 0)
                if workout_label in {"长距离", "长距离有氧"} and current + 1 > 1:
                    status = "violated"
                    message = "本周已存在长距离训练，再安排将超过每周 1 次上限。"
                    warnings.append(message)
            elif constraint_id == "c_long_run_duration_cap":
                max_session_minutes = self._safe_float(athlete_profile.get("max_session_minutes"))
                duration_value = self._safe_float(parameters.get("duration_min"))
                if max_session_minutes is not None and duration_value is not None and duration_value > max_session_minutes:
                    parameters["duration_min"] = str(int(max_session_minutes))
                    status = "adjusted"
                    message = f"长距离时长从 {int(duration_value)} 下调到 {int(max_session_minutes)} 分钟。"
                    adjustments.append(message)
            elif constraint_id == "c_easy_after_quality":
                prev_quality = bool(context.get("previous_day_was_quality"))
                if prev_quality and workout_label not in RECOVERY_WORKOUT_LABELS:
                    status = "violated"
                    message = "前一日为质量课，当前建议应为轻松跑、恢复跑或休息。"
                    warnings.append(message)

            constraint_reports.append({
                "constraint_id": constraint_id,
                "label": constraint.get("label", constraint_id),
                "rule": constraint.get("rule", ""),
                "status": status,
                "message": message,
            })

        return constraint_reports, warnings, adjustments

    def decide_workout_draft(
        self,
        workout_label: str,
        athlete_profile: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        athlete_profile = athlete_profile or {}
        context = context or {}
        templates = self.get_templates_for_workout(workout_label)

        if not templates:
            return {
                "status": "no_template",
                "workout_label": workout_label,
                "message": f"未找到 `{workout_label}` 对应的模板。",
                "template": None,
                "parameters": {},
                "constraints": [],
                "warnings": [f"workout `{workout_label}` 尚未注册到 template registry"],
            }

        template = templates[0]
        parameters, adjustments = self._apply_profile_to_template(template, athlete_profile)
        constraint_reports, warnings, constraint_adjustments = self._evaluate_constraints(
            workout_label=workout_label,
            template_id=template["template_id"],
            parameters=parameters,
            athlete_profile=athlete_profile,
            context=context,
        )
        adjustments.extend(constraint_adjustments)

        violated = [item for item in constraint_reports if item["status"] == "violated"]
        adjusted = [item for item in constraint_reports if item["status"] == "adjusted"]
        status = "ready"
        if violated:
            status = "blocked"
        elif adjusted:
            status = "adjusted"

        return {
            "status": status,
            "workout_label": workout_label,
            "template_id": template["template_id"],
            "template_label": template.get("label", ""),
            "zone_label": template.get("zone_label", ""),
            "physiology_targets": list(template.get("physiology_targets", [])),
            "adaptation_targets": list(template.get("adaptation_targets", [])),
            "parameters": parameters,
            "constraints": constraint_reports,
            "adjustments": adjustments,
            "warnings": warnings,
            "context_used": copy.deepcopy(context),
        }

    def _is_quality_workout(self, workout_label: str) -> bool:
        return str(workout_label or "").strip() in QUALITY_WORKOUT_LABELS

    def _is_long_run_workout(self, workout_label: str) -> bool:
        return "长距离" in str(workout_label or "").strip()

    def _build_week_planner_context(
        self,
        week_state: Dict[str, Any],
        day_index: int,
        day_label: str,
    ) -> Dict[str, Any]:
        last_quality_index = week_state.get("last_quality_index")
        last_quality_hours_ago = None
        if last_quality_index is not None and day_index > last_quality_index:
            last_quality_hours_ago = (day_index - last_quality_index) * 24

        history = copy.deepcopy(week_state.get("history", []))
        previous_day = history[-1] if history else {}
        previous_day_type = str(previous_day.get("type", "") or "").strip()

        return {
            "current_day": day_label,
            "day_index": day_index,
            "week_history": history,
            "quality_count": int(week_state.get("quality_sessions", 0) or 0),
            "quality_sessions_this_week": int(week_state.get("quality_sessions", 0) or 0),
            "last_quality_day": week_state.get("last_quality_day"),
            "last_quality_index": last_quality_index,
            "last_quality_hours_ago": last_quality_hours_ago,
            "long_run_done": bool(week_state.get("long_run_done", False)),
            "long_runs_this_week": 1 if week_state.get("long_run_done") else 0,
            "long_run_day": week_state.get("long_run_day"),
            "previous_day_type": previous_day_type,
            "previous_day_was_quality": self._is_quality_workout(previous_day_type),
            "previous_day_was_long_run": self._is_long_run_workout(previous_day_type),
            "blocked_count": int(week_state.get("blocked_count", 0) or 0),
        }

    def _evaluate_week_level_rules(
        self,
        workout_label: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        violations: List[Dict[str, str]] = []
        is_quality = self._is_quality_workout(workout_label)
        is_long_run = self._is_long_run_workout(workout_label)

        if is_quality and int(context.get("quality_sessions_this_week", 0) or 0) >= 2:
            violations.append({
                "constraint_id": "planner_quality_sessions_weekly_cap",
                "label": "周级调度器: 质量课总量上限",
                "rule": "quality_sessions_per_week <= 2",
                "message": "本周已安排 2 次质量课，当前训练需降级为低强度或休息。",
            })

        hours = self._safe_float(context.get("last_quality_hours_ago"))
        if is_quality and hours is not None and hours < 48:
            violations.append({
                "constraint_id": "planner_quality_gap_48h",
                "label": "周级调度器: 高强度间隔约束",
                "rule": "quality_gap_hours >= 48",
                "message": f"距离上一次质量课仅 {int(hours)} 小时，当前训练需改为恢复类安排。",
            })

        if is_long_run and bool(context.get("long_run_done", False)):
            violations.append({
                "constraint_id": "planner_long_run_weekly_cap",
                "label": "周级调度器: 长距离周上限",
                "rule": "long_runs_per_week <= 1",
                "message": "本周已存在长距离训练，当前长距离请求将被阻断。",
            })

        if is_long_run and bool(context.get("previous_day_was_quality", False)):
            violations.append({
                "constraint_id": "planner_long_run_before_easy_only",
                "label": "周级调度器: 长距离前一天约束",
                "rule": "day_before_long_run in recovery",
                "message": "长距离前一天不能安排质量课，当前训练需回退为轻松跑/恢复跑/休息。",
            })

        if bool(context.get("previous_day_was_long_run", False)) and workout_label not in RECOVERY_WORKOUT_LABELS:
            violations.append({
                "constraint_id": "planner_recovery_after_long_run",
                "label": "周级调度器: 长距离次日恢复约束",
                "rule": "day_after_long_run in recovery",
                "message": "长距离次日应安排恢复性训练或休息，当前训练需降级。",
            })

        return violations

    def _attach_week_rule_violations(
        self,
        draft: Dict[str, Any],
        violations: List[Dict[str, str]],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        blocked_draft = copy.deepcopy(draft)
        blocked_draft["status"] = "blocked"
        blocked_draft["warnings"] = list(blocked_draft.get("warnings", []))
        blocked_draft["constraints"] = list(blocked_draft.get("constraints", []))
        for item in violations:
            blocked_draft["warnings"].append(item["message"])
            blocked_draft["constraints"].append({
                "constraint_id": item["constraint_id"],
                "label": item["label"],
                "rule": item["rule"],
                "status": "violated",
                "message": item["message"],
            })
        blocked_draft["context_used"] = copy.deepcopy(context)
        return blocked_draft

    def _build_rest_day_draft(
        self,
        context: Dict[str, Any],
        reasons: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return {
            "status": "adjusted",
            "workout_label": "休息",
            "template_id": "",
            "template_label": "rest_day_fallback",
            "zone_label": "Z1",
            "physiology_targets": [],
            "adaptation_targets": ["恢复"],
            "parameters": {},
            "constraints": [],
            "adjustments": list(reasons or []),
            "warnings": [],
            "context_used": copy.deepcopy(context),
        }

    def _update_week_state(
        self,
        week_state: Dict[str, Any],
        day_index: int,
        day_label: str,
        selected_type: str,
        draft: Dict[str, Any],
    ) -> Dict[str, Any]:
        next_state = copy.deepcopy(week_state)
        status = str(draft.get("status", "") or "").strip()
        if status == "blocked":
            next_state["blocked_count"] = int(next_state.get("blocked_count", 0) or 0) + 1

        history = list(next_state.get("history", []))
        history.append({
            "day": day_label,
            "type": selected_type,
            "status": status or "ready",
            "zone_label": str(draft.get("zone_label", "") or "").strip(),
        })
        next_state["history"] = history

        if self._is_quality_workout(selected_type):
            next_state["quality_sessions"] = int(next_state.get("quality_sessions", 0) or 0) + 1
            next_state["last_quality_day"] = day_label
            next_state["last_quality_index"] = day_index

        if self._is_long_run_workout(selected_type):
            next_state["long_run_done"] = True
            next_state["long_run_day"] = day_label

        return next_state

    def plan_week_drafts(
        self,
        week_skeleton: List[Dict[str, Any]],
        athlete_profile: Optional[Dict[str, Any]] = None,
        fallback_workouts: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        athlete_profile = athlete_profile or {}
        fallbacks = fallback_workouts or WEEK_FALLBACK_WORKOUTS
        week_state: Dict[str, Any] = {
            "quality_sessions": 0,
            "last_quality_day": None,
            "last_quality_index": None,
            "long_run_done": False,
            "long_run_day": None,
            "blocked_count": 0,
            "history": [],
        }
        week_plan: List[Dict[str, Any]] = []

        for day_index, item in enumerate(week_skeleton or []):
            day_label = str((item or {}).get("day", "") or f"Day{day_index + 1}").strip()
            requested_type = str((item or {}).get("type", "") or "休息").strip() or "休息"
            base_context = self._build_week_planner_context(week_state, day_index, day_label)
            decision_trace: List[Dict[str, Any]] = []

            if requested_type in {"休息", "Rest", "rest"}:
                draft = self._build_rest_day_draft(base_context, reasons=[])
                selected_type = "休息"
            else:
                selected_type = requested_type
                draft: Optional[Dict[str, Any]] = None
                candidates = [requested_type] + [alt for alt in fallbacks if alt != requested_type]

                for candidate in candidates:
                    decision_context = self._build_week_planner_context(week_state, day_index, day_label)
                    candidate_draft = self.decide_workout_draft(
                        workout_label=candidate,
                        athlete_profile=athlete_profile,
                        context=decision_context,
                    )
                    planner_violations = self._evaluate_week_level_rules(candidate, decision_context)
                    if planner_violations:
                        candidate_draft = self._attach_week_rule_violations(
                            candidate_draft,
                            planner_violations,
                            decision_context,
                        )

                    decision_trace.append({
                        "requested": candidate,
                        "status": candidate_draft.get("status", "unknown"),
                        "warnings": list(candidate_draft.get("warnings", [])),
                    })

                    has_runnable_template = bool(candidate_draft.get("template_id")) or candidate == "休息"
                    if candidate_draft.get("status") != "blocked" and has_runnable_template:
                        selected_type = candidate
                        draft = candidate_draft
                        break

                    if draft is None:
                        draft = candidate_draft

                if draft is None or draft.get("status") == "blocked":
                    fallback_reason = [
                        f"原始请求 `{requested_type}` 在周级约束下不可执行，自动降级为休息。"
                    ]
                    if draft:
                        fallback_reason.extend(list(draft.get("warnings", [])))
                    draft = self._build_rest_day_draft(base_context, reasons=fallback_reason)
                    selected_type = "休息"
                    decision_trace.append({
                        "requested": "休息",
                        "status": draft.get("status", "adjusted"),
                        "warnings": list(draft.get("warnings", [])),
                    })

                if selected_type != requested_type:
                    draft["status"] = "adjusted"
                    draft["adjustments"] = list(draft.get("adjustments", []))
                    draft["adjustments"].append(
                        f"训练类型从 `{requested_type}` 调整为 `{selected_type}` 以满足周级约束。"
                    )

            week_state_before = self._build_week_planner_context(week_state, day_index, day_label)
            week_state = self._update_week_state(week_state, day_index, day_label, selected_type, draft)
            week_state_after = self._build_week_planner_context(week_state, day_index, day_label)

            draft["decision_trace"] = copy.deepcopy(decision_trace)
            draft["week_state_before"] = week_state_before
            draft["week_state_after"] = week_state_after
            draft["context_used"] = copy.deepcopy(week_state_before)

            week_plan.append({
                "day": day_label,
                "type": selected_type,
                "requested_type": requested_type,
                "draft": draft,
                "status": draft.get("status", "ready"),
            })

        return week_plan

    def _migrate_graph_schema(self) -> bool:
        changed = False

        for node in self.nodes.values():
            if "type" not in node or not node.get("type"):
                node["type"] = self.classify_entity(node.get("label", ""))
                changed = True
            if "source_chunks" not in node or not isinstance(node.get("source_chunks"), list):
                node["source_chunks"] = list(node.get("source_chunks") or [])
                changed = True

        for edge in self.edges:
            source_node = self.nodes.get(edge.get("source", ""), {})
            target_node = self.nodes.get(edge.get("target", ""), {})
            head_type = source_node.get("type")
            tail_type = target_node.get("type")

            if not edge.get("canonical_relation"):
                edge["canonical_relation"] = self.map_relation(
                    edge.get("relation", ""),
                    head_type=head_type,
                    tail_type=tail_type,
                )
                changed = True

            if not isinstance(edge.get("evidence"), dict):
                source_chunks = source_node.get("source_chunks", [])
                target_chunks = target_node.get("source_chunks", [])
                shared_chunks = [cid for cid in source_chunks if cid in set(target_chunks)]
                chunk_id = (shared_chunks[0] if shared_chunks else (source_chunks[0] if source_chunks else "")) or ""
                edge["evidence"] = self._build_edge_evidence(
                    source_id=chunk_id,
                    text_span="Recovered from legacy graph edge.",
                    source_name="legacy_graph",
                    confidence=0.3,
                )
                changed = True

        return changed

    async def extract_triples(self, text: str, chunk_id: str, allow_llm: bool = False) -> List[List[str]]:
        """使用 LLM 从文本中提取 [实体1, 关系, 实体2] 三元组"""
        if self.STRICT_MODE and not allow_llm:
            logger.info(f"[graph_engine] STRICT_MODE 开启，拦截 LLM 三元组提取 ({chunk_id})")
            return []
        
        prompt = f"""你是一个专业的知识图谱构建专家。请从以下文本中提取关键的实体（名词）及其相互关系。

提取要求：
1. 识别文本中的核心概念、人物、组织、方法、技术、指标或任何重要实体。
2. 将它们表示为简洁的三元组格式：[实体1, 关系, 实体2]。
3. 关系应该是简短的动词或描述性短语（例如：“位于”、“属于”、“提高”、“导致”、“包含”、“研究”）。
4. **必须且仅**输出一个标准的 JSON 数组。
5. 如果文本中没有任何有价值的关系，请返回空数组 []。
6. 不要输出任何解释文字，不要包含 Markdown 代码块标签。

【示例】
输入文本： 高强度间歇训练（HIIT）可以显著提高运动员的最大摄氧量（VO2 max）。这项技术被国家田径队广泛采用。
输出JSON： [["高强度间歇训练", "提高", "最大摄氧量"], ["国家田径队", "采用", "高强度间歇训练"]]

待处理文本：
{text}

JSON 输出："""
        
        try:
            response = await asyncio.wait_for(_get_llm().ainvoke([HumanMessage(content=prompt)]), timeout=120.0)
            content = response.content.strip()
            
            # 清理包装
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            content = content.strip()
            
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    valid = [t for t in data if isinstance(t, list) and len(t) >= 3]
                    if valid: return valid
            # 仅捕获 JSON 解析错误走正则兜底；放过 KeyboardInterrupt 等系统异常
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

            # 正则兜底
            fallback_matches = re.findall(r'\[\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\]', content)
            if fallback_matches:
                return [list(m) for m in fallback_matches]
            
            fallback_matches_tuple = re.findall(r'\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^,]+)\s*\)', content)
            if fallback_matches_tuple:
                return [[i.strip().strip('"').strip("'") for i in m] for m in fallback_matches_tuple]

        except asyncio.TimeoutError:
            logger.warning(f"提取超时 ({chunk_id})")
            return None 
        except Exception as e:
            logger.error(f"提取三元组失败 ({chunk_id}): {e}")
            return None 
        return [] 

    def _add_triple(self, sub: str, pred: str, obj: str, source_id: str, evidence: Optional[Dict[str, Any]] = None):
        """将单个三元组添加到内存图谱中"""
        self._upsert_edge(
            sub,
            obj,
            str(pred),
            source_id=source_id,
            evidence=evidence,
        )

    async def build_graph(self, chunks: List[Dict[str, Any]], progress_callback=None, incremental: bool = True):
        """遍历分片构建图谱"""
        if not incremental:
            logger.info("正在进行全量构建，清除现有图谱数据...")
            self.nodes = {}
            self.edges = []
            self.processed_chunks = {}
        
        if not chunks:
            logger.warning("传入的 chunks 为空，无法构建图谱")
            return len(self.nodes), len(self.edges)

        # 过滤已处理的分片
        new_chunks = []
        for c in chunks:
            cid = c["chunk_id"]
            text = c.get("text", "")
            text_hash = hashlib.md5(text.encode()).hexdigest()
            
            existing = self.processed_chunks.get(cid)
            # 兼容旧版纯哈希字符串和新版字典元数据
            existing_hash = existing.get("hash") if isinstance(existing, dict) else existing
            
            if cid not in self.processed_chunks or existing_hash != text_hash:
                new_chunks.append((c, text_hash))
        
        if not new_chunks:
            logger.info("所有分片均已处理且内容无变化，无需更新图谱。")
            return len(self.nodes), len(self.edges)

        # 顺序处理新分片 (不再进行首中尾抽样，确保覆盖的连续性)
        BATCH_SIZE = 100 # 每轮处理上限，可根据 LLM 速率调整
        if len(new_chunks) <= BATCH_SIZE:
            process_items = new_chunks
        else:
            process_items = new_chunks[:BATCH_SIZE]
            
        total = len(process_items)
        pending_total = len(new_chunks)
        logger.info(f"开始构建图谱 (增量: {incremental})，本轮处理前 {total} 个新分片 (剩余待处理: {pending_total - total})...")
        
        extracted_count = 0
        for i, (chunk, text_hash) in enumerate(process_items):
            triples = await self.extract_triples(chunk["text"], chunk["chunk_id"], allow_llm=True)
            
            if triples is not None:
                extracted_count += len(triples)
                if triples:
                    logger.info(f"[{i+1}/{total}] 成功从 {chunk['chunk_id']} 提取 {len(triples)} 条三元组 (累计: {extracted_count})")
                
                # 记录详细元数据以便追溯提取有限性
                self.processed_chunks[chunk["chunk_id"]] = {
                    "hash": text_hash,
                    "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "success",
                    "triples_count": len(triples)
                }
                for triple in triples:
                    if not isinstance(triple, list) or len(triple) < 3:
                        continue
                    evidence = self._build_edge_evidence(
                        source_id=chunk["chunk_id"],
                        text_span=chunk.get("text", ""),
                        source_name=chunk.get("source_file") or chunk.get("source") or "unknown",
                        confidence=0.82,
                    )
                    self._add_triple(triple[0], triple[1], triple[2], chunk["chunk_id"], evidence=evidence)
            else:
                logger.warning(f"[{i+1}/{total}] {chunk['chunk_id']} 提取失败，跳过标记以待下次重试")
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        self.save_graph()
        logger.info(f"图谱构建完毕：{len(self.nodes)} 节点, {len(self.edges)} 边")
        return len(self.nodes), len(self.edges)

    async def add_multimodal_description(self, description: str, source_id: str):
        """将多模态描述注入图谱"""
        logger.info(f"开始处理多模态描述，来源: {source_id}")
        triples = await self.extract_triples(description, source_id, allow_llm=True)
        if triples:
            for triple in triples:
                if not isinstance(triple, list) or len(triple) < 3:
                    continue
                evidence = self._build_edge_evidence(
                    source_id=source_id,
                    text_span=description,
                    source_name=source_id,
                    confidence=0.6,
                )
                self._add_triple(triple[0], triple[1], triple[2], source_id, evidence=evidence)
            self.save_graph()
            logger.info(f"多模态描述注入完毕，成功提取 {len(triples)} 条三元组")
            return len(triples)
        return 0

    def search_graph(self, query_entities: List[str], max_hops: int = 2) -> Dict[str, Any]:
        """图谱搜索：基于查询实体进行多跳推理"""
        if not self.nodes:
            return {"nodes": {}, "edges": []}
            
        related_node_ids = set()
        related_edges = []
        
        seeds = [e.lower().strip() for e in query_entities]
        current_level = []
        
        for s in seeds:
            for node_id, node_info in self.nodes.items():
                label = node_info["label"].lower()
                if s in label or label in s:
                    current_level.append(node_id)
        
        current_level = list(set(current_level))
        
        for hop in range(max_hops):
            next_level = []
            for node_id in current_level:
                related_node_ids.add(node_id)
                for edge in self.edges:
                    s_id = edge["source"]
                    t_id = edge["target"]
                    if s_id == node_id and t_id not in related_node_ids:
                        related_edges.append(edge)
                        next_level.append(t_id)
                    elif t_id == node_id and s_id not in related_node_ids:
                        related_edges.append(edge)
                        next_level.append(s_id)
            current_level = list(set(next_level))
            if not current_level:
                break
        
        related_node_ids.update(current_level)
        for edge in related_edges:
            related_node_ids.add(edge["source"])
            related_node_ids.add(edge["target"])
                
        final_nodes = {}
        for nid in related_node_ids:
            if nid in self.nodes:
                label = self.nodes[nid].get("label", "")
                if label and not self._is_id(label) and not self._is_metadata(label):
                    final_nodes[nid] = self.nodes[nid]

        return {
            "nodes": final_nodes,
            "edges": [e for e in related_edges if e["source"] in final_nodes and e["target"] in final_nodes]
        }

    def generate_mermaid(self, nodes: Dict = None, edges: List = None, limit: int = 50, highlight_phrases: List[str] = None) -> str:
        """生成 Mermaid 代码用于可视化"""
        if nodes is None and edges is None and limit == 50:
            current_key = f"{len(self.nodes)}_{len(self.edges)}_{hash(tuple(highlight_phrases or []))}"
            if self._mermaid_cache and self._cache_key == current_key:
                return self._mermaid_cache
            
        target_nodes = nodes if nodes is not None else self.nodes
        target_edges = edges if edges is not None else self.edges
        
        if not target_nodes:
            return "flowchart TD\n  Empty[知识图谱为空，请先构建]"
        
        mermaid = "flowchart LR\n"
        mermaid += "    %% 样式定义\n"
        mermaid += "    classDef entity fill:#e1f5fe,stroke:#01579b,stroke-width:2.5px,color:#000,font-weight:bold;\n"
        mermaid += "    classDef highlight fill:#fff9c4,stroke:#fbc02d,stroke-width:3px,color:#000,font-weight:bold;\n"
        
        display_edges = target_edges[:limit]
        added_nodes = set()
        
        def clean_label(l):
            l = str(l)
            l = re.sub(r'[^\w\s\u4e00-\u9fa5\.\-\(\)]', '', l)
            return l.strip()

        def word_wrap(text, width=25):
            if len(text) <= width: return text
            words = text.split()
            lines = []
            current_line = []
            current_length = 0
            for word in words:
                if current_length + len(word) > width:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                    current_length = len(word)
                else:
                    current_line.append(word)
                    current_length += len(word) + 1
            if current_line:
                lines.append(" ".join(current_line))
            return "<br/>".join(lines)

        def check_highlight(text):
            phrases = highlight_phrases or []
            for phrase in phrases:
                if phrase.lower() in text.lower():
                    return True
            return False

        for edge in display_edges:
            s_id = str(edge.get("source", "")).strip()
            t_id = str(edge.get("target", "")).strip()
            
            if not s_id or not t_id:
                continue
                
            s_raw_label = target_nodes.get(s_id, {}).get("label")
            t_raw_label = target_nodes.get(t_id, {}).get("label")
            
            if not s_raw_label or not t_raw_label or self._is_id(s_raw_label) or self._is_id(t_raw_label) or self._is_metadata(s_raw_label) or self._is_metadata(t_raw_label):
                continue
                
            s_label_clean = clean_label(s_raw_label)
            t_label_clean = clean_label(t_raw_label)
            
            s_high = check_highlight(s_label_clean)
            t_high = check_highlight(t_label_clean)
            
            s_label = word_wrap(s_label_clean)
            t_label = word_wrap(t_label_clean)
            
            relation_raw = edge.get("relation", "related")
            relation = word_wrap(clean_label(relation_raw), width=20)
            
            if not s_label or not t_label:
                continue

            s_m_id = "N" + hashlib.md5(s_id.encode()).hexdigest()[:8]
            t_m_id = "N" + hashlib.md5(t_id.encode()).hexdigest()[:8]
            
            if s_m_id not in added_nodes:
                mermaid += f'    {s_m_id}["{s_label}"]\n'
                mermaid += f'    class {s_m_id} {"highlight" if s_high else "entity"}\n'
                added_nodes.add(s_m_id)
            if t_m_id not in added_nodes:
                mermaid += f'    {t_m_id}["{t_label}"]\n'
                mermaid += f'    class {t_m_id} {"highlight" if t_high else "entity"}\n'
                added_nodes.add(t_m_id)
                
            mermaid += f'    {s_m_id} -- "{relation}" --> {t_m_id}\n'
            
        if not added_nodes and nodes:
             for nid, ninfo in nodes.items():
                 m_id = "N" + hashlib.md5(nid.encode()).hexdigest()[:8]
                 label = word_wrap(clean_label(ninfo.get("label", nid)))
                 mermaid += f'    {m_id}["{label}"]\n'
                 mermaid += f'    class {m_id} entity\n'
        
        if not added_nodes:
            res = "flowchart TD\n  Empty[暂无有效的图谱关系]"
        else:
            res = mermaid
            
        if nodes is None and edges is None and limit == 50:
            self._mermaid_cache = res
            self._cache_key = current_key
            
        return res

def _node_type_for_entity(entity: str, expert_domain: str) -> str:
    """根据实体文本和领域推断 KG 节点类型。

    检查顺序按特异性从高到低排列，避免通用词（如"阈值"）先被 workout 匹配。
    """
    lowered = entity.lower()
    # 伤病/康复 — 先于 workout，因为"恢复跑"也含"恢复"
    rehab_keywords = ["疼痛", "pain", "伤病", "injury", "康复", "rehab",
                      "炎症", "inflammation", "骨折", "fracture", "拉伤", "strain",
                      "跟腱", "achilles", "足底", "plantar", "膝", "knee"]
    if any(kw in lowered for kw in rehab_keywords):
        return "injury"
    # 营养
    nutrition_keywords = ["碳水", "carb", "蛋白", "protein",
                          "补给", "fuel", "水合", "hydration", "电解质", "electrolyte",
                          "能量", "energy", "补剂", "supplement", "糖原", "glycogen"]
    if any(kw in lowered for kw in nutrition_keywords):
        return "nutrition"
    # 生理指标 — 先于 workout，因为"乳酸阈值"是生理概念不是训练课
    phys_keywords = ["心率", "heart_rate", "vo2max", "vo2", "乳酸", "lactate",
                     "配速", "pace", "步频", "cadence", "步幅", "stride",
                     "摄氧量", "代谢", "metabolism", "脂肪", "fat_oxidation"]
    if any(kw in lowered for kw in phys_keywords):
        return "physiology"
    # 训练类型实体
    workout_keywords = ["跑", "run", "jog", "间歇", "节奏", "tempo", "长距离", "lsd",
                        "恢复", "recovery", "轻松", "easy", "冲刺", "sprint",
                        "重复", "repetition", "法特莱克", "fartlek"]
    if any(kw in lowered for kw in workout_keywords):
        return "workout"
    # 概念/策略
    return "concept"


def _infer_bridge_type(head: str, tail: str, domain: str) -> str:
    """推断跨领域桥接边的类型。"""
    lowered_head = head.lower()
    lowered_tail = tail.lower()
    risk_keywords = ["疼痛", "pain", "伤病", "injury", "疲劳", "fatigue",
                     "风险", "risk", "红旗", "red_flag"]
    if any(kw in lowered_head for kw in risk_keywords) or any(kw in lowered_tail for kw in risk_keywords):
        return "causal"
    constraint_keywords = ["容量", "volume", "强度", "intensity", "上限", "cap",
                           "限制", "limit", "不能", "cannot"]
    if any(kw in lowered_head for kw in constraint_keywords) or any(kw in lowered_tail for kw in constraint_keywords):
        return "constraint"
    handoff_keywords = ["补给", "fuel", "营养", "nutrition", "恢复", "recovery",
                        "策略", "strategy", "比赛", "race"]
    if any(kw in lowered_head for kw in handoff_keywords) or any(kw in lowered_tail for kw in handoff_keywords):
        return "handoff"
    return "dependency"


def _rewrite_queue_status(queue_path: str | Path) -> None:
    """回写候选队列，更新已合并候选的状态。"""
    import json as _json
    from pathlib import Path as _Path

    qp = _Path(queue_path)
    if not qp.exists():
        return
    lines = qp.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            entry = _json.loads(line)
        except _json.JSONDecodeError:
            updated.append(line)
            continue
        if entry.get("status") == "merged":
            updated.append(_json.dumps(entry, ensure_ascii=False))
        else:
            updated.append(line.strip())
    qp.write_text("\n".join(updated) + "\n", encoding="utf-8")


graph_engine = GraphEngine()


def graph_runtime_health(
    vector_health: Optional[Dict[str, Any]] = None,
    graph_engine_instance: Optional[GraphEngine] = None,
) -> Dict[str, Any]:
    engine = graph_engine_instance or graph_engine
    graph_path = Path(getattr(engine, "GRAPH_DATA_PATH", GRAPH_DATA_PATH))
    graph_dir = graph_path.parent
    graph_source = _graph_source_label(graph_dir)
    vector_payload = dict(vector_health or {})
    vector_dir_raw = str(vector_payload.get("vector_dir") or "")
    vector_dir = Path(vector_dir_raw) if vector_dir_raw else V2_VECTOR_DIR
    vector_source = str(vector_payload.get("source") or _graph_source_label(vector_dir))
    graph_ready = bool(getattr(engine, "nodes", {}) or graph_path.exists())
    source_aligned = _safe_resolve(graph_dir) == _safe_resolve(vector_dir)
    reason = ""
    if not source_aligned:
        reason = f"graph_source_mismatch:{graph_source}!={vector_source}"
    elif not graph_ready:
        reason = "graph_unavailable"
    graph_fusion_enabled = source_aligned and graph_ready
    return {
        "graph_path": str(graph_path),
        "graph_source": graph_source,
        "vector_source": vector_source,
        "graph_ready": graph_ready,
        "graph_vector_source_aligned": source_aligned,
        "graph_fusion_enabled": graph_fusion_enabled,
        "reason": reason,
    }


def plan_week_drafts(
    week_skeleton: List[Dict[str, Any]],
    athlete_profile: Optional[Dict[str, Any]] = None,
    graph_engine_instance: Optional[GraphEngine] = None,
) -> List[Dict[str, Any]]:
    engine = graph_engine_instance or graph_engine
    return engine.plan_week_drafts(
        week_skeleton=week_skeleton,
        athlete_profile=athlete_profile,
    )
