import argparse
import hashlib
import json
import math
import os
import pickle
import re
import time
import shutil
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any, Tuple

# 配置日志
logger = logging.getLogger("vector_kb")

from marathon_qa_assistant.core.app_state import BASE_DIR, DATA_DIR, DEFAULT_VECTOR_DIR, LEGACY_DEFAULT_VECTOR_DIR, LEGACY_USER_VECTOR_DIR, RUNTIME_USER_VECTOR_DIR, USER_VECTOR_DIR, V2_VECTOR_DIR, LEGACY_UPLOAD_DOCS_DIR, UPLOAD_DOCS_DIR
from marathon_qa_assistant.core.settings import get_settings
from marathon_qa_assistant.services.document_preprocess import normalize_text
from marathon_qa_assistant.services.kb.health import summarize_runtime_index_schema
from marathon_qa_assistant.services.kb.runtime_quarantine import filter_quarantined_chunks

# 引入 LangChain 和 FAISS
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
LEGACY_RUNTIME_QUARANTINE_REPORT = DATA_DIR / "knowledge" / "governance" / "legacy_runtime_quarantine_report.json"
EVIDENCE_CHAIN_METADATA_KEYS = (
    "source_registry_id",
    "source_label",
    "source_url",
    "local_path",
    "section",
    "locator_hint",
    "page_hint",
    "paragraph_index",
    "char_start",
    "char_end",
    "text_span",
    "section_anchor",
    "paragraph_hash",
    "text_span_hash",
    "language",
    "evidence_domain",
    "knowledge_layer",
    "domain_pack",
    "allowed_use",
    "prescription_permission",
    "quality_tier",
    "review_status",
    "exclude_from_training_generation",
    "needs_review",
    "display_mode",
    "why_retrieved",
    "score_breakdown",
    "retrieval_mode",
    "retrieval_status",
    "query_variant",
    "query_variants",
    "query_variant_count",
    "best_query_variant",
    "bilingual_match",
    "consensus_count",
    "confidence_level",
    "graph_relation_strength",
    "evidence_source_type",
    "decision_gate",
    "decision_gate_reason",
    "governance_conflict_id",
    "conflict_detected",
    "conflict_reason",
    "conflicting_sources",
    "can_write_core",
    "explanation_only",
    "keywords_zh",
    "keywords_en",
    "synonyms",
    "domain_terms",
    "parent_text",  # Parent-Child 检索：小块召回时附带的父级完整上下文
)


# 检索增强关键词映射
QUERY_HINTS = {
    "周期": "periodization block periodized training cycle macrocycle mesocycle",
    "营养": "nutrition marathon hydration carbohydrate fueling diet protein",
    "饮食": "diet nutrition food eating meal plan calorie",
    "补给": "fueling hydration carbohydrate electrolyte intake",
    "过度训练": "overtraining overreaching excessive loading fatigue injury",
    "伤": "injury recovery rehabilitation pain therapist orthopedic",
    "痛": "pain injury recovery rehabilitation therapist",
    "康复": "recovery rehabilitation injury physical therapy",
    "高温": "heat stress hot environment hydration safety thermal",
    "力量": "strength training resistance program gym weightlifting",
    "耐力": "endurance training aerobic running cardiovascular",
    "马拉松": "marathon running training plan race long distance",
    "配速": "pace speed velocity timing splits",
    "短跑": "sprint acceleration mechanics sprint technique stride frequency stride length arm swing ground contact start acceleration",
    "中长跑": "middle distance endurance event 800 1500 3000 race specific training aerobic anaerobic",
    "专项": "specificity event-specific race-specific training skill transfer not harming specialization",
    "安全": "safety risk warning caution advice health emergency",
    "风险": "risk danger safety hazard warning",
    "禁忌": "contraindication warning caution safety avoid",
    "知识库": "knowledge base scope domain expert area content coverage",
    "领域": "knowledge base scope domain expert area content coverage",
    "文档": "book document source reference literature paper pdf",
    "参考": "reference source bibliography citations documentation",
    "原则": "principle methodology theory fundamental framework guidelines",
    "减量": "taper tapering pre-race recovery glycogen supercompensation",
    "碳水加载": "carbohydrate loading glycogen supercompensation carb-loading pre-race",
    "赛前": "pre-race tapering carb-loading race preparation strategy",
    "生物力学": "biomechanics gait cycle foot strike running form kinematics",
    "步频": "cadence step frequency stride rate Heiderscheit running",
    "步幅": "stride length overstriding braking impulse running form",
    "触地": "foot strike landing pattern RFS MFS FFS ground contact",
    "跑姿": "running form technique posture gait biomechanics",
    "比赛策略": "race strategy pacing negative split execution marathon",
    "赛道": "race course pacing elevation grade terrain execution",
    "撞墙": "hitting the wall bonking glycogen depletion fatigue marathon",
    "热适应": "heat acclimation acclimatization thermal adaptation hot environment",
    "脱水": "dehydration hypohydration fluid balance hydration status",
    "电解质": "electrolyte sodium potassium hyponatremia hydration sports drink",
    "补水": "hydration fluid replacement drinking water electrolyte sports drink",
    "损伤预防": "injury prevention overuse tendinopathy stress fracture runner knee",
    "跑者膝": "runner knee patellofemoral PFPS iliotibial ITBS injury",
    "跟腱": "achilles tendon tendinopathy calf heel pain injury",
    "足底筋膜炎": "plantar fasciitis foot arch heel pain running injury",
    "跑鞋": "running shoe rotation footwear Malisoux cushioning drop",
    "降温": "cooling precooling ice slurry cold water immersion heat illness",
    "热射病": "heat stroke hyperthermia heat illness emergency exertional",
    "抽筋": "cramp muscle cramping electrolyte sodium hydration heat",
    # ── Task 2: 热身/力量/恢复权威文献检索增强 ──
    "拉伸": "stretching static dynamic flexibility warmup performance range of motion",
    "热身": "warmup stretching dynamic static pre-exercise preparation activation",
    "力量训练": "strength training resistance plyometric running economy endurance performance heavy load",
    "恢复策略": "recovery fatigue sleep cool-down post-exercise regeneration muscle damage soccer team sport glycogen",
    "恢复": "recovery fatigue glycogen muscle damage sleep regeneration post-exercise soccer cool-down nutrition hydration",
    "冷身": "cool-down recovery post-exercise warm-down gradual intensity reduction stretching",
    "睡眠": "sleep recovery regeneration circadian rhythm athlete performance fatigue",
    "运动处方": "exercise prescription FITT principle cardiorespiratory resistance flexibility periodization",
    "抗阻训练": "resistance training strength weightlifting load repetition running economy",
    "跑步经济性": "running economy oxygen consumption biomechanics efficiency strength training",
    "柔韧性": "flexibility stretching range of motion static dynamic proprioceptive neuromuscular",
    "疲劳恢复": "fatigue recovery muscle damage glycogen replenishment sleep regeneration post-exercise",
    "疲劳": "fatigue recovery muscle damage glycogen depletion sleep regeneration overtraining",
}

QUERY_VARIANT_HINTS = {
    "步行测试": "6-minute walk test",
    "周期化": "periodization periodized training macrocycle mesocycle",
    "训练周期": "training cycle periodization block",
    "减量": "taper tapering pre-race recovery",
    "配速": "pace pacing splits velocity",
    "补给": "fueling hydration carbohydrate electrolyte intake",
    "碳水加载": "carbohydrate loading glycogen supercompensation",
    "伤病": "injury pain rehabilitation overuse tendinopathy",
    "损伤": "injury prevention overuse tendinopathy stress fracture",
    "跑者膝": "runner knee patellofemoral pain syndrome PFPS",
    "跟腱": "achilles tendon tendinopathy calf heel pain",
    "足底筋膜炎": "plantar fasciitis heel pain foot arch",
    "热射病": "heat stroke exertional heat illness hyperthermia emergency",
    "乳酸阈": "lactate threshold threshold pace LT",
    "最大摄氧量": "VO2max maximal oxygen uptake aerobic power",
    "轻松跑": "easy run easy pace aerobic base",
    "节奏跑": "tempo run threshold run lactate threshold",
    "间歇": "interval training repetitions VO2max workout",
    "长距离": "long run endurance run marathon preparation",
    # ── Task 2: 热身/力量/恢复双语变体 ──
    "拉伸": "stretching static dynamic flexibility",
    "热身": "warmup pre-exercise preparation",
    "力量训练": "strength training resistance plyometric",
    "冷身": "cool-down warm-down post-exercise recovery",
    "恢复策略": "recovery strategy regeneration post-exercise",
    "睡眠": "sleep circadian recovery athlete",
    "运动处方": "exercise prescription FITT principle",
    "抗阻训练": "resistance training strength weightlifting",
    "跑步经济性": "running economy efficiency biomechanics",
    "柔韧性": "flexibility range of motion stretching",
    "疲劳恢复": "fatigue recovery muscle damage glycogen",
}

# 英文关键词 → 领域映射（模块级，避免每次调用 extract_semantic_terms 重复分配）
_ENGLISH_DOMAIN_MAP: dict[str, tuple[str, ...]] = {
    "nutrition": (
        "nutrition", "nutrient", "carbohydrate", "carb", "protein",
        "hydration", "electrolyte", "fueling", "glycogen", "dehydration",
        "diet", "supplement", "caffeine", "nitrate", "meal",
        "calcium", "zma", "glycerol", "hyperhydration", "intake",
        "omega-3", "omega 3", "dha", "epa", "fatty acid", "dosage",
        "calorie", "banana",
    ),
    "injury_safety": (
        "injury", "overtraining", "overreaching", "strain", "overuse",
        "tendon", "fracture", "bone stress", "plantar", "knee",
        "muscle damage", "fatigue", "risk factor", "addiction",
        "biomechanic", "tibial", "bsi", "return to run", "return-to-run",
    ),
    "medical_safety": (
        "renal", "heat stroke", "heat stress", "hyperthermia",
        "cardiac", "chest pain", "dizziness", "contraindication",
        "symptom", "ibuprofen", "headache", "cold", "illness",
        "hematological", "biomarker", "red-s", "ioc", "female athlete triad",
    ),
    "training_protocol": (
        "training", "endurance", "aerobic", "anaerobic", "vo2max",
        "lactate", "threshold", "periodization", "pace", "stride",
        "cadence", "biomechanics", "marathon", "half marathon",
        "interval", "tempo", "easy run", "long run", "taper",
        "workout", "repetition", "mental fatigue",
        "intensity zone", "intensity model", "norwegian",
        "acute", "chronic", "workload", "running economy",
        "runner", "running",
    ),
}


