# Data Models & Schemas

Generated: 2026-01-26 14:30:00

## VL Agent Schema Tools

### vl_agent.tools.data_tool_factory

Path: `vl_agent\tools\data_tool_factory.py`

Functions: create_data_append_tool
- Dynamically creates data append tools based on confirmed schema

### vl_agent.tools.data_tools

Path: `vl_agent\tools\data_tools.py`

Functions: data_list
- Lists all extracted data rows from state

### vl_agent.tools.schema_tools

Path: `vl_agent\tools\schema_tools.py`

Functions:
- schema_add_field - Add field to schema
- schema_remove_field - Remove field from schema
- schema_update_field - Update field definition
- schema_list - List current schema fields
- schema_confirm - Confirm schema for extraction
- schema_reset - Reset schema to empty

## State Management

State stored in `tool_context.state` dictionary:

| Key | Type | Description |
|-----|------|-------------|
| schema_fields | JSON array | Field definitions |
| schema_confirmed | "true"/"false" | Schema confirmation flag |
| extracted_rows | JSON array | Extracted data rows |

### Schema Field Structure

```json
{
  "name": "string",
  "type": "string|number|boolean",
  "description": "Field description"
}
```

### Extracted Row Structure

```json
{
  "source_file": "path/to/file.pdf",
  "page": 1,
  "data": {
    "field1": "value1",
    "field2": "value2"
  }
}
```

## Data Processing Flow

```
1. Define Schema Phase
   └─> Add fields (schema_add_field)
   └─> List fields (schema_list)
   └─> Confirm schema (schema_confirm)

2. Extract Data Phase
   └─> Load PDFs (batch_extract_pdfs)
   └─> VL model processes pages
   └─> Extract to schema
   └─> Save to extracted_rows

3. Export Phase
   └─> Excel export (XLSX)
   └─> JSON output
```

## Doc Assistant Data Flow [NEW]

```
1. Document Loading
   └─> PDF/Image input
   └─> Render pages to images

2. Document Understanding
   └─> VL model analyzes content
   └─> Extract text and structure

3. Q&A Response
   └─> Answer user questions
   └─> Reference specific content
```

## Key Data Formats

### Input Formats
- PDF documents (.pdf)
- Image files (.png, .jpg, .jpeg)

### Output Formats
- JSON (extracted data, classification results)
- Excel/XLSX (structured data export)

### Classification Result

```json
{
  "file_path": "path/to/file.pdf",
  "is_supplier_contract": true,
  "confidence": 0.95,
  "reason": "Contains supplier terms and conditions"
}
```
