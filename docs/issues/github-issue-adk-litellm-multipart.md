# [Bug] LiteLlm adapter silently drops non-function_response parts in multipart Content

## Description

The `LiteLlm` adapter in `google/adk/models/lite_llm.py` silently discards non-`function_response` parts when a `Content` object contains multiple parts including a `function_response`. This breaks Vision-Language (VL) agent workflows where tools load images via the artifact system and attach them alongside function responses.

When a tool returns both a function response and additional content (such as images loaded from artifacts), only the function response is converted to a `ChatCompletionToolMessage`. All other parts (text, `inline_data` with images, etc.) are silently ignored without any warning or error.

## Steps to Reproduce

1. Create a tool that saves an image artifact and returns `tool_response_artifact_id`
2. Create a `before_model_callback` that:
   - Detects `function_response` from the tool
   - Loads the artifact and injects the image into the **same Content** as the `function_response`
3. Use the agent with a VL-capable model via LiteLlm
4. The VL model reports it cannot see the image

### Tool Implementation

```python
from google.adk.tools import ToolContext
from google.genai import types

async def load_image(tool_context: ToolContext, image_path: str) -> dict:
    """Load an image for VL model analysis."""
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # Save image as artifact
    part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
    artifact_id = f"img_{tool_context.function_call_id}.png"
    await tool_context.save_artifact(filename=artifact_id, artifact=part)

    # Return artifact_id for callback to find
    return {"tool_response_artifact_id": artifact_id, "status": "success"}
```

### Callback Implementation

```python
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest
from google.genai.types import Part

async def before_model_modifier(callback_context: CallbackContext, llm_request: LlmRequest):
    """Inject tool artifacts into LLM request."""
    for content in llm_request.contents:
        modified_parts = []
        for part in content.parts:
            if part.function_response and part.function_response.name == "load_image":
                artifact_id = part.function_response.response.get("tool_response_artifact_id")
                if artifact_id:
                    artifact = await callback_context.load_artifact(filename=artifact_id)
                    # Inject image into the SAME Content as function_response
                    # This causes the image to be silently dropped!
                    modified_parts.extend([
                        part,  # function_response
                        Part(text=f"[Image: {artifact_id}]"),
                        artifact,  # inline_data image - WILL BE DROPPED
                    ])
                else:
                    modified_parts.append(part)
            else:
                modified_parts.append(part)
        content.parts = modified_parts
    return None
```

### Agent Configuration

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

agent = LlmAgent(
    model=LiteLlm(model="openai/qwen-vl-max"),  # Any VL model via LiteLlm
    name="vl_agent",
    before_model_callback=before_model_modifier,
    tools=[load_image],
)
```

### Result

The `LlmRequest` before conversion shows all 3 parts:
```
Content(role='user', parts=[
    Part(function_response=...),      # ✓ Kept
    Part(text='[Image: ...]'),        # ✗ Dropped
    Part(inline_data=Blob(...)),      # ✗ Dropped
])
```

But LiteLlm only sends the `function_response` to the model, dropping the image.

## Expected Behavior

Either:
1. All parts of the multipart `Content` should be converted to appropriate message types and included in the conversation
2. Or at minimum, a warning should be logged indicating that some parts were dropped

The VL model should receive both:
- The tool result message (function response)
- The image content for visual analysis

## Actual Behavior

Only the `function_response` parts are converted to `ChatCompletionToolMessage`. All other parts (text, `inline_data` with images) are silently discarded. No warning is logged.

The VL model never sees the image content, causing it to hallucinate or fail to perform visual analysis tasks.

## Root Cause Analysis

In `_content_to_message_param()`, the code processes `function_response` parts first and returns early:

```python
def _content_to_message_param(
    self, content: types.Content
) -> Union[ChatCompletionMessageParam, list[ChatCompletionMessageParam]]:
    # ... earlier code ...

    tool_messages: list[ChatCompletionToolMessageParam] = []
    for part in content.parts:
        if part.function_response:
            tool_messages.append(
                ChatCompletionToolMessageParam(
                    role="tool",
                    tool_call_id=part.function_response.id,
                    content=json.dumps(part.function_response.response),
                )
            )

    # Early return - all other parts are dropped!
    if tool_messages:
        return tool_messages if len(tool_messages) > 1 else tool_messages[0]

    # Text and image handling only happens if there are NO function_response parts
    # ...
