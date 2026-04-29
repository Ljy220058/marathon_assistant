import os
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("ocr_service")

# ============================================================
# PaddleOCR 延迟加载
# ============================================================
_paddle_ocr = None
_paddle_ocr_available = None

def _get_paddle_ocr():
    global _paddle_ocr, _paddle_ocr_available
    if _paddle_ocr_available is not None:
        return _paddle_ocr if _paddle_ocr_available else None
    try:
        from paddleocr import PaddleOCR
        # 部分版本可能不支持 show_log 参数，若报错则移除
        _paddle_ocr = PaddleOCR(lang='ch', use_angle_cls=True)
        _paddle_ocr_available = True
        logger.info("PaddleOCR 初始化成功")
    except Exception as e:
        logger.warning(f"PaddleOCR 初始化失败: {e}")
        _paddle_ocr_available = False
    return _paddle_ocr if _paddle_ocr_available else None


# ============================================================
# Pillow 延迟加载
# ============================================================
def _load_image(image_path: str):
    try:
        from PIL import Image
        return Image.open(image_path)
    except Exception as e:
        raise RuntimeError(f"无法打开图片文件: {e}")


# ============================================================
# OCR 质量评估
# ============================================================
def evaluate_ocr_quality(raw_lines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    对 OCR 识别结果进行多维度质量评估
    
    Args:
        raw_lines: PaddleOCR 返回结果列表，每项包含 text 和 confidence
    
    Returns:
        质量评分字典：
        - overall_score: 总体质量分 (0-100)
        - avg_confidence: 平均置信度
        - char_count: 识别的总字符数
        - line_count: 识别行数
        - low_conf_ratio: 低置信度行占比
        - quality_level: quality等级 (excellent/good/fair/poor)
        - warnings: 质量警告列表
    """
    if not raw_lines:
        return {
            "overall_score": 0,
            "avg_confidence": 0,
            "char_count": 0,
            "line_count": 0,
            "low_conf_ratio": 1.0,
            "quality_level": "poor",
            "warnings": ["OCR 未识别到任何文本"],
        }
    
    confidences = []
    char_counts = []
    full_text_parts = []
    
    for item in raw_lines:
        text = item.get("text", "")
        conf = item.get("confidence", 0)
        confidences.append(conf)
        full_text_parts.append(text)
        char_counts.append(len(text))
    
    full_text = "".join(full_text_parts)
    avg_conf = sum(confidences) / len(confidences)
    total_chars = sum(char_counts)
    
    # 低置信度行占比（置信度 < 0.6 视为低质量）
    low_conf_count = sum(1 for c in confidences if c < 0.6)
    low_conf_ratio = low_conf_count / len(confidences)
    
    warnings = []
    
    # 文本连贯性检查
    if total_chars < 10:
        warnings.append("识别文本过短（可能为空白图片或图表）")
    
    if low_conf_ratio > 0.5:
        warnings.append(f"超过{low_conf_ratio*100:.0f}%的行置信度偏低")
    
    # 文本可读性检查：非字母数字字符占比
    alphanum = sum(1 for ch in full_text if ch.isalnum() or ch.isspace())
    if total_chars > 0:
        junk_ratio = 1 - (alphanum / total_chars)
        if junk_ratio > 0.4:
            warnings.append("文本中存在大量乱码或非可读字符")
    
    # 综合评分
    conf_score = min(avg_conf * 100, 100)
    length_score = min(total_chars / 50 * 20, 20)  # 50字符以上给满分
    quality_penalty = low_conf_ratio * 30 + (0 if not warnings else len(warnings) * 5)
    overall_score = max(0, min(100, conf_score * 0.5 + length_score + 30 - quality_penalty))
    
    if overall_score >= 80:
        quality_level = "excellent"
    elif overall_score >= 60:
        quality_level = "good"
    elif overall_score >= 40:
        quality_level = "fair"
    else:
        quality_level = "poor"
    
    return {
        "overall_score": round(overall_score, 1),
        "avg_confidence": round(avg_conf, 4),
        "char_count": total_chars,
        "line_count": len(raw_lines),
        "low_conf_ratio": round(low_conf_ratio, 4),
        "quality_level": quality_level,
        "warnings": warnings,
    }


# ============================================================
# PaddleOCR 图片文字识别
# ============================================================
async def ocr_image(image_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    使用 PaddleOCR 对图片进行文字识别，并返回质量评估
    
    Args:
        image_path: 图片文件路径
    
    Returns:
        (extracted_text, quality_report)
    """
    ocr = _get_paddle_ocr()
    
    if ocr is None:
        raise RuntimeError("PaddleOCR 未就绪，无法执行 OCR")
    
    def _run_ocr():
        result = ocr.ocr(image_path)
        if not result or not result[0]:
            return []
        lines = []
        for line_info in result[0]:
            box = line_info[0]
            text_info = line_info[1]
            lines.append({
                "text": text_info[0],
                "confidence": text_info[1],
                "box": box,
            })
        return lines
    
    raw_lines = await asyncio.to_thread(_run_ocr)
    
    if not raw_lines:
        text = ""
    else:
        text = "\n".join([item["text"] for item in raw_lines])
    
    quality = evaluate_ocr_quality(raw_lines)
    
    logger.info(f"OCR 完成: {len(raw_lines)} 行, 质量: {quality['quality_level']}, 评分: {quality['overall_score']}")
    
    return text, quality


# ============================================================
# 主入口：纯 OCR 图片文字提取
# ============================================================
async def extract_text_from_image(image_path: str) -> Dict[str, Any]:
    """
    纯 OCR 图片文字提取：仅使用 PaddleOCR
    
    Args:
        image_path: 图片文件路径
    
    Returns:
        {
            "text": str,              # 提取的文本
            "engine": str,            # 使用的引擎 (paddleocr)
            "ocr_quality": dict,      # OCR 质量评估
            "vlm_used": bool,         # 始终为 False（保留字段兼容）
        }
    """
    ocr_text = ""
    ocr_quality = None
    vlm_used = False
    engine = "paddleocr"
    
    try:
        ocr_text, ocr_quality = await ocr_image(image_path)
        engine = "paddleocr"
    except Exception as e:
        logger.warning(f"PaddleOCR 识别失败: {e}")
        ocr_text = ""
        ocr_quality = evaluate_ocr_quality([])
    
    return {
        "text": ocr_text,
        "engine": engine,
        "ocr_quality": ocr_quality,
        "vlm_used": vlm_used,
    }


# ============================================================
# 图片预处理工具
# ============================================================
def preprocess_image_for_ocr(image_path: str) -> Optional[str]:
    """
    对图片进行 OCR 预处理（灰度化、增强对比度），返回处理后图片路径
    """
    try:
        from PIL import Image, ImageEnhance
        img = Image.open(image_path)
        # 转为灰度
        if img.mode != 'L':
            img = img.convert('L')
        # 增强对比度
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        # 保存临时文件
        tmp_path = image_path + ".preprocessed.png"
        img.save(tmp_path)
        return tmp_path
    except Exception as e:
        logger.warning(f"图片预处理失败: {e}")
        return None


ocr_service = extract_text_from_image
