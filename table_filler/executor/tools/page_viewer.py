"""页面查看工具。

供 VL 模型查看文档页面，返回图片内容。
"""

import base64
from typing import Any

from google.adk.tools import ToolContext
from google.genai import types

from shared.state_keys import StateKeys


def get_page_count(tool_context: ToolContext) -> dict[str, Any]:
    """获取当前文档的总页数。

    在开始提取前调用此工具，了解文档规模并规划查看策略。
    必须在 load_document() 之后、view_page() 之前调用。

    Returns:
        dict 包含:
        - total_pages: 文档总页数
        - document_path: 当前文档路径
        - document_type: 文档类型 (pdf/image)
        - message: 描述信息

    Example:
        >>> get_page_count()
        {"total_pages": 5, "message": "文档共 5 页"}
    """
    images = tool_context.state.get(StateKeys.DOCUMENT_IMAGES, [])
    doc_path = tool_context.state.get(StateKeys.DOCUMENT_PATH, "")
    doc_type = tool_context.state.get(StateKeys.DOCUMENT_TYPE, "")

    if not images:
        return {
            "total_pages": 0,
            "document_path": None,
            "document_type": None,
            "message": "没有加载文档。请先调用 load_document() 加载文档。",
        }

    return {
        "total_pages": len(images),
        "document_path": doc_path,
        "document_type": doc_type,
        "message": f"文档共 {len(images)} 页",
    }


def view_page(
    tool_context: ToolContext,
    page_number: int,
) -> types.Content:
    """查看文档的指定页面。

    像人类翻阅文档一样查看特定页面。返回的页面图片可供 VL 模型直接分析，
    识别文字、表格、签名、印章等视觉元素。

    这是提取数据的主要工具。每查看一页，请仔细阅读内容，
    发现字段值时使用 add_note() 记录。

    Args:
        page_number: 页码（从 1 开始）。必须在 1 到总页数之间。

    Returns:
        types.Content 包含页面图片，可供 VL 模型直接查看分析。
        如果页码无效或未加载文档，返回错误信息。

    Example:
        >>> view_page(1)   # 查看第一页
        >>> view_page(3)   # 查看第三页

        典型工作流程:
        1. get_page_count() → 5 页
        2. view_page(1) → 看到第一页，提取信息
        3. add_note("contract_id: ABC-123", "field")
        4. view_page(2) → 看到第二页，继续提取
    """
    images = tool_context.state.get(StateKeys.DOCUMENT_IMAGES, [])

    if not images:
        return types.Content(
            parts=[
                types.Part.from_text(
                    "错误: 没有加载文档。请先调用 load_document() 加载文档。"
                )
            ]
        )

    total_pages = len(images)

    # 验证页码 (1-indexed)
    if page_number < 1 or page_number > total_pages:
        return types.Content(
            parts=[
                types.Part.from_text(
                    f"错误: 页码 {page_number} 无效。有效范围: 1 到 {total_pages}。"
                )
            ]
        )

    # 获取图片 (转换为 0-indexed)
    image_base64 = images[page_number - 1]

    # 记录查看的页面
    viewed_pages = tool_context.state.get(StateKeys.VIEWED_PAGES, [])
    if page_number not in viewed_pages:
        viewed_pages.append(page_number)
        tool_context.state[StateKeys.VIEWED_PAGES] = viewed_pages

    # 记录当前查看的页面，供 notebook 使用
    tool_context.state[StateKeys.CURRENT_PAGE] = page_number

    # 解码图片
    image_bytes = base64.b64decode(image_base64)

    # 返回图片内容供 VL 模型查看
    return types.Content(
        parts=[
            types.Part.from_text(f"第 {page_number} 页 / 共 {total_pages} 页:"),
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        ]
    )
