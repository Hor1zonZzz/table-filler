from google.adk.tools import ToolContext
from google.genai import types
import os

SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
}


async def picture_loader(
    tool_context: ToolContext,
    image_path: str,
) -> dict[str, str]:
    """Load an image from local file path for VL model analysis.

    Args:
        image_path: Local file path to the image (PNG, JPG, JPEG, GIF, BMP, WEBP)

    Returns:
        dict with:
            - tool_response_artifact_id: Artifact ID for callback injection
            - status: success/error
            - message: Description
    """
    # 1. 验证文件存在
    if not os.path.exists(image_path):
        return {
            "status": "error",
            "tool_response_artifact_id": "",
            "message": f"File not found: {image_path}",
        }

    # 2. 验证格式
    ext = os.path.splitext(image_path)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        return {
            "status": "error",
            "tool_response_artifact_id": "",
            "message": f"Unsupported format: {ext}. Supported: {', '.join(SUPPORTED_FORMATS)}",
        }

    # 3. 读取文件
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # 4. 创建 Part 并保存 artifact
    mime_type = MIME_TYPES[ext]
    part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    artifact_id = f"loaded_img_{tool_context.function_call_id}{ext}"
    await tool_context.save_artifact(filename=artifact_id, artifact=part)

    return {
        "status": "success",
        "tool_response_artifact_id": artifact_id,
        "message": f"Image loaded: {os.path.basename(image_path)}",
    }