DEFAULT_TEST_QUESTIONS = [
    "如何定义并安排周期化训练以支持长期跑步表现提升？",
    "马拉松训练期如何进行营养与补给规划？",
    "过度训练常见风险信号有哪些，如何识别？",
    "高温环境下训练有哪些安全建议？",
    "力量训练与耐力训练如何在同一训练计划中平衡？",
]

EMBEDDING_MODEL = "nomic-embed-text:latest" # bge-m3 对某些文本返回 NaN，改用 nomic
EMBEDDING_CANDIDATE_MODELS = ("nomic-embed-text:latest", "bge-m3", "multilingual-e5")
SEMANTIC_CHUNKING_STRATEGY = "semantic_v2_sentence_window"  # v2：小块索引 + 句子窗口上下文

# Sentence Window 配置：小块负责精确召回，parent_text 负责为 LLM 提供完整上下文
SENTENCE_WINDOW_CHUNK_SIZE = 250   # 索引用小块，提高 embedding 区分度
SENTENCE_WINDOW_OVERLAP = 30       # 小块之间的小量重叠
SENTENCE_WINDOW_CONTEXT_CHARS = 600  # parent_text 前后扩展的字符数，约 3-5 句

# 分库检索：马拉松相关领域列表（external_reference 不参与默认检索）
MARATHON_DOMAIN_SHARDS = ("training_protocol", "nutrition", "injury_safety", "medical_safety")
ALL_DOMAIN_SHARDS = (*MARATHON_DOMAIN_SHARDS, "external_reference")

DOMAIN_PACK_TO_DOMAIN = {
    "endurance_training_protocols": "training_protocol",
    "training_protocols": "training_protocol",
    "training_load": "training_protocol",
    "strength_conditioning": "training_protocol",
    "mobility_recovery": "training_protocol",
    "environment_race_context": "training_protocol",
    "action_library": "training_protocol",
    "nutrition_hydration_race_fueling": "nutrition",
    "nutrition_race_fueling": "nutrition",
    "load_injury_safety": "injury_safety",
    "rehab_return_to_run": "injury_safety",
    "medical_risk": "medical_safety",
    "ai_rag_evidence_explanation": "external_reference",
    "hci_health_recommender_systems": "external_reference",
    "competitor_product_tasks": "external_reference",
    "user_profile_cases": "external_reference",
}


def _stable_anchor(value: Any, *, length: int = 16) -> str:
    normalized = " ".join(str(value or "").strip().lower().split())
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:length] if normalized else ""


def _chunk_anchor_metadata(source_registry_id: str, section: str, text: str) -> dict:
    return {
        "source_registry_id": source_registry_id,
        "section_anchor": _stable_anchor(section or "document_paragraph", length=12),
        "paragraph_hash": _stable_anchor(text, length=16),
        "text_span_hash": _stable_anchor(str(text or "")[:500], length=16),
    }


def _build_source_metadata(file_path: Path) -> dict:
    source_anchor = _stable_anchor(str(file_path.absolute()), length=12)
    return {
        "source_file": file_path.name,
        "source_path": str(file_path.absolute()),
        "source_registry_id": f"src_{source_anchor}" if source_anchor else "",
    }


def candidate_source_dirs() -> list[Path]:
    return [
        UPLOAD_DOCS_DIR,
        LEGACY_UPLOAD_DOCS_DIR,
        BASE_DIR / "domain_docs",
    ]


def infer_source_path(source_file: str) -> str:
    if not source_file or source_file == "unknown":
        return ""
    for candidate_dir in candidate_source_dirs():
        candidate_path = candidate_dir / source_file
        if candidate_path.exists():
            return str(candidate_path.absolute())
    return ""


def _normalize_chunk_source(chunk: dict) -> dict:
    normalized = dict(chunk)
    source_file = str(normalized.get("source_file", "") or "").strip()
    source_path = str(normalized.get("source_path", "") or "").strip()
    if not source_path and source_file:
        normalized["source_path"] = infer_source_path(source_file)
    return normalized

def _embedding_model_name() -> str:
    settings = get_settings()
    return str(getattr(settings, "embedding_model", "") or EMBEDDING_MODEL).strip() or EMBEDDING_MODEL


def get_embeddings(model: str | None = None):
    return OllamaEmbeddings(model=str(model or _embedding_model_name()), base_url=get_settings().ollama_base_url)


def _validate_embedding_vector(vector: Any, *, chunk_id: str = "") -> list[float]:
    values = list(vector or [])
    if not values:
        raise ValueError(f"empty embedding vector for chunk_id={chunk_id or 'unknown'}")
    bad = [value for value in values if not isinstance(value, (int, float)) or math.isnan(float(value)) or math.isinf(float(value))]
    if bad:
        raise ValueError(f"invalid embedding vector for chunk_id={chunk_id or 'unknown'}: contains NaN/Inf/non-numeric values")
    return [float(value) for value in values]


def _validate_embedding_model_on_sample(embeddings: Any, docs: list[Document]) -> dict:
    sample = docs[: min(3, len(docs))]
    report = {
        "embedding_model": _embedding_model_name(),
        "embedding_validation_sample_size": len(sample),
        "embedding_validation_errors": [],
    }
    for doc in sample:
        chunk_id = str((doc.metadata or {}).get("chunk_id") or "")
        try:
            vector = embeddings.embed_query(doc.page_content[:1000])
            _validate_embedding_vector(vector, chunk_id=chunk_id)
        except Exception as exc:
            report["embedding_validation_errors"].append({"chunk_id": chunk_id, "error": str(exc)})
    if report["embedding_validation_errors"]:
        raise ValueError(f"Embedding validation failed before FAISS build: {report}")
    return report


def _build_faiss_batched(docs: list[Document], embeddings: Any, batch_size: int = 64):
    """Build FAISS with batched embeddings to avoid one HTTP request per chunk.

    当批量嵌入因个别文本触发 NaN 而整体失败时，自动降级为逐条嵌入并跳过 NaN 片段。
    """
    if not docs:
        raise ValueError("Cannot build FAISS index from empty docs")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    text_embedding_pairs: list[tuple[str, list[float]]] = []
    metadatas: list[dict] = []
    ids: list[str] = []
    skipped_nan: list[str] = []
    for start in range(0, len(docs), batch_size):
        batch = docs[start : start + batch_size]
        texts = [str(doc.page_content or "") for doc in batch]
        if any(not text.strip() for text in texts):
            raise ValueError("Cannot batch embed empty document text")
        try:
            vectors = embeddings.embed_documents(texts)
            if len(vectors) != len(batch):
                raise ValueError(f"embed_documents returned {len(vectors)} vectors for {len(batch)} docs")
            # 批内逐条验证，遇 NaN 跳过
            for doc, text, vector in zip(batch, texts, vectors):
                chunk_id = str((doc.metadata or {}).get("chunk_id") or "")
                try:
                    validated = _validate_embedding_vector(vector, chunk_id=chunk_id)
                    text_embedding_pairs.append((text, validated))
                    metadatas.append(dict(doc.metadata or {}))
                    ids.append(chunk_id or f"doc_{len(ids):06d}")
                except ValueError:
                    skipped_nan.append(chunk_id)
        except Exception as batch_err:
            # 批量嵌入整体失败（如 BGE-M3 对某些 URL 文本返回 NaN 导致 Ollama 500）
            # 降级为逐条嵌入，跳过失败的片段
            logger.warning("批量嵌入失败 (batch %d-%d): %s，降级为逐条嵌入",
                           start, start + len(batch) - 1, batch_err)
            for doc, text in zip(batch, texts):
                chunk_id = str((doc.metadata or {}).get("chunk_id") or "")
                try:
                    vector = embeddings.embed_query(text)
                    validated = _validate_embedding_vector(vector, chunk_id=chunk_id)
                    text_embedding_pairs.append((text, validated))
                    metadatas.append(dict(doc.metadata or {}))
                    ids.append(chunk_id or f"doc_{len(ids):06d}")
                except Exception:
                    skipped_nan.append(chunk_id)
    if skipped_nan:
        logger.warning("跳过 %d 个 NaN 片段 (模型: %s): %s",
                       len(skipped_nan), _embedding_model_name(), skipped_nan[:20])
    if not text_embedding_pairs:
        raise ValueError(f"Cannot build FAISS index: all {len(docs)} documents produced NaN embeddings")
    return FAISS.from_embeddings(text_embedding_pairs, embeddings, metadatas=metadatas, ids=ids)


def _build_faiss(docs: list[Document], embeddings: Any):
    try:
        return _build_faiss_batched(docs, embeddings)
    except Exception as exc:
        logger.warning("批量构建 FAISS 失败，降级到 LangChain from_documents: %s", exc)
        return FAISS.from_documents(docs, embeddings)


def _strip_faiss_docstore_text(faiss_store: Any, placeholder: str = "") -> int:
    docstore_dict = getattr(getattr(faiss_store, "docstore", None), "_dict", None)
    if not isinstance(docstore_dict, dict):
        return 0
    stripped = 0
    for doc in docstore_dict.values():
        if isinstance(doc, Document) and doc.page_content != placeholder:
            doc.page_content = placeholder
            stripped += 1
    return stripped


def _build_chunk_text_cache(chunks: list[dict]) -> dict[str, str]:
    cache: dict[str, str] = {}
    for chunk in chunks or []:
        chunk_id = str(chunk.get("chunk_id") or "")
        if chunk_id:
            cache[chunk_id] = str(chunk.get("text") or "")
    return cache


def _attach_chunk_text_cache(faiss_store: Any, chunks: list[dict]) -> Any:
    if faiss_store is not None:
        setattr(faiss_store, "_chunk_text_cache", _build_chunk_text_cache(chunks))
    return faiss_store


def _load_chunk_text(chunk_id: str, chunks_cache: dict[str, str] | None) -> str:
    if not chunk_id or not chunks_cache:
        return ""
    return str(chunks_cache.get(str(chunk_id)) or "")

def extract_pdf_pages(file_path: Path) -> list[tuple[int, str]]:
    """提取 PDF 每一页的内容"""
    try:
        import fitz
    except Exception:
        fitz = None
    if fitz is not None:
        pages = []
        with fitz.open(file_path) as doc:
            for idx, page in enumerate(doc, start=1):
                page_text = page.get_text("text") or ""
                pages.append((idx, page_text))
        return pages
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError("未安装可用的 PDF 文本抽取库，请安装 PyMuPDF 或 pypdf") from exc
    reader = PdfReader(str(file_path))
    pages = []
    for idx, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        pages.append((idx, page_text))
    return pages

