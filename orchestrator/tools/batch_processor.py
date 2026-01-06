"""Batch PDF processing with parallel execution and retry mechanism."""

import asyncio
import json
from pathlib import Path
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from tenacity import retry, stop_after_attempt, wait_exponential

from orchestrator.tools.pdf_to_images import pdf_to_images
from processing.agent import processing_pipeline
from shared.models import ProcessingStatus

# Concurrency control
MAX_CONCURRENT_PDFS = 10


async def _process_single_pdf_internal(
    pdf_path: str,
    form_config: list[dict[str, Any]],
    session_service: InMemorySessionService,
    app_name: str,
) -> dict[str, Any]:
    """
    Process a single PDF through the entire pipeline.

    Steps:
    1. Convert PDF to images (no OCR - VL model will view directly)
    2. Run processing_pipeline (Executor views pages -> Checker verifies)
    3. Return aggregated result
    """
    result = {
        "pdf_path": pdf_path,
        "status": ProcessingStatus.FAIL.value,
        "confidence": 0.0,
        "final_record": {},
        "issues": [],
        "error": None,
    }

    # Step 1: Validate PDF exists
    if not Path(pdf_path).exists():
        result["error"] = f"PDF file not found: {pdf_path}"
        return result

    # Step 2: Convert PDF to images (NO OCR - just images)
    try:
        images_result = pdf_to_images(pdf_path)
        if images_result.get("status") == "error":
            result["error"] = f"PDF conversion failed: {images_result.get('error', 'Unknown error')}"
            return result

        pdf_images = images_result.get("images", [])
        if not pdf_images:
            result["error"] = "PDF has no pages"
            return result

    except Exception as e:
        result["error"] = f"PDF processing exception: {str(e)}"
        return result

    # Step 3: Create a session for this PDF processing
    try:
        session = await session_service.create_session(
            app_name=app_name,
            user_id="batch_processor",
        )

        # Set up state for the processing pipeline
        # The VL agents will use view_page() to access these images
        session.state["temp:pdf_images"] = pdf_images
        session.state["temp:current_pdf"] = pdf_path
        session.state["temp:notebook"] = []
        session.state["temp:viewed_pages"] = []
        session.state["form_config"] = form_config

        # Step 4: Run the processing pipeline
        runner = Runner(
            agent=processing_pipeline,
            app_name=app_name,
            session_service=session_service,
        )

        # Run the pipeline - executor will view pages and extract, checker will verify
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=f"Extract form fields from the PDF at {pdf_path}. Use view_page() to see the document pages. Form fields to extract are in form_config.",
        ):
            # We collect events but mainly care about final state
            pass

        # Step 5: Collect results from session state
        filled_record = session.state.get("temp:filled_record", {})
        verification_result = session.state.get("temp:verification_result", {})

        # Parse results if they're strings
        if isinstance(filled_record, str):
            try:
                filled_record = json.loads(filled_record)
            except json.JSONDecodeError:
                filled_record = {"raw": filled_record}

        if isinstance(verification_result, str):
            try:
                verification_result = json.loads(verification_result)
            except json.JSONDecodeError:
                verification_result = {"status": "NEEDS_REVIEW", "raw": verification_result}

        # Build final result
        result["status"] = verification_result.get("status", ProcessingStatus.NEEDS_REVIEW.value)
        result["confidence"] = verification_result.get("confidence", 0.0)
        result["issues"] = verification_result.get("issues", [])

        # Use corrected record if available, otherwise use filled record
        corrected = verification_result.get("corrected_record", {})
        if corrected:
            fields = filled_record.get("fields", filled_record)
            if isinstance(fields, dict):
                fields.update(corrected)
            result["final_record"] = fields
        else:
            result["final_record"] = filled_record.get("fields", filled_record)

    except Exception as e:
        result["error"] = f"Processing exception: {str(e)}"

    return result


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
async def _process_with_retry(
    pdf_path: str,
    form_config: list[dict[str, Any]],
    session_service: InMemorySessionService,
    app_name: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    """Process a single PDF with retry logic and concurrency control."""
    async with semaphore:
        return await _process_single_pdf_internal(
            pdf_path, form_config, session_service, app_name
        )


async def batch_process_pdfs_async(
    pdf_paths: list[str],
    form_config: list[dict[str, Any]],
    max_concurrent: int = MAX_CONCURRENT_PDFS,
) -> dict[str, Any]:
    """
    Process multiple PDFs in parallel with concurrency control and retry.

    Args:
        pdf_paths: List of PDF file paths to process
        form_config: Form field configuration
        max_concurrent: Maximum concurrent PDF processing (default: 10)

    Returns:
        Batch processing results with success/failure counts
    """
    if not pdf_paths:
        return {
            "status": "error",
            "error": "No PDF paths provided",
        }

    if not form_config:
        return {
            "status": "error",
            "error": "No form configuration. Use set_form_config first.",
        }

    # Create session service for batch processing
    session_service = InMemorySessionService()
    app_name = "table_filler_batch"

    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_concurrent)

    # Create tasks for all PDFs
    tasks = [
        _process_with_retry(
            pdf_path, form_config, session_service, app_name, semaphore
        )
        for pdf_path in pdf_paths
    ]

    # Execute all tasks with error handling
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Aggregate results
    successful = []
    needs_review = []
    failed = []

    for i, result in enumerate(results):
        pdf_path = pdf_paths[i]

        if isinstance(result, Exception):
            failed.append({
                "pdf_path": pdf_path,
                "status": ProcessingStatus.FAIL.value,
                "error": str(result),
                "final_record": {},
                "issues": [],
                "confidence": 0.0,
            })
        elif result.get("error"):
            failed.append(result)
        elif result.get("status") == ProcessingStatus.PASS.value:
            successful.append(result)
        elif result.get("status") == ProcessingStatus.FAIL.value:
            failed.append(result)
        else:
            needs_review.append(result)

    return {
        "status": "success",
        "total_count": len(pdf_paths),
        "successful_count": len(successful),
        "needs_review_count": len(needs_review),
        "failed_count": len(failed),
        "successful": successful,
        "needs_review": needs_review,
        "failed": failed,
    }


