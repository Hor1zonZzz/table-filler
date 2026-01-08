"""批量处理工具 - 使用 Recipe 驱动的文档提取。"""

import asyncio
import json
from pathlib import Path
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from shared.state_keys import StateKeys
from shared.constants import MAX_CONCURRENT_DOCUMENTS, MAX_RETRY_ATTEMPTS
from table_filler.executor.pipeline import extraction_pipeline
from table_filler.executor.tools.document_loader import load_document
from table_filler.models.recipe import Recipe
from table_filler.models.verification import VerificationStatus


async def _process_single_document(
    document_path: str,
    recipe: Recipe,
    session_service: InMemorySessionService,
    app_name: str,
) -> dict[str, Any]:
    """处理单个文档。

    Args:
        document_path: 文档路径
        recipe: Recipe 配方
        session_service: Session 服务
        app_name: 应用名称

    Returns:
        处理结果
    """
    result = {
        "document_path": document_path,
        "status": VerificationStatus.FAIL.value,
        "confidence": 0.0,
        "final_record": {},
        "issues": [],
        "error": None,
    }

    # 验证文件存在
    if not Path(document_path).exists():
        result["error"] = f"文件不存在: {document_path}"
        return result

    try:
        # 创建 session
        session = await session_service.create_session(
            app_name=app_name,
            user_id="batch_processor",
        )

        # 设置 state
        session.state[StateKeys.RECIPE] = recipe.model_dump()
        session.state[StateKeys.DOCUMENT_PATH] = document_path
        session.state[StateKeys.NOTEBOOK] = []
        session.state[StateKeys.VIEWED_PAGES] = []

        # 预加载文档图片
        from table_filler.executor.tools.document_loader import load_document
        import base64

        path = Path(document_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            from vl_agent.tools.pdf_renderer import render_pdf_page, get_pdf_page_count

            total_pages = get_pdf_page_count(document_path)
            images = []
            for page_num in range(total_pages):
                image_bytes = render_pdf_page(document_path, page_num, 150)
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                images.append(image_base64)
            session.state[StateKeys.DOCUMENT_IMAGES] = images
            session.state[StateKeys.DOCUMENT_TYPE] = "pdf"
        else:
            with open(document_path, "rb") as f:
                image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            session.state[StateKeys.DOCUMENT_IMAGES] = [image_base64]
            session.state[StateKeys.DOCUMENT_TYPE] = "image"

        # 运行提取管道
        runner = Runner(
            agent=extraction_pipeline,
            app_name=app_name,
            session_service=session_service,
        )

        # 构建提取指令
        field_names = recipe.get_field_names()
        instruction = (
            f"从文档 {path.name} 中提取以下字段: {', '.join(field_names)}。\n"
            f"文档类型: {recipe.document_type}\n"
            f"使用 get_page_count() 和 view_page() 查看文档页面。"
        )

        async for _ in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=instruction)],
            ),
        ):
            pass

        # 收集结果
        extraction_result = session.state.get(StateKeys.EXTRACTION_RESULT, {})
        verification_result = session.state.get(StateKeys.VERIFICATION_RESULT, {})

        # 解析字符串结果
        if isinstance(extraction_result, str):
            try:
                extraction_result = json.loads(extraction_result)
            except json.JSONDecodeError:
                extraction_result = {"raw": extraction_result}

        if isinstance(verification_result, str):
            try:
                verification_result = json.loads(verification_result)
            except json.JSONDecodeError:
                verification_result = {
                    "status": VerificationStatus.NEEDS_REVIEW.value,
                    "raw": verification_result,
                }

        # 构建最终结果
        result["status"] = verification_result.get(
            "status", VerificationStatus.NEEDS_REVIEW.value
        )
        result["confidence"] = verification_result.get("confidence", 0.0)
        result["issues"] = verification_result.get("issues", [])

        # 使用纠正后的记录（如果有）
        corrected = verification_result.get("corrected_record", {})
        if corrected:
            fields = extraction_result.get("fields", extraction_result)
            if isinstance(fields, dict):
                fields.update(corrected)
            result["final_record"] = fields
        else:
            result["final_record"] = extraction_result.get("fields", extraction_result)

    except Exception as e:
        result["error"] = f"处理异常: {str(e)}"

    return result


