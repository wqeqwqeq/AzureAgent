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
    # Check if the input actually mentions resource groups or specific resources
    input_text = str(input_data).lower()
    
    # Skip validation for general queries that don't mention specific resources
    skip_phrases = [
        "list all subscriptions",
        "show subscriptions", 
        "list subscriptions",
        "switch to subscription",
        "list resource groups",
        "show resource groups",
        "list all resource groups"
    ]
    
    if any(phrase in input_text for phrase in skip_phrases):
        # These queries don't require resource group validation
        return GuardrailFunctionOutput(
            output_info=ResourceGroupExistsOutput(
                resource_group_exists=True,
                reasoning="Query does not require resource group validation",
                resource_group_name="N/A"
            ),
            tripwire_triggered=False,
        )
    
    # If we already have a resource group in context and this query is about operations within it
    # (like testing connections, listing services, etc.), skip validation
    if (ctx.context.resource_group_name and 
        any(phrase in input_text for phrase in [
            "test the connection", "test connection", "list linked services", 
            "show linked services", "in the same", "same data factory"
        ])):
        return GuardrailFunctionOutput(
            output_info=ResourceGroupExistsOutput(
                resource_group_exists=True,
                reasoning=f"Using previously validated resource group: {ctx.context.resource_group_name}",
                resource_group_name=ctx.context.resource_group_name
            ),
            tripwire_triggered=False,
        )
    
    # Check if input mentions a resource group
    rg_keywords = ["resource group", "resource-group", "rg "]
    has_rg_mention = any(keyword in input_text for keyword in rg_keywords)
    
    if not has_rg_mention:
        # No resource group mentioned, allow through
        return GuardrailFunctionOutput(
            output_info=ResourceGroupExistsOutput(
                resource_group_exists=True,
                reasoning="No specific resource group mentioned in query",
                resource_group_name="N/A"
            ),
            tripwire_triggered=False,
        )
    
    # Resource group is mentioned, validate it
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
    # Check if the input actually mentions specific resources
    input_text = str(input_data).lower()
    
    # Skip validation for general queries that don't mention specific resources
    skip_phrases = [
        "list all subscriptions",
        "show subscriptions",
        "list subscriptions", 
        "switch to subscription",
        "list resource groups",
        "show resource groups",
        "list all resource groups",
        "list all resources",
        "show all resources"
    ]
    
    if any(phrase in input_text for phrase in skip_phrases):
        # These queries don't require resource validation
        return GuardrailFunctionOutput(
            output_info=ResourceExistsOutput(
                resource_exists=True,
                reasoning="Query does not require specific resource validation",
                resource_name="N/A",
                resource_type="N/A"
            ),
            tripwire_triggered=False,
        )
    
    # If we already have a resource in context and this query is about operations within it
    # (like testing connections, listing services, etc.), skip validation
    if (ctx.context.resource_name and 
        any(phrase in input_text for phrase in [
            "test the connection", "test connection", "list linked services", 
            "show linked services", "in the same", "same data factory"
        ])):
        return GuardrailFunctionOutput(
            output_info=ResourceExistsOutput(
                resource_exists=True,
                reasoning=f"Using previously validated resource: {ctx.context.resource_name}",
                resource_name=ctx.context.resource_name,
                resource_type="Microsoft.DataFactory/factories"  # Assume ADF based on context
            ),
            tripwire_triggered=False,
        )
    
    # Check if input mentions specific resource types or names
    resource_keywords = [
        "data factory", "adf", "key vault", "batch account", 
        "linked service", "pipeline", "trigger"
    ]
    has_resource_mention = any(keyword in input_text for keyword in resource_keywords)
    
    if not has_resource_mention:
        # No specific resource mentioned, allow through
        return GuardrailFunctionOutput(
            output_info=ResourceExistsOutput(
                resource_exists=True,
                reasoning="No specific resource mentioned in query",
                resource_name="N/A", 
                resource_type="N/A"
            ),
            tripwire_triggered=False,
        )
    
    # Specific resource is mentioned, validate it
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
