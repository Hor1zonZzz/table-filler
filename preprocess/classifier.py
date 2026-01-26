"""PDF classification module for supplier contract identification.

This module provides functionality to classify PDFs into supplier contracts
vs. other documents using a vision-language model via OpenAI SDK Batch API.
"""

import base64
import json
import os
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from openai import OpenAI

from vl_agent.tools.pdf_renderer import (
    get_pdf_page_count,
    render_pdf_page,
    validate_pdf_path,
)

from .prompts import CLASSIFY_PROMPT

# DashScope API limit: 10MB per base64 image
MAX_BASE64_BYTES = 10 * 1024 * 1024
# DPI levels to try (from high to low)
DPI_LEVELS = [150, 120, 100, 72, 50]

# Output directories
QUALIFIED_DIR = Path("./data/供应商合同")
REJECTED_DIR = Path("./data/非供应商合同")

# Batch job state file for progress tracking
BATCH_STATE_FILE = Path("./batch_job_state.json")

# Type alias for classification result
type ClassificationResult = dict[str, str | bool | None]


def _get_config() -> tuple[str, str, str]:
    """Get configuration from environment variables at runtime.

    Returns:
        Tuple of (vl_model, api_key, base_url).
    """
    return (
        os.getenv("VL_MODEL", "qwen3-vl-plus"),
        os.getenv("DASHSCOPE_API_KEY", ""),
        os.getenv("DASHSCOPE_BASE_URL", ""),
    )


def _get_client() -> OpenAI:
    """Create OpenAI client with current environment configuration.

    Returns:
        Configured OpenAI client instance.
    """
    _, api_key, base_url = _get_config()
    return OpenAI(api_key=api_key, base_url=base_url)