@retry(
    stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
async def _process_with_retry(
    document_path: str,
    recipe: Recipe,
    session_service: InMemorySessionService,
    app_name: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    """带重试和并发控制的处理。"""
    async with semaphore:
        return await _process_single_document(
            document_path, recipe, session_service, app_name
        )


async def _batch_process_async(
    document_paths: list[str],
    recipe: Recipe,
    max_concurrent: int = MAX_CONCURRENT_DOCUMENTS,
) -> dict[str, Any]:
    """异步批量处理文档。"""
    if not document_paths:
        return {
            "status": "error",
            "error": "没有提供文档路径",
        }

    session_service = InMemorySessionService()
    app_name = "table_filler_batch"

    semaphore = asyncio.Semaphore(max_concurrent)

    tasks = [
        _process_with_retry(doc_path, recipe, session_service, app_name, semaphore)
        for doc_path in document_paths
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 分类结果
    successful = []
    needs_review = []
    failed = []

    for i, result in enumerate(results):
        doc_path = document_paths[i]

        if isinstance(result, Exception):
            failed.append(
                {
                    "document_path": doc_path,
                    "status": VerificationStatus.FAIL.value,
                    "error": str(result),
                    "final_record": {},
                    "issues": [],
                    "confidence": 0.0,
                }
            )
        elif result.get("error"):
            failed.append(result)
        elif result.get("status") == VerificationStatus.PASS.value:
            successful.append(result)
        elif result.get("status") == VerificationStatus.FAIL.value:
            failed.append(result)
        else:
            needs_review.append(result)

    return {
        "status": "success",
        "total_count": len(document_paths),
        "successful_count": len(successful),
        "needs_review_count": len(needs_review),
        "failed_count": len(failed),
        "successful": successful,
        "needs_review": needs_review,
        "failed": failed,
    }


async def batch_process_documents(
    tool_context: ToolContext,
    document_paths: list[str],
    max_concurrent: int = MAX_CONCURRENT_DOCUMENTS,
) -> dict[str, Any]:
    """批量处理文档，提取 Recipe 定义的字段。

    并行处理多个文档（最多 10 个并发），自动重试失败的处理（最多 3 次）。
    必须先配置 Recipe（通过 planner_agent）。

    对于每个文档，VL 模型会：
    1. 直接查看文档页面（无需 OCR）
    2. 提取 Recipe 定义的字段值
    3. 验证提取结果的准确性
    4. 报告置信度和发现的问题

    结果分为三类：
    - 成功: 高置信度，所有必填字段都找到
    - 需审核: 有不确定性或缺少可选字段
    - 失败: 无法处理或有严重错误

    Args:
        document_paths: 文档路径列表（PDF 或图片）
        max_concurrent: 最大并发数，默认 10

    Returns:
        dict 包含:
        - status: "success" 或 "error"
        - message: 处理结果摘要
        - total_count: 总处理数
        - successful_count: 成功数
        - needs_review_count: 需审核数
        - failed_count: 失败数
        - successful: 成功记录列表
        - needs_review: 需审核记录列表
        - failed: 失败记录列表

    Example:
        >>> await batch_process_documents(ctx, [
        ...     "/data/contracts/contract001.pdf",
        ...     "/data/contracts/contract002.pdf",
        ... ])
        {
            "status": "success",
            "message": "处理了 2 个文档: 1 成功, 1 需审核, 0 失败",
            ...
        }
    """
    # 获取 Recipe
    recipe_dict = tool_context.state.get(StateKeys.RECIPE)
    if not recipe_dict:
        return {
            "status": "error",
            "error": "没有配置 Recipe。请先使用 planner_agent 配置提取规则。",
        }

    try:
        recipe = Recipe.model_validate(recipe_dict)
    except Exception as e:
        return {
            "status": "error",
            "error": f"Recipe 格式错误: {str(e)}",
        }

    if not recipe.fields:
        return {
            "status": "error",
            "error": "Recipe 没有定义字段。请先添加要提取的字段。",
        }

    # 验证文档路径
    valid_paths = []
    invalid_paths = []
    for path in document_paths:
        if Path(path).exists():
            valid_paths.append(path)
        else:
            invalid_paths.append(path)

    if invalid_paths:
        print(f"警告: {len(invalid_paths)} 个文件不存在: {invalid_paths[:5]}...")

    if not valid_paths:
        return {
            "status": "error",
            "error": "没有找到有效的文档文件",
            "invalid_paths": invalid_paths,
        }

    # 执行批量处理
    result = await _batch_process_async(valid_paths, recipe, max_concurrent)

    # 存储结果用于导出
    tool_context.state[StateKeys.BATCH_RESULTS] = result

    # 添加摘要消息
    result["message"] = (
        f"处理了 {result['total_count']} 个文档: "
        f"{result['successful_count']} 成功, "
        f"{result['needs_review_count']} 需审核, "
        f"{result['failed_count']} 失败"
    )

    return result
