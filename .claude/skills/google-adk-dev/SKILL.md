---
name: google-adk-dev
description: "Google Agent Development Kit (ADK) Python development skill. Use when building, developing, or debugging ADK agents, multi-agent systems, tools, callbacks, MCP integrations, or when needing ADK Python API references, tutorials, and best practices. Triggers include creating ADK agents, implementing tools, setting up multi-agent workflows (Sequential/Parallel/Loop), MCP toolset integration, agent deployment, ADK debugging, or any Google ADK Python development task."
---

# Google ADK Development Skill

Build AI agents using Google's Agent Development Kit (ADK) - an open-source, code-first Python framework for sophisticated multi-agent systems.

## Key Resources

| Resource | URL | Purpose |
|----------|-----|---------|
| **Official Docs** | https://google.github.io/adk-docs/ | Primary documentation |
| **Python API Reference** | https://google.github.io/adk-docs/api-reference/python/ | Detailed API docs |
| **GitHub Source** | https://github.com/google/adk-python | Source code, issues, examples |
| **LLM Context Files** | `llms.txt` and `llms-full.txt` in repo root | For vibe coding context |
| **Google Cloud Docs** | https://docs.cloud.google.com/agent-builder/agent-development-kit/overview | Vertex AI integration |

## Quick Start

```bash
# Install
pip install google-adk

# Create project
adk create my_agent

# Run locally
adk run my_agent    # CLI mode
adk web             # Web UI at http://localhost:8000
```

## Core Concepts

### Agent Types

1. **LlmAgent** - Uses LLM for reasoning and decision-making
2. **Workflow Agents** - Deterministic orchestration:
   - `SequentialAgent` - Execute sub-agents in order
   - `ParallelAgent` - Execute sub-agents concurrently  
   - `LoopAgent` - Repeat until condition met
3. **Custom Agents** - Inherit from `BaseAgent` for custom logic

### Basic Agent Structure

```python
from google.adk.agents import Agent

def my_tool(param: str) -> dict:
    """Tool docstring becomes the description for the LLM."""
    return {"status": "success", "result": param}

root_agent = Agent(
    model='gemini-2.0-flash',
    name='my_agent',
    instruction='You are a helpful assistant.',
    tools=[my_tool]
)
```

## Reference Documentation

For detailed guidance, read the appropriate reference file:

- **Multi-agent systems & workflows**: See [references/multi-agent.md](references/multi-agent.md)
- **Tools & MCP integration**: See [references/tools-mcp.md](references/tools-mcp.md)  
- **Callbacks & patterns**: See [references/callbacks.md](references/callbacks.md)
- **API quick reference**: See [references/api-quick-ref.md](references/api-quick-ref.md)

## Development Workflow

1. **Fetch latest docs** - Search/fetch from official sources for current APIs
2. **Check GitHub** - For source code understanding and recent changes
3. **Use llms.txt** - Fetch `https://raw.githubusercontent.com/google/adk-python/main/llms.txt` for LLM context
4. **Test iteratively** - Use `adk web` for interactive debugging

## Common Patterns

### Environment Setup

```python
# .env file
GOOGLE_GENAI_API_KEY=your_api_key  # For Google AI Studio
# OR for Vertex AI:
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your_project_id
GOOGLE_CLOUD_LOCATION=us-central1
```

### Multi-Agent Delegation

```python
from google.adk.agents import LlmAgent

specialist = LlmAgent(
    name="Specialist",
    description="Handles specific tasks",  # Used for auto-routing
    model="gemini-2.0-flash"
)

coordinator = LlmAgent(
    name="Coordinator", 
    model="gemini-2.0-flash",
    instruction="Route requests to appropriate specialists.",
    sub_agents=[specialist]
)
```

### State Sharing

```python
# Use output_key to write to shared state
agent_a = LlmAgent(
    name="AgentA",
    instruction="Process input.",
    output_key="processed_data"  # Saves output to state['processed_data']
)

agent_b = LlmAgent(
    name="AgentB", 
    instruction="Use {processed_data} for next step."  # Reads from state
)
```

## Debugging Tips

- Use `adk web` for visual step-by-step inspection
- Check `context.state` for data flow issues
- Implement `before_model_callback` / `after_model_callback` for logging
- Review agent `description` fields for routing problems

## Key Imports

```python
from google.adk.agents import Agent, LlmAgent, BaseAgent
from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent
from google.adk.tools import google_search, FunctionTool
from google.adk.tools.mcp_tool import MCPToolset
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
```
