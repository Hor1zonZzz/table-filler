"""VL Agent - A vision-language agent for image Q&A tasks."""

import os
import json

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from .tools import picture_loader
from .callbacks import before_model_modifier


# Use qwen3-vl-flash via DashScope API (same as existing codebase)
model = LiteLlm(
    model="openai/qwen3-vl-flash",
    api_base=os.getenv("DASHSCOPE_BASE_URL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
)

root_agent = LlmAgent(
    model=model,
    name="vl_qa_agent",
    description="A vision-language agent that answers questions about images",
    before_model_callback=before_model_modifier,
    instruction="""You are an image analysis assistant with vision capabilities.

When user provides an image path, use the picture_loader tool to load the image first, then analyze it.

Just use once picture_loader tool.
""",
    tools=[picture_loader],
)