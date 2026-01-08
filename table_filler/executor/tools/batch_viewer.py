"""批量页面查看工具。

一次性加载所有页面，供 VL 模型在单次对话中分析整个文档。
"""

import base64
from typing import Any

from google.adk.tools import ToolContext
from google.genai import types

from shared.state_keys import StateKeys

MAX_PAGES = 50  # 最大支持页数


async def view_all_pages(tool_context: ToolContext) -> dict[str, Any]:
    """一次性加载所有页面为图片。

    将文档所有页面创建为 artifacts，通过 before_model_callback 注入到模型上下文。
    VL 模型可以在单次对话中看到并分析所有页面，无需多次调用。

    限制：最多支持 50 页。超过此限制的文档会返回错误，需要用户分批处理或使用其他方式。

    调用前必须先执行 load_document() 加载文档到 state。

    Returns:
        dict 包含:
        - status: "success" 或 "error"
        - tool_response_artifact_ids: 所有页面的 artifact ID 列表（成功时）
        - total_pages: 文档总页数
        - message: 描述信息

    Example:
        >>> # 先加载文档
        >>> load_document("/path/to/document.pdf")
        >>> # 然后批量查看所有页面
        >>> view_all_pages()
        {
            "status": "success",
            "tool_response_artifact_ids": ["tbl_p1_xxx.png", "tbl_p2_xxx.png", ...],
            "total_pages": 24,
            "message": "已加载全部 24 页。请按顺序分析每一页。"
        }
    """
    images = tool_context.state.get(StateKeys.DOCUMENT_IMAGES, [])
    doc_path = tool_context.state.get(StateKeys.DOCUMENT_PATH, "")

    if not images:
        return {
            "status": "error",
            "tool_response_artifact_ids": [],
            "total_pages": 0,
            "message": "没有加载文档。请先调用 load_document() 加载文档。",
        }

    total_pages = len(images)

    # 检查页数限制
    if total_pages >= MAX_PAGES:
        return {
            "status": "error",
            "tool_response_artifact_ids": [],
            "total_pages": total_pages,
            "max_pages": MAX_PAGES,
            "message": f"文档共 {total_pages} 页，超过最大限制 {MAX_PAGES} 页，无法处理。请将文档拆分后重试。",
        }

    # 为每页创建 artifact
    artifact_ids = []
    for page_num, image_base64 in enumerate(images):
        image_bytes = base64.b64decode(image_base64)
        part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        artifact_id = f"tbl_p{page_num + 1}_{tool_context.function_call_id}.png"
        await tool_context.save_artifact(filename=artifact_id, artifact=part)
        artifact_ids.append(artifact_id)

    # 记录已查看所有页面
    tool_context.state[StateKeys.VIEWED_PAGES] = list(range(1, total_pages + 1))

    return {
        "status": "success",
        "tool_response_artifact_ids": artifact_ids,
        "total_pages": total_pages,
        "document_path": doc_path,
        "message": f"已加载全部 {total_pages} 页。请按顺序分析每一页，提取所需字段。",
    }
