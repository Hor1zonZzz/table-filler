"""Processing pipeline using SequentialAgent for Executor -> Checker flow."""

from google.adk.agents import SequentialAgent

from processing.executor.agent import executor_agent
from processing.checker.agent import checker_agent

# SequentialAgent ensures deterministic order:
# 1. executor_agent runs first, views PDF pages directly, extracts fields to temp:filled_record
# 2. checker_agent runs second, views pages to verify extraction, saves to temp:verification_result
#
# Both agents are VL-capable and share the same InvocationContext:
# - temp:pdf_images - List of base64-encoded page images
# - temp:notebook - Notes recorded during extraction
# - temp:viewed_pages - Pages already viewed
# - form_config - Field configuration (from session state)
#
# No OCR is performed - agents view images directly like a human would.

processing_pipeline = SequentialAgent(
    name="processing_pipeline",
    description="Processes a single PDF document: VL agent views pages, extracts fields, then verifies results",
    sub_agents=[executor_agent, checker_agent],
)
