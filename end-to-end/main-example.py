import asyncio
from agents import Runner, trace
from DAPEAgent.triage_agent import get_triage_agent
from DAPEAgent.config import AzureCtx
from agents.mcp import MCPServerStdio
import time
import argparse

import mlflow
from mlflow.openai._agent_tracer import add_mlflow_trace_processor  # <- internal API

# 1️⃣ call autolog with log_traces=False so NO SDK patching happens
mlflow.openai.autolog(log_traces=False)    

# 2️⃣ re-attach ONLY the Agent-SDK processor
add_mlflow_trace_processor()             

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("OpenAI-Agents-only")

from agents.mcp import ToolFilterContext

def rg_only(ctx: ToolFilterContext, tool) -> bool:
    """
    Keep only tools that act on resource groups and
    hide everything else.
    """
    return '-monitor-' in tool.name or '-kusto-' in tool.name or '-group-list' in tool.name
async def main():
    """Main async function to run the triage agent."""
    
    parser = argparse.ArgumentParser(description="Run the triage agent")
    parser.add_argument("--mcp", action="store_true", help="Use MCP server")
    args = parser.parse_args()

    if args.mcp:
        params = {"command": "npx", "args": ["-y", "@azure/mcp@latest", "server", "start"]}
        now = time.time()
        async with MCPServerStdio(params=params, client_session_timeout_seconds=240, tool_filter=rg_only) as mcp_server:
            print(f"MCP server started in {time.time() - now} seconds")


            triage_agent = get_triage_agent(use_mcp_server=True, mcp_servers=[mcp_server])

            result = await Runner.run(
                triage_agent,
                input=[{"content": "Show me all resource groups in my subscription", "role": "user"}],
                context=AzureCtx(subscription_id="ee5f77a1-2e59-4335-8bdf-f7ea476f6523"
                                )  # Add initial context instance
            )
            
            print("Agent Response:")
            print(result)
    else:
        triage_agent = get_triage_agent()
        result = await Runner.run(
                triage_agent,
                input=[{"content": "show me all the linked service in adf-stanley", "role": "user"}],
                context=AzureCtx(subscription_id="ee5f77a1-2e59-4335-8bdf-f7ea476f6523",
                                resource_group_name="SQL-RG",
                                )  # Add initial context instance
            )
        print("Agent Response:")
        print(result)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
