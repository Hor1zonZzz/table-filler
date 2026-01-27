"""Service registration for ADK web (agents_dir level).

ADK requires services.py to be at the agents_dir level.
This file imports from doc_assistant to trigger service registration.
"""

# Import to trigger SqliteMemoryService registration
from doc_assistant.services import *  # noqa: F401, F403
