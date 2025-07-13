"""Azure MCP Agent module.

Provides an agent that uses Azure MCP server tools through tool filtering.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from agents import (
    Agent,
    OpenAIChatCompletionsModel,
)
from agents.mcp import MCPServerStdio, ToolFilterContext

from ..agent_builder import _build_client, load_yaml_prompt
from ..config import AzureCtx


def allow_tools(ctx: ToolFilterContext, tool) -> bool:
    """
    Tool filter function to allow specific Azure MCP tools.
    
    Args:
        ctx: Tool filter context
        tool: The tool to check
        
    Returns:
        bool: True if tool is allowed, False otherwise
    """
    tool_list = [
        "microsoft_docs_search",
        "azmcp-azureterraformbestpractices-get",
        "azmcp-bestpractices-get",
        "azmcp-bicepschema-get",
        "azmcp-cosmos-account-list",
        "azmcp-cosmos-database-container-item-query",
        "azmcp-cosmos-database-container-list",
        "azmcp-cosmos-database-list",
        "azmcp-foundry-models-deploy",
        "azmcp-foundry-models-deployments-list",
        "azmcp-foundry-models-list",
        "azmcp-group-list",
        "azmcp-kusto-cluster-get",
        "azmcp-kusto-cluster-list",
        "azmcp-kusto-database-list",
        "azmcp-kusto-query",
        "azmcp-kusto-sample",
        "azmcp-kusto-table-list",
        "azmcp-kusto-table-schema",
        "azmcp-monitor-healthmodels-entity-gethealth",
        "azmcp-monitor-metrics-definitions",
        "azmcp-monitor-metrics-query",
        "azmcp-monitor-resource-log-query",
        "azmcp-monitor-table-list",
        "azmcp-monitor-table-type-list",
        "azmcp-monitor-workspace-list",
        "azmcp-monitor-workspace-log-query",
        "azmcp-role-assignment-list",
        "azmcp-subscription-list"
    ]
    if tool.name in tool_list:
        return True
    return False


def get_azure_mcp_agent(
    user_input: Optional[str] = None,
    subscription_id: Optional[str] = None,
    resource_group_name: Optional[str] = None,
    resource_name: Optional[str] = None,
    context: Optional[AzureCtx] = None
) -> tuple[Agent[AzureCtx], MCPServerStdio, Optional[AzureCtx]]:
    """
    Get the Azure MCP Agent instance.
    
    If context parameters are provided, they will be used to configure the agent's context.
    
    Args:
        user_input: Optional user's question or request (used when creating context)
        subscription_id: Optional Azure subscription ID
        resource_group_name: Optional Azure resource group name
        resource_name: Optional Azure resource name
        context: Optional pre-configured context
    
    Returns:
        tuple[Agent[AzureCtx], Optional[AzureCtx]]: The Azure MCP Agent and its context
    """

    # Uncomment below if you want to use a YAML prompt file
    yaml_path = Path(__file__).parent.parent / "prompts" / "azure_mcp_prompt.yaml"
    prompt_data = load_yaml_prompt(yaml_path)
    system_prompt = prompt_data.get("system_prompt", "You are an Azure specialist.")
    model = prompt_data.get("model", "gpt-4o-mini")
    handoff_description = prompt_data.get("handoff_description", "Azure MCP Agent")

    # If context parameters are provided, create and set the context
    if context is not None or any([subscription_id, resource_group_name, resource_name]):
        if context is None:
            context = AzureCtx(
                subscription_id=subscription_id,
                resource_group_name=resource_group_name,
                resource_name=resource_name,
                intent=user_input or ""
            )
            # Initialize authentication
            context.ensure_auth()

    # Create MCP server with tool filtering  
    mcp_server = MCPServerStdio(
        params={"command": "npx", "args": ["-y", "@azure/mcp@latest", "server", "start"]}, 
        client_session_timeout_seconds=240, 
        tool_filter=allow_tools
    )

    agent = Agent[AzureCtx](
        name="Azure MCP Agent",
        model=OpenAIChatCompletionsModel(model, openai_client=_build_client()),
        instructions=system_prompt,
        mcp_servers=[mcp_server],
        handoff_description=handoff_description,
    )
    
    return agent, mcp_server, context, 
