"""Recipe 验证工具。

验证当前 Recipe 的完整性和有效性。
"""

from google.adk.tools import ToolContext

from shared.state_keys import StateKeys
from table_filler.models.recipe import Recipe, FieldType


async def validate_recipe(
    tool_context: ToolContext,
) -> dict:
    """验证当前 Recipe 的完整性。

    检查 Recipe 是否配置正确，包括：
    - 是否有字段定义
    - 必填字段是否有描述
    - 枚举类型是否有选项
    - 字段名是否符合规范

    Returns:
        dict 包含:
        - status: "valid", "warning", 或 "invalid"
        - issues: 问题列表
        - suggestions: 改进建议
        - summary: 配方摘要
    """
    recipe_dict = tool_context.state.get(StateKeys.RECIPE)
    if not recipe_dict:
        return {
            "status": "invalid",
            "issues": ["没有找到配方，请先调用 create_recipe()"],
            "suggestions": [],
            "summary": None,
        }

    try:
        recipe = Recipe.model_validate(recipe_dict)
    except Exception as e:
        return {
            "status": "invalid",
            "issues": [f"配方格式错误: {str(e)}"],
            "suggestions": [],
            "summary": None,
        }

    issues = []
    suggestions = []

    # 检查是否有字段
    if not recipe.fields:
        issues.append("配方没有定义任何字段")

    # 检查每个字段
    for field in recipe.fields:
        # 检查字段名规范
        if not field.name.replace("_", "").isalnum():
            issues.append(
                f"字段名 '{field.name}' 包含非法字符，应只使用字母、数字和下划线"
            )

        # 检查必填字段的描述
        if field.required and not field.description:
            suggestions.append(
                f"建议为必填字段 '{field.name}' 添加描述，帮助提取更准确"
            )

        # 检查枚举类型
        if field.field_type == FieldType.ENUM and not field.enum_choices:
            issues.append(f"枚举字段 '{field.name}' 没有定义选项 (enum_choices)")

        # 检查别名
        if not field.aliases and not field.description:
            suggestions.append(
                f"建议为字段 '{field.name}' 添加别名或描述，提高提取成功率"
            )

    # 检查配方元数据
    if not recipe.name:
        suggestions.append("建议为配方添加名称")

    if not recipe.global_context:
        suggestions.append("建议添加 global_context，帮助 VL 模型理解文档类型")

    # 生成摘要
    required_fields = recipe.get_required_fields()
    summary = {
        "recipe_id": recipe.recipe_id,
        "name": recipe.name,
        "document_type": recipe.document_type,
        "total_fields": len(recipe.fields),
        "required_fields": len(required_fields),
        "field_names": recipe.get_field_names(),
    }

    # 确定状态
    if issues:
        status = "invalid"
    elif suggestions:
        status = "warning"
    else:
        status = "valid"

    return {
        "status": status,
        "issues": issues,
        "suggestions": suggestions,
        "summary": summary,
        "message": _generate_message(status, issues, suggestions),
    }


def _generate_message(
    status: str,
    issues: list[str],
    suggestions: list[str],
) -> str:
    """生成验证结果消息。"""
    if status == "valid":
        return "配方验证通过，可以开始处理文档"
    elif status == "warning":
        return f"配方基本有效，但有 {len(suggestions)} 条改进建议"
    else:
        return f"配方有 {len(issues)} 个问题需要修复"
