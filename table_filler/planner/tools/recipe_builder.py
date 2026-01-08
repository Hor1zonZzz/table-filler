"""Recipe 构建工具。

提供创建、更新、添加、删除 Recipe 字段的工具函数。
"""

from typing import Any

from google.adk.tools import ToolContext

from shared.state_keys import StateKeys
from table_filler.models.recipe import (
    Recipe,
    FieldDefinition,
    FieldType,
    MissingStrategy,
    ExtractionHint,
)


async def create_recipe(
    tool_context: ToolContext,
    name: str,
    description: str,
    document_type: str,
    fields: list[dict[str, Any]],
) -> dict[str, Any]:
    """创建新的提取配方。

    根据用户需求创建一个新的 Recipe，定义要提取的字段及其规则。

    Args:
        name: 配方名称，如 "销售合同提取"
        description: 配方描述，说明用途
        document_type: 文档类型: contract, invoice, form, report, general
        fields: 字段定义列表，每个字段包含:
            - name (str, 必需): 字段唯一标识符 (snake_case)
            - display_name (str): 显示名称
            - description (str): 字段描述
            - field_type (str): 类型: text, number, date, currency 等
            - required (bool): 是否必填
            - aliases (list[str]): 文档中的别名

    Returns:
        dict 包含:
        - status: "success" 或 "error"
        - recipe_id: 配方 ID
        - field_count: 字段数量
        - message: 描述信息

    Example:
        >>> await create_recipe(
        ...     tool_context,
        ...     name="合同提取",
        ...     description="提取销售合同关键信息",
        ...     document_type="contract",
        ...     fields=[
        ...         {"name": "contract_id", "field_type": "text", "required": True},
        ...         {"name": "amount", "field_type": "currency"}
        ...     ]
        ... )
    """
    try:
        # 构建字段定义
        field_definitions = []
        for field_dict in fields:
            # 处理 field_type
            field_type_str = field_dict.get("field_type", "text")
            try:
                field_type = FieldType(field_type_str)
            except ValueError:
                field_type = FieldType.TEXT

            # 处理 extraction_hint
            hint_dict = field_dict.get("extraction_hint", {})
            extraction_hint = ExtractionHint(
                location_hints=hint_dict.get("location_hints", []),
                visual_cues=hint_dict.get("visual_cues", []),
                context_keywords=hint_dict.get("context_keywords", []),
                extraction_prompt=hint_dict.get("extraction_prompt", ""),
            )

            # 处理 missing_strategy
            missing_str = field_dict.get("missing_strategy", "null")
            try:
                missing_strategy = MissingStrategy(missing_str)
            except ValueError:
                missing_strategy = MissingStrategy.NULL

            field_def = FieldDefinition(
                name=field_dict.get("name", ""),
                display_name=field_dict.get("display_name", ""),
                description=field_dict.get("description", ""),
                field_type=field_type,
                aliases=field_dict.get("aliases", []),
                required=field_dict.get("required", False),
                extraction_hint=extraction_hint,
                missing_strategy=missing_strategy,
                default_value=field_dict.get("default_value"),
            )
            field_definitions.append(field_def)

        # 创建 Recipe
        recipe = Recipe(
            name=name,
            description=description,
            document_type=document_type,
            fields=field_definitions,
        )

        # 保存到 state
        tool_context.state[StateKeys.RECIPE] = recipe.model_dump()

        return {
            "status": "success",
            "recipe_id": recipe.recipe_id,
            "field_count": len(recipe.fields),
            "fields": [f.name for f in recipe.fields],
            "message": f"配方 '{name}' 创建成功，包含 {len(recipe.fields)} 个字段",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"创建配方失败: {str(e)}",
        }


