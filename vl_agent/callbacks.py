# vl_agent/callbacks.py

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest
from google.genai import types
from google.genai.types import Part, Content
import hashlib
from typing import List

# Tools that return images via artifact system
IMAGE_TOOLS = ["edit_product_asset", "picture_loader", "load_all_pdf_pages"]


async def before_model_modifier(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    """Modify LLM request to include artifact references for images.

    For LiteLlm/OpenAI-compatible endpoints, images must be in a separate
    user Content, not in the same Content as function_response.
    """
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
    filename = part.inline_data.display_name or "uploaded_image"
    image_data = part.inline_data.data

    # Combine filename and image data for hash
    hash_input = filename.encode("utf-8") + image_data
    content_hash = hashlib.sha256(hash_input).hexdigest()[:16]

    # Extract file extension from mime type
    mime_type = part.inline_data.mime_type
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

    # Single artifact case (e.g., picture_loader)
    artifact_id = part.function_response.response.get("tool_response_artifact_id")
    if artifact_id:
        artifact = await callback_context.load_artifact(filename=artifact_id)
        if artifact:
            artifacts.append(artifact)
        return artifacts

    # Multiple artifacts case (e.g., load_all_pdf_pages)
    artifact_ids = part.function_response.response.get("tool_response_artifact_ids", [])
    for aid in artifact_ids:
        artifact = await callback_context.load_artifact(filename=aid)
        if artifact:
            artifacts.append(artifact)

    return artifacts