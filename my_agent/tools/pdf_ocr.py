"""
PDF OCR 工具 - 使用 OpenAI Vision API 将 PDF 转换为 Markdown
"""

import asyncio
import base64
from pathlib import Path

import fitz  # pymupdf
from dotenv import load_dotenv
from openai import AsyncOpenAI

# 加载 tools 目录下的 .env 配置（覆盖已有值）
_tools_env = Path(__file__).parent / ".env"
if _tools_env.exists():
    load_dotenv(_tools_env, override=True)

async def _ocr_single_page(
    client: AsyncOpenAI,
    image_base64: str,
    page_num: int,
    model: str = "qwen3-vl-8b-instruct",
) -> str:
    """使用 OpenAI Vision API 对单页图片进行 OCR"""

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """请将这张图片中的所有文字内容转换为 Markdown 格式。
要求：
1. 保持原文的结构和层次
2. 正确识别标题、段落、列表、表格等元素
3. 表格使用 Markdown 表格语法
4. 如果有图片或图表，用 [图片描述] 标注
5. 保持原文语言，不要翻译
6. 只输出 Markdown 内容，不要添加额外说明""",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        max_tokens=4096,
    )

    return response.choices[0].message.content or ""


async def _process_pdf_pages(
    pdf_path: str,
    client: AsyncOpenAI,
    model: str = "qwen3-vl-8b-instruct",
    dpi: int = 200,
) -> list[dict]:
    """处理 PDF 所有页面并返回 OCR 结果"""

    doc = fitz.open(pdf_path)
    results = []

    # 将所有页面转换为图片
    pages_data = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        # 使用更高的 DPI 获取更清晰的图片
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        image_bytes = pix.tobytes("png")
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        pages_data.append((page_num + 1, image_base64))

    doc.close()

    # 并发处理所有页面的 OCR
    tasks = [
        _ocr_single_page(client, image_base64, page_num, model)
        for page_num, image_base64 in pages_data
    ]

    ocr_results = await asyncio.gather(*tasks, return_exceptions=True)

    for (page_num, _), result in zip(pages_data, ocr_results):
        if isinstance(result, Exception):
            results.append({
                "page": page_num,
                "content": f"[OCR 错误: {str(result)}]",
                "error": True,
            })
        else:
            results.append({
                "page": page_num,
                "content": result,
                "error": False,
            })

    return results


def pdf_to_markdown(
    pdf_path: str,
    model: str = "gpt-4o",
    dpi: int = 200,
) -> dict:
    """
    将 PDF 文件的每一页进行 OCR 并转换为 Markdown 格式。

    Args:
        pdf_path: PDF 文件的路径（支持绝对路径或相对路径）
        model: 用于 OCR 的 OpenAI 模型名称，默认为 gpt-4o
        dpi: 渲染 PDF 页面的 DPI，默认为 200

    Returns:
        包含 OCR 结果的字典：
        - status: 处理状态 (success/error)
        - total_pages: PDF 总页数
        - pages: 每页的 OCR 结果列表
        - markdown: 合并后的完整 Markdown 文本
        - error: 错误信息（如果有）
    """

    # 验证文件路径
    path = Path(pdf_path)
    if not path.exists():
        return {
            "status": "error",
            "error": f"文件不存在: {pdf_path}",
        }

    if not path.suffix.lower() == ".pdf":
        return {
            "status": "error",
            "error": f"不是 PDF 文件: {pdf_path}",
        }

    # 创建异步客户端
    client = AsyncOpenAI()

    # 运行异步处理
    try:
        results = asyncio.run(
            _process_pdf_pages(str(path), client, model, dpi)
        )
    except Exception as e:
        return {
            "status": "error",
            "error": f"处理 PDF 时出错: {str(e)}",
        }

    # 合并所有页面的 Markdown
    markdown_parts = []
    for result in results:
        page_header = f"<!-- Page {result['page']} -->\n"
        markdown_parts.append(page_header + result["content"])

    full_markdown = "\n\n---\n\n".join(markdown_parts)

    # 统计错误页数
    error_count = sum(1 for r in results if r.get("error"))

    return {
        "status": "success" if error_count == 0 else "partial_success",
        "total_pages": len(results),
        "error_pages": error_count,
        "pages": results,
        "markdown": full_markdown,
    }
