from __future__ import annotations

"""DAPEAgent.adf.linked_services_agent

Task-specific agent for Azure Data Factory Linked Services management.
Wraps `azure_tools.adf.linked_services.ADFLinkedServices` and exposes its
methods via @function_tool-decorated wrappers.
"""

import json
from pathlib import Path
from typing import Optional

from agents import Agent, OpenAIChatCompletionsModel, function_tool, RunContextWrapper

from DAPEAgent.agent_builder import _build_client, load_yaml_prompt
from DAPEAgent.utils.azure_adapters import get_resource_handler, AzureCtx


@function_tool
def list_linked_services(
    ctx: RunContextWrapper[AzureCtx],
    filter_by_type: Optional[str] = None
) -> str:
    """
    List all linked services in the Azure Data Factory.
    
    Args:
        filter_by_type: Optional filter to only show linked services of a specific type
    
    Returns:
        JSON string containing the list of linked services
    """
    try:
        service = get_resource_handler("adf.linked_services", ctx.context)
        services = service.list_linked_services(filter_by_type=filter_by_type)
        return json.dumps(services, indent=2)
    except Exception as e:
        return f"Error listing linked services: {str(e)}"


@function_tool
def get_linked_service_details(
    ctx: RunContextWrapper[AzureCtx],
    linked_service_name: str
) -> str:
    """
    Get detailed information about a specific linked service.
    
    Args:
        linked_service_name: Name of the linked service to get details for
    
    Returns:
        JSON string containing the linked service details
    """
    try:
        service = get_resource_handler("adf.linked_services", ctx.context)
        service_details = service.get_linked_service_details(linked_service_name)
        return json.dumps(service_details, indent=2)
    except Exception as e:
        return f"Error getting linked service details: {str(e)}"


@function_tool
def update_snowflake_linked_service(
    ctx: RunContextWrapper[AzureCtx],
    linked_service_name: str,
    old_fqdn: str,
    new_fqdn: str,
    dry_run: bool = True
) -> str:
    """
    Update the Snowflake account FQDN in a linked service.
    
    Args:
        linked_service_name: Name of the Snowflake linked service to update
        old_fqdn: Current FQDN to replace
        new_fqdn: New FQDN to use
        dry_run: If True, only shows what would be changed without making actual changes
    
    Returns:
        Status message about the update operation
    """
    try:
        service = get_resource_handler("adf.linked_services", ctx.context)
        result = service.update_linked_service_sf_account(
            linked_service_name=linked_service_name,
            old_fqdn=old_fqdn,
            new_fqdn=new_fqdn,
            dry_run=dry_run
        )
        
        if dry_run:
            return f"Dry run completed. Would update linked service '{linked_service_name}' from '{old_fqdn}' to '{new_fqdn}'"
        else:
            return f"Successfully updated linked service '{linked_service_name}' from '{old_fqdn}' to '{new_fqdn}'"
    except Exception as e:
        return f"Error updating linked service: {str(e)}"


@function_tool
def test_linked_service_connection(
    ctx: RunContextWrapper[AzureCtx],
    linked_service_name: str
) -> str:
    """
    Test the connection of a linked service.
    
    Args:
        linked_service_name: Name of the linked service to test
    
    Returns:
        Result of the connection test
    """
    try:
        service = get_resource_handler("adf.linked_services", ctx.context)
        test_result = service.test_linked_service_connection(linked_service_name)
        
        if test_result.get("succeeded"):
            return f"Connection test successful for linked service '{linked_service_name}'"
        else:
            error_message = test_result.get("errors", [{}])[0].get("message", "Unknown error")
            return f"Connection test failed for linked service '{linked_service_name}': {error_message}"
    except Exception as e:
        return f"Error testing linked service connection: {str(e)}"


def get_agent() -> Agent:
    """
    Create and return the ADF Linked Services agent.
    
    Returns:
        Configured Agent instance ready for use with an AzureCtx context
    """
    # Load the prompt from the YAML file
    prompt_path = Path(__file__).parent / "prompts" / "linked_service_prompt.yaml"
    agent_config = load_yaml_prompt(prompt_path)
    instructions = agent_config["system_prompt"]
    model = agent_config["model"]
    
    return Agent(
        name="ADF Linked Services Specialist",
        model=OpenAIChatCompletionsModel(
            model=model,
            openai_client=_build_client(azure_deployment=model),
        ),
        instructions=instructions,
        tools=[
            list_linked_services,
            get_linked_service_details,
            update_snowflake_linked_service,
            test_linked_service_connection,
        ],
        handoff_description="You are a specialist in Azure Data Factory Linked Services. You are able to list, get details, update Snowflake linked services, and test linked service connections.",
    ) 