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
from .shared_tools import set_azure_context




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
        # tools=[
        #     set_azure_context,
        # ],
        handoffs=[
            handoff(adf_linked_service_agent),
            handoff(adf_integration_runtime_agent),
            handoff(keyvault_agent),
            handoff(mcp_agent),
        ],
        **kwargs
    )
    return triage_agent, azure_mcp_server



async def run_triage_agent(question: str, azure_ctx: AzureCtx):
    """Run the triage agent with the given question and context."""
    triage_agent, azure_mcp_server = get_triage_agent()
    await azure_mcp_server.connect()
    
    # Run the agent
    result = await Runner.run(
        triage_agent,
        input=[{"content": question, "role": "user"}],
        context=azure_ctx
    )
    await azure_mcp_server.cleanup()
    
    return result
