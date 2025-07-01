from __future__ import annotations

"""DAPEAgent.triage_agent

Main triage agent for Azure resource management.
Determines the appropriate specialist agent based on user requests.
"""

import json
from pathlib import Path
from typing import Optional

from agents import Agent, OpenAIChatCompletionsModel, function_tool, Runner, RunContextWrapper
from pydantic import BaseModel

from DAPEAgent.agent_builder import _build_client, load_yaml_prompt
from DAPEAgent.utils.azure_adapters import get_resource_handler, AzureCtx


# Triage Agent Tools
@function_tool
def switch_subscription(
    ctx: RunContextWrapper[AzureCtx],
    subscription_name_or_id: str
) -> str:
    """
    Switch to a different Azure subscription.
    
    Args:
        subscription_name_or_id: Either the subscription name or subscription ID
    
    Returns:
        Status message about the subscription switch
    """
    try:
        from azure_tools.subscription_resource import SubscriptionResourceManager
        result = SubscriptionResourceManager.switch_subscription(subscription_name_or_id)
        
        # Get the actual subscription ID and name after switching
        current_subscription_id = SubscriptionResourceManager.get_current_subscription_id()
        current_subscription_name = SubscriptionResourceManager.get_current_subscription_name()
        
        # Store the correct subscription information in the shared context
        ctx.context.subscription_id = current_subscription_id
        ctx.context.subscription_name = current_subscription_name
        
        return f"Successfully switched to subscription: {current_subscription_name} ({current_subscription_id})"
    except Exception as e:
        return f"Error switching subscription: {str(e)}"


@function_tool
def list_subscriptions(ctx: RunContextWrapper[AzureCtx]) -> str:
    """
    List all subscriptions the signed-in identity can see.
    
    Returns:
        JSON string containing the list of subscriptions
    """
    try:
        service = get_resource_handler("subscription_resource", ctx.context)
        subscriptions = list(service.list_subscriptions())
        subscription_list = [
            {
                "subscription_id": sub.subscription_id,
                "display_name": sub.display_name,
                "state": sub.state.value if hasattr(sub.state, 'value') else str(sub.state)
            }
            for sub in subscriptions
        ]
        return json.dumps(subscription_list, indent=2)
    except Exception as e:
        return f"Error listing subscriptions: {str(e)}"


@function_tool
def list_rg_in_subscription(ctx: RunContextWrapper[AzureCtx]) -> str:
    """
    List all resource groups in the current subscription.
    
    Returns:
        JSON string containing the list of resource groups
    """
    try:
        service = get_resource_handler("subscription_resource", ctx.context)
        resource_groups = list(service.list_rg_in_subscription())
        rg_list = [
            {
                "name": rg.name,
                "location": rg.location,
                "provisioning_state": getattr(rg, 'provisioning_state', 'Unknown')
            }
            for rg in resource_groups
        ]
        return json.dumps(rg_list, indent=2)
    except Exception as e:
        return f"Error listing resource groups: {str(e)}"


@function_tool
def list_resource_in_sub(
    ctx: RunContextWrapper[AzureCtx],
    resource_type: Optional[str] = None
) -> str:
    """
    List resources in the subscription, optionally filtered by resource type.
    
    Args:
        resource_type: Optional resource type filter (Microsoft.KeyVault/vaults, 
                      Microsoft.DataFactory/factories, Microsoft.Batch/batchAccounts)
    
    Returns:
        JSON string containing the list of resources
    """
    try:
        service = get_resource_handler("subscription_resource", ctx.context)
        resources = service.list_resource_in_sub(resource_type=resource_type)
        return json.dumps(resources, indent=2)
    except Exception as e:
        return f"Error listing resources: {str(e)}"


def get_agent() -> Agent:
    """
    Create and return the main triage agent.
    
    Returns:
        Configured Agent instance ready for use with an AzureCtx context
    """
    # Import specialist agents
    from DAPEAgent.adf.linked_services_agent import get_agent as get_linked_services_agent
    # Add other specialist agents as needed
    
    # Create specialist agent instances (they will receive the same context)
    linked_services_agent = get_linked_services_agent()
    
    # Load the prompt from the YAML file
    prompt_path = Path(__file__).parent / "triage_agent.yaml"
    agent_config = load_yaml_prompt(prompt_path)
    triage_config = agent_config["triage_agent"]
    
    return Agent(
        name="Azure Resource Triage Agent",
        model=OpenAIChatCompletionsModel(
            model=triage_config["model"],
            openai_client=_build_client(azure_deployment=triage_config["model"]),
        ),
        instructions=triage_config["system_prompt"],
        tools=[
            switch_subscription,
            list_subscriptions,
            list_rg_in_subscription,
            list_resource_in_sub,
        ],
        handoffs=[linked_services_agent],
    )