def extract_docx_text(file_path: Path) -> str:
    """提取 docx 文件内容"""
    try:
        from docx import Document
    except Exception as exc:
        raise RuntimeError("处理 docx 需要安装 python-docx") from exc
    document = Document(str(file_path))
    return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text)

def extract_image_text_sync(file_path: Path) -> str:
    """同步方式从图片中提取文字（OCR）"""
    import asyncio
    from marathon_qa_assistant.services.ocr_service import extract_text_from_image
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(lambda: asyncio.run(extract_text_from_image(str(file_path))))
                result = future.result(timeout=120)
        else:
            result = asyncio.run(extract_text_from_image(str(file_path)))
    except RuntimeError:
        result = asyncio.run(extract_text_from_image(str(file_path)))
    
    ocr_quality = result.get("ocr_quality", {})
    engine = result.get("engine", "unknown")
    text = result.get("text", "")
    
    if not text.strip():
        raise RuntimeError(f"图片未识别到有效文字 (引擎: {engine}, 评分: {ocr_quality.get('overall_score', 0)})")
    
    header = f"[OCR来源: {file_path.name} | 引擎: {engine} | 置信度: {ocr_quality.get('avg_confidence', 0):.2f}]\n"
    return header + text

def load_pages(file_path: Path) -> list[tuple[int, str]]:
    """根据扩展名加载文件页内容（支持文档和图片OCR）"""
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return extract_pdf_pages(file_path)
    if ext in {".txt", ".md"}:
        return [(1, file_path.read_text(encoding="utf-8", errors="ignore"))]
    if ext == ".docx":
        return [(1, extract_docx_text(file_path))]
    if ext in IMAGE_EXTENSIONS:
        return [(1, extract_image_text_sync(file_path))]
    raise ValueError(f"不支持的文件格式: {file_path.name}")

def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """将文本切分为分片"""
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap 不能小于 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须小于 chunk_size")
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = end - chunk_overlap
    return chunks


_SENTENCE_BOUNDARIES = [
    re.compile('。'),
    re.compile('\n\n'),
    re.compile('[，；]'),
    re.compile('[）》」]'),
]


def _find_best_split(text: str, chunk_size: int) -> int:
    if len(text) <= chunk_size:
        return len(text)
    window = text[:chunk_size]
    for pattern in _SENTENCE_BOUNDARIES:
        matches = list(pattern.finditer(window))
        if matches:
            return matches[-1].end()
    return chunk_size


