from agents.mcp import ToolFilterContext
from agents.mcp import MCPServerStdio

# %%
import os
from dotenv import load_dotenv

from openai import AsyncAzureOpenAI
from agents import Agent, Runner, trace, set_default_openai_client, set_tracing_disabled, OpenAIChatCompletionsModel, set_tracing_export_api_key
from agents.mcp import MCPServerStdio
import time
import asyncio
from agents.lifecycle import AgentHooks

load_dotenv()

# Set up Azure OpenAI client
azure_openai_client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY") or "",
    api_version=os.getenv("AZURE_OPENAI_API_VERSION") or "",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT") or "",
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT") or ""
)
# Model configuration
model = OpenAIChatCompletionsModel(
    model="gpt-4o",
    openai_client=azure_openai_client
)

set_tracing_disabled(True)

def allow_tools(ctx: ToolFilterContext, tool) -> bool:
    tool_list = ["microsoft_docs_search",
                "azmcp-azureterraformbestpractices-get",
                "azmcp-bestpractices-get",
                "azmcp-bicepschema-get",
                "azmcp-cosmos-account-list",
                "azmcp-cosmos-database-container-item-query",
                "azmcp-cosmos-database-container-list",
                "azmcp-cosmos-database-list",
                "azmcp-foundry-models-deploy",
                "azmcp-foundry-models-deployments-list",
                "azmcp-foundry-models-list",
                "azmcp-group-list",
                "azmcp-kusto-cluster-get",
                "azmcp-kusto-cluster-list",
                "azmcp-kusto-database-list",
                "azmcp-kusto-query",
                "azmcp-kusto-sample",
                "azmcp-kusto-table-list",
                "azmcp-kusto-table-schema",
                "azmcp-monitor-healthmodels-entity-gethealth",
                "azmcp-monitor-metrics-definitions",
                "azmcp-monitor-metrics-query",
                "azmcp-monitor-resource-log-query",
                "azmcp-monitor-table-list",
                "azmcp-monitor-table-type-list",
                "azmcp-monitor-workspace-list",
                "azmcp-monitor-workspace-log-query",
                "azmcp-role-assignment-list",
                "azmcp-subscription-list"]
    if tool.name in tool_list:
        return True
    return False


# Create MCP server without connecting
from agents.mcp import MCPServerStdioParams

# Custom agent hooks to handle MCP server lifecycle
class MCPServerHooks(AgentHooks):
    def __init__(self, mcp_server: MCPServerStdio):
        self.mcp_server = mcp_server
        self.test = 0
    async def on_start(self, context, agent):
        """Connect to MCP server when agent starts"""
        await self.mcp_server.connect()
        self.test += 1
        print(f"on_start: {self.test}")
    
    async def on_end(self, context, agent, output):
        """Cleanup MCP server when agent ends"""    
        await self.mcp_server.cleanup()
        self.test += 1
        print(f"on_end: {self.test}")
    



# Create agent with MCP server hooks



async def main():
   # MCP server parameters
    instructions = """You are an Github specialist with access to comprehensive Github MCP tools for managing and querying Github resources."""
    # MCP server parameters
    params = {"command": "docker", 
              "args": ["run", "-i", "--rm", 
                       "-e", f"GITHUB_PERSONAL_ACCESS_TOKEN={os.getenv('GITHUB_PAT')}", 
                       "-e", "GITHUB_READ_ONLY=1", 
                       "ghcr.io/github/github-mcp-server"]
              }
    now = time.time()
    mcp_server = MCPServerStdio(params=params, client_session_timeout_seconds=240)
    print(f"MCP server started in {time.time() - now} seconds")
    agent = Agent(
        name="azure key vault specialist", 
        instructions=instructions, 
        model=model, 
        mcp_servers=[mcp_server],
        hooks=MCPServerHooks(mcp_server)
    )
        
    with trace("github_mcp_test"):
        print("\n=== GITHUB Agent (MCP) Demo ===\n")
        request = "my username is wqeqwqeq, for flask_auto_search repo, any branch has merged into master and doesn't have any commit for 90 days?"
        result = await Runner.run(agent, request)
        print(f"\nResponse: {result.final_output}\n")
        

if __name__ == "__main__":
    asyncio.run(main())