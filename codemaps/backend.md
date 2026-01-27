# Backend Architecture

Generated: 2026-01-26 14:30:00

## VL Agent Module

Vision-Language agent for document table extraction using Google ADK.

### Core Components

#### vl_agent.agent

Path: `vl_agent\agent.py`

- LlmAgent definition with DeepSeek model
- Tool registration and sub-agent configuration

#### vl_agent.main

Path: `vl_agent\main.py`

- CLI entry point for interactive agent sessions
- Runner initialization and session management

#### vl_agent.config

Path: `vl_agent\config.py`

Classes:
- **StorageType** (Enum): MEMORY, SQLITE, POSTGRESQL
- **Config**: Storage configuration with environment variables

#### vl_agent.services

Path: `vl_agent\services.py`

Functions: create_session_service

#### vl_agent.callbacks

Path: `vl_agent\callbacks.py`

Functions:
- before_tool_validator - Validates schema before extraction
- before_model_modifier - Dynamically injects tools based on state

#### vl_agent.tracing

Path: `vl_agent\tracing.py`

- Phoenix instrumentation setup
- Tracing configuration

### Tools Module

#### vl_agent.tools.batch_extractor

Functions: batch_extract_pdfs
- Batch extract structured data from multiple PDFs
- Uses VL model for page processing

#### vl_agent.tools.data_tool_factory

Functions: create_data_append_tool
- Factory for creating dynamic data append tools

#### vl_agent.tools.data_tools

Functions: data_list
- List extracted data rows

#### vl_agent.tools.pdf_loader_batch

Functions: load_pdfs_batch
- Batch PDF loading utilities

#### vl_agent.tools.pdf_renderer

Functions: render_pdf_page, get_pdf_page_count, validate_pdf_path
- PDF to image rendering with DPI adaptation

#### vl_agent.tools.picture_loader

Functions: load_picture
- Image file handling

#### vl_agent.tools.schema_tools

Functions:
- schema_add_field
- schema_remove_field
- schema_update_field
- schema_list
- schema_confirm
- schema_reset

---

## Doc Assistant Module [NEW]

General-purpose document reading and Q&A capability.

### Core Components

#### doc_assistant.agent

Path: `doc_assistant\agent.py`

- LlmAgent with read_document tool
- Document Q&A functionality

#### doc_assistant.main

Path: `doc_assistant\main.py`

- Interactive CLI entry point

#### doc_assistant.config

Path: `doc_assistant\config.py`

Classes:
- **StorageType** (Enum): MEMORY, SQLITE, POSTGRESQL
- **Config**: API keys for DeepSeek/DashScope

#### doc_assistant.services

Path: `doc_assistant\services.py`

Functions: create_session_service

### Tools Module

#### doc_assistant.tools.document_reader

Path: `doc_assistant\tools\document_reader.py`

Functions: read_document
- Core tool for reading PDFs and images
- Uses VL model for document understanding

#### doc_assistant.tools.pdf_utils

Path: `doc_assistant\tools\pdf_utils.py`

Functions: render_page, get_page_count
- PDF utilities for rendering and page handling

---

## Module Dependencies

```
vl_agent
├── google.adk
├── litellm
├── pymupdf
└── openpyxl

doc_assistant
├── google.adk
├── litellm
└── pymupdf

preprocess
├── openai (Batch API)
└── pymupdf
```

## Session Persistence Options

| Type | Backend | Use Case |
|------|---------|----------|
| memory | In-memory | Development, single session |
| sqlite | aiosqlite | Local persistence |
| postgresql | asyncpg | Production deployment |

Environment variables:
- `VL_STORAGE_TYPE` / `DOC_STORAGE_TYPE`
- `VL_DATABASE_URL` / `DOC_DATABASE_URL`
