"""VL Agent - Table Extractor.

This agent reads PDF documents and extracts data into a configured table schema.
Like a human reading a PDF and filling out a form.
"""

import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from .tools import batch_extract_pdfs
from .callbacks import before_model_modifier, before_tool_validator


# Use DeepSeek Chat as the main orchestrator model
model = LiteLlm(
    model="deepseek/deepseek-chat",
    api_base=os.getenv("DEEPSEEK_BASE_URL"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
)

root_agent = LlmAgent(
    model=model,
    name="table_extractor",
    description="An orchestrator agent that manages schema and coordinates PDF data extraction",
    before_model_callback=before_model_modifier,
    before_tool_callback=before_tool_validator,
    instruction="""You are a table extraction orchestrator.
Your job is to manage schema definition and coordinate PDF data extraction.

## Workflow

1. **Schema Definition Phase**: Define table schema based on user's description
   - Add fields, show schema_list for user review
   - Wait for user's explicit approval before confirming schema

2. **Data Extraction Phase**: After schema is confirmed
   - Use batch_extract_pdfs to extract data from PDF files
   - Use data_list to show extracted results

## Notes
- Remind user must set schema before extract data
- Use the tools available to you in each phase
- If you need to start over, use schema_reset
""",
    tools=[batch_extract_pdfs],
)