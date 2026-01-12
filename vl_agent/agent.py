"""VL Agent - Table Extractor.

This agent reads PDF documents and extracts data into a configured table schema.
Like a human reading a PDF and filling out a form.
"""

import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from .tools import picture_loader, load_all_pdf_pages, set_config
from .callbacks import before_model_modifier


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
    instruction="""You are a table extraction agent with vision capabilities.
Your job is to read PDF/image documents and extract data into a structured table.

## Available Tools

1. **set_config**: Configure table schema (columns to extract)
   - columns: List of column definitions, each with:
     - name: Column name
     - type: "string", "number", "date", "boolean"
     - description: What this field represents

2. **load_all_pdf_pages**: Load entire PDF as images
   - pdf_path: Path to the PDF file

3. **picture_loader**: Load a single image file

## Workflow (IMPORTANT - Follow This Order)

When user describes a table structure, you MUST:

1. **FIRST** call set_config() to save the table schema
   - Convert user's description into columns format
   - Example: User says "提取姓名和金额" → call set_config(columns=[{"name": "姓名", "type": "string"}, {"name": "金额", "type": "number"}])

2. **THEN** load the document
   - For PDF: call load_all_pdf_pages(pdf_path)
   - For image: call picture_loader(image_path)

3. **FINALLY** extract and output data as markdown table

## Output Format

| Column1 | Column2 | Column3 |
|---------|---------|---------|
| value1  | value2  | value3  |

If a field cannot be found, use "-".

## Important
- ALWAYS call set_config BEFORE loading documents
- Match fields by meaning, not just exact text
- For dates, use YYYY-MM-DD format
""",
    tools=[picture_loader, load_all_pdf_pages, set_config],
)