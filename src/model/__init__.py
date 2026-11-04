"""
模型模块
"""
from .base import ModelBase
from .mock import MockModel, get_mock_model
from .real import RealModel

__all__ = ["ModelBase", "MockModel", "get_mock_model", "RealModel"]
