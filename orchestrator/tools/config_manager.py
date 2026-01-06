"""Form configuration management tools."""

from typing import Any

from google.adk.tools import ToolContext


def set_form_config(
    fields: list[dict[str, Any]],
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Set the form field configuration for table filling.

    This configuration will be used for all subsequent PDF processing.
    Call this before processing any PDFs.

    Args:
        fields: List of field configurations. Each field should have:
            - name: str - Field name, unique identifier (required)
            - description: str - What this field represents (helps extraction)
            - field_type: str - Data type: text, number, date, currency, phone, email, id_number
            - required: bool - Whether this field must be filled
            - aliases: list[str] - Alternative names used in documents

    Returns:
        Confirmation of saved configuration

    Example:
        set_form_config([
            {"name": "合同编号", "description": "合同的唯一编号", "field_type": "text", "required": True},
            {"name": "甲方名称", "description": "合同甲方公司或个人名称", "field_type": "text", "required": True},
            {"name": "合同金额", "description": "合同总金额", "field_type": "currency", "aliases": ["金额", "总价"]},
            {"name": "签订日期", "description": "合同签订日期", "field_type": "date", "aliases": ["签约日期", "日期"]},
        ])
    """
    if not fields:
        return {"status": "error", "error": "No fields provided. Please specify at least one field."}

    # Validate and normalize fields
    validated_fields = []
    field_names = set()

    for i, field in enumerate(fields):
        # Check required 'name' property
        if "name" not in field or not field["name"]:
            return {
                "status": "error",
                "error": f"Field at index {i} is missing required 'name' property",
            }

        name = field["name"]

        # Check for duplicate names
        if name in field_names:
            return {
                "status": "error",
                "error": f"Duplicate field name: '{name}'",
            }
        field_names.add(name)

        # Normalize field configuration
        validated_field = {
            "name": name,
            "description": field.get("description", ""),
            "field_type": field.get("field_type", "text"),
            "required": field.get("required", False),
            "aliases": field.get("aliases", []),
            "validation_rules": field.get("validation_rules", {}),
        }
        validated_fields.append(validated_field)

    # Save to session state (persists across conversation turns)
    tool_context.state["form_config"] = validated_fields

    return {
        "status": "success",
        "message": f"Form configuration saved with {len(validated_fields)} fields.",
        "field_count": len(validated_fields),
        "fields": [
            {
                "name": f["name"],
                "type": f["field_type"],
                "required": f["required"],
            }
            for f in validated_fields
        ],
    }


def get_form_config(tool_context: ToolContext) -> dict[str, Any]:
    """
    Retrieve the current form field configuration.

    Returns:
        Current field configuration or message if not configured
    """
    config = tool_context.state.get("form_config", [])

    if not config:
        return {
            "status": "not_configured",
            "message": "No form configuration set. Use set_form_config to configure fields first.",
            "hint": "Tell me what fields you need to extract from the contracts.",
        }

    return {
        "status": "success",
        "field_count": len(config),
        "fields": config,
    }


def clear_form_config(tool_context: ToolContext) -> dict[str, Any]:
    """
    Clear the current form configuration.

    Returns:
        Confirmation of cleared configuration
    """
    if "form_config" in tool_context.state:
        del tool_context.state["form_config"]
        return {"status": "success", "message": "Form configuration cleared."}

    return {"status": "success", "message": "No configuration to clear."}