def split_text_sentence_aware(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap 不能小于 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须小于 chunk_size")
    text = text.strip()
    if not text:
        return []
    chunks = []
    position = 0
    length = len(text)
    while position < length:
        remaining = text[position:]
        cut = _find_best_split(remaining, chunk_size)
        chunk = text[position:position + cut].strip()
        if chunk:
            chunks.append(chunk)
        if position + cut >= length:
            break
        position = position + cut - chunk_overlap
        if position < 0:
            position = 0
    return chunks


def normalize_query_text(text: str) -> str:
    """Normalize Chinese queries without changing user intent."""
    value = str(text or "")
    trans = str.maketrans(
        {
            "，": ",",
            "。": ".",
            "？": "?",
            "！": "!",
            "：": ":",
            "；": ";",
            "（": "(",
            "）": ")",
            "【": "[",
            "】": "]",
            "％": "%",
        }
    )
    value = value.translate(trans)
    value = re.sub(r"(\d+(?:\.\d+)?)\s*(公里|千米)", r"\1 km", value, flags=re.IGNORECASE)
    value = re.sub(r"(\d+(?:\.\d+)?)\s*(分钟|分)", r"\1 min", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _semantic_units(text: str) -> list[tuple[str, str]]:
    units: list[tuple[str, str]] = []
    current_title = ""
    buffer: list[str] = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            if buffer:
                units.append((current_title, "\n".join(buffer).strip()))
                buffer = []
            continue
        is_heading = bool(re.match(r"^(#{1,6}\s+|第[一二三四五六七八九十\d]+[章节]|[一二三四五六七八九十\d]+[、.]\s*)", line))
        if is_heading:
            if buffer:
                units.append((current_title, "\n".join(buffer).strip()))
                buffer = []
            current_title = line.lstrip("#").strip()
            buffer.append(line)
            continue
        buffer.append(line)
    if buffer:
        units.append((current_title, "\n".join(buffer).strip()))
    if not units and text.strip():
        units.append(("", text.strip()))
    return units


def split_text_semantic(text: str, chunk_size: int, chunk_overlap: int) -> list[dict]:
    """Split by headings/paragraphs first, then sentence-aware fallback for long units."""
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须小于 chunk_size 且不能为负")
    normalized = normalize_text(text).strip()
    if not normalized:
        return []

    chunks: list[dict] = []
    pending_title = ""
    pending_text = ""
    pending_start = 0
    paragraph_index = 0
    for title, unit in _semantic_units(normalized):
        unit = unit.strip()
        if not unit:
            continue
        paragraph_index += 1
        start = normalized.find(unit, pending_start)
        if start < 0:
            start = pending_start
        end = start + len(unit)
        pending_start = end

        if len(unit) > chunk_size:
            for part in split_text_sentence_aware(unit, chunk_size=chunk_size, chunk_overlap=chunk_overlap):
                part_start = normalized.find(part, start)
                if part_start < 0:
                    part_start = start
                chunks.append(
                    {
                        "text": part,
                        "section": title or "document_paragraph",
                        "paragraph_index": paragraph_index,
                        "char_start": part_start,
                        "char_end": part_start + len(part),
                        "text_span": part[:500],
                        "chunking_strategy": SEMANTIC_CHUNKING_STRATEGY,
                    }
                )
            pending_title = ""
            pending_text = ""
            continue

        if len(unit) < 80 and pending_text:
            pending_text = f"{pending_text}\n{unit}".strip()
            continue
        if pending_text:
            chunks.append(
                {
                    "text": pending_text,
                    "section": pending_title or "document_paragraph",
                    "paragraph_index": paragraph_index,
                    "char_start": max(0, start - len(pending_text)),
                    "char_end": start,
                    "text_span": pending_text[:500],
                    "chunking_strategy": SEMANTIC_CHUNKING_STRATEGY,
                }
            )
        pending_title = title
        pending_text = unit

    if pending_text:
        start = normalized.find(pending_text)
        if start < 0:
            start = max(0, len(normalized) - len(pending_text))
        chunks.append(
            {
                "text": pending_text,
                "section": pending_title or "document_paragraph",
                "paragraph_index": len(chunks) + 1,
                "char_start": start,
                "char_end": start + len(pending_text),
                "text_span": pending_text[:500],
                "chunking_strategy": SEMANTIC_CHUNKING_STRATEGY,
            }
        )
    return chunks


def extract_semantic_terms(text: str) -> dict:
    value = str(text or "")
    keywords_zh = [term for term in QUERY_VARIANT_HINTS if term in value]
    keywords_en: list[str] = []
    synonyms: list[str] = []
    for term in keywords_zh:
        hint = QUERY_VARIANT_HINTS.get(term, "")
        if hint:
            keywords_en.extend(hint.split()[:6])
            synonyms.append(hint)
    domain_terms = []
    # 中文关键词 → 领域（保持不变）
    for term, domain in (
        # 训练方案
        ("减量", "training_protocol"),
        ("周期化", "training_protocol"),
        ("训练周期", "training_protocol"),
        ("配速", "training_protocol"),
        ("乳酸阈", "training_protocol"),
        ("最大摄氧量", "training_protocol"),
        ("轻松跑", "training_protocol"),
        ("节奏跑", "training_protocol"),
        ("间歇", "training_protocol"),
        ("长距离", "training_protocol"),
        ("步行测试", "training_protocol"),
        ("赛前", "training_protocol"),
        ("比赛策略", "training_protocol"),
        ("步频", "training_protocol"),
        ("步幅", "training_protocol"),
        ("触地", "training_protocol"),
        ("跑姿", "training_protocol"),
        ("生物力学", "training_protocol"),
        # 营养补给
        ("补给", "nutrition"),
        ("碳水", "nutrition"),
        ("碳水加载", "nutrition"),
        ("营养", "nutrition"),
        ("饮食", "nutrition"),
        ("补水", "nutrition"),
        ("电解质", "nutrition"),
        ("脱水", "nutrition"),
        # 伤病安全
        ("伤病", "injury_safety"),
        ("损伤", "injury_safety"),
        ("跑者膝", "injury_safety"),
        ("跟腱", "injury_safety"),
        ("足底筋膜炎", "injury_safety"),
        ("损伤预防", "injury_safety"),
        ("抽筋", "injury_safety"),
        ("过度训练", "injury_safety"),
        # 医疗安全（需要转诊/停止训练的严重情况）
        ("热射病", "medical_safety"),
        ("胸痛", "medical_safety"),
        ("头晕", "medical_safety"),
        ("伤", "injury_safety"),
        ("痛", "injury_safety"),
        ("康复", "injury_safety"),
        ("安全", "medical_safety"),
        ("风险", "medical_safety"),
        ("禁忌", "medical_safety"),
        ("高温", "medical_safety"),
        ("降温", "medical_safety"),
        ("热适应", "medical_safety"),
        # 遗漏的中文关键词
        ("力量", "training_protocol"),
        ("耐力", "training_protocol"),
        ("专项", "training_protocol"),
    ):
        if term in value and domain not in domain_terms:
            domain_terms.append(domain)

    # 英文关键词 → 领域（使用模块级 _ENGLISH_DOMAIN_MAP，纯英文 query 无法命中中文关键词时走这里）
    value_lower = value.lower()
    for domain, keywords in _ENGLISH_DOMAIN_MAP.items():
        if any(kw in value_lower for kw in keywords):
            if domain not in domain_terms:
                domain_terms.append(domain)
        # 英文可匹配多个领域
    return {
        "keywords_zh": list(dict.fromkeys(keywords_zh)),
        "keywords_en": list(dict.fromkeys(keywords_en)),
        "synonyms": list(dict.fromkeys(synonyms)),
        "domain_terms": domain_terms,
    }


def _extract_file_domain_terms(full_text: str) -> list[str]:
    domains: list[str] = []
    for raw_pack in re.findall(r"Domain pack:\s*([^\s.]+)", str(full_text or ""), flags=re.IGNORECASE):
        domain = DOMAIN_PACK_TO_DOMAIN.get(str(raw_pack or "").strip())
        if domain and domain not in domains:
            domains.append(domain)
    return domains


def _merge_domain_terms(file_domain_terms: list[str], chunk_domain_terms: list[str] | None) -> list[str]:
    merged = list(file_domain_terms or [])
    for domain in chunk_domain_terms or []:
        if domain not in merged:
            merged.append(domain)
    return merged


# ── 分库检索 ──────────────────────────────────────────────

def _get_primary_domain(chunk: dict) -> str:
    """返回片段所属主领域（分库键）。取文件级第一个标签，无标签则归入 unlabeled。"""
    domain_terms = chunk.get("domain_terms") or []
    if not domain_terms:
        return "unlabeled"
    return str(domain_terms[0])


def _route_query_to_shards(query_text: str) -> list[str]:
    """根据查询文本的领域标签决定检索哪些分库。

    无领域标签 → 搜全部马拉松分库（external_reference 除外）。
    有领域标签 → 搜匹配的马拉松分库。
    """
    query_terms = extract_semantic_terms(query_text)
    query_domains = set(query_terms.get("domain_terms") or [])
    if not query_domains:
        # 无领域标签 → 可能 OOD，不搜任何分库
        return []
    matching = query_domains & set(MARATHON_DOMAIN_SHARDS)
    if matching:
        return sorted(matching)
    return list(MARATHON_DOMAIN_SHARDS)


def chunk_quality_report(chunks: list[dict]) -> dict:
    lengths = [len(str(chunk.get("text") or "")) for chunk in chunks]
    located = [
        chunk
        for chunk in chunks
        if chunk.get("source_file") and (chunk.get("page") not in (None, "", 0) or chunk.get("section"))
    ]
    meta_keys = ("source_file", "page", "section", "paragraph_index", "char_start", "char_end", "text_span")
    complete = 0
    for chunk in chunks:
        complete += sum(1 for key in meta_keys if chunk.get(key) not in (None, "", {}))
    denominator = max(1, len(chunks) * len(meta_keys))
    domain_labeled_count = sum(1 for chunk in chunks if chunk.get("domain_terms"))
    return {
        "chunking_strategy": SEMANTIC_CHUNKING_STRATEGY,
        "chunk_count": len(chunks),
        "average_chunk_length": round(sum(lengths) / len(lengths), 2) if lengths else 0.0,
        "short_chunk_count": sum(1 for length in lengths if length < 80),
        "long_chunk_count": sum(1 for length in lengths if length > 900),
        "metadata_completeness": round(complete / denominator, 4),
        "locatable_source_ratio": round(len(located) / max(1, len(chunks)), 4),
        "domain_labeled_count": domain_labeled_count,
        "domain_coverage_ratio": round(domain_labeled_count / max(1, len(chunks)), 4),
    }

def _strip_page_headers(pages: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """检测并移除 PDF 每页重复的标题/页码前缀，解决"标题污染"导致同文档片段向量坍缩的问题。

    算法：取前三页的前 200 字符，找最长公共前缀。如果该前缀出现在过半页面中且长度 > 30 字符，
    将其从每页剥离。同时移除 "Page X." 或 "Page X of Y" 形式的页码标记。
    """
    if len(pages) < 2:
        return pages
    # 取前三页的首行/首段作为候选前缀
    candidates = []
    for _, raw_text in pages[: min(3, len(pages))]:
        line = raw_text.strip().split("\n")[0][:200] if raw_text.strip() else ""
        if line:
            candidates.append(line)
    if len(candidates) < 2:
        return pages
    # 找最长公共前缀
    def _common_prefix(a: str, b: str) -> str:
        end = 0
        for ca, cb in zip(a, b):
            if ca != cb:
                break
            end += 1
        return a[:end]
    prefix = candidates[0]
    for c in candidates[1:]:
        prefix = _common_prefix(prefix, c)
    # 后缀直到第一个完整单词边界
    if " " in prefix:
        last_space = prefix.rfind(" ")
        if last_space > len(prefix) * 0.7:
            prefix = prefix[:last_space]
    prefix = prefix.rstrip(" ,-.:;")
    if len(prefix) < 30:
        return pages  # 太短，可能是偶然重合
    # 确认该前缀在多数页面中出现
    match_count = sum(1 for _, t in pages if str(t or "").strip().startswith(prefix))
    if match_count < len(pages) * 0.5:
        return pages
    # 剥离
    cleaned = []
    for page_num, raw_text in pages:
        text = str(raw_text or "").strip()
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            # 移除紧随的 "Page X." 或 "Page X of Y" 或纯数字页码
            text = re.sub(r"^[Pp]age\s*\d+(\s*of\s*\d+)?[.\s]*", "", text, count=1)
            text = re.sub(r"^\d{1,4}\s*\n", "", text, count=1)
        cleaned.append((page_num, text.strip()))
    return cleaned


def collect_chunks(input_dir: Path | List[Path], chunk_size: int, chunk_overlap: int) -> tuple[list[dict], list[dict]]:
    """从目录或文件列表中收集所有文本分片"""
    all_chunks = []
    file_stats = []
    
    # 兼容单个目录或文件列表
    if isinstance(input_dir, list):
        files_to_process = sorted(input_dir, key=lambda p: p.name.lower())
    else:
        if not input_dir.exists():
            return [], []
        files_to_process = sorted(input_dir.iterdir(), key=lambda p: p.name.lower())

    for file_path in files_to_process:
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        page_count = 0
        chunk_count = 0
        source_meta = _build_source_metadata(file_path)
        try:
            pages = load_pages(file_path)
            page_count = len(pages)
            full_text = "\n".join(raw_page for _, raw_page in pages)
            file_domain_terms = _extract_file_domain_terms(full_text)
            # 剥离每页重复的论文标题/页码前缀，消除"标题污染"导致的同文档向量坍缩
            pages = _strip_page_headers(pages)

            if file_path.stem == "动作库":
                from marathon_qa_assistant.services.exercise_parser import parse_action_library

                parsed_entries = parse_action_library(full_text)

                for entry in parsed_entries:
                    parts = [f"name：{entry['name']}"]
                    if entry.get("categories"):
                        parts.append(f"categories：{' , '.join(entry['categories'])}")
                    if entry.get("content"):
                        parts.append(f"content：{entry['content']}")
                    if entry.get("objective"):
                        parts.append(f"objective：{entry['objective']}")
                    text = "\n".join(parts)

                    import hashlib
                    name_hash = hashlib.sha1(
                        entry["name"].encode("utf-8")
                    ).hexdigest()[:8]
                    chunk_id = f"动作库_{name_hash}"

                    all_chunks.append({
                        "chunk_id": chunk_id,
                        "source_file": source_meta["source_file"],
                        "source_path": source_meta["source_path"],
                        "page": entry.get("page", 0),
                        "domain_terms": file_domain_terms,
                        "text": text,
                    })
                    chunk_count += 1

                file_stats.append({
                    "source_file": source_meta["source_file"],
                    "source_path": source_meta["source_path"],
                    "pages": page_count,
                    "chunks": chunk_count,
                })
                continue

            for page_num, raw_page in pages:
                cleaned_page = normalize_text(raw_page)
                if get_settings().semantic_chunking_enabled:
                    page_chunks = split_text_semantic(cleaned_page, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                else:
                    page_chunks = [
                        {
                            "text": chunk_text,
                            "section": "fixed_window",
                            "paragraph_index": idx,
                            "char_start": None,
                            "char_end": None,
                            "text_span": chunk_text[:500],
                            "chunking_strategy": "fixed_window",
                        }
                        for idx, chunk_text in enumerate(
                            split_text_sentence_aware(cleaned_page, chunk_size=chunk_size, chunk_overlap=chunk_overlap),
                            start=1,
                        )
                    ]
                for idx, chunk in enumerate(page_chunks, start=1):
                    chunk_text = str(chunk.get("text") or "").strip()
                    if not chunk_text:
                        continue
                    anchor_meta = _chunk_anchor_metadata(
                        str(source_meta.get("source_registry_id") or ""),
                        str(chunk.get("section") or "document_paragraph"),
                        chunk_text,
                    )
                    if get_settings().semantic_chunking_enabled:
                        chunk_id = (
                            f"{anchor_meta['source_registry_id']}_"
                            f"{anchor_meta['section_anchor']}_"
                            f"p{page_num:04d}_"
                            f"{anchor_meta['paragraph_hash']}_"
                            f"{anchor_meta['text_span_hash']}"
                        )
                    else:
                        chunk_id = f"{file_path.stem}_p{page_num:04d}_c{idx:04d}"
                    semantic_terms = extract_semantic_terms(chunk_text)
                    semantic_terms["domain_terms"] = _merge_domain_terms(
                        file_domain_terms,
                        semantic_terms.get("domain_terms") or [],
                    )
                    # Sentence Window：小块（text）负责精确召回，大块（parent_text）负责提供上下文
                    # parent_text 取 ±SENTENCE_WINDOW_CONTEXT_CHARS 字符范围，确保 LLM 看到完整语义
                    if chunk.get("char_start") is not None:
                        parent_start = max(0, (chunk.get("char_start") or 0) - SENTENCE_WINDOW_CONTEXT_CHARS)
                        parent_end = min(len(cleaned_page), (chunk.get("char_end") or 0) + SENTENCE_WINDOW_CONTEXT_CHARS)
                        parent_text = cleaned_page[parent_start:parent_end].strip()
                    else:
                        parent_text = cleaned_page[:SENTENCE_WINDOW_CHUNK_SIZE + SENTENCE_WINDOW_CONTEXT_CHARS * 2]
                    all_chunks.append(
                        {
                            "chunk_id": chunk_id,
                            **anchor_meta,
                            "source_file": source_meta["source_file"],
                            "source_path": source_meta["source_path"],
                            "page": page_num,
                            "section": chunk.get("section") or "document_paragraph",
                            "paragraph_index": chunk.get("paragraph_index") or idx,
                            "char_start": chunk.get("char_start"),
                            "char_end": chunk.get("char_end"),
                            "text_span": chunk.get("text_span") or chunk_text[:500],
                            "chunking_strategy": chunk.get("chunking_strategy") or SEMANTIC_CHUNKING_STRATEGY,
                            "parent_text": parent_text,
                            **semantic_terms,
                            "text": chunk_text,
                        }
                    )
                chunk_count += len(page_chunks)
            file_stats.append(
                {
                    "source_file": source_meta["source_file"],
                    "source_path": source_meta["source_path"],
                    "pages": page_count,
                    "chunks": chunk_count,
                }
            )
        except Exception as exc:
            file_stats.append(
                {
                    "source_file": source_meta["source_file"],
                    "source_path": source_meta["source_path"],
                    "pages": page_count,
                    "chunks": chunk_count,
                    "error": str(exc),
                }
            )
    return all_chunks, file_stats

def build_hybrid_indices(chunks: list[dict]):
    """
    为了兼容 module_kb.py 的签名，返回三个占位符。
    真正的向量构建在 save_outputs 中执行。
    """
    return "faiss_vectorizer", "faiss_matrix", "faiss_bm25"

def save_outputs(output_dir: Path, chunks: list[dict], vectorizer, matrix, bm25) -> dict:
    """保存构建好的向量库和分片数据"""
    # 确保 output_dir 及其所有父目录都存在
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"创建输出目录失败: {e}")
        # 尝试强制创建父目录
        os.makedirs(str(output_dir), exist_ok=True)
    
    # 1. 构建 FAISS 向量库
    faiss_dir = output_dir / "faiss_db"
    
    if faiss_dir.exists():
        try:
            shutil.rmtree(faiss_dir)
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"清理旧目录失败: {e}")

    # 再次确保 faiss_dir 存在
    try:
        faiss_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"创建 FAISS 目录失败: {e}")
        os.makedirs(str(faiss_dir), exist_ok=True)
            
    embeddings = get_embeddings()
    logger.info(f"正在构建 FAISS 向量库: {faiss_dir}")
    
    # 准备 Document 对象，过滤空文本以避开 Ollama 空 embedding 导致的 FAISS 构建失败。
    docs = []
    skipped_empty_text_chunk_ids = []
    for c in chunks:
        text = str(c.get("text") or "")
        if not text.strip():
            skipped_empty_text_chunk_ids.append(str(c.get("chunk_id") or ""))
            continue
        metadata = {
            "chunk_id": c.get("chunk_id", ""),
            "source_file": c.get("source_file", ""),
            "source_path": c.get("source_path") or c.get("local_path", ""),
            "page": c.get("page", 1),
        }
        # v2 chunk metadata 是证据可见闭环的一部分，必须随 FAISS Document 保存。
        for key in EVIDENCE_CHAIN_METADATA_KEYS:
            if key in c:
                metadata[key] = c.get(key)
        docs.append(Document(page_content=text, metadata=metadata))

    if not docs:
        raise ValueError(
            "Cannot build FAISS index: no non-empty documents after filtering chunks. "
            f"skipped_empty_text_chunk_ids={skipped_empty_text_chunk_ids}"
        )
    if skipped_empty_text_chunk_ids:
        logger.warning("跳过空文本分片，避免 Ollama 返回空 embedding: %s", skipped_empty_text_chunk_ids)

    embedding_validation = _validate_embedding_model_on_sample(embeddings, docs)
    faiss_store = _build_faiss(docs, embeddings)
    stripped_docstore_text_count = _strip_faiss_docstore_text(faiss_store)
    faiss_dir_str = str(faiss_dir)
    
    # 在保存时同样尝试处理 Windows 中文路径问题
    import os
    if os.name == 'nt':
        try:
            rel_path = os.path.relpath(faiss_dir_str, os.getcwd())
            faiss_store.save_local(rel_path)
            logger.info(f"FAISS 索引已保存 (相对路径: {rel_path})")
        except Exception as rel_e:
            logger.debug(f"相对路径保存失败: {rel_e}，尝试使用绝对路径")
            faiss_store.save_local(faiss_dir_str)
    else:
        faiss_store.save_local(faiss_dir_str)
    
    # 2. 保存 chunks.jsonl 供其他模块使用
    chunks_path = output_dir / "chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8") as f:
        for row in chunks:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            
    logger.info("FAISS indexing complete!")
    
    return {
        "chunks_file": str(chunks_path),
        "faiss_dir": str(faiss_dir),
        "embedding_model": _embedding_model_name(),
        "embedding_candidates": list(EMBEDDING_CANDIDATE_MODELS),
        "embedding_validation": embedding_validation,
        "stripped_docstore_text_count": stripped_docstore_text_count,
        "chunking_strategy": SEMANTIC_CHUNKING_STRATEGY,
        "chunk_quality": chunk_quality_report(chunks),
    }

