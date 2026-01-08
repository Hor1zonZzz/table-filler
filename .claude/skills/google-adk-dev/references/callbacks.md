# Callbacks & Design Patterns

## Table of Contents
1. [Callback Types](#callback-types)
2. [Callback Context](#callback-context)
3. [Design Patterns](#design-patterns)
   - [1. Content Filtering](#1-content-filtering--policy-enforcement)
   - [2. Logging & Observability](#2-logging--observability)
   - [3. Caching](#3-caching)
   - [4. Request/Response Modification](#4-requestresponse-modification)
   - [5. Short-Circuit Execution](#5-short-circuit-execution)
   - [6. Tool Confirmation (HITL)](#6-tool-confirmation-hitl)
   - [7. Artifact Injection (Multimodal)](#7-artifact-injection-multimodal)
4. [Best Practices](#best-practices)
5. [Troubleshooting](#troubleshooting)

## Callback Types

ADK provides hooks at specific points in the agent lifecycle:

| Callback | Trigger Point | Use Case |
|----------|--------------|----------|
| `before_agent_callback` | Before agent runs | Validation, setup |
| `after_agent_callback` | After agent completes | Cleanup, logging |
| `before_model_callback` | Before LLM call | Modify prompt, cache check |
| `after_model_callback` | After LLM response | Modify response, logging |
| `before_tool_callback` | Before tool execution | Validate args, auth |
| `after_tool_callback` | After tool execution | Process result, cache |

## Callback Context

### CallbackContext (Agent/Model)
```python
from google.adk.agents.callback_context import CallbackContext

def my_callback(context: CallbackContext):
    # Access state
    user_lang = context.state.get('language', 'en')
    
    # Access session
    session_id = context.session.id
    
    # Access invocation info
    invocation_id = context.invocation_id
```

### ToolContext (Tools)
```python
from google.adk.tools import ToolContext

def before_tool(tool_context: ToolContext, tool_name: str, args: dict):
    # Access same properties plus tool-specific info
    tool_context.state["last_tool"] = tool_name
```

## Design Patterns

### 1. Content Filtering / Policy Enforcement
Block requests that violate policies.

```python
from google.adk.agents import LlmAgent
from google.adk.models import LlmResponse
from google.genai import types

FORBIDDEN_TOPICS = ["illegal", "harmful"]

def content_filter(context, llm_request):
    """Block forbidden content before LLM call."""
    prompt_text = str(llm_request.contents)
    
    for topic in FORBIDDEN_TOPICS:
        if topic in prompt_text.lower():
            return LlmResponse(
                content=types.Content(
                    parts=[types.Part(text="I cannot process this request.")]
                )
            )
    return None  # Continue normally

agent = LlmAgent(
    name="filtered_agent",
    model="gemini-2.0-flash",
    before_model_callback=content_filter
)
```

### 2. Logging & Observability
Log agent activities for debugging and monitoring.

```python
import logging

def log_before_tool(context, tool_name: str, args: dict):
    logging.info(f"[{context.invocation_id}] Calling tool: {tool_name} with args: {args}")
    return None  # Continue normally

def log_after_tool(context, tool_name: str, args: dict, result: dict):
    logging.info(f"[{context.invocation_id}] Tool {tool_name} returned: {result}")
    return None

agent = LlmAgent(
    name="logged_agent",
    model="gemini-2.0-flash",
    before_tool_callback=log_before_tool,
    after_tool_callback=log_after_tool
)
```

### 3. Caching
Avoid redundant LLM/tool calls.

```python
import hashlib

def generate_cache_key(request):
    return hashlib.md5(str(request).encode()).hexdigest()

def cache_check(context, llm_request):
    """Check cache before LLM call."""
    cache_key = f"cache:{generate_cache_key(llm_request)}"
    cached = context.state.get(cache_key)
    
    if cached:
        return cached  # Return cached response
    return None  # Continue to LLM

def cache_save(context, llm_request, llm_response):
    """Save response to cache after LLM call."""
    cache_key = f"cache:{generate_cache_key(llm_request)}"
    context.state[cache_key] = llm_response
    return None  # Return original response

agent = LlmAgent(
    name="cached_agent",
    model="gemini-2.0-flash",
    before_model_callback=cache_check,
    after_model_callback=cache_save
)
```

### 4. Request/Response Modification
Transform inputs or outputs.

```python
def add_system_context(context, llm_request):
    """Add user context to system instruction."""
    user_lang = context.state.get('language', 'en')
    
    if llm_request.config and llm_request.config.system_instruction:
        llm_request.config.system_instruction += f"\nUser language: {user_lang}"
    
    return None  # Continue with modified request

def format_response(context, llm_request, llm_response):
    """Post-process LLM response."""
    # Modify response content if needed
    return None  # Return original or modified response

agent = LlmAgent(
    name="modified_agent",
    model="gemini-2.0-flash",
    before_model_callback=add_system_context,
    after_model_callback=format_response
)
```

### 5. Short-Circuit Execution
Skip normal execution based on conditions.

```python
def check_maintenance(context):
    """Skip agent if in maintenance mode."""
    if context.state.get('maintenance_mode'):
        from google.genai import types
        return types.Content(
            parts=[types.Part(text="System is under maintenance.")]
        )
    return None

agent = LlmAgent(
    name="guarded_agent",
    model="gemini-2.0-flash",
    before_agent_callback=check_maintenance
)
```

### 6. Tool Confirmation (HITL)
Require human approval for sensitive tools.

```python
SENSITIVE_TOOLS = ["delete_file", "send_email", "make_payment"]

def require_confirmation(context, tool_name: str, args: dict):
    """Block sensitive tools pending confirmation."""
    if tool_name in SENSITIVE_TOOLS:
        if not context.state.get(f"confirmed:{tool_name}"):
            return {
                "status": "pending",
                "message": f"Tool '{tool_name}' requires confirmation. Args: {args}"
            }
    return None  # Continue normally

agent = LlmAgent(
    name="safe_agent",
    model="gemini-2.0-flash",
    before_tool_callback=require_confirmation
)
```

### 7. Artifact Injection (Multimodal)
Enable VL models to see images from tools or user uploads. This pattern uses `before_model_callback` to inject image artifacts into the LLM request.

**Data Flow:**
```
Tool/User Input → save_artifact() → tool returns artifact_id
                                           ↓
before_model_callback → load_artifact() → inject Part into request
                                           ↓
                                    VL Model sees image
```

#### Tool Side: Save and Return Artifact ID

```python
from google.adk.tools import ToolContext
from google.genai import types

async def load_image(tool_context: ToolContext, path: str) -> dict:
    """Load image for VL model analysis."""
    with open(path, "rb") as f:
        data = f.read()

    # Create Part and save as artifact
    part = types.Part.from_bytes(data=data, mime_type="image/png")
    artifact_id = f"img_{tool_context.function_call_id}.png"
    await tool_context.save_artifact(filename=artifact_id, artifact=part)

    # Return artifact_id for callback to find
    return {"tool_response_artifact_id": artifact_id, "status": "success"}
```

#### Callback Side: Inject Artifacts into Request

```python
import hashlib
from google.genai import types

def _hash_artifact_id(part) -> str:
    """Generate unique ID for user-uploaded image."""
    data = part.inline_data.data
    content_hash = hashlib.sha256(data).hexdigest()[:16]
    ext = part.inline_data.mime_type.split("/")[-1]
    return f"user_img_{content_hash}.{ext}"

async def inject_artifacts(callback_context, llm_request):
    """Inject tool artifacts and user images into LLM request."""
    for content in llm_request.contents:
        if not content.parts:
            continue

        modified_parts = []
        for part in content.parts:
            # Handle user-uploaded images (inline_data)
            if part.inline_data:
                artifact_id = _hash_artifact_id(part)
                if artifact_id not in await callback_context.list_artifacts():
                    await callback_context.save_artifact(filename=artifact_id, artifact=part)
                modified_parts.extend([
                    types.Part(text=f"[User Image: {artifact_id}]"),
                    part
                ])

            # Handle tool-generated artifacts (function_response)
            elif part.function_response:
                tool_name = part.function_response.name
                if tool_name in ["load_image", "edit_image", "generate_image"]:
                    artifact_id = part.function_response.response.get("tool_response_artifact_id")
                    if artifact_id:
                        artifact = await callback_context.load_artifact(filename=artifact_id)
                        modified_parts.extend([
                            part,
                            types.Part(text=f"[Tool Artifact: {artifact_id}]"),
                            artifact
                        ])
                    else:
                        modified_parts.append(part)
                else:
                    modified_parts.append(part)

            # Keep other parts unchanged
            else:
                modified_parts.append(part)

        content.parts = modified_parts
    return None  # Continue with modified request

agent = LlmAgent(
    name="vl_agent",
    model="gemini-2.0-flash",  # VL-capable model
    before_model_callback=inject_artifacts,
    tools=[load_image]
)
```

**Key Points:**
- Tools use `tool_context.save_artifact()` to store images
- Tools return `tool_response_artifact_id` in response dict
- Callback uses `callback_context.load_artifact()` to retrieve images
- Text markers (`[User Image: ...]`, `[Tool Artifact: ...]`) help VL model understand context
- User inline_data is hashed to generate unique artifact IDs

**Warning (LiteLlm/OpenAI-compatible endpoints):** Do not inject images into the same Content that contains a `function_response`. The LiteLlm adapter converts `function_response` to OpenAI's `tool` message format, which only supports string content - other parts like `inline_data` are silently dropped. Instead, append images as a separate user Content. See [Troubleshooting](#litellm-images-lost-in-function_response-content) for details.

## Best Practices

1. **Use Correct Context Type**: `CallbackContext` for agent/model, `ToolContext` for tools
2. **Return None to Continue**: Return `None` to proceed with normal execution
3. **Return Value to Override**: Return a response to short-circuit execution
4. **Keep Callbacks Fast**: Avoid heavy processing that blocks the agent
5. **Handle Exceptions**: Wrap callback logic in try-except to prevent agent failures
6. **Use State for Communication**: Pass data between callbacks via `context.state`

```python
# Pattern: Safe callback with error handling
def safe_callback(context, *args):
    try:
        # Callback logic
        pass
    except Exception as e:
        logging.error(f"Callback error: {e}")
        return None  # Continue normally on error
```

## Troubleshooting

### LiteLlm: Images Lost in function_response Content

**Symptom**: When using `before_model_callback` to inject images into a Content that contains `function_response`, the VL model reports it cannot see the image.

**Cause**: ADK's LiteLlm adapter converts `function_response` to OpenAI's `tool` message format, which only supports string content. Other parts (text, inline_data) in the same Content are silently dropped.

**Solution**: Never inject images into Content containing `function_response`. Instead, append a new user Content:

```python
# ❌ Wrong - image will be lost
for content in llm_request.contents:
    for part in content.parts:
        if part.function_response:
            content.parts.append(image_part)  # Lost!

# ✅ Correct - separate Content for images
llm_request.contents.append(
    types.Content(
        role="user",
        parts=[types.Part(text="[Image from tool]"), image_part]
    )
)
```

**Applies to**: Any OpenAI-compatible endpoint via LiteLlm (Qwen, DeepSeek, etc.)

## Resources
- Callback patterns: https://google.github.io/adk-docs/callbacks/design-patterns-and-best-practices/
- Callback reference: https://google.github.io/adk-docs/callbacks/
