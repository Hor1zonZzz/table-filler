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
    schema_add_field,
    schema_remove_field,
    schema_update_field,
    schema_list,
    schema_confirm,
    schema_reset,
)
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

## Schema Management Tools

- **schema_add_field(name, desc, type, required, default)**: Add a field
- **schema_remove_field(name)**: Remove a field
- **schema_update_field(name, updates)**: Update field attributes
- **schema_list()**: Show current schema
- **schema_confirm()**: Lock schema for processing, Set it up once and it will work.
- **schema_reset()**: Clear and start over

Field types: "string", "number", "date", "boolean"

## Document Loading Tools

- **load_all_pdf_pages(pdf_path)**: Load entire PDF as images
- **picture_loader(image_path)**: Load a single image file

## Guidelines

- Add fields based on user's description, then show schema_list for user to review
- Wait for user's explicit approval before calling schema_confirm
- Load document and extract data only after schema is confirmed
- Output as JSON array, use null for missing fields
- Use YYYY-MM-DD for dates
""",
    tools=[
        picture_loader,
        load_all_pdf_pages,
        schema_add_field,
        schema_remove_field,
        schema_update_field,
        schema_list,
        schema_confirm,
        schema_reset,
    ],
)