def load_chunks(chunks_file: Path) -> list[dict]:
    """加载 jsonl 格式的分片数据"""
    chunks = []
    with chunks_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            chunks.append(_normalize_chunk_source(json.loads(line)))
    # 只在运行时屏蔽已隔离来源，不删除原始 chunks 以便后续审计。
    return filter_quarantined_chunks(chunks, LEGACY_RUNTIME_QUARANTINE_REPORT)

def _trusted_vector_dirs() -> list[Path]:
    return [
        USER_VECTOR_DIR,
        V2_VECTOR_DIR,
        RUNTIME_USER_VECTOR_DIR,
        LEGACY_USER_VECTOR_DIR,
        DEFAULT_VECTOR_DIR,
        LEGACY_DEFAULT_VECTOR_DIR,
    ]


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.absolute() == right.absolute()
    except Exception:
        return str(left) == str(right)


def _is_trusted_faiss_dir(faiss_dir: Path) -> bool:
    vector_dir = Path(faiss_dir).parent.resolve()
    if any(_same_path(vector_dir, trusted_dir) for trusted_dir in _trusted_vector_dirs()):
        return True
    # 分库索引目录：data/vector_kb/v2_sharded*/{domain}/faiss_db
    for shard_rel in ("v2_sharded", "v2_sharded_clean"):
        sharded_base = (V2_VECTOR_DIR.parent / shard_rel).resolve()
        try:
            vector_dir.relative_to(sharded_base)
            return True
        except ValueError:
            pass
    return False


def _kb_source_label(vector_dir: Path) -> str:
    path = Path(vector_dir)
    labels = [
        (USER_VECTOR_DIR, "user"),
        (V2_VECTOR_DIR, "v2"),
        (RUNTIME_USER_VECTOR_DIR, "runtime_user"),
        (LEGACY_USER_VECTOR_DIR, "legacy_user"),
        (DEFAULT_VECTOR_DIR, "default"),
        (LEGACY_DEFAULT_VECTOR_DIR, "legacy_default"),
    ]
    for candidate, label in labels:
        if _same_path(path, candidate):
            return label
    return "external"


def _load_faiss_store(faiss_dir: Path, embeddings):
    # 反序列化 FAISS pkl 有风险，只允许项目配置的知识库目录加载。
    if not _is_trusted_faiss_dir(faiss_dir):
        logger.warning(f"拒绝加载未受信任的 FAISS 目录: {faiss_dir}")
        return None
    try:
        return FAISS.load_local(str(faiss_dir), embeddings, allow_dangerous_deserialization=True)
    except Exception as exc:
        logger.warning("常规 FAISS 加载失败，尝试内存反序列化兜底: %s", exc)
        try:
            return _load_faiss_store_from_files(faiss_dir, embeddings)
        except Exception as fallback_exc:
            logger.error("内存反序列化兜底也失败: %s", fallback_exc)
            return None


def _load_faiss_store_from_files(faiss_dir: Path, embeddings):
    import faiss
    import numpy as np

    index_file = Path(faiss_dir) / "index.faiss"
    pkl_file = Path(faiss_dir) / "index.pkl"
    # 用 Python 文件读取绕过 FAISS C++ fopen 对 Windows 中文路径的兼容问题。
    index_bytes = index_file.read_bytes()
    with pkl_file.open("rb") as handle:
        docstore, index_to_docstore_id = pickle.load(handle)
    index = faiss.deserialize_index(np.frombuffer(index_bytes, dtype=np.uint8))
    return FAISS(
        embedding_function=embeddings.embed_query,
        index=index,
        docstore=docstore,
        index_to_docstore_id=index_to_docstore_id,
    )


def probe_vector_kb_health(vector_dir: Path) -> dict:
    vector_dir = Path(vector_dir)
    chunks_file = vector_dir / "chunks.jsonl"
    faiss_dir = vector_dir / "faiss_db"
    faiss_index_file = faiss_dir / "index.faiss"
    report = {
        "ok": False,
        "ready": False,
        "vector_dir": str(vector_dir),
        "source": _kb_source_label(vector_dir),
        "reason": "",
        "chunks_count": 0,
        "faiss_ready": False,
        "bm25_ready": False,
        "fallback_active": False,
        "embedding_model": _embedding_model_name(),
        "chunking_strategy": "unknown",
        "eval_report_path": "",
        "index_schema_version": "missing",
        "metadata_completeness": 0.0,
        "runtime_core_prescription_enabled": False,
    }
    if not chunks_file.exists():
        report["reason"] = f"未找到 chunks 文件: {chunks_file}"
        return report
    chunks = load_chunks(chunks_file)
    schema_summary = summarize_runtime_index_schema(chunks)
    chunking_values = {str(chunk.get("chunking_strategy") or "") for chunk in chunks if chunk.get("chunking_strategy")}
    report.update(
        {
            "ok": bool(chunks),
            "ready": bool(chunks),
            "chunks_count": len(chunks),
            "index_schema_version": schema_summary["index_schema_version"],
            "metadata_completeness": float(schema_summary["metadata_completeness"]),
            "runtime_core_prescription_enabled": bool(schema_summary["runtime_core_prescription_enabled"]),
            "bm25_ready": bool(chunks),
            "chunking_strategy": sorted(chunking_values)[0] if chunking_values else "legacy_or_registry",
        }
    )
    if not faiss_index_file.exists():
        report.update(
            {
                "reason": f"FAISS 索引文件缺失，启用当前 v2 chunks fallback: {faiss_index_file}",
                "fallback_active": bool(chunks),
                "runtime_core_prescription_enabled": False,
            }
        )
        return report
    try:
        embeddings = get_embeddings()
        faiss_store = _load_faiss_store(faiss_dir, embeddings)
    except Exception as exc:
        report.update(
            {
                "reason": f"FAISS 加载失败，启用当前 v2 chunks fallback: {exc}",
                "fallback_active": bool(chunks),
                "runtime_core_prescription_enabled": False,
            }
        )
        return report

    if faiss_store is None:
        report.update(
            {
                "reason": "FAISS 不可用，启用当前 v2 chunks fallback",
                "fallback_active": bool(chunks),
                "runtime_core_prescription_enabled": False,
            }
        )
        return report
    report.update({"ok": True, "ready": True, "faiss_ready": True, "fallback_active": False, "reason": ""})
    return report


