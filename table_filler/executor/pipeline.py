"""提取流程管道。

使用 SequentialAgent 强制执行 executor → verifier 的顺序。
"""

from google.adk.agents import SequentialAgent

from .agent import executor_agent
from ..verifier.agent import verifier_agent

extraction_pipeline = SequentialAgent(
    name="extraction_pipeline",
    description="提取并验证文档字段",
    sub_agents=[executor_agent, verifier_agent],
)
