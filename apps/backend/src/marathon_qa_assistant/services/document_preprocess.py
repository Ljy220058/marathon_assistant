import argparse
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# 配置日志
logger = logging.getLogger("document_preprocess")

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}

def normalize_text(text: str) -> str:
    """标准化文本内容，移除冗余空格和特殊字符"""
    if not text:
        return ""
    text = text.replace("\u00a0", " ")
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.split("\n")]
    cleaned_lines = [line for line in lines if line]
    return "\n".join(cleaned_lines).strip()

# ── P1: 非正文行过滤 ──

# 论文元数据/致谢行模式
_METADATA_PATTERNS = [
    re.compile(r'^(Supervision|Writing\s*[–-]\s*(original|review)|Correspondence|Funding|Acknowledgments?|Conflicts?\s*of\s*interest|Ethics\s*approval|Data\s*availability)\s*[:;]', re.IGNORECASE),
    re.compile(r'^(Received|Accepted|Published|Submitted)\s*[:;].*\d{4}', re.IGNORECASE),
    re.compile(r'^https?://doi\.org/', re.IGNORECASE),
]
# PubMed/数据库搜索语法
_PUBMED_PATTERNS = [
    re.compile(r'\b(OR|AND|NOT)\s+[A-Z]{2,4}\s*\(', re.IGNORECASE),  # OR SU (lateral...)
    re.compile(r'^\s*"[^"]+"\[(tiab|mesh|tw|ot)\]', re.IGNORECASE),
]
# 参考文献编号行
_REF_PATTERNS = [
    re.compile(r'^\s*\[\d+([,;–-]\d+)*\]\s'),  # [1], [1,2], [1-3]
    re.compile(r'^\s*\d+\.\s{2,}[A-Z]'),  # "1.  Author Name..."
]

def _line_is_table_row(line: str) -> bool:
    """检测表行：数字+符号占比过高"""
    stripped = line.strip()
    if len(stripped) < 5:
        return True  # 极短行当作碎片
    symbols_and_digits = sum(1 for c in stripped if not c.isalpha() and not c.isspace())
    return symbols_and_digits / max(len(stripped), 1) > 0.40

def _line_is_stat_fragment(line: str) -> bool:
    """检测孤立统计值行"""
    stripped = line.strip()
    if not stripped:
        return False
    # 匹配: "p < 0.01", "F(1,37) = 9.3", "−2.4 ± 6.3%", "73.0 ± 1.6"
    if re.match(r'^[pPFtχ][\s(<≤=]', stripped):
        return True
    if re.match(r'^[−\-–±\d][\d\s.,±\-–=<>()%]+$', stripped):
        return True
    return False

def filter_non_prose_lines(text: str) -> str:
    """过滤非正文行：表行、搜索语法、论文元数据、统计碎片、参考文献编号。
    在 normalize_text() 之后调用。"""
    if not text:
        return ""
    filtered: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) < 20 and (len(stripped.split()) < 5):
            continue  # 极短行丢弃
        if _line_is_table_row(stripped):
            continue
        if _line_is_stat_fragment(stripped):
            continue
        if any(p.search(stripped) for p in _METADATA_PATTERNS):
            continue
        if any(p.search(stripped) for p in _PUBMED_PATTERNS):
            continue
        if any(p.search(stripped) for p in _REF_PATTERNS):
            continue
        filtered.append(stripped)
    return "\n".join(filtered).strip()

def extract_pdf_text(file_path: Path) -> str:
    """从 PDF 文件中提取纯文本"""
    try:
        import fitz # PyMuPDF
    except Exception:
        fitz = None
    
    if fitz is not None:
        chunks = []
        try:
            with fitz.open(file_path) as doc:
                for page in doc:
                    page_text = page.get_text("text")
                    if page_text:
                        chunks.append(page_text)
            return "\n".join(chunks)
        except Exception as e:
            logger.error(f"PyMuPDF 提取 PDF 失败: {e}")

    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError("未安装可用的 PDF 文本抽取库，请安装 PyMuPDF 或 pypdf") from exc
    
    try:
        reader = PdfReader(str(file_path))
        chunks = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text:
                chunks.append(page_text)
        return "\n".join(chunks)
    except Exception as e:
        raise RuntimeError(f"pypdf 提取 PDF 失败: {e}")

def extract_docx_text(file_path: Path) -> str:
    """从 DOCX 文件中提取纯文本"""
    try:
        from docx import Document
    except Exception as exc:
        raise RuntimeError("处理 docx 需要安装 python-docx") from exc
    try:
        document = Document(str(file_path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text)
    except Exception as e:
        raise RuntimeError(f"提取 DOCX 失败: {e}")

def load_text(file_path: Path) -> str:
    """根据文件类型加载文本内容"""
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return extract_pdf_text(file_path)
    if ext == ".docx":
        return extract_docx_text(file_path)
    if ext in {".txt", ".md"}:
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            raise RuntimeError(f"读取文本文件失败: {e}")
    if ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}:
        import asyncio
        from marathon_qa_assistant.services.ocr_service import extract_text_from_image
        try:
            result = asyncio.run(extract_text_from_image(str(file_path)))
        except RuntimeError:
            loop = asyncio.get_event_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(lambda: asyncio.run(extract_text_from_image(str(file_path))))
                result = future.result(timeout=120)
        text = result.get("text", "")
        if not text.strip():
            raise RuntimeError(f"图片未识别到有效文字: {file_path.name}")
        return text
    raise ValueError(f"不支持的文件格式: {file_path.name}")

def process_file(file_path: Path, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """处理单个文件并（可选地）保存清理后的结果"""
    raw = load_text(file_path)
    cleaned = normalize_text(raw)
    
    result = {
        "source_file": file_path.name,
        "source_ext": file_path.suffix.lower(),
        "raw_chars": len(raw),
        "cleaned_chars": len(cleaned),
    }
    
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{file_path.stem}.cleaned.txt"
        output_file.write_text(cleaned, encoding="utf-8")
        result["output_file"] = output_file.name
        
    return result

def main() -> None:
    """命令行工具入口"""
    parser = argparse.ArgumentParser(description="马拉松助手文档预处理工具")
    parser.add_argument("--input-dir", default="domain_docs", help="输入文档目录")
    parser.add_argument("--output-dir", default="cleaned_docs", help="清理后的文档输出目录")
    parser.add_argument("--report-file", default="preprocess_report.json", help="处理报告保存路径")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).absolute()
    output_dir = Path(args.output_dir).absolute()
    report_file = Path(args.report_file).absolute()

    if not input_dir.exists():
        logger.error(f"输入目录不存在: {input_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    
    files = sorted([f for f in input_dir.iterdir() if f.is_file()], key=lambda p: p.name.lower())
    
    for file_path in files:
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            logger.info(f"正在处理: {file_path.name}")
            records.append(process_file(file_path, output_dir))
        except Exception as exc:
            logger.error(f"处理 {file_path.name} 出错: {exc}")
            records.append({
                "source_file": file_path.name,
                "source_ext": file_path.suffix.lower(),
                "error": str(exc),
            })

    summary = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "total_files": len(records),
        "success_files": sum(1 for x in records if "error" not in x),
        "failed_files": sum(1 for x in records if "error" in x),
        "records": records,
    }
    
    report_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    main()
