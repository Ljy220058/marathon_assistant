
import re
import logging
from typing import Tuple

logger = logging.getLogger("security_utils")

class InputGuard:
    """输入安全过滤器"""

    def __init__(self):
        # 危险关键词模式
        self.dangerous_patterns = [
            r"忽略.*(?:之前|以上|所有).*(?:指令|规则|限制)",
            r"(?:system|系统).*(?:prompt|提示|指令)",
            r"\b(?:api|密钥|key|token|password|密码)\b\s*[:：=]",
            r"(?:扮演|假装|角色扮演).*(?:DAN|无限制|不受限)",
            r"(?:越狱|jailbreak|bypass|绕过)",
            r"(?:ignore|disregard).*(?:previous|above|all).*(?:instructions|rules)",
            r"reveal.*system.*prompt",
        ]

        # 注入模式
        self.injection_patterns = [
            r"---\s*\n.*(?:指令|instruction|system)",  # 分隔符注入
            r"```.*(?:system|指令)",                     # 代码块注入
            r"(?:base64|decode|解码).*(?:执行|execute)",  # 编码绕过
        ]

        self.compiled_dangerous = [re.compile(p, re.IGNORECASE) for p in self.dangerous_patterns]
        self.compiled_injection = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.injection_patterns]

    def check(self, input_text: str, input_type: str = "query") -> Tuple[bool, str]:
        """
        检查输入内容是否安全。
        input_type: "query", "rag", "history", "planner"
        返回 (is_safe, reason)
        """
        if not input_text:
            return True, "输入为空"

        # 1. 检查危险关键词
        for pattern in self.compiled_dangerous:
            if pattern.search(input_text):
                return False, f"检测到潜在的危险模式 ({input_type})：{pattern.pattern[:30]}..."

        # 2. 检查注入模式
        for pattern in self.compiled_injection:
            if pattern.search(input_text):
                return False, f"检测到潜在的注入攻击模式 ({input_type})"

        return True, "安全"

class OutputGuard:
    """输出安全检测器"""

    def __init__(self):
        # 敏感信息模式
        self.sensitive_patterns = [
            r"sk-[a-zA-Z0-9]{15,}",         # API Key 格式 (更宽松以捕获更多)
            r"sk-marathon-\d{4}-secret-key", # 专门捕获模拟密钥
            r"(?:密钥|key|token|password|密码)\s*[:：]\s*\S+", 
            r"(?:系统提示|system prompt)\s*[:：]",
        ]

        # 有害内容关键词
        self.harmful_patterns = [
            r"(?:制造|制作).*(?:炸弹|武器|毒品|病毒)",
            r"(?:攻击|入侵|破解|渗透).*(?:步骤|教程|方法|工具)",
            r"(?:自杀|自残).*(?:方法|步骤)",
            r"how to (?:hack|bypass|exploit)",
        ]

        self.compiled_sensitive = [re.compile(p, re.IGNORECASE) for p in self.sensitive_patterns]
        self.compiled_harmful = [re.compile(p, re.IGNORECASE) for p in self.harmful_patterns]

    def check(self, output: str) -> Tuple[bool, str, str]:
        """
        检查模型输出是否安全。
        返回 (is_safe, cleaned_output, reason)
        """
        cleaned = output

        # 1. 检查敏感信息泄露并脱敏
        leaked = False
        for pattern in self.compiled_sensitive:
            if pattern.search(cleaned):
                cleaned = pattern.sub("[已脱敏]", cleaned)
                leaked = True
        
        if leaked:
            return False, cleaned, "检测到敏感信息泄露，已自动脱敏"

        # 2. 检查有害内容
        for pattern in self.compiled_harmful:
            if pattern.search(cleaned):
                return False, "抱歉，我无法提供此类有害信息。", "检测到有害内容，已拦截"

        return True, cleaned, "输出安全"
