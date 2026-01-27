# Preprocessing Module

Generated: 2026-01-26 14:30:00

## Purpose

Document classification and preprocessing before VL agent processing.
Uses OpenAI Batch API for efficient multi-document classification.

### preprocess.__init__

Path: `preprocess\__init__.py`

Exports: classify_pdfs_batch, classify_single_pdf, run_classification

### preprocess.classifier

Path: `preprocess\classifier.py`

#### Configuration Functions
- `_get_config` - Load API configuration
- `_get_client` - Create OpenAI client

#### State Management
- `_save_batch_state` - Persist batch job state
- `_load_batch_state` - Load batch job state
- `query_batch_progress` - Check batch job status

#### PDF Processing
- `_render_page_with_size_limit` - Render page with size constraints
- `render_all_pages` - Render all pages of a PDF

#### Classification
- `_parse_classification_response` - Parse API response
- `_compute_qualified` - Determine qualification status
- `classify_single_pdf` - Classify a single PDF
- `_build_batch_request_line` - Build batch API request
- `classify_pdfs_batch` - Batch classify multiple PDFs

#### File Organization
- `move_to_category` - Move file to category folder
- `run_classification` - End-to-end classification workflow

### preprocess.prompts

Path: `preprocess\prompts.py`

Classification prompts for determining document types:
- Supplier contract detection
- Document categorization criteria

## Classification Workflow

```
1. Input: Directory of PDF files

2. Render Phase
   └─> Convert PDF pages to images
   └─> Apply size limits

3. Classification Phase (Batch API)
   └─> Build batch requests
   └─> Submit to OpenAI Batch API
   └─> Poll for completion
   └─> Parse results

4. Organization Phase
   └─> Move files to category folders
   └─> Generate classification report
```

## Batch Processing

Uses OpenAI Batch API for cost-effective processing:
- 50% lower cost than real-time API
- Processes up to 50,000 requests per batch
- 24-hour completion window

### Batch State Structure

```json
{
  "batch_id": "batch_abc123",
  "status": "in_progress|completed|failed",
  "created_at": "2026-01-26T10:00:00Z",
  "file_mappings": {
    "request_id_1": "path/to/file1.pdf",
    "request_id_2": "path/to/file2.pdf"
  }
}
```

## Integration with VL Agent

```
preprocess.classifier
        |
        v
   [Qualified PDFs]
        |
        v
   vl_agent.tools.batch_extractor
        |
        v
   [Structured Data Output]
```
