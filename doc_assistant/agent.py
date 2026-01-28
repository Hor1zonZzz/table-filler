"""Agent definition for Document Assistant."""

import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger('google_adk').setLevel(logging.DEBUG)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('LiteLLM').setLevel(logging.INFO)

from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.apps.app import EventsCompactionConfig
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import preload_memory

from .tools.document_reader import read_document

# Agent instruction (system prompt)
INSTRUCTION = """你是一个通用文档处理助手。

## 你的能力
你可以使用 read_document 工具读取 PDF 或图片文档，并回答用户关于文档内容的问题。

## 使用指南
当用户询问文档相关问题时：
1. 使用 read_document 工具读取相关文档
2. 基于工具返回的内容回答用户问题

## read_document 工具说明
- file_path: 文档路径（支持 PDF 和常见图片格式）
- question: 你想了解的问题
- pages: （可选）对于 PDF，可以指定要读取的页码列表（从 1 开始）

## 使用建议
- 如果用户没有指定页码，你可以先读取前几页了解文档结构
- 对于长文档，建议用户指定关注的页面范围以节省时间
- 如果文档内容无法回答问题，请诚实告知用户

## 示例对话
用户: "请帮我看看这份合同的签订日期"
助手: [调用 read_document 工具读取合同文档]
助手: "根据文档内容，这份合同的签订日期是 2024年1月15日。"
"""


# Create model using LiteLlm for DeepSeek (same env vars as vl_agent)
model = LiteLlm(
    model="deepseek/deepseek-chat",
    api_base=os.getenv("DEEPSEEK_BASE_URL"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
)


# Create the root agent
root_agent = LlmAgent(
    model=model,
    name="doc_assistant",
    description="通用文档问答助手，可以读取 PDF 和图片并回答问题",
    instruction=INSTRUCTION,
    tools=[read_document, preload_memory],
)

# App with event compaction (auto-discovered by adk web)
app = App(
    name="doc_assistant",
    root_agent=root_agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=10,
        overlap_size=4,
    ),
)
