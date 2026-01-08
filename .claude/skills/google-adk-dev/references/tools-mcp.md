# Tools & MCP Integration

## Table of Contents
1. [Function Tools](#function-tools)
2. [Built-in Tools](#built-in-tools)
3. [MCP Integration](#mcp-integration)
4. [Tool Context](#tool-context)

## Function Tools

### Basic Function Tool
Any Python function can be a tool. Docstring becomes the tool description.

```python
from google.adk.agents import Agent

def get_weather(city: str) -> dict:
    """Retrieves the current weather for a specified city.
    
    Args:
        city: The name of the city to get weather for.
    
    Returns:
        dict: Weather information with status and report.
    """
    # Implementation
    return {"status": "success", "report": f"Weather in {city}: Sunny, 25°C"}

def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city."""
    import datetime
    from zoneinfo import ZoneInfo
    # Implementation
    return {"status": "success", "time": "10:30 AM"}

root_agent = Agent(
    model='gemini-2.0-flash',
    name='weather_agent',
    tools=[get_weather, get_current_time]
)
```

### FunctionTool Wrapper
For explicit tool creation with more control.

```python
from google.adk.tools import FunctionTool

weather_tool = FunctionTool(get_weather)
```

## Built-in Tools

### Google Search
```python
from google.adk.agents import Agent
from google.adk.tools import google_search

agent = Agent(
    name="search_agent",
    model="gemini-2.0-flash",
    tools=[google_search]
)
```

### Code Execution
```python
from google.adk.code_executors import VertexAICodeExecutor

executor = VertexAICodeExecutor()
# Use in agent configuration
```

## MCP Integration

### Using Existing MCP Servers

#### Stdio Connection (Local)
```python
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset
from mcp import StdioServerParameters

root_agent = LlmAgent(
    model='gemini-2.0-flash',
    name='filesystem_agent',
    instruction='Help the user manage their files.',
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command='npx',
                args=['-y', '@anthropic-ai/mcp-server-filesystem', '/path/to/folder']
            )
        )
    ]
)
```

#### SSE Connection (Remote)
```python
from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseServerParams

tools = MCPToolset(
    connection_params=SseServerParams(
        url="http://localhost:8001/sse"
    )
)
```

#### Streamable HTTP (Production)
```python
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnection

tools = MCPToolset(
    connection_params=StreamableHTTPConnection(
        url="http://localhost:3000/mcp"
    )
)
```

### Google Maps MCP Example
```python
import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset
from mcp import StdioServerParameters

root_agent = LlmAgent(
    model='gemini-2.0-flash',
    name='maps_assistant_agent',
    instruction='Help users with directions and location info.',
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command='npx',
                args=['-y', '@anthropic-ai/mcp-server-google-maps'],
                env={
                    **os.environ,
                    'GOOGLE_MAPS_API_KEY': os.getenv('GOOGLE_MAPS_API_KEY')
                }
            )
        )
    ]
)
```

### Dynamic Tool Fetching
```python
async def get_mcp_tools():
    """Gets tools from the MCP Server."""
    tools = MCPToolset(
        connection_params=StdioServerParameters(
            command='python',
            args=['mcp_server.py']
        ),
        timeout=30
    )
    return await tools.get_tools_async()

# Use in agent
agent = LlmAgent(
    name="mcp_agent",
    model="gemini-2.0-flash",
    tools=await get_mcp_tools()
)
```

## Tool Context

Access tool context for state management and artifacts.

```python
from google.adk.tools import ToolContext

def my_tool(param: str, tool_context: ToolContext) -> dict:
    """Tool with context access."""
    # Read/write state
    tool_context.state["my_key"] = "my_value"
    
    # Access session info
    session_id = tool_context.session.id
    
    # Save artifact
    tool_context.save_artifact("output.txt", "File content")
    
    return {"status": "success"}
```

## MCP Server Creation

### Exposing ADK Tools via MCP
```python
from mcp.server.lowlevel import Server
from mcp import types as mcp_types
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

def create_mcp_server():
    weather_tool = FunctionTool(get_weather)
    
    app = Server("weather-mcp-server")
    
    @app.list_tools()
    async def list_tools() -> list[mcp_types.Tool]:
        return [adk_to_mcp_tool_type(weather_tool)]
    
    @app.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "get_weather":
            return await weather_tool.run_async(**arguments)
    
    return app
```

## Resources
- MCP Tools: https://google.github.io/adk-docs/tools-custom/mcp-tools/
- MCP Overview: https://google.github.io/adk-docs/mcp/
- Tool creation: https://google.github.io/adk-docs/tools/
