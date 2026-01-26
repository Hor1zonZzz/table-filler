# Architecture Overview

Generated: 2026-01-23 09:45:43

## Project Structure

This is a document processing system using Google ADK for vision-language AI agents.
The system extracts structured data from contracts and other documents.

## Module Categories

### Vl Agent (7 modules)

- `vl_agent.__init__` - vl_agent\__init__.py
- `vl_agent.agent` - vl_agent\agent.py
- `vl_agent.callbacks` - vl_agent\callbacks.py
- `vl_agent.config` - vl_agent\config.py
- `vl_agent.main` - vl_agent\main.py
- `vl_agent.services` - vl_agent\services.py
- `vl_agent.tracing` - vl_agent\tracing.py

### Vl Agent.Tools (8 modules)

- `vl_agent.tools.__init__` - vl_agent\tools\__init__.py
- `vl_agent.tools.batch_extractor` - vl_agent\tools\batch_extractor.py
- `vl_agent.tools.data_tool_factory` - vl_agent\tools\data_tool_factory.py
- `vl_agent.tools.data_tools` - vl_agent\tools\data_tools.py
- `vl_agent.tools.pdf_loader_batch` - vl_agent\tools\pdf_loader_batch.py
- `vl_agent.tools.pdf_renderer` - vl_agent\tools\pdf_renderer.py
- `vl_agent.tools.picture_loader` - vl_agent\tools\picture_loader.py
- `vl_agent.tools.schema_tools` - vl_agent\tools\schema_tools.py

### Preprocess (3 modules)

- `preprocess.__init__` - preprocess\__init__.py
- `preprocess.classifier` - preprocess\classifier.py
- `preprocess.prompts` - preprocess\prompts.py

### Tests (1 modules)

- `testpreprocess` - testpreprocess.py

### Other (1 modules)

- `analyze_codemap` - analyze_codemap.py

## Key External Dependencies

- agent
- ast
- asyncio
- base64
- batch_extractor
- callbacks
- classifier
- collections
- config
- data_tool_factory
- data_tools
- datetime
- dotenv
- enum
- fitz