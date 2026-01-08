"""文档加载工具。

加载 PDF 或图片文档，将其转换为图片存储在 state 中供 VL 模型查看。
"""

import base64
from pathlib import Path

from google.adk.tools import ToolContext

from shared.state_keys import StateKeys
from shared.constants import PDF_EXTENSIONS, IMAGE_EXTENSIONS, DEFAULT_PDF_DPI


async def load_document(
    tool_context: ToolContext,
    document_path: str,
    dpi: int = DEFAULT_PDF_DPI,
) -> dict:
    """加载 PDF 或图片文档。

    将文档转换为 base64 图片列表存储在 state 中，供后续 view_page() 使用。
    支持 PDF 文件（多页）和图片文件（单页）。

    Args:
        document_path: 文档路径（PDF 或图片文件）
        dpi: PDF 渲染分辨率，默认 150

    Returns:
        dict 包含:
        - status: "success" 或 "error"
        - document_path: 文档路径
        - document_type: "pdf" 或 "image"
        - total_pages: 总页数
        - message: 描述信息

    Example:
        >>> await load_document(ctx, "/path/to/contract.pdf")
        {"status": "success", "total_pages": 5, ...}

        >>> await load_document(ctx, "/path/to/scan.png")
        {"status": "success", "total_pages": 1, ...}
    """
    path = Path(document_path)

    if not path.exists():
        return {
            "status": "error",
            "message": f"文件不存在: {document_path}",
        }

    suffix = path.suffix.lower()

    # 检查文件类型
    if suffix not in PDF_EXTENSIONS and suffix not in IMAGE_EXTENSIONS:
        return {
            "status": "error",
            "message": f"不支持的文件类型: {suffix}。支持: PDF, PNG, JPG, JPEG, GIF, BMP, WEBP",
        }

    try:
        images: list[str] = []

        # 处理 PDF
        if suffix in PDF_EXTENSIONS:
            from vl_agent.tools.pdf_renderer import (
                render_pdf_page,
                get_pdf_page_count,
            )

            total_pages = get_pdf_page_count(document_path)

            # 渲染所有页面
            for page_num in range(total_pages):
                image_bytes = render_pdf_page(document_path, page_num, dpi)
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                images.append(image_base64)

            doc_type = "pdf"

        # 处理图片
        else:
            with open(document_path, "rb") as f:
                image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            images.append(image_base64)

            total_pages = 1
            doc_type = "image"

        # 存储到 state
        tool_context.state[StateKeys.DOCUMENT_IMAGES] = images
        tool_context.state[StateKeys.DOCUMENT_PATH] = document_path
        tool_context.state[StateKeys.DOCUMENT_TYPE] = doc_type
        tool_context.state[StateKeys.VIEWED_PAGES] = []
        tool_context.state[StateKeys.NOTEBOOK] = []

        return {
            "status": "success",
            "document_path": document_path,
            "document_type": doc_type,
            "total_pages": total_pages,
            "message": f"文档加载成功: {path.name}，共 {total_pages} 页",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"加载文档失败: {str(e)}",
        }
