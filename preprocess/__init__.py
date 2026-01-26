"""PDF preprocessing module for supplier contract classification.

This module provides tools to classify PDFs into supplier contracts
vs. other documents before batch data extraction.

Example usage:
    from preprocess import run_classification

    result = run_classification(
        input_dir="./pdfs",
        max_workers=10,
    )

    print(f"Total: {result['total']}")
    print(f"Qualified: {result['qualified']}")
    print(f"Rejected: {result['rejected']}")
"""

from .classifier import (
    classify_pdfs_batch,
    classify_single_pdf,
    move_to_category,
    query_batch_progress,
    render_all_pages,
    run_classification,
)
from .prompts import CLASSIFY_PROMPT

__all__ = [
    "CLASSIFY_PROMPT",
    "classify_pdfs_batch",
    "classify_single_pdf",
    "move_to_category",
    "query_batch_progress",
    "render_all_pages",
    "run_classification",
]
