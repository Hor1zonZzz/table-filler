"""Table Filler 的回调函数。

处理 VL 模型的图片注入，确保工具返回的图片能被模型正确看到。
"""

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest
from google.genai.types import Part, Content

# 返回图片的工具名称
IMAGE_TOOLS = ["view_page", "view_all_pages"]


async def before_model_modifier(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> LlmResponse | None:
    """修改 LLM 请求，注入工具返回的图片。

    对于 LiteLlm/OpenAI 兼容的端点，图片必须放在单独的 user Content 中，
    不能和 function_response 放在同一个 Content 里。

    Args:
        callback_context: 回调上下文
        llm_request: LLM 请求对象

    Returns:
        None（继续处理）或 LlmResponse（中断处理）
    """
    artifacts_to_inject = []

    for content in llm_request.contents:
        if not content.parts:
            continue

        modified_parts = []
        for part in content.parts:
            # 处理用户上传的内联图片（保留在同一 Content 中）
            if part.inline_data:
                processed_parts = await _process_inline_data_part(
                    part, callback_context
                )
                modified_parts.extend(processed_parts)

            # 处理函数响应 - 收集 artifacts，不在这里注入
            elif part.function_response:
                if part.function_response.name in IMAGE_TOOLS:
                    extracted = await _extract_artifacts_from_response(
                        part, callback_context
                    )
                    artifacts_to_inject.extend(extracted)
                # 保留 function_response 原样
                modified_parts.append(part)

            # 默认：保持 part 不变
            else:
                modified_parts.append(part)

        content.parts = modified_parts

    # 将收集的 artifacts 作为单独的 user Content 追加
    # 避免 LiteLlm 丢弃 function_response Content 中的图片
    if artifacts_to_inject:
        if len(artifacts_to_inject) == 1:
            intro_text = "[工具加载的图片] 请分析以下内容:"
        else:
            intro_text = f"[工具加载了 {len(artifacts_to_inject)} 张图片] 请按顺序分析:"

        llm_request.contents.append(
            Content(
                role="user",
                parts=[
                    Part(text=intro_text),
                    *artifacts_to_inject,
                ],
            )
        )

    return None


async def _process_inline_data_part(
    part: Part,
    callback_context: CallbackContext,
) -> list[Part]:
    """处理内联数据 parts（用户上传的图片）。

    Returns:
        包含 artifact 标记和图片的 parts 列表。
    """
    import hashlib

    artifact_id = _generate_artifact_id(part)

    # 如果 artifact 不存在则保存
    if artifact_id not in await callback_context.list_artifacts():
        await callback_context.save_artifact(filename=artifact_id, artifact=part)

    return [
        Part(text=f"[用户上传的图片] Artifact ID: {artifact_id}"),
        part,
    ]


def _generate_artifact_id(part: Part) -> str:
    """为用户上传的图片生成唯一的 artifact ID。

    Returns:
        基于哈希的 artifact ID，带有正确的文件扩展名。
    """
    import hashlib

    filename = part.inline_data.display_name or "uploaded_image"
    image_data = part.inline_data.data

    # 组合文件名和图片数据生成哈希
    hash_input = filename.encode("utf-8") + image_data
    content_hash = hashlib.sha256(hash_input).hexdigest()[:16]

    # 从 mime type 提取文件扩展名
    mime_type = part.inline_data.mime_type
    extension = mime_type.split("/")[-1]

    return f"usr_upl_img_{content_hash}.{extension}"


async def _extract_artifacts_from_response(
    part: Part,
    callback_context: CallbackContext,
) -> list[Part]:
    """从函数响应中提取 artifact(s)。

    支持单个 artifact (tool_response_artifact_id) 和
    多个 artifacts (tool_response_artifact_ids) 用于批量加载。

    Returns:
        artifact Parts 列表（如果没有找到则为空列表）。
    """
    artifacts = []

    # 单个 artifact 情况
    response = part.function_response.response
    if isinstance(response, dict):
        artifact_id = response.get("tool_response_artifact_id")
        if artifact_id:
            artifact = await callback_context.load_artifact(filename=artifact_id)
            if artifact:
                artifacts.append(artifact)
            return artifacts

        # 多个 artifacts 情况
        artifact_ids = response.get("tool_response_artifact_ids", [])
        for aid in artifact_ids:
            artifact = await callback_context.load_artifact(filename=aid)
            if artifact:
                artifacts.append(artifact)

    return artifacts
