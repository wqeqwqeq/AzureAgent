from __future__ import annotations
import logging
import os
import asyncio
from dotenv import load_dotenv

from openai import AsyncAzureOpenAI
from agents import Agent, Runner, trace, set_default_openai_client, set_tracing_disabled, OpenAIChatCompletionsModel, set_tracing_export_api_key
from agents.mcp import MCPServerStdio
import time

load_dotenv()

# Set up Azure OpenAI client
azure_openai_client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT")
)

openai_client = azure_openai_client
set_default_openai_client(openai_client)

# Set up tracing
set_tracing_export_api_key(os.getenv("OPENAI_API_KEY"))
set_tracing_disabled(False)

# Model configuration
model = OpenAIChatCompletionsModel(
    model="gpt-4o",
    openai_client=openai_client
)

# Agent instructions
instructions = """You are an Azure specialist with access to Azure mcp server.

You will be expect to ask questions related to Azure monitor
"""

async def main():
    """Demonstrate the ADF Linked Services agent with MCP server."""
    
    # MCP server parameters
    params = {"command": "npx", "args": ["-y", "@azure/mcp@latest", "server", "start"]}
    now = time.time()
    async with MCPServerStdio(params=params, client_session_timeout_seconds=240) as mcp_server:
        print(f"MCP server started in {time.time() - now} seconds")
        agent = Agent(
            name="azure key vault specialist", 
            instructions=instructions, 
            model=model, 
            mcp_servers=[mcp_server]
        )
        
        with trace("azure_key_vault_mcp_test"):
            print("\n=== Azure Key Vault Agent (MCP) Demo ===\n")
            request = "Show me all keys in my 'stanleyakvprod' Key Vault?"
            result = await Runner.run(agent, request)
            print(f"\nResponse: {result.final_output}\n")
            
    print("\n=== Demo Complete ===\n")

if __name__ == "__main__":
    asyncio.run(main()) 