from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

from agents import (
    Agent,
    RunContextWrapper,
    function_tool,
    OpenAIChatCompletionsModel,
)

from azure_tools.adf.linked_services import ADFLinkedServices
from ..agent_builder import _build_client, load_yaml_prompt
from ..config import AzureCtx


# ---------- Tool Functions ----------
@function_tool
def list_linked_services(
    ctx: RunContextWrapper[AzureCtx],
    filter_by_type: Annotated[Optional[str], "Optional filter to only show linked services of a specific type"] = None
) -> str:
    """
    List all linked services in the Azure Data Factory.
    
    Args:
        filter_by_type: Optional filter to only show linked services of a specific type
    
    Returns:
        JSON string containing the list of linked services
    """
    try:
        c = ctx.context
        adf_service = ADFLinkedServices(
            subscription_id=c.subscription_id,
            resource_group_name=c.resource_group_name,
            resource_name=c.resource_name,
            auth=c.ensure_auth()  # Use shared authentication
        )
        services = adf_service.list_linked_services(filter_by_type=filter_by_type)
        return json.dumps(services, indent=2)
    except Exception as e:
        return f"Error listing linked services: {str(e)}"


@function_tool
def get_linked_service_details(
    ctx: RunContextWrapper[AzureCtx],
    linked_service_name: Annotated[str, "Name of the linked service to get details for"]
) -> str:
    """
    Get detailed information about a specific linked service.
    
    Args:
        linked_service_name: Name of the linked service to get details for
    
    Returns:
        JSON string containing the linked service details
    """
    try:
        c = ctx.context
        adf_service = ADFLinkedServices(
            subscription_id=c.subscription_id,
            resource_group_name=c.resource_group_name,
            resource_name=c.resource_name,
            auth=c.ensure_auth()  # Use shared authentication
        )
        service_details = adf_service.get_linked_service_details(linked_service_name)
        return json.dumps(service_details, indent=2)
    except Exception as e:
        return f"Error getting linked service details: {str(e)}"


@function_tool
def update_linked_service_sf_account(
    ctx: RunContextWrapper[AzureCtx],
    linked_service_name: Annotated[str, "Name of the Snowflake linked service to update"],
    old_fqdn: Annotated[str, "Current FQDN to replace"],
    new_fqdn: Annotated[str, "New FQDN to use"],
    dry_run: Annotated[bool, "If True, only shows what would be changed without making actual changes"] = True
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
        c = ctx.context
        adf_service = ADFLinkedServices(
            subscription_id=c.subscription_id,
            resource_group_name=c.resource_group_name,
            resource_name=c.resource_name,
            auth=c.ensure_auth()  # Use shared authentication
        )
        result = adf_service.update_linked_service_sf_account(
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
    linked_service_name: Annotated[str, "Name of the linked service to test"]
) -> str:
    """
    Test the connection of a linked service.
    
    Args:
        linked_service_name: Name of the linked service to test
    
    Returns:
        Result of the connection test
    """
    try:
        c = ctx.context
        adf_service = ADFLinkedServices(
            subscription_id=c.subscription_id,
            resource_group_name=c.resource_group_name,
            resource_name=c.resource_name,
            auth=c.ensure_auth()  # Use shared authentication
        )
        test_result = adf_service.test_linked_service_connection(linked_service_name)
        
        if test_result.get("succeeded"):
            return f"Connection test successful for linked service '{linked_service_name}'"
        else:
            error_message = test_result.get("errors", [{}])[0].get("message", "Unknown error")
            return f"Connection test failed for linked service '{linked_service_name}': {error_message}"
    except Exception as e:
        return f"Error testing linked service connection: {str(e)}"



# ---------- ADF Linked Service Agent Factory ----------
def get_agent_adf_linked_services(
    user_input: Optional[str] = None,
    subscription_id: Optional[str] = None,
    resource_group_name: Optional[str] = None,
    resource_name: Optional[str] = None,
    context: Optional[AzureCtx] = None
) -> Agent[AzureCtx]:
    """
    Get the ADF Linked Service Agent instance.
    
    If context parameters are provided, they will be used to configure the agent's context.
    
    Args:
        user_input: Optional user's question or request (used when creating context)
        subscription_id: Optional Azure subscription ID
        resource_group_name: Optional Azure resource group name
        resource_name: Optional Azure Data Factory name
        context: Optional pre-configured context
    
    Returns:
        Agent[AzureCtx]: The ADF Linked Service Agent
    """

    yaml_path = Path(__file__).parent.parent / "prompts" / "linked_service_prompt.yaml"
    prompt_data = load_yaml_prompt(yaml_path)

    system_prompt = prompt_data.get("system_prompt", "You are an Azure Data Factory Linked Services specialist.")
    model = prompt_data.get("model", "gpt-4.1-mini")
    handoff_description = prompt_data.get("handoff_description", "ADF Linked Service Agent")

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
            

    agent = Agent[AzureCtx](
        name="ADF Linked Service Agent",
        model=OpenAIChatCompletionsModel(model, openai_client=_build_client()),
        instructions=system_prompt,
        tools=[
            list_linked_services,
            get_linked_service_details,
            update_linked_service_sf_account,
            test_linked_service_connection,
        ],
        handoff_description=handoff_description,
    )
    

    
    return agent, context