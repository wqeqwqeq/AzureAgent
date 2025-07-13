from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

from agents import (
    Agent,
    Runner,
    RunContextWrapper,  # core
    function_tool,
    handoff,  # tools & handoffs
    OpenAIChatCompletionsModel,
)
from agents.mcp import MCPServerStdio

from azure_tools.auth import AzureAuthentication
from .agent_builder import _build_client, load_yaml_prompt
from .config import AzureCtx
from .adf.linked_services_agent import get_agent_adf_linked_services
from .adf.integration_runtime_agent import get_agent_adf_integration_runtime
# from .adf.pipelines_agent import get_agent_adf_pipelines # this is not working as of now due to pydantic issue
from .keyvault.key_vault_agent import get_agent_key_vault
from .mcp.azure_mcp_agent import get_azure_mcp_agent


# ---------- Triage agent tools ----------
@function_tool
def set_azure_context(
    ctx: RunContextWrapper[AzureCtx],
    subscription_id: Annotated[Optional[str], "Azure subscription ID in format XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"] = None,
    resource_group_name: Annotated[Optional[str], "Azure resource group name"] = None,
    resource_name: Annotated[Optional[str], "Specific Azure resource name (e.g., vault name, data factory name)"] = None,
    intent: Annotated[Optional[str], "Plain-English description of what the user wants to do with the resource"] = None,
) -> str:
    """Store the parsed Azure resource context information and initialize authentication.
    Call this function first to check existing context and update with any new information.
    Only updates fields that are provided (not None). Preserves existing context values."""
    c = ctx.context
    
    # Track what was already available vs newly set
    already_available = []
    newly_set = []
    
    # Check and update each field
    if c.subscription_id:
        already_available.append(f"Subscription ID: {c.subscription_id}")
    elif subscription_id is not None:
        c.subscription_id = subscription_id
        newly_set.append(f"Subscription ID: {subscription_id}")
    
    if c.resource_group_name:
        already_available.append(f"Resource Group: {c.resource_group_name}")
    elif resource_group_name is not None:
        c.resource_group_name = resource_group_name
        newly_set.append(f"Resource Group: {resource_group_name}")
    
    if c.resource_name:
        already_available.append(f"Resource Name: {c.resource_name}")
    elif resource_name is not None:
        c.resource_name = resource_name
        newly_set.append(f"Resource Name: {resource_name}")
    
    if c.intent:
        already_available.append(f"Intent: {c.intent}")
    elif intent is not None:
        c.intent = intent
        newly_set.append(f"Intent: {intent}")
    
    # Initialize authentication if not already done
    if c.auth is None:
        c.auth = AzureAuthentication()
    
    # Determine what's still missing
    missing = []
    if not c.subscription_id:
        missing.append("Subscription ID")
    if not c.resource_group_name:
        missing.append("Resource Group")
    if not c.resource_name:
        missing.append("Resource Name")
    if not c.intent:
        missing.append("Intent")
    
    # Build status message
    status_parts = []
    
    if already_available:
        status_parts.append(f"Already available: {', '.join(already_available)}")
    
    if newly_set:
        status_parts.append(f"Newly set: {', '.join(newly_set)}")
    
    if missing:
        status_parts.append(f"Still missing: {', '.join(missing)}")
    else:
        status_parts.append("All required information is now available!")
    
    status_parts.append(f"Authentication: {'Initialized' if c.auth else 'Not initialized'}")
    
    return "\n".join(status_parts)




def get_triage_agent( **kwargs) -> tuple[Agent[AzureCtx], MCPServerStdio]:

    yaml_path = Path(__file__).parent / "prompts" / "triage_agent.yaml"
    prompt_data = load_yaml_prompt(yaml_path)
    system_prompt = prompt_data.get("system_prompt", "You are an Azure resource triage assistant.")

    model = prompt_data.get("model", "gpt-4.1-mini")

    adf_linked_service_agent, _ = get_agent_adf_linked_services()
    adf_integration_runtime_agent, _ = get_agent_adf_integration_runtime()
    keyvault_agent, _ = get_agent_key_vault()
    mcp_agent, azure_mcp_server , _ = get_azure_mcp_agent()
    triage_agent = Agent[AzureCtx](
        name="Azure Triage Agent",
        model=OpenAIChatCompletionsModel(model, openai_client=_build_client()),
        instructions=system_prompt,
        tools=[
            set_azure_context,
        ],
        handoffs=[
            handoff(adf_linked_service_agent),
            handoff(adf_integration_runtime_agent),
            handoff(keyvault_agent),
            handoff(mcp_agent),
        ],
        **kwargs
    )
    return triage_agent, azure_mcp_server



