# Multi-Agent Systems & Workflows

## Table of Contents
1. [Agent Hierarchy](#agent-hierarchy)
2. [Workflow Agents](#workflow-agents)
3. [Communication Mechanisms](#communication-mechanisms)
4. [Common Patterns](#common-patterns)

## Agent Hierarchy

ADK organizes agents in a tree structure. Parent-child relationships control conversation flow.

```python
from google.adk.agents import LlmAgent, BaseAgent

greeter = LlmAgent(name="Greeter", model="gemini-2.0-flash")
task_doer = BaseAgent(name="TaskExecutor")

coordinator = LlmAgent(
    name="Coordinator",
    model="gemini-2.0-flash",
    description="I coordinate greetings and tasks.",
    sub_agents=[greeter, task_doer]
)
# Framework automatically sets parent_agent on children
```

**Rules:**
- Single Parent Rule: An agent can only have one parent
- Navigate with `agent.parent_agent` or `agent.find_agent(name)`

## Workflow Agents

### SequentialAgent
Execute sub-agents one after another.

```python
from google.adk.agents import LlmAgent, SequentialAgent

parser = LlmAgent(name="Parser", instruction="Parse the input.", output_key="parsed_data")
analyzer = LlmAgent(name="Analyzer", instruction="Analyze {parsed_data}.", output_key="analysis")
summarizer = LlmAgent(name="Summarizer", instruction="Summarize {analysis}.")

pipeline = SequentialAgent(
    name="DataPipeline",
    sub_agents=[parser, analyzer, summarizer]
)
```

### ParallelAgent
Execute sub-agents concurrently. Each agent should write to unique state keys.

```python
from google.adk.agents import LlmAgent, ParallelAgent

flight_agent = LlmAgent(name="FlightSearch", output_key="flight_results")
hotel_agent = LlmAgent(name="HotelSearch", output_key="hotel_results")

parallel_search = ParallelAgent(
    name="TravelSearch",
    sub_agents=[flight_agent, hotel_agent]
)
```

### LoopAgent
Repeat sub-agents until condition met.

```python
from google.adk.agents import LlmAgent, LoopAgent

critic = LlmAgent(
    name="Critic",
    instruction="Review {current_draft}. Provide critique.",
    output_key="critique_notes"
)

refiner = LlmAgent(
    name="Refiner",
    instruction="Improve {current_draft} based on {critique_notes}.",
    output_key="current_draft"
)

refinement_loop = LoopAgent(
    name="RefinementLoop",
    max_iterations=3,
    sub_agents=[critic, refiner]
)
```

## Communication Mechanisms

### 1. Shared Session State
Agents read/write to `context.state` or `session.state`.

```python
# Writer agent
agent_a = LlmAgent(
    name="AgentA",
    instruction="Find the capital of France.",
    output_key="capital_city"  # Writes to state['capital_city']
)

# Reader agent
agent_b = LlmAgent(
    name="AgentB",
    instruction="Tell me about {capital_city}."  # Reads from state
)
```

### 2. LLM-Driven Delegation
Parent uses LLM reasoning to route to appropriate sub-agent based on `description`.

```python
billing_agent = LlmAgent(
    name="Billing",
    description="Handles billing inquiries.",  # Key for routing
    model="gemini-2.0-flash"
)

support_agent = LlmAgent(
    name="Support",
    description="Handles technical support.",
    model="gemini-2.0-flash"
)

coordinator = LlmAgent(
    name="Coordinator",
    model="gemini-2.0-flash",
    instruction="Route user requests to the appropriate specialist.",
    sub_agents=[billing_agent, support_agent]
)
```

### 3. Explicit Invocation (AgentTool)
Wrap sub-agent as a tool for explicit calling.

```python
from google.adk.tools.agent_tool import AgentTool

specialist = LlmAgent(name="Specialist", model="gemini-2.0-flash")

coordinator = LlmAgent(
    name="Coordinator",
    model="gemini-2.0-flash",
    tools=[AgentTool(agent=specialist)]
)
```

## Common Patterns

### Hub-and-Spoke (Coordinator Pattern)
Central coordinator routes to specialists.

```python
coordinator = LlmAgent(
    name="Coordinator",
    model="gemini-2.0-flash",
    instruction="Analyze requests and delegate to appropriate specialist.",
    sub_agents=[billing_agent, support_agent, sales_agent]
)
```

### Pipeline Pattern
Sequential processing with state passing.

```python
workflow = SequentialAgent(
    name="DataWorkflow",
    sub_agents=[
        LlmAgent(name="Fetch", output_key="raw_data"),
        LlmAgent(name="Clean", instruction="Clean {raw_data}", output_key="clean_data"),
        LlmAgent(name="Analyze", instruction="Analyze {clean_data}", output_key="analysis"),
        LlmAgent(name="Report", instruction="Create report from {analysis}")
    ]
)
```

### Iterative Refinement
Loop with critique and revision.

```python
generator = LlmAgent(name="Generator", output_key="current_draft")

refinement_loop = LoopAgent(
    name="RefinementLoop",
    max_iterations=3,
    sub_agents=[critic, refiner]
)

workflow = SequentialAgent(sub_agents=[generator, refinement_loop])
```

## Resources
- Multi-agent docs: https://google.github.io/adk-docs/agents/multi-agents/
- Workflow agents: https://google.github.io/adk-docs/agents/workflow-agents/
- Custom agents: https://google.github.io/adk-docs/agents/custom-agents/
