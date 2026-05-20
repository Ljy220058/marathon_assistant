import asyncio
import base64
import httpx
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

logger = logging.getLogger("multimodal_service")

class MultimodalService:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/chat"
        self._ocr = None  # 延迟加载 OCR 引擎以节省启动内存

    def get_ocr_engine(self):
        """延迟初始化 PaddleOCR"""
        if self._ocr is None and PaddleOCR is not None:
            try:
                # PaddleOCR 3.5.0 参数适配
                self._ocr = PaddleOCR(use_textline_orientation=True, lang="ch")
                logger.info("PaddleOCR 引擎初始化成功")
            except Exception as e:
                logger.error(f"PaddleOCR 初始化失败: {e}")
        return self._ocr

    async def run_ocr(self, image_path: str) -> str:
        """执行本地 OCR 识别"""
        ocr = self.get_ocr_engine()
        if not ocr:
            return ""
        
        try:
            # 在线程池中运行同步的 OCR 任务
            result = await asyncio.to_thread(ocr.ocr, image_path)
            if not result or not result[0]:
                return ""
            
            # 拼接识别到的文本
            texts = [line[1][0] for line in result[0]]
            return "\n".join(texts)
        except Exception as e:
            logger.error(f"OCR 识别出错: {e}")
            return ""

    def encode_image(self, image_path: str) -> str:
        """将图像文件编码为 Base64 字符串"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    async def call_vlm(self, model: str, prompt: str, image_path: str, log_callback: Optional[Callable] = None) -> str:
        """调用 Ollama VLM 模型"""
        def _log(msg: str):
            logger.info(msg)
            if log_callback:
                if asyncio.iscoroutinefunction(log_callback):
                    asyncio.create_task(log_callback(msg))
                else:
                    log_callback(msg)

        try:
            start_time = time.monotonic()
            _log(f"开始调用 VLM 模型 {model}, 图片路径: {image_path}")
            if not os.path.exists(image_path):
                err_msg = f"错误: 文件 {image_path} 不存在"
                logger.error(err_msg)
                if log_callback:
                    if asyncio.iscoroutinefunction(log_callback): asyncio.create_task(log_callback(err_msg))
                    else: log_callback(err_msg)
                return err_msg

            file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
            _log(f"开始读取图片并进行 Base64 编码（{file_size_mb:.2f} MB）")

            # 使用 asyncio.to_thread 处理同步的图片编码以避免阻塞事件循环
            image_base64 = await asyncio.to_thread(self.encode_image, image_path)
            encode_elapsed = time.monotonic() - start_time
            _log(f"图片编码完成（耗时 {encode_elapsed:.1f}s），准备发送请求到 {self.api_url}")
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [image_base64]
                    }
                ],
                "stream": False
            }
            
            timeout_config = httpx.Timeout(300.0, connect=10.0, read=300.0) 
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                _log(f"请求已发出，正在等待模型 {model} 返回结果...")
                response = await client.post(self.api_url, json=payload)
                
                if response.status_code != 200:
                    error_detail = response.text
                    if "out of memory" in error_detail.lower() or response.status_code == 500:
                        if model == "llama3.2-vision:11b":
                            _log(f"模型 {model} 显存不足，尝试切换到 llava:7b")
                            return await self.call_vlm("llava:7b", prompt, image_path, log_callback)
                        return f"错误: 模型 {model} 加载失败，可能是显存不足。"
                    return f"错误: 模型返回 {response.status_code}"
                
                result = response.json()
                total_elapsed = time.monotonic() - start_time
                _log(f"VLM 响应成功（总耗时 {total_elapsed:.1f}s），正在提取内容...")
                return result.get("message", {}).get("content", "无回复内容")
        except httpx.TimeoutException:
            if model == "llama3.2-vision:11b":
                _log(f"模型 {model} 调用超时，尝试切换到 llava:7b")
                return await self.call_vlm("llava:7b", prompt, image_path, log_callback)
            return "错误: 模型调用超时"
        except Exception as e:
            return f"错误: {str(e)}"

    async def compare_vlms(self, image_path: str, prompt: str = "请详细描述这张图片/图表的内容。", log_callback: Optional[Callable] = None) -> Dict[str, str]:
        """同时调用两个模型进行对比"""
        models = ["llava:7b", "llama3.2-vision:11b"]
        results = {}
        for model in models:
            results[model] = await self.call_vlm(model, prompt, image_path, log_callback)
        return results

    async def smart_analyze_image(self, image_path: str, log_callback: Optional[Callable] = None) -> str:
        """图片文本提取主链路：仅执行本地 OCR，不再回退 VLM。"""
        def _log(msg: str):
            if log_callback:
                if asyncio.iscoroutinefunction(log_callback): asyncio.create_task(log_callback(msg))
                else: log_callback(msg)
            logger.info(msg)

        if not os.path.exists(image_path):
            err_msg = f"错误: 文件 {image_path} 不存在"
            logger.error(err_msg)
            return err_msg

        _log("⚡ 正在执行本地 OCR 文本提取...")
        start_time = time.monotonic()
        ocr_text = await self.run_ocr(image_path)
        ocr_elapsed = time.monotonic() - start_time

        if ocr_text.strip():
            _log(f"✅ OCR 识别成功（耗时 {ocr_elapsed:.1f}s），字符数: {len(ocr_text)}")
            return f"[OCR 识别文本]:\n{ocr_text}"

        _log(f"⚠️ OCR 未识别到有效文本（耗时 {ocr_elapsed:.1f}s）")
        return "错误: OCR 未识别到有效文本"

    async def extract_and_analyze_pdf(self, pdf_path: str, output_dir: str = "temp_images", log_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """从 PDF 中提取文本：优先提取矢量文本，其次对页面图片执行 OCR。"""
        if not fitz:
            return []
            
        def _log(msg: str):
            if log_callback:
                if asyncio.iscoroutinefunction(log_callback): asyncio.create_task(log_callback(msg))
                else: log_callback(msg)
            logger.info(msg)

        Path(output_dir).mkdir(exist_ok=True)
        doc = fitz.open(pdf_path)
        visual_insights = []
        
        _log(f"📄 开始分析 PDF: {os.path.basename(pdf_path)}，共 {len(doc)} 页")

        for page_index in range(len(doc)):
            page = doc[page_index]
            
            # 1. 优先尝试提取矢量文本 (瞬时)
            page_text = page.get_text().strip()
            if len(page_text) > 100:
                _log(f"🚀 第 {page_index+1} 页提取到大量矢量文本，跳过 OCR/VLM")
                visual_insights.append({
                    "page": page_index + 1,
                    "method": "vector_text",
                    "description": f"[PDF 矢量文本]:\n{page_text}"
                })
                continue

            # 2. 如果文本很少，提取图片或对整个页面截图进行分析
            image_list = page.get_images()
            if not image_list:
                # 页面没有嵌入图片但文本很少，可能是扫描件，对整页进行渲染
                _log(f"📸 第 {page_index+1} 页疑似扫描件，正在渲染页面图像...")
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # 2倍缩放保证清晰度
                image_path = Path(output_dir) / f"page_{page_index+1}_render.png"
                pix.save(str(image_path))
                
                description = await self.smart_analyze_image(str(image_path), log_callback)
                visual_insights.append({
                    "page": page_index + 1, 
                    "method": "render_ocr",
                    "image_path": str(image_path), 
                    "description": description
                })
            else:
                # 处理页面内的图片
                for img_index, img in enumerate(image_list):
                    if img_index >= 3: break # 每页最多分析3张图，防止任务过重
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_path = Path(output_dir) / f"page{page_index+1}_img{img_index+1}.{base_image['ext']}"
                    
                    with open(image_path, "wb") as f:
                        f.write(base_image["image"])
                    
                    _log(f"🔍 正在分析第 {page_index+1} 页第 {img_index+1} 张图片...")
                    description = await self.smart_analyze_image(str(image_path), log_callback)
                    visual_insights.append({
                        "page": page_index + 1, 
                        "method": "image_ocr",
                        "image_path": str(image_path), 
                        "description": description
                    })

        doc.close()
        return visual_insights

multimodal_service = MultimodalService()
