"""Transfer 工具。

用于 Planner 完成配置后返回主对话。
"""

from google.adk.tools import ToolContext

from shared.state_keys import StateKeys
from table_filler.models.recipe import Recipe


async def finish_planning(
    tool_context: ToolContext,
) -> dict:
    """完成配置，返回主对话。

    当 Recipe 配置完成后调用此工具，将控制权转回 conversation_agent。
    会自动验证配方是否有效。

    Returns:
        dict 包含:
        - status: "success" 或 "error"
        - recipe_summary: 配方摘要
        - message: 描述信息
    """
    recipe_dict = tool_context.state.get(StateKeys.RECIPE)
    if not recipe_dict:
        return {
            "status": "error",
            "message": "没有配方，请先创建配方再完成配置",
        }

    try:
        recipe = Recipe.model_validate(recipe_dict)

        if not recipe.fields:
            return {
                "status": "error",
                "message": "配方没有定义任何字段，请先添加字段",
            }

        # 设置 transfer
        tool_context.actions.transfer_to_agent = "conversation_agent"

        return {
            "status": "success",
            "recipe_summary": {
                "recipe_id": recipe.recipe_id,
                "name": recipe.name,
                "document_type": recipe.document_type,
                "field_count": len(recipe.fields),
                "required_field_count": len(recipe.get_required_fields()),
                "fields": recipe.get_field_names(),
            },
            "message": f"配方 '{recipe.name}' 配置完成，共 {len(recipe.fields)} 个字段。"
            "现在可以处理文档了。",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"完成配置失败: {str(e)}",
        }
