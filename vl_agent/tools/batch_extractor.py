"""Batch PDF data extraction using concurrent VL model calls.

This module provides a batch extraction tool that processes multiple PDFs
concurrently using AsyncOpenAI SDK to call vision-language models.
"""

import asyncio
import base64
import json
import os

from openai import AsyncOpenAI
from google.adk.tools.tool_context import ToolContext

from .pdf_renderer import (
    render_pdf_page,
    get_pdf_page_count,
    validate_pdf_path,
)

# DashScope API limit: 10MB per base64 image
MAX_BASE64_BYTES = 10 * 1024 * 1024
# DPI levels to try (from high to low)
DPI_LEVELS = [150, 120, 100, 72, 50]
# VL model for extraction
VL_MODEL = os.getenv("VL_MODEL", "qwen3-vl-flash")


def _render_page_with_size_limit(
    pdf_path: str,
    page_num: int,
    max_bytes: int = MAX_BASE64_BYTES,
) -> tuple[str, int]:
    """Render PDF page with progressive DPI reduction to fit size limit.

    Args:
        pdf_path: Path to PDF file.
        page_num: Page number (0-indexed).
        max_bytes: Maximum base64 size in bytes.

    Returns:
        Tuple of (base64_string, dpi_used).
    """
    image_b64 = ""
    final_dpi = DPI_LEVELS[-1]

    for dpi in DPI_LEVELS:
        image_bytes = render_pdf_page(pdf_path, page_num, dpi=dpi)
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        b64_size = len(image_b64)
        final_dpi = dpi

        if b64_size <= max_bytes:
            if dpi != DPI_LEVELS[0]:
                print(f"[DPI] Page {page_num + 1}: reduced to {dpi} DPI ({b64_size / 1024 / 1024:.2f}MB)")
            return image_b64, dpi

        print(f"[DPI] Page {page_num + 1}: {dpi} DPI too large ({b64_size / 1024 / 1024:.2f}MB), trying lower...")

    # Return lowest DPI result even if still too large
    print(f"[DPI] Warning: Page {page_num + 1} still exceeds limit at lowest DPI")
    return image_b64, final_dpi


async def batch_extract_pdfs(
    tool_context: ToolContext,
    pdf_paths: list[str],
    max_concurrent: int = 5,
) -> dict:
    """Batch extract structured data from multiple PDFs using VL model.

    This tool processes multiple PDF files concurrently, extracting data
    according to the confirmed schema. Each PDF is rendered to images and
    sent to the VL model for extraction.

    Args:
        pdf_paths: List of PDF file paths to process.
        max_concurrent: Maximum number of concurrent model requests (default 5).

    Returns:
        dict containing:
            - status: "success", "partial", or "error"
            - total_processed: Number of PDFs processed
            - total_extracted: Number of data rows extracted
            - errors: List of error messages (if any)
    """
    # Read schema from state
    schema_fields_raw = tool_context.state.get("schema_fields", "[]")
    schema_fields = json.loads(schema_fields_raw) if schema_fields_raw else []

    if not schema_fields:
        return {
            "status": "error",
            "message": "Schema not configured. Please define and confirm schema first.",
        }

    # Initialize AsyncOpenAI client
    client = AsyncOpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=os.getenv("DASHSCOPE_BASE_URL"),
    )

    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded_extract(pdf_path: str) -> dict:
        async with semaphore:
            return await _extract_single_pdf(client, pdf_path, schema_fields)

    # Execute all extractions concurrently
    tasks = [bounded_extract(path) for path in pdf_paths]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Aggregate results
    all_rows: list[dict] = []
    errors: list[str] = []

    for i, result in enumerate(results):
        pdf_path = pdf_paths[i]
        if isinstance(result, BaseException):
            errors.append(f"{pdf_path}: {str(result)}")
        elif isinstance(result, dict):
            if result.get("status") == "error":
                errors.append(f"{pdf_path}: {result.get('message', 'Unknown error')}")
            elif result.get("status") == "success":
                all_rows.extend(result.get("rows", []))

    # Write extracted rows to state
    existing_raw = tool_context.state.get("extracted_rows", "[]")
    existing_rows = json.loads(existing_raw) if existing_raw else []
    existing_rows.extend(all_rows)
    tool_context.state["extracted_rows"] = json.dumps(existing_rows, ensure_ascii=False)

    # Determine overall status
    if not errors:
        status = "success"
    elif all_rows:
        status = "partial"
    else:
        status = "error"

    return {
        "status": status,
        "total_processed": len(pdf_paths),
        "total_extracted": len(all_rows),
        "errors": errors if errors else None,
    }