def batch_process_pdfs(
    pdf_paths: list[str],
    tool_context: Any,
) -> dict[str, Any]:
    """
    Process multiple PDFs in parallel with VL model extraction.

    The VL model views PDF pages directly (no OCR), extracts form fields,
    and verifies the results. Failed PDFs are automatically retried up to 3 times.

    Args:
        pdf_paths: List of PDF file paths to process
        tool_context: ADK tool context for state access

    Returns:
        Processing results including:
        - total_count: Total PDFs processed
        - successful_count: Successfully processed PDFs
        - needs_review_count: PDFs needing human review
        - failed_count: Failed PDFs
        - successful/needs_review/failed: Detailed results lists

    Example:
        batch_process_pdfs([
            "/path/to/contract1.pdf",
            "/path/to/contract2.pdf",
            ...
        ])
    """
    # Get form configuration from session state
    form_config = tool_context.state.get("form_config")
    if not form_config:
        return {
            "status": "error",
            "error": "Form configuration not set. Use set_form_config first.",
        }

    # Validate PDF paths
    valid_paths = []
    invalid_paths = []
    for path in pdf_paths:
        if Path(path).exists():
            valid_paths.append(path)
        else:
            invalid_paths.append(path)

    if invalid_paths:
        print(f"Warning: {len(invalid_paths)} PDF files not found: {invalid_paths[:5]}...")

    if not valid_paths:
        return {
            "status": "error",
            "error": "No valid PDF files found",
            "invalid_paths": invalid_paths,
        }

    # Run async batch processing
    try:
        result = asyncio.run(
            batch_process_pdfs_async(valid_paths, form_config)
        )

        # Store results in state for export
        tool_context.state["temp:batch_results"] = result

        # Add summary message
        result["message"] = (
            f"Processed {result['total_count']} PDFs: "
            f"{result['successful_count']} successful, "
            f"{result['needs_review_count']} needs review, "
            f"{result['failed_count']} failed"
        )

        return result

    except Exception as e:
        return {
            "status": "error",
            "error": f"Batch processing failed: {str(e)}",
        }