async def update_recipe(
    tool_context: ToolContext,
    field_name: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """更新现有字段的属性。

    修改指定字段的配置，如描述、类型、验证规则等。

    Args:
        field_name: 要更新的字段名称
        updates: 要更新的属性，可包含:
            - display_name, description, field_type
            - required, aliases, extraction_hint
            - missing_strategy, default_value

    Returns:
        dict 包含:
        - status: "success" 或 "error"
        - field_name: 更新的字段名
        - changes: 更新的属性列表
        - message: 描述信息
    """
    recipe_dict = tool_context.state.get(StateKeys.RECIPE)
    if not recipe_dict:
        return {
            "status": "error",
            "message": "没有找到配方，请先调用 create_recipe()",
        }

    try:
        recipe = Recipe.model_validate(recipe_dict)

        if not recipe.update_field(field_name, updates):
            return {
                "status": "error",
                "message": f"字段 '{field_name}' 不存在",
            }

        # 保存更新后的 recipe
        tool_context.state[StateKeys.RECIPE] = recipe.model_dump()

        return {
            "status": "success",
            "field_name": field_name,
            "changes": list(updates.keys()),
            "message": f"字段 '{field_name}' 已更新: {', '.join(updates.keys())}",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"更新字段失败: {str(e)}",
        }


async def add_field(
    tool_context: ToolContext,
    field: dict[str, Any],
) -> dict[str, Any]:
    """向配方添加新字段。

    Args:
        field: 字段定义，格式同 create_recipe 的 fields 参数

    Returns:
        dict 包含:
        - status: "success" 或 "error"
        - field_name: 添加的字段名
        - total_fields: 当前总字段数
        - message: 描述信息
    """
    recipe_dict = tool_context.state.get(StateKeys.RECIPE)
    if not recipe_dict:
        return {
            "status": "error",
            "message": "没有找到配方，请先调用 create_recipe()",
        }

    try:
        recipe = Recipe.model_validate(recipe_dict)

        # 处理 field_type
        field_type_str = field.get("field_type", "text")
        try:
            field_type = FieldType(field_type_str)
        except ValueError:
            field_type = FieldType.TEXT

        field_def = FieldDefinition(
            name=field.get("name", ""),
            display_name=field.get("display_name", ""),
            description=field.get("description", ""),
            field_type=field_type,
            aliases=field.get("aliases", []),
            required=field.get("required", False),
            default_value=field.get("default_value"),
        )

        recipe.add_field(field_def)

        # 保存更新后的 recipe
        tool_context.state[StateKeys.RECIPE] = recipe.model_dump()

        return {
            "status": "success",
            "field_name": field_def.name,
            "total_fields": len(recipe.fields),
            "message": f"字段 '{field_def.name}' 已添加，当前共 {len(recipe.fields)} 个字段",
        }

    except ValueError as e:
        return {
            "status": "error",
            "message": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"添加字段失败: {str(e)}",
        }


async def remove_field(
    tool_context: ToolContext,
    field_name: str,
) -> dict[str, Any]:
    """从配方中删除字段。

    Args:
        field_name: 要删除的字段名称

    Returns:
        dict 包含:
        - status: "success" 或 "error"
        - field_name: 删除的字段名
        - remaining_fields: 剩余字段数
        - message: 描述信息
    """
    recipe_dict = tool_context.state.get(StateKeys.RECIPE)
    if not recipe_dict:
        return {
            "status": "error",
            "message": "没有找到配方，请先调用 create_recipe()",
        }

    try:
        recipe = Recipe.model_validate(recipe_dict)

        if not recipe.remove_field(field_name):
            return {
                "status": "error",
                "message": f"字段 '{field_name}' 不存在",
            }

        # 保存更新后的 recipe
        tool_context.state[StateKeys.RECIPE] = recipe.model_dump()

        return {
            "status": "success",
            "field_name": field_name,
            "remaining_fields": len(recipe.fields),
            "message": f"字段 '{field_name}' 已删除，剩余 {len(recipe.fields)} 个字段",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"删除字段失败: {str(e)}",
        }