```

When `tool_messages` is non-empty, the function returns immediately. Any text parts, `inline_data` parts (images), or other content types in the same `Content` object are never processed.

## Suggested Fix

**Option 1: Log a warning (minimal change)**

Add a warning when non-`function_response` parts are being dropped:

```python
if tool_messages:
    # Check if other parts are being dropped
    other_parts = [p for p in content.parts if not p.function_response]
    if other_parts:
        logger.warning(
            f"Dropping {len(other_parts)} non-function_response parts from Content. "
            "Multipart Content with mixed function_response and other parts is not fully supported."
        )
    return tool_messages if len(tool_messages) > 1 else tool_messages[0]
```

**Option 2: Handle multipart Content properly (recommended)**

Split multipart `Content` into multiple messages when it contains both `function_response` and other parts:

```python
def _content_to_message_param(
    self, content: types.Content
) -> Union[ChatCompletionMessageParam, list[ChatCompletionMessageParam]]:
    messages = []

    # Process function_response parts
    for part in content.parts:
        if part.function_response:
            messages.append(
                ChatCompletionToolMessageParam(
                    role="tool",
                    tool_call_id=part.function_response.id,
                    content=json.dumps(part.function_response.response),
                )
            )

    # Process other parts (text, images, etc.)
    other_parts = [p for p in content.parts if not p.function_response]
    if other_parts:
        # Convert to user message with text/image content
        user_content = self._parts_to_content(other_parts)
        if user_content:
            messages.append(
                ChatCompletionUserMessageParam(
                    role="user",
                    content=user_content,
                )
            )

    if not messages:
        # Handle empty content case
        ...

    return messages if len(messages) > 1 else messages[0]
```

## Environment

- **ADK Version**: (please specify version from `pip show google-adk`)
- **Python Version**: 3.11+
- **LiteLLM Version**: (please specify version from `pip show litellm`)
- **Model**: Any VL-capable model via LiteLlm (e.g., `openai/gpt-4o`, `anthropic/claude-3-opus`)
- **OS**: Windows/Linux/macOS

## Additional Context

### Current Workaround

In the `before_model_callback`, instead of injecting image into the Content containing `function_response`, append a **separate user Content**:

```python
async def before_model_modifier(callback_context: CallbackContext, llm_request: LlmRequest):
    """Inject tool artifacts into LLM request."""
    artifacts_to_inject = []

    # Step 1: Extract artifacts from function_response (don't modify that Content)
    for content in llm_request.contents:
        for part in content.parts:
            if part.function_response and part.function_response.name == "load_image":
                artifact_id = part.function_response.response.get("tool_response_artifact_id")
                if artifact_id:
                    artifact = await callback_context.load_artifact(filename=artifact_id)
                    artifacts_to_inject.append((artifact_id, artifact))

    # Step 2: Append as SEPARATE user Content (not in function_response Content)
    if artifacts_to_inject:
        from google.genai import types
        for artifact_id, artifact in artifacts_to_inject:
            llm_request.contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part(text=f"[Image from tool: {artifact_id}]"),
                        artifact,
                    ]
                )
            )

    return None
```

This works but is unintuitive and requires developers to understand the LiteLlm conversion internals.

### Impact

This issue particularly affects:
- Document processing agents that view images/PDFs
- Multi-modal agents that combine tool outputs with visual content
- Any workflow where tools need to provide both structured responses and visual data

### Related

- This may affect other model adapters if they follow a similar pattern
- The native Gemini adapter may handle this differently (not verified)
