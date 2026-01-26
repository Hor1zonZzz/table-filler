# Data Models & Schemas

Generated: 2026-01-23 09:45:43

## Schema Tools

### vl_agent.tools.data_tool_factory

Path: `vl_agent\tools\data_tool_factory.py`

Functions: create_data_append_tool

### vl_agent.tools.data_tools

Path: `vl_agent\tools\data_tools.py`

Functions: data_list

### vl_agent.tools.schema_tools

Path: `vl_agent\tools\schema_tools.py`

Functions: schema_add_field, schema_remove_field, schema_update_field, schema_list, schema_confirm, schema_reset

## Data Processing Flow

1. **Input**: PDF/Image documents
2. **Preprocessing**: Document classification and routing (preprocess module)
3. **Extraction**: Vision-language model extracts structured data
4. **Output**: JSON results and Excel files

## Key Data Formats

- Contract data schema (see docs/design.md)
- Classification results (JSON)
- Extracted data (Excel/XLSX)