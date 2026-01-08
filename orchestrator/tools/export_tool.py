"""导出工具。"""

from datetime import datetime
from pathlib import Path
from typing import Literal

from google.adk.tools import ToolContext

from shared.state_keys import StateKeys
from table_filler.models.recipe import Recipe
from table_filler.exporters.excel_exporter import ExcelExporter


async def export_results(
    tool_context: ToolContext,
    output_path: str | None = None,
    format: Literal["excel", "json", "csv"] = "excel",
    include_failed: bool = False,
    include_needs_review: bool = True,
) -> dict:
    """导出处理结果到文件。

    将批处理结果导出到指定格式的文件。目前支持 Excel 格式。

    Excel 文件包含：
    - "Successful" sheet: 成功提取的记录
    - "Needs Review" sheet: 需要人工审核的记录（可选）
    - "Failed" sheet: 处理失败的记录（可选）
    - "Summary" sheet: 处理统计信息

    Args:
        output_path: 输出文件路径。如果不指定，自动生成带时间戳的文件名。
        format: 输出格式，目前支持 "excel"。
        include_failed: 是否包含失败记录，默认 False。
        include_needs_review: 是否包含需审核记录，默认 True。

    Returns:
        dict 包含:
        - status: "success" 或 "error"
        - file_path: 输出文件的绝对路径
        - message: 描述信息
        - statistics: 各类别记录数
        - sheets: 创建的 sheet 列表

    Example:
        >>> await export_results(ctx, "/output/results.xlsx")
        {
            "status": "success",
            "file_path": "/output/results.xlsx",
            "message": "Excel 文件已导出: /output/results.xlsx",
            ...
        }

        >>> await export_results(ctx)  # 自动生成文件名
        # 生成: export_20240115_143052.xlsx
    """
    # 获取批处理结果
    batch_results = tool_context.state.get(StateKeys.BATCH_RESULTS)
    if not batch_results:
        return {
            "status": "error",
            "error": "没有批处理结果。请先运行 batch_process_documents。",
        }

    # 获取 Recipe
    recipe_dict = tool_context.state.get(StateKeys.RECIPE)
    if not recipe_dict:
        return {
            "status": "error",
            "error": "没有找到 Recipe。",
        }

    try:
        recipe = Recipe.model_validate(recipe_dict)
    except Exception as e:
        return {
            "status": "error",
            "error": f"Recipe 格式错误: {str(e)}",
        }

    # 目前只支持 Excel
    if format != "excel":
        return {
            "status": "error",
            "error": f"暂不支持 {format} 格式。目前支持: excel",
        }

    # 生成输出路径
    if not output_path:
        exporter = ExcelExporter()
        output_path = exporter.generate_filename("export")

    output_path = Path(output_path)

    # 执行导出
    exporter = ExcelExporter()
    result = exporter.export(
        results=batch_results,
        output_path=output_path,
        recipe=recipe,
        include_failed=include_failed,
        include_needs_review=include_needs_review,
    )

    return result
