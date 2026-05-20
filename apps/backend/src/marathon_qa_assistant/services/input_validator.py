import os
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("input_validator")

# ============================================================
# 支持的文件类型
# ============================================================
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".doc"}
ALL_SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS

MIME_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
}

# 内容安全敏感词
SENSITIVE_KEYWORDS = ["exec(", "eval(", "rm -rf", "DROP TABLE", "<script", "<?php"]


# ============================================================
# 文件类型检测 (python-magic)
# ============================================================
def _detect_mime_type(file_path: str) -> Optional[str]:
    try:
        import magic
        mime = magic.from_file(file_path, mime=True)
        return mime
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"python-magic 检测失败: {e}")
    
    # fallback: 文件头检测
    try:
        with open(file_path, "rb") as f:
            header = f.read(16)
        if header[:4] == b'\x89PNG':
            return "image/png"
        if header[:2] == b'\xff\xd8':
            return "image/jpeg"
        if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
            return "image/webp"
        if header[:2] == b'BM':
            return "image/bmp"
        if header[:4] == b'%PDF':
            return "application/pdf"
        if header[:2] == b'PK' and b'word/' in header:
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    except Exception:
        pass
    
    return None


def _check_file_size(file_path: str, max_size_mb: int = 100) -> Tuple[bool, str]:
    """检查文件大小"""
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"文件过大 ({size_mb:.1f}MB)，上限 {max_size_mb}MB"
    return True, f"{size_mb:.1f}MB"


def _check_image_resolution(file_path: str, min_pixels: int = 100, max_pixels: int = 8000) -> Tuple[bool, str]:
    """检查图片分辨率"""
    ext = Path(file_path).suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        return True, ""
    try:
        from PIL import Image
        with Image.open(file_path) as img:
            w, h = img.size
        if w < min_pixels or h < min_pixels:
            return False, f"图片分辨率过低 ({w}x{h})，最小 {min_pixels}x{min_pixels}"
        if w > max_pixels or h > max_pixels:
            return False, f"图片分辨率过高 ({w}x{h})，最大 {max_pixels}x{max_pixels}"
        return True, f"{w}x{h}"
    except Exception as e:
        return True, ""  # 非图片文件不检查


def _check_content_safety(text: str) -> Tuple[bool, List[str]]:
    """检查文本内容安全性"""
    hits = []
    lower = text.lower()
    for kw in SENSITIVE_KEYWORDS:
        if kw.lower() in lower:
            hits.append(kw)
    return len(hits) == 0, hits


