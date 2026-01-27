# Architecture Overview

Generated: 2026-01-26 14:30:00

## Project Structure

Python document processing system using Google ADK for vision-language AI agents.
Extracts structured data from contracts and documents.

## Module Categories

### Vl Agent (7 modules)

- `vl_agent.__init__` - vl_agent\__init__.py (Phoenix tracing init)
- `vl_agent.agent` - vl_agent\agent.py (LlmAgent with DeepSeek)
- `vl_agent.callbacks` - vl_agent\callbacks.py (tool validation, LLM modifiers)
- `vl_agent.config` - vl_agent\config.py (storage config)
- `vl_agent.main` - vl_agent\main.py (CLI entry point)
- `vl_agent.services` - vl_agent\services.py (SessionService factory)
- `vl_agent.tracing` - vl_agent\tracing.py (Phoenix instrumentation)

### Vl Agent.Tools (8 modules)

- `vl_agent.tools.__init__` - vl_agent\tools\__init__.py
- `vl_agent.tools.batch_extractor` - vl_agent\tools\batch_extractor.py (batch PDF extraction)
- `vl_agent.tools.data_tool_factory` - vl_agent\tools\data_tool_factory.py (dynamic tool creation)
- `vl_agent.tools.data_tools` - vl_agent\tools\data_tools.py (data listing)
- `vl_agent.tools.pdf_loader_batch` - vl_agent\tools\pdf_loader_batch.py (batch PDF loading)
- `vl_agent.tools.pdf_renderer` - vl_agent\tools\pdf_renderer.py (PDF to image)
- `vl_agent.tools.picture_loader` - vl_agent\tools\picture_loader.py (image handling)
- `vl_agent.tools.schema_tools` - vl_agent\tools\schema_tools.py (schema CRUD)

### Doc Assistant (5 modules) [NEW]

- `doc_assistant.__init__` - doc_assistant\__init__.py
- `doc_assistant.agent` - doc_assistant\agent.py (document Q&A agent)
- `doc_assistant.config` - doc_assistant\config.py (API keys, storage)
- `doc_assistant.main` - doc_assistant\main.py (CLI entry point)
- `doc_assistant.services` - doc_assistant\services.py (SessionService)

### Doc Assistant.Tools (2 modules) [NEW]

- `doc_assistant.tools.document_reader` - doc_assistant\tools\document_reader.py (VL document reading)
- `doc_assistant.tools.pdf_utils` - doc_assistant\tools\pdf_utils.py (PDF utilities)

### Preprocess (3 modules)

- `preprocess.__init__` - preprocess\__init__.py
- `preprocess.classifier` - preprocess\classifier.py (OpenAI Batch API classification)
- `preprocess.prompts` - preprocess\prompts.py (classification prompts)

### Tests (7 modules) [NEW]

- `tests.doc_assistant.test_agent` - tests\doc_assistant\test_agent.py
- `tests.doc_assistant.test_config` - tests\doc_assistant\test_config.py
- `tests.doc_assistant.test_document_reader` - tests\doc_assistant\test_document_reader.py
- `tests.doc_assistant.test_main` - tests\doc_assistant\test_main.py
- `tests.doc_assistant.test_pdf_utils` - tests\doc_assistant\test_pdf_utils.py
- `tests.doc_assistant.test_services` - tests\doc_assistant\test_services.py

## System Architecture

```
User Input (CLI/API)
        |
        v
+------------------+
|   Google ADK     |  Runner/LlmAgent
|     Runner       |
+--------+---------+
         |
+--------v---------+
| Main Agent       |  DeepSeek Model
| (Orchestration)  |
+--------+---------+
         |
+--------v--------------------------+
|        Tool Layer (Async)         |
|                                   |
| Schema tools  | Data tools        |
| PDF tools     | Classification    |
+-----------------------------------+
```

## Key External Dependencies

- google-adk (>=1.21.0) - Agent framework
- litellm (>=1.80.11) - LLM abstraction
- openai (>=1.0.0) - API client
- pymupdf (>=1.24.0) - PDF processing
- openpyxl (>=3.1.0) - Excel export
- arize-phoenix (>=12.29.0) - Observability

## Entry Points

```bash
# VL Agent
uv run python -m vl_agent.main

# Doc Assistant
uv run python -m doc_assistant.main

# ADK API Server
uv run adk api_server --port 8000 .
```
