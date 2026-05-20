import httpx
import asyncio
import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger("wiki_agent")

class WikiAgent:
    """维基百科检索智能体：提供外部通用知识补充"""
    
    def __init__(self):
        self.api_url_zh = "https://zh.wikipedia.org/w/api.php"
        self.api_url_en = "https://en.wikipedia.org/w/api.php"
        self.timeout = 5.0
        # 维基百科 API 要求必须提供 User-Agent
        self.headers = {
            "User-Agent": "MarathonOS-Agent/1.0 (https://github.com/your-repo; mailto:your-email@example.com) httpx/0.24.1"
        }

    async def search(self, entities: List[str], lang: str = "zh") -> str:
        """对多个实体进行维基百科检索并汇总摘要"""
        if not entities:
            return ""
        
        # 预处理实体：清洗冗余字符，提取核心名词
        cleaned_entities = self._clean_entities(entities)
        
        url = self.api_url_zh if lang == "zh" else self.api_url_en
        tasks = [self._get_summary(entity, url) for entity in cleaned_entities[:3]] # 限制前 3 个实体
        summaries = await asyncio.gather(*tasks)
        
        # 如果中文检索失败且实体包含英文/专业缩写，尝试英文维基
        # 这里的 summaries 已经包含了经过模糊匹配的结果
        valid_summaries = []
        seen_titles = set()
        
        for s in summaries:
            if not s: continue
            # 提取标题进行去重，标题格式为 【维基百科 - Title】
            title_match = re.search(r'【维基百科 - (.*?)】', s)
            if title_match:
                title = title_match.group(1)
                if title in seen_titles: continue
                seen_titles.add(title)
            valid_summaries.append(s)

        if not valid_summaries and lang == "zh":
            # 过滤出包含英文字符的实体进行英文重试
            en_entities = [e for e in cleaned_entities if any(c.isalpha() for c in e)]
            if en_entities:
                logger.info(f"Wiki 中文检索无果，尝试英文检索: {en_entities}")
                en_tasks = [self._get_summary(entity, self.api_url_en) for entity in en_entities[:2]]
                en_summaries = await asyncio.gather(*en_tasks)
                for s in en_summaries:
                    if not s: continue
                    title_match = re.search(r'【维基百科 - (.*?)】', s)
                    if title_match:
                        title = title_match.group(1)
                        if title in seen_titles: continue
                        seen_titles.add(title)
                    valid_summaries.append(s)

        if not valid_summaries:
            return ""
        
        return "\n\n".join(valid_summaries)

    def _clean_entities(self, entities: List[str]) -> List[str]:
        """清洗实体列表，移除语气词和过长的描述"""
        cleaned = []
        noise_words = [
            "是什么", "怎么跑", "如何", "的原理", "建议", "计划", "课表", "练习",
            "训练方法", "提升", "提高", "怎么做", "详解", "教程", "指南", "方案",
            "基础知识", "定义", "意义", "作用"
        ]
        for ent in entities:
            # 1. 移除常见噪音词
            temp = ent
            for nw in noise_words:
                temp = temp.replace(nw, "")
            
            # 2. 特殊缩写映射 (常见运动科学术语)
            abbreviation_map = {
                "VO2MAX": "VO2 max",
                "LTHR": "Lactate threshold",
                "MAF180": "MAF Method",
                "FARTLEK": "Fartlek",
                "HIIT": "High-intensity interval training"
            }
            if temp.upper() in abbreviation_map:
                cleaned.append(abbreviation_map[temp.upper()])
            
            # 3. 处理中英文混合实体
            brackets = re.findall(r'([^(（]+)[(（]([^)）]+)[)）]', temp)
            if brackets:
                for outside, inside in brackets:
                    cleaned.append(outside.strip())
                    cleaned.append(inside.strip())
            else:
                cleaned.append(temp.strip())
        
        # 最终过滤：去重，长度限制，移除单字（除非是特殊术语）
        final_cleaned = []
        for c in cleaned:
            if c and c not in final_cleaned:
                if len(c) > 1:
                    final_cleaned.append(c)
        
        logger.info(f"Entities cleaned: {entities} -> {final_cleaned}")
        return final_cleaned

    async def _get_summary(self, entity: str, url: str) -> str:
        """获取单个实体的维基百科摘要，支持多级搜索回退"""
        # 增加领域限定词以提高搜索准确度
        domain_keywords = " (running exercise sports)"
        
        # 1. 尝试直接通过标题获取
        summary = await self._fetch_by_title(entity, url)
        if summary:
            return summary
            
        # 2. 如果失败，尝试通过搜索获取匹配的标题列表
        # 尝试带领域词的搜索
        search_queries = [entity + domain_keywords, entity]
        
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            for q in search_queries:
                search_params = {
                    "action": "query",
                    "format": "json",
                    "list": "search",
                    "srsearch": q,
                    "srlimit": 3
                }
                
                try:
                    resp = await client.get(url, params=search_params)
                    search_data = resp.json()
                    search_results = search_data.get("query", {}).get("search", [])
                    
                    for res in search_results:
                        best_title = res["title"]
                        if best_title.lower() == entity.lower(): continue
                            
                        summary = await self._fetch_by_title(best_title, url)
                        if summary:
                            # 验证摘要内容是否与跑步/运动相关，防止匹配到火车站、电视剧等
                            content_lower = summary.lower()
                            title_lower = best_title.lower()
                            
                            # 关键词过滤
                            relevance_keywords = ["run", "sport", "exercise", "training", "heart", "physiolog", "muscle", "fitness", "athlete", "跑", "运动", "训练", "心率", "生理", "肌肉", "耐力", "体能", "选手", "oxygen", "lactate", "threshold", "endurance", "aerobic", "anaerobic"]
                            is_relevant = any(kw in content_lower for kw in relevance_keywords)
                            
                            # 降低缩写匹配的严格程度，只要标题包含缩写，或者内容中包含该缩写且满足基本相关性即可
                            if len(entity) <= 5 and entity.upper() == entity: # 可能是缩写
                                # 如果标题包含缩写，或者是专业映射词，则放宽限制
                                if entity.lower() in title_lower:
                                    is_relevant = True
                                elif f" {entity} " not in f" {content_lower} ":
                                    # 如果既不在标题也不在正文作为一个独立词出现，才判定为不相关
                                    is_relevant = is_relevant and (len(content_lower) > 200) # 至少有一定长度的背景
                            
                            if is_relevant:
                                logger.info(f"Wiki 模糊匹配成功: '{q}' -> '{best_title}'")
                                return summary
                            else:
                                logger.debug(f"Wiki 匹配项不相关: '{best_title}' (Content keywords not found)")
                except Exception as e:
                    error_msg = str(e)
                    if "ConnectError" in error_msg or "Timeout" in error_msg:
                        logger.error(f"Wiki 访问受限或网络超时: {error_msg}")
                    else:
                        logger.debug(f"Wiki 搜索回退失败 '{q}': {e}")
            
        return ""

    async def _fetch_by_title(self, title: str, url: str) -> str:
        """核心逻辑：通过确切标题获取摘要"""
        params = {
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "titles": title,
            "redirects": 1
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                pages = data.get("query", {}).get("pages", {})
                for page_id, page_info in pages.items():
                    if page_id == "-1":
                        continue
                    final_title = page_info.get("title", "")
                    extract = page_info.get("extract", "")
                    if extract:
                        short_extract = extract[:500] + "..." if len(extract) > 500 else extract
                        return f"【维基百科 - {final_title}】\n{short_extract}"
        except Exception as e:
            logger.warning(f"WikiAgent 抓取标题 '{title}' 失败: {e}")
        
        return ""

wiki_agent = WikiAgent()
