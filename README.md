# Azure Agent

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
