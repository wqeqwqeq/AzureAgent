# Azure Agent Framework

## 🎉 New: Improved Context Management

The Azure Agent Framework now features automatic context management using the OpenAI Agents SDK's built-in context sharing mechanism. **No more manual context passing!**

### Key Improvements

- **Natural Language Context Extraction**: The triage agent automatically extracts subscription, resource group, and resource names from natural language queries
- **Shared Context**: All agents share the same context object using `RunContextWrapper[AzureCtx]`
- **Automatic Population**: Context information is populated automatically as agents use tools and validate resources
- **No Manual Configuration**: No need to manually specify subscription IDs or resource names upfront

### Usage Example

```python
import asyncio
from DAPEAgent.triage_agent import get_agent
from DAPEAgent.utils.azure_adapters import AzureCtx
from agents import Runner

async def main():
    # Create empty context - LLM will populate it automatically
    ctx = AzureCtx()
    
    # Get triage agent (no context parameter needed!)
    triage = get_agent()
    
    # Natural language query - no manual context required
    result = await Runner.run(
        triage, 
        "Show me linked services in prod-adf in the ProductionRG resource group",
        context=ctx
    )
    
    print(f"Result: {result.final_output}")
    # Context is now automatically populated:
    print(f"Resource Group: {ctx.resource_group_name}")  # "ProductionRG"
    print(f"Resource Name: {ctx.resource_name}")         # "prod-adf"

asyncio.run(main())
```

### How It Works

1. **User Input**: Natural language queries like "Switch to ContosoProd subscription and list linked services in adf-prod"
2. **Context Extraction**: The triage agent extracts key information (subscription names, resource groups, resource names)
3. **Automatic Storage**: Tools and guardrails automatically store validated information in the shared context
4. **Agent Handoff**: Specialist agents receive the populated context automatically
5. **Persistent Context**: Context persists throughout the conversation for seamless multi-step operations

### Interactive Mode

Run the example with interactive mode:

```bash
python triage_agent_example.py --interactive
```

This allows you to have natural conversations with the agent and see how context is automatically managed.

---

## Original README Content

An AI-powered agent for managing Azure resources including Azure Data Factory, Batch, Key Vault, and Resource Locks.

## Features

- **Azure Data Factory**: Manage linked services, integration runtimes, triggers, pipelines, and managed private endpoints
- **Azure Batch**: Scale pool nodes and manage batch operations
- **Azure Key Vault**: Retrieve and manage secrets
- **Resource Locks**: Manage resource locks at the resource group level
- **AI Agent Integration**: Expose Azure operations as AI agent tools

## Setup

1. Install dependencies:
   ```bash
   uv install
   ```

2. Copy environment file and configure:
   ```bash
   cp .env.sample .env
   # Edit .env with your Azure credentials
   ```

3. Authenticate with Azure CLI:
   ```bash
   az login
   ```

## Usage

### Direct Azure Tools

```python
from azure_tools import AzureAuthentication
from azure_tools.adf import ADFLinkedServices

# Shared authentication
auth = AzureAuthentication()

# Use ADF linked services
adf_ls = ADFLinkedServices(
    resource_group_name="my-rg",
    resource_name="my-adf",
    auth=auth
)

services = adf_ls.list_linked_services()
```

### AI Agent

```python
from agent import AzureAgent

agent = AzureAgent()
response = agent.run("List all linked services in my ADF")
```

## Project Structure

- `azure_tools/`: Core Azure management utilities
- `agent/`: AI agent integration layer
- `tests/`: Unit and integration tests
