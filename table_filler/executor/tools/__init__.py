"""Executor 工具集。"""

from .document_loader import load_document
from .page_viewer import get_page_count, view_page
from .batch_viewer import view_all_pages
from .notebook import add_note, read_notes, clear_notes

__all__ = [
    "load_document",
    "get_page_count",
    "view_page",
    "view_all_pages",
    "add_note",
    "read_notes",
    "clear_notes",
]
