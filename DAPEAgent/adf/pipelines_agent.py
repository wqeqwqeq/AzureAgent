"""Stub module for the ADF-Pipelines task agent.

Will encapsulate operations provided by `azure_tools.adf.pipelines.ADFPipelines`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional, Dict, Any

from agents import (
    Agent,
    RunContextWrapper,
    function_tool,
    OpenAIChatCompletionsModel,
)

from azure_tools.adf.pipelines import ADFPipeline
from ..agent_builder import _build_client, load_yaml_prompt
from ..config import AzureCtx


# ---------- Tool Functions ----------
@function_tool
def run_and_fetch(
    ctx: RunContextWrapper[AzureCtx],
    pipeline_name: Annotated[str, "Name of the pipeline to run"],
    activity_name: Annotated[Optional[str], "Optional specific activity name. If None, returns all activities"] = None,
    parameters: Annotated[Optional[Dict[str, Any]], "Optional dictionary of parameters to pass to the pipeline"] = None
) -> str:
    """
    Run a pipeline and wait for completion, then fetch activity results.
    
    Args:
        pipeline_name: Name of the pipeline to run
        activity_name: Optional specific activity name. If None, returns all activities
        parameters: Optional dictionary of parameters to pass to the pipeline
    
    Returns:
        JSON string containing activity results after successful completion
    """
    try:
        c = ctx.context
        adf_pipeline = ADFPipeline(
            subscription_id=c.subscription_id,
            resource_group_name=c.resource_group_name,
            resource_name=c.resource_name,
            auth=c.ensure_auth()
        )
        
        results = adf_pipeline.run_and_fetch(pipeline_name, activity_name, parameters)
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error in run_and_fetch operation: {str(e)}"


# ---------- ADF Pipelines Agent Factory ----------
def get_agent_adf_pipelines(
    user_input: Optional[str] = None,
    subscription_id: Optional[str] = None,
    resource_group_name: Optional[str] = None,
    resource_name: Optional[str] = None,
    context: Optional[AzureCtx] = None
) -> Agent[AzureCtx]:
    """
    Get the ADF Pipelines Agent instance.
    
    If context parameters are provided, they will be used to configure the agent's context.
    
    Args:
        user_input: Optional user's question or request (used when creating context)
        subscription_id: Optional Azure subscription ID
        resource_group_name: Optional Azure resource group name
        resource_name: Optional Azure Data Factory name
        context: Optional pre-configured context
    
    Returns:
        Agent[AzureCtx]: The ADF Pipelines Agent
    """

    yaml_path = Path(__file__).parent.parent / "prompts" / "pipelines_prompt.yaml"
    prompt_data = load_yaml_prompt(yaml_path)

    system_prompt = prompt_data.get("system_prompt", "You are an Azure Data Factory Pipelines specialist.")
    model = prompt_data.get("model", "gpt-4.1-mini")
    handoff_description = prompt_data.get("handoff_description", "ADF Pipelines Agent")

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
        name="ADF Pipelines Agent",
        model=OpenAIChatCompletionsModel(model, openai_client=_build_client()),
        instructions=system_prompt,
        tools=[
            run_and_fetch,
        ],
        handoff_description=handoff_description,
    )
    
    return agent, context 