from __future__ import annotations
from typing import Annotated, Optional
from agents import (
    RunContextWrapper,  # core
    function_tool,
)
from azure_tools.auth import AzureAuthentication
from .config import AzureCtx


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
    status_parts = ["Message from set_azure_context: "]
    
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
        status_parts.append("Authentication: Newly set")
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
    
    if already_available:
        status_parts.append(f"Already available: {', '.join(already_available)}")
    
    if newly_set:
        status_parts.append(f"Newly set: {', '.join(newly_set)}")
    
    # if missing:
    #     status_parts.append(f"Still missing: {', '.join(missing)}")
    # else:
    #     status_parts.append("All required information is now available!")
    
    # status_parts.append(f"Authentication: {'Initialized' if c.auth else 'Not initialized'}")
    # status_parts.append("Don't call this function AGAIN or ask follow-up questions in case anything is missing.")
    # status_parts.append("For the other agents who see this information, please ONLY use the provided (if any) subscription id, resource group name, resource name.")
    
    return "\n".join(status_parts)