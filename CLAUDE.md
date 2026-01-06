# CLAUDE.md

## Project Overview

A multi-agent system built with **Google ADK (Agent Development Kit)** for automated contract digitization. VL (Vision-Language) models view PDF pages directly like a human and extract form fields. No OCR required.

**Key Features:**
- VL model directly views PDF pages (no OCR intermediate step)
- Parallel PDF processing with concurrency control
- Anti-hallucination verification by checker agent
- Notebook system for multi-page information tracking
- Configurable form fields via conversation
- Excel export with multiple sheets

## Commands

```bash
# Run the agent (using ADK CLI)
adk run orchestrator

# Or run directly
python main.py

# Install dependencies
uv sync

# Lint and format
ruff check .
ruff format .

# Type checking
basedpyright
```

## Architecture

### Overview

```
conversation_agent (LlmAgent)
    │
    ├── tools: [set_form_config, batch_process_pdfs, export_to_excel]
    │
    └── batch_process_pdfs internally calls:
            │
            └── processing_pipeline (SequentialAgent)
                    │
                    ├── executor_agent → views pages, extracts fields
                    └── checker_agent → views pages, verifies results
```

**Key Design**:
- Uses `tools` instead of `sub_agents` so users always interact with the top-level agent
- VL agents view PDF images directly (no OCR conversion)
- Notebook tools help agents record information across multiple pages

### Directory Structure

```
table-filler/
├── main.py                     # Entry point
├── orchestrator/               # Top-level conversation agent
│   ├── agent.py                # conversation_agent with tools
│   └── tools/
│       ├── batch_processor.py  # Parallel processing + retry
│       ├── config_manager.py   # Form field configuration
│       ├── excel_exporter.py   # Excel export
│       └── pdf_to_images.py    # PDF to base64 images (no OCR)
│
├── processing/                 # Processing pipeline
│   ├── agent.py                # SequentialAgent [executor → checker]
│   ├── shared_tools/           # Tools shared by executor and checker
│   │   ├── page_viewer.py      # view_page(), get_page_count()
│   │   └── notebook.py         # add_note(), read_notes(), clear_notes()
│   ├── executor/
│   │   └── agent.py            # VL extraction agent
│   └── checker/
│       └── agent.py            # VL verification agent
│
└── shared/
    └── models.py               # Pydantic data models
```

### VL Model Approach

Unlike traditional OCR-based extraction, this system:

1. **Converts PDF to images** - `pdf_to_images()` creates base64 PNG images
2. **VL agent views pages** - Executor calls `view_page(1)` to see page 1
3. **Records findings** - Uses `add_note("contract_id: ABC-123", "field")` to remember
4. **Compiles result** - After viewing all pages, reads notes and outputs JSON
5. **Checker verifies** - Also views pages to confirm extracted values exist

**Why no OCR?**
- VL models understand document layout, tables, and handwriting directly
- OCR adds latency and potential errors
- Images preserve visual context that OCR loses

### Agent Pattern

**Top-level agent with tools (NOT sub_agents):**
```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

model = LiteLlm(model="openai/deepseek-chat")
root_agent = LlmAgent(
    model=model,
    name="conversation_agent",
    instruction="...",
    tools=[set_form_config, batch_process_pdfs, export_to_excel],
    # NOTE: No sub_agents - use tools to keep control
)
```

**VL executor agent with page viewing:**
```python
executor_agent = LlmAgent(
    model=LiteLlm(model="openai/gpt-4o"),  # VL-capable model
    name="executor_agent",
    tools=[get_page_count, view_page, add_note, read_notes, clear_notes],
    output_key="temp:filled_record",
)
```

**Processing pipeline with SequentialAgent:**
```python
from google.adk.agents import SequentialAgent

processing_pipeline = SequentialAgent(
    name="processing_pipeline",
    sub_agents=[executor_agent, checker_agent],  # Forced order
)
```

### Data Flow

```
User: "Extract these fields: contract_id, party_a, amount..."
    ↓
conversation_agent → set_form_config() → state['form_config']
    ↓
User: "Process these PDFs: /path/to/*.pdf"
    ↓
conversation_agent → batch_process_pdfs()
    ↓
    ├── PDF 1 ──┐
    ├── PDF 2 ──┼── Parallel (semaphore=10)
    └── PDF N ──┘
         │
         ↓ Each PDF
    pdf_to_images() → base64 images stored in state
         │
         ↓
    processing_pipeline (SequentialAgent)
         │
         ├── executor_agent
         │     ├── get_page_count() → "5 pages"
         │     ├── view_page(1) → sees page 1
         │     ├── add_note("contract_id: ABC-123", "field")
         │     ├── view_page(2) → sees page 2
         │     └── ... outputs final JSON
         │
         └── checker_agent
               ├── view_page(1) → verifies values exist
               └── ... outputs verification result
         │
         ↓
    Results aggregated → state['temp:batch_results']
    ↓
conversation_agent: "Processed N PDFs: X successful, Y needs review, Z failed"
    ↓
User: "Export to Excel"
    ↓
conversation_agent → export_to_excel() → Excel file
```

### Environment Variables

Required in `.env` files:
- `OPENAI_API_KEY` - API key for VL model endpoint
- `OPENAI_BASE_URL` - Base URL for the API endpoint

## Key Implementation Details

### Why tools instead of sub_agents?

| Feature | sub_agents (transfer) | tools |
|---------|----------------------|-------|
| Control | Transfers to sub-agent | Stays with parent |
| User interaction | With sub-agent | Always with parent |
| Result return | Manual transfer back | Automatic |

### Concurrency Control

```python
semaphore = asyncio.Semaphore(10)  # Max 10 concurrent PDFs
async with semaphore:
    result = await process_single_pdf(...)
```

### Retry Mechanism

```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
async def process_single_pdf(...):
    ...
```

### State Management

| Key | Scope | Purpose |
|-----|-------|---------|
| `form_config` | Session | Form field configuration |
| `temp:pdf_images` | Invocation | Base64 images of current PDF |
| `temp:notebook` | Invocation | Notes recorded during extraction |
| `temp:viewed_pages` | Invocation | Pages already viewed |
| `temp:filled_record` | Invocation | Extraction result |
| `temp:verification_result` | Invocation | Verification result |
| `temp:batch_results` | Invocation | All results for export |

### Page Viewing Tools

```python
# Check total pages
get_page_count() → {"total_pages": 5}

# View a specific page (1-indexed)
view_page(1) → Image content for VL model

# Record information found
add_note("contract_id: ABC-123", "field")
add_note("Signature on page 3", "location")

# Recall recorded notes
read_notes(None)      # All notes
read_notes("field")   # Only field notes
```

## Google ADK Reference

- Docs: https://google.github.io/adk-docs/llms.txt
- SequentialAgent for deterministic ordering
- Tools are Python functions with docstrings (ADK auto-generates schemas)
- Use `output_key` to auto-save agent output to state
