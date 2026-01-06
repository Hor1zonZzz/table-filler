"""Form configuration management tools for defining extraction fields."""

from typing import Any

from google.adk.tools import ToolContext


def set_form_config(
    fields: list[dict[str, Any]],
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Configure the form fields to extract from contract documents.

    Use this tool BEFORE processing any PDFs. The configuration defines which
    fields the VL model should look for when viewing document pages. This
    configuration persists across the entire session and applies to all
    subsequent PDF processing.

    Args:
        fields: List of field configuration dictionaries. Each field should have:
            - name (str, required): Unique field identifier, e.g., "contract_id"
            - description (str): What this field represents - helps the VL model
                understand what to look for, e.g., "The unique contract number"
            - field_type (str): Data type hint: "text", "number", "date",
                "currency", "phone", "email", "id_number", or any custom type
            - required (bool): Whether this field must be found (default: false)
            - aliases (list[str]): Alternative names used in documents,
                e.g., ["Contract No.", "Agreement ID"]

    Returns:
        A dictionary containing:
        - status: "success" or "error"
        - message: Confirmation or error message
        - field_count: Number of configured fields (if successful)
        - fields: Summary of configured fields (if successful)
        - error: Error description (if failed)

    Example:
        >>> set_form_config([
        ...     {
        ...         "name": "contract_id",
        ...         "description": "Unique contract identifier number",
        ...         "field_type": "text",
        ...         "required": True
        ...     },
        ...     {
        ...         "name": "party_a",
        ...         "description": "Name of the first contracting party",
        ...         "field_type": "text",
        ...         "required": True
        ...     },
        ...     {
        ...         "name": "total_amount",
        ...         "description": "Total contract value",
        ...         "field_type": "currency",
        ...         "aliases": ["amount", "contract value", "price"]
        ...     },
        ...     {
        ...         "name": "signing_date",
        ...         "description": "Date when contract was signed",
        ...         "field_type": "date",
        ...         "aliases": ["date", "effective date"]
        ...     }
        ... ])
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

    Use this tool to check what fields are currently configured for extraction.
    Helpful for verifying settings before processing PDFs or showing users
    the current configuration.

    Returns:
        A dictionary containing:
        - status: "success" or "not_configured"
        - field_count: Number of configured fields (if configured)
        - fields: Full field configuration list (if configured)
        - message: Status message
        - hint: Suggestion if not configured

    Example:
        >>> get_form_config()
        {
            "status": "success",
            "field_count": 4,
            "fields": [
                {"name": "contract_id", "field_type": "text", ...},
                ...
            ]
        }
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
    Remove the current form field configuration.

    Use this tool to reset the configuration when you need to define a
    completely new set of fields. After clearing, you must call set_form_config
    again before processing any PDFs.

    Returns:
        A dictionary containing:
        - status: "success"
        - message: Confirmation that configuration was cleared

    Example:
        >>> clear_form_config()
        {"status": "success", "message": "Form configuration cleared."}
    """
    if "form_config" in tool_context.state:
        del tool_context.state["form_config"]
        return {"status": "success", "message": "Form configuration cleared."}

    return {"status": "success", "message": "No configuration to clear."}