def load_vector_kb(vector_dir: Path):
    """
    加载向量库，返回 (chunks, vectorizer, matrix, bm25) 结构。
    实际上 matrix 位置放置的是 FAISS 实例。
    """
    vector_dir = Path(vector_dir)
    chunks_file = vector_dir / "chunks.jsonl"
    faiss_dir = vector_dir / "faiss_db"
    
    if not chunks_file.exists():
        raise FileNotFoundError(f"未找到 chunks 文件: {chunks_file}")
    
    chunks = load_chunks(chunks_file)
    
    # 初始化 FAISS 客户端作为 "matrix"
    embeddings = get_embeddings()
    faiss_store = None

    # 更加严谨的可用性判断：不仅检查目录，还要检查索引文件 index.faiss
    faiss_index_file = faiss_dir / "index.faiss"

    if faiss_index_file.exists():
        try:
            faiss_store = _load_faiss_store(faiss_dir, embeddings)
            if faiss_store is not None:
                _attach_chunk_text_cache(faiss_store, chunks)
                logger.info(f"FAISS 索引加载成功 (trusted loader: {faiss_dir})")
        except Exception as e:
            logger.error(f"加载 FAISS 失败 (路径: {faiss_dir}): {e}")
            faiss_store = None
    else:
        logger.warning(f"FAISS 索引文件缺失: {faiss_index_file}，将以空库运行。")

    bm25_index = build_bm25_fallback_index(chunks)
    # 返回: chunks, vectorizer(dummy), matrix(faiss), bm25(fallback index)
    return chunks, "faiss_vectorizer", faiss_store, bm25_index


def load_sharded_kb(shard_base: Path):
    """加载分库索引。

    目录结构:
        shard_base/
          training_protocol/
            chunks.jsonl
            faiss_db/
          nutrition/
            ...

    返回:
        shard_stores: dict[str, FAISS]  - 每个分库的 FAISS 实例
        shard_chunks: dict[str, list]   - 每个分库的片段列表
        all_chunks: list                - 所有片段（用于 BM25 fallback）
        bm25_index: dict                - 全局 BM25 fallback
    """
    shard_base = Path(shard_base)
    shard_stores: dict[str, Any] = {}
    shard_chunks: dict[str, list] = {}
    all_chunks: list = []
    embeddings = get_embeddings()

    for shard_name in ALL_DOMAIN_SHARDS:
        shard_dir = shard_base / shard_name
        chunks_file = shard_dir / "chunks.jsonl"
        faiss_dir = shard_dir / "faiss_db"

        if not chunks_file.exists():
            logger.warning("分库 %s 的 chunks.jsonl 不存在: %s", shard_name, chunks_file)
            shard_stores[shard_name] = None
            shard_chunks[shard_name] = []
            continue

        chunks = load_chunks(chunks_file)
        shard_chunks[shard_name] = chunks
        all_chunks.extend(chunks)

        faiss_index_file = faiss_dir / "index.faiss"
        if faiss_index_file.exists():
            try:
                store = _load_faiss_store(faiss_dir, embeddings)
                if store is not None:
                    _attach_chunk_text_cache(store, chunks)
                shard_stores[shard_name] = store
            except Exception as e:
                logger.error("加载分库 %s FAISS 失败: %s", shard_name, e)
                shard_stores[shard_name] = None
        else:
            shard_stores[shard_name] = None

    # 每个分库独立 BM25 索引 → RRF 融合时 BM25 不会跨领域污染 FAISS 的结果
    shard_bm25: dict[str, Any] = {}
    for shard_name in ALL_DOMAIN_SHARDS:
        sc = shard_chunks.get(shard_name, [])
        shard_bm25[shard_name] = build_bm25_fallback_index(sc) if sc else None
    global_bm25 = build_bm25_fallback_index(all_chunks)
    return shard_stores, shard_chunks, all_chunks, shard_bm25, global_bm25


def _search_one_shard(variant: str, shard_name: str, faiss_store: Any,
                       chunks_cache: dict[str, str] | None, per_shard_k: int) -> list[dict]:
    """在单个分库内执行检索，返回该分库的命中列表。"""
    try:
        results = faiss_store.similarity_search_with_score(variant, k=per_shard_k)
    except Exception as e:
        logger.error("分库 %s 检索失败: %s", shard_name, e)
        return []
    hits = []
    for doc, distance in results:
        hit = _doc_to_hit(doc, distance=distance, chunks_cache=chunks_cache)
        hit["retrieval_mode"] = f"sharded:{shard_name}"
        hit["query_variant"] = variant
        hit["why_retrieved"] = f"FAISS similarity search in {shard_name} shard."
        score_breakdown = hit.get("score_breakdown") if isinstance(hit.get("score_breakdown"), dict) else {}
        score_breakdown["query_variant"] = variant
        score_breakdown["shard"] = shard_name
        hit["score_breakdown"] = score_breakdown
        hits.append(hit)
    hits = sorted(hits, key=lambda x: x["score"], reverse=True)
    if get_settings().domain_filter_enabled:
        hits = _filter_hits_by_domain(variant, hits)
    return hits


def _doc_to_hit(doc: Document, distance: float, chunks_cache: dict[str, str] | None = None) -> dict:
    """把 LangChain Document 转成检索命中，并保留证据链展示元数据。"""
    metadata = doc.metadata or {}
    chunk_id = metadata.get("chunk_id", "unknown")
    text = doc.page_content or _load_chunk_text(str(chunk_id), chunks_cache)
    score = round(1.0 / (1.0 + float(distance)), 6)
    hit = {
        "score": score,
        "chunk_id": chunk_id,
        "source_file": metadata.get("source_file", "unknown"),
        "source_path": metadata.get("source_path", "") or infer_source_path(metadata.get("source_file", "")),
        "page": metadata.get("page", 1),
        "text": text,
        "distance": float(distance),
    }
    for key in EVIDENCE_CHAIN_METADATA_KEYS:
        if key in metadata:
            hit[key] = metadata.get(key)
    hit.setdefault("retrieval_mode", "vector")
    hit.setdefault("why_retrieved", "FAISS similarity search matched the query after keyword expansion.")
    hit.setdefault("score_breakdown", {"vector_score": score, "distance": float(distance)})
    return hit


def _tokenize_for_fallback(text: str) -> list[str]:
    value = normalize_query_text(text).lower()
    latin = re.findall(r"[a-z0-9][a-z0-9_\-+.]*", value)
    chinese: list[str] = []
    for segment in re.findall(r"[\u4e00-\u9fff]+", value):
        if len(segment) == 1:
            chinese.append(segment)
            continue
        for width in (2, 3, 4):
            for idx in range(0, max(0, len(segment) - width + 1)):
                chinese.append(segment[idx : idx + width])
    return list(dict.fromkeys([token for token in [*latin, *chinese] if token.strip()]))


def build_bm25_fallback_index(chunks: list[dict]) -> dict:
    documents = []
    doc_freq: dict[str, int] = {}
    for idx, chunk in enumerate(chunks or []):
        text = str(chunk.get("text") or "")
        tokens = _tokenize_for_fallback(
            " ".join(
                [
                    text,
                    " ".join(str(item) for item in chunk.get("keywords_zh") or []),
                    " ".join(str(item) for item in chunk.get("keywords_en") or []),
                    " ".join(str(item) for item in chunk.get("domain_terms") or []),
                ]
            )
        )
        if not tokens:
            continue
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        for token in counts:
            doc_freq[token] = doc_freq.get(token, 0) + 1
        documents.append({"index": idx, "chunk": chunk, "tokens": counts, "length": len(tokens)})
    avg_len = sum(doc["length"] for doc in documents) / max(1, len(documents))
    return {"documents": documents, "doc_freq": doc_freq, "avg_len": avg_len, "doc_count": len(documents)}


def _bm25_score(tokens: list[str], doc: dict, index: dict) -> float:
    k1 = 1.5
    b = 0.75
    score = 0.0
    doc_count = max(1, int(index.get("doc_count") or 0))
    avg_len = float(index.get("avg_len") or 1.0)
    length = max(1.0, float(doc.get("length") or 1.0))
    counts = doc.get("tokens") or {}
    for token in tokens:
        tf = float(counts.get(token) or 0.0)
        if tf <= 0:
            continue
        df = float((index.get("doc_freq") or {}).get(token) or 0.0)
        idf = math.log(1.0 + (doc_count - df + 0.5) / (df + 0.5))
        score += idf * ((tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b + b * length / avg_len)))
    return score


def fallback_search(question: str, chunks: list[dict], bm25: Any = None, top_k: int | None = 5) -> list[dict]:
    index = bm25 if isinstance(bm25, dict) and bm25.get("documents") else build_bm25_fallback_index(chunks)
    tokens = _tokenize_for_fallback(question)
    if not tokens:
        return []
    scored = []
    for doc in index.get("documents") or []:
        score = _bm25_score(tokens, doc, index)
        if score > 0:
            scored.append((score, doc.get("chunk") or {}))
    scored.sort(key=lambda item: item[0], reverse=True)
    limited = scored if top_k is None else scored[:top_k]
    max_score = max([score for score, _ in limited], default=1.0)
    hits = []
    for score, chunk in limited:
        normalized_score = round(float(score) / max(1.0, float(max_score)), 6)
        hit = {
            "score": normalized_score,
            "chunk_id": chunk.get("chunk_id", "unknown"),
            "source_file": chunk.get("source_file", "unknown"),
            "source_path": chunk.get("source_path") or chunk.get("local_path", "") or infer_source_path(chunk.get("source_file", "")),
            "page": chunk.get("page", 1),
            "text": chunk.get("text", ""),
            "distance": 1.0 - normalized_score,
            "retrieval_mode": "bm25_fallback",
            "retrieval_status": "degraded_retrieval",
            "query_variant": "fallback_text",
            "why_retrieved": "FAISS was unavailable; current v2 chunks were searched with lexical BM25-style fallback.",
            "score_breakdown": {"bm25_score": round(float(score), 6), "fallback_score": normalized_score},
            "display_mode": "legacy_explanation",
            "prescription_permission": "explanation_only",
            "allowed_use": "explanation",
            "evidence_source_type": "explanatory_context",
            "can_write_core": False,
            "explanation_only": True,
        }
        for key in EVIDENCE_CHAIN_METADATA_KEYS:
            if key in chunk and key not in {"display_mode", "prescription_permission", "allowed_use", "can_write_core", "explanation_only"}:
                hit[key] = chunk.get(key)
        hits.append(hit)
    return hits


def _enhance_query_with_hints(query: str) -> str:
    enhanced = query
    for key, hint in QUERY_HINTS.items():
        if key in query and hint not in enhanced:
            enhanced = f"{enhanced} {hint}"
    return enhanced.strip()


