from __future__ import annotations

"""DAPEAgent.triage_agent

Main triage agent for Azure resource management with guardrails.
Determines the appropriate specialist agent based on user requests and validates
resource existence before handoff.
"""

import json
from pathlib import Path
from typing import Optional

from agents import Agent, OpenAIChatCompletionsModel, function_tool, InputGuardrail, GuardrailFunctionOutput, Runner, RunContextWrapper
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
        
        # Store the subscription information in the shared context
        ctx.context.subscription_id = result  # Assuming switch_subscription returns the subscription ID
        ctx.context.subscription_name = subscription_name_or_id
        
        return f"Successfully switched to subscription: {subscription_name_or_id}"
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


# Guardrail Agent Tools
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
                "provisioning_state": rg.provisioning_state
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


# Pydantic models for guardrail outputs
class ResourceGroupExistsOutput(BaseModel):
    resource_group_exists: bool
    reasoning: str
    resource_group_name: str


class ResourceExistsOutput(BaseModel):
    resource_exists: bool
    reasoning: str
    resource_name: str
    resource_type: str


# Guardrail agents
def get_rg_guardrail_agent() -> Agent:
    """Create the resource group existence guardrail agent."""
    prompt_path = Path(__file__).parent / "triage_agent.yaml"
    agent_config = load_yaml_prompt(prompt_path)
    rg_config = agent_config["rg_guardrail"]
    
    return Agent(
        name="Resource Group Guardrail",
        model=OpenAIChatCompletionsModel(
            model=rg_config["model"],
            openai_client=_build_client(azure_deployment=rg_config["model"]),
        ),
        instructions=rg_config["system_prompt"],
        tools=[list_rg_in_subscription],
        output_type=ResourceGroupExistsOutput,
    )


def get_resource_guardrail_agent() -> Agent:
    """Create the resource existence guardrail agent."""
    prompt_path = Path(__file__).parent / "triage_agent.yaml"
    agent_config = load_yaml_prompt(prompt_path)
    resource_config = agent_config["resource_guardrail"]
    
    return Agent(
        name="Resource Guardrail",
        model=OpenAIChatCompletionsModel(
            model=resource_config["model"],
            openai_client=_build_client(azure_deployment=resource_config["model"]),
        ),
        instructions=resource_config["system_prompt"],
        tools=[list_resource_in_sub],
        output_type=ResourceExistsOutput,
    )


# Guardrail functions
async def resource_group_guardrail(ctx, agent, input_data):
    """Guardrail to check if the specified resource group exists."""
    rg_agent = get_rg_guardrail_agent()
    result = await Runner.run(rg_agent, input_data, context=ctx.context)
    final_output = result.final_output_as(ResourceGroupExistsOutput)
    
    # Store the resource group name in context if it exists
    if final_output.resource_group_exists:
        ctx.context.resource_group_name = final_output.resource_group_name
    
    return GuardrailFunctionOutput(
        output_info=final_output,
        tripwire_triggered=not final_output.resource_group_exists,
    )


async def resource_exists_guardrail(ctx, agent, input_data):
    """Guardrail to check if the specified resource exists."""
    resource_agent = get_resource_guardrail_agent()
    result = await Runner.run(resource_agent, input_data, context=ctx.context)
    final_output = result.final_output_as(ResourceExistsOutput)
    
    # Store the resource name in context if it exists
    if final_output.resource_exists:
        ctx.context.resource_name = final_output.resource_name
    
    return GuardrailFunctionOutput(
        output_info=final_output,
        tripwire_triggered=not final_output.resource_exists,
    )


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
        ],
        handoffs=[linked_services_agent],
        input_guardrails=[
            InputGuardrail(guardrail_function=resource_group_guardrail),
            InputGuardrail(guardrail_function=resource_exists_guardrail),
        ],
        handoff_description="Main triage agent that routes Azure resource management requests to appropriate specialist agents.",
    )
