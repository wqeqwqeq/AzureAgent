"""Stub module for the KeyVault task agent.

Will interface with `azure_tools.keyvault.AzureKeyVault` for secret CRUD operations.
"""

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

from azure_tools.keyvault import AzureKeyVault
from ..agent_builder import _build_client, load_yaml_prompt
from ..config import AzureCtx
from ..shared_tools import set_azure_context

# ---------- Tool Functions ----------
@function_tool
def list_secrets(
    ctx: RunContextWrapper[AzureCtx]
) -> str:
    """
    List all secrets in the Azure Key Vault.
    
    Returns:
        JSON string containing the list of secrets with their properties
    """
    try:
        c = ctx.context
        kv_service = AzureKeyVault(
            subscription_id=c.subscription_id,
            resource_group_name=c.resource_group_name,
            resource_name=c.resource_name,
            auth=c.ensure_auth()  # Use shared authentication
        )
        secrets = kv_service.list_secrets()
        return json.dumps(secrets, indent=2, default=str)
    except Exception as e:
        return f"Error listing secrets: {str(e)}"


@function_tool
def get_secret(
    ctx: RunContextWrapper[AzureCtx],
    secret_name: Annotated[str, "Name of the secret to retrieve"]
) -> str:
    """
    Get the value of a specific secret from the Azure Key Vault.
    
    Args:
        secret_name: Name of the secret to retrieve
    
    Returns:
        The secret value as a string
    """
    try:
        c = ctx.context
        kv_service = AzureKeyVault(
            subscription_id=c.subscription_id,
            resource_group_name=c.resource_group_name,
            resource_name=c.resource_name,
            auth=c.ensure_auth()  # Use shared authentication
        )
        secret_value = kv_service.get_secret(secret_name)
        return f"Successfully retrieved secret '{secret_name}': {secret_value}"
    except Exception as e:
        return f"Error getting secret '{secret_name}': {str(e)}"


@function_tool
def set_secret(
    ctx: RunContextWrapper[AzureCtx],
    secret_name: Annotated[str, "Name of the secret to set"],
    secret_value: Annotated[str, "Value of the secret to set"]
) -> str:
    """
    Set or update a secret in the Azure Key Vault.
    
    Args:
        secret_name: Name of the secret to set
        secret_value: Value of the secret to set
    
    Returns:
        Status message about the set operation
    """
    try:
        c = ctx.context
        kv_service = AzureKeyVault(
            subscription_id=c.subscription_id,
            resource_group_name=c.resource_group_name,
            resource_name=c.resource_name,
            auth=c.ensure_auth()  # Use shared authentication
        )
        kv_service.set_secret(secret_name, secret_value)
        return f"Successfully set secret '{secret_name}' in Key Vault '{c.resource_name}'"
    except Exception as e:
        return f"Error setting secret '{secret_name}': {str(e)}"





# ---------- Key Vault Agent Factory ----------
def get_agent_key_vault(
    user_input: Optional[str] = None,
    subscription_id: Optional[str] = None,
    resource_group_name: Optional[str] = None,
    resource_name: Optional[str] = None,
    context: Optional[AzureCtx] = None
) -> Agent[AzureCtx]:
    """
    Get the Key Vault Agent instance.
    
    If context parameters are provided, they will be used to configure the agent's context.
    
    Args:
        user_input: Optional user's question or request (used when creating context)
        subscription_id: Optional Azure subscription ID
        resource_group_name: Optional Azure resource group name
        resource_name: Optional Azure Key Vault name
        context: Optional pre-configured context
    
    Returns:
        Agent[AzureCtx]: The Key Vault Agent
    """
    yaml_path = Path(__file__).parent.parent / "prompts" / "key_vault_prompt.yaml"
    prompt_data = load_yaml_prompt(yaml_path)
    
    system_prompt = prompt_data.get("system_prompt", "You are an Azure Key Vault specialist.")
    model = prompt_data.get("model", "gpt-4.1-mini")
    handoff_description = prompt_data.get("handoff_description", "Key Vault Agent")

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
        name="Key Vault Agent",
        model=OpenAIChatCompletionsModel(model, openai_client=_build_client()),
        instructions=system_prompt,
        tools=[
            list_secrets,
            get_secret,
            set_secret,
            set_azure_context
        ],
        handoff_description=handoff_description,
    )
    
    return agent, context 