def _save_batch_state(
    batch_job_id: str,
    path_to_id: dict[str, str],
    total_pdfs: int,
) -> None:
    """Save batch job state for progress tracking.

    Args:
        batch_job_id: The batch job ID from API.
        path_to_id: Mapping of PDF paths to custom IDs.
        total_pdfs: Total number of PDFs in batch.
    """
    state = {
        "batch_job_id": batch_job_id,
        "path_to_id": path_to_id,
        "total_pdfs": total_pdfs,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(BATCH_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _load_batch_state() -> dict | None:
    """Load saved batch job state.

    Returns:
        Batch state dictionary or None if not found.
    """
    if not BATCH_STATE_FILE.exists():
        return None
    with open(BATCH_STATE_FILE, encoding="utf-8") as f:
        return json.load(f)


def query_batch_progress() -> dict:
    """Query the progress of current batch job.

    Returns:
        dict containing:
            - status: Batch job status
            - batch_job_id: The job ID
            - total: Total requests
            - completed: Completed requests
            - failed: Failed requests
            - progress_pct: Progress percentage
            - message: Human readable status message
    """
    state = _load_batch_state()
    if not state:
        return {
            "status": "no_job",
            "message": "没有正在运行的批处理任务",
        }

    batch_job_id = state.get("batch_job_id")
    total_pdfs = state.get("total_pdfs", 0)

    try:
        client = _get_client()
        batch_status = client.batches.retrieve(batch_job_id)

        completed = batch_status.request_counts.completed if batch_status.request_counts else 0
        failed = batch_status.request_counts.failed if batch_status.request_counts else 0
        total = batch_status.request_counts.total if batch_status.request_counts else total_pdfs

        progress_pct = (completed + failed) / total * 100 if total > 0 else 0

        status_messages = {
            "validating": "正在验证批处理文件...",
            "in_progress": f"处理中: {completed}/{total} 完成 ({progress_pct:.1f}%)",
            "finalizing": "正在整理结果...",
            "completed": "批处理完成！",
            "failed": "批处理失败",
            "cancelled": "批处理已取消",
            "expired": "批处理已过期",
        }

        return {
            "status": batch_status.status,
            "batch_job_id": batch_job_id,
            "total": total,
            "completed": completed,
            "failed": failed,
            "progress_pct": progress_pct,
            "message": status_messages.get(batch_status.status, batch_status.status),
            "created_at": state.get("created_at"),
        }

    except Exception as e:
        return {
            "status": "error",
            "batch_job_id": batch_job_id,
            "message": f"查询失败: {e}",
        }


def _render_page_with_size_limit(
    pdf_path: str,
    page_num: int,
    max_bytes: int = MAX_BASE64_BYTES,
) -> tuple[str, int]:
    """Render PDF page with progressive DPI reduction to fit size limit.

    Args:
        pdf_path: Path to PDF file.
        page_num: Page number (0-indexed).
        max_bytes: Maximum base64 size in bytes.

    Returns:
        Tuple of (base64_string, dpi_used).
    """
    image_b64 = ""
    final_dpi = DPI_LEVELS[-1]

    for dpi in DPI_LEVELS:
        image_bytes = render_pdf_page(pdf_path, page_num, dpi=dpi)
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        b64_size = len(image_b64)
        final_dpi = dpi

        if b64_size <= max_bytes:
            return image_b64, dpi

    # Return lowest DPI result even if still too large
    print(f"[DPI] Warning: Page {page_num + 1} still exceeds limit at lowest DPI")
    return image_b64, final_dpi


def render_all_pages(pdf_path: str) -> list[str]:
    """Render all pages of a PDF to base64 images.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of base64-encoded PNG images for each page.

    Raises:
        ValueError: If PDF path is invalid.
        RuntimeError: If PDF rendering fails.
    """
    is_valid, error_msg = validate_pdf_path(pdf_path)
    if not is_valid:
        raise ValueError(error_msg)

    try:
        total_pages = get_pdf_page_count(pdf_path)
        images: list[str] = []

        for page_num in range(total_pages):
            image_b64, _ = _render_page_with_size_limit(pdf_path, page_num)
            images.append(image_b64)

        return images

    except Exception as e:
        raise RuntimeError(f"Failed to render PDF {pdf_path}: {e}") from e


def _parse_classification_response(content: str) -> ClassificationResult:
    """Parse VL model response into classification result.

    Args:
        content: Raw response content from VL model.

    Returns:
        Parsed classification result dictionary.
    """
    content = content.strip()

    # Handle markdown code blocks
    if content.startswith("```"):
        lines = content.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.startswith("```"):
                in_block = not in_block
                continue
            if in_block:
                json_lines.append(line)
        content = "\n".join(json_lines)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "is_two_party_contract": False,
            "reason": f"Failed to parse response: {content[:200]}",
        }


def _compute_qualified(result: ClassificationResult) -> bool:
    """Compute whether a PDF qualifies as a supplier contract.

    Args:
        result: Classification result from VL model.

    Returns:
        True if PDF meets all criteria, False otherwise.
    """
    return (
        result.get("is_two_party_contract", False) is True
        and result.get("party_a_contains_shengteng", False) is True
        and result.get("party_b_is_supplier", False) is True
    )


def classify_single_pdf(
    client: OpenAI,
    pdf_path: str,
    images: list[str],
) -> ClassificationResult:
    """Classify a single PDF using VL model.

    Args:
        client: OpenAI client instance.
        pdf_path: Path to the PDF file.
        images: List of base64-encoded page images.

    Returns:
        Classification result dictionary.
    """
    vl_model, _, _ = _get_config()

    # Build image content for the message
    image_contents = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img}"},
        }
        for img in images
    ]

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": CLASSIFY_PROMPT},
                *image_contents,
            ],
        }
    ]

    try:
        response = client.chat.completions.create(
            model=vl_model,
            messages=messages,
        )

        content = response.choices[0].message.content
        if content is None:
            return {
                "is_two_party_contract": False,
                "reason": "VL model returned empty response",
            }

        result = _parse_classification_response(content)
        result["pdf_path"] = pdf_path
        result["qualified"] = _compute_qualified(result)

        return result

    except Exception as e:
        return {
            "pdf_path": pdf_path,
            "is_two_party_contract": False,
            "reason": f"VL model error: {e}",
            "qualified": False,
        }


def _build_batch_request_line(
    custom_id: str,
    images: list[str],
    vl_model: str,
) -> dict:
    """Build a single batch request line.

    Args:
        custom_id: Unique identifier for this request.
        images: List of base64-encoded page images.
        vl_model: VL model name to use.

    Returns:
        Batch request dictionary for JSONL file.
    """
    image_contents = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img}"},
        }
        for img in images
    ]

    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": vl_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": CLASSIFY_PROMPT},
                        *image_contents,
                    ],
                }
            ],
        },
    }


