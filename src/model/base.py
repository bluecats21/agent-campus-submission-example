"""
模型决策接口定义
"""
from abc import ABC, abstractmethod


class ModelBase(ABC):
    """模型决策基类"""
    
    @abstractmethod
    def decide(self, state: dict) -> dict:
        """
        根据当前状态决定下一步动作
        
        Args:
            state: {
                "query": "用户问题",
                "conversation_history": [],
                "steps": [...],
                "current_step": 0,
                "last_observation": {...}  # 上一步工具返回
            }
        
        Returns:
            {
                "action": "工具名称",
                "args": {"参数": "值"},
                "reason": "决策理由",
                "terminate": False
            }
        """
        pass
