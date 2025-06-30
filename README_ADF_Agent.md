# ADF Linked Services Agent

This project implements an AI agent that manages Azure Data Factory (ADF) Linked Services using the OpenAI Agents framework. The agent follows the pattern from `test.py` and provides a conversational interface for ADF operations.

## Features

The ADF agent provides the following capabilities:

- **List Linked Services**: Get all linked services or filter by type (e.g., Snowflake, SQL Database)
- **Get Service Details**: Retrieve detailed configuration of specific linked services
- **Update Snowflake Services**: Update Snowflake FQDN configurations with dry-run support
- **Test Connections**: Verify linked service connectivity

## Prerequisites

1. **Azure Data Factory**: Access to an existing ADF instance
2. **Azure Authentication**: Configured Azure CLI or service principal
3. **OpenAI Agents**: Install the required Python packages
4. **Environment Variables**: Configure the required settings

## Required Environment Variables

Create a `.env` file with the following variables:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-gpt-4o-deployment-name

# OpenAI API Key for tracing (optional)
OPENAI_API_KEY=your_openai_api_key_for_tracing

# Azure Data Factory Configuration
ADF_RESOURCE_GROUP=your-resource-group-name
ADF_FACTORY_NAME=your-adf-factory-name
ADF_SUBSCRIPTION_ID=your-azure-subscription-id
```

## Installation

1. Install required packages:
```bash
pip install openai agents azure-mgmt-datafactory azure-identity python-dotenv
```

2. Ensure Azure CLI is installed and authenticated:
```bash
az login
az account set --subscription "your-subscription-id"
```

## Usage

### Running the Demo

```bash
python adf_agent.py
```

The demo will:
1. List all linked services
2. Filter by Snowflake type
3. Get details of a specific service
4. Perform a dry-run update
5. Test service connection

### Using the Agent Interactively

```python
from adf_agent import adf_agent
from agents import Runner

# Example conversation
result = await Runner.run(
    adf_agent,
    input="Show me all Snowflake linked services in my ADF"
)
print(result.final_output)
```

## Function Tools

The agent uses the following function tools:

### `list_linked_services(filter_by_type: Optional[str] = None)`
- Lists all linked services
- Optional filtering by service type
- Returns JSON formatted service list

### `get_linked_service_details(linked_service_name: str)`
- Gets detailed configuration for a specific service
- Returns JSON formatted service details

### `update_snowflake_linked_service(linked_service_name, old_fqdn, new_fqdn, dry_run=True)`
- Updates Snowflake FQDN in linked services
- Supports dry-run mode for preview
- Returns operation status

### `test_linked_service_connection(linked_service_name: str)`
- Tests connectivity for a linked service
- Returns connection test results

## Azure Integration

The agent integrates with Azure through:

- **Azure Identity**: Uses DefaultAzureCredential for authentication
- **Azure Data Factory SDK**: Leverages the official Azure SDK
- **REST API**: Direct API calls for advanced operations

## Error Handling

The agent includes comprehensive error handling:

- Azure authentication errors
- API rate limiting
- Service configuration issues
- Network connectivity problems

## Security Considerations

- Uses Azure managed identity when possible
- Supports dry-run mode for destructive operations
- Validates input parameters
- Logs operations for audit purposes

## Tracing and Monitoring

The agent supports OpenTelemetry tracing:

- Workflow-level tracing
- Function call tracing
- Error tracking
- Performance monitoring

## Example Conversations

**List Services:**
```
User: "Show me all linked services"
Agent: [Lists all services with names and types]
```

**Filter by Type:**
```
User: "Show only Snowflake services"
Agent: [Lists only Snowflake linked services]
```

**Update Configuration:**
```
User: "Update the Snowflake service 'MySnowflake' to use new-account.snowflakecomputing.com"
Agent: [Performs dry run, shows preview, asks for confirmation]
```

**Test Connection:**
```
User: "Test the connection for MySnowflake"
Agent: [Tests connection and reports results]
```

## Troubleshooting

Common issues and solutions:

1. **Authentication Errors**: Ensure Azure CLI is logged in
2. **Resource Not Found**: Verify ADF name and resource group
3. **Permission Denied**: Check Azure RBAC permissions
4. **Connection Tests Fail**: Verify network connectivity and credentials

## Contributing

When extending the agent:

1. Follow the function_tool pattern
2. Include comprehensive docstrings
3. Add proper error handling
4. Update the agent's instructions
5. Add tools to the agent's tools list 