"""Schema management tools for VL agent."""

import json
from google.adk.tools import ToolContext

VALID_TYPES = {"string", "number", "date", "boolean"}


def _get_fields(tool_context: ToolContext) -> list[dict]:
    """Load schema fields from state."""
    raw = tool_context.state.get("schema_fields", "[]")
    return json.loads(raw) if raw else []


def _save_fields(tool_context: ToolContext, fields: list[dict]) -> None:
    """Save schema fields to state."""
    tool_context.state["schema_fields"] = json.dumps(fields, ensure_ascii=False)


def _is_confirmed(tool_context: ToolContext) -> bool:
    """Check if schema is confirmed."""
    return tool_context.state.get("schema_confirmed") == "true"


def schema_add_field(
    tool_context: ToolContext,
    name: str,
    desc: str,
    type: str,
    required: bool = True,
    default: str | None = None,
) -> str:
    """Add a field to the schema.

    Args:
        name: Field name (unique identifier).
        desc: Field description.
        type: Data type - "string", "number", "date", "boolean".
        required: Whether the field is required.
        default: Default value if missing.

    Returns:
        "success" or error message.
    """
    if _is_confirmed(tool_context):
        return "error: schema is confirmed, call schema_reset first"
    if type not in VALID_TYPES:
        return f"error: invalid type '{type}', must be one of {VALID_TYPES}"

    fields = _get_fields(tool_context)
    if any(f["name"] == name for f in fields):
        return f"error: field '{name}' already exists"

    fields.append({
        "name": name,
        "desc": desc,
        "type": type,
        "required": required,
        "default": default,
    })
    _save_fields(tool_context, fields)
    return "success"


def schema_remove_field(tool_context: ToolContext, name: str) -> str:
    """Remove a field from the schema.

    Args:
        name: Field name to remove.

    Returns:
        "success" or error message.
    """
    if _is_confirmed(tool_context):
        return "error: schema is confirmed, call schema_reset first"

    fields = _get_fields(tool_context)
    new_fields = [f for f in fields if f["name"] != name]
    if len(new_fields) == len(fields):
        return f"error: field '{name}' not found"

    _save_fields(tool_context, new_fields)
    return "success"


def schema_update_field(
    tool_context: ToolContext,
    name: str,
    updates: dict,
) -> str:
    """Update field attributes.

    Args:
        name: Field name to update.
        updates: Dict of attributes to update (desc, type, required, default).

    Returns:
        "success" or error message.
    """
    if _is_confirmed(tool_context):
        return "error: schema is confirmed, call schema_reset first"

    fields = _get_fields(tool_context)
    for field in fields:
        if field["name"] == name:
            if "type" in updates and updates["type"] not in VALID_TYPES:
                return f"error: invalid type '{updates['type']}'"
            field.update({k: v for k, v in updates.items() if k != "name"})
            _save_fields(tool_context, fields)
            return "success"
    return f"error: field '{name}' not found"


def schema_list(tool_context: ToolContext) -> str:
    """List all fields in the schema.

    Returns:
        Formatted field list or empty message.
    """
    fields = _get_fields(tool_context)
    if not fields:
        return "Schema is empty."

    confirmed = _is_confirmed(tool_context)
    lines = [f"Schema ({len(fields)} fields)" + (" [CONFIRMED]" if confirmed else ":")]
    for f in fields:
        req = "*" if f.get("required", True) else ""
        default = f" = {f['default']}" if f.get("default") is not None else ""
        lines.append(f"  - {f['name']}{req} ({f['type']}){default}: {f['desc']}")
    return "\n".join(lines)


def schema_confirm(tool_context: ToolContext) -> str:
    """Confirm and lock the schema for processing.

    Returns:
        "success" or error message.
    """
    if _is_confirmed(tool_context):
        return "already confirmed, no need to call again"

    fields = _get_fields(tool_context)
    if not fields:
        return "error: schema is empty, add fields first"

    tool_context.state["schema_confirmed"] = "true"
    return "success"


def schema_reset(tool_context: ToolContext) -> str:
    """Reset schema to empty state.

    Returns:
        "success"
    """
    tool_context.state["schema_fields"] = "[]"
    tool_context.state["schema_confirmed"] = "false"
    return "success"
