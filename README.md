# Azure Agent Framework

A sophisticated AI-powered agent system for managing Azure resources through natural language interactions. The framework uses a triage agent to intelligently route requests to specialized agents for Azure Data Factory, Key Vault, and other Azure services. Using OpenAI Agent SDK

## 🏗️ Architecture

The framework follows a **triage-based architecture** where:

1. **Triage Agent**: Analyzes user requests and extracts Azure context (subscription, resource group, resource name)
2. **Specialist Agents**: Handle specific Azure service operations
3. **Shared Context**: All agents share Azure authentication and resource context automatically

### Implemented Specialist Agents

- **🔗 ADF Linked Services Agent**: Manage Azure Data Factory linked services
- **⚙️ ADF Integration Runtime Agent**: Handle integration runtime operations  
- **🔐 Key Vault Agent**: Retrieve and manage secrets from Azure Key Vault

## 🚀 Quick Start

### Installation

1. Install uv package manager:
   ```bash
   pip install uv
   ```

2. Sync dependencies:
   ```bash
   uv sync
   ```

3. Authenticate with Azure CLI:
   ```bash
   az login
   ```

### Run Example

```bash
uv run main-example.py
```

## 💬 Usage Examples

### Natural Language Queries

The triage agent understands natural language and automatically extracts Azure context:

```python
import asyncio
from agents import Runner, trace
from DAPEAgent.triage_agent import get_triage_agent
from DAPEAgent.config import AzureCtx

async def main():
    triage_agent = get_triage_agent()
    
    # The agent will automatically extract:
    # - Key Vault name: "stanleyakvprod" 
    # - Resource Group: "adf"
    # - Operation: retrieve secrets
    result = await Runner.run(
        triage_agent,
        input=[{"content": "what's the value for secret test-secret-2 and test-secret-1 in the key vault stanleyakvprod in resource group adf", "role": "user"}],
        context=AzureCtx(subscription_id="ee5f77a1-2e59-4335-8bdf-f7ea476f6523")
    )
    
    print("Agent Response:", result)

asyncio.run(main())
```

### Example Queries by Service

**Key Vault Operations:**
- "Get the value of secret 'database-password' from vault 'prod-kv' in resource group 'production'"
- "List all secrets in key vault 'dev-vault'"
- "What's the value for secrets test-secret-1 and test-secret-2?"

**ADF Linked Services:**
- "List all linked services in data factory 'prod-adf'"
- "Show details for linked service 'snowflake-prod'"
- "Test connection for linked service 'sql-server-dev'"
- "Update Snowflake FQDN from old.snowflake.com to new.snowflake.com in linked service 'sf-prod'"

**ADF Integration Runtime:**
- "List all integration runtimes in data factory 'prod-adf'"
- "Show status of integration runtime 'AutoResolveIntegrationRuntime'"
- "Get details for integration runtime 'self-hosted-ir'"

## 🛠️ Available Tools

### Key Vault Agent Tools
- `get_secret_value`: Retrieve specific secret values
- `list_secrets`: List all secrets in a Key Vault
- `get_secret_details`: Get detailed information about a secret

### ADF Linked Services Agent Tools
- `list_linked_services`: List all linked services (with optional type filtering)
- `get_linked_service_details`: Get detailed configuration of a specific linked service
- `update_linked_service_sf_account`: Update Snowflake FQDN in linked services (with dry-run support)
- `test_linked_service_connection`: Test if a linked service can connect successfully

### ADF Integration Runtime Agent Tools
- `list_integration_runtimes`: List all integration runtimes
- `get_integration_runtime_details`: Get detailed information about a specific integration runtime
- `get_integration_runtime_status`: Check the current status of an integration runtime

### Triage Agent Tools
- `set_azure_context`: Store and manage Azure resource context (subscription, resource group, resource name)

## 🔧 Project Structure

```
AzureAgent/
├── azure_tools/                 # Core Azure SDK wrappers
│   ├── adf/                    # Azure Data Factory tools
│   │   ├── integration_runtime_agent.py
│   │   ├── linked_services_agent.py
│   │   └── pipelines_agent.py
│   ├── auth.py                 # Azure authentication
│   ├── base.py                 # Base classes
│   └── keyvault.py             # Key Vault operations
├── DAPEAgent/                  # AI Agent framework
│   ├── adf/                    # ADF specialist agents
│   │   ├── integration_runtime_agent.py
│   │   ├── linked_services_agent.py
│   │   └── pipelines_agent.py
│   ├── keyvault/               # Key Vault agents
│   │   └── key_vault_agent.py
│   ├── prompts/                # Agent prompts and configurations
│   │   ├── triage_agent.yaml
│   │   ├── key_vault_prompt.yaml
│   │   ├── linked_service_prompt.yaml
│   │   └── integration_runtime_prompt.yaml
│   ├── agent_builder.py        # Agent factory utilities
│   ├── config.py               # Azure context configuration
│   └── triage_agent.py         # Main triage agent
├── end-to-end/                 # End-to-end examples
└── main-example.py             # Main example script
```

## 🎯 How It Works

1. **Context Extraction**: The triage agent parses natural language to extract Azure resource information
2. **Authentication**: Shared Azure authentication across all agents using Azure CLI credentials
3. **Intelligent Routing**: Based on keywords and context, requests are routed to appropriate specialist agents
4. **Tool Execution**: Specialist agents execute Azure operations using the extracted context
5. **Result Formatting**: Results are returned in human-readable format with JSON details when needed

## 🔐 Authentication

The framework uses Azure CLI authentication. Ensure you're logged in:

```bash
az login
```

The agents will automatically use your CLI credentials for Azure API calls.

## 📝 Configuration

Each agent is configured through YAML prompt files in `DAPEAgent/prompts/`:

- **System prompts**: Define agent behavior and expertise
- **Model configuration**: Specify which OpenAI model to use  
- **Handoff descriptions**: Define how the triage agent should route requests

## 🚧 Extending the Framework

To add new specialist agents:

1. Create agent implementation in appropriate subfolder
2. Add prompt configuration YAML file
3. Register agent in `triage_agent.py`
4. Update triage routing patterns in `triage_agent.yaml`

## 📖 Examples

See `main-example.py` for a complete working example, or check the `end-to-end/` directory for more advanced scenarios.

---

*Built with OpenAI Agents SDK and Azure SDK for Python*