# ============================================================
# 主校验入口
# ============================================================
def validate_file(file_path: str) -> Dict[str, Any]:
    """
    对上传文件进行全面校验
    
    Args:
        file_path: 文件路径
    
    Returns:
        {
            "valid": bool,
            "file_type": str,         # 检测到的真实 MIME 类型
            "ext_match": bool,        # 扩展名与真实类型是否匹配
            "size_ok": bool,
            "size_info": str,
            "resolution_ok": bool,
            "resolution_info": str,
            "errors": list[str],
            "warnings": list[str],
        }
    """
    result = {
        "valid": True,
        "file_type": "unknown",
        "ext_match": True,
        "size_ok": True,
        "size_info": "",
        "resolution_ok": True,
        "resolution_info": "",
        "errors": [],
        "warnings": [],
    }
    
    if not os.path.exists(file_path):
        result["valid"] = False
        result["errors"].append("文件不存在")
        return result
    
    # 1. 检测真实 MIME 类型
    mime = _detect_mime_type(file_path)
    if mime:
        result["file_type"] = mime
    
    ext = Path(file_path).suffix.lower()
    
    # 2. 扩展名与真实类型一致性
    if mime and ext:
        expected_exts = {
            "image/png": [".png"],
            "image/jpeg": [".jpg", ".jpeg"],
            "image/webp": [".webp"],
            "image/bmp": [".bmp"],
            "image/tiff": [".tiff", ".tif"],
            "application/pdf": [".pdf"],
            "text/plain": [".txt", ".md"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
            "application/msword": [".doc"],
        }
        if mime in expected_exts and ext not in expected_exts[mime]:
            result["ext_match"] = False
            result["warnings"].append(f"文件扩展名 {ext} 与实际类型 {mime} 不匹配")
    
    # 3. 文件大小检查
    size_ok, size_info = _check_file_size(file_path)
    result["size_ok"] = size_ok
    result["size_info"] = size_info
    if not size_ok:
        result["valid"] = False
        result["errors"].append(size_info)
    
    # 4. 图片分辨率检查
    res_ok, res_info = _check_image_resolution(file_path)
    result["resolution_ok"] = res_ok
    result["resolution_info"] = res_info
    if not res_ok:
        result["valid"] = False
        result["errors"].append(res_info)
    
    # 5. 扩展名是否在支持列表中
    if ext not in ALL_SUPPORTED_EXTENSIONS:
        result["valid"] = False
        result["errors"].append(f"不支持的文件格式: {ext}")
    
    # 6. 文本文件内容安全检查
    if ext in {".txt", ".md"}:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()[:10000]
            safe, hits = _check_content_safety(content)
            if not safe:
                result["warnings"].append(f"文本包含潜在风险内容: {', '.join(hits)}")
        except Exception:
            pass
    
    return result


def validate_pasted_text(text: str) -> Dict[str, Any]:
    """
    对用户粘贴的文本进行校验
    
    Args:
        text: 用户粘贴的文本
    
    Returns:
        {
            "valid": bool,
            "char_count": int,
            "line_count": int,
            "is_empty": bool,
            "is_too_short": bool,
            "is_too_long": bool,
            "safety_ok": bool,
            "warnings": list[str],
        }
    """
    result = {
        "valid": True,
        "char_count": len(text),
        "line_count": len(text.splitlines()) if text else 0,
        "is_empty": False,
        "is_too_short": False,
        "is_too_long": False,
        "safety_ok": True,
        "warnings": [],
    }
    
    stripped = text.strip()
    
    if not stripped:
        result["valid"] = False
        result["is_empty"] = True
        result["warnings"].append("文本为空")
        return result
    
    if len(stripped) < 10:
        result["is_too_short"] = True
        result["warnings"].append("文本过短（少于10个字符），可能无法提供有效的知识检索")
    
    if len(stripped) > 50000:
        result["is_too_long"] = True
        result["warnings"].append("文本较长（超过50000字符），请注意系统性能")
    
    safe, hits = _check_content_safety(stripped)
    if not safe:
        result["safety_ok"] = False
        result["warnings"].append(f"文本包含潜在风险内容: {', '.join(hits)}")
    
    return result


def save_pasted_text(text: str, output_dir: Path, prefix: str = "pasted") -> Optional[Path]:
    """
    将粘贴文本保存为 .txt 文件，返回文件路径
    
    Args:
        text: 粘贴的文本内容
        output_dir: 输出目录
        prefix: 文件名前缀
    
    Returns:
        保存后的文件路径，失败返回 None
    """
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.txt"
    file_path = output_dir / filename
    
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(text, encoding="utf-8")
        logger.info(f"粘贴文本已保存: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"保存粘贴文本失败: {e}")
        return None


def validate_ocr_result(ocr_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    对 OCR 提取结果进行质量校验，决定是否采纳进知识库
    
    Args:
        ocr_result: ocr_service.extract_text_from_image 的返回结果
    
    Returns:
        {
            "accepted": bool,          # 是否采纳
            "reason": str,             # 不采纳的原因
            "quality_summary": str,    # 质量摘要
            "suggested_action": str,   # 建议操作
        }
    """
    quality = ocr_result.get("ocr_quality", {})
    text = ocr_result.get("text", "")
    engine = ocr_result.get("engine", "unknown")
    
    quality_level = quality.get("quality_level", "poor")
    overall_score = quality.get("overall_score", 0)
    char_count = quality.get("char_count", 0)
    warnings = quality.get("warnings", [])
    
    if quality_level == "poor" and char_count < 5:
        return {
            "accepted": False,
            "reason": "OCR 未能识别到有效文本内容",
            "quality_summary": f"引擎: {engine} | 字符数: {char_count} | 评分: {overall_score}",
            "suggested_action": "建议使用更清晰的图片，或手动输入文字内容",
        }
    
    if quality_level == "poor":
        return {
            "accepted": True,
            "reason": "",
            "quality_summary": f"引擎: {engine} | 字符数: {char_count} | 评分: {overall_score} (低质量，已标记)",
            "suggested_action": f"OCR 质量较低，建议人工复核。警告: {', '.join(warnings[:3])}",
        }
    
    return {
        "accepted": True,
        "reason": "",
        "quality_summary": f"引擎: {engine} | 字符数: {char_count} | 评分: {overall_score} | 等级: {quality_level}",
        "suggested_action": "",
    }


# ============================================================
# 便捷函数：统一输入校验管道
# ============================================================
def validate_and_prepare_input(
    input_type: str,
    file_path: Optional[str] = None,
    pasted_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    统一输入校验入口
    
    Args:
        input_type: "file" 或 "pasted_text"
        file_path: 文件路径（input_type="file" 时必需）
        pasted_text: 粘贴文本（input_type="pasted_text" 时必需）
    
    Returns:
        {"accepted": bool, "errors": list, "warnings": list, "metadata": dict}
    """
    if input_type == "file" and file_path:
        return validate_file(file_path)
    
    if input_type == "pasted_text" and pasted_text is not None:
        return validate_pasted_text(pasted_text)
    
    return {"accepted": False, "errors": ["无效的输入类型"], "warnings": [], "metadata": {}}
