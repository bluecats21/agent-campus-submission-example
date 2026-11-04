"""
真实模型 API 实现（可选）
"""
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .base import ModelBase


# 加载环境变量
load_dotenv(Path(__file__).parent.parent.parent / ".env")


class RealModel(ModelBase):
    """真实 LLM API 调用"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        初始化真实模型
        
        Args:
            api_key: OpenAI API Key，无则从环境变量读取
            base_url: API Base URL
            model: 模型名称
        
        Raises:
            ValueError: 无 API Key 时抛出明确异常
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model or os.getenv("MODEL_NAME", "gpt-4o-mini")
        
        if not self.api_key:
            raise ValueError(
                "未配置 OPENAI_API_KEY。请在 .env 文件中设置，或在初始化时传入 api_key 参数。"
                "如无 API Key，请使用 MockModel 进行流程验证。"
            )
        
        # 延迟导入，避免无谓依赖
        try:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=0
            )
        except ImportError:
            raise ImportError(
                "需要安装 langchain-openai：pip install langchain-openai"
            )
    
    def decide(self, state: dict) -> dict:
        """
        调用真实 LLM 决策
        
        TODO: 第 5 步实现完整的 prompt + 工具调用逻辑
        当前仅作为接口占位
        """
        raise NotImplementedError(
            "RealModel.decide 尚未完整实现。"
            "需要：1) 加载 system.txt 提示词；2) 构造消息列表；3) 解析 LLM 输出。"
            "当前请使用 MockModel 验证流程。"
        )
