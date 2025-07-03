import asyncio
from agents import Runner, trace
from DAPEAgent.triage_agent import get_triage_agent
from DAPEAgent.config import AzureCtx
from agents.mcp import MCPServerStdio
import time
import argparse

async def main():
    """Main async function to run the triage agent."""
    
    parser = argparse.ArgumentParser(description="Run the triage agent")
    parser.add_argument("--mcp", action="store_true", help="Use MCP server")
    args = parser.parse_args()

    if args.mcp:
        params = {"command": "npx", "args": ["-y", "@azure/mcp@latest", "server", "start"]}
        now = time.time()
        async with MCPServerStdio(params=params, client_session_timeout_seconds=240) as mcp_server:
            print(f"MCP server started in {time.time() - now} seconds")


            triage_agent = get_triage_agent(use_mcp_server=True, mcp_servers=[mcp_server])

            result = await Runner.run(
                triage_agent,
                input=[{"content": "Show me all resource groups in my subscription", "role": "user"}],
                context=AzureCtx(subscription_id="ee5f77a1-2e59-4335-8bdf-f7ea476f6523",
                                resource_group_name="SQL-RG",
                                )  # Add initial context instance
            )
            
            print("Agent Response:")
            print(result)
    else:
        triage_agent = get_triage_agent()
        result = await Runner.run(
                triage_agent,
                input=[{"content": "list keyvault in 'stanleyakvprod' ", "role": "user"}],
                context=AzureCtx(subscription_id="ee5f77a1-2e59-4335-8bdf-f7ea476f6523",
                                resource_group_name="adf",
                                )  # Add initial context instance
            )
        print("Agent Response:")
        print(result)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