def classify_pdfs_batch(
    client: OpenAI,
    pdf_images: dict[str, list[str]],
    poll_interval: int = 30,
) -> list[ClassificationResult]:
    """Classify multiple PDFs using OpenAI Batch API.

    Args:
        client: OpenAI client instance.
        pdf_images: Dict mapping pdf_path to list of base64 images.
        poll_interval: Seconds between status checks (default 30).

    Returns:
        List of classification results.
    """
    if not pdf_images:
        return []

    vl_model, _, _ = _get_config()

    # Step 1: Build JSONL batch file
    batch_lines = []
    path_to_id: dict[str, str] = {}

    for i, (pdf_path, images) in enumerate(pdf_images.items()):
        custom_id = f"pdf_{i}"
        path_to_id[pdf_path] = custom_id
        line = _build_batch_request_line(custom_id, images, vl_model)
        batch_lines.append(json.dumps(line, ensure_ascii=False))

    jsonl_content = "\n".join(batch_lines)

    # Step 2: Upload batch file
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".jsonl",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(jsonl_content)
        batch_file_path = f.name

    try:
        with open(batch_file_path, "rb") as f:
            batch_file = client.files.create(file=f, purpose="batch")

        print(f"[Batch] Uploaded batch file: {batch_file.id}")

        # Step 3: Create batch job
        batch_job = client.batches.create(
            input_file_id=batch_file.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
        )

        print(f"[Batch] Created batch job: {batch_job.id}")

        # Save batch state for progress tracking
        _save_batch_state(batch_job.id, path_to_id, len(pdf_images))

        # Step 4: Poll for completion
        while True:
            batch_status = client.batches.retrieve(batch_job.id)
            status = batch_status.status

            # Print detailed progress
            if batch_status.request_counts:
                completed = batch_status.request_counts.completed
                failed = batch_status.request_counts.failed
                total = batch_status.request_counts.total
                progress_pct = (completed + failed) / total * 100 if total > 0 else 0
                print(f"[Batch] Status: {status} | Progress: {completed}/{total} ({progress_pct:.1f}%)")
            else:
                print(f"[Batch] Status: {status}")

            if status == "completed":
                break
            elif status in ("failed", "cancelled", "expired"):
                print(f"[Batch] Job {status}: {batch_status.errors}")
                return [
                    {
                        "pdf_path": path,
                        "is_two_party_contract": False,
                        "reason": f"Batch job {status}",
                        "qualified": False,
                    }
                    for path in pdf_images.keys()
                ]

            time.sleep(poll_interval)

        # Step 5: Download and parse results
        output_file_id = batch_status.output_file_id
        if not output_file_id:
            return [
                {
                    "pdf_path": path,
                    "is_two_party_contract": False,
                    "reason": "No output file from batch",
                    "qualified": False,
                }
                for path in pdf_images.keys()
            ]

        output_content = client.files.content(output_file_id)
        output_lines = output_content.text.strip().split("\n")

        # Map results back to paths
        id_to_path = {v: k for k, v in path_to_id.items()}
        results: list[ClassificationResult] = []

        for line in output_lines:
            if not line.strip():
                continue

            try:
                response_data = json.loads(line)
                custom_id = response_data.get("custom_id", "")
                pdf_path = id_to_path.get(custom_id, "")

                # Extract response content
                response_body = response_data.get("response", {}).get("body", {})
                choices = response_body.get("choices", [])

                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    result = _parse_classification_response(content)
                else:
                    result = {
                        "is_two_party_contract": False,
                        "reason": "No choices in batch response",
                    }

                result["pdf_path"] = pdf_path
                result["qualified"] = _compute_qualified(result)
                results.append(result)

            except json.JSONDecodeError as e:
                print(f"[Batch] Failed to parse result line: {e}")

        return results

    finally:
        # Clean up temp file
        Path(batch_file_path).unlink(missing_ok=True)


def move_to_category(
    pdf_path: str,
    qualified: bool,
    qualified_dir: Path = QUALIFIED_DIR,
    rejected_dir: Path = REJECTED_DIR,
) -> str:
    """Move PDF to appropriate category directory.

    Args:
        pdf_path: Source path of the PDF.
        qualified: Whether the PDF is qualified as supplier contract.
        qualified_dir: Directory for qualified PDFs.
        rejected_dir: Directory for rejected PDFs.

    Returns:
        Destination path of the moved file.
    """
    src_path = Path(pdf_path)
    dest_dir = qualified_dir if qualified else rejected_dir

    # Ensure destination directory exists
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Handle filename conflicts
    dest_path = dest_dir / src_path.name
    counter = 1

    while dest_path.exists():
        stem = src_path.stem
        suffix = src_path.suffix
        dest_path = dest_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    shutil.copy2(src_path, dest_path)
    return str(dest_path)


