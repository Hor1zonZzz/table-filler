# ADK API Quick Reference

## Table of Contents
1. [Core Imports](#core-imports)
2. [Agent Classes](#agent-classes)
3. [Tools](#tools)
4. [Sessions & State](#sessions--state)
5. [Runners](#runners)
6. [CLI Commands](#cli-commands)

## Core Imports

```python
# Agents
from google.adk.agents import Agent, LlmAgent, BaseAgent
from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent
from google.adk.agents.callback_context import CallbackContext

# Tools
from google.adk.tools import FunctionTool, google_search
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.mcp_tool import MCPToolset

# Sessions
from google.adk.sessions import InMemorySessionService, Session

# Runners
from google.adk.runners import Runner

# Models & Types
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types
```

## Agent Classes

### Agent / LlmAgent
Main agent class using LLM for reasoning.

```python
from google.adk.agents import Agent, LlmAgent

agent = Agent(
    name="my_agent",              # Required: unique name
    model="gemini-2.0-flash",     # Required: model ID
    instruction="You are...",      # System instruction
    description="Handles...",      # For auto-routing in multi-agent
    tools=[tool1, tool2],          # List of tools
    sub_agents=[agent1, agent2],   # Child agents
    output_key="result",           # Save output to state[key]
    
    # Callbacks
    before_agent_callback=fn,
    after_agent_callback=fn,
    before_model_callback=fn,
    after_model_callback=fn,
    before_tool_callback=fn,
    after_tool_callback=fn,
)
```

### SequentialAgent
Execute sub-agents in sequence.

```python
from google.adk.agents import SequentialAgent

pipeline = SequentialAgent(
    name="pipeline",
    sub_agents=[agent_a, agent_b, agent_c]
)
```

### ParallelAgent
Execute sub-agents concurrently.

```python
from google.adk.agents import ParallelAgent

parallel = ParallelAgent(
    name="parallel_tasks",
    sub_agents=[agent_a, agent_b]  # Each should write to unique state keys
)
```

### LoopAgent
Repeat sub-agents until condition.

```python
from google.adk.agents import LoopAgent

loop = LoopAgent(
    name="refinement_loop",
    max_iterations=5,              # Maximum iterations
    sub_agents=[critic, refiner]
)
```

### BaseAgent
Base class for custom agents.

```python
from google.adk.agents import BaseAgent

class MyCustomAgent(BaseAgent):
    async def _run_async_impl(self, ctx):
        # Custom logic
        yield event
```

## Tools

### Function Tool
```python
def my_tool(param: str, optional: int = 10) -> dict:
    """Tool description for LLM.
    
    Args:
        param: Description of param.
        optional: Description with default.
    
    Returns:
        dict with status and result.
    """
    return {"status": "success", "data": param}

# Use directly
agent = Agent(tools=[my_tool])

# Or wrap explicitly
from google.adk.tools import FunctionTool
tool = FunctionTool(my_tool)
```

### Tool with Context
```python
from google.adk.tools import ToolContext

def stateful_tool(param: str, tool_context: ToolContext) -> dict:
    """Tool that accesses context."""
    # Read/write state
    tool_context.state["key"] = "value"
    
    # Access session
    session_id = tool_context.session.id
    
    return {"status": "success"}
```

### AgentTool
Wrap agent as callable tool.

```python
from google.adk.tools.agent_tool import AgentTool

specialist = LlmAgent(name="Specialist", model="gemini-2.0-flash")
agent_tool = AgentTool(agent=specialist)

coordinator = Agent(tools=[agent_tool])
```

### MCPToolset
Connect to MCP servers.

```python
from google.adk.tools.mcp_tool import MCPToolset
from mcp import StdioServerParameters

tools = MCPToolset(
    connection_params=StdioServerParameters(
        command='npx',
        args=['-y', '@anthropic-ai/mcp-server-filesystem', '/path']
    ),
    timeout=30  # Optional timeout
)
```

## Sessions & State

### InMemorySessionService
```python
from google.adk.sessions import InMemorySessionService

session_service = InMemorySessionService()

# Create session
session = session_service.create_session(
    app_name="my_app",
    user_id="user_123"
)

# Get session
session = session_service.get_session(
    app_name="my_app",
    user_id="user_123",
    session_id="session_456"
)
```

### State Access
```python
# In callbacks
context.state["key"] = "value"
value = context.state.get("key", "default")

# In tools
tool_context.state["key"] = "value"

# Temporary state (current turn only)
context.state["temp:key"] = "value"
```

## Runners

### Basic Runner
```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

runner = Runner(
    agent=root_agent,
    app_name="my_app",
    session_service=InMemorySessionService()
)

# Run async
async for event in runner.run_async(
    user_id="user_123",
    session_id="session_456",
    new_message=types.Content(parts=[types.Part(text="Hello")])
):
    print(event)
```

### With FastAPI
```python
from google.adk.cli.fast_api import get_fast_api_app

app = get_fast_api_app(
    agent_dir="./agents",
    session_db_url="sqlite:///sessions.db",
    allow_origins=["*"],
    web=True  # Enable web UI
)
```

## CLI Commands

```bash
# Create new agent project
adk create <agent_name>

# Run agent in CLI mode
adk run <agent_folder>

# Run with web UI (http://localhost:8000)
adk web

# Run API server
adk api_server

# Evaluate agent
adk eval <agent_folder> <eval_set.json>
```

## Environment Variables

```bash
# Google AI Studio
GOOGLE_GENAI_API_KEY=your_api_key

# Vertex AI
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your_project_id
GOOGLE_CLOUD_LOCATION=us-central1
```

## Resources
- Full API reference: https://google.github.io/adk-docs/api-reference/python/
- Agents module: https://google.github.io/adk-docs/api-reference/python/google-adk.html
- Tools module: https://google.github.io/adk-docs/api-reference/python/google-adk-tools.html
