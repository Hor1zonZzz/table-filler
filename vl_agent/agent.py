"""VL Agent - Table Extractor.

This agent reads PDF documents and extracts data into a configured table schema.
Like a human reading a PDF and filling out a form.
"""

import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from .tools import (
    picture_loader,
    load_all_pdf_pages,
)
from .callbacks import before_model_modifier, before_tool_validator


# Use qwen3-vl-flash via DashScope API (VL-capable model)
model = LiteLlm(
    model="openai/qwen3-vl-flash",
    api_base=os.getenv("DASHSCOPE_BASE_URL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
)

root_agent = LlmAgent(
    model=model,
    name="table_extractor",
    description="A vision-language agent that extracts data from PDF into structured tables",
    before_model_callback=before_model_modifier,
    before_tool_callback=before_tool_validator,
    instruction="""You are a table extraction agent with vision capabilities.
Your job is to read PDF/image documents and extract data into a structured table.

## Workflow

1. **Schema Definition Phase**: Define table schema based on user's description
   - Add fields, show schema_list for user review
   - Wait for user's explicit approval before confirming schema

2. **Data Extraction Phase**: After schema is confirmed
   - Load document with load_all_pdf_pages or picture_loader
   - Extract data according to confirmed schema
   - Output as JSON array, use null for missing fields, YYYY-MM-DD for dates

## Notes
- Remind user must set schema before extract data
- Use the tools available to you in each phase
- If you need to start over, use schema_reset
""",
    tools=[
        picture_loader,
        load_all_pdf_pages,
    ],
)