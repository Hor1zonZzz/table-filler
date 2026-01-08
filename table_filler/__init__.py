"""通用表格填写助手模块。

该模块实现了基于 Recipe（配方）的文档数据提取系统，
包含 Planner、Executor、Verifier 三个核心 Agent。
"""

# 延迟导入以避免循环依赖
# from .models.recipe import Recipe, FieldDefinition
# from .planner.agent import planner_agent
# from .executor.pipeline import extraction_pipeline

__all__ = [
    "Recipe",
    "FieldDefinition",
    "planner_agent",
    "extraction_pipeline",
]
