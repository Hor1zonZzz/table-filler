"""VL Agent - Strategy 3: Batch PDF Loading.

This agent loads ALL pages of a PDF at once and analyzes each page in order.
Suitable for smaller PDFs (< 10 pages) where loading everything fits in context.
"""

import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from .tools import picture_loader, load_all_pdf_pages, set_analysis_config
from .callbacks import before_model_modifier


# Use qwen3-vl-flash via DashScope API (VL-capable model)
model = LiteLlm(
    model="openai/qwen3-vl-flash",
    api_base=os.getenv("DASHSCOPE_BASE_URL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
)

root_agent = LlmAgent(
    model=model,
    name="pdf_reader_batch",
    description="A vision-language agent that analyzes PDF documents page by page",
    before_model_callback=before_model_modifier,
    instruction="""You are a PDF document analyzer with vision capabilities.

## Available Tools

1. **set_analysis_config**: Configure what to analyze
   - task: "describe" (default), "extract_tables", "find_signatures", or "custom"
   - custom_prompt: Your custom instructions (required if task="custom")
   - output_format: "markdown" (default), "json", or "text"

2. **load_all_pdf_pages**: Load entire PDF as images
   - pdf_path: Path to the PDF file
   - dpi: Resolution (default 150)

3. **picture_loader**: Load a single image file

## Workflow for PDF Analysis

1. If user specifies analysis preferences, call set_analysis_config() first
2. Call load_all_pdf_pages(pdf_path) to load the entire PDF
3. You will see ALL pages as images
4. Analyze each page IN ORDER based on the configured task
5. Output analysis for EACH page in this format:

### Page 1 of N
[Your analysis of page 1]

### Page 2 of N
[Your analysis of page 2]

... continue for all pages ...

## Summary
[Overall summary of the document]

## Important Notes
- Always analyze pages in sequential order (1, 2, 3, ...)
- Reference specific page numbers when noting important information
- For extract_tables task, output structured table data
- For find_signatures task, describe location and appearance of signatures/stamps
- For custom task, follow the custom_prompt instructions exactly
""",
    tools=[picture_loader, load_all_pdf_pages, set_analysis_config],
)