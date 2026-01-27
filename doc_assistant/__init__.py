"""Document Assistant - A general-purpose document Q&A assistant.

Usage:
    Run with ADK web interface:
        adk web doc_assistant
"""

from pathlib import Path

from dotenv import load_dotenv


# Load environment variables (prioritize project root .env)
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()

from . import tracing as _tracing  # noqa: F401 - Initialize Phoenix tracing
from . import agent  # Required by ADK for agent discovery

__all__ = ["agent"]
