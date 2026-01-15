# vl_agent/callbacks.py

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools import FunctionTool, ToolContext
from google.adk.tools.base_tool import BaseTool
from google.genai import types
from google.genai.types import Part, Content
import hashlib
from typing import List

import json

from .tools.schema_tools import (
    schema_add_field,
    schema_remove_field,
    schema_update_field,
    schema_list,
    schema_confirm,
    schema_reset,
)
from .tools.data_tools import data_list
from .tools.data_tool_factory import create_data_append_tool

# Tools that return images via artifact system
IMAGE_TOOLS = ["picture_loader", "load_all_pdf_pages"]

# Pre-create FunctionTool instances at module level to avoid repeated creation overhead
SCHEMA_EDIT_TOOLS = [
    FunctionTool(schema_add_field),
    FunctionTool(schema_remove_field),
    FunctionTool(schema_update_field),
    FunctionTool(schema_list),
    FunctionTool(schema_confirm),
]

SCHEMA_RESET_TOOL = [
    FunctionTool(schema_reset),
]

# Static data tool (data_list doesn't need dynamic parameters)
DATA_LIST_TOOL = [
    FunctionTool(data_list),
]

# Tools that require schema confirmation before execution
REQUIRE_SCHEMA_TOOLS = {"batch_extract_pdfs"}


async def before_tool_validator(
    tool: BaseTool,
    args: dict,
    tool_context: ToolContext,
) -> dict | None:
    """Validate tool calls before execution.

    Ensures schema is confirmed before loading documents.
    """
    if tool.name in REQUIRE_SCHEMA_TOOLS:
        schema_confirmed = tool_context.state.get("schema_confirmed")
        if schema_confirmed != "true":
            return {
                "error": "Schema not confirmed. Please define and confirm schema first using schema_confirm tool."
            }

    return None  # Continue with tool execution


async def before_model_modifier(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    """Modify LLM request to include artifact references for images.

    For LiteLlm/OpenAI-compatible endpoints, images must be in a separate
    user Content, not in the same Content as function_response.
    """
    # Debug: print state before sending to LLM
    print(f"[DEBUG] State before LLM call: {callback_context.state._value}")

    # Dynamic tool injection based on schema_confirmed state
    schema_confirmed = callback_context.state.get("schema_confirmed")
    if schema_confirmed == "true":
        # Schema confirmed: provide reset tool and data tools
        llm_request.append_tools(SCHEMA_RESET_TOOL)
        llm_request.append_tools(DATA_LIST_TOOL)

        # Dynamically create data_append with schema-based parameters
        schema_fields_raw = callback_context.state.get("schema_fields", "[]")
        schema_fields = json.loads(schema_fields_raw) if schema_fields_raw else []
        if schema_fields:
            data_append_tool = create_data_append_tool(schema_fields)
            llm_request.append_tools([data_append_tool])
    else:
        # Schema not confirmed: provide editing tools
        llm_request.append_tools(SCHEMA_EDIT_TOOLS)

    artifacts_to_inject = []

    for content in llm_request.contents:
        if not content.parts:
            continue

        modified_parts = []
        for part in content.parts:
            # Handle user-uploaded inline images (keep in same Content)
            if part.inline_data:
                processed_parts = await _process_inline_data_part(
                    part, callback_context
                )
                modified_parts.extend(processed_parts)

            # Handle function response - collect artifacts, don't inject here
            elif part.function_response:
                if part.function_response.name in IMAGE_TOOLS:
                    extracted = await _extract_artifacts_from_response(
                        part, callback_context
                    )
                    artifacts_to_inject.extend(extracted)
                # Keep function_response as-is
                modified_parts.append(part)

            # Default: keep part as-is
            else:
                modified_parts.append(part)

        content.parts = modified_parts

    # Append collected artifacts as separate user Content
    # This avoids LiteLlm dropping images in function_response Content
    if artifacts_to_inject:
        # Create descriptive text for the images
        if len(artifacts_to_inject) == 1:
            intro_text = "[Tool loaded image] Please analyze the following:"
        else:
            intro_text = f"[Tool loaded {len(artifacts_to_inject)} images] Please analyze each in order:"

        llm_request.contents.append(
            Content(
                role="user",
                parts=[
                    Part(text=intro_text),
                    *artifacts_to_inject,
                ]
            )
        )

    print(f"final llm request: {llm_request}")


async def _process_inline_data_part(
    part: Part, callback_context: CallbackContext
) -> List[Part]:
    """Process inline data parts (user-uploaded images).

    Returns:
        List of parts including artifact marker and the image.
    """
    artifact_id = _generate_artifact_id(part)

    # Save artifact if it doesn't exist
    if artifact_id not in await callback_context.list_artifacts():
        await callback_context.save_artifact(filename=artifact_id, artifact=part)

    return [
        Part(
            text=f"[User Uploaded Artifact] Below is the content of artifact ID : {artifact_id}"
        ),
        part,
    ]


def _generate_artifact_id(part: Part) -> str:
    """Generate a unique artifact ID for user uploaded image.

    Returns:
        Hash-based artifact ID with proper file extension.
    """
    inline_data = part.inline_data
    if not inline_data:
        raise ValueError("Expected Part.inline_data to be set")

    filename = inline_data.display_name or "uploaded_image"
    image_data = inline_data.data
    mime_type = inline_data.mime_type
    if image_data is None or mime_type is None:
        raise ValueError("inline_data.data and inline_data.mime_type are required")

    # Combine filename and image data for hash
    hash_input = filename.encode("utf-8") + image_data
    content_hash = hashlib.sha256(hash_input).hexdigest()[:16]

    extension = mime_type.split("/")[-1]

    return f"usr_upl_img_{content_hash}.{extension}"


async def _extract_artifacts_from_response(
    part: Part, callback_context: CallbackContext
) -> list[Part]:
    """Extract artifact(s) from function response.

    Supports both single artifact (tool_response_artifact_id) and
    multiple artifacts (tool_response_artifact_ids) for batch loading.

    Returns:
        List of artifact Parts (empty if none found).
    """
    artifacts = []

    function_response = part.function_response
    response = function_response.response if function_response else None
    if not response:
        return artifacts

    # Single artifact case (e.g., picture_loader)
    artifact_id = response.get("tool_response_artifact_id")
    if artifact_id:
        artifact = await callback_context.load_artifact(filename=artifact_id)
        if artifact:
            artifacts.append(artifact)
        return artifacts

    # Multiple artifacts case (e.g., load_all_pdf_pages)
    artifact_ids = response.get("tool_response_artifact_ids", [])
    for aid in artifact_ids:
        artifact = await callback_context.load_artifact(filename=aid)
        if artifact:
            artifacts.append(artifact)

    return artifacts