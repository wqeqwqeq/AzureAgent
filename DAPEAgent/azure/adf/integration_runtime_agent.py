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

from azure_tools.adf.integration_runtime import ADFIntegrationRuntime
from ..agent_builder import _build_client, load_yaml_prompt
from ..config import AzureCtx
from ..shared_tools import set_azure_context


# ---------- Tool Functions ----------
@function_tool
def get_ir_details(
    ctx: RunContextWrapper[AzureCtx],
    ir_name: Annotated[str, "Name of the integration runtime to get details for"]
) -> str:
    """
    Get detailed information about a specific integration runtime.
    
    Args:
        ir_name: Name of the integration runtime to get details for
    
    Returns:
        JSON string containing the integration runtime details
    """
    try:
        c = ctx.context
        adf_service = ADFIntegrationRuntime(
            subscription_id=c.subscription_id,
            resource_group_name=c.resource_group_name,
            resource_name=c.resource_name,
            auth=c.ensure_auth()  # Use shared authentication
        )
        ir_details = adf_service.get_ir(ir_name)
        return json.dumps(ir_details, indent=2)
    except Exception as e:
        return f"Error getting integration runtime details: {str(e)}"


@function_tool
def get_ir_status(
    ctx: RunContextWrapper[AzureCtx],
    ir_name: Annotated[str, "Name of the integration runtime to check status for"]
) -> str:
    """
    Get the status of an integration runtime.
    
    Args:
        ir_name: Name of the integration runtime to check status for
    
    Returns:
        Status information about interactive authoring
    """
    try:
        c = ctx.context
        adf_service = ADFIntegrationRuntime(
            subscription_id=c.subscription_id,
            resource_group_name=c.resource_group_name,
            resource_name=c.resource_name,
            auth=c.ensure_auth()  # Use shared authentication
        )
        is_enabled = adf_service.get_ir_status(ir_name)
        status = "enabled" if is_enabled else "disabled"
        return f"Interactive authoring for integration runtime '{ir_name}' is {status}"
    except Exception as e:
        return f"Error getting integration runtime status: {str(e)}"


@function_tool
def get_ir_type(
    ctx: RunContextWrapper[AzureCtx],
    ir_name: Annotated[str, "Name of the integration runtime to get type for"]
) -> str:
    """
    Get the type of an integration runtime.
    
    Args:
        ir_name: Name of the integration runtime to get type for
    
    Returns:
        Type of the integration runtime (e.g., "Managed", "SelfHosted")
    """
    try:
        c = ctx.context
        adf_service = ADFIntegrationRuntime(
            subscription_id=c.subscription_id,
            resource_group_name=c.resource_group_name,
            resource_name=c.resource_name,
            auth=c.ensure_auth()  # Use shared authentication
        )
        ir_type = adf_service.get_ir_type(ir_name)
        return f"Integration runtime '{ir_name}' is of type: {ir_type}"
    except Exception as e:
        return f"Error getting integration runtime type: {str(e)}"


@function_tool
def enable_interactive_authoring(
    ctx: RunContextWrapper[AzureCtx],
    ir_name: Annotated[str, "Name of the integration runtime to enable interactive authoring for"],
    minutes: Annotated[int, "Number of minutes to enable interactive authoring for"] = 10
) -> str:
    """
    Enable interactive authoring for a Managed integration runtime.
    
    Args:
        ir_name: Name of the integration runtime to enable interactive authoring for
        minutes: Number of minutes to enable interactive authoring for (default: 10)
    
    Returns:
        Status message about the operation
    """
    try:
        c = ctx.context
        adf_service = ADFIntegrationRuntime(
            subscription_id=c.subscription_id,
            resource_group_name=c.resource_group_name,
            resource_name=c.resource_name,
            auth=c.ensure_auth()  # Use shared authentication
        )
        
        # Check if it's already enabled
        if adf_service.get_ir_status(ir_name):
            return f"Interactive authoring is already enabled for integration runtime '{ir_name}'"
        
        # Check if it's a Managed integration runtime
        ir_type = adf_service.get_ir_type(ir_name)
        if ir_type != "Managed":
            return f"Interactive authoring is only supported for Managed integration runtimes. Current type: {ir_type}"
        
        adf_service.enable_interactive_authoring(ir_name, minutes)
        return f"Successfully enabled interactive authoring for integration runtime '{ir_name}' for {minutes} minutes"
    except Exception as e:
        return f"Error enabling interactive authoring: {str(e)}"


# ---------- ADF Integration Runtime Agent Factory ----------
def get_agent_adf_integration_runtime(
    user_input: Optional[str] = None,
    subscription_id: Optional[str] = None,
    resource_group_name: Optional[str] = None,
    resource_name: Optional[str] = None,
    context: Optional[AzureCtx] = None
) -> Agent[AzureCtx]:
    """
    Get the ADF Integration Runtime Agent instance.
    
    If context parameters are provided, they will be used to configure the agent's context.
    
    Args:
        user_input: Optional user's question or request (used when creating context)
        subscription_id: Optional Azure subscription ID
        resource_group_name: Optional Azure resource group name
        resource_name: Optional Azure Data Factory name
        context: Optional pre-configured context
    
    Returns:
        Agent[AzureCtx]: The ADF Integration Runtime Agent
    """

    yaml_path = Path(__file__).parent.parent / "prompts" / "integration_runtime_prompt.yaml"
    prompt_data = load_yaml_prompt(yaml_path)

    system_prompt = prompt_data.get("system_prompt", "You are an Azure Data Factory Integration Runtime specialist.")
    model = prompt_data.get("model", "gpt-4.1-mini")
    handoff_description = prompt_data.get("handoff_description", "ADF Integration Runtime Agent")

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
        name="ADF Integration Runtime Agent",
        model=OpenAIChatCompletionsModel(model, openai_client=_build_client()),
        instructions=system_prompt,
        tools=[
            get_ir_details,
            get_ir_status,
            get_ir_type,
            enable_interactive_authoring,
            set_azure_context
        ],
        handoff_description=handoff_description,
    )
    
    return agent, context