# Backend Architecture

Generated: 2026-01-23 09:45:43

## VL Agent Module

Vision-Language agent for document processing using Google ADK.

### Core Components

#### vl_agent.agent

Path: `vl_agent\agent.py`

#### vl_agent.main

Path: `vl_agent\main.py`

#### vl_agent.config

Path: `vl_agent\config.py`

Classes:
- **StorageType**
  - Inherits: Enum
- **Config**

#### vl_agent.services

Path: `vl_agent\services.py`

Functions: create_session_service

#### vl_agent.callbacks

Path: `vl_agent\callbacks.py`

#### vl_agent.tracing

Path: `vl_agent\tracing.py`

### Tools Module

#### vl_agent.tools.__init__


#### vl_agent.tools.batch_extractor


#### vl_agent.tools.data_tool_factory

  Functions: create_data_append_tool

#### vl_agent.tools.data_tools

  Functions: data_list

#### vl_agent.tools.pdf_loader_batch


#### vl_agent.tools.pdf_renderer

  Functions: render_pdf_page, get_pdf_page_count, validate_pdf_path

#### vl_agent.tools.picture_loader


#### vl_agent.tools.schema_tools

  Functions: schema_add_field, schema_remove_field, schema_update_field

### Module Dependencies