async def _extract_single_pdf(
    client: AsyncOpenAI,
    pdf_path: str,
    schema_fields: list[dict],
) -> dict:
    """Extract data from a single PDF using VL model.

    Args:
        client: AsyncOpenAI client instance.
        pdf_path: Path to the PDF file.
        schema_fields: List of field definitions from confirmed schema.

    Returns:
        dict with status and extracted rows or error message.
    """
    # Validate PDF path
    is_valid, error_msg = validate_pdf_path(pdf_path)
    if not is_valid:
        return {"status": "error", "message": error_msg}

    # Render all pages to base64 images with progressive DPI
    try:
        total_pages = get_pdf_page_count(pdf_path)
        image_contents = []

        for page_num in range(total_pages):
            image_b64, dpi_used = _render_page_with_size_limit(pdf_path, page_num)
            image_contents.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_b64}"},
            })

    except Exception as e:
        return {"status": "error", "message": f"Failed to render PDF: {str(e)}"}

    # Build extraction prompt
    schema_prompt = _build_schema_prompt(schema_fields)

    # Build messages for VL model
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": schema_prompt},
                *image_contents,
            ],
        }
    ]

    # Debug: print request info
    print(f"\n{'='*60}")
    print(f"[VL Request] PDF: {pdf_path}")
    print(f"[VL Request] Total pages: {total_pages}")
    print(f"[VL Request] Prompt:\n{schema_prompt}")
    print(f"[VL Request] Images: {len(image_contents)} items")
    for i, img in enumerate(image_contents):
        url = img["image_url"]["url"]
        # Print truncated base64 preview
        b64_preview = url[:80] + "..." if len(url) > 80 else url
        print(f"  [{i+1}] {b64_preview}")
    print(f"{'='*60}\n")

    # Call VL model
    try:
        response = await client.chat.completions.create(
            model=VL_MODEL,
            messages=messages,
        )

        # Parse response
        content = response.choices[0].message.content

        # Debug: print response
        print(f"\n{'='*60}")
        print(f"[VL Response] PDF: {pdf_path}")
        print(f"[VL Response] Content:\n{content}")
        print(f"{'='*60}\n")

        if content is None:
            return {"status": "error", "message": "VL model returned empty response"}

        parsed = _parse_extraction_result(content, schema_fields)

        return {"status": "success", "rows": parsed}

    except Exception as e:
        print(f"\n[VL Error] PDF: {pdf_path}, Error: {str(e)}\n")
        return {"status": "error", "message": f"VL model error: {str(e)}"}


def _build_schema_prompt(schema_fields: list[dict]) -> str:
    """Build extraction prompt from schema fields.

    Args:
        schema_fields: List of field definitions.

    Returns:
        Formatted prompt string for VL model.
    """
    lines = [
        "Extract data from this document according to the following schema.",
        "Return the result as a JSON array where each element is an object with the specified fields.",
        "",
        "Schema fields:",
    ]

    for field in schema_fields:
        name = field["name"]
        desc = field.get("desc", "")
        field_type = field.get("type", "string")
        required = "required" if field.get("required", True) else "optional"
        lines.append(f"- {name} ({field_type}, {required}): {desc}")

    lines.extend([
        "",
        "Rules:",
        "- Use null for missing optional fields",
        "- Use YYYY-MM-DD format for dates",
        "- Extract ALL matching records from the document",
        "",
        "Return ONLY valid JSON array, no other text.",
    ])

    return "\n".join(lines)


def _parse_extraction_result(content: str, schema_fields: list[dict]) -> list[dict]:
    """Parse VL model response into structured data.

    Args:
        content: Raw response content from VL model.
        schema_fields: List of field definitions for validation.

    Returns:
        List of extracted data rows.
    """
    # Try to extract JSON from response
    content = content.strip()

    # Handle markdown code blocks
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first and last lines (```json and ```)
        json_lines = []
        in_block = False
        for line in lines:
            if line.startswith("```"):
                in_block = not in_block
                continue
            if in_block:
                json_lines.append(line)
        content = "\n".join(json_lines)

    try:
        parsed = json.loads(content)

        # Ensure it's a list
        if isinstance(parsed, dict):
            # Handle {"data": [...]} format
            if "data" in parsed:
                parsed = parsed["data"]
            else:
                parsed = [parsed]

        if not isinstance(parsed, list):
            return []

        # Validate and normalize each row
        field_names = {f["name"] for f in schema_fields}
        normalized = []

        for row in parsed:
            if isinstance(row, dict):
                # Keep only known fields
                normalized_row = {k: v for k, v in row.items() if k in field_names}
                normalized.append(normalized_row)

        return normalized

    except json.JSONDecodeError:
        return []