def _build_query_variants(query: str, hints: Dict[str, str] | None = None) -> list[str]:
    """Build a compact bilingual variant set for retrieval fusion."""
    raw_query = normalize_query_text(str(query or "").strip())
    if not raw_query:
        return []

    hint_map = dict(QUERY_VARIANT_HINTS)
    if isinstance(hints, dict):
        hint_map.update({str(key): str(value) for key, value in hints.items()})

    if not re.search(r"[\u4e00-\u9fff]", raw_query):
        return [raw_query]

    annotated_query = raw_query
    english_query = raw_query
    for chinese_term, english_hint in hint_map.items():
        if chinese_term in annotated_query:
            annotated_query = annotated_query.replace(chinese_term, f"{chinese_term}({english_hint})")
            english_query = english_query.replace(chinese_term, f" {english_hint} ")

    english_query = re.sub(r"[\u4e00-\u9fff]+", " ", english_query)
    english_query = re.sub(r"[，。！？、；：”“‘’（）【】《》]", " ", english_query)
    english_query = re.sub(r"[^\w\s+\-.]", " ", english_query)
    english_query = " ".join(english_query.split()).strip()

    variants = [raw_query]
    if annotated_query and annotated_query not in variants:
        variants.append(annotated_query)
    enhanced_query = _enhance_query_with_hints(raw_query)
    if enhanced_query and enhanced_query not in variants:
        variants.append(enhanced_query)
    if english_query and english_query not in variants:
        variants.append(english_query)
    return variants


def _metadata_completeness(hit: dict) -> int:
    return sum(1 for key in EVIDENCE_CHAIN_METADATA_KEYS if hit.get(key) not in (None, "", {}))


def _rrf_fusion(*hit_lists: list[dict], k: int = 60, top_k: int = 5) -> list[dict]:
    """Reciprocal Rank Fusion：合并多路检索结果，按倒数排名融合分数。

    解决了 FAISS 语义检索（区分度低）和 BM25 关键词检索（精确但缺语义）的互补问题。
    参考: Cormack et al., "Reciprocal Rank Fusion outperforms Condorcet and individual rankers", SIGIR 2009.
    """
    # 按 chunk_id 聚合
    rrf_scores: dict[str, float] = {}
    best_hits: dict[str, dict] = {}
    for hit_list in hit_lists:
        for rank, hit in enumerate(hit_list or [], start=1):
            key = str(hit.get("chunk_id") or f"{hit.get('source_file','')}:{hit.get('page','')}:{hit.get('text','')[:80]}")
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank)
            existing = best_hits.get(key)
            if existing is None or float(hit.get("score") or 0) > float(existing.get("score") or 0):
                best_hits[key] = dict(hit)
    # 按 RRF 分数排序，保留原始 FAISS score（RRF 仅用于排序）
    fused = []
    for key, rrf in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
        hit = best_hits[key]
        score_breakdown = hit.get("score_breakdown") if isinstance(hit.get("score_breakdown"), dict) else {}
        score_breakdown["rrf_score"] = round(rrf, 6)
        hit["score_breakdown"] = score_breakdown
        hit["retrieval_mode"] = (hit.get("retrieval_mode", "vector") + "+rrf").replace("+rrf+rrf", "+rrf")
        fused.append(hit)
        if len(fused) >= top_k:
            break
    return fused


def _merge_ranked_hits(hit_groups: list[list[dict]], top_k: int | None = 5) -> list[dict]:
    """按 chunk 合并多路命中；分数保留最高，元数据保留最完整。"""
    merged: dict[str, dict] = {}
    run_counts: dict[str, int] = {}
    query_variants: dict[str, list[str]] = {}
    best_variants: dict[str, str] = {}
    for group in hit_groups:
        for hit in group or []:
            key = str(hit.get("chunk_id") or f"{hit.get('source_file', '')}:{hit.get('page', '')}:{hit.get('text', '')[:80]}")
            run_counts[key] = run_counts.get(key, 0) + 1
            variant = str(hit.get("query_variant") or "")
            if variant:
                query_variants.setdefault(key, [])
                if variant not in query_variants[key]:
                    query_variants[key].append(variant)
            existing = merged.get(key)
            if existing is None:
                merged[key] = dict(hit)
                best_variants[key] = variant
                continue
            if float(hit.get("score") or 0.0) > float(existing.get("score") or 0.0):
                for key_to_keep in ("score", "distance", "rank_score"):
                    if key_to_keep in hit:
                        existing[key_to_keep] = hit[key_to_keep]
                best_variants[key] = variant
            richer = hit if _metadata_completeness(hit) > _metadata_completeness(existing) else existing
            for meta_key in EVIDENCE_CHAIN_METADATA_KEYS:
                if richer.get(meta_key) not in (None, "", {}):
                    existing[meta_key] = richer.get(meta_key)
    for key, hit in merged.items():
        variants = query_variants.get(key, [])
        hit["query_variants"] = variants
        hit["query_variant_count"] = len(variants)
        hit["consensus_count"] = run_counts.get(key, 1)
        hit["best_query_variant"] = best_variants.get(key, hit.get("query_variant", ""))
        has_chinese = any(re.search(r"[\u4e00-\u9fff]", variant) for variant in variants)
        has_english = any(re.search(r"[a-zA-Z]", variant) and not re.search(r"[\u4e00-\u9fff]", variant) for variant in variants)
        hit["bilingual_match"] = bool(has_chinese and has_english)
        score_breakdown = hit.get("score_breakdown") if isinstance(hit.get("score_breakdown"), dict) else {}
        score_breakdown.update(
            {
                "consensus_count": hit["consensus_count"],
                "query_variant_count": hit["query_variant_count"],
                "bilingual_match": hit["bilingual_match"],
            }
        )
        hit["score_breakdown"] = score_breakdown
    ranked = sorted(
        merged.values(),
        key=lambda item: float(item.get("score") or 0.0),
        reverse=True,
    )
    return ranked if top_k is None else ranked[:top_k]


def _filter_hits_by_domain(query_text: str, hits: list[dict]) -> list[dict]:
    """根据查询领域标签过滤不相关片段。查询无领域标签或片段无领域标签时保留。"""
    query_terms = extract_semantic_terms(query_text)
    query_domains = set(query_terms.get("domain_terms") or [])
    if not query_domains:
        return hits  # 查询无领域标签，不过滤
    kept = []
    dropped = []
    for hit in hits:
        hit_domains = set(hit.get("domain_terms") or [])
        if not hit_domains or (query_domains & hit_domains):
            kept.append(hit)
        else:
            dropped.append(hit["chunk_id"])
    if dropped:
        logger.info("领域过滤: 查询领域=%s, 丢弃片段=%s", sorted(query_domains), dropped)
    return kept


def _retrieve_sharded(question: str, shard_chunks: dict, shard_stores: dict,
                       shard_bm25: dict, top_k: int | None) -> list[dict]:
    """分库检索：路由查询到匹配的领域分库，FAISS + 分库 BM25 → RRF 融合。

    shard_bm25: dict[str, BM25 index] — 每个分库独立的 BM25 索引，避免跨领域关键词污染。
    """
    query = normalize_query_text(normalize_text(question))
    variants = _build_query_variants(query) if get_settings().retrieval_variants_enabled else [_enhance_query_with_hints(query)]
    if not variants:
        return []

    # 路由：优先用第一个增强 variant 提取领域（英文 query 依赖 QUERY_HINTS 的中英映射）
    shards_to_search = _route_query_to_shards(variants[0])
    if not shards_to_search:
        return []  # 无领域匹配 → OOD，直接返回空

    # 每个分库取 top_k 条，合并后排序
    per_shard_k = top_k if top_k is not None else 10
    chunks_cache = _build_chunk_text_cache([
        c for clist in shard_chunks.values() for c in clist
    ])

    def _search_variant_in_shards(variant: str) -> list[dict]:
        shard_hits: list[list[dict]] = []
        for shard_name in shards_to_search:
            store = shard_stores.get(shard_name)
            if store is None:
                continue
            hits = _search_one_shard(variant, shard_name, store, chunks_cache, per_shard_k)
            if hits:
                shard_hits.append(hits)
        return [h for hits in shard_hits for h in hits]

    def _search_variant_sharded_with_bm25(variant: str) -> list[dict]:
        """分库 FAISS + 分库 BM25 → RRF 融合。BM25 只搜匹配分库，不跨领域。"""
        try:
            shard_hits = _search_variant_in_shards(variant)
        except Exception as exc:
            logger.error("分库 FAISS 检索失败: %s", exc)
            shard_hits = []
        rrf_candidate_k = (top_k or 5) * 4
        # BM25 按分库检索，每个分库独立搜，后置领域过滤
        bm25_hits: list[dict] = []
        for shard_name in shards_to_search:
            sb = shard_bm25.get(shard_name)
            sc = shard_chunks.get(shard_name, [])
            if sb and sc:
                try:
                    hits = fallback_search(variant, sc, bm25=sb, top_k=rrf_candidate_k)
                except Exception as exc:
                    logger.error("分库 BM25 检索失败 [%s]: %s", shard_name, exc)
                    continue
                for h in hits:
                    h["retrieval_mode"] = f"bm25:{shard_name}"
                    h["query_variant"] = variant
                if get_settings().domain_filter_enabled:
                    hits = _filter_hits_by_domain(variant, hits)
                bm25_hits.extend(hits)
        try:
            return _rrf_fusion(shard_hits, bm25_hits, top_k=top_k or 5)
        except Exception as exc:
            logger.error("RRF 融合失败 (FAISS=%d, BM25=%d): %s", len(shard_hits), len(bm25_hits), exc)
            return (shard_hits + bm25_hits)[:top_k or 5]

    if len(variants) == 1:
        try:
            hit_groups = [_search_variant_sharded_with_bm25(variants[0])]
        except Exception as exc:
            logger.error("分库混合检索失败: %s", exc)
            if not get_settings().bm25_fallback_enabled:
                return []
            all_chunks = [c for clist in shard_chunks.values() for c in clist]
            fallback_bm25 = build_bm25_fallback_index(all_chunks)
            raw_hits = fallback_search(variants[0], all_chunks, bm25=fallback_bm25, top_k=top_k)
            return _filter_hits_by_domain(variants[0], raw_hits) if get_settings().domain_filter_enabled else raw_hits
    else:
        hit_groups_by_variant: dict[str, list[dict]] = {}
        with ThreadPoolExecutor(max_workers=min(len(variants), 4)) as executor:
            futures = {executor.submit(_search_variant_sharded_with_bm25, variant): variant for variant in variants}
            for future in as_completed(futures):
                variant = futures[future]
                try:
                    hit_groups_by_variant[variant] = future.result()
                except Exception as exc:
                    logger.error("分库混合检索一路失败: %s", exc)
                    hit_groups_by_variant[variant] = []
        hit_groups = [hit_groups_by_variant.get(variant, []) for variant in variants]
        if not any(hit_groups):
            if not get_settings().bm25_fallback_enabled:
                return []
            all_chunks = [c for clist in shard_chunks.values() for c in clist]
            fallback_bm25 = build_bm25_fallback_index(all_chunks)
            raw_hits = fallback_search(variants[0], all_chunks, bm25=fallback_bm25, top_k=top_k)
            return _filter_hits_by_domain(variants[0], raw_hits) if get_settings().domain_filter_enabled else raw_hits

    return _merge_ranked_hits(hit_groups, top_k=top_k)