def run_classification(
    input_dir: str,
    max_workers: int = 10,
    use_batch_api: bool = True,
    qualified_dir: str | None = None,
    rejected_dir: str | None = None,
) -> dict:
    """Run PDF classification pipeline.

    This is the main entry point for the classification process. It:
    1. Scans the input directory for PDFs
    2. Renders all pages using thread pool
    3. Classifies PDFs using VL model (Batch API or individual requests)
    4. Moves PDFs to appropriate directories
    5. Saves classification results to JSON

    Args:
        input_dir: Directory containing PDFs to classify.
        max_workers: Maximum number of worker threads (default 10).
        use_batch_api: Whether to use Batch API (default True).
        qualified_dir: Custom directory for qualified PDFs.
        rejected_dir: Custom directory for rejected PDFs.

    Returns:
        dict containing:
            - total: Total number of PDFs processed
            - qualified: Number of qualified supplier contracts
            - rejected: Number of rejected documents
            - output_file: Path to classification results JSON
            - errors: List of any errors encountered
    """
    # Set up directories
    q_dir = Path(qualified_dir) if qualified_dir else QUALIFIED_DIR
    r_dir = Path(rejected_dir) if rejected_dir else REJECTED_DIR
    q_dir.mkdir(parents=True, exist_ok=True)
    r_dir.mkdir(parents=True, exist_ok=True)

    # Scan for PDFs
    input_path = Path(input_dir)
    pdf_paths = list(input_path.glob("**/*.pdf"))

    if not pdf_paths:
        return {
            "total": 0,
            "qualified": 0,
            "rejected": 0,
            "output_file": None,
            "errors": ["No PDF files found in input directory"],
        }

    print(f"[Classify] Found {len(pdf_paths)} PDF files")

    # Initialize OpenAI client
    client = _get_client()

    # Step 1: Render all PDFs using thread pool
    print("[Classify] Rendering PDF pages...")
    pdf_images: dict[str, list[str]] = {}
    render_errors: list[str] = []

    def render_pdf(pdf_path: Path) -> tuple[str, list[str] | None, str | None]:
        path_str = str(pdf_path)
        try:
            images = render_all_pages(path_str)
            return path_str, images, None
        except Exception as e:
            return path_str, None, str(e)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(render_pdf, p) for p in pdf_paths]

        for future in futures:
            path_str, images, error = future.result()
            if error:
                render_errors.append(f"{path_str}: {error}")
                print(f"[Render] Error: {path_str} - {error}")
            elif images:
                pdf_images[path_str] = images
                print(f"[Render] OK: {path_str} ({len(images)} pages)")

    print(f"[Classify] Rendered {len(pdf_images)} PDFs successfully")

    # Step 2: Classify PDFs
    print("[Classify] Classifying PDFs...")
    results: list[ClassificationResult] = []

    if use_batch_api:
        results = classify_pdfs_batch(client, pdf_images)
    else:
        # Concurrent individual classification
        completed = 0
        total = len(pdf_images)

        def classify_one(item: tuple[str, list[str]]) -> ClassificationResult:
            nonlocal completed
            pdf_path, images = item
            result = classify_single_pdf(client, pdf_path, images)
            completed += 1
            status = "✓" if result.get("qualified") else "✗"
            print(f"[Classify] [{completed}/{total}] {status} {Path(pdf_path).name}")
            return result

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(classify_one, pdf_images.items()))

    # Step 3: Move files using thread pool
    print("[Classify] Moving files to categories...")

    def move_file(result: ClassificationResult) -> ClassificationResult:
        pdf_path = result.get("pdf_path", "")
        qualified = result.get("qualified", False)

        if pdf_path and Path(pdf_path).exists():
            dest_path = move_to_category(pdf_path, qualified, q_dir, r_dir)
            result["dest_path"] = dest_path
            print(f"[Move] {pdf_path} -> {dest_path}")

        return result

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(move_file, results))

    # Step 4: Save results to JSON
    output_file = "./classification_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Compute statistics
    qualified_count = sum(1 for r in results if r.get("qualified"))
    rejected_count = len(results) - qualified_count

    # Print summary
    print("\n" + "=" * 60)
    print("[Classification Summary]")
    print(f"  Total PDFs: {len(pdf_paths)}")
    print(f"  Rendered successfully: {len(pdf_images)}")
    print(f"  Render errors: {len(render_errors)}")
    print(f"  Qualified (供应商合同): {qualified_count}")
    print(f"  Rejected (非供应商合同): {rejected_count}")
    print(f"  Results saved to: {output_file}")
    print("=" * 60 + "\n")

    return {
        "total": len(pdf_paths),
        "qualified": qualified_count,
        "rejected": rejected_count,
        "output_file": output_file,
        "errors": render_errors if render_errors else None,
    }
