import base64
import httpx
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

logger = logging.getLogger("multimodal_module")

class MultimodalModule:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/chat"

    def encode_image(self, image_path: str) -> str:
        """将图像文件编码为 Base64 字符串"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    async def call_vlm(self, model: str, prompt: str, image_path: str) -> str:
        """调用 Ollama VLM 模型"""
        try:
            logger.info(f"开始调用 VLM 模型 {model}, 图片路径: {image_path}")
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return f"错误: 文件 {image_path} 不存在"
                
            # 使用 cl.make_async 处理同步的图片编码（如果在 Chainlit 环境中）
            image_base64 = self.encode_image(image_path)
            logger.info(f"图片编码完成，准备发送请求到 {self.api_url}")
            
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
            
            # 增加更细致的超时控制 (针对 11B 模型加载建议 300s)
            timeout_config = httpx.Timeout(300.0, connect=10.0, read=300.0) 
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                logger.info(f"正在向 Ollama 发送 POST 请求 (模型: {model})...")
                response = await client.post(self.api_url, json=payload)
                logger.info(f"Ollama 响应完成, 状态码: {response.status_code}")
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"模型 {model} 返回错误状态码 {response.status_code}: {error_detail}")
                    
                    # 针对 llama3.2-vision 的常见内存不足错误提供更友好的提示
                    if "out of memory" in error_detail.lower() or response.status_code == 500:
                        if model == "llama3.2-vision:11b":
                            logger.info("尝试自动回退到 llava:7b...")
                            return await self.call_vlm("llava:7b", prompt, image_path)
                        return f"错误: 模型 {model} 加载失败，可能是显存不足。建议尝试 llava:7b 或关闭其他占用显存的程序。"
                        
                    return f"错误: 模型返回 {response.status_code}"
                
                result = response.json()
                return result.get("message", {}).get("content", "无回复内容")
        except httpx.TimeoutException:
            logger.error(f"调用模型 {model} 超时 (300s)")
            if model == "llama3.2-vision:11b":
                logger.info("超时回退: 尝试使用 llava:7b...")
                return await self.call_vlm("llava:7b", prompt, image_path)
            return "错误: 模型调用超时，请检查 Ollama 是否响应过慢（11B 模型加载可能需要较长时间）"
        except Exception as e:
            logger.error(f"调用模型 {model} 发生异常: {type(e).__name__}: {str(e)}")
            return f"错误: {str(e)}"

    async def compare_vlms(self, image_path: str, prompt: str = "请详细描述这张图片/图表的内容，提取所有关键数据、趋势和实体信息。") -> Dict[str, str]:
        """同时调用两个模型进行对比"""
        models = ["llava:7b", "llama3.2-vision:11b"]
        results = {}
        
        for model in models:
            logger.info(f"正在调用 {model} 分析图片...")
            results[model] = await self.call_vlm(model, prompt, image_path)
            
        return results

    async def extract_and_analyze_pdf(self, pdf_path: str, output_dir: str = "temp_images") -> List[Dict[str, Any]]:
        """从 PDF 中提取图片并使用 VLM 分析"""
        if not fitz:
            logger.error("PyMuPDF (fitz) is not installed.")
            return []
            
        Path(output_dir).mkdir(exist_ok=True)
        doc = fitz.open(pdf_path)
        visual_insights = []
        
        # 限制只处理前 10 张图片，避免 API 调用过多
        image_count = 0
        for page_index in range(len(doc)):
            if image_count >= 10: break
            
            page = doc[page_index]
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                if image_count >= 10: break
                
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                image_filename = f"page{page_index+1}_img{img_index+1}.{image_ext}"
                image_path = Path(output_dir) / image_filename
                
                with open(image_path, "wb") as f:
                    f.write(image_bytes)
                
                logger.info(f"正在分析 PDF 图片: {image_filename}...")
                description = await self.call_vlm(
                    "llama3.2-vision:11b", 
                    "这张图片是从科研 PDF 中提取的，请描述其中的图表、数据或关键视觉信息。", 
                    str(image_path)
                )
                
                visual_insights.append({
                    "page": page_index + 1,
                    "image_path": str(image_path),
                    "description": description
                })
                image_count += 1
                
        doc.close()
        return visual_insights

multimodal_module = MultimodalModule()