def retrieve(question: str, chunks: list[dict], vectorizer, matrix, top_k: int | None, bm25=None,
             *, rerank: bool = False, rerank_candidate_k: int = 20) -> list[dict]:
    """
    执行检索逻辑。这里的 matrix 实际上是 FAISS 实例，或分库模式下的 shard_stores dict。

    Args:
        rerank: 是否启用 bge-reranker 二阶段精排。启用时 FAISS 粗排取 top rerank_candidate_k
                条，再经 reranker 精排到 top_k 条。
        rerank_candidate_k: 送 reranker 的候选数，默认 20。
    """
    # 分库检索路径：bm25 是 shard_bm25 dict（由 load_sharded_kb 返回）
    if get_settings().sharded_retrieval_enabled:
        result = _retrieve_sharded(question, chunks, matrix, bm25, top_k) if isinstance(bm25, dict) else _retrieve_sharded(question, chunks, matrix, {}, top_k)
        if rerank:
            result = _apply_rerank(question, result, top_k, rerank_candidate_k)
        return result

    faiss_store = matrix
    if not faiss_store:
        if not get_settings().bm25_fallback_enabled:
            logger.warning("FAISS 数据库未初始化，BM25 fallback 已关闭，返回空检索结果。")
            return []
        logger.warning("FAISS 数据库未初始化，使用当前 v2 chunks 的 BM25 fallback。")
        return fallback_search(question, chunks, bm25=bm25, top_k=top_k)

    query = normalize_query_text(normalize_text(question))
    variants = _build_query_variants(query) if get_settings().retrieval_variants_enabled else [_enhance_query_with_hints(query)]
    if not variants:
        return []
    per_variant_k = top_k if top_k is not None else max(10, len(chunks or []))
    chunks_cache = getattr(faiss_store, "_chunk_text_cache", None) or _build_chunk_text_cache(chunks)

    def _search_one_variant(variant: str) -> list[dict]:
        results = faiss_store.similarity_search_with_score(variant, k=per_variant_k)
        hits = []
        for doc, distance in results:
            hit = _doc_to_hit(doc, distance=distance, chunks_cache=chunks_cache)
            hit["retrieval_mode"] = "vector_fusion" if len(variants) > 1 else "vector"
            hit["query_variant"] = variant
            hit["why_retrieved"] = "FAISS similarity search matched one query variant in bilingual retrieval fusion."
            score_breakdown = hit.get("score_breakdown") if isinstance(hit.get("score_breakdown"), dict) else {}
            score_breakdown["query_variant"] = variant
            score_breakdown["variant_count"] = len(variants)
            hit["score_breakdown"] = score_breakdown
            hits.append(hit)
        hits = sorted(hits, key=lambda x: x["score"], reverse=True)
        if get_settings().domain_filter_enabled:
            hits = _filter_hits_by_domain(variant, hits)
        return hits

    def _search_one_variant_with_bm25(variant: str) -> list[dict]:
        """FAISS + BM25 双路检索 → RRF 融合。top_k 条 FAISS + top_k*4 条 BM25 粗排，RRF 精排到 top_k。"""
        # FAISS 语义检索（粗排扩大候选池）
        try:
            faiss_hits = _search_one_variant(variant)
        except Exception:
            faiss_hits = []
        # BM25 关键词检索（补充 FAISS 对专有名词/精确短语的盲区）
        rrf_candidate_k = (top_k or 5) * 4  # 候选池大小 = top_k × 4
        raw_bm25_hits = fallback_search(variant, chunks, bm25=bm25, top_k=rrf_candidate_k)
        # BM25 hit 标记模式，后置领域过滤
        for h in raw_bm25_hits:
            h["retrieval_mode"] = "bm25"
            h["query_variant"] = variant
        if get_settings().domain_filter_enabled:
            raw_bm25_hits = _filter_hits_by_domain(variant, raw_bm25_hits)
        # RRF 融合：语义相关性 + 关键词精确匹配
        return _rrf_fusion(faiss_hits, raw_bm25_hits, top_k=top_k or 5)

    if len(variants) == 1:
        try:
            hit_groups = [_search_one_variant_with_bm25(variants[0])]
        except Exception as exc:
            logger.error("混合检索失败: %s", exc)
            if not get_settings().bm25_fallback_enabled:
                return []
            raw_hits = fallback_search(variants[0], chunks, bm25=bm25, top_k=top_k)
            return _filter_hits_by_domain(variants[0], raw_hits) if get_settings().domain_filter_enabled else raw_hits
    else:
        hit_groups_by_variant: dict[str, list[dict]] = {}
        with ThreadPoolExecutor(max_workers=min(len(variants), 4)) as executor:
            futures = {executor.submit(_search_one_variant_with_bm25, variant): variant for variant in variants}
            for future in as_completed(futures):
                variant = futures[future]
                try:
                    hit_groups_by_variant[variant] = future.result()
                except Exception as exc:
                    logger.error("混合检索一路失败，保留其他 query variant 结果: %s", exc)
                    hit_groups_by_variant[variant] = []
        hit_groups = [hit_groups_by_variant.get(variant, []) for variant in variants]
        if not any(hit_groups):
            if not get_settings().bm25_fallback_enabled:
                return []
            raw_hits = fallback_search(variants[0], chunks, bm25=bm25, top_k=top_k)
            return _filter_hits_by_domain(variants[0], raw_hits) if get_settings().domain_filter_enabled else raw_hits

    result = _merge_ranked_hits(hit_groups, top_k=top_k)
    if rerank:
        result = _apply_rerank(question, result, top_k, rerank_candidate_k)
    return result


def _apply_rerank(question: str, hits: list[dict], top_k: int | None, candidate_k: int) -> list[dict]:
    """对检索结果应用 bge-reranker 精排。候选池不足 candidate_k 时直接用全部候选。"""
    if not hits:
        return []
    from marathon_qa_assistant.services.reranker import rerank_hits, reranker_available
    if not reranker_available():
        return hits[:top_k] if top_k is not None else hits
    candidates = hits[:candidate_k]
    final_k = top_k if top_k is not None else 5
    reranked = rerank_hits(question, candidates, top_k=final_k)
    return reranked


def build_answer(hits: list[dict]) -> str:
    """从检索结果构建简短回答片段（供调试/测试用）"""
    if not hits:
        return "未检索到有效证据，请尝试更具体的问题。"
    snippets = []
    for hit in hits[:3]:
        text = hit["text"].replace("\n", " ").strip()
        snippets.append(text[:220])
    return " ".join(snippets).strip()

def load_test_questions(questions_file: Path | None) -> list[str]:
    """加载测试问题列表"""
    if questions_file is None:
        return DEFAULT_TEST_QUESTIONS
    if not questions_file.exists():
        raise FileNotFoundError(f"测试问题文件不存在: {questions_file}")
    if questions_file.suffix.lower() == ".json":
        data = json.loads(questions_file.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("JSON 问题文件应为字符串数组")
        questions = [str(x).strip() for x in data if str(x).strip()]
        if not questions:
            raise ValueError("JSON 问题文件为空")
        return questions
    questions = []
    for line in questions_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            questions.append(line)
    if not questions:
        raise ValueError("问题文件为空")
    return questions

def run_rag_test(vector_dir: Path, output_file: Path, top_k: int, questions: list[str]) -> dict:
    """运行 RAG 检索基准测试"""
    chunks, vectorizer, matrix, bm25 = load_vector_kb(vector_dir)
    results = []
    for question in questions:
        hits = retrieve(question, chunks, vectorizer, matrix, top_k=top_k, bm25=bm25)
        citations = [
            {
                "source_file": x["source_file"],
                "page": x["page"],
                "chunk_id": x["chunk_id"],
                "score": x["score"],
            }
            for x in hits
        ]
        results.append(
            {
                "question": question,
                "answer": build_answer(hits),
                "citations": citations,
                "retrieved_chunks": hits,
            }
        )
    report = {
        "vector_dir": str(vector_dir),
        "top_k": top_k,
        "question_count": len(questions),
        "results": results,
    }
    output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["build", "test"], default="build")
    parser.add_argument("--input-dir", default="domain_docs")
    parser.add_argument("--output-dir", default="vector_kb")
    parser.add_argument("--report-file", default="vector_kb_report.json")
    parser.add_argument("--chunk-size", type=int, default=SENTENCE_WINDOW_CHUNK_SIZE)
    parser.add_argument("--chunk-overlap", type=int, default=SENTENCE_WINDOW_OVERLAP)
    parser.add_argument("--vector-dir", default="vector_kb")
    parser.add_argument("--test-output", default="rag_test_results.json")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--questions-file", default=None)
    args = parser.parse_args()

    if args.mode == "build":
        logger.info("Starting build mode...")
        input_dir = Path(args.input_dir).absolute()
        output_dir = Path(args.output_dir).absolute()
        report_file = Path(args.report_file).absolute()
        if not input_dir.exists():
            raise FileNotFoundError(f"输入目录不存在: {input_dir}")
        
        chunks, file_stats = collect_chunks(
            input_dir=input_dir,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        if not chunks:
            raise RuntimeError("未生成任何 chunk，无法构建向量库")
            
        vectorizer, matrix, bm25 = build_hybrid_indices(chunks)
        saved_paths = save_outputs(output_dir, chunks, vectorizer, matrix, bm25)
        
        report = {
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "chunk_size": args.chunk_size,
            "chunk_overlap": args.chunk_overlap,
            "total_chunks": len(chunks),
            "engine": "FAISS + Nomic Embedding",
            "files": file_stats,
            "artifacts": saved_paths,
        }
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Build finished successfully.")
        return

    vector_dir = Path(args.vector_dir).absolute()
    output_file = Path(args.test_output).absolute()
    questions_file = Path(args.questions_file).absolute() if args.questions_file else None
    questions = load_test_questions(questions_file)
    test_report = run_rag_test(vector_dir=vector_dir, output_file=output_file, top_k=args.top_k, questions=questions)
    print(json.dumps(test_report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
