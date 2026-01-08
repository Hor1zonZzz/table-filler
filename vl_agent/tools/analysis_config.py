"""Analysis configuration tool for PDF processing.

This tool allows users to configure what kind of analysis
the VL model should perform on PDF pages.
"""

from google.adk.tools import ToolContext

# Valid analysis tasks
VALID_TASKS = ["describe", "extract_tables", "find_signatures", "custom"]

# Valid output formats
VALID_FORMATS = ["markdown", "json", "text"]


async def set_analysis_config(
    tool_context: ToolContext,
    task: str = "describe",
    custom_prompt: str | None = None,
    output_format: str = "markdown",
) -> dict:
    """Configure what to analyze in PDF pages.

    Args:
        task: Analysis task type. One of:
            - "describe": General description of page content and layout
            - "extract_tables": Extract all table data as structured format
            - "find_signatures": Identify signatures, stamps, handwritten marks
            - "custom": Follow custom_prompt instructions
        custom_prompt: Custom analysis instructions (required if task="custom")
        output_format: Output format - "markdown", "json", or "text"

    Returns:
        dict with status and current configuration
    """
    if task not in VALID_TASKS:
        return {
            "status": "error",
            "message": f"Invalid task '{task}'. Use one of: {VALID_TASKS}",
        }

    if output_format not in VALID_FORMATS:
        return {
            "status": "error",
            "message": f"Invalid output_format '{output_format}'. Use one of: {VALID_FORMATS}",
        }

    if task == "custom" and not custom_prompt:
        return {
            "status": "error",
            "message": "custom_prompt is required when task='custom'",
        }

    config = {
        "task": task,
        "custom_prompt": custom_prompt,
        "output_format": output_format,
    }

    tool_context.state["pdf_analysis_config"] = config

    return {
        "status": "success",
        "config": config,
        "message": f"Analysis configured: {task} with {output_format} output",
    